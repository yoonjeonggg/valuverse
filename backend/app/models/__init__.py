"""모든 모델을 한 곳에서 import 해 Base.metadata 에 등록한다."""

from app.models.auction import Bid, BlindBid, Item
from app.models.economy import Attendance, Coupon, MissionClaim
from app.models.notification import Notification
from app.models.point import PointTransaction
from app.models.prediction import Prediction, PredictionBet
from app.models.report import Report
from app.models.review import Review
from app.models.skill import Escrow, SkillBooking, SkillItem
from app.models.user import User

__all__ = [
    "Attendance",
    "Bid",
    "BlindBid",
    "Coupon",
    "Escrow",
    "Item",
    "MissionClaim",
    "Notification",
    "PointTransaction",
    "Prediction",
    "PredictionBet",
    "Report",
    "Review",
    "SkillBooking",
    "SkillItem",
    "User",
]
