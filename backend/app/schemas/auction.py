from datetime import datetime
from typing import Optional, Literal

from pydantic import BaseModel, Field

from app.schemas.common import ORMModel


# ----- Item -----
class ItemCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: Optional[str] = None
    category: Optional[str] = Field(default=None, max_length=50)
    image_url: Optional[str] = Field(default=None, max_length=500)
    start_price: int = Field(ge=0)
    buy_now_price: Optional[int] = Field(default=None, ge=0)
    end_time: datetime


class ItemUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=200)
    description: Optional[str] = None
    category: Optional[str] = Field(default=None, max_length=50)
    image_url: Optional[str] = Field(default=None, max_length=500)
    buy_now_price: Optional[int] = Field(default=None, ge=0)
    end_time: Optional[datetime] = None


class ItemResponse(ORMModel):
    id: int
    seller_id: int
    title: str
    description: Optional[str] = None
    category: Optional[str] = None
    image_url: Optional[str] = None
    start_price: int
    buy_now_price: Optional[int] = None
    current_price: int
    end_time: datetime
    status: str
    winner_id: Optional[int] = None
    final_price: Optional[int] = None
    extended_count: int = 0
    created_at: datetime


# ----- Bid -----
class BidCreate(BaseModel):
    amount: int = Field(gt=0)


class BuyNowResponse(ORMModel):
    item_id: int
    buyer_id: int
    final_price: int
    status: str


class BidResponse(ORMModel):
    id: int
    item_id: int
    bidder_id: int
    amount: int
    is_cancelled: bool
    created_at: datetime


# ----- Blind Bid -----
class BlindBidCreate(BaseModel):
    amount: int = Field(gt=0)


class BlindBidRankResponse(BaseModel):
    item_id: int
    my_bid_id: int
    rank: int
    total_bids: int


class BlindBidResultRow(ORMModel):
    id: int
    bidder_id: int
    amount: int
    rank: int
