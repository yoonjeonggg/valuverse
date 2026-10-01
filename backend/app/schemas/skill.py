from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.common import ORMModel


# ----- SkillItem -----
class SkillItemCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str | None = None
    category: str | None = Field(default=None, max_length=50)
    image_url: str | None = Field(default=None, max_length=500)
    start_price: int = Field(ge=0)
    duration_minutes: int | None = Field(default=None, ge=0)
    provide_type: str | None = Field(default=None, max_length=50)
    available_schedule: str | None = None
    end_time: datetime | None = None


class SkillItemUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    category: str | None = Field(default=None, max_length=50)
    image_url: str | None = Field(default=None, max_length=500)
    duration_minutes: int | None = Field(default=None, ge=0)
    provide_type: str | None = Field(default=None, max_length=50)
    available_schedule: str | None = None
    end_time: datetime | None = None


class SkillItemResponse(ORMModel):
    id: int
    seller_id: int
    title: str
    description: str | None = None
    category: str | None = None
    image_url: str | None = None
    start_price: int
    duration_minutes: int | None = None
    provide_type: str | None = None
    available_schedule: str | None = None
    end_time: datetime | None = None
    status: str
    created_at: datetime


# ----- SkillBooking -----
class SkillBookingCreate(BaseModel):
    skill_item_id: int
    buyer_id: int
    amount: int = Field(gt=0)
    scheduled_at: datetime


class SkillBookingUpdate(BaseModel):
    scheduled_at: datetime | None = None
    status: Literal["pending", "in_progress", "completed", "no_show", "cancelled"] | None = None


class SkillBookingNoShow(BaseModel):
    party: Literal["seller", "buyer"]


class SkillBookingResponse(ORMModel):
    id: int
    skill_item_id: int
    seller_id: int
    buyer_id: int
    amount: int
    scheduled_at: datetime
    status: str
    created_at: datetime


# ----- Escrow -----
class EscrowCreate(BaseModel):
    # 스킬 예약 에스크로는 예약 수락 시 자동 생성되므로, 직접 결제는 일반 경매 상품만 대상.
    item_id: int
    payee_id: int
    amount: int = Field(gt=0)


class EscrowUpdate(BaseModel):
    status: Literal["settled", "refunded"]


class EscrowResponse(ORMModel):
    id: int
    booking_id: int | None = None
    item_id: int | None = None
    payer_id: int
    payee_id: int
    amount: int
    status: str
    created_at: datetime
    updated_at: datetime | None = None
