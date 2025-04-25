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


class UserStatisticsResponse(BaseModel):
    conversation_count: int
    ocr_recognition_count: int
    knowledge_base_search_count: int
    flow_chart_count: int
    mind_map_count: int


class UserWithStatisticsResponse(BaseModel):
    user: UserResponse
    statistics: UserStatisticsResponse
    
    
class AllUsersResponse(BaseModel):
    users: list[UserWithStatisticsResponse]
