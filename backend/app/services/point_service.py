from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.point import PointTransaction
from app.models.user import User
from app.schemas.point import PointTransactionCreate


def create_transaction(
    db: Session, requester: User, payload: PointTransactionCreate
) -> PointTransaction:
    target_id = payload.user_id or requester.id

    # 남의 포인트를 조작하려면 관리자여야 한다.
    if target_id != requester.id and not requester.is_admin:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, "다른 사용자의 포인트를 변경할 수 없습니다."
        )

    target = db.query(User).filter(User.id == target_id).first()
    if not target:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "대상 사용자를 찾을 수 없습니다.")

    new_balance = target.points + payload.amount
    if new_balance < 0:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "보유 포인트가 부족합니다.")

    target.points = new_balance
    tx = PointTransaction(
        user_id=target.id,
        amount=payload.amount,
        type=payload.type,
        memo=payload.memo,
        balance_after=new_balance,
    )
    db.add(tx)
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
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "사용자를 찾을 수 없습니다.")
    return user.points
