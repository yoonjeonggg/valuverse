from fastapi import APIRouter, Query, status

from app.core.deps import CurrentAdmin, CurrentUser, DbSession
from app.schemas.report import ReportCreate, ReportResponse, ReportUpdate
from app.services import report_service

router = APIRouter(prefix="/reports", tags=["Report"])


@router.post("", response_model=ReportResponse, status_code=status.HTTP_201_CREATED)
def create_report(payload: ReportCreate, db: DbSession, user: CurrentUser):
    return report_service.create_report(db, user, payload)


@router.get("", response_model=list[ReportResponse])
def list_reports(
    db: DbSession,
    admin: CurrentAdmin,
    status_filter: str | None = Query(default=None, alias="status"),
    target_type: str | None = None,
    target_id: int | None = None,
):
    return report_service.list_reports(db, status_filter, target_type, target_id)


@router.get("/{report_id}", response_model=ReportResponse)
def get_report(report_id: int, db: DbSession, admin: CurrentAdmin):
    return report_service.get_report(db, report_id)


@router.patch("/{report_id}", response_model=ReportResponse)
def update_report(
    report_id: int,
    payload: ReportUpdate,
    db: DbSession,
    admin: CurrentAdmin,
):
    return report_service.update_report(db, report_id, payload)
