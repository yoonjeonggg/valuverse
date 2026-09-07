from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, func
from app.database import Base


class Report(Base):
    """신고. 이력 보존을 위해 삭제하지 않는다."""

    __tablename__ = "reports"

    id = Column(Integer, primary_key=True, index=True)
    reporter_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    target_type = Column(String(20), nullable=False)  # user | item | skill_item | review
    target_id = Column(Integer, nullable=False)
    reason = Column(Text, nullable=False)
    # pending | in_progress | resolved | rejected
    status = Column(String(20), nullable=False, default="pending", index=True)
    admin_memo = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
