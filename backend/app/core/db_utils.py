from fastapi import HTTPException, status
from sqlalchemy.orm import Session


def get_or_404(db: Session, model, id_, detail: str, *extra_filters):
    obj = db.query(model).filter(model.id == id_, *extra_filters).first()
    if not obj:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail)
    return obj
