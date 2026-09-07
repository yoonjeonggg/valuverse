from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field

from app.schemas.common import ORMModel


class SignupRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=64)
    nickname: str = Field(min_length=2, max_length=20)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserUpdateRequest(BaseModel):
    nickname: Optional[str] = Field(default=None, min_length=2, max_length=20)
    profile_image: Optional[str] = Field(default=None, max_length=500)
    password: Optional[str] = Field(default=None, min_length=8, max_length=64)


class UserResponse(ORMModel):
    id: int
    email: EmailStr
    nickname: str
    profile_image: Optional[str] = None
    points: int
    rating: float
    created_at: datetime


class PublicProfileResponse(ORMModel):
    id: int
    nickname: str
    profile_image: Optional[str] = None
    rating: float


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
