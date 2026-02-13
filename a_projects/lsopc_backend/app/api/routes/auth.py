# -*- coding: utf-8 -*-
"""用户认证路由：注册、登录、当前用户"""

import logging
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
import jwt

from pymongo import ReturnDocument

from app.config import settings
from app.schemas.auth import (
    UserCreate,
    UserLogin,
    Token,
    TokenData,
    UserBase,
    ProfileUpdate,
    RechargeRequest,
    RechargeResponse,
    UsageRecordResponse,
)
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
        detail="请登录",
        headers={"WWW-Authenticate": "Bearer"},
    )
    expired_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="请登录",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
    except jwt.ExpiredSignatureError:
        raise expired_exception
    except jwt.PyJWTError:
        raise credentials_exception

    user = await db.db.users.find_one({"username": token_data.username})
    if user is None:
        raise credentials_exception
    # 只取前端需要的字段，避免 _id/hashed_password 等传入模型
    user_data = {
        "username": user["username"],
        "email": user.get("email"),
        "nickname": user.get("nickname"),
        "balance": float(user.get("balance", 0)),
        "total_spent": float(user.get("total_spent", 0)),
    }
    return UserBase(**user_data)


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
    
    # 准备写入数据（排除 password，单独写入 hashed_password）
    user_dict = user_in.model_dump(exclude={"password"})
    user_dict["hashed_password"] = get_password_hash(user_in.password)
    user_dict["balance"] = 0.0  # 新用户默认余额 0 元
    user_dict["total_spent"] = 0.0  # 新用户累计消费 0 元

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


@router.get("/me", response_model=UserBase, summary="获取当前用户个人信息与账户余额")
async def read_users_me(current_user: UserBase = Depends(get_current_user)):
    """获取当前登录用户的个人信息和账户余额，新注册用户默认余额为 0 元"""
    return current_user


@router.patch("/me", response_model=UserBase, summary="更新当前用户个人信息")
async def update_profile(
    body: ProfileUpdate,
    current_user: UserBase = Depends(get_current_user),
):
    """仅允许更新邮箱、昵称；用户名不可修改"""
    update_data = body.model_dump(exclude_unset=True)
    if not update_data:
        return current_user
    updated = await db.db.users.find_one_and_update(
        {"username": current_user.username},
        {"$set": update_data},
        return_document=ReturnDocument.AFTER,
    )
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")
    user_data = {
        "username": updated["username"],
        "email": updated.get("email"),
        "nickname": updated.get("nickname"),
        "balance": float(updated.get("balance", 0)),
        "total_spent": float(updated.get("total_spent", 0)),
    }
    return UserBase(**user_data)


# 调用记录集合名
USAGE_RECORDS_COLLECTION = "usage_records"


@router.get("/records", response_model=list[UsageRecordResponse], summary="获取当前用户调用记录")
async def get_usage_records(
    current_user: UserBase = Depends(get_current_user),
    limit: int = 50,
    offset: int = 0,
):
    """分页返回当前用户的调用记录，按时间倒序"""
    if limit < 1 or limit > 100:
        limit = 50
    if offset < 0:
        offset = 0
    cursor = (
        db.db[USAGE_RECORDS_COLLECTION]
        .find({"username": current_user.username})
        .sort("created_at", -1)
        .skip(offset)
        .limit(limit)
    )
    items = []
    async for doc in cursor:
        created_at = doc.get("created_at")
        if hasattr(created_at, "isoformat"):
            created_at = created_at.isoformat()
        else:
            created_at = str(created_at) if created_at else ""
        items.append(
            UsageRecordResponse(
                id=str(doc.get("_id", "")),
                record_type=doc.get("record_type", "image"),
                type_label=doc.get("type_label", "图片生成"),
                amount=float(doc.get("amount", 0)),
                count=int(doc.get("count", 1)),
                created_at=created_at,
            )
        )
    return items


@router.post("/recharge", response_model=RechargeResponse, summary="账户充值")
async def recharge(
    body: RechargeRequest,
    current_user: UserBase = Depends(get_current_user),
):
    """
    为当前登录用户充值。金额与用户绑定，使用数据库原子操作保证总金额一致。
    金额单位：元，保留两位小数；单笔充值范围 0.01～100000 元。
    """
    amount = body.amount  # 已在 RechargeRequest 中校验并保留两位小数

    # 原子更新：仅对当前用户 $inc balance，并返回更新后的文档，保证总金额一致
    updated = await db.db.users.find_one_and_update(
        {"username": current_user.username},
        {"$inc": {"balance": amount}},
        return_document=ReturnDocument.AFTER,
    )
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")

    new_balance = round(float(updated.get("balance", 0)), 2)
    # 防止并发或历史数据导致余额为负，做一次兜底校正
    if new_balance < 0:
        await db.db.users.update_one(
            {"username": current_user.username},
            {"$set": {"balance": 0.0}},
        )
        new_balance = 0.0

    logger.info("Recharge: user=%s, added=%.2f, balance_after=%.2f", current_user.username, amount, new_balance)
    return RechargeResponse(balance=new_balance, added=amount)
