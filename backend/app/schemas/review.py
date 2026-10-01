from datetime import datetime

from pydantic import BaseModel, Field, model_validator

from app.schemas.common import ORMModel


class ReviewCreate(BaseModel):
    target_user_id: int
    item_id: int | None = None
    skill_item_id: int | None = None
    rating: int = Field(ge=1, le=5)
    content: str | None = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def _one_target(self):
        if bool(self.item_id) == bool(self.skill_item_id):
            raise ValueError("item_id 또는 skill_item_id 중 정확히 하나를 지정해야 합니다.")
        return self


class ReviewUpdate(BaseModel):
    rating: int | None = Field(default=None, ge=1, le=5)
    content: str | None = Field(default=None, max_length=2000)


class ReviewResponse(ORMModel):
    id: int
    author_id: int
    target_user_id: int
    item_id: int | None = None
    skill_item_id: int | None = None
    rating: int
    content: str | None = None
    created_at: datetime
    updated_at: datetime | None = None
