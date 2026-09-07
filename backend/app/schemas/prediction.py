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
    is_cancelled: bool
    created_at: datetime
