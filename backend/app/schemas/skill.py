from datetime import datetime
from typing import Optional, Literal

from pydantic import BaseModel, Field

from app.schemas.common import ORMModel


# ----- SkillItem -----
class SkillItemCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: Optional[str] = None
    category: Optional[str] = Field(default=None, max_length=50)
    image_url: Optional[str] = Field(default=None, max_length=500)
    start_price: int = Field(ge=0)
    duration_minutes: Optional[int] = Field(default=None, ge=0)
    provide_type: Optional[str] = Field(default=None, max_length=50)
    available_schedule: Optional[str] = None
    end_time: Optional[datetime] = None


class SkillItemUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=200)
    description: Optional[str] = None
    category: Optional[str] = Field(default=None, max_length=50)
    image_url: Optional[str] = Field(default=None, max_length=500)
    duration_minutes: Optional[int] = Field(default=None, ge=0)
    provide_type: Optional[str] = Field(default=None, max_length=50)
    available_schedule: Optional[str] = None
    end_time: Optional[datetime] = None


class SkillItemResponse(ORMModel):
    id: int
    seller_id: int
    title: str
    description: Optional[str] = None
    category: Optional[str] = None
    image_url: Optional[str] = None
    start_price: int
    duration_minutes: Optional[int] = None
    provide_type: Optional[str] = None
    available_schedule: Optional[str] = None
    end_time: Optional[datetime] = None
    status: str
    created_at: datetime


# ----- SkillBooking -----
class SkillBookingCreate(BaseModel):
    skill_item_id: int
    buyer_id: int
    scheduled_at: datetime


class SkillBookingUpdate(BaseModel):
    scheduled_at: Optional[datetime] = None
    status: Optional[Literal["in_progress", "completed", "no_show", "cancelled"]] = None


class SkillBookingResponse(ORMModel):
    id: int
    skill_item_id: int
    seller_id: int
    buyer_id: int
    scheduled_at: datetime
    status: str
    created_at: datetime


# ----- Escrow -----
class EscrowCreate(BaseModel):
    booking_id: Optional[int] = None
    item_id: Optional[int] = None
    payee_id: int
    amount: int = Field(gt=0)


class EscrowUpdate(BaseModel):
    status: Literal["holding", "settled", "refunded"]


class EscrowResponse(ORMModel):
    id: int
    booking_id: Optional[int] = None
    item_id: Optional[int] = None
    payer_id: int
    payee_id: int
    amount: int
    status: str
    created_at: datetime
    updated_at: Optional[datetime] = None
