from datetime import datetime

from pydantic import BaseModel

from app.schemas.common import ORMModel


class NotificationResponse(ORMModel):
    id: int
    user_id: int
    type: str
    message: str
    related_type: str | None = None
    related_id: int | None = None
    is_read: bool
    created_at: datetime


class UnreadCountResponse(BaseModel):
    unread: int
