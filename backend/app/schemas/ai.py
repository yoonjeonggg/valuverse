from typing import Optional

from pydantic import BaseModel, Field


class PriceSuggestionResponse(BaseModel):
    category: str
    auction_type: Optional[str] = None
    sample_size: int
    enough_data: bool
    avg_final_price: Optional[int] = None
    median_final_price: Optional[int] = None
    min_final_price: Optional[int] = None
    max_final_price: Optional[int] = None
    suggested_start_price: Optional[int] = None
    suggested_buy_now_price: Optional[int] = None


class AbuseCheckRequest(BaseModel):
    text: str = Field(min_length=1, max_length=5000)


class AbuseCheckResponse(BaseModel):
    flagged: bool
    score: int
    matched_terms: list[str]
    categories: list[str]
