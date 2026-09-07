from fastapi import HTTPException, status
from sqlalchemy.orm import Session

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
    if not db.query(User.id).filter(User.id == payload.buyer_id).first():
        raise HTTPException(status.HTTP_404_NOT_FOUND, "구매자를 찾을 수 없습니다.")

    booking = SkillBooking(
        skill_item_id=payload.skill_item_id,
        seller_id=seller.id,
        buyer_id=payload.buyer_id,
        scheduled_at=payload.scheduled_at,
        status="in_progress",
    )
    skill_item.status = "awarded"
    db.add(booking)
    db.commit()
    db.refresh(booking)
    return booking


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
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(booking, field, value)
    db.commit()
    db.refresh(booking)
    return booking


def cancel_booking(db: Session, booking_id: int, user_id: int) -> None:
    booking = get_booking(db, booking_id, user_id)
    if booking.status in ("completed", "no_show"):
        raise HTTPException(status.HTTP_409_CONFLICT, "이미 종료된 예약입니다.")
    booking.status = "cancelled"
    db.commit()


# ==================== Escrow ====================
def create_escrow(db: Session, payer: User, payload: EscrowCreate) -> Escrow:
    if not payload.booking_id and not payload.item_id:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, "booking_id 또는 item_id 가 필요합니다."
        )
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
    if escrow.status != "holding":
        raise HTTPException(
            status.HTTP_409_CONFLICT, "보관중 상태에서만 변경할 수 있습니다."
        )
    escrow.status = payload.status
    db.commit()
    db.refresh(escrow)
    return escrow
