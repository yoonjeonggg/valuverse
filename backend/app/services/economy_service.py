"""포인트 이코노미 - 적립(출석/미션/광고)과 소모(상단 노출권).

기획서 원칙: 포인트는 출석·미션·광고 시청 등 무상 활동으로만 획득한다.
현금 충전 경로는 없다.
"""

from datetime import timedelta
from typing import Callable

from fastapi import HTTPException, status
from sqlalchemy import exists, func
from sqlalchemy.orm import Session
from sqlalchemy.sql.expression import Exists

from app.core.config import settings
from app.core.db_utils import commit_or_conflict, get_or_404, save
from app.core.timeutils import aware, now, is_past
from app.models.auction import Bid, Item
from app.models.economy import Attendance, Coupon, MissionClaim
from app.models.point import PointTransaction
from app.models.review import Review
from app.models.user import User
from app.services import point_service


# ==================== 출석 체크 ====================
def _latest_attendance(db: Session, user_id: int) -> Attendance | None:
    return (
        db.query(Attendance)
        .filter(Attendance.user_id == user_id)
        .order_by(Attendance.check_date.desc())
        .first()
    )


def _yesterday_str(today) -> str:
    return (today - timedelta(days=1)).isoformat()


def _active_streak(latest: Attendance | None, today) -> int:
    """마지막 출석이 어제/오늘이 아니면 스트릭은 이미 끊긴 것 -- 다음 출석 시
    1일로 리셋되므로(check_in 참고) 옛 스트릭 값을 그대로 노출하지 않는다."""
    if latest is None:
        return 0
    if latest.check_date in (today.isoformat(), _yesterday_str(today)):
        return latest.streak
    return 0


def get_active_attendance_streak(db: Session, user_id: int) -> int:
    return _active_streak(_latest_attendance(db, user_id), now().date())


def _check_in_reward(streak: int) -> int:
    bonus_days = min(streak, settings.point_checkin_streak_cap)
    return settings.point_checkin_base + settings.point_checkin_streak_bonus * (
        bonus_days - 1
    )


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

    streak = (latest.streak + 1) if latest and latest.check_date == _yesterday_str(today) else 1

    reward = _check_in_reward(streak)

    db.add(
        Attendance(
            user_id=user.id, check_date=today_str, streak=streak, reward=reward
        )
    )
    point_service.apply_delta(db, user, reward, "attendance", f"출석 체크 ({streak}일 연속)")
    # 동시에 두 번 출석 요청이 오면 UNIQUE(user_id, check_date) 위반 -> 409로 변환.
    commit_or_conflict(db, "오늘은 이미 출석했습니다.")
    return {
        "check_date": today_str,
        "streak": streak,
        "reward": reward,
        "balance": user.points,
        "next_check_in_reward": _check_in_reward(streak + 1),
    }


# ==================== 미션 ====================
# key -> (보상, 설명, 달성 조건). 조건은 EXISTS 식이라 목록 조회 시 모든 미션을
# SELECT 한 번으로 확인할 수 있다 (미션 수만큼 쿼리를 날리지 않는다).
MISSIONS: dict[str, tuple[int, str, Callable[[int], Exists]]] = {
    "first_bid": (
        50,
        "첫 입찰하기",
        # 입찰 후 취소해도 달성으로 치면 입찰-취소만으로 보상을 받을 수 있다.
        lambda uid: exists().where(Bid.bidder_id == uid, Bid.is_cancelled.is_(False)),
    ),
    "first_item": (
        50,
        "상품 처음 등록하기",
        lambda uid: exists().where(Item.seller_id == uid, Item.is_deleted.is_(False)),
    ),
    "first_review": (
        30,
        "리뷰 처음 작성하기",
        lambda uid: exists().where(
            Review.author_id == uid, Review.is_deleted.is_(False)
        ),
    ),
}


def list_missions(db: Session, user: User) -> list[dict]:
    claimed = {
        key
        for (key,) in db.query(MissionClaim.mission_key).filter(
            MissionClaim.user_id == user.id
        )
    }
    achieved = db.query(*(cond(user.id) for _, _, cond in MISSIONS.values())).one()
    return [
        {
            "key": key,
            "description": desc,
            "reward": reward,
            "achieved": bool(done),
            "claimed": key in claimed,
        }
        for (key, (reward, desc, _)), done in zip(MISSIONS.items(), achieved)
    ]


def _already_claimed(db: Session, user_id: int, key: str) -> bool:
    return db.query(
        exists().where(MissionClaim.user_id == user_id, MissionClaim.mission_key == key)
    ).scalar()


def claim_mission(db: Session, user: User, key: str) -> dict:
    if key not in MISSIONS:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "존재하지 않는 미션입니다.")
    reward, desc, cond = MISSIONS[key]
    if _already_claimed(db, user.id, key):
        raise HTTPException(status.HTTP_409_CONFLICT, "이미 보상을 받은 미션입니다.")
    if not db.query(cond(user.id)).scalar():
        raise HTTPException(status.HTTP_409_CONFLICT, "아직 달성하지 못한 미션입니다.")

    db.add(MissionClaim(user_id=user.id, mission_key=key, reward=reward))
    point_service.apply_delta(db, user, reward, "mission", f"미션 보상: {desc}")
    # 동시에 두 번 수령 요청이 오면 UNIQUE(user_id, mission_key) 위반 -> 409로 변환.
    commit_or_conflict(db, "이미 보상을 받은 미션입니다.")
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
    point_service.spend(db, user.id, cost, "spend", f"쿠폰 교환: {desc}")
    coupon = Coupon(
        user_id=user.id,
        catalog_key=key,
        discount_percent=discount,
        cost=cost,
        expires_at=now() + timedelta(days=settings.coupon_valid_days),
    )
    db.add(coupon)
    return save(db, coupon)


def list_my_coupons(db: Session, user_id: int, unused_only: bool = False) -> list[Coupon]:
    q = db.query(Coupon).filter(Coupon.user_id == user_id)
    if unused_only:
        q = q.filter(Coupon.is_used.is_(False))
    return q.order_by(Coupon.created_at.desc()).all()


def use_coupon(db: Session, coupon_id: int, user_id: int) -> Coupon:
    # 본인 쿠폰으로 범위를 좁혀 조회한다: 남의 쿠폰이면 403 대신 404 를 돌려줘 쿠폰 ID 존재
    # 여부가 드러나지 않게 하고(열거 방지), 남의 행을 잠그지도 않는다.
    # 동시에 두 번 사용 요청이 오면 둘 다 is_used=False 를 보고 통과할 수 있으므로 잠그고 읽는다.
    coupon = get_or_404(
        db, Coupon, coupon_id, "쿠폰을 찾을 수 없습니다.",
        Coupon.user_id == user_id, for_update=True,
    )
    if coupon.is_used:
        raise HTTPException(status.HTTP_409_CONFLICT, "이미 사용한 쿠폰입니다.")
    if is_past(coupon.expires_at):
        raise HTTPException(status.HTTP_409_CONFLICT, "유효기간이 지난 쿠폰입니다.")
    coupon.is_used = True
    coupon.used_at = now()
    return save(db, coupon)


# ==================== 광고 보상 ====================
def _last_ad_reward_at(db: Session, user_id: int):
    return (
        db.query(func.max(PointTransaction.created_at))
        .filter(PointTransaction.user_id == user_id, PointTransaction.type == "ad")
        .scalar()
    )


def _ad_next_available_at(db: Session, user_id: int):
    """쿨다운 중이면 다시 받을 수 있는 시각, 아니면 None."""
    last = aware(_last_ad_reward_at(db, user_id))
    if last is None:
        return None
    available_at = last + timedelta(seconds=settings.point_ad_min_interval_seconds)
    return available_at if available_at > now() else None


def _ad_views_today(db: Session, user_id: int) -> int:
    today_start = now().replace(hour=0, minute=0, second=0, microsecond=0)
    return (
        db.query(func.count(PointTransaction.id))
        .filter(
            PointTransaction.user_id == user_id,
            PointTransaction.type == "ad",
            PointTransaction.created_at >= today_start,
        )
        .scalar()
    )


def ad_reward(db: Session, user: User) -> dict:
    # 동시 요청이 모두 "아직 한도 미만"으로 세고 통과하지 않도록, 세기 전에 사용자 행을 잠가
    # 같은 사용자의 광고 보상 요청을 직렬화한다.
    user = point_service.lock_user(db, user.id)
    views_today = _ad_views_today(db, user.id)
    if views_today >= settings.point_ad_daily_limit:
        raise HTTPException(
            status.HTTP_409_CONFLICT, "오늘 광고 보상 한도를 모두 사용했습니다."
        )
    # 광고 시청 여부를 서버가 검증할 수 없으므로, 최소한 광고 길이보다 빠른 연속 호출
    # (스크립트 연타)은 막는다.
    available_at = _ad_next_available_at(db, user.id)
    if available_at is not None:
        wait = int((available_at - now()).total_seconds()) + 1
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            f"광고 보상은 {wait}초 후에 다시 받을 수 있습니다.",
            headers={"Retry-After": str(wait)},
        )

    reward = settings.point_ad_reward
    point_service.apply_delta(db, user, reward, "ad", "리워드 광고 시청")
    db.commit()
    return {
        "reward": reward,
        "views_today": views_today + 1,
        "daily_limit": settings.point_ad_daily_limit,
        "balance": user.points,
        "next_available_at": now()
        + timedelta(seconds=settings.point_ad_min_interval_seconds),
    }


# ==================== 포인트 센터 요약 ====================
def get_points_summary(db: Session, user: User) -> dict:
    """포인트 화면 첫 진입에 필요한 상태(잔액/출석/광고)를 한 번에 돌려준다."""
    check_in_status = get_check_in_status(db, user)
    streak = check_in_status["streak"]
    return {
        "balance": user.points,
        **check_in_status,
        "streak_cap": settings.point_checkin_streak_cap,
        # 오늘 출석하면 받을 보상 (이미 출석했으면 내일 이어서 출석할 때의 보상)
        "next_check_in_reward": _check_in_reward(streak + 1),
        "ad_views_today": _ad_views_today(db, user.id),
        "ad_daily_limit": settings.point_ad_daily_limit,
        "ad_reward": settings.point_ad_reward,
        "ad_next_available_at": _ad_next_available_at(db, user.id),
    }
