from fastapi import APIRouter, Query, status

from app.core.deps import DbSession, CurrentUser, CurrentAdmin
from app.schemas.point import (
    PointTransactionCreate,
    PointTransactionResponse,
    PointBalanceResponse,
    CheckInResponse,
    CheckInStatusResponse,
    PointsSummaryResponse,
    MissionStatus,
    MissionClaimResponse,
    AdRewardResponse,
    CouponCatalogRow,
    CouponResponse,
)
from app.services import point_service, economy_service

router = APIRouter(tags=["Point"])


@router.post(
    "/point-transactions",
    response_model=PointTransactionResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_point_transaction(
    payload: PointTransactionCreate,
    db: DbSession,
    admin: CurrentAdmin,
):
    """수동 포인트 조정 (관리자 전용). 일반 적립은 출석/미션/광고 엔드포인트를 사용한다."""
    return point_service.create_transaction(db, admin, payload)


@router.get(
    "/users/me/point-transactions",
    response_model=list[PointTransactionResponse],
)
def list_my_point_transactions(
    db: DbSession,
    user: CurrentUser,
    type_filter: str | None = Query(default=None, alias="type", max_length=30),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
):
    return point_service.list_transactions(db, user.id, type_filter, skip, limit)


@router.get("/users/me/points/balance", response_model=PointBalanceResponse)
def get_my_point_balance(db: DbSession, user: CurrentUser):
    return PointBalanceResponse(
        user_id=user.id, balance=point_service.get_balance(db, user.id)
    )


@router.get("/users/me/points/summary", response_model=PointsSummaryResponse)
def get_my_points_summary(db: DbSession, user: CurrentUser):
    """포인트 센터 첫 화면용: 잔액 + 출석 상태 + 오늘 광고 시청 현황을 한 번에."""
    return economy_service.get_points_summary(db, user)


# ==================== 적립 (출석 / 미션 / 광고) ====================
@router.get("/points/check-in/status", response_model=CheckInStatusResponse)
def check_in_status(db: DbSession, user: CurrentUser):
    return economy_service.get_check_in_status(db, user)


@router.post("/points/check-in", response_model=CheckInResponse)
def check_in(db: DbSession, user: CurrentUser):
    return economy_service.check_in(db, user)


@router.get("/points/missions", response_model=list[MissionStatus])
def list_missions(db: DbSession, user: CurrentUser):
    return economy_service.list_missions(db, user)


@router.post("/points/missions/{key}/claim", response_model=MissionClaimResponse)
def claim_mission(key: str, db: DbSession, user: CurrentUser):
    return economy_service.claim_mission(db, user, key)


@router.post("/points/ad-reward", response_model=AdRewardResponse)
def ad_reward(db: DbSession, user: CurrentUser):
    return economy_service.ad_reward(db, user)


# ==================== 소모 (쿠폰 교환) ====================
@router.get("/points/coupons/catalog", response_model=list[CouponCatalogRow])
def coupon_catalog():
    return economy_service.list_coupon_catalog()


@router.post("/points/coupons/{key}/redeem", response_model=CouponResponse)
def redeem_coupon(key: str, db: DbSession, user: CurrentUser):
    return economy_service.redeem_coupon(db, user, key)


@router.get("/users/me/coupons", response_model=list[CouponResponse])
def list_my_coupons(
    db: DbSession,
    user: CurrentUser,
    unused_only: bool = Query(default=False, alias="unused"),
):
    return economy_service.list_my_coupons(db, user.id, unused_only)


@router.post("/points/coupons/{coupon_id}/use", response_model=CouponResponse)
def use_coupon(coupon_id: int, db: DbSession, user: CurrentUser):
    return economy_service.use_coupon(db, coupon_id, user.id)
