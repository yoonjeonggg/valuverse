from fastapi import APIRouter, HTTPException, status

from app.core.deps import CurrentUser, DbSession
from app.core.security import create_access_token
from app.schemas.user import (
    LoginRequest,
    PublicProfileResponse,
    SignupRequest,
    TokenResponse,
    UserResponse,
    UserUpdateRequest,
)
from app.services import dashboard_service, user_service

auth_router = APIRouter(prefix="/auth", tags=["Auth"])
user_router = APIRouter(prefix="/users", tags=["User"])


@auth_router.post("/signup", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def signup(payload: SignupRequest, db: DbSession):
    return user_service.create_user(db, payload)


@auth_router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: DbSession):
    user = user_service.authenticate_user(db, payload.email, payload.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="이메일 또는 비밀번호가 올바르지 않습니다.",
        )
    token = create_access_token(subject=user.email)
    return TokenResponse(access_token=token)


@user_router.get("/me", response_model=UserResponse)
def get_my_info(current_user: CurrentUser):
    return current_user


@user_router.get("/me/dashboard")
def get_my_dashboard(current_user: CurrentUser, db: DbSession):
    return dashboard_service.get_dashboard(db, current_user)


@user_router.patch("/me", response_model=UserResponse)
def update_my_info(
    payload: UserUpdateRequest,
    current_user: CurrentUser,
    db: DbSession,
):
    return user_service.update_user(db, current_user, payload)


@user_router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
def delete_my_account(current_user: CurrentUser, db: DbSession):
    user_service.deactivate_user(db, current_user)


@user_router.get("/{user_id}", response_model=PublicProfileResponse)
def get_user_profile(user_id: int, db: DbSession):
    return user_service.get_user(db, user_id)
