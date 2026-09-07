from datetime import datetime, timezone


def now() -> datetime:
    return datetime.now(timezone.utc)


def aware(dt: datetime | None) -> datetime | None:
    """SQLite 는 tzinfo 를 저장하지 않으므로 naive 값을 UTC 로 간주한다."""
    if dt is None:
        return None
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)


def is_past(dt: datetime | None) -> bool:
    a = aware(dt)
    return a is not None and a <= now()
