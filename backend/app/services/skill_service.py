import logging
from datetime import timedelta

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.db_utils import apply_patch, get_or_404, save
from app.core.errors import BadRequest, Conflict, Forbidden
from app.core.timeutils import aware, is_past, now, require_future
from app.models.auction import Item
from app.models.skill import Escrow, SkillBid, SkillBooking, SkillItem
from app.models.user import User
from app.schemas.skill import (
    EscrowCreate,
    EscrowUpdate,
    SkillBidCreate,
    SkillBookingCreate,
    SkillBookingUpdate,
    SkillItemCreate,
    SkillItemUpdate,
)
from app.services import notification_service, point_service

logger = logging.getLogger(__name__)


def _release_escrow(db: Session, escrow: Escrow, settle: bool) -> None:
    """보관중인 에스크로를 판매자에게 정산(settle=True)하거나 구매자에게 환불한다."""
    verb = "정산" if settle else "환불"
    if escrow.status != "holding":
        raise Conflict(f"보관중 상태의 에스크로만 {verb}할 수 있습니다.")
    recipient = db.get(User, escrow.payee_id if settle else escrow.payer_id)
    point_service.apply_delta(
        db,
        recipient,
        escrow.amount,
        "etc" if settle else "refund",
        f"스킬 거래 {verb} (에스크로 #{escrow.id})",
    )
    escrow.status = "settled" if settle else "refunded"
    logger.info(
        "에스크로 %s escrow_id=%s recipient_id=%s amount=%s",
        verb,
        escrow.id,
        recipient.id,
        escrow.amount,
    )


def _booking_escrow(db: Session, booking_id: int) -> Escrow | None:
    return db.query(Escrow).filter(Escrow.booking_id == booking_id).first()


# ==================== SkillItem ====================
def create_skill_item(db: Session, seller_id: int, payload: SkillItemCreate) -> SkillItem:
    require_future(payload.end_time)
    item = SkillItem(
        seller_id=seller_id,
        status="recruiting",
        current_price=payload.start_price,
        **payload.model_dump(),
    )
    db.add(item)
    return save(db, item)


def list_skill_items(
    db: Session,
    category: str | None = None,
    status_filter: str | None = None,
    skip: int = 0,
    limit: int = 50,
) -> list[SkillItem]:
    # 마감 시간이 지났는데 아직 확정 전인 상품을 먼저 낙찰/유찰로 확정해야
    # 상태 필터와 페이지 크기가 맞는다.
    _finalize_expired(db)
    q = db.query(SkillItem).filter(SkillItem.is_deleted.is_(False))
    if category:
        q = q.filter(SkillItem.category == category)
    if status_filter:
        q = q.filter(SkillItem.status == status_filter)
    return q.order_by(SkillItem.created_at.desc()).offset(skip).limit(limit).all()


def get_skill_item(db: Session, item_id: int, for_update: bool = False) -> SkillItem:
    item = get_or_404(
        db,
        SkillItem,
        item_id,
        "스킬 상품을 찾을 수 없습니다.",
        SkillItem.is_deleted.is_(False),
        for_update=for_update,
    )
    return _finalize_if_ended(db, item)


def _has_bids(db: Session, item_id: int) -> bool:
    return db.query(SkillBid.id).filter(SkillBid.skill_item_id == item_id).first() is not None


def _get_editable_skill_item(db: Session, item_id: int, user_id: int, action: str) -> SkillItem:
    """판매자 본인이고, 입찰이 들어오기 전인 스킬 상품만 수정/삭제할 수 있다."""
    item = get_skill_item(db, item_id)
    if item.seller_id != user_id:
        raise Forbidden(f"본인 상품만 {action}할 수 있습니다.")
    if item.status != "recruiting":
        raise Conflict(f"마감된 상품은 {action}할 수 없습니다.")
    if _has_bids(db, item_id):
        raise Conflict(f"입찰이 시작된 상품은 {action}할 수 없습니다.")
    return item


def update_skill_item(
    db: Session, item_id: int, user_id: int, payload: SkillItemUpdate
) -> SkillItem:
    item = _get_editable_skill_item(db, item_id, user_id, "수정")
    require_future(payload.end_time)
    apply_patch(item, payload)
    return save(db, item)


def delete_skill_item(db: Session, item_id: int, user_id: int) -> None:
    item = _get_editable_skill_item(db, item_id, user_id, "삭제")
    item.is_deleted = True
    db.commit()


# ==================== 입찰 / 마감 (FR-SKL-07) ====================
# 흐름: 모집중(recruiting)에 공개 입찰 -> 마감 시 최고 입찰자를 낙찰자로 확정(awarded)
# -> 판매자가 낙찰자에게 일정을 정해 예약 요청 -> 낙찰자가 수락하면 낙찰가를 에스크로에 보관.
# 입찰이 없으면 유찰(closed). 일반 경매와 같은 행 잠금·자동 연장 규칙을 쓴다.
def _top_bid(db: Session, item_id: int) -> SkillBid | None:
    return (
        db.query(SkillBid)
        .filter(SkillBid.skill_item_id == item_id)
        .order_by(SkillBid.amount.desc(), SkillBid.created_at.asc(), SkillBid.id.asc())
        .first()
    )


def _finalize(db: Session, item: SkillItem) -> SkillItem:
    """입찰을 마감하고 최고 입찰자를 낙찰자로 확정한다. 입찰이 없으면 유찰."""
    top = _top_bid(db, item.id)
    if top is None:
        item.status = "closed"
    else:
        item.status = "awarded"
        item.winner_id = top.bidder_id
        item.final_price = top.amount
        notification_service.notify(
            db,
            top.bidder_id,
            "won",
            f"'{item.title}' 스킬 경매에 낙찰되었습니다. (낙찰가 {top.amount}) "
            "판매자가 일정을 정해 예약을 요청합니다.",
            "skill_item",
            item.id,
        )
        notification_service.notify(
            db,
            item.seller_id,
            "sold",
            f"'{item.title}' 스킬 경매가 낙찰되었습니다. (낙찰가 {top.amount}) "
            "낙찰자에게 예약을 요청하세요.",
            "skill_item",
            item.id,
        )
    db.commit()
    db.refresh(item)
    logger.info(
        "스킬 경매 마감 skill_item_id=%s winner_id=%s final_price=%s",
        item.id,
        item.winner_id,
        item.final_price,
    )
    return item


def _finalize_if_ended(db: Session, item: SkillItem) -> SkillItem:
    """마감 시간이 지난 모집중 상품을 낙찰/유찰로 확정한다.

    조회 요청 여러 개가 동시에 같은 상품을 확정해 알림이 두 번 가지 않도록,
    행을 잠근 뒤 상태를 다시 확인하고 확정한다.
    """
    if item.status != "recruiting" or not is_past(item.end_time):
        return item
    locked = (
        db.query(SkillItem)
        .filter(SkillItem.id == item.id)
        .populate_existing()
        .with_for_update()
        .one()
    )
    if locked.status == "recruiting" and is_past(locked.end_time):
        return _finalize(db, locked)
    return locked


def _finalize_expired(db: Session) -> None:
    now_naive = now().replace(tzinfo=None)
    expired_ids = [
        row.id
        for row in db.query(SkillItem.id).filter(
            SkillItem.status == "recruiting",
            SkillItem.is_deleted.is_(False),
            SkillItem.end_time.is_not(None),
            SkillItem.end_time <= now_naive,
        )
    ]
    for item_id in expired_ids:
        _finalize_if_ended(db, db.get(SkillItem, item_id))


def _maybe_extend(item: SkillItem) -> None:
    """스나이핑 방지: 마감 임박 입찰이면 마감 시간을 연장한다 (일반 경매와 같은 규칙)."""
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


def create_bid(db: Session, item_id: int, bidder: User, payload: SkillBidCreate) -> SkillBid:
    # 동시 입찰이 최고가를 덮어쓰지 않도록 상품 행을 잠그고 검증~갱신을 한 트랜잭션에서 한다.
    item = get_skill_item(db, item_id, for_update=True)
    if item.seller_id == bidder.id:
        raise BadRequest("본인 상품에는 입찰할 수 없습니다.")
    if item.status != "recruiting" or is_past(item.end_time):
        raise Conflict("마감된 스킬 경매입니다.")

    prev_top = _top_bid(db, item.id)
    if prev_top is None:
        if payload.amount < item.start_price:
            raise BadRequest(f"시작가({item.start_price}) 이상이어야 합니다.")
    elif payload.amount <= item.current_price:
        raise BadRequest(f"현재가({item.current_price})보다 높은 금액이어야 합니다.")
    # 낙찰가는 수락 시 포인트로 결제되므로, 지금 낼 수 없는 금액으로는 입찰하지 못하게 한다.
    # (수락 시점에 잔액을 다시 확인하므로 여기서는 잠그지 않는다.)
    if point_service.get_balance(db, bidder.id) < payload.amount:
        raise BadRequest("포인트가 부족해 입찰할 수 없습니다.")

    bid = SkillBid(skill_item_id=item.id, bidder_id=bidder.id, amount=payload.amount)
    db.add(bid)
    item.current_price = payload.amount
    if prev_top and prev_top.bidder_id != bidder.id:
        notification_service.notify(
            db,
            prev_top.bidder_id,
            "bid_outbid",
            f"'{item.title}' 스킬 경매에서 더 높은 입찰가가 등장했습니다. "
            f"(현재가 {payload.amount})",
            "skill_item",
            item.id,
        )
    _maybe_extend(item)
    return save(db, bid)


def list_bids(db: Session, item_id: int) -> list[SkillBid]:
    get_skill_item(db, item_id)
    return (
        db.query(SkillBid)
        .filter(SkillBid.skill_item_id == item_id)
        .order_by(SkillBid.amount.desc(), SkillBid.created_at.asc())
        .all()
    )


def list_my_bids(db: Session, user_id: int) -> list[SkillBid]:
    return (
        db.query(SkillBid)
        .filter(SkillBid.bidder_id == user_id)
        .order_by(SkillBid.created_at.desc())
        .all()
    )


def close_skill_item(db: Session, item_id: int, user_id: int) -> SkillItem:
    """판매자가 입찰을 조기 마감하고 낙찰자를 확정한다."""
    item = get_skill_item(db, item_id, for_update=True)
    if item.seller_id != user_id:
        raise Forbidden("본인 상품만 마감할 수 있습니다.")
    if item.status != "recruiting":
        raise Conflict("이미 마감된 스킬 경매입니다.")
    return _finalize(db, item)


# ==================== SkillBooking ====================
_OPEN_BOOKING = ("pending", "in_progress")


# 흐름: 판매자가 낙찰자에게 일정을 정해 예약을 "요청"(pending) -> 낙찰자가 수락하면 그때
# 낙찰가를 포인트에서 차감해 에스크로에 보관(in_progress) -> 완료(정산) / 노쇼 / 취소(환불).
# 구매자 동의 없이 판매자가 남의 포인트를 차감하지 못하도록 차감은 수락 시점에만 한다.
# 구매자와 금액은 낙찰 결과로 정해져 판매자가 임의로 지정할 수 없다.
def create_booking(db: Session, seller: User, payload: SkillBookingCreate) -> SkillBooking:
    # 같은 상품에 예약 요청이 동시에 두 번 들어와도 하나만 생기도록 상품 행을 잠근다.
    skill_item = get_skill_item(db, payload.skill_item_id, for_update=True)
    if skill_item.seller_id != seller.id:
        raise Forbidden("해당 스킬 상품의 판매자만 예약을 생성할 수 있습니다.")
    if skill_item.status != "awarded" or skill_item.winner_id is None:
        raise Conflict("낙찰된 스킬 상품만 예약을 요청할 수 있습니다.")
    open_booking = (
        db.query(SkillBooking.id)
        .filter(
            SkillBooking.skill_item_id == skill_item.id,
            SkillBooking.status.in_(_OPEN_BOOKING),
        )
        .first()
    )
    if open_booking:
        raise Conflict("이미 진행중인 예약 요청이 있습니다.")

    booking = SkillBooking(
        skill_item_id=skill_item.id,
        seller_id=seller.id,
        buyer_id=skill_item.winner_id,
        amount=skill_item.final_price,
        scheduled_at=payload.scheduled_at,
        status="pending",
    )
    db.add(booking)
    notification_service.notify(
        db,
        skill_item.winner_id,
        "booking",
        f"'{skill_item.title}' 스킬 예약 요청이 도착했습니다. "
        f"수락하면 낙찰가 {skill_item.final_price} 포인트가 에스크로에 보관됩니다.",
        "skill_item",
        skill_item.id,
    )
    return save(db, booking)


def accept_booking(db: Session, booking_id: int, user: User) -> SkillBooking:
    """구매자가 예약 요청을 수락하면 포인트를 차감해 에스크로에 보관한다 (FR-SKL-03)."""
    booking = _lock_booking(db, booking_id, user)
    if user.id != booking.buyer_id:
        raise Forbidden("구매자만 수락할 수 있습니다.")
    if booking.status != "pending":
        raise Conflict("수락 대기중인 예약이 아닙니다.")

    point_service.spend(
        db, user.id, booking.amount, "spend", f"스킬 낙찰 보관 #{booking.skill_item_id}"
    )
    db.add(
        Escrow(
            booking_id=booking.id,
            payer_id=user.id,
            payee_id=booking.seller_id,
            amount=booking.amount,
            status="holding",
        )
    )
    booking.status = "in_progress"
    notification_service.notify(
        db,
        booking.seller_id,
        "booking",
        "구매자가 스킬 예약을 수락했습니다.",
        "skill_item",
        booking.skill_item_id,
    )
    return save(db, booking)


def complete_booking(db: Session, booking_id: int, user: User) -> SkillBooking:
    """구매자가 서비스 완료를 확인하면 에스크로를 판매자에게 정산한다 (FR-SKL-03)."""
    booking = _lock_booking(db, booking_id, user)
    if user.id != booking.buyer_id and not user.is_admin:
        raise Forbidden("구매자만 완료를 확인할 수 있습니다.")
    if booking.status != "in_progress":
        raise Conflict("진행중인 예약이 아닙니다.")

    escrow = _booking_escrow(db, booking.id)
    if escrow:
        _release_escrow(db, escrow, settle=True)
    booking.status = "completed"
    _set_skill_item_status(db, booking.skill_item_id, "closed")
    notification_service.notify(
        db,
        booking.seller_id,
        "settlement",
        f"스킬 거래가 완료되어 {booking.amount} 포인트가 정산되었습니다.",
        "skill_item",
        booking.skill_item_id,
    )
    return save(db, booking)


def no_show_booking(db: Session, booking_id: int, user: User, party: str) -> SkillBooking:
    """노쇼 처리 (FR-SKL-05). 신고는 거래 상대방에 대해서만 할 수 있다.

    - 판매자 노쇼(구매자가 신고): 구매자에게 전액 환불.
    - 구매자 노쇼(판매자가 신고): 판매자에게 정산 (노쇼한 구매자가 포인트를 잃는다).
    """
    booking = _lock_booking(db, booking_id, user)
    if booking.status != "in_progress":
        raise Conflict("진행중인 예약이 아닙니다.")
    # 스스로 노쇼했다고 신고해 환불받거나, 제3자가 대신 신고하지 못하게 한다.
    reporter = booking.buyer_id if party == "seller" else booking.seller_id
    if user.id != reporter and not user.is_admin:
        raise Forbidden("노쇼는 거래 상대방만 신고할 수 있습니다.")

    escrow = _booking_escrow(db, booking.id)
    if escrow:
        # 판매자 노쇼면 구매자에게 환불, 구매자 노쇼면 판매자에게 정산.
        _release_escrow(db, escrow, settle=party != "seller")
    booking.status = "no_show"
    _set_skill_item_status(db, booking.skill_item_id, "closed")

    victim = booking.buyer_id if party == "seller" else booking.seller_id
    who = "판매자" if party == "seller" else "구매자"
    notification_service.notify(
        db,
        victim,
        "no_show",
        f"스킬 예약이 {who} 노쇼로 종료되었습니다.",
        "skill_item",
        booking.skill_item_id,
    )
    return save(db, booking)


def _set_skill_item_status(db: Session, skill_item_id: int, new_status: str) -> None:
    item = db.get(SkillItem, skill_item_id)
    if item:
        item.status = new_status


def list_my_bookings(db: Session, user_id: int) -> list[SkillBooking]:
    return (
        db.query(SkillBooking)
        .filter((SkillBooking.seller_id == user_id) | (SkillBooking.buyer_id == user_id))
        .order_by(SkillBooking.created_at.desc())
        .all()
    )


def _party_filter(user: User, *cols):
    """관리자가 아니면 당사자 행만 보이게 한다. 남의 행은 403 대신 404 로 존재 여부를 숨긴다."""
    if user.is_admin:
        return ()
    return (or_(*(c == user.id for c in cols)),)


def get_booking(db: Session, booking_id: int, user: User, for_update: bool = False) -> SkillBooking:
    return get_or_404(
        db,
        SkillBooking,
        booking_id,
        "예약을 찾을 수 없습니다.",
        *_party_filter(user, SkillBooking.seller_id, SkillBooking.buyer_id),
        for_update=for_update,
    )


def _lock_booking(db: Session, booking_id: int, user: User) -> SkillBooking:
    """상태 전환(수락/완료/노쇼/취소)이 동시에 와도 이중 정산·환불하지 않도록 행을 잠근다."""
    return get_booking(db, booking_id, user, for_update=True)


def update_booking(
    db: Session, booking_id: int, user: User, payload: SkillBookingUpdate
) -> SkillBooking:
    booking = get_booking(db, booking_id, user)
    if booking.status not in _OPEN_BOOKING:
        raise Conflict("진행중인 예약만 변경할 수 있습니다.")
    data = payload.model_dump(exclude_unset=True)
    # 상태 전환(수락/정산/노쇼/취소)은 전용 엔드포인트로만 처리한다.
    if data.get("status") not in (None, booking.status):
        raise BadRequest(
            "상태 변경은 accept / complete / no-show / DELETE 엔드포인트를 사용하세요."
        )
    if payload.scheduled_at is not None:
        booking.scheduled_at = payload.scheduled_at
    return save(db, booking)


def cancel_booking(db: Session, booking_id: int, user: User) -> None:
    """예약 취소(요청 거절 포함).

    수락 전이면 낙찰 상태를 유지해 판매자가 다른 일정으로 다시 요청할 수 있고,
    수락 후면 낙찰자에게 환불하고 거래를 종료한다.
    """
    booking = _lock_booking(db, booking_id, user)
    if booking.status not in _OPEN_BOOKING:
        raise Conflict("이미 종료된 예약입니다.")
    if booking.status == "in_progress":
        escrow = _booking_escrow(db, booking.id)
        if escrow and escrow.status == "holding":
            _release_escrow(db, escrow, settle=False)
        _set_skill_item_status(db, booking.skill_item_id, "closed")
    booking.status = "cancelled"
    other = booking.seller_id if user.id == booking.buyer_id else booking.buyer_id
    notification_service.notify(
        db,
        other,
        "booking",
        "스킬 예약이 취소되었습니다.",
        "skill_item",
        booking.skill_item_id,
    )
    db.commit()


# ==================== Escrow ====================
# 스킬 예약에 딸린 에스크로는 예약 엔드포인트(accept/complete/no-show/cancel)로만 움직인다.
# 여기는 일반 경매 상품 대금을 직접 맡기는 용도.
def create_escrow(db: Session, payer: User, payload: EscrowCreate) -> Escrow:
    item = get_or_404(
        db, Item, payload.item_id, "상품을 찾을 수 없습니다.", Item.is_deleted.is_(False)
    )
    if payload.payee_id != item.seller_id:
        raise BadRequest("상품 판매자에게만 에스크로 결제할 수 있습니다.")
    if payload.payee_id == payer.id:
        raise BadRequest("본인에게 보낼 수 없습니다.")
    # 결제자 포인트를 차감해 보관한다. 정산/환불 시 이동한다.
    point_service.spend(db, payer.id, payload.amount, "spend", "에스크로 보관")
    escrow = Escrow(
        item_id=item.id,
        payer_id=payer.id,
        payee_id=payload.payee_id,
        amount=payload.amount,
        status="holding",
    )
    db.add(escrow)
    return save(db, escrow)


def get_escrow(db: Session, escrow_id: int, user: User, for_update: bool = False) -> Escrow:
    return get_or_404(
        db,
        Escrow,
        escrow_id,
        "에스크로를 찾을 수 없습니다.",
        *_party_filter(user, Escrow.payer_id, Escrow.payee_id),
        for_update=for_update,
    )


def update_escrow_status(db: Session, escrow_id: int, user: User, payload: EscrowUpdate) -> Escrow:
    escrow = get_escrow(db, escrow_id, user, for_update=True)
    if escrow.booking_id is not None:
        raise Conflict("스킬 예약 에스크로는 예약에서 처리해야 합니다.")
    # 받는 쪽이 스스로 정산하거나 낸 쪽이 일방적으로 환불받지 못하게 한다:
    # 정산(판매자에게 지급)은 결제자가 확정하고, 환불은 수취인이 승인한다.
    if payload.status == "settled":
        if user.id != escrow.payer_id and not user.is_admin:
            raise Forbidden("결제자만 정산을 확정할 수 있습니다.")
        _release_escrow(db, escrow, settle=True)
    else:  # refunded
        if user.id != escrow.payee_id and not user.is_admin:
            raise Forbidden("수취인만 환불을 승인할 수 있습니다.")
        _release_escrow(db, escrow, settle=False)
    return save(db, escrow)
