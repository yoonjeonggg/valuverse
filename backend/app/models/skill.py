from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    Boolean,
    DateTime,
    ForeignKey,
    func,
)
from app.database import Base


class SkillItem(Base):
    """스킬(재능) 판매 상품."""

    __tablename__ = "skill_items"

    id = Column(Integer, primary_key=True, index=True)
    seller_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    category = Column(String(50), nullable=True, index=True)
    image_url = Column(String(500), nullable=True)
    start_price = Column(Integer, nullable=False)
    duration_minutes = Column(Integer, nullable=True)
    provide_type = Column(String(50), nullable=True)  # 온라인/오프라인/파일 등
    available_schedule = Column(Text, nullable=True)
    end_time = Column(DateTime(timezone=True), nullable=True)
    # recruiting | awarded | closed
    status = Column(String(20), nullable=False, default="recruiting", index=True)
    is_deleted = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class SkillBooking(Base):
    """스킬 낙찰 후 예약."""

    __tablename__ = "skill_bookings"

    id = Column(Integer, primary_key=True, index=True)
    skill_item_id = Column(Integer, ForeignKey("skill_items.id"), nullable=False, index=True)
    seller_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    buyer_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    # 낙찰가. 예약 생성 시 구매자 포인트에서 차감돼 에스크로에 보관된다.
    amount = Column(Integer, nullable=False, default=0)
    scheduled_at = Column(DateTime(timezone=True), nullable=False)
    # in_progress | completed | no_show | cancelled
    status = Column(String(20), nullable=False, default="in_progress", index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Escrow(Base):
    """에스크로. 이력 보존을 위해 삭제하지 않는다."""

    __tablename__ = "escrows"

    id = Column(Integer, primary_key=True, index=True)
    booking_id = Column(Integer, ForeignKey("skill_bookings.id"), nullable=True, index=True)
    item_id = Column(Integer, ForeignKey("items.id"), nullable=True, index=True)
    payer_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    payee_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    amount = Column(Integer, nullable=False)
    # holding | settled | refunded
    status = Column(String(20), nullable=False, default="holding", index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
