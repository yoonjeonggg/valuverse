from datetime import datetime
from typing import Optional, Literal

from pydantic import BaseModel, Field

from app.schemas.common import ORMModel


class ReportCreate(BaseModel):
    target_type: Literal["user", "item", "skill_item", "review"]
    target_id: int
    reason: str = Field(min_length=1, max_length=2000)


class ReportUpdate(BaseModel):
    status: Literal["pending", "in_progress", "resolved", "rejected"]
    admin_memo: Optional[str] = Field(default=None, max_length=2000)


class ReportResponse(ORMModel):
    id: int
    reporter_id: int
    target_type: str
    target_id: int
    reason: str
    status: str
    admin_memo: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
