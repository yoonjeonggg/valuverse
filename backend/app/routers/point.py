from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, get_current_admin
from app.database import get_db
from app.models.user import User
from app.schemas.point import (
    PointTransactionCreate,
    PointTransactionResponse,
    PointBalanceResponse,
    CheckInResponse,
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
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    """수동 포인트 조정 (관리자 전용). 일반 적립은 출석/미션/광고 엔드포인트를 사용한다."""
    return point_service.create_transaction(db, admin, payload)


@router.get(
    "/users/me/point-transactions",
    response_model=list[PointTransactionResponse],
)
def list_my_point_transactions(
    type_filter: str | None = Query(default=None, alias="type"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return point_service.list_transactions(db, user.id, type_filter)


@router.get("/users/me/points/balance", response_model=PointBalanceResponse)
def get_my_point_balance(
    db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    return PointBalanceResponse(
        user_id=user.id, balance=point_service.get_balance(db, user.id)
    )


# ==================== 적립 (출석 / 미션 / 광고) ====================
@router.post("/points/check-in", response_model=CheckInResponse)
def check_in(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return economy_service.check_in(db, user)


@router.get("/points/missions", response_model=list[MissionStatus])
def list_missions(
    db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    return economy_service.list_missions(db, user)


@router.post("/points/missions/{key}/claim", response_model=MissionClaimResponse)
def claim_mission(
    key: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return economy_service.claim_mission(db, user, key)


@router.post("/points/ad-reward", response_model=AdRewardResponse)
def ad_reward(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return economy_service.ad_reward(db, user)


# ==================== 소모 (쿠폰 교환) ====================
@router.get("/points/coupons/catalog", response_model=list[CouponCatalogRow])
def coupon_catalog():
    return economy_service.list_coupon_catalog()


@router.post("/points/coupons/{key}/redeem", response_model=CouponResponse)
def redeem_coupon(
    key: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return economy_service.redeem_coupon(db, user, key)


@router.get("/users/me/coupons", response_model=list[CouponResponse])
def list_my_coupons(
    unused_only: bool = Query(default=False, alias="unused"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return economy_service.list_my_coupons(db, user.id, unused_only)


@router.post("/points/coupons/{coupon_id}/use", response_model=CouponResponse)
def use_coupon(
    coupon_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return economy_service.use_coupon(db, coupon_id, user.id)
