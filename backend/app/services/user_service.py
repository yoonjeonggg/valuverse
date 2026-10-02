import logging

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.db_utils import commit_or_conflict, get_or_404, save
from app.core.security import hash_password, verify_password
from app.models.user import User
from app.schemas.user import SignupRequest, UserUpdateRequest

logger = logging.getLogger(__name__)


def get_user_by_email(db: Session, email: str) -> User | None:
    return db.query(User).filter(User.email == email).first()


def get_user(db: Session, user_id: int) -> User:
    return get_or_404(db, User, user_id, "사용자를 찾을 수 없습니다.")


def create_user(db: Session, payload: SignupRequest) -> User:
    if get_user_by_email(db, payload.email):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="이미 가입된 이메일입니다.",
        )

    user = User(
        email=payload.email,
        password_hash=hash_password(payload.password),
        nickname=payload.nickname,
        points=0,
    )
    db.add(user)
    # 같은 이메일로 동시에 가입하면 위 확인을 둘 다 통과할 수 있다 -> UNIQUE 위반을 409로.
    commit_or_conflict(db, "이미 가입된 이메일입니다.")
    db.refresh(user)
    logger.info("회원가입 user_id=%s", user.id)
    return user


def authenticate_user(db: Session, email: str, password: str) -> User | None:
    user = get_user_by_email(db, email)
    if not user or not verify_password(password, user.password_hash):
        return None
    if not user.is_active:
        return None
    return user


def update_user(db: Session, user: User, payload: UserUpdateRequest) -> User:
    if payload.nickname is not None:
        user.nickname = payload.nickname
    if payload.profile_image is not None:
        user.profile_image = payload.profile_image
    if payload.password is not None:
        # 토큰만 탈취당해도 비밀번호까지 바꿔 계정을 빼앗기지 않도록 현재 비밀번호를 확인한다.
        if not payload.current_password or not verify_password(
            payload.current_password, user.password_hash
        ):
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST, "현재 비밀번호가 일치하지 않습니다."
            )
        user.password_hash = hash_password(payload.password)
    return save(db, user)


def deactivate_user(db: Session, user: User) -> None:
    """회원 탈퇴 - 소프트 삭제."""
    user.is_active = False
    db.commit()
