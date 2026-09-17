from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.schemas.common import ORMModel


class PointTransactionCreate(BaseModel):
    # 대상 유저. 생략 시 요청자 본인.
    user_id: Optional[int] = None
    amount: int = Field(description="양수=적립, 음수=차감")
    type: str = Field(min_length=1, max_length=30)
    memo: Optional[str] = Field(default=None, max_length=255)


class PointTransactionResponse(ORMModel):
    id: int
    user_id: int
    amount: int
    type: str
    memo: Optional[str] = None
    balance_after: int
    created_at: datetime


class PointBalanceResponse(BaseModel):
    user_id: int
    balance: int


# ----- 포인트 이코노미 (적립/소모) -----
class CheckInResponse(BaseModel):
    check_date: str
    streak: int
    reward: int
    balance: int


class CheckInStatusResponse(BaseModel):
    checked_in_today: bool
    streak: int


class MissionStatus(BaseModel):
    key: str
    description: str
    reward: int
    achieved: bool
    claimed: bool


class MissionClaimResponse(BaseModel):
    key: str
    reward: int
    balance: int


class AdRewardResponse(BaseModel):
    reward: int
    views_today: int
    daily_limit: int
    balance: int


class SpotlightResponse(BaseModel):
    item_id: int
    spotlight_until: datetime
    cost: int
    balance: int


class CouponCatalogRow(BaseModel):
    key: str
    cost: int
    discount_percent: int
    description: str


class CouponResponse(ORMModel):
    id: int
    catalog_key: str
    discount_percent: int
    cost: int
    is_used: bool
    used_at: Optional[datetime] = None
    expires_at: datetime
    created_at: datetime
