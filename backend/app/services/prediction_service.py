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
    PredictionSettleRequest,
)
from app.services import notification_service


def _active_bets(db: Session, prediction_id: int) -> list[PredictionBet]:
    return (
        db.query(PredictionBet)
        .filter(
            PredictionBet.prediction_id == prediction_id,
            PredictionBet.is_cancelled.is_(False),
        )
        .all()
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


def get_odds(db: Session, prediction_id: int) -> dict:
    """현재 베팅 풀 기준 파리뮤추얼 배당 배수를 계산한다 (FR-PRD-03)."""
    get_prediction(db, prediction_id)
    bets = [b for b in _active_bets(db, prediction_id) if b.result == "pending"]
    yes = [b for b in bets if b.position == "yes"]
    no = [b for b in bets if b.position == "no"]
    yes_pool = sum(b.amount for b in yes)
    no_pool = sum(b.amount for b in no)
    total = yes_pool + no_pool
    return {
        "prediction_id": prediction_id,
        "yes_pool": yes_pool,
        "no_pool": no_pool,
        "total_pool": total,
        "yes_backers": len(yes),
        "no_backers": len(no),
        "yes_odds": round(total / yes_pool, 2) if yes_pool else None,
        "no_odds": round(total / no_pool, 2) if no_pool else None,
    }


def settle_prediction(
    db: Session, prediction_id: int, payload: PredictionSettleRequest
) -> dict:
    """명제를 정산한다. 승리 포지션 베팅자에게 파리뮤추얼 방식으로 배당 (FR-PRD-04).

    - 승리 풀이 비어 있으면(아무도 정답을 고르지 않음) 전원 원금 환불.
    - 그 외에는 승자가 전체 풀을 자기 지분 비율로 나눠 가진다.
    """
    prediction = get_prediction(db, prediction_id)
    if prediction.status == "settled":
        raise HTTPException(status.HTTP_409_CONFLICT, "이미 정산된 명제입니다.")
    if not is_past(prediction.end_time):
        raise HTTPException(
            status.HTTP_409_CONFLICT, "마감 시간 전에는 정산할 수 없습니다."
        )

    bets = [b for b in _active_bets(db, prediction_id) if b.result == "pending"]
    total_pool = sum(b.amount for b in bets)
    winners = [b for b in bets if b.position == payload.result]
    losers = [b for b in bets if b.position != payload.result]
    winning_pool = sum(b.amount for b in winners)

    total_payout = 0
    refunded = winning_pool == 0

    users = {b.user_id: db.get(User, b.user_id) for b in bets}

    if refunded:
        for b in bets:
            _pay(db, users[b.user_id], b, b.amount, "refunded", "refund",
                 f"예측 정산 환불 #{prediction_id}")
            total_payout += b.amount
            notification_service.notify(
                db, b.user_id, "bet_result",
                f"'{prediction.title}' 정산: 승자가 없어 {b.amount} 포인트를 환불했습니다.",
                "prediction", prediction_id,
            )
    else:
        for b in winners:
            amount = b.amount * total_pool // winning_pool
            _pay(db, users[b.user_id], b, amount, "won", "bet",
                 f"예측 정산 배당 #{prediction_id}")
            total_payout += amount
            notification_service.notify(
                db, b.user_id, "bet_result",
                f"'{prediction.title}' 베팅에 적중해 {amount} 포인트를 받았습니다.",
                "prediction", prediction_id,
            )
        for b in losers:
            b.result = "lost"
            b.payout = 0
            notification_service.notify(
                db, b.user_id, "bet_result",
                f"'{prediction.title}' 베팅이 빗나갔습니다.",
                "prediction", prediction_id,
            )

    prediction.status = "settled"
    prediction.result = payload.result
    db.commit()

    return {
        "prediction_id": prediction_id,
        "result": payload.result,
        "total_pool": total_pool,
        "winning_pool": winning_pool,
        "winners": len(winners),
        "losers": len(losers),
        "total_payout": total_payout,
        "refunded": refunded,
    }


def _pay(
    db: Session,
    user: User,
    bet: PredictionBet,
    amount: int,
    bet_result: str,
    tx_type: str,
    memo: str,
) -> None:
    bet.result = bet_result
    bet.payout = amount
    if amount <= 0 or user is None:
        return
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
