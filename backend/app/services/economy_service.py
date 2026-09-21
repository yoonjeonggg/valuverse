"""포인트 이코노미 - 적립(출석/미션/광고)과 소모(상단 노출권).

기획서 원칙: 포인트는 출석·미션·광고 시청 등 무상 활동으로만 획득한다.
현금 충전 경로는 없다.
"""

from datetime import timedelta

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.timeutils import now, is_past
from app.models.auction import Bid, Item
from app.models.economy import Attendance, Coupon, MissionClaim
from app.models.point import PointTransaction
from app.models.review import Review
from app.models.user import User
from app.services.point_service import apply_delta as _grant

# ==================== 출석 체크 ====================
def _latest_attendance(db: Session, user_id: int) -> Attendance | None:
    return (
        db.query(Attendance)
        .filter(Attendance.user_id == user_id)
        .order_by(Attendance.check_date.desc())
        .first()
    )


def _active_streak(latest: Attendance | None, today) -> int:
    """마지막 출석이 어제/오늘이 아니면 스트릭은 이미 끊긴 것 -- 다음 출석 시
    1일로 리셋되므로(check_in 참고) 옛 스트릭 값을 그대로 노출하지 않는다."""
    if latest is None:
        return 0
    yesterday = (today - timedelta(days=1)).isoformat()
    if latest.check_date == today.isoformat() or latest.check_date == yesterday:
        return latest.streak
    return 0


def get_active_attendance_streak(db: Session, user_id: int) -> int:
    return _active_streak(_latest_attendance(db, user_id), now().date())


def get_check_in_status(db: Session, user: User) -> dict:
    today = now().date()
    latest = _latest_attendance(db, user.id)
    return {
        "checked_in_today": bool(latest and latest.check_date == today.isoformat()),
        "streak": _active_streak(latest, today),
    }


def check_in(db: Session, user: User) -> dict:
    today = now().date()
    today_str = today.isoformat()

    latest = _latest_attendance(db, user.id)
    if latest and latest.check_date == today_str:
        raise HTTPException(status.HTTP_409_CONFLICT, "오늘은 이미 출석했습니다.")

    yesterday = (today - timedelta(days=1)).isoformat()
    streak = (latest.streak + 1) if latest and latest.check_date == yesterday else 1

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


# ==================== 쿠폰 교환 (포인트 소모처) ====================
# key -> (가격, 할인율(%), 설명)
COUPON_CATALOG: dict[str, tuple[int, int, str]] = {
    "fee_5": (200, 5, "수수료 5% 할인 쿠폰"),
    "fee_10": (350, 10, "수수료 10% 할인 쿠폰"),
    "fee_20": (600, 20, "수수료 20% 할인 쿠폰"),
}


def list_coupon_catalog() -> list[dict]:
    return [
        {"key": k, "cost": c, "discount_percent": d, "description": desc}
        for k, (c, d, desc) in COUPON_CATALOG.items()
    ]


def redeem_coupon(db: Session, user: User, key: str) -> Coupon:
    if key not in COUPON_CATALOG:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "존재하지 않는 쿠폰입니다.")
    cost, discount, desc = COUPON_CATALOG[key]
    if user.points < cost:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "보유 포인트가 부족합니다.")

    _grant(db, user, -cost, "spend", f"쿠폰 교환: {desc}")
    coupon = Coupon(
        user_id=user.id,
        catalog_key=key,
        discount_percent=discount,
        cost=cost,
        expires_at=now() + timedelta(days=settings.coupon_valid_days),
    )
    db.add(coupon)
    db.commit()
    db.refresh(coupon)
    return coupon


def list_my_coupons(db: Session, user_id: int, unused_only: bool = False) -> list[Coupon]:
    q = db.query(Coupon).filter(Coupon.user_id == user_id)
    if unused_only:
        q = q.filter(Coupon.is_used.is_(False))
    return q.order_by(Coupon.created_at.desc()).all()


def use_coupon(db: Session, coupon_id: int, user_id: int) -> Coupon:
    coupon = db.query(Coupon).filter(Coupon.id == coupon_id).first()
    if not coupon:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "쿠폰을 찾을 수 없습니다.")
    if coupon.user_id != user_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "본인 쿠폰만 사용할 수 있습니다.")
    if coupon.is_used:
        raise HTTPException(status.HTTP_409_CONFLICT, "이미 사용한 쿠폰입니다.")
    if is_past(coupon.expires_at):
        raise HTTPException(status.HTTP_409_CONFLICT, "유효기간이 지난 쿠폰입니다.")
    coupon.is_used = True
    coupon.used_at = now()
    db.commit()
    db.refresh(coupon)
    return coupon


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
