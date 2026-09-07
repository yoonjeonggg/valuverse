from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, func
from app.database import Base


class PointTransaction(Base):
    """포인트 적립/차감 이력. 수정/삭제 대상이 아니다 (정정은 신규 트랜잭션)."""

    __tablename__ = "point_transactions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    # 양수=적립, 음수=차감
    amount = Column(Integer, nullable=False)
    # attendance | mission | ad | bet | spend | refund | admin | etc
    type = Column(String(30), nullable=False, index=True)
    memo = Column(String(255), nullable=True)
    balance_after = Column(Integer, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
