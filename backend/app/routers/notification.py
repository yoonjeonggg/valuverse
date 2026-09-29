from fastapi import APIRouter, Query

from app.core.deps import DbSession, CurrentUser
from app.schemas.notification import NotificationResponse, UnreadCountResponse
from app.services import notification_service

router = APIRouter(tags=["Notification"])


@router.get("/users/me/notifications", response_model=list[NotificationResponse])
def list_my_notifications(
    db: DbSession,
    user: CurrentUser,
    unread_only: bool = Query(default=False, alias="unread"),
    limit: int = Query(default=50, le=200),
):
    return notification_service.list_notifications(db, user.id, unread_only, limit)


@router.get("/users/me/notifications/unread-count", response_model=UnreadCountResponse)
def unread_count(db: DbSession, user: CurrentUser):
    return UnreadCountResponse(unread=notification_service.unread_count(db, user.id))


@router.post("/notifications/{notification_id}/read", response_model=NotificationResponse)
def mark_read(notification_id: int, db: DbSession, user: CurrentUser):
    return notification_service.mark_read(db, notification_id, user.id)


@router.post("/notifications/read-all", response_model=UnreadCountResponse)
def mark_all_read(db: DbSession, user: CurrentUser):
    notification_service.mark_all_read(db, user.id)
    return UnreadCountResponse(unread=0)
