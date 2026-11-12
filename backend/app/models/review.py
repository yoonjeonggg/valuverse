from sqlalchemy import (
    Boolean,
    Column,
    ForeignKey,
    Integer,
    Text,
    func,
)

from app.core.db_types import UTCDateTime
from app.database import Base


class Review(Base):
    """거래(일반/스킬) 완료 후 리뷰."""

    __tablename__ = "reviews"

    id = Column(Integer, primary_key=True, index=True)
    author_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    target_user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    item_id = Column(Integer, ForeignKey("items.id"), nullable=True, index=True)
    skill_item_id = Column(Integer, ForeignKey("skill_items.id"), nullable=True, index=True)
    rating = Column(Integer, nullable=False)  # 1 ~ 5
    content = Column(Text, nullable=True)
    is_deleted = Column(Boolean, nullable=False, default=False)
    created_at = Column(UTCDateTime(), server_default=func.now())
    updated_at = Column(UTCDateTime(), onupdate=func.now())
