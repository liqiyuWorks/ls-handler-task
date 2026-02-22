# -*- coding: utf-8 -*-
"""用户认证路由：注册、登录、手机验证码登录/注册、当前用户"""

import logging
import random
from datetime import datetime, timedelta

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
    SendSmsCodeRequest,
    LoginBySmsRequest,
    TokenWithUser,
    SetPasswordRequest,
    ChangePasswordRequest,
)
from app.services.auth_utils import get_password_hash, verify_password, create_access_token
from app.services.database import db
from app.services.sms_service import send_sms_code
from app.utils.time_utils import utc_iso_for_api

logger = logging.getLogger(__name__)
router = APIRouter()

# 短信验证码内存存储：phone -> {"code": str, "expires_at": datetime}
_sms_code_store: dict[str, dict] = {}

# 定义 OAuth2 方案
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


async def get_current_user(token: str = Depends(oauth2_scheme)):
    """获取当前登录用户。JWT sub 为手机号或用户名（历史），按手机号/用户名查找用户。"""
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
        sub: str = payload.get("sub")
        if not sub:
            raise credentials_exception
    except jwt.ExpiredSignatureError:
        raise expired_exception
    except jwt.PyJWTError:
        raise credentials_exception

    user = await db.db.users.find_one({"$or": [{"phone": sub}, {"username": sub}]})
    if user is None:
        raise credentials_exception
    # 对外统一用 username 字段表示唯一标识（手机号或历史用户名），便于现有逻辑复用
    display_id = user.get("phone") or user.get("username")
    user_data = {
        "username": display_id,
        "phone": user.get("phone"),
        "email": user.get("email"),
        "nickname": user.get("nickname"),
        "balance": float(user.get("balance", 0)),
        "total_spent": float(user.get("total_spent", 0)),
    }
    return UserBase(**user_data)


@router.post("/register", summary="用户注册（已废弃，仅支持手机验证码注册）")
async def register(user_in: UserCreate):
    """已废弃：仅支持手机验证码登录/注册，请使用 POST /auth/send-sms-code 与 POST /auth/login-by-sms"""
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="仅支持手机验证码注册，请使用验证码登录/注册",
    )


def _sms_set_code(phone: str, code: str) -> None:
    now = datetime.utcnow()
    _sms_code_store[phone] = {
        "code": code,
        "expires_at": now + timedelta(seconds=settings.SMS_CODE_EXPIRE_SECONDS),
        "sent_at": now,
    }


def _sms_verify_code(phone: str, code: str) -> bool:
    entry = _sms_code_store.get(phone)
    if not entry:
        return False
    if datetime.utcnow() > entry["expires_at"]:
        del _sms_code_store[phone]
        return False
    if entry["code"] != code:
        return False
    del _sms_code_store[phone]
    return True


@router.post("/send-sms-code", summary="发送短信验证码")
async def api_send_sms_code(body: SendSmsCodeRequest):
    """向手机号发送 6 位验证码，用于验证码登录/注册。同一手机号 60 秒内仅可请求一次。"""
    phone = body.phone
    now = datetime.utcnow()
    entry = _sms_code_store.get(phone)
    if entry and (now - entry["sent_at"]).total_seconds() < 60:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="请 60 秒后再获取验证码")
    code = "".join(str(random.randint(0, 9)) for _ in range(6))
    _sms_set_code(phone, code)
    if not send_sms_code(phone, code):
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="验证码发送失败，请稍后重试")
    return {"ok": True, "message": "验证码已发送"}


@router.post("/login-by-sms", response_model=TokenWithUser, summary="手机验证码登录/注册")
async def login_by_sms(body: LoginBySmsRequest):
    """验证码正确则登录；若该手机号未注册则自动注册（需随后设置密码）。返回 need_set_password 时前端需引导设置密码。"""
    if not _sms_verify_code(body.phone, body.code):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="验证码错误或已过期，请重新获取",
        )
    phone = body.phone
    user = await db.db.users.find_one({"$or": [{"phone": phone}, {"username": phone}]})
    if not user:
        user_dict = {
            "username": phone,
            "phone": phone,
            "balance": 0.0,
            "total_spent": 0.0,
        }
        await db.db.users.insert_one(user_dict)
        logger.info("New user registered by phone: %s", phone)
        user = user_dict
    else:
        if not user.get("phone"):
            await db.db.users.update_one({"_id": user["_id"]}, {"$set": {"phone": phone}})
    display_id = user.get("phone") or user.get("username")
    user_data = {
        "username": display_id,
        "phone": user.get("phone"),
        "email": user.get("email"),
        "nickname": user.get("nickname"),
        "balance": float(user.get("balance", 0)),
        "total_spent": float(user.get("total_spent", 0)),
    }
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    sub = user.get("phone") or user.get("username")
    access_token = create_access_token(
        data={"sub": sub}, expires_delta=access_token_expires
    )
    need_set_password = not bool(user.get("hashed_password"))
    logger.info("User logged in by SMS: %s need_set_password=%s", sub, need_set_password)
    return TokenWithUser(
        access_token=access_token,
        token_type="bearer",
        user=UserBase(**user_data),
        need_set_password=need_set_password,
    )


@router.post("/login", response_model=TokenWithUser, summary="手机号+密码登录")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """使用手机号（或用户名）与密码登录，减少验证码发送。"""
    phone_or_username = (form_data.username or "").strip()
    if not phone_or_username or not form_data.password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="请输入手机号和密码",
        )
    user = await db.db.users.find_one({"$or": [{"phone": phone_or_username}, {"username": phone_or_username}]})
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="手机号或密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.get("hashed_password"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="该账号尚未设置密码，请使用验证码登录后设置",
        )
    if not verify_password(form_data.password, user["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="手机号或密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )
    display_id = user.get("phone") or user.get("username")
    user_data = {
        "username": display_id,
        "phone": user.get("phone"),
        "email": user.get("email"),
        "nickname": user.get("nickname"),
        "balance": float(user.get("balance", 0)),
        "total_spent": float(user.get("total_spent", 0)),
    }
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": display_id}, expires_delta=access_token_expires
    )
    logger.info("User logged in by password: %s", display_id)
    return TokenWithUser(
        access_token=access_token,
        token_type="bearer",
        user=UserBase(**user_data),
        need_set_password=False,
    )


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
        {"$or": [{"phone": current_user.username}, {"username": current_user.username}]},
        {"$set": update_data},
        return_document=ReturnDocument.AFTER,
    )
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")
    display_id = updated.get("phone") or updated.get("username")
    user_data = {
        "username": display_id,
        "phone": updated.get("phone"),
        "email": updated.get("email"),
        "nickname": updated.get("nickname"),
        "balance": float(updated.get("balance", 0)),
        "total_spent": float(updated.get("total_spent", 0)),
    }
    return UserBase(**user_data)


@router.patch("/me/set-password", response_model=UserBase, summary="首次设置密码")
async def set_password(
    body: SetPasswordRequest,
    current_user: UserBase = Depends(get_current_user),
):
    """验证码注册后或未设密用户，设置登录密码。仅当当前账号无密码时可调用。"""
    user = await db.db.users.find_one(
        {"$or": [{"phone": current_user.username}, {"username": current_user.username}]}
    )
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")
    if user.get("hashed_password"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="已设置过密码，请使用「修改密码」")
    hashed = get_password_hash(body.password)
    updated = await db.db.users.find_one_and_update(
        {"$or": [{"phone": current_user.username}, {"username": current_user.username}]},
        {"$set": {"hashed_password": hashed}},
        return_document=ReturnDocument.AFTER,
    )
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")
    display_id = updated.get("phone") or updated.get("username")
    user_data = {
        "username": display_id,
        "phone": updated.get("phone"),
        "email": updated.get("email"),
        "nickname": updated.get("nickname"),
        "balance": float(updated.get("balance", 0)),
        "total_spent": float(updated.get("total_spent", 0)),
    }
    logger.info("User set password: %s", display_id)
    return UserBase(**user_data)


@router.patch("/me/change-password", response_model=UserBase, summary="修改密码")
async def change_password(
    body: ChangePasswordRequest,
    current_user: UserBase = Depends(get_current_user),
):
    """在个人中心修改登录密码，需校验当前密码。"""
    user = await db.db.users.find_one(
        {"$or": [{"phone": current_user.username}, {"username": current_user.username}]}
    )
    if not user or not user.get("hashed_password"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="请先设置密码")
    if not verify_password(body.old_password, user["hashed_password"]):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="当前密码错误")
    hashed = get_password_hash(body.new_password)
    updated = await db.db.users.find_one_and_update(
        {"$or": [{"phone": current_user.username}, {"username": current_user.username}]},
        {"$set": {"hashed_password": hashed}},
        return_document=ReturnDocument.AFTER,
    )
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")
    display_id = updated.get("phone") or updated.get("username")
    user_data = {
        "username": display_id,
        "phone": updated.get("phone"),
        "email": updated.get("email"),
        "nickname": updated.get("nickname"),
        "balance": float(updated.get("balance", 0)),
        "total_spent": float(updated.get("total_spent", 0)),
    }
    logger.info("User change password: %s", display_id)
    return UserBase(**user_data)


# 调用记录集合名
USAGE_RECORDS_COLLECTION = "usage_records"


@router.get("/records", response_model=list[UsageRecordResponse], summary="获取当前用户调用记录")
async def get_usage_records(
    current_user: UserBase = Depends(get_current_user),
    limit: int = 50,
    offset: int = 0,
):
    """分页返回当前用户的调用记录，按时间倒序。统一按手机号匹配，兼容仅含 username 的历史记录。"""
    if limit < 1 or limit > 100:
        limit = 50
    if offset < 0:
        offset = 0
    user_doc = await db.db.users.find_one(
        {"$or": [{"phone": current_user.username}, {"username": current_user.username}]}
    )
    identifiers = [current_user.username]
    if user_doc:
        for key in ("username", "phone"):
            v = user_doc.get(key)
            if v and v not in identifiers:
                identifiers.append(v)
    phone_values = [v for v in identifiers if v and len(v) == 11 and v.isdigit()]
    if not phone_values and getattr(current_user, "phone", None):
        phone_values = [current_user.phone]
    if phone_values:
        query = {"$or": [{"phone": {"$in": phone_values}}, {"username": {"$in": identifiers}}]}
    else:
        query = {"username": {"$in": identifiers}}
    cursor = (
        db.db[USAGE_RECORDS_COLLECTION]
        .find(query)
        .sort("created_at", -1)
        .skip(offset)
        .limit(limit)
    )
    items = []
    async for doc in cursor:
        created_at = utc_iso_for_api(doc.get("created_at"))
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
            {"$or": [{"phone": current_user.username}, {"username": current_user.username}]},
            {"$set": {"balance": 0.0}},
        )
        new_balance = 0.0

    logger.info("Recharge: user=%s, added=%.2f, balance_after=%.2f", current_user.username, amount, new_balance)
    return RechargeResponse(balance=new_balance, added=amount)
