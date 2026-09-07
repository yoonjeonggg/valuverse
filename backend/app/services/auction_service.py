from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.timeutils import now, aware, is_past
from app.models.auction import Item, Bid, BlindBid
from app.schemas.auction import (
    ItemCreate,
    ItemUpdate,
    BidCreate,
    BlindBidCreate,
)


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
    if status_filter:
        q = q.filter(Item.status == status_filter)
    return q.order_by(Item.created_at.desc()).offset(skip).limit(limit).all()


def get_item(db: Session, item_id: int) -> Item:
    item = db.query(Item).filter(Item.id == item_id, Item.is_deleted.is_(False)).first()
    if not item:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "상품을 찾을 수 없습니다.")
    return item


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


# ==================== Bid ====================
def create_bid(db: Session, item_id: int, bidder_id: int, payload: BidCreate) -> Bid:
    item = get_item(db, item_id)
    if item.seller_id == bidder_id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "본인 상품에는 입찰할 수 없습니다.")
    if item.status != "ongoing" or is_past(item.end_time):
        raise HTTPException(status.HTTP_409_CONFLICT, "마감된 경매입니다.")
    if payload.amount <= item.current_price:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"현재가({item.current_price})보다 높은 금액이어야 합니다.",
        )

    bid = Bid(item_id=item_id, bidder_id=bidder_id, amount=payload.amount)
    item.current_price = payload.amount
    db.add(bid)
    db.commit()
    db.refresh(bid)
    return bid


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
