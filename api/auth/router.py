import os
from datetime import datetime, timedelta

import jwt
from dotenv import load_dotenv
from fastapi import APIRouter, Depends, HTTPException, status
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from api.auth.models import (
    AllUsersResponse,
    LoginRequest,
    RegisterRequest,
    TokenResponse,
    UpdateUserRequest,
    UserResponse,
    UserStatisticsResponse,
    UserWithStatisticsResponse,
)
from db.database import get_db
from db.models import User, UserStatistics, UserType
from middlewares.auth import admin_only_middleware, auth_middleware

load_dotenv()

router = APIRouter(prefix="/auth")
password_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

JWT_SECRET = os.getenv("JWT_SECRET")
if not JWT_SECRET:
    raise RuntimeError("JWT_SECRET environment variable not set")


def create_user_response(user: User) -> UserResponse:
    return UserResponse(
        id=str(user.id),
        email=user.email,
        nickname=user.nickname,
        created_at=str(user.created_at),
        updated_at=str(user.updated_at),
        type=user.type,
    )


def create_user_statistics_response(stats: UserStatistics) -> UserStatisticsResponse:
    return UserStatisticsResponse(
        knowledge_base_search_count=stats.knowledge_base_search_count,
        ocr_recognition_count=stats.ocr_recognition_count,
        conversation_count=stats.conversation_count,
        flow_chart_count=stats.flow_chart_count,
        mind_map_count=stats.mind_map_count,
    )


def generate_jwt_token(user_id: str) -> str:
    return jwt.encode(
        {"sub": user_id, "exp": datetime.now() + timedelta(days=30)},
        JWT_SECRET,
        algorithm="HS256",
    )


@router.post("/register", response_model=TokenResponse)
async def register(account: RegisterRequest, db: Session = Depends(get_db)):
    if len(account.password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 8 characters long",
        )

    if db.query(User).filter(User.email == account.email).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    try:
        user = User(
            email=account.email,
            password_hash=password_context.hash(account.password),
            nickname=account.nickname,
            type=UserType.user,
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        user_stats = UserStatistics(user_id=user.id)
        db.add(user_stats)
        db.commit()

        token = generate_jwt_token(str(user.id))
        return TokenResponse(
            token=token,
            user=create_user_response(user),
        )

    except Exception as e:
        print(e, flush=True)
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )


@router.post("/login", response_model=TokenResponse)
async def login(account: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == account.email).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    if not password_context.verify(account.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    token = generate_jwt_token(str(user.id))
    return TokenResponse(
        token=token,
        user=create_user_response(user),
    )


@router.get("/me", response_model=UserResponse)
async def get_current_user(
    db: Session = Depends(get_db), user: User = Depends(auth_middleware)
):
    return create_user_response(user)


@router.put("/me", response_model=UserResponse)
async def update_user(
    user_data: UpdateUserRequest,
    db: Session = Depends(get_db),
    user: User = Depends(auth_middleware),
):
    if user_data.password and len(user_data.password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 8 characters long",
        )
    try:
        if user_data.nickname:
            user.nickname = user_data.nickname
        if user_data.email:
            existing_user = (
                db.query(User)
                .filter(User.email == user_data.email, User.id != user.id)
                .first()
            )
            if existing_user:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Email already registered",
                )
            user.email = user_data.email
        if user_data.password:
            user.password_hash = password_context.hash(user_data.password)
        db.commit()
        db.refresh(user)
        return create_user_response(user)
    except HTTPException:
        raise
    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )


@router.get("/statistics", response_model=UserStatisticsResponse)
async def get_user_statistics(
    db: Session = Depends(get_db), user: User = Depends(auth_middleware)
):
    user_stats = (
        db.query(UserStatistics).filter(UserStatistics.user_id == user.id).first()
    )
    return UserStatisticsResponse(
        knowledge_base_search_count=user_stats.knowledge_base_search_count,
        ocr_recognition_count=user_stats.ocr_recognition_count,
        conversation_count=user_stats.conversation_count,
        flow_chart_count=user_stats.flow_chart_count,
        mind_map_count=user_stats.mind_map_count,
    )


@router.get("/", response_model=AllUsersResponse)
async def get_all_users(
    db: Session = Depends(get_db), _: None = Depends(admin_only_middleware)
):
    users = db.query(User).all()
    result = []
    
    for user in users:
        user_stats = db.query(UserStatistics).filter(UserStatistics.user_id == user.id).first()
        if not user_stats:
            user_stats = UserStatistics(user_id=user.id)
            db.add(user_stats)
            db.commit()
            db.refresh(user_stats)
            
        user_with_stats = UserWithStatisticsResponse(
            user=create_user_response(user),
            statistics=create_user_statistics_response(user_stats)
        )
        result.append(user_with_stats)
    
    return AllUsersResponse(users=result)