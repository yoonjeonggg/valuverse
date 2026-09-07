from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.point import (
    PointTransactionCreate,
    PointTransactionResponse,
    PointBalanceResponse,
)
from app.services import point_service

router = APIRouter(tags=["Point"])


@router.post(
    "/point-transactions",
    response_model=PointTransactionResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_point_transaction(
    payload: PointTransactionCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return point_service.create_transaction(db, user, payload)


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
