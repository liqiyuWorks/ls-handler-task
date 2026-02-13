# -*- coding: utf-8 -*-
"""用户认证相关的 Pydantic 模型"""

from typing import Optional
from decimal import Decimal
from pydantic import BaseModel, EmailStr, Field, field_validator


class UserBase(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: Optional[EmailStr] = None
    balance: float = Field(default=0.0, ge=0, description="账户余额（元）")
    total_spent: float = Field(default=0.0, ge=0, description="累计消费（元）")


class UserCreate(UserBase):
    password: str = Field(..., min_length=6)


class UserLogin(BaseModel):
    username: str
    password: str


class UserInDB(UserBase):
    hashed_password: str


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: Optional[str] = None


# 单笔充值上限 10 万元，金额保留 2 位小数
RECHARGE_AMOUNT_MIN = 0.01
RECHARGE_AMOUNT_MAX = 100_000.00


class RechargeRequest(BaseModel):
    """充值请求：金额单位元，保留两位小数"""
    amount: float = Field(..., gt=0, description="充值金额（元）")

    @field_validator("amount")
    @classmethod
    def amount_rounded(cls, v: float) -> float:
        """限制精度并校验范围，保证金额稳定正确"""
        if v < RECHARGE_AMOUNT_MIN or v > RECHARGE_AMOUNT_MAX:
            raise ValueError(f"充值金额须在 {RECHARGE_AMOUNT_MIN}～{RECHARGE_AMOUNT_MAX} 元之间")
        return round(float(Decimal(str(v)).quantize(Decimal("0.01"))), 2)


class RechargeResponse(BaseModel):
    """充值成功响应：返回当前用户最新余额"""
    balance: float = Field(..., ge=0, description="充值后账户余额（元）")
    added: float = Field(..., ge=0, description="本次充值金额（元）")
