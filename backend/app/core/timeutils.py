from datetime import UTC, datetime

from app.core.errors import BadRequest


def now() -> datetime:
    return datetime.now(UTC)


def aware(dt: datetime | None) -> datetime | None:
    """SQLite 는 tzinfo 를 저장하지 않으므로 naive 값을 UTC 로 간주한다."""
    if dt is None:
        return None
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=UTC)


def is_past(dt: datetime | None) -> bool:
    a = aware(dt)
    return a is not None and a <= now()


def iso(dt: datetime | None) -> str | None:
    return dt.isoformat() if dt else None


def require_future(dt: datetime | None, field: str = "마감 시간") -> None:
    """마감 시간처럼 미래여야 하는 값이 지났으면 400. None 은 '변경 없음'으로 보고 통과."""
    if is_past(dt):
        raise BadRequest(f"{field}은 현재 이후여야 합니다.")
