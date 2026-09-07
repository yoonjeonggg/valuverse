from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.timeutils import is_past
from app.models.prediction import Prediction, PredictionBet
from app.models.point import PointTransaction
from app.models.user import User
from app.schemas.prediction import (
    PredictionCreate,
    PredictionUpdate,
    PredictionBetCreate,
)


# ==================== Prediction ====================
def create_prediction(
    db: Session, admin: User, payload: PredictionCreate
) -> Prediction:
    prediction = Prediction(
        title=payload.title,
        description=payload.description,
        end_time=payload.end_time,
        yes_odds=payload.yes_odds,
        no_odds=payload.no_odds,
        status="ongoing",
        created_by=admin.id,
    )
    db.add(prediction)
    db.commit()
    db.refresh(prediction)
    return prediction


def list_predictions(
    db: Session, status_filter: str | None = None
) -> list[Prediction]:
    q = db.query(Prediction)
    if status_filter:
        q = q.filter(Prediction.status == status_filter)
    return q.order_by(Prediction.created_at.desc()).all()


def get_prediction(db: Session, prediction_id: int) -> Prediction:
    prediction = db.query(Prediction).filter(Prediction.id == prediction_id).first()
    if not prediction:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "명제를 찾을 수 없습니다.")
    return prediction


def update_prediction(
    db: Session, prediction_id: int, payload: PredictionUpdate
) -> Prediction:
    prediction = get_prediction(db, prediction_id)
    data = payload.model_dump(exclude_unset=True)
    # 마감 후에는 상태/결과(정산) 관련 필드만 허용
    if prediction.status != "ongoing" or is_past(prediction.end_time):
        allowed = {"status", "result"}
        if set(data) - allowed:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                "마감된 명제는 상태/결과만 변경할 수 있습니다.",
            )
    for field, value in data.items():
        setattr(prediction, field, value)
    db.commit()
    db.refresh(prediction)
    return prediction


def delete_prediction(db: Session, prediction_id: int) -> None:
    prediction = get_prediction(db, prediction_id)
    has_bets = (
        db.query(PredictionBet.id)
        .filter(
            PredictionBet.prediction_id == prediction_id,
            PredictionBet.is_cancelled.is_(False),
        )
        .first()
        is not None
    )
    if has_bets:
        raise HTTPException(
            status.HTTP_409_CONFLICT, "베팅이 있는 명제는 삭제할 수 없습니다."
        )
    db.delete(prediction)
    db.commit()


# ==================== PredictionBet ====================
def create_bet(
    db: Session, prediction_id: int, user: User, payload: PredictionBetCreate
) -> PredictionBet:
    prediction = get_prediction(db, prediction_id)
    if prediction.status != "ongoing" or is_past(prediction.end_time):
        raise HTTPException(status.HTTP_409_CONFLICT, "마감된 명제입니다.")
    if user.points < payload.amount:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "보유 포인트가 부족합니다.")

    user.points -= payload.amount
    bet = PredictionBet(
        prediction_id=prediction_id,
        user_id=user.id,
        position=payload.position,
        amount=payload.amount,
        result="pending",
    )
    db.add(bet)
    db.add(
        PointTransaction(
            user_id=user.id,
            amount=-payload.amount,
            type="bet",
            memo=f"예측 베팅 #{prediction_id}",
            balance_after=user.points,
        )
    )
    db.commit()
    db.refresh(bet)
    return bet


def list_my_bets(db: Session, user_id: int) -> list[PredictionBet]:
    return (
        db.query(PredictionBet)
        .filter(PredictionBet.user_id == user_id)
        .order_by(PredictionBet.created_at.desc())
        .all()
    )


def cancel_bet(db: Session, bet_id: int, user: User) -> None:
    bet = db.query(PredictionBet).filter(PredictionBet.id == bet_id).first()
    if not bet:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "베팅을 찾을 수 없습니다.")
    if bet.user_id != user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "본인 베팅만 취소할 수 있습니다.")
    if bet.is_cancelled:
        raise HTTPException(status.HTTP_409_CONFLICT, "이미 취소된 베팅입니다.")

    prediction = get_prediction(db, bet.prediction_id)
    if prediction.status != "ongoing" or is_past(prediction.end_time):
        raise HTTPException(status.HTTP_409_CONFLICT, "마감 후에는 취소할 수 없습니다.")

    bet.is_cancelled = True
    bet.result = "refunded"
    user.points += bet.amount
    db.add(
        PointTransaction(
            user_id=user.id,
            amount=bet.amount,
            type="refund",
            memo=f"예측 베팅 취소 #{bet.prediction_id}",
            balance_after=user.points,
        )
    )
    db.commit()
