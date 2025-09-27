#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库连接和操作
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError
from config import DATABASE_CONFIG
from models import Base, User, Account, Trade, Position
from datetime import datetime
import logging
import hashlib
import secrets

# 创建数据库引擎
engine = create_engine(DATABASE_CONFIG["url"], echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 创建所有表
def create_tables():
    """创建数据库表"""
    Base.metadata.create_all(bind=engine)

def get_db():
    """获取数据库会话"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class DatabaseManager:
    """数据库管理器"""
    
    def __init__(self):
        self.engine = engine
        self.SessionLocal = SessionLocal
    
    # 用户管理方法
    def create_user(self, username: str, email: str, password: str, full_name: str = None, is_admin: bool = False):
        """创建用户"""
        db = self.SessionLocal()
        try:
            # 检查用户名和邮箱是否已存在
            if self.get_user_by_username(username):
                raise ValueError("用户名已存在")
            if self.get_user_by_email(email):
                raise ValueError("邮箱已存在")
            
            user = User(
                username=username,
                email=email,
                full_name=full_name,
                is_admin=is_admin
            )
            user.set_password(password)
            
            db.add(user)
            db.commit()
            db.refresh(user)
            
            # 为用户创建默认账户
            self.create_account(f"{username}的账户", 1000000, user.id)
            
            return user
        except SQLAlchemyError as e:
            db.rollback()
            raise e
        finally:
            db.close()
    
    def get_user_by_username(self, username: str):
        """根据用户名获取用户"""
        db = self.SessionLocal()
        try:
            return db.query(User).filter(User.username == username).first()
        finally:
            db.close()
    
    def get_user_by_email(self, email: str):
        """根据邮箱获取用户"""
        db = self.SessionLocal()
        try:
            return db.query(User).filter(User.email == email).first()
        finally:
            db.close()
    
    def get_user_by_id(self, user_id: int):
        """根据ID获取用户"""
        db = self.SessionLocal()
        try:
            return db.query(User).filter(User.id == user_id).first()
        finally:
            db.close()
    
    def update_user_last_login(self, user_id: int):
        """更新用户最后登录时间"""
        db = self.SessionLocal()
        try:
            user = db.query(User).filter(User.id == user_id).first()
            if user:
                user.last_login = datetime.utcnow()
                db.commit()
        except SQLAlchemyError as e:
            db.rollback()
            print(f"Update last login error: {e}")
        except Exception as e:
            print(f"Update last login error: {e}")
        finally:
            db.close()
    
    def get_user_accounts(self, user_id: int):
        """获取用户的所有账户"""
        db = self.SessionLocal()
        try:
            return db.query(Account).filter(Account.user_id == user_id).all()
        finally:
            db.close()
    
    def reset_account_data(self, account_id: int, user_id: int):
        """重置账户数据到初始状态"""
        db = self.SessionLocal()
        try:
            # 验证账户属于该用户
            account = db.query(Account).filter(Account.id == account_id, Account.user_id == user_id).first()
            if not account:
                raise ValueError("账户不存在或无权限访问")
            
            # 获取初始权益
            initial_equity = account.initial_equity
            
            # 删除所有交易记录
            db.query(Trade).filter(Trade.account_id == account_id).delete()
            
            # 删除所有持仓记录
            db.query(Position).filter(Position.account_id == account_id).delete()
            
            # 重置账户数据
            account.current_equity = initial_equity
            account.total_pnl = 0.0
            account.updated_at = datetime.utcnow()
            
            db.commit()
            
            return {
                "success": True,
                "message": "账户数据已重置到初始状态",
                "initial_equity": initial_equity,
                "current_equity": initial_equity,
                "total_pnl": 0.0
            }
            
        except SQLAlchemyError as e:
            db.rollback()
            raise e
        except Exception as e:
            db.rollback()
            raise e
        finally:
            db.close()
    
    def create_account(self, account_name: str, initial_equity: float = 1000000, user_id: int = None):
        """创建账户"""
        db = self.SessionLocal()
        try:
            account = Account(
                user_id=user_id,
                account_name=account_name,
                initial_equity=initial_equity,
                current_equity=initial_equity
            )
            db.add(account)
            db.commit()
            db.refresh(account)
            return account
        except SQLAlchemyError as e:
            db.rollback()
            raise e
        finally:
            db.close()
    
    def get_account(self, account_id: int):
        """获取账户"""
        db = self.SessionLocal()
        try:
            return db.query(Account).filter(Account.id == account_id).first()
        finally:
            db.close()
    
    def get_account_by_name(self, account_name: str):
        """根据名称获取账户"""
        db = self.SessionLocal()
        try:
            return db.query(Account).filter(Account.account_name == account_name).first()
        finally:
            db.close()
    
    def get_all_accounts(self):
        """获取所有账户"""
        db = self.SessionLocal()
        try:
            return db.query(Account).all()
        finally:
            db.close()
    
    def update_account_equity(self, account_id: int, new_equity: float):
        """更新账户权益"""
        db = self.SessionLocal()
        try:
            account = db.query(Account).filter(Account.id == account_id).first()
            if account:
                account.current_equity = new_equity
                account.total_pnl = new_equity - account.initial_equity
                db.commit()
                return account
        except SQLAlchemyError as e:
            db.rollback()
            raise e
        finally:
            db.close()
    
    def create_trade(self, trade_data: dict):
        """创建交易记录"""
        db = self.SessionLocal()
        try:
            trade = Trade(**trade_data)
            db.add(trade)
            db.commit()
            db.refresh(trade)
            return trade
        except SQLAlchemyError as e:
            db.rollback()
            raise e
        finally:
            db.close()
    
    def get_account_trades(self, account_id: int, limit: int = 10):
        """获取账户交易记录"""
        db = self.SessionLocal()
        try:
            return db.query(Trade).filter(
                Trade.account_id == account_id
            ).order_by(Trade.created_at.desc()).limit(limit).all()
        finally:
            db.close()
    
    def get_position(self, account_id: int, contract_type: str, contract_month: str):
        """获取持仓"""
        db = self.SessionLocal()
        try:
            return db.query(Position).filter(
                Position.account_id == account_id,
                Position.contract_type == contract_type,
                Position.contract_month == contract_month
            ).first()
        finally:
            db.close()
    
    def update_or_create_position(self, position_data: dict):
        """更新或创建持仓"""
        db = self.SessionLocal()
        try:
            position = db.query(Position).filter(
                Position.account_id == position_data['account_id'],
                Position.contract_type == position_data['contract_type'],
                Position.contract_month == position_data['contract_month']
            ).first()
            
            if position:
                # 更新现有持仓
                for key, value in position_data.items():
                    if key != 'account_id' and key != 'contract_type' and key != 'contract_month':
                        setattr(position, key, value)
            else:
                # 创建新持仓
                position = Position(**position_data)
                db.add(position)
            
            db.commit()
            db.refresh(position)
            return position
        except SQLAlchemyError as e:
            db.rollback()
            raise e
        finally:
            db.close()
    
    def get_account_positions(self, account_id: int):
        """获取账户所有持仓"""
        db = self.SessionLocal()
        try:
            return db.query(Position).filter(Position.account_id == account_id).all()
        finally:
            db.close()
    
    def get_position_by_id(self, position_id: int):
        """根据ID获取持仓"""
        db = self.SessionLocal()
        try:
            return db.query(Position).filter(Position.id == position_id).first()
        finally:
            db.close()
    
    def update_position(self, position: Position):
        """更新持仓"""
        db = self.SessionLocal()
        try:
            db.merge(position)
            db.commit()
            return position
        except SQLAlchemyError as e:
            db.rollback()
            raise e
        finally:
            db.close()
    
    def delete_position(self, position_id: int):
        """删除持仓（平仓时）"""
        db = self.SessionLocal()
        try:
            position = db.query(Position).filter(Position.id == position_id).first()
            if position:
                db.delete(position)
                db.commit()
                return True
            return False
        except SQLAlchemyError as e:
            db.rollback()
            raise e
        finally:
            db.close()
