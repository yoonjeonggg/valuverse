"""API 에러 응답용 예외.

서비스/라우터는 상태코드를 직접 고르는 대신 의미에 맞는 예외를 던진다.
모두 HTTPException 을 상속하므로 FastAPI 가 그대로 `{"detail": message}` 로 응답한다.

    raise Conflict("이미 정산된 명제입니다.")
"""

from fastapi import HTTPException, status


class ApiError(HTTPException):
    status_code: int = status.HTTP_400_BAD_REQUEST

    def __init__(self, message: str, headers: dict[str, str] | None = None) -> None:
        super().__init__(status_code=self.status_code, detail=message, headers=headers)


class BadRequest(ApiError):
    """요청 값은 형식상 맞지만 업무 규칙상 처리할 수 없음 (잔액 부족, 금액 미달 등)."""

    status_code = status.HTTP_400_BAD_REQUEST


class Unauthorized(ApiError):
    """인증 정보가 없거나 유효하지 않음."""

    status_code = status.HTTP_401_UNAUTHORIZED

    def __init__(self, message: str) -> None:
        super().__init__(message, headers={"WWW-Authenticate": "Bearer"})


class Forbidden(ApiError):
    """인증은 됐지만 권한이 없음."""

    status_code = status.HTTP_403_FORBIDDEN


class NotFound(ApiError):
    """없거나, 남의 리소스라 존재를 드러내지 않음."""

    status_code = status.HTTP_404_NOT_FOUND


class Conflict(ApiError):
    """현재 상태와 충돌 (이미 처리됨, 마감됨, 동시 요청 중복 등)."""

    status_code = status.HTTP_409_CONFLICT


class TooManyRequests(ApiError):
    status_code = status.HTTP_429_TOO_MANY_REQUESTS
