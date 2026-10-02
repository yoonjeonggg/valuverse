"""애플리케이션 로깅 설정 + 요청 로깅 미들웨어.

- 모든 로그 레코드에 요청 ID(`request_id`)를 붙인다. 요청 헤더 `X-Request-ID` 가
  있으면 그대로 쓰고, 없으면 새로 만든다. 응답 헤더에도 같은 값을 돌려준다.
- 요청마다 메서드/경로/상태코드/소요시간/사용자 ID 를 한 줄로 남긴다.
  (uvicorn 기본 access 로그는 이것과 중복되므로 끈다.)
- 처리되지 않은 예외는 스택트레이스와 함께 기록하고 500 JSON 으로 응답한다.
- LOG_FORMAT=json 이면 한 줄 JSON 으로 출력해 수집기(Loki/ELK 등)에 바로 넣을 수 있다.
"""

import json
import logging
import logging.config
import time
import uuid
from contextvars import ContextVar
from datetime import UTC, datetime
from pathlib import Path

from fastapi import Request
from fastapi.responses import JSONResponse

from app.core.config import settings

request_id_var: ContextVar[str] = ContextVar("request_id", default="-")

logger = logging.getLogger("app.request")

_REQUEST_ID_HEADER = "X-Request-ID"
# 상태 확인용 엔드포인트는 호출이 잦아 INFO 로 남기면 로그가 묻힌다.
_QUIET_PATHS = {"/health"}
# 이 시간 이상 걸린 요청은 WARNING 으로 올린다.
_SLOW_REQUEST_MS = 1000

# LogRecord 기본 속성. 이 외의 속성은 `extra=` 로 넘어온 값으로 보고 JSON 에 포함한다.
_RESERVED_ATTRS = set(
    logging.LogRecord("", 0, "", 0, "", None, None).__dict__
) | {"message", "asctime", "request_id"}


class RequestIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_var.get()
        return True


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        data = {
            "time": datetime.fromtimestamp(record.created, UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "request_id": getattr(record, "request_id", "-"),
            "message": record.getMessage(),
        }
        for key, value in record.__dict__.items():
            if key not in _RESERVED_ATTRS and not key.startswith("_"):
                data[key] = value
        if record.exc_info:
            data["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(data, ensure_ascii=False, default=str)


def setup_logging() -> None:
    formatter = "json" if settings.log_format.lower() == "json" else "text"
    handlers: dict = {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": formatter,
            "filters": ["request_id"],
        },
    }
    if settings.log_file:
        Path(settings.log_file).parent.mkdir(parents=True, exist_ok=True)
        handlers["file"] = {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": settings.log_file,
            "maxBytes": settings.log_file_max_bytes,
            "backupCount": settings.log_file_backup_count,
            "encoding": "utf-8",
            "formatter": formatter,
            "filters": ["request_id"],
        }

    logging.config.dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "filters": {"request_id": {"()": RequestIdFilter}},
            "formatters": {
                "text": {
                    "format": "%(asctime)s %(levelname)-7s [%(request_id)s] %(name)s: %(message)s",
                },
                "json": {"()": JsonFormatter},
            },
            "handlers": handlers,
            "root": {"level": settings.log_level.upper(), "handlers": list(handlers)},
            "loggers": {
                # uvicorn 로그도 같은 핸들러/포맷으로 모은다.
                "uvicorn": {"handlers": [], "propagate": True},
                "uvicorn.error": {"handlers": [], "propagate": True},
                # 요청 로그는 미들웨어가 남기므로 기본 access 로그는 끈다.
                "uvicorn.access": {"handlers": [], "propagate": False},
                # True 면 실행되는 SQL 을 모두 남긴다 (개발용).
                "sqlalchemy.engine": {"level": "INFO" if settings.log_sql else "WARNING"},
            },
        }
    )


async def request_logging_middleware(request: Request, call_next):
    request_id = request.headers.get(_REQUEST_ID_HEADER) or uuid.uuid4().hex[:16]
    token = request_id_var.set(request_id)
    start = time.perf_counter()
    try:
        try:
            response = await call_next(request)
        except Exception:
            logger.exception(
                "처리되지 않은 예외: %s %s", request.method, request.url.path
            )
            response = JSONResponse(
                status_code=500,
                content={"detail": "서버 내부 오류가 발생했습니다.", "request_id": request_id},
            )

        elapsed_ms = round((time.perf_counter() - start) * 1000, 1)
        if response.status_code >= 500 or elapsed_ms >= _SLOW_REQUEST_MS:
            level = logging.WARNING
        elif request.url.path in _QUIET_PATHS:
            level = logging.DEBUG
        else:
            level = logging.INFO
        logger.log(
            level,
            "%s %s -> %s (%sms)",
            request.method,
            request.url.path,
            response.status_code,
            elapsed_ms,
            extra={
                "method": request.method,
                "path": request.url.path,
                "status": response.status_code,
                "duration_ms": elapsed_ms,
                # get_current_user 가 인증에 성공하면 채워 둔다.
                "user_id": getattr(request.state, "user_id", None),
                "client_ip": request.client.host if request.client else None,
            },
        )
        response.headers[_REQUEST_ID_HEADER] = request_id
        return response
    finally:
        request_id_var.reset(token)
