from typing import Optional

from pydantic import BaseModel, EmailStr

from db.models import UserType


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    nickname: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: str
    email: EmailStr
    nickname: str
    created_at: str
    updated_at: str
    type: UserType


class TokenResponse(BaseModel):
    token: str
    user: UserResponse


class UpdateUserRequest(BaseModel):
    nickname: Optional[str] = None
    email: Optional[EmailStr] = None
    password: Optional[str] = None
