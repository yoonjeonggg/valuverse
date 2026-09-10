from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, get_current_admin
from app.database import get_db
from app.models.user import User
from app.schemas.report import ReportCreate, ReportUpdate, ReportResponse
from app.services import report_service

router = APIRouter(prefix="/reports", tags=["Report"])


@router.post("", response_model=ReportResponse, status_code=status.HTTP_201_CREATED)
def create_report(
    payload: ReportCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return report_service.create_report(db, user, payload)


@router.get("", response_model=list[ReportResponse])
def list_reports(
    status_filter: str | None = Query(default=None, alias="status"),
    target_type: str | None = None,
    target_id: int | None = None,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    return report_service.list_reports(db, status_filter, target_type, target_id)


@router.get("/{report_id}", response_model=ReportResponse)
def get_report(
    report_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    return report_service.get_report(db, report_id)


@router.patch("/{report_id}", response_model=ReportResponse)
def update_report(
    report_id: int,
    payload: ReportUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    return report_service.update_report(db, report_id, payload)
