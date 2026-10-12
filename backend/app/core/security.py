import warnings
from datetime import UTC, datetime, timedelta

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

_DEFAULT_SECRET_KEY = "dev-secret-change-me"  # noqa: S105 - config 기본값과 같아야 한다


def warn_if_default_secret(secret_key: str) -> bool:
    """기본 SECRET_KEY 로 뜨면 경고한다 (토큰 위조 가능). 경고했으면 True."""
    if secret_key != _DEFAULT_SECRET_KEY:
        return False
    warnings.warn(
        "SECRET_KEY 가 기본값입니다. 운영 환경에서는 .env 에 SECRET_KEY 를 설정하세요.",
        stacklevel=2,
    )
    return True


warn_if_default_secret(settings.secret_key)


def hash_password(plain_password: str) -> str:
    return pwd_context.hash(plain_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(subject: str) -> str:
    expire = datetime.now(UTC) + timedelta(minutes=settings.access_token_expire_minutes)
    payload = {"sub": subject, "exp": expire}
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


def decode_access_token(token: str) -> str | None:
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        return payload.get("sub")
    except JWTError:
        return None
