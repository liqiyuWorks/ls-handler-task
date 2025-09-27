#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
用户认证模块
"""

from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from models import User, TokenData
import os

# JWT配置
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-here-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# 密码加密
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2方案
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码"""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """生成密码哈希"""
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """创建访问令牌"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_token(token: str, credentials_exception):
    """验证令牌"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
    except JWTError:
        raise credentials_exception
    return token_data

def get_user_by_username(db: Session, username: str) -> Optional[User]:
    """根据用户名获取用户"""
    return db.query(User).filter(User.username == username).first()

def get_user_by_email(db: Session, email: str) -> Optional[User]:
    """根据邮箱获取用户"""
    return db.query(User).filter(User.email == email).first()

def authenticate_user(db: Session, username: str, password: str) -> Optional[User]:
    """验证用户"""
    try:
        user = get_user_by_username(db, username)
        if not user:
            return None
        if not user.check_password(password):
            return None
        return user
    except Exception as e:
        print(f"Authenticate user error: {e}")
        return None

def get_current_user_dependency():
    """获取当前用户依赖（延迟导入避免循环依赖）"""
    from database import get_db
    
    def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
        """获取当前用户"""
        credentials_exception = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
        token_data = verify_token(token, credentials_exception)
        user = get_user_by_username(db, username=token_data.username)
        if user is None:
            raise credentials_exception
        return user
    
    return get_current_user

def get_current_active_user_dependency():
    """获取当前活跃用户依赖"""
    get_current_user = get_current_user_dependency()
    
    def get_current_active_user(current_user: User = Depends(get_current_user)):
        """获取当前活跃用户"""
        if not current_user.is_active:
            raise HTTPException(status_code=400, detail="Inactive user")
        return current_user
    
    return get_current_active_user

def get_current_admin_user_dependency():
    """获取当前管理员用户依赖"""
    get_current_active_user = get_current_active_user_dependency()
    
    def get_current_admin_user(current_user: User = Depends(get_current_active_user)):
        """获取当前管理员用户"""
        if not current_user.is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not enough permissions"
            )
        return current_user
    
    return get_current_admin_user