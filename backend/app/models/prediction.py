from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    Boolean,
    Float,
    DateTime,
    ForeignKey,
    func,
)
from app.database import Base


class Prediction(Base):
    """예측시장 명제 (관리자 등록)."""

    __tablename__ = "predictions"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(300), nullable=False)
    description = Column(Text, nullable=True)
    end_time = Column(DateTime(timezone=True), nullable=False)
    # ongoing | closed | settled
    status = Column(String(20), nullable=False, default="ongoing", index=True)
    yes_odds = Column(Float, nullable=False, default=2.0)
    no_odds = Column(Float, nullable=False, default=2.0)
    # 정산 시 확정된 결과: yes | no | null
    result = Column(String(10), nullable=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class PredictionBet(Base):
    """예측시장 베팅."""

    __tablename__ = "prediction_bets"

    id = Column(Integer, primary_key=True, index=True)
    prediction_id = Column(Integer, ForeignKey("predictions.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    position = Column(String(10), nullable=False)  # yes | no
    amount = Column(Integer, nullable=False)  # 차감된 포인트
    # pending | won | lost | refunded
    result = Column(String(10), nullable=False, default="pending")
    is_cancelled = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
