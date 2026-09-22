from fastapi import HTTPException, status
from sqlalchemy.orm import Session


def get_or_404(
    db: Session, model, id_, detail: str, *extra_filters, for_update: bool = False
):
    """`for_update=True` 면 행 잠금(SELECT ... FOR UPDATE)을 걸고 최신 값으로
    갱신해서 읽는다. 포인트 잔액처럼 확인 후 차감하는 동시 요청에서
    이중 사용(잔액 초과 차감)을 막을 때 사용한다."""
    q = db.query(model).filter(model.id == id_, *extra_filters)
    if for_update:
        q = q.populate_existing().with_for_update()
    obj = q.first()
    if not obj:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail)
    return obj
