from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, get_current_admin
from app.database import get_db
from app.models.user import User
from app.schemas.prediction import (
    PredictionCreate,
    PredictionUpdate,
    PredictionResponse,
    PredictionBetCreate,
    PredictionBetResponse,
    PredictionOddsResponse,
    PredictionSettleRequest,
    PredictionSettleResponse,
)
from app.services import prediction_service

prediction_router = APIRouter(prefix="/predictions", tags=["Prediction"])
bet_router = APIRouter(tags=["Prediction Bet"])


# ==================== Prediction ====================
@prediction_router.post(
    "", response_model=PredictionResponse, status_code=status.HTTP_201_CREATED
)
def create_prediction(
    payload: PredictionCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    return prediction_service.create_prediction(db, admin, payload)


@prediction_router.get("", response_model=list[PredictionResponse])
def list_predictions(
    status_filter: str | None = Query(default=None, alias="status"),
    db: Session = Depends(get_db),
):
    return prediction_service.list_predictions(db, status_filter)


@prediction_router.get("/{prediction_id}", response_model=PredictionResponse)
def get_prediction(prediction_id: int, db: Session = Depends(get_db)):
    return prediction_service.get_prediction(db, prediction_id)


@prediction_router.get("/{prediction_id}/odds", response_model=PredictionOddsResponse)
def get_odds(prediction_id: int, db: Session = Depends(get_db)):
    return prediction_service.get_odds(db, prediction_id)


@prediction_router.post(
    "/{prediction_id}/settle", response_model=PredictionSettleResponse
)
def settle_prediction(
    prediction_id: int,
    payload: PredictionSettleRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    return prediction_service.settle_prediction(db, prediction_id, payload)


@prediction_router.patch("/{prediction_id}", response_model=PredictionResponse)
def update_prediction(
    prediction_id: int,
    payload: PredictionUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    return prediction_service.update_prediction(db, prediction_id, payload)


@prediction_router.delete(
    "/{prediction_id}", status_code=status.HTTP_204_NO_CONTENT
)
def delete_prediction(
    prediction_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    prediction_service.delete_prediction(db, prediction_id)


# ==================== PredictionBet ====================
@prediction_router.post(
    "/{prediction_id}/bets",
    response_model=PredictionBetResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Prediction Bet"],
)
def create_bet(
    prediction_id: int,
    payload: PredictionBetCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return prediction_service.create_bet(db, prediction_id, user, payload)


@bet_router.get(
    "/users/me/prediction-bets",
    response_model=list[PredictionBetResponse],
    tags=["Prediction Bet"],
)
def list_my_bets(
    db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    return prediction_service.list_my_bets(db, user.id)


@bet_router.delete(
    "/prediction-bets/{bet_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["Prediction Bet"],
)
def cancel_bet(
    bet_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    prediction_service.cancel_bet(db, bet_id, user)
