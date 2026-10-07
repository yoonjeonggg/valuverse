from datetime import UTC, datetime


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
