from datetime import datetime
from typing import Optional, Literal

from pydantic import BaseModel, Field

from app.schemas.common import ORMModel


# ----- Prediction -----
class PredictionCreate(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    description: Optional[str] = None
    end_time: datetime
    yes_odds: float = Field(default=2.0, gt=1.0)
    no_odds: float = Field(default=2.0, gt=1.0)


class PredictionUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=300)
    description: Optional[str] = None
    end_time: Optional[datetime] = None
    yes_odds: Optional[float] = Field(default=None, gt=1.0)
    no_odds: Optional[float] = Field(default=None, gt=1.0)
    status: Optional[Literal["ongoing", "closed", "settled"]] = None
    result: Optional[Literal["yes", "no"]] = None


class PredictionResponse(ORMModel):
    id: int
    title: str
    description: Optional[str] = None
    end_time: datetime
    status: str
    yes_odds: float
    no_odds: float
    result: Optional[str] = None
    created_by: int
    created_at: datetime


# ----- PredictionBet -----
class PredictionBetCreate(BaseModel):
    position: Literal["yes", "no"]
    amount: int = Field(gt=0)


class PredictionBetResponse(ORMModel):
    id: int
    prediction_id: int
    user_id: int
    position: str
    amount: int
    result: str
    payout: int = 0
    is_cancelled: bool
    created_at: datetime


# ----- 파리뮤추얼 배당 / 정산 -----
class PredictionOddsResponse(BaseModel):
    prediction_id: int
    yes_pool: int
    no_pool: int
    total_pool: int
    yes_backers: int
    no_backers: int
    # 배당 배수(원금 포함). 해당 포지션 풀이 비어 있으면 null.
    yes_odds: Optional[float] = None
    no_odds: Optional[float] = None


class PredictionSettleRequest(BaseModel):
    result: Literal["yes", "no"]


class PredictionSettleResponse(BaseModel):
    prediction_id: int
    result: str
    total_pool: int
    winning_pool: int
    winners: int
    losers: int
    total_payout: int
    refunded: bool
