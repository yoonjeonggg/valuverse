import logging

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.db_utils import get_or_404, save
from app.core.errors import BadRequest, Conflict, NotFound
from app.models.auction import Item
from app.models.report import Report
from app.models.review import Review
from app.models.skill import SkillItem
from app.models.user import User
from app.schemas.report import ReportCreate, ReportUpdate
from app.services import notification_service
from app.services.review_service import recalc_rating

logger = logging.getLogger(__name__)

_TARGET_MODELS = {
    "user": User,
    "item": Item,
    "skill_item": SkillItem,
    "review": Review,
}

_OPEN_STATUSES = ("pending", "in_progress")


def _get_target(db: Session, target_type: str, target_id: int):
    return db.get(_TARGET_MODELS[target_type], target_id)


def create_report(db: Session, reporter: User, payload: ReportCreate) -> Report:
    target = _get_target(db, payload.target_type, payload.target_id)
    if target is None:
        raise NotFound("신고 대상을 찾을 수 없습니다.")
    if payload.target_type == "user" and payload.target_id == reporter.id:
        raise BadRequest("본인을 신고할 수 없습니다.")

    dup = (
        db.query(Report.id)
        .filter(
            Report.reporter_id == reporter.id,
            Report.target_type == payload.target_type,
            Report.target_id == payload.target_id,
            Report.status.in_(_OPEN_STATUSES),
        )
        .first()
    )
    if dup:
        raise Conflict("이미 접수된 신고가 처리 중입니다.")

    report = Report(
        reporter_id=reporter.id,
        target_type=payload.target_type,
        target_id=payload.target_id,
        reason=payload.reason,
        status="pending",
    )
    db.add(report)

    # 관리자에게 새 신고 알림
    for (admin_id,) in db.query(User.id).filter(User.is_admin.is_(True)):
        notification_service.notify(
            db,
            admin_id,
            "report_new",
            f"새 신고가 접수되었습니다: {payload.target_type} #{payload.target_id}",
            "report",
            None,
        )

    return save(db, report)


def list_reports(
    db: Session,
    status_filter: str | None = None,
    target_type: str | None = None,
    target_id: int | None = None,
) -> list[Report]:
    q = db.query(Report)
    if status_filter:
        q = q.filter(Report.status == status_filter)
    if target_type:
        q = q.filter(Report.target_type == target_type)
    if target_id is not None:
        q = q.filter(Report.target_id == target_id)
    return q.order_by(Report.created_at.desc()).all()


def get_report(db: Session, report_id: int) -> Report:
    return get_or_404(db, Report, report_id, "신고를 찾을 수 없습니다.")


_CLOSED_STATUSES = ("resolved", "rejected")


def update_report(db: Session, report_id: int, payload: ReportUpdate) -> Report:
    report = get_report(db, report_id)
    # 처리가 끝난 신고를 다시 열면 재인용 때 제재가 두 번 적용됐다 (resolved -> pending -> resolved).
    if report.status in _CLOSED_STATUSES and payload.status != report.status:
        raise Conflict("처리가 끝난 신고의 상태는 바꿀 수 없습니다.")
    # 같은 상태로 다시 보내면 메모만 고친다 (제재/알림을 반복하지 않는다).
    entering = payload.status if payload.status != report.status else None

    report.status = payload.status
    if payload.admin_memo is not None:
        report.admin_memo = payload.admin_memo

    if entering == "resolved":
        _apply_sanction(db, report)
    if entering in _CLOSED_STATUSES:
        verb = "처리" if entering == "resolved" else "반려"
        notification_service.notify(
            db,
            report.reporter_id,
            f"report_{entering}",
            f"신고(#{report.id})가 {verb}되었습니다.",
            "report",
            report.id,
        )

    return save(db, report)


def _apply_sanction(db: Session, report: Report) -> None:
    """신고가 인용(resolved)되면 대상에 제재를 적용한다 (FR-COM-04)."""
    target = _get_target(db, report.target_type, report.target_id)
    if target is None:
        return

    if report.target_type == "user":
        notification_service.notify(
            db,
            target.id,
            "sanction",
            "회원님에 대한 신고가 인용되었습니다.",
            "user",
            target.id,
        )
        resolved_count = (
            db.query(Report.id)
            .filter(
                Report.target_type == "user",
                Report.target_id == target.id,
                Report.status == "resolved",
            )
            .count()
        ) + 1  # 이번 건 포함
        if resolved_count >= settings.report_auto_deactivate_threshold:
            target.is_active = False
            logger.warning(
                "누적 신고로 계정 비활성화 user_id=%s resolved=%s", target.id, resolved_count
            )
            notification_service.notify(
                db,
                target.id,
                "sanction",
                "누적 신고로 계정이 비활성화되었습니다.",
                "user",
                target.id,
            )
    elif report.target_type in ("item", "skill_item"):
        target.is_deleted = True
        target.status = "closed"
        notification_service.notify(
            db,
            target.seller_id,
            "sanction",
            "신고 인용으로 등록물이 삭제되었습니다.",
            report.target_type,
            target.id,
        )
    elif report.target_type == "review":
        target.is_deleted = True
        db.flush()
        recalc_rating(db, target.target_user_id)
        notification_service.notify(
            db,
            target.author_id,
            "sanction",
            "신고 인용으로 작성한 리뷰가 삭제되었습니다.",
            "review",
            target.id,
        )
