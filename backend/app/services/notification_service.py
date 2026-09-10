"""알림 생성/조회 (FR-COM-03).

`notify()` 는 세션에 추가만 하고 커밋하지 않는다. 이벤트를 일으킨 서비스의
트랜잭션이 함께 커밋한다.
"""

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.notification import Notification


def notify(
    db: Session,
    user_id: int,
    ntype: str,
    message: str,
    related_type: str | None = None,
    related_id: int | None = None,
) -> None:
    db.add(
        Notification(
            user_id=user_id,
            type=ntype,
            message=message,
            related_type=related_type,
            related_id=related_id,
        )
    )


def list_notifications(
    db: Session, user_id: int, unread_only: bool = False, limit: int = 50
) -> list[Notification]:
    q = db.query(Notification).filter(Notification.user_id == user_id)
    if unread_only:
        q = q.filter(Notification.is_read.is_(False))
    return q.order_by(Notification.created_at.desc(), Notification.id.desc()).limit(limit).all()


def unread_count(db: Session, user_id: int) -> int:
    return (
        db.query(func.count(Notification.id))
        .filter(Notification.user_id == user_id, Notification.is_read.is_(False))
        .scalar()
    )


def mark_read(db: Session, notification_id: int, user_id: int) -> Notification:
    notif = (
        db.query(Notification)
        .filter(Notification.id == notification_id)
        .first()
    )
    if not notif:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "알림을 찾을 수 없습니다.")
    if notif.user_id != user_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "본인 알림만 처리할 수 있습니다.")
    notif.is_read = True
    db.commit()
    db.refresh(notif)
    return notif


def mark_all_read(db: Session, user_id: int) -> int:
    updated = (
        db.query(Notification)
        .filter(Notification.user_id == user_id, Notification.is_read.is_(False))
        .update({"is_read": True})
    )
    db.commit()
    return updated
