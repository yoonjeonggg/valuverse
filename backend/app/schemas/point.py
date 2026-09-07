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
