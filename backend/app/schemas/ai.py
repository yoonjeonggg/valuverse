from typing import Literal

from pydantic import BaseModel, Field


class PriceSuggestionResponse(BaseModel):
    category: str
    auction_type: str | None = None
    sample_size: int
    enough_data: bool
    avg_final_price: int | None = None
    median_final_price: int | None = None
    min_final_price: int | None = None
    max_final_price: int | None = None
    suggested_start_price: int | None = None
    suggested_buy_now_price: int | None = None


class AbuseCheckRequest(BaseModel):
    text: str = Field(min_length=1, max_length=5000)


class AbuseCheckResponse(BaseModel):
    flagged: bool
    score: int
    matched_terms: list[str]
    categories: list[str]


class DescriptionSuggestionRequest(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    category: str | None = None
    keywords: list[str] = Field(default_factory=list)
    existing_description: str | None = Field(default=None, max_length=5000)


class DescriptionSuggestionResponse(BaseModel):
    draft_description: str
    suggestions: list[str]
    market_context: PriceSuggestionResponse | None = None


class SkillTagRequest(BaseModel):
    intro_text: str = Field(min_length=1, max_length=5000)


class SkillTagResponse(BaseModel):
    suggested_category: str
    suggested_level: str
    category_scores: dict[str, int]


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=1000)
    item_id: int | None = None
    item_type: Literal["item", "skill_item"] = "item"


class ChatResponse(BaseModel):
    answer: str
    references: list[str]
    item_id: int | None = None
