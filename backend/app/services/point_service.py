from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.db_utils import get_or_404
from app.models.point import PointTransaction
from app.models.user import User
from app.schemas.point import PointTransactionCreate


def apply_delta(
    db: Session,
    user: User,
    amount: int,
    tx_type: str,
    memo: str | None = None,
) -> PointTransaction:
    """사용자 포인트를 `amount` 만큼 조정하고 이력 트랜잭션을 남긴다.

    잔액/권한 검증은 호출자 책임이며, 커밋도 호출자가 한다.
    (양수=적립, 음수=차감. `type` 예: attendance|mission|ad|bet|spend|refund|etc)
    """
    user.points += amount
    tx = PointTransaction(
        user_id=user.id,
        amount=amount,
        type=tx_type,
        memo=memo,
        balance_after=user.points,
    )
    db.add(tx)
    return tx


def create_transaction(
    db: Session, requester: User, payload: PointTransactionCreate
) -> PointTransaction:
    target_id = payload.user_id or requester.id

    # 남의 포인트를 조작하려면 관리자여야 한다.
    if target_id != requester.id and not requester.is_admin:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, "다른 사용자의 포인트를 변경할 수 없습니다."
        )

    target = get_or_404(db, User, target_id, "대상 사용자를 찾을 수 없습니다.")

    if target.points + payload.amount < 0:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "보유 포인트가 부족합니다.")

    tx = apply_delta(db, target, payload.amount, payload.type, payload.memo)
    db.commit()
    db.refresh(tx)
    return tx


def list_transactions(
    db: Session, user_id: int, type_filter: str | None = None
) -> list[PointTransaction]:
    q = db.query(PointTransaction).filter(PointTransaction.user_id == user_id)
    if type_filter:
        q = q.filter(PointTransaction.type == type_filter)
    return q.order_by(PointTransaction.created_at.desc()).all()


def get_balance(db: Session, user_id: int) -> int:
    return get_or_404(db, User, user_id, "사용자를 찾을 수 없습니다.").points
