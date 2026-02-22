# -*- coding: utf-8 -*-
"""用户认证相关的 Pydantic 模型"""

from typing import Optional
from decimal import Decimal
from pydantic import BaseModel, EmailStr, Field, field_validator


class UserBase(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    phone: Optional[str] = Field(default=None, max_length=11, description="手机号，唯一键，不可修改")
    email: Optional[EmailStr] = None
    nickname: Optional[str] = Field(default=None, max_length=50, description="昵称")
    balance: float = Field(default=0.0, ge=0, description="账户余额（元）")
    total_spent: float = Field(default=0.0, ge=0, description="累计消费（元）")


class ProfileUpdate(BaseModel):
    """更新个人信息（仅允许修改邮箱、昵称）"""
    email: Optional[EmailStr] = None
    nickname: Optional[str] = Field(default=None, max_length=50)


class UserCreate(UserBase):
    password: str = Field(..., min_length=6)


class UserLogin(BaseModel):
    username: str
    password: str


# 手机验证码登录 / 注册
class SendSmsCodeRequest(BaseModel):
    phone: str = Field(..., min_length=11, max_length=11, description="11 位手机号")

    @field_validator("phone")
    @classmethod
    def phone_digits(cls, v: str) -> str:
        if not v.isdigit():
            raise ValueError("手机号须为数字")
        return v


class LoginBySmsRequest(BaseModel):
    phone: str = Field(..., min_length=11, max_length=11, description="11 位手机号")
    code: str = Field(..., min_length=4, max_length=8, description="短信验证码")

    @field_validator("phone")
    @classmethod
    def phone_digits(cls, v: str) -> str:
        if not v.isdigit():
            raise ValueError("手机号须为数字")
        return v


class TokenWithUser(BaseModel):
    """登录成功返回：令牌 + 用户信息（供前端保存）"""
    access_token: str
    token_type: str = "bearer"
    user: UserBase
    need_set_password: bool = Field(default=False, description="首次注册或未设密时需在客户端完成设置密码")


class SetPasswordRequest(BaseModel):
    """首次设置密码（验证码注册后或未设密用户）"""
    password: str = Field(..., min_length=6, description="登录密码，至少6位")


class ChangePasswordRequest(BaseModel):
    """在个人中心修改密码"""
    old_password: str = Field(..., description="当前密码")
    new_password: str = Field(..., min_length=6, description="新密码，至少6位")


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


class UsageRecordResponse(BaseModel):
    """单条调用记录（用于个人中心调用记录列表）"""
    id: str = Field(..., description="记录 ID")
    record_type: str = Field(..., description="类型: image | chat | knowledge")
    type_label: str = Field(..., description="展示名称")
    amount: float = Field(..., ge=0, description="消耗金额（元）")
    count: int = Field(default=1, ge=0)
    created_at: str = Field(..., description="创建时间 ISO 字符串")


class CozeConfigResponse(BaseModel):
    """扣子知识库配置：API Token 与 Space ID（仅当前用户）"""
    coze_api_token: Optional[str] = Field(default=None, description="Coze API Token，未配置时为 null")
    coze_space_id: Optional[str] = Field(default=None, description="Coze Space ID，未配置时为 null")


class CozeConfigUpdate(BaseModel):
    """更新扣子知识库配置（可只传需要更新的字段）"""
    coze_api_token: Optional[str] = Field(default=None, description="Coze API Token")
    coze_space_id: Optional[str] = Field(default=None, description="Coze Space ID")
