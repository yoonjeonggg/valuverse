from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, func
from app.database import Base


class Notification(Base):
    """사용자 알림 (FR-COM-03). 입찰 경쟁·낙찰·정산 등 이벤트 발생 시 생성된다."""

    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    # bid_outbid | won | sold | booking | settlement | no_show | bet_result
    type = Column(String(30), nullable=False, index=True)
    message = Column(String(255), nullable=False)
    related_type = Column(String(30), nullable=True)  # item | skill_item | prediction
    related_id = Column(Integer, nullable=True)
    is_read = Column(Boolean, nullable=False, default=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
