# -*- coding: utf-8 -*-
"""用户认证路由：注册、登录、当前用户"""

import logging
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
import jwt

from app.config import settings
from app.schemas.auth import UserCreate, UserLogin, Token, TokenData, UserBase
from app.services.auth_utils import get_password_hash, verify_password, create_access_token
from app.services.database import db

logger = logging.getLogger(__name__)
router = APIRouter()

# 定义 OAuth2 方案
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


async def get_current_user(token: str = Depends(oauth2_scheme)):
    """获取当前登录用户的依赖项"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
    except jwt.PyJWTError:
        raise credentials_exception
    
    user = await db.db.users.find_one({"username": token_data.username})
    if user is None:
        raise credentials_exception
    return UserBase(**user)


@router.post("/register", response_model=UserBase, summary="用户注册")
async def register(user_in: UserCreate):
    """注册新用户"""
    # 检查用户是否已存在
    existing_user = await db.db.users.find_one({
        "$or": [
            {"username": user_in.username},
            {"email": user_in.email} if user_in.email else {"_id": None}
        ]
    })
    if existing_user:
        raise HTTPException(
            status_code=400,
            detail="Username or email already registered"
        )
    
    # 准备写入数据
    user_dict = user_in.dict()
    user_dict["hashed_password"] = get_password_hash(user_dict.pop("password"))
    
    # 写入数据库
    await db.db.users.insert_one(user_dict)
    logger.info("New user registered: %s", user_in.username)
    
    return UserBase(**user_dict)


@router.post("/login", response_model=Token, summary="用户登录 (OAuth2 兼容)")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """登录并返回 JWT 访问令牌"""
    user = await db.db.users.find_one({"username": form_data.username})
    if not user or not verify_password(form_data.password, user["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user["username"]}, expires_delta=access_token_expires
    )
    
    logger.info("User logged in: %s", user["username"])
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/me", response_model=UserBase, summary="获取当前用户信息")
async def read_users_me(current_user: UserBase = Depends(get_current_user)):
    """获取当前已验证用户的信息"""
    return current_user
