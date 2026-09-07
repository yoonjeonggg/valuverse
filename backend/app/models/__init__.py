"""모든 모델을 한 곳에서 import 해 Base.metadata 에 등록한다."""

from app.models.user import User
from app.models.auction import Item, Bid, BlindBid
from app.models.skill import SkillItem, SkillBooking, Escrow
from app.models.prediction import Prediction, PredictionBet
from app.models.point import PointTransaction
from app.models.review import Review
from app.models.report import Report

__all__ = [
    "User",
    "Item",
    "Bid",
    "BlindBid",
    "SkillItem",
    "SkillBooking",
    "Escrow",
    "Prediction",
    "PredictionBet",
    "PointTransaction",
    "Review",
    "Report",
]
