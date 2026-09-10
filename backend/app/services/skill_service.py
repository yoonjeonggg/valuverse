from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.point import PointTransaction
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


def _move_points(db: Session, user: User, amount: int, tx_type: str, memo: str) -> None:
    user.points += amount
    db.add(
        PointTransaction(
            user_id=user.id,
            amount=amount,
            type=tx_type,
            memo=memo,
            balance_after=user.points,
        )
    )


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
    item = (
        db.query(SkillItem)
        .filter(SkillItem.id == item_id, SkillItem.is_deleted.is_(False))
        .first()
    )
    if not item:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "스킬 상품을 찾을 수 없습니다.")
    return item


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

    buyer = db.get(User, payload.buyer_id)
    if not buyer:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "구매자를 찾을 수 없습니다.")
    if buyer.points < payload.amount:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, "구매자의 보유 포인트가 부족합니다."
        )

    booking = SkillBooking(
        skill_item_id=payload.skill_item_id,
        seller_id=seller.id,
        buyer_id=buyer.id,
        amount=payload.amount,
        scheduled_at=payload.scheduled_at,
        status="in_progress",
    )
    db.add(booking)
    db.flush()  # booking.id 확보

    # 낙찰가를 구매자 포인트에서 차감해 에스크로에 보관한다 (FR-SKL-03)
    _move_points(
        db, buyer, -payload.amount, "spend", f"스킬 낙찰 보관 #{skill_item.id}"
    )
    db.add(
        Escrow(
            booking_id=booking.id,
            payer_id=buyer.id,
            payee_id=seller.id,
            amount=payload.amount,
            status="holding",
        )
    )
    skill_item.status = "awarded"
    notification_service.notify(
        db, buyer.id, "booking",
        f"'{skill_item.title}' 스킬 예약이 확정되었습니다.",
        "skill_item", skill_item.id,
    )
    db.commit()
    db.refresh(booking)
    return booking


def complete_booking(db: Session, booking_id: int, user: User) -> SkillBooking:
    """구매자가 서비스 완료를 확인하면 에스크로를 판매자에게 정산한다 (FR-SKL-03)."""
    booking = get_booking(db, booking_id, user.id)
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
    _close_skill_item(db, booking.skill_item_id)
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
    """노쇼 처리 (FR-SKL-05).

    - 판매자 노쇼: 구매자에게 전액 환불.
    - 구매자 노쇼: 판매자에게 정산 (노쇼한 구매자가 포인트를 잃는다).
    """
    booking = get_booking(db, booking_id, user.id)
    if booking.status != "in_progress":
        raise HTTPException(status.HTTP_409_CONFLICT, "진행중인 예약이 아닙니다.")

    escrow = _booking_escrow(db, booking.id)
    if escrow:
        if party == "seller":
            _refund_escrow(db, escrow)
        else:
            _settle_escrow(db, escrow)
    booking.status = "no_show"
    _close_skill_item(db, booking.skill_item_id)

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


def _close_skill_item(db: Session, skill_item_id: int) -> None:
    item = db.get(SkillItem, skill_item_id)
    if item:
        item.status = "closed"


def list_my_bookings(db: Session, user_id: int) -> list[SkillBooking]:
    return (
        db.query(SkillBooking)
        .filter(
            (SkillBooking.seller_id == user_id) | (SkillBooking.buyer_id == user_id)
        )
        .order_by(SkillBooking.created_at.desc())
        .all()
    )


def get_booking(db: Session, booking_id: int, user_id: int) -> SkillBooking:
    booking = db.query(SkillBooking).filter(SkillBooking.id == booking_id).first()
    if not booking:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "예약을 찾을 수 없습니다.")
    if user_id not in (booking.seller_id, booking.buyer_id):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "조회 권한이 없습니다.")
    return booking


def update_booking(
    db: Session, booking_id: int, user_id: int, payload: SkillBookingUpdate
) -> SkillBooking:
    booking = get_booking(db, booking_id, user_id)
    if booking.status != "in_progress":
        raise HTTPException(status.HTTP_409_CONFLICT, "진행중인 예약만 변경할 수 있습니다.")
    data = payload.model_dump(exclude_unset=True)
    # 상태 전환(정산/노쇼/취소)은 전용 엔드포인트로만 처리한다.
    if data.get("status") not in (None, "in_progress"):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "상태 변경은 complete / no-show / DELETE 엔드포인트를 사용하세요.",
        )
    if payload.scheduled_at is not None:
        booking.scheduled_at = payload.scheduled_at
    db.commit()
    db.refresh(booking)
    return booking


def cancel_booking(db: Session, booking_id: int, user_id: int) -> None:
    booking = get_booking(db, booking_id, user_id)
    if booking.status in ("completed", "no_show"):
        raise HTTPException(status.HTTP_409_CONFLICT, "이미 종료된 예약입니다.")
    escrow = _booking_escrow(db, booking.id)
    if escrow and escrow.status == "holding":
        _refund_escrow(db, escrow)
    booking.status = "cancelled"
    _close_skill_item(db, booking.skill_item_id)
    db.commit()


# ==================== Escrow ====================
def create_escrow(db: Session, payer: User, payload: EscrowCreate) -> Escrow:
    if not payload.booking_id and not payload.item_id:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, "booking_id 또는 item_id 가 필요합니다."
        )
    if payload.payee_id == payer.id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "본인에게 보낼 수 없습니다.")
    if not db.get(User, payload.payee_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "수취인을 찾을 수 없습니다.")
    if payer.points < payload.amount:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "보유 포인트가 부족합니다.")

    # 결제자 포인트를 차감해 보관한다. 정산/환불 시 이동한다.
    _move_points(db, payer, -payload.amount, "spend", "에스크로 보관")
    escrow = Escrow(
        booking_id=payload.booking_id,
        item_id=payload.item_id,
        payer_id=payer.id,
        payee_id=payload.payee_id,
        amount=payload.amount,
        status="holding",
    )
    db.add(escrow)
    db.commit()
    db.refresh(escrow)
    return escrow


def get_escrow(db: Session, escrow_id: int, user: User) -> Escrow:
    escrow = db.query(Escrow).filter(Escrow.id == escrow_id).first()
    if not escrow:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "에스크로를 찾을 수 없습니다.")
    if not user.is_admin and user.id not in (escrow.payer_id, escrow.payee_id):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "조회 권한이 없습니다.")
    return escrow


def update_escrow_status(
    db: Session, escrow_id: int, user: User, payload: EscrowUpdate
) -> Escrow:
    escrow = get_escrow(db, escrow_id, user)
    if payload.status == "holding":
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "holding 으로 되돌릴 수 없습니다.")
    if payload.status == "settled":
        _settle_escrow(db, escrow)
    else:  # refunded
        _refund_escrow(db, escrow)
    db.commit()
    db.refresh(escrow)
    return escrow
