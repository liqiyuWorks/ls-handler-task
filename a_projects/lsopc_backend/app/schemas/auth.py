# -*- coding: utf-8 -*-
"""用户认证相关的 Pydantic 模型"""

from typing import Optional
from pydantic import BaseModel, EmailStr, Field


class UserBase(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: Optional[EmailStr] = None


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
