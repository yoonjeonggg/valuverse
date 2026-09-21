"""마이페이지 통합 요약 (FR-COM-02)."""

from sqlalchemy import and_, case, func, or_
from sqlalchemy.orm import Session

from app.models.auction import Bid, Item
from app.models.notification import Notification
from app.models.prediction import PredictionBet
from app.models.report import Report
from app.models.review import Review
from app.models.skill import SkillBooking, SkillItem
from app.models.user import User
from app.services.economy_service import get_active_attendance_streak


def _count(db: Session, model, *conditions) -> int:
    return (
        db.query(func.count(model.id)).filter(*conditions).scalar() or 0
    )


def _counts_by_group(db: Session, model, group_col, *conditions) -> dict:
    """group_col 값별 개수. 매칭되는 행이 없으면 그 값은 결과에서 빠진다."""
    rows = (
        db.query(group_col, func.count(model.id))
        .filter(*conditions)
        .group_by(group_col)
        .all()
    )
    return dict(rows)


def get_dashboard(db: Session, user: User) -> dict:
    uid = user.id

    # 내 입찰이 걸린 진행중 경매 (상품 기준 distinct)
    active_bid_items = (
        db.query(func.count(func.distinct(Bid.item_id)))
        .join(Item, Item.id == Bid.item_id)
        .filter(
            Bid.bidder_id == uid,
            Bid.is_cancelled.is_(False),
            Item.status == "ongoing",
        )
        .scalar()
        or 0
    )

    # 판매/낙찰 3건을 한 번에: 상품이 내 판매글이거나 내가 낙찰자인 경우만 스캔.
    selling_ongoing, sold, won = (
        db.query(
            func.sum(
                case(
                    (
                        and_(
                            Item.seller_id == uid,
                            Item.status == "ongoing",
                            Item.is_deleted.is_(False),
                        ),
                        1,
                    ),
                    else_=0,
                )
            ),
            func.sum(
                case(
                    (
                        and_(
                            Item.seller_id == uid,
                            Item.status == "closed",
                            Item.winner_id.isnot(None),
                        ),
                        1,
                    ),
                    else_=0,
                )
            ),
            func.sum(case((Item.winner_id == uid, 1), else_=0)),
        )
        .filter(or_(Item.seller_id == uid, Item.winner_id == uid))
        .first()
    )

    # 예약 상태별 건수를 한 번에 (구매자/판매자 어느 쪽이든 매칭).
    booking_counts = _counts_by_group(
        db,
        SkillBooking,
        SkillBooking.status,
        or_(SkillBooking.buyer_id == uid, SkillBooking.seller_id == uid),
        SkillBooking.status.in_(("in_progress", "completed")),
    )

    # 예측 배팅 결과별 건수를 한 번에.
    bet_counts = _counts_by_group(
        db, PredictionBet, PredictionBet.result, PredictionBet.user_id == uid
    )

    return {
        "user_id": uid,
        "points": user.points,
        "rating": user.rating,
        "unread_notifications": _count(
            db, Notification, Notification.user_id == uid, Notification.is_read.is_(False)
        ),
        "attendance_streak": get_active_attendance_streak(db, uid),
        "auction": {
            "selling_ongoing": selling_ongoing or 0,
            "sold": sold or 0,
            "won": won or 0,
            "active_bids": active_bid_items,
        },
        "skill": {
            "selling": _count(
                db, SkillItem,
                SkillItem.seller_id == uid,
                SkillItem.is_deleted.is_(False),
            ),
            "bookings_in_progress": booking_counts.get("in_progress", 0),
            "bookings_completed": booking_counts.get("completed", 0),
        },
        "prediction_bets": {
            r: bet_counts.get(r, 0) for r in ("pending", "won", "lost")
        },
        "reviews_written": _count(
            db, Review, Review.author_id == uid, Review.is_deleted.is_(False)
        ),
        "reports_open": _count(
            db, Report,
            Report.reporter_id == uid,
            Report.status.in_(("pending", "in_progress")),
        ),
    }
