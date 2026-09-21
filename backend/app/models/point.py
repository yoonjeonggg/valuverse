from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Index, func
from app.database import Base


class PointTransaction(Base):
    """포인트 적립/차감 이력. 수정/삭제 대상이 아니다 (정정은 신규 트랜잭션)."""

    __tablename__ = "point_transactions"
    __table_args__ = (
        # 광고 보상 일일 한도 조회(user_id + type + created_at 범위)에 사용.
        Index("ix_point_tx_user_type_created", "user_id", "type", "created_at"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    # 양수=적립, 음수=차감
    amount = Column(Integer, nullable=False)
    # attendance | mission | ad | bet | spend | refund | admin | etc
    type = Column(String(30), nullable=False, index=True)
    memo = Column(String(255), nullable=True)
    balance_after = Column(Integer, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
