"""마이페이지 통합 요약 (FR-COM-02)."""

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.auction import Bid, Item
from app.models.economy import Attendance
from app.models.notification import Notification
from app.models.prediction import PredictionBet
from app.models.report import Report
from app.models.review import Review
from app.models.skill import SkillBooking, SkillItem
from app.models.user import User


def _count(db: Session, model, *conditions) -> int:
    return (
        db.query(func.count(model.id)).filter(*conditions).scalar() or 0
    )


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

    latest_attendance = (
        db.query(Attendance)
        .filter(Attendance.user_id == uid)
        .order_by(Attendance.check_date.desc())
        .first()
    )

    def bookings(field, status: str) -> int:
        return _count(db, SkillBooking, field == uid, SkillBooking.status == status)

    return {
        "user_id": uid,
        "points": user.points,
        "rating": user.rating,
        "unread_notifications": _count(
            db, Notification, Notification.user_id == uid, Notification.is_read.is_(False)
        ),
        "attendance_streak": latest_attendance.streak if latest_attendance else 0,
        "auction": {
            "selling_ongoing": _count(
                db, Item,
                Item.seller_id == uid,
                Item.status == "ongoing",
                Item.is_deleted.is_(False),
            ),
            "sold": _count(
                db, Item,
                Item.seller_id == uid,
                Item.status == "closed",
                Item.winner_id.isnot(None),
            ),
            "won": _count(db, Item, Item.winner_id == uid),
            "active_bids": active_bid_items,
        },
        "skill": {
            "selling": _count(
                db, SkillItem,
                SkillItem.seller_id == uid,
                SkillItem.is_deleted.is_(False),
            ),
            "bookings_in_progress": bookings(SkillBooking.buyer_id, "in_progress")
            + bookings(SkillBooking.seller_id, "in_progress"),
            "bookings_completed": bookings(SkillBooking.buyer_id, "completed")
            + bookings(SkillBooking.seller_id, "completed"),
        },
        "prediction_bets": {
            r: _count(db, PredictionBet, PredictionBet.user_id == uid, PredictionBet.result == r)
            for r in ("pending", "won", "lost")
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
