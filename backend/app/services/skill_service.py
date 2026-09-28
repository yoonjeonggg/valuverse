from fastapi import HTTPException, status
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.db_utils import get_or_404
from app.models.auction import Item
from app.models.skill import SkillItem, SkillBooking, Escrow
from app.models.user import User
from app.schemas.skill import (
    SkillItemCreate,
    SkillItemUpdate,
    SkillBookingCreate,
    SkillBookingUpdate,
    EscrowCreate,
    EscrowUpdate,
)
from app.services import notification_service
from app.services.point_service import apply_delta as _move_points


def _settle_escrow(db: Session, escrow: Escrow) -> None:
    """보관중인 에스크로를 판매자에게 정산한다."""
    if escrow.status != "holding":
        raise HTTPException(
            status.HTTP_409_CONFLICT, "보관중 상태의 에스크로만 정산할 수 있습니다."
        )
    payee = db.get(User, escrow.payee_id)
    _move_points(db, payee, escrow.amount, "etc", f"스킬 거래 정산 (에스크로 #{escrow.id})")
    escrow.status = "settled"


def _refund_escrow(db: Session, escrow: Escrow) -> None:
    """보관중인 에스크로를 구매자에게 환불한다."""
    if escrow.status != "holding":
        raise HTTPException(
            status.HTTP_409_CONFLICT, "보관중 상태의 에스크로만 환불할 수 있습니다."
        )
    payer = db.get(User, escrow.payer_id)
    _move_points(db, payer, escrow.amount, "refund", f"스킬 거래 환불 (에스크로 #{escrow.id})")
    escrow.status = "refunded"


def _booking_escrow(db: Session, booking_id: int) -> Escrow | None:
    return db.query(Escrow).filter(Escrow.booking_id == booking_id).first()


# ==================== SkillItem ====================
def create_skill_item(db: Session, seller_id: int, payload: SkillItemCreate) -> SkillItem:
    item = SkillItem(seller_id=seller_id, status="recruiting", **payload.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def list_skill_items(
    db: Session,
    category: str | None = None,
    status_filter: str | None = None,
    skip: int = 0,
    limit: int = 50,
) -> list[SkillItem]:
    q = db.query(SkillItem).filter(SkillItem.is_deleted.is_(False))
    if category:
        q = q.filter(SkillItem.category == category)
    if status_filter:
        q = q.filter(SkillItem.status == status_filter)
    return q.order_by(SkillItem.created_at.desc()).offset(skip).limit(limit).all()


def get_skill_item(db: Session, item_id: int) -> SkillItem:
    return get_or_404(
        db, SkillItem, item_id, "스킬 상품을 찾을 수 없습니다.", SkillItem.is_deleted.is_(False)
    )


def update_skill_item(
    db: Session, item_id: int, user_id: int, payload: SkillItemUpdate
) -> SkillItem:
    item = get_skill_item(db, item_id)
    if item.seller_id != user_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "본인 상품만 수정할 수 있습니다.")
    if item.status != "recruiting":
        raise HTTPException(status.HTTP_409_CONFLICT, "낙찰 후에는 수정할 수 없습니다.")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(item, field, value)
    db.commit()
    db.refresh(item)
    return item


def delete_skill_item(db: Session, item_id: int, user_id: int) -> None:
    item = get_skill_item(db, item_id)
    if item.seller_id != user_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "본인 상품만 삭제할 수 있습니다.")
    if item.status != "recruiting":
        raise HTTPException(status.HTTP_409_CONFLICT, "낙찰 후에는 삭제할 수 없습니다.")
    item.is_deleted = True
    db.commit()


# ==================== SkillBooking ====================
_OPEN_BOOKING = ("pending", "in_progress")

# 흐름: 판매자가 구매자에게 예약을 "요청"(pending) -> 구매자가 수락하면 그때 구매자
# 포인트를 차감해 에스크로에 보관(in_progress) -> 완료(정산) / 노쇼 / 취소(환불).
# 구매자 동의 없이 판매자가 남의 포인트를 차감하지 못하도록 차감은 수락 시점에만 한다.
def create_booking(
    db: Session, seller: User, payload: SkillBookingCreate
) -> SkillBooking:
    skill_item = get_skill_item(db, payload.skill_item_id)
    if skill_item.seller_id != seller.id:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, "해당 스킬 상품의 판매자만 예약을 생성할 수 있습니다."
        )
    if skill_item.status != "recruiting":
        raise HTTPException(status.HTTP_409_CONFLICT, "이미 낙찰된 스킬 상품입니다.")
    if payload.buyer_id == seller.id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "본인에게 예약할 수 없습니다.")
    buyer = get_or_404(
        db, User, payload.buyer_id, "구매자를 찾을 수 없습니다.", User.is_active.is_(True)
    )

    booking = SkillBooking(
        skill_item_id=skill_item.id,
        seller_id=seller.id,
        buyer_id=buyer.id,
        amount=payload.amount,
        scheduled_at=payload.scheduled_at,
        status="pending",
    )
    db.add(booking)
    # 수락/거절 전까지 다른 구매자에게 중복 요청하지 못하게 잡아둔다.
    skill_item.status = "awarded"
    notification_service.notify(
        db, buyer.id, "booking",
        f"'{skill_item.title}' 스킬 예약 요청이 도착했습니다. "
        f"수락하면 {payload.amount} 포인트가 에스크로에 보관됩니다.",
        "skill_item", skill_item.id,
    )
    db.commit()
    db.refresh(booking)
    return booking


def accept_booking(db: Session, booking_id: int, user: User) -> SkillBooking:
    """구매자가 예약 요청을 수락하면 포인트를 차감해 에스크로에 보관한다 (FR-SKL-03)."""
    booking = _lock_booking(db, booking_id, user)
    if user.id != booking.buyer_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "구매자만 수락할 수 있습니다.")
    if booking.status != "pending":
        raise HTTPException(status.HTTP_409_CONFLICT, "수락 대기중인 예약이 아닙니다.")

    # 동시에 여러 번 결제 요청이 오면 잔액을 초과해 차감할 수 있으므로 잠그고 다시 읽는다.
    buyer = get_or_404(db, User, user.id, "사용자를 찾을 수 없습니다.", for_update=True)
    if buyer.points < booking.amount:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "보유 포인트가 부족합니다.")

    _move_points(
        db, buyer, -booking.amount, "spend", f"스킬 낙찰 보관 #{booking.skill_item_id}"
    )
    db.add(
        Escrow(
            booking_id=booking.id,
            payer_id=buyer.id,
            payee_id=booking.seller_id,
            amount=booking.amount,
            status="holding",
        )
    )
    booking.status = "in_progress"
    notification_service.notify(
        db, booking.seller_id, "booking",
        "구매자가 스킬 예약을 수락했습니다.",
        "skill_item", booking.skill_item_id,
    )
    db.commit()
    db.refresh(booking)
    return booking


def complete_booking(db: Session, booking_id: int, user: User) -> SkillBooking:
    """구매자가 서비스 완료를 확인하면 에스크로를 판매자에게 정산한다 (FR-SKL-03)."""
    booking = _lock_booking(db, booking_id, user)
    if user.id != booking.buyer_id and not user.is_admin:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, "구매자만 완료를 확인할 수 있습니다."
        )
    if booking.status != "in_progress":
        raise HTTPException(status.HTTP_409_CONFLICT, "진행중인 예약이 아닙니다.")

    escrow = _booking_escrow(db, booking.id)
    if escrow:
        _settle_escrow(db, escrow)
    booking.status = "completed"
    _set_skill_item_status(db, booking.skill_item_id, "closed")
    notification_service.notify(
        db, booking.seller_id, "settlement",
        f"스킬 거래가 완료되어 {booking.amount} 포인트가 정산되었습니다.",
        "skill_item", booking.skill_item_id,
    )
    db.commit()
    db.refresh(booking)
    return booking


def no_show_booking(
    db: Session, booking_id: int, user: User, party: str
) -> SkillBooking:
    """노쇼 처리 (FR-SKL-05). 신고는 거래 상대방에 대해서만 할 수 있다.

    - 판매자 노쇼(구매자가 신고): 구매자에게 전액 환불.
    - 구매자 노쇼(판매자가 신고): 판매자에게 정산 (노쇼한 구매자가 포인트를 잃는다).
    """
    booking = _lock_booking(db, booking_id, user)
    if booking.status != "in_progress":
        raise HTTPException(status.HTTP_409_CONFLICT, "진행중인 예약이 아닙니다.")
    # 스스로 노쇼했다고 신고해 환불받거나, 제3자가 대신 신고하지 못하게 한다.
    reporter = booking.buyer_id if party == "seller" else booking.seller_id
    if user.id != reporter and not user.is_admin:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, "노쇼는 거래 상대방만 신고할 수 있습니다."
        )

    escrow = _booking_escrow(db, booking.id)
    if escrow:
        if party == "seller":
            _refund_escrow(db, escrow)
        else:
            _settle_escrow(db, escrow)
    booking.status = "no_show"
    _set_skill_item_status(db, booking.skill_item_id, "closed")

    victim = booking.buyer_id if party == "seller" else booking.seller_id
    who = "판매자" if party == "seller" else "구매자"
    notification_service.notify(
        db, victim, "no_show",
        f"스킬 예약이 {who} 노쇼로 종료되었습니다.",
        "skill_item", booking.skill_item_id,
    )
    db.commit()
    db.refresh(booking)
    return booking


def _set_skill_item_status(db: Session, skill_item_id: int, new_status: str) -> None:
    item = db.get(SkillItem, skill_item_id)
    if item:
        item.status = new_status


def list_my_bookings(db: Session, user_id: int) -> list[SkillBooking]:
    return (
        db.query(SkillBooking)
        .filter(
            (SkillBooking.seller_id == user_id) | (SkillBooking.buyer_id == user_id)
        )
        .order_by(SkillBooking.created_at.desc())
        .all()
    )


def _party_filter(user: User, *cols):
    """관리자가 아니면 당사자 행만 보이게 한다. 남의 행은 403 대신 404 로 존재 여부를 숨긴다."""
    if user.is_admin:
        return ()
    return (or_(*(c == user.id for c in cols)),)


def get_booking(
    db: Session, booking_id: int, user: User, for_update: bool = False
) -> SkillBooking:
    return get_or_404(
        db, SkillBooking, booking_id, "예약을 찾을 수 없습니다.",
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
        raise HTTPException(status.HTTP_409_CONFLICT, "진행중인 예약만 변경할 수 있습니다.")
    data = payload.model_dump(exclude_unset=True)
    # 상태 전환(수락/정산/노쇼/취소)은 전용 엔드포인트로만 처리한다.
    if data.get("status") not in (None, booking.status):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "상태 변경은 accept / complete / no-show / DELETE 엔드포인트를 사용하세요.",
        )
    if payload.scheduled_at is not None:
        booking.scheduled_at = payload.scheduled_at
    db.commit()
    db.refresh(booking)
    return booking



def cancel_booking(db: Session, booking_id: int, user: User) -> None:
    """예약 취소(요청 거절 포함). 수락 전이면 상품을 다시 모집중으로, 수락 후면 환불하고 종료."""
    booking = _lock_booking(db, booking_id, user)
    if booking.status not in _OPEN_BOOKING:
        raise HTTPException(status.HTTP_409_CONFLICT, "이미 종료된 예약입니다.")
    if booking.status == "pending":
        _set_skill_item_status(db, booking.skill_item_id, "recruiting")
    else:
        escrow = _booking_escrow(db, booking.id)
        if escrow and escrow.status == "holding":
            _refund_escrow(db, escrow)
        _set_skill_item_status(db, booking.skill_item_id, "closed")
    booking.status = "cancelled"
    other = booking.seller_id if user.id == booking.buyer_id else booking.buyer_id
    notification_service.notify(
        db, other, "booking", "스킬 예약이 취소되었습니다.",
        "skill_item", booking.skill_item_id,
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
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, "상품 판매자에게만 에스크로 결제할 수 있습니다."
        )
    if payload.payee_id == payer.id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "본인에게 보낼 수 없습니다.")
    # 동시에 여러 번 결제 요청이 오면 잔액을 초과해 차감할 수 있으므로 잠그고 다시 읽는다.
    payer = get_or_404(db, User, payer.id, "사용자를 찾을 수 없습니다.", for_update=True)
    if payer.points < payload.amount:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "보유 포인트가 부족합니다.")

    # 결제자 포인트를 차감해 보관한다. 정산/환불 시 이동한다.
    _move_points(db, payer, -payload.amount, "spend", "에스크로 보관")
    escrow = Escrow(
        item_id=item.id,
        payer_id=payer.id,
        payee_id=payload.payee_id,
        amount=payload.amount,
        status="holding",
    )
    db.add(escrow)
    db.commit()
    db.refresh(escrow)
    return escrow


def get_escrow(
    db: Session, escrow_id: int, user: User, for_update: bool = False
) -> Escrow:
    return get_or_404(
        db, Escrow, escrow_id, "에스크로를 찾을 수 없습니다.",
        *_party_filter(user, Escrow.payer_id, Escrow.payee_id),
        for_update=for_update,
    )


def update_escrow_status(
    db: Session, escrow_id: int, user: User, payload: EscrowUpdate
) -> Escrow:
    escrow = get_escrow(db, escrow_id, user, for_update=True)
    if escrow.booking_id is not None:
        raise HTTPException(
            status.HTTP_409_CONFLICT, "스킬 예약 에스크로는 예약에서 처리해야 합니다."
        )
    # 받는 쪽이 스스로 정산하거나 낸 쪽이 일방적으로 환불받지 못하게 한다:
    # 정산(판매자에게 지급)은 결제자가 확정하고, 환불은 수취인이 승인한다.
    if payload.status == "settled":
        if user.id != escrow.payer_id and not user.is_admin:
            raise HTTPException(
                status.HTTP_403_FORBIDDEN, "결제자만 정산을 확정할 수 있습니다."
            )
        _settle_escrow(db, escrow)
    else:  # refunded
        if user.id != escrow.payee_id and not user.is_admin:
            raise HTTPException(
                status.HTTP_403_FORBIDDEN, "수취인만 환불을 승인할 수 있습니다."
            )
        _refund_escrow(db, escrow)
    db.commit()
    db.refresh(escrow)
    return escrow
