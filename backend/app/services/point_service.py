from fastapi import HTTPException, status
from sqlalchemy import update
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import set_committed_value

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

    메모리의 user.points 에 더하지 않고 `UPDATE ... SET points = points + :amount
    RETURNING points` 한 문장으로 DB 에서 원자적으로 증감한다. 요청 시작 시점에
    로드해둔 stale 한 잔액에 더해 덮어쓰면, 그 사이 다른 요청이 커밋한 증감이
    사라진다(lost update: 예) 출석 적립과 쿠폰 교환이 동시에 오면 차감이 무효화).
    """
    balance = db.execute(
        update(User)
        .where(User.id == user.id)
        .values(points=User.points + amount)
        .returning(User.points)
        .execution_options(synchronize_session=False)
    ).scalar_one()
    set_committed_value(user, "points", balance)
    tx = PointTransaction(
        user_id=user.id,
        amount=amount,
        type=tx_type,
        memo=memo,
        balance_after=balance,
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

    target = get_or_404(
        db, User, target_id, "대상 사용자를 찾을 수 없습니다.", for_update=True
    )

    if target.points + payload.amount < 0:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "보유 포인트가 부족합니다.")

    # 행위자(관리자) 기록 -- 누가 조정했는지 이력에서 추적할 수 있게 남긴다.
    memo = f"[관리자 #{requester.id}] {payload.memo}"
    tx = apply_delta(db, target, payload.amount, payload.type, memo)
    db.commit()
    db.refresh(tx)
    return tx


def list_transactions(
    db: Session,
    user_id: int,
    type_filter: str | None = None,
    skip: int = 0,
    limit: int = 50,
) -> list[PointTransaction]:
    q = db.query(PointTransaction).filter(PointTransaction.user_id == user_id)
    if type_filter:
        q = q.filter(PointTransaction.type == type_filter)
    return (
        q.order_by(PointTransaction.created_at.desc(), PointTransaction.id.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


def get_balance(db: Session, user_id: int) -> int:
    return get_or_404(db, User, user_id, "사용자를 찾을 수 없습니다.").points
