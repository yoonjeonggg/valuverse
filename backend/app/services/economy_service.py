"""포인트 이코노미 - 적립(출석/미션/광고)과 소모(상단 노출권).

기획서 원칙: 포인트는 출석·미션·광고 시청 등 무상 활동으로만 획득한다.
현금 충전 경로는 없다.
"""

from datetime import timedelta

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.timeutils import now
from app.models.auction import Bid, Item
from app.models.economy import Attendance, MissionClaim
from app.models.point import PointTransaction
from app.models.review import Review
from app.models.user import User


def _grant(db: Session, user: User, amount: int, tx_type: str, memo: str) -> None:
    user.points += amount
    db.add(
        PointTransaction(
            user_id=user.id,
            amount=amount,
            type=tx_type,
            memo=memo,
            balance_after=user.points,
        )
    )


# ==================== 출석 체크 ====================
def check_in(db: Session, user: User) -> dict:
    today = now().date()
    today_str = today.isoformat()

    if (
        db.query(Attendance.id)
        .filter(Attendance.user_id == user.id, Attendance.check_date == today_str)
        .first()
    ):
        raise HTTPException(status.HTTP_409_CONFLICT, "오늘은 이미 출석했습니다.")

    yesterday = (today - timedelta(days=1)).isoformat()
    prev = (
        db.query(Attendance)
        .filter(Attendance.user_id == user.id, Attendance.check_date == yesterday)
        .first()
    )
    streak = (prev.streak + 1) if prev else 1

    bonus_days = min(streak, settings.point_checkin_streak_cap)
    reward = settings.point_checkin_base + settings.point_checkin_streak_bonus * (
        bonus_days - 1
    )

    db.add(
        Attendance(
            user_id=user.id, check_date=today_str, streak=streak, reward=reward
        )
    )
    _grant(db, user, reward, "attendance", f"출석 체크 ({streak}일 연속)")
    db.commit()
    return {
        "check_date": today_str,
        "streak": streak,
        "reward": reward,
        "balance": user.points,
    }


# ==================== 미션 ====================
# key -> (보상, 설명, 달성 조건 검증 함수)
def _did_bid(db: Session, user_id: int) -> bool:
    return db.query(Bid.id).filter(Bid.bidder_id == user_id).first() is not None


def _did_register_item(db: Session, user_id: int) -> bool:
    return db.query(Item.id).filter(Item.seller_id == user_id).first() is not None


def _did_review(db: Session, user_id: int) -> bool:
    return (
        db.query(Review.id)
        .filter(Review.author_id == user_id, Review.is_deleted.is_(False))
        .first()
        is not None
    )


MISSIONS: dict[str, tuple[int, str]] = {
    "first_bid": (50, "첫 입찰하기"),
    "first_item": (50, "상품 처음 등록하기"),
    "first_review": (30, "리뷰 처음 작성하기"),
}

_CHECKERS = {
    "first_bid": _did_bid,
    "first_item": _did_register_item,
    "first_review": _did_review,
}


def list_missions(db: Session, user: User) -> list[dict]:
    claimed = {
        c.mission_key
        for c in db.query(MissionClaim).filter(MissionClaim.user_id == user.id)
    }
    out = []
    for key, (reward, desc) in MISSIONS.items():
        out.append(
            {
                "key": key,
                "description": desc,
                "reward": reward,
                "achieved": _CHECKERS[key](db, user.id),
                "claimed": key in claimed,
            }
        )
    return out


def claim_mission(db: Session, user: User, key: str) -> dict:
    if key not in MISSIONS:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "존재하지 않는 미션입니다.")
    if (
        db.query(MissionClaim.id)
        .filter(MissionClaim.user_id == user.id, MissionClaim.mission_key == key)
        .first()
    ):
        raise HTTPException(status.HTTP_409_CONFLICT, "이미 보상을 받은 미션입니다.")
    if not _CHECKERS[key](db, user.id):
        raise HTTPException(status.HTTP_409_CONFLICT, "아직 달성하지 못한 미션입니다.")

    reward = MISSIONS[key][0]
    db.add(MissionClaim(user_id=user.id, mission_key=key, reward=reward))
    _grant(db, user, reward, "mission", f"미션 보상: {MISSIONS[key][1]}")
    db.commit()
    return {"key": key, "reward": reward, "balance": user.points}


# ==================== 광고 보상 ====================
def ad_reward(db: Session, user: User) -> dict:
    today_start = now().replace(hour=0, minute=0, second=0, microsecond=0)
    views_today = (
        db.query(func.count(PointTransaction.id))
        .filter(
            PointTransaction.user_id == user.id,
            PointTransaction.type == "ad",
            PointTransaction.created_at >= today_start,
        )
        .scalar()
    )
    if views_today >= settings.point_ad_daily_limit:
        raise HTTPException(
            status.HTTP_409_CONFLICT, "오늘 광고 보상 한도를 모두 사용했습니다."
        )

    reward = settings.point_ad_reward
    _grant(db, user, reward, "ad", "리워드 광고 시청")
    db.commit()
    return {
        "reward": reward,
        "views_today": views_today + 1,
        "daily_limit": settings.point_ad_daily_limit,
        "balance": user.points,
    }
