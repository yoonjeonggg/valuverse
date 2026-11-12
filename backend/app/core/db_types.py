from datetime import UTC, datetime

from sqlalchemy import DateTime
from sqlalchemy.types import TypeDecorator


class UTCDateTime(TypeDecorator):
    """항상 UTC aware datetime 으로 읽고 쓰는 DateTime.

    SQLite 는 tzinfo 를 저장하지 않아 읽은 값이 naive 가 되고, 응답 JSON 에 타임존 표기
    없이("2026-11-12T06:20:00") 나가면 브라우저가 로컬 시각으로 해석해 KST 에서 9시간 어긋났다.
    저장할 때 UTC 로 바꾸고, 읽을 때 naive 값을 UTC 로 간주해 DB 종류와 무관하게 같은 값을 준다.
    """

    impl = DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(self, value: datetime | None, dialect):
        if value is not None and value.tzinfo is not None:
            value = value.astimezone(UTC)
            if dialect.name == "sqlite":
                value = value.replace(tzinfo=None)
        return value

    def process_result_value(self, value: datetime | None, dialect):
        if value is not None and value.tzinfo is None:
            value = value.replace(tzinfo=UTC)
        return value
