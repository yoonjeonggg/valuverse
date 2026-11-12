from typing import Annotated

from fastapi import Depends, Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.errors import Forbidden, Unauthorized
from app.core.security import decode_access_token
from app.database import get_db
from app.models.user import User

# auto_error=False: 토큰이 없을 때 FastAPI 기본 영문 메시지("Not authenticated") 대신
# get_current_user 가 한국어 메시지로 401 을 낸다.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)


def lookup_user_by_token(db: Session, token: str | None) -> User | None:
    """토큰을 디코드해 사용자를 조회한다 (활성 여부는 호출자가 판단). HTTP/WS 인증 공용."""
    if not token:
        return None
    email = decode_access_token(token)
    if not email:
        return None
    return db.query(User).filter(User.email == email).first()


# 라우터 시그니처용 별칭. `db: DbSession, user: CurrentUser` 처럼 쓴다.
DbSession = Annotated[Session, Depends(get_db)]


def get_current_user(
    request: Request,
    token: Annotated[str | None, Depends(oauth2_scheme)],
    db: DbSession,
) -> User:
    if not token:
        raise Unauthorized("로그인이 필요합니다.")
    user = lookup_user_by_token(db, token)
    if user is None:
        raise Unauthorized("인증 정보가 유효하지 않습니다.")

    if not user.is_active:
        raise Forbidden("비활성화된 계정입니다.")

    # 요청 로그에 누가 호출했는지 남기기 위해 기록 (logging_setup 미들웨어가 읽는다).
    request.state.user_id = user.id
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def get_current_admin(current_user: CurrentUser) -> User:
    if not current_user.is_admin:
        raise Forbidden("관리자 권한이 필요합니다.")
    return current_user


CurrentAdmin = Annotated[User, Depends(get_current_admin)]
