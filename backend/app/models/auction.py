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


class Item(Base):
    """일반 경매 상품."""

    __tablename__ = "items"

    id = Column(Integer, primary_key=True, index=True)
    seller_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    category = Column(String(50), nullable=True, index=True)
    image_url = Column(String(500), nullable=True)
    start_price = Column(Integer, nullable=False)
    buy_now_price = Column(Integer, nullable=True)
    current_price = Column(Integer, nullable=False, default=0)
    # general(공개 실시간) | blind(밀봉)
    auction_type = Column(
        String(10), nullable=False, default="general", server_default="general", index=True
    )
    # 블라인드 낙찰 규칙: first(1st-price) | second(Vickrey 2nd-price)
    blind_price_rule = Column(
        String(10), nullable=False, default="first", server_default="first"
    )
    end_time = Column(DateTime(timezone=True), nullable=False)
    # ongoing | closed
    status = Column(String(20), nullable=False, default="ongoing", index=True)
    is_deleted = Column(Boolean, nullable=False, default=False)
    # 낙찰 확정 결과 (마감/즉시구매 시 채워짐). 유찰이면 winner_id 는 NULL 로 남는다.
    winner_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    final_price = Column(Integer, nullable=True)
    # 마감 임박 입찰로 자동 연장된 횟수 (스나이핑 방지)
    extended_count = Column(Integer, nullable=False, default=0)
    # 상단 노출권 만료 시각. 이 시각 이전이면 목록 상단에 노출된다 (FR-PRD-08).
    spotlight_until = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Bid(Base):
    """일반 경매 입찰."""

    __tablename__ = "bids"

    id = Column(Integer, primary_key=True, index=True)
    item_id = Column(Integer, ForeignKey("items.id"), nullable=False, index=True)
    bidder_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    amount = Column(Integer, nullable=False)
    is_cancelled = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class BlindBid(Base):
    """블라인드(비공개) 경매 입찰. 금액은 마감 전까지 노출하지 않는다."""

    __tablename__ = "blind_bids"

    id = Column(Integer, primary_key=True, index=True)
    item_id = Column(Integer, ForeignKey("items.id"), nullable=False, index=True)
    bidder_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    # 순위 계산에만 사용, 마감 전 직렬화 금지
    amount = Column(Integer, nullable=False)
    is_cancelled = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
