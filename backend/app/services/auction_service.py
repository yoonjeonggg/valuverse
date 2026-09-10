from datetime import timedelta

from fastapi import HTTPException, status
from sqlalchemy import case
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.timeutils import now, aware, is_past
from app.models.auction import Item, Bid, BlindBid
from app.models.user import User
from app.services import notification_service, point_service
from app.services.ws_manager import manager as ws_manager


def _iso(dt) -> str | None:
    return dt.isoformat() if dt else None
from app.schemas.auction import (
    ItemCreate,
    ItemUpdate,
    BidCreate,
    BlindBidCreate,
)


# ==================== 낙찰/마감 ====================
def _top_bid(db: Session, item_id: int) -> Bid | None:
    return (
        db.query(Bid)
        .filter(Bid.item_id == item_id, Bid.is_cancelled.is_(False))
        .order_by(Bid.amount.desc(), Bid.created_at.asc())
        .first()
    )


def _finalize(db: Session, item: Item) -> Item:
    """경매를 마감 상태로 확정한다. 최고 입찰자를 낙찰자로 기록.

    일반 입찰(Bid)과 블라인드 입찰(BlindBid) 중 존재하는 쪽을 사용하며,
    블라인드는 1st-price(제시가 그대로 낙찰)로 처리한다. 입찰이 없으면 유찰.
    """
    top = _top_bid(db, item.id)
    if top is None:
        blind_bids = _ranked_blind_bids(db, item.id)
        if blind_bids:
            winner = blind_bids[0]
            item.winner_id = winner.bidder_id
            # Vickrey: 2위 입찰가로 결제. 입찰자가 1명뿐이면 본인 제시가.
            if item.blind_price_rule == "second" and len(blind_bids) >= 2:
                item.final_price = blind_bids[1].amount
            else:
                item.final_price = winner.amount
            item.current_price = item.final_price
    else:
        item.winner_id = top.bidder_id
        item.final_price = top.amount

    item.status = "closed"
    if item.winner_id:
        notification_service.notify(
            db, item.winner_id, "won",
            f"'{item.title}' 경매에 낙찰되었습니다. (낙찰가 {item.final_price})",
            "item", item.id,
        )
        notification_service.notify(
            db, item.seller_id, "sold",
            f"'{item.title}' 경매가 낙찰되었습니다. (낙찰가 {item.final_price})",
            "item", item.id,
        )
    db.commit()
    db.refresh(item)
    ws_manager.broadcast(
        item.id,
        {
            "type": "closed",
            "item_id": item.id,
            "status": item.status,
            "winner_id": item.winner_id,
            "final_price": item.final_price,
        },
    )
    return item


def _finalize_if_ended(db: Session, item: Item) -> Item:
    if item.status == "ongoing" and is_past(item.end_time):
        return _finalize(db, item)
    return item


# ==================== Item ====================
def create_item(db: Session, seller_id: int, payload: ItemCreate) -> Item:
    item = Item(
        seller_id=seller_id,
        title=payload.title,
        description=payload.description,
        category=payload.category,
        image_url=payload.image_url,
        start_price=payload.start_price,
        buy_now_price=payload.buy_now_price,
        current_price=payload.start_price,
        auction_type=payload.auction_type,
        blind_price_rule=payload.blind_price_rule,
        end_time=payload.end_time,
        status="ongoing",
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def list_items(
    db: Session,
    category: str | None = None,
    status_filter: str | None = None,
    skip: int = 0,
    limit: int = 50,
) -> list[Item]:
    q = db.query(Item).filter(Item.is_deleted.is_(False))
    if category:
        q = q.filter(Item.category == category)

    # 상단 노출권이 살아있는 상품을 먼저 정렬한다 (FR-PRD-08).
    now_naive = now().replace(tzinfo=None)
    spotlighted = case(
        (Item.spotlight_until.is_(None), 0),
        (Item.spotlight_until < now_naive, 0),
        else_=1,
    )
    items = (
        q.order_by(spotlighted.desc(), Item.created_at.desc(), Item.id.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    for item in items:
        _finalize_if_ended(db, item)
    if status_filter:
        items = [i for i in items if i.status == status_filter]
    return items


def buy_spotlight(db: Session, item_id: int, user: User) -> Item:
    """포인트로 상단 노출권을 구매한다 (FR-PRD-08)."""
    item = get_item(db, item_id)
    if item.seller_id != user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "본인 상품만 노출할 수 있습니다.")
    if item.status != "ongoing":
        raise HTTPException(status.HTTP_409_CONFLICT, "진행중인 경매만 노출할 수 있습니다.")
    if user.points < settings.spotlight_cost:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "보유 포인트가 부족합니다.")

    base = now()
    current = aware(item.spotlight_until)
    if current and current > base:
        base = current  # 남은 시간에 이어붙인다
    item.spotlight_until = base + timedelta(hours=settings.spotlight_hours)

    point_service.apply_delta(
        db, user, -settings.spotlight_cost, "spend", f"상단 노출권 구매 #{item.id}"
    )
    db.commit()
    db.refresh(item)
    return item


def get_item(db: Session, item_id: int) -> Item:
    item = db.query(Item).filter(Item.id == item_id, Item.is_deleted.is_(False)).first()
    if not item:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "상품을 찾을 수 없습니다.")
    return _finalize_if_ended(db, item)


def _has_bids(db: Session, item_id: int) -> bool:
    return (
        db.query(Bid.id)
        .filter(Bid.item_id == item_id, Bid.is_cancelled.is_(False))
        .first()
        is not None
    )


def update_item(db: Session, item_id: int, user_id: int, payload: ItemUpdate) -> Item:
    item = get_item(db, item_id)
    if item.seller_id != user_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "본인 상품만 수정할 수 있습니다.")
    if _has_bids(db, item_id):
        raise HTTPException(
            status.HTTP_409_CONFLICT, "입찰이 시작된 상품은 수정할 수 없습니다."
        )
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(item, field, value)
    db.commit()
    db.refresh(item)
    return item


def delete_item(db: Session, item_id: int, user_id: int) -> None:
    item = get_item(db, item_id)
    if item.seller_id != user_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "본인 상품만 삭제할 수 있습니다.")
    if _has_bids(db, item_id):
        # 입찰이 있으면 소프트 삭제
        item.is_deleted = True
        item.status = "closed"
        db.commit()
    else:
        db.delete(item)
        db.commit()


def close_item(db: Session, item_id: int, user_id: int) -> Item:
    """판매자가 경매를 조기 마감하고 낙찰자를 확정한다."""
    item = get_item(db, item_id)
    if item.seller_id != user_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "본인 상품만 마감할 수 있습니다.")
    if item.status != "ongoing":
        raise HTTPException(status.HTTP_409_CONFLICT, "이미 마감된 경매입니다.")
    return _finalize(db, item)


def buy_now(db: Session, item_id: int, buyer_id: int) -> Item:
    """즉시구매가로 경매를 즉시 낙찰 처리한다."""
    item = get_item(db, item_id)
    if item.auction_type != "general":
        raise HTTPException(
            status.HTTP_409_CONFLICT, "블라인드 경매는 즉시구매를 지원하지 않습니다."
        )
    if item.buy_now_price is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "즉시구매가 없는 상품입니다.")
    if item.seller_id == buyer_id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "본인 상품은 구매할 수 없습니다.")
    if item.status != "ongoing" or is_past(item.end_time):
        raise HTTPException(status.HTTP_409_CONFLICT, "마감된 경매입니다.")
    if item.current_price >= item.buy_now_price:
        raise HTTPException(
            status.HTTP_409_CONFLICT, "현재가가 즉시구매가 이상입니다."
        )

    price = item.buy_now_price
    db.add(Bid(item_id=item_id, bidder_id=buyer_id, amount=price))
    item.current_price = price
    item.status = "closed"
    item.winner_id = buyer_id
    item.final_price = price
    notification_service.notify(
        db, item.seller_id, "sold",
        f"'{item.title}' 상품이 즉시구매로 판매되었습니다. (금액 {price})",
        "item", item.id,
    )
    db.commit()
    db.refresh(item)
    ws_manager.broadcast(
        item.id,
        {
            "type": "closed",
            "item_id": item.id,
            "status": item.status,
            "winner_id": item.winner_id,
            "final_price": item.final_price,
            "reason": "buy_now",
        },
    )
    return item


# ==================== Bid ====================
def _lock_item(db: Session, item_id: int) -> Item:
    """입찰 처리 동안 상품 행을 잠근다 (NFR-02, 동시 입찰 정합성).

    SQLite 는 행 잠금을 지원하지 않으므로 그 경우엔 일반 조회로 대체한다.
    """
    q = db.query(Item).filter(Item.id == item_id, Item.is_deleted.is_(False))
    if db.bind and db.bind.dialect.name != "sqlite":
        q = q.with_for_update()
    item = q.first()
    if not item:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "상품을 찾을 수 없습니다.")
    return _finalize_if_ended(db, item)


def create_bid(db: Session, item_id: int, bidder_id: int, payload: BidCreate) -> Bid:
    item = _lock_item(db, item_id)
    if item.auction_type != "general":
        raise HTTPException(
            status.HTTP_409_CONFLICT, "블라인드 경매는 비공개 입찰을 사용하세요."
        )
    if item.seller_id == bidder_id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "본인 상품에는 입찰할 수 없습니다.")
    if item.status != "ongoing" or is_past(item.end_time):
        raise HTTPException(status.HTTP_409_CONFLICT, "마감된 경매입니다.")
    if payload.amount <= item.current_price:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"현재가({item.current_price})보다 높은 금액이어야 합니다.",
        )

    # 직전 최고 입찰자 (경쟁 알림 대상)
    prev_top = _top_bid(db, item_id)

    bid = Bid(item_id=item_id, bidder_id=bidder_id, amount=payload.amount)
    item.current_price = payload.amount
    db.add(bid)

    if prev_top and prev_top.bidder_id != bidder_id:
        notification_service.notify(
            db, prev_top.bidder_id, "bid_outbid",
            f"'{item.title}' 경매에서 더 높은 입찰가가 등장했습니다. (현재가 {payload.amount})",
            "item", item.id,
        )

    # 스나이핑 방지: 마감 임박 입찰이면 마감시간을 연장한다 (FR-AUC-03)
    _maybe_extend(item)

    db.commit()
    db.refresh(bid)
    ws_manager.broadcast(
        item_id,
        {
            "type": "bid",
            "item_id": item_id,
            "bid_id": bid.id,
            "bidder_id": bidder_id,
            "amount": bid.amount,
            "current_price": item.current_price,
            "end_time": _iso(item.end_time),
            "extended_count": item.extended_count,
        },
    )
    return bid


def _maybe_extend(item: Item) -> None:
    end = aware(item.end_time)
    if end is None:
        return
    remaining = (end - now()).total_seconds()
    if (
        0 < remaining <= settings.auction_extend_window_seconds
        and item.extended_count < settings.auction_max_extensions
    ):
        item.end_time = end + timedelta(seconds=settings.auction_extend_by_seconds)
        item.extended_count += 1


def list_bids_for_item(db: Session, item_id: int) -> list[Bid]:
    get_item(db, item_id)
    return (
        db.query(Bid)
        .filter(Bid.item_id == item_id)
        .order_by(Bid.amount.desc(), Bid.created_at.asc())
        .all()
    )


def list_my_bids(db: Session, user_id: int) -> list[Bid]:
    return (
        db.query(Bid)
        .filter(Bid.bidder_id == user_id)
        .order_by(Bid.created_at.desc())
        .all()
    )


def cancel_bid(db: Session, bid_id: int, user_id: int) -> None:
    bid = db.query(Bid).filter(Bid.id == bid_id).first()
    if not bid:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "입찰을 찾을 수 없습니다.")
    if bid.bidder_id != user_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "본인 입찰만 취소할 수 있습니다.")
    if bid.is_cancelled:
        raise HTTPException(status.HTTP_409_CONFLICT, "이미 취소된 입찰입니다.")

    # 정책: 등록 직후 5분 이내에만 취소 허용
    created = aware(bid.created_at)
    if created is not None and (now() - created).total_seconds() > 300:
        raise HTTPException(
            status.HTTP_409_CONFLICT, "입찰 후 5분이 지나 취소할 수 없습니다."
        )

    bid.is_cancelled = True

    # 최고가였다면 현재가 재계산
    item = get_item(db, bid.item_id)
    top = (
        db.query(Bid)
        .filter(Bid.item_id == bid.item_id, Bid.is_cancelled.is_(False))
        .order_by(Bid.amount.desc())
        .first()
    )
    item.current_price = top.amount if top else item.start_price
    db.commit()


# ==================== Blind Bid ====================
def create_blind_bid(
    db: Session, item_id: int, bidder_id: int, payload: BlindBidCreate
) -> BlindBid:
    item = get_item(db, item_id)
    if item.auction_type != "blind":
        raise HTTPException(
            status.HTTP_409_CONFLICT, "블라인드 경매가 아닙니다."
        )
    if item.status != "ongoing" or is_past(item.end_time):
        raise HTTPException(status.HTTP_409_CONFLICT, "마감된 경매입니다.")
    if item.seller_id == bidder_id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "본인 상품에는 입찰할 수 없습니다.")

    existing = (
        db.query(BlindBid)
        .filter(
            BlindBid.item_id == item_id,
            BlindBid.bidder_id == bidder_id,
            BlindBid.is_cancelled.is_(False),
        )
        .first()
    )
    if existing:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "이미 입찰했습니다. 취소 후 재입찰하세요.",
        )

    bid = BlindBid(item_id=item_id, bidder_id=bidder_id, amount=payload.amount)
    db.add(bid)
    db.commit()
    db.refresh(bid)
    return bid


def _ranked_blind_bids(db: Session, item_id: int) -> list[BlindBid]:
    return (
        db.query(BlindBid)
        .filter(BlindBid.item_id == item_id, BlindBid.is_cancelled.is_(False))
        .order_by(BlindBid.amount.desc(), BlindBid.created_at.asc())
        .all()
    )


def get_my_blind_rank(db: Session, item_id: int, user_id: int) -> dict:
    get_item(db, item_id)
    bids = _ranked_blind_bids(db, item_id)
    for idx, b in enumerate(bids, start=1):
        if b.bidder_id == user_id:
            return {
                "item_id": item_id,
                "my_bid_id": b.id,
                "rank": idx,
                "total_bids": len(bids),
            }
    raise HTTPException(status.HTTP_404_NOT_FOUND, "입찰 내역이 없습니다.")


def get_blind_results(db: Session, item_id: int) -> list[dict]:
    item = get_item(db, item_id)
    if item.status != "closed" and not is_past(item.end_time):
        raise HTTPException(
            status.HTTP_409_CONFLICT, "마감 후에만 결과를 조회할 수 있습니다."
        )
    bids = _ranked_blind_bids(db, item_id)
    return [
        {"id": b.id, "bidder_id": b.bidder_id, "amount": b.amount, "rank": idx}
        for idx, b in enumerate(bids, start=1)
    ]


def cancel_blind_bid(db: Session, bid_id: int, user_id: int) -> None:
    bid = db.query(BlindBid).filter(BlindBid.id == bid_id).first()
    if not bid:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "입찰을 찾을 수 없습니다.")
    if bid.bidder_id != user_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "본인 입찰만 취소할 수 있습니다.")
    item = get_item(db, bid.item_id)
    if item.status == "closed" or is_past(item.end_time):
        raise HTTPException(status.HTTP_409_CONFLICT, "마감 후에는 취소할 수 없습니다.")
    bid.is_cancelled = True
    db.commit()
