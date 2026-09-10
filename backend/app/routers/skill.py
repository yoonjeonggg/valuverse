from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.skill import (
    SkillItemCreate,
    SkillItemUpdate,
    SkillItemResponse,
    SkillBookingCreate,
    SkillBookingUpdate,
    SkillBookingNoShow,
    SkillBookingResponse,
    EscrowCreate,
    EscrowUpdate,
    EscrowResponse,
)
from app.services import skill_service

skill_item_router = APIRouter(prefix="/skill-items", tags=["Skill Item"])
booking_router = APIRouter(prefix="/skill-bookings", tags=["Skill Booking"])
escrow_router = APIRouter(prefix="/escrows", tags=["Escrow"])


# ==================== SkillItem ====================
@skill_item_router.post(
    "", response_model=SkillItemResponse, status_code=status.HTTP_201_CREATED
)
def create_skill_item(
    payload: SkillItemCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return skill_service.create_skill_item(db, user.id, payload)


@skill_item_router.get("", response_model=list[SkillItemResponse])
def list_skill_items(
    category: str | None = None,
    status_filter: str | None = Query(default=None, alias="status"),
    skip: int = 0,
    limit: int = Query(default=50, le=200),
    db: Session = Depends(get_db),
):
    return skill_service.list_skill_items(db, category, status_filter, skip, limit)


@skill_item_router.get("/{item_id}", response_model=SkillItemResponse)
def get_skill_item(item_id: int, db: Session = Depends(get_db)):
    return skill_service.get_skill_item(db, item_id)


@skill_item_router.patch("/{item_id}", response_model=SkillItemResponse)
def update_skill_item(
    item_id: int,
    payload: SkillItemUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return skill_service.update_skill_item(db, item_id, user.id, payload)


@skill_item_router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_skill_item(
    item_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    skill_service.delete_skill_item(db, item_id, user.id)


# ==================== SkillBooking ====================
@booking_router.post(
    "", response_model=SkillBookingResponse, status_code=status.HTTP_201_CREATED
)
def create_booking(
    payload: SkillBookingCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return skill_service.create_booking(db, user, payload)


@booking_router.get("", response_model=list[SkillBookingResponse])
def list_my_bookings(
    db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    return skill_service.list_my_bookings(db, user.id)


@booking_router.get("/{booking_id}", response_model=SkillBookingResponse)
def get_booking(
    booking_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return skill_service.get_booking(db, booking_id, user.id)


@booking_router.patch("/{booking_id}", response_model=SkillBookingResponse)
def update_booking(
    booking_id: int,
    payload: SkillBookingUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return skill_service.update_booking(db, booking_id, user.id, payload)


@booking_router.post("/{booking_id}/complete", response_model=SkillBookingResponse)
def complete_booking(
    booking_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return skill_service.complete_booking(db, booking_id, user)


@booking_router.post("/{booking_id}/no-show", response_model=SkillBookingResponse)
def no_show_booking(
    booking_id: int,
    payload: SkillBookingNoShow,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return skill_service.no_show_booking(db, booking_id, user, payload.party)


@booking_router.delete("/{booking_id}", status_code=status.HTTP_204_NO_CONTENT)
def cancel_booking(
    booking_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    skill_service.cancel_booking(db, booking_id, user.id)


# ==================== Escrow ====================
@escrow_router.post(
    "", response_model=EscrowResponse, status_code=status.HTTP_201_CREATED
)
def create_escrow(
    payload: EscrowCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return skill_service.create_escrow(db, user, payload)


@escrow_router.get("/{escrow_id}", response_model=EscrowResponse)
def get_escrow(
    escrow_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return skill_service.get_escrow(db, escrow_id, user)


@escrow_router.patch("/{escrow_id}", response_model=EscrowResponse)
def update_escrow(
    escrow_id: int,
    payload: EscrowUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return skill_service.update_escrow_status(db, escrow_id, user, payload)
