from sqlalchemy import (
    Boolean,
    Column,
    Integer,
    String,
    DateTime,
    ForeignKey,
    UniqueConstraint,
    func,
)
from app.database import Base


class Attendance(Base):
    """출석 체크 기록 (FR-PRD-05). 사용자당 하루 1건."""

    __tablename__ = "attendances"
    __table_args__ = (UniqueConstraint("user_id", "check_date", name="uq_attendance_day"),)

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    check_date = Column(String(10), nullable=False)  # YYYY-MM-DD (UTC)
    streak = Column(Integer, nullable=False, default=1)
    reward = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class MissionClaim(Base):
    """미션 보상 수령 기록 (FR-PRD-06). 사용자당 미션별 1건."""

    __tablename__ = "mission_claims"
    __table_args__ = (
        UniqueConstraint("user_id", "mission_key", name="uq_mission_claim"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    mission_key = Column(String(40), nullable=False)
    reward = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Coupon(Base):
    """포인트로 교환한 수수료 할인 쿠폰 (FR-PRD-08)."""

    __tablename__ = "coupons"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    catalog_key = Column(String(40), nullable=False)
    discount_percent = Column(Integer, nullable=False)
    cost = Column(Integer, nullable=False)
    is_used = Column(Boolean, nullable=False, default=False, index=True)
    used_at = Column(DateTime(timezone=True), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
