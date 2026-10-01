from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.db_utils import apply_patch, get_or_404, save
from app.core.timeutils import is_past
from app.models.prediction import Prediction, PredictionBet
from app.models.user import User
from app.schemas.prediction import (
    PredictionBetCreate,
    PredictionCreate,
    PredictionSettleRequest,
    PredictionUpdate,
)
from app.services import notification_service, point_service


def _pending_bets_filter(prediction_id: int) -> tuple:
    return (
        PredictionBet.prediction_id == prediction_id,
        PredictionBet.is_cancelled.is_(False),
        PredictionBet.result == "pending",
    )


def _is_open(prediction: Prediction) -> bool:
    """진행중이고 마감 시간 전이면 베팅/취소/내용 수정이 가능하다."""
    return prediction.status == "ongoing" and not is_past(prediction.end_time)


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
    return save(db, prediction)


def list_predictions(
    db: Session, status_filter: str | None = None
) -> list[Prediction]:
    q = db.query(Prediction)
    if status_filter:
        q = q.filter(Prediction.status == status_filter)
    return q.order_by(Prediction.created_at.desc()).all()


def get_prediction(
    db: Session, prediction_id: int, for_update: bool = False
) -> Prediction:
    return get_or_404(
        db, Prediction, prediction_id, "명제를 찾을 수 없습니다.", for_update=for_update
    )


def update_prediction(
    db: Session, prediction_id: int, payload: PredictionUpdate
) -> Prediction:
    prediction = get_prediction(db, prediction_id)
    data = payload.model_dump(exclude_unset=True)
    # 마감 후에는 상태/결과(정산) 관련 필드만 허용
    if not _is_open(prediction):
        allowed = {"status", "result"}
        if set(data) - allowed:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                "마감된 명제는 상태/결과만 변경할 수 있습니다.",
            )
    apply_patch(prediction, payload)
    return save(db, prediction)


def delete_prediction(db: Session, prediction_id: int) -> None:
    prediction = get_prediction(db, prediction_id)
    has_bets = db.query(
        db.query(PredictionBet.id)
        .filter(
            PredictionBet.prediction_id == prediction_id,
            PredictionBet.is_cancelled.is_(False),
        )
        .exists()
    ).scalar()
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
    if not _is_open(prediction):
        raise HTTPException(status.HTTP_409_CONFLICT, "마감된 명제입니다.")
    point_service.spend(
        db, user.id, payload.amount, "bet", f"예측 베팅 #{prediction_id}"
    )
    bet = PredictionBet(
        prediction_id=prediction_id,
        user_id=user.id,
        position=payload.position,
        amount=payload.amount,
        result="pending",
    )
    db.add(bet)
    return save(db, bet)


def get_odds(db: Session, prediction_id: int) -> dict:
    """현재 베팅 풀 기준 파리뮤추얼 배당 배수를 계산한다 (FR-PRD-03)."""
    get_prediction(db, prediction_id)
    # 베팅 행을 전부 가져와 파이썬에서 합산하지 않고, 포지션별 합계/인원을 DB 에서 집계한다.
    pools = {
        position: (pool, backers)
        for position, pool, backers in db.query(
            PredictionBet.position,
            func.sum(PredictionBet.amount),
            func.count(PredictionBet.id),
        )
        .filter(*_pending_bets_filter(prediction_id))
        .group_by(PredictionBet.position)
    }
    yes_pool, yes_backers = pools.get("yes", (0, 0))
    no_pool, no_backers = pools.get("no", (0, 0))
    total = yes_pool + no_pool
    return {
        "prediction_id": prediction_id,
        "yes_pool": yes_pool,
        "no_pool": no_pool,
        "total_pool": total,
        "yes_backers": yes_backers,
        "no_backers": no_backers,
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
    # 정산 요청이 동시에 두 번 오면 배당이 이중 지급될 수 있으므로 명제 행을 잠그고 읽는다.
    prediction = get_prediction(db, prediction_id, for_update=True)
    if prediction.status == "settled":
        raise HTTPException(status.HTTP_409_CONFLICT, "이미 정산된 명제입니다.")
    if not is_past(prediction.end_time):
        raise HTTPException(
            status.HTTP_409_CONFLICT, "마감 시간 전에는 정산할 수 없습니다."
        )

    bets = db.query(PredictionBet).filter(*_pending_bets_filter(prediction_id)).all()
    total_pool = sum(b.amount for b in bets)
    winners = [b for b in bets if b.position == payload.result]
    losers = [b for b in bets if b.position != payload.result]
    winning_pool = sum(b.amount for b in winners)

    total_payout = 0
    refunded = winning_pool == 0

    # 베팅자마다 한 번씩 조회하지 않고 한 쿼리로 가져온다.
    user_ids = {b.user_id for b in bets}
    users = (
        {u.id: u for u in db.query(User).filter(User.id.in_(user_ids))} if user_ids else {}
    )

    if refunded:
        for b in bets:
            _pay(db, users.get(b.user_id), b, b.amount, "refunded", "refund",
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
            _pay(db, users.get(b.user_id), b, amount, "won", "bet",
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
    point_service.apply_delta(db, user, amount, tx_type, memo)


def list_my_bets(db: Session, user_id: int) -> list[PredictionBet]:
    return (
        db.query(PredictionBet)
        .filter(PredictionBet.user_id == user_id)
        .order_by(PredictionBet.created_at.desc())
        .all()
    )


def cancel_bet(db: Session, bet_id: int, user: User) -> None:
    # 본인 베팅만 조회(남의 베팅이면 404)하고, 동시 취소로 이중 환불되지 않게 행을 잠근다.
    bet = get_or_404(
        db, PredictionBet, bet_id, "베팅을 찾을 수 없습니다.",
        PredictionBet.user_id == user.id, for_update=True,
    )
    if bet.is_cancelled:
        raise HTTPException(status.HTTP_409_CONFLICT, "이미 취소된 베팅입니다.")

    prediction = get_prediction(db, bet.prediction_id)
    if not _is_open(prediction):
        raise HTTPException(status.HTTP_409_CONFLICT, "마감 후에는 취소할 수 없습니다.")

    bet.is_cancelled = True
    bet.result = "refunded"
    point_service.apply_delta(
        db, user, bet.amount, "refund", f"예측 베팅 취소 #{bet.prediction_id}"
    )
    db.commit()
