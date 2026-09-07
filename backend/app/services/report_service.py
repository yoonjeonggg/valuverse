from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.report import Report
from app.models.user import User
from app.schemas.report import ReportCreate, ReportUpdate


def create_report(db: Session, reporter: User, payload: ReportCreate) -> Report:
    report = Report(
        reporter_id=reporter.id,
        target_type=payload.target_type,
        target_id=payload.target_id,
        reason=payload.reason,
        status="pending",
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    return report


def list_reports(db: Session, status_filter: str | None = None) -> list[Report]:
    q = db.query(Report)
    if status_filter:
        q = q.filter(Report.status == status_filter)
    return q.order_by(Report.created_at.desc()).all()


def get_report(db: Session, report_id: int) -> Report:
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "신고를 찾을 수 없습니다.")
    return report


def update_report(db: Session, report_id: int, payload: ReportUpdate) -> Report:
    report = get_report(db, report_id)
    report.status = payload.status
    if payload.admin_memo is not None:
        report.admin_memo = payload.admin_memo
    db.commit()
    db.refresh(report)
    return report
