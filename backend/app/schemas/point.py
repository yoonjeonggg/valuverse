from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator

from app.core.config import settings
from app.schemas.common import ORMModel


# 관리자 수동 조정에 쓸 수 있는 유형. attendance/mission/ad 같은 적립 유형을 위조하면
# 광고 일일 한도 집계와 감사 이력이 오염되므로 허용하지 않는다.
AdminTxType = Literal["admin", "refund", "etc"]


class PointTransactionCreate(BaseModel):
    # 대상 유저. 생략 시 요청자 본인.
    user_id: Optional[int] = None
    amount: int = Field(
        ge=-settings.point_admin_adjust_max,
        le=settings.point_admin_adjust_max,
        description="양수=적립, 음수=차감 (0 불가)",
    )
    type: AdminTxType = "admin"
    # 감사 추적을 위해 조정 사유는 필수.
    memo: str = Field(min_length=1, max_length=200)

    @field_validator("amount")
    @classmethod
    def _non_zero(cls, v: int) -> int:
        if v == 0:
            raise ValueError("0 포인트는 조정할 수 없습니다.")
        return v


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
    # 내일 이어서 출석할 때 받을 보상 (화면이 요약을 다시 불러오지 않아도 되도록)
    next_check_in_reward: int


class CheckInStatusResponse(BaseModel):
    checked_in_today: bool
    streak: int


class PointsSummaryResponse(BaseModel):
    balance: int
    checked_in_today: bool
    streak: int
    streak_cap: int
    next_check_in_reward: int
    ad_views_today: int
    ad_daily_limit: int
    ad_reward: int
    ad_next_available_at: Optional[datetime] = None


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
    next_available_at: datetime


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
