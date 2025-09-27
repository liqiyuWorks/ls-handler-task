#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FFA模拟交易系统数据模型
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Text, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
from pydantic import BaseModel, EmailStr
from typing import Optional, List
import uuid
import hashlib
import secrets

Base = declarative_base()

class User(Base):
    """用户表"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(100))
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login = Column(DateTime)
    
    # 关联关系
    accounts = relationship("Account", back_populates="user")
    
    def set_password(self, password: str):
        """设置密码（哈希）"""
        salt = secrets.token_hex(16)
        pwd_hash = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt.encode('utf-8'), 100000)
        self.hashed_password = f"{salt}:{pwd_hash.hex()}"
    
    def check_password(self, password: str) -> bool:
        """验证密码"""
        if not self.hashed_password:
            return False
        try:
            salt, pwd_hash = self.hashed_password.split(':')
            return pwd_hash == hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt.encode('utf-8'), 100000).hex()
        except ValueError:
            return False

class Account(Base):
    """账户表"""
    __tablename__ = "accounts"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)  # 关联用户
    account_name = Column(String(100), unique=True, index=True)
    initial_equity = Column(Float, default=1000000)  # 初始权益
    current_equity = Column(Float, default=1000000)  # 当前权益
    total_pnl = Column(Float, default=0)  # 累计盈亏
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关联关系
    user = relationship("User", back_populates="accounts")
    trades = relationship("Trade", back_populates="account")
    positions = relationship("Position", back_populates="account")
    settlement_statements = relationship("SettlementStatement", back_populates="account")

class Trade(Base):
    """交易记录表"""
    __tablename__ = "trades"
    
    id = Column(Integer, primary_key=True, index=True)
    trade_id = Column(String(50), unique=True, index=True)  # 交易ID
    account_id = Column(Integer, ForeignKey("accounts.id"))
    
    # 基础交易信息
    contract = Column(String(20))  # 合约代码 (如 PMX)
    month = Column(String(20))  # 合约期限 (月份/季度/年度)
    trade_date = Column(DateTime, default=datetime.utcnow)  # 交易开仓日期
    strategy = Column(String(20))  # 交易类型 (Future, Call, Put)
    action = Column(String(20))  # 操作 (开仓, 平仓)
    buy_sell = Column(String(10))  # 交易方向 (多头, 空头)
    
    # 价格信息
    future_price = Column(Float)  # 开仓价格 (开仓时标的价格)
    strike_price = Column(Float, nullable=True)  # 行权价 (期权涉及)
    premium = Column(Float, nullable=True)  # 权利金 (期权涉及)
    
    # 交易量
    volume = Column(Integer)  # 交易手数
    short_volume = Column(Integer, default=0)  # 空头交易量
    long_volume = Column(Integer, default=0)  # 多头交易量
    
    # 费用信息
    commissions = Column(Float, default=0)  # 手续费 (场外交易+经纪费+交易所手续费+清算费)
    
    # 兼容性字段 (保持向后兼容)
    contract_type = Column(String(20))  # 合约类型 C5TC, P4TC, S5TC
    contract_month = Column(String(10))  # 合约月份
    contract_name = Column(String(50))  # 合约名称
    price = Column(Float)  # 交易价格 (兼容字段)
    
    # 费用计算 (兼容性字段)
    commission = Column(Float, default=0)  # 佣金
    clearing_fee = Column(Float, default=20)  # 清算费
    total_fees = Column(Float, default=0)  # 总费用
    
    # 盈亏信息
    trade_pnl = Column(Float, default=0)  # 交易盈亏
    total_amount = Column(Float, default=0)  # 总额
    
    # 持仓信息
    previous_position = Column(Integer, default=0)  # 上期持仓量
    current_position = Column(Integer, default=0)  # 当前持仓量
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # 关联关系
    account = relationship("Account", back_populates="trades")

class Position(Base):
    """持仓表"""
    __tablename__ = "positions"
    
    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey("accounts.id"))
    
    # 基础持仓信息
    contract = Column(String(20))  # 合约代码
    month = Column(String(20))  # 合约期限
    strategy = Column(String(20))  # 交易类型 (Future, Call, Put)
    buy_sell = Column(String(10))  # 交易方向 (多头, 空头)
    open_interest = Column(Integer, default=0)  # 持仓量
    future_price = Column(Float, default=0)  # 开仓价格 (平均开仓成本价)
    strike_price = Column(Float, nullable=True)  # 行权价 (期权涉及)
    premium = Column(Float, nullable=True)  # 权利金 (期权涉及)
    daily_settlement_price = Column(Float, default=0)  # 当日结算价
    unrealized_pnl = Column(Float, default=0)  # 浮动盈亏
    commissions = Column(Float, default=0)  # 手续费
    
    # 兼容性字段
    contract_type = Column(String(20))  # 合约类型
    contract_month = Column(String(10))  # 合约月份
    position_volume = Column(Integer, default=0)  # 持仓量 (兼容字段)
    average_price = Column(Float, default=0)  # 平均价格 (兼容字段)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关联关系
    account = relationship("Account", back_populates="positions")

# Pydantic模型
class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str
    full_name: Optional[str] = None

class UserLogin(BaseModel):
    username: str
    password: str

class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    full_name: Optional[str]
    is_active: bool
    is_admin: bool
    created_at: datetime
    last_login: Optional[datetime]

class Token(BaseModel):
    access_token: str
    token_type: str
    expires_in: int

class TokenData(BaseModel):
    username: Optional[str] = None

class AccountCreate(BaseModel):
    account_name: str
    initial_equity: float = 1000000

class AccountResponse(BaseModel):
    id: int
    account_name: str
    initial_equity: float
    current_equity: float
    total_pnl: float
    created_at: datetime
    updated_at: datetime

class TradeCreate(BaseModel):
    # 新字段
    contract: str  # 合约代码
    month: str  # 合约期限
    trade_date: Optional[datetime] = None  # 交易日期
    strategy: str  # 交易类型 (Future, Call, Put)
    action: str  # 操作 (开仓, 平仓)
    buy_sell: str  # 交易方向 (多头, 空头)
    future_price: float  # 开仓价格
    strike_price: Optional[float] = None  # 行权价
    premium: Optional[float] = None  # 权利金
    volume: int  # 交易量
    commissions: Optional[float] = 0  # 手续费
    
    # 兼容性字段
    contract_type: Optional[str] = None
    contract_month: Optional[str] = None
    contract_name: Optional[str] = None
    price: Optional[float] = None

class TradeResponse(BaseModel):
    id: int
    trade_id: str
    
    # 新字段
    contract: str
    month: str
    trade_date: datetime
    strategy: str
    action: str
    buy_sell: str
    future_price: float
    strike_price: Optional[float]
    premium: Optional[float]
    volume: int
    short_volume: int
    long_volume: int
    commissions: float
    
    # 兼容性字段
    contract_type: Optional[str]
    contract_month: Optional[str]
    contract_name: Optional[str]
    price: Optional[float]
    
    # 费用和盈亏信息
    commission: float
    clearing_fee: float
    total_fees: float
    trade_pnl: float
    total_amount: float
    previous_position: int
    current_position: int
    created_at: datetime

class PositionResponse(BaseModel):
    id: int
    
    # 新字段
    contract: str
    month: str
    strategy: str
    buy_sell: str
    open_interest: int
    future_price: float
    strike_price: Optional[float]
    premium: Optional[float]
    daily_settlement_price: float
    unrealized_pnl: float
    commissions: float
    
    # 兼容性字段
    contract_type: Optional[str]
    contract_month: Optional[str]
    position_volume: Optional[int]
    average_price: Optional[float]
    
    created_at: datetime
    updated_at: datetime

class AccountSummary(BaseModel):
    account: AccountResponse
    positions: List[PositionResponse]
    recent_trades: List[TradeResponse]
    total_unrealized_pnl: float
    recommended_volume: int

class TradeRequest(BaseModel):
    """交易请求模型"""
    # 新字段
    contract: str  # 合约代码
    month: str  # 合约期限
    trade_date: Optional[datetime] = None  # 交易日期
    strategy: str  # 交易类型 (Future, Call, Put)
    action: str  # 操作 (开仓, 平仓)
    buy_sell: str  # 交易方向 (多头, 空头)
    future_price: float  # 开仓价格
    strike_price: Optional[float] = None  # 行权价
    premium: Optional[float] = None  # 权利金
    volume: int  # 交易量
    short_volume: int = 0  # 空头交易量
    long_volume: int = 0  # 多头交易量
    commissions: Optional[float] = 0  # 手续费
    
    # 兼容性字段
    contract_type: Optional[str] = None
    contract_month: Optional[str] = None
    price: Optional[float] = None

# 结算单相关模型
class SettlementStatement(Base):
    """结算单表"""
    __tablename__ = "settlement_statements"
    
    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey("accounts.id"))
    statement_period = Column(String(50))  # 结算单周期 (如: 2025-01-27)
    period_start = Column(DateTime)  # 周期开始时间
    period_end = Column(DateTime)  # 周期结束时间
    
    # 账户总结字段
    beginning_equity = Column(Float)  # 期初权益
    deposits = Column(Float, default=0.0)  # 期间入金
    withdrawals = Column(Float, default=0.0)  # 期间出金
    realized_pnl = Column(Float, default=0.0)  # 平仓盈亏
    unrealized_pnl = Column(Float, default=0.0)  # 浮动盈亏
    commissions = Column(Float, default=0.0)  # 手续费
    ending_equity = Column(Float)  # 期末权益
    
    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关联
    account = relationship("Account", back_populates="settlement_statements")

class SettlementStatementRequest(BaseModel):
    """结算单请求模型"""
    account_id: int
    statement_period: str  # 结算单周期
    period_start: datetime
    period_end: datetime

class SettlementStatementResponse(BaseModel):
    """结算单响应模型"""
    id: int
    account_id: int
    statement_period: str
    period_start: datetime
    period_end: datetime
    beginning_equity: float
    deposits: float
    withdrawals: float
    realized_pnl: float
    unrealized_pnl: float
    commissions: float
    ending_equity: float
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

# 交易明细相关模型
class ClosedTradeDetail(BaseModel):
    """已平仓交易明细"""
    closing_date: datetime  # 平仓日期
    contract: str  # 合约名称
    month: str  # 合约期限
    strategy: str  # 策略
    buy_sell: str  # 交易方向
    open_date: datetime  # 交易日期
    open_future_price: float  # 开仓价格
    strike_price: Optional[float] = None  # 行权价
    open_premium: Optional[float] = None  # 开仓权利金
    close_future_price: float  # 平仓价格
    close_premium: Optional[float] = None  # 平仓权利金
    realized_pnl: float  # 平仓盈亏
    volume: int  # 交易量
    commissions: float  # 手续费
    
    class Config:
        from_attributes = True

class SettlementStatementDetail(BaseModel):
    """结算单详情模型（包含交易明细）"""
    settlement: SettlementStatementResponse
    closed_trades: List[ClosedTradeDetail]
    total_trades: int
    total_volume: int
    avg_realized_pnl: float
    
    class Config:
        from_attributes = True
