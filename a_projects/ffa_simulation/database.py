#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库连接和操作
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError
from config import DATABASE_CONFIG
from models import Base, User, Account, Trade, Position, SettlementStatement
from datetime import datetime
from typing import List, Optional
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
            
            # 删除所有结算单
            db.query(SettlementStatement).filter(SettlementStatement.account_id == account_id).delete()
            
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
    
    def update_trade(self, trade_id: int, update_data: dict) -> bool:
        """更新交易记录"""
        db = self.SessionLocal()
        try:
            trade = db.query(Trade).filter(Trade.id == trade_id).first()
            if trade:
                for key, value in update_data.items():
                    if hasattr(trade, key):
                        setattr(trade, key, value)
                db.commit()
                return True
            return False
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
    
    def get_position(self, account_id: int, contract: str, month: str):
        """获取持仓"""
        db = self.SessionLocal()
        try:
            return db.query(Position).filter(
                Position.account_id == account_id,
                Position.contract == contract,
                Position.month == month
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
    
    # 结算单相关方法
    def create_settlement_statement(self, settlement_data: dict) -> SettlementStatement:
        """创建结算单"""
        db = self.SessionLocal()
        try:
            settlement = SettlementStatement(**settlement_data)
            db.add(settlement)
            db.commit()
            db.refresh(settlement)
            return settlement
        except SQLAlchemyError as e:
            db.rollback()
            raise e
        finally:
            db.close()
    
    def get_settlement_statements(self, account_id: int) -> List[SettlementStatement]:
        """获取账户的结算单列表"""
        db = self.SessionLocal()
        try:
            statements = db.query(SettlementStatement).filter(
                SettlementStatement.account_id == account_id
            ).order_by(SettlementStatement.created_at.desc()).all()
            return statements
        except SQLAlchemyError as e:
            raise e
        finally:
            db.close()
    
    def get_settlement_statement(self, statement_id: int) -> Optional[SettlementStatement]:
        """获取特定结算单"""
        db = self.SessionLocal()
        try:
            statement = db.query(SettlementStatement).filter(
                SettlementStatement.id == statement_id
            ).first()
            return statement
        except SQLAlchemyError as e:
            raise e
        finally:
            db.close()
    
    def calculate_settlement_data(self, account_id: int, period_start: datetime, period_end: datetime) -> dict:
        """计算结算单数据"""
        db = self.SessionLocal()
        try:
            # 获取账户信息
            account = db.query(Account).filter(Account.id == account_id).first()
            if not account:
                raise ValueError("账户不存在")
            
            # 获取周期内的交易记录
            trades = db.query(Trade).filter(
                Trade.account_id == account_id,
                Trade.trade_date >= period_start,
                Trade.trade_date <= period_end
            ).all()
            
            # 获取周期结束时的持仓
            positions = db.query(Position).filter(Position.account_id == account_id).all()
            
            # 计算各项数据
            beginning_equity = account.initial_equity  # 期初权益（简化处理）
            deposits = 0.0  # 期间入金（暂时设为0）
            withdrawals = 0.0  # 期间出金（暂时设为0）
            
            # 计算平仓盈亏
            realized_pnl = sum(trade.trade_pnl or 0 for trade in trades if trade.action == "平仓")
            
            # 计算浮动盈亏
            unrealized_pnl = sum(position.unrealized_pnl or 0 for position in positions)
            
            # 计算手续费
            commissions = sum(trade.commissions or 0 for trade in trades)
            
            # 计算期末权益
            ending_equity = beginning_equity + deposits - withdrawals + realized_pnl + unrealized_pnl - commissions
            
            return {
                "beginning_equity": beginning_equity,
                "deposits": deposits,
                "withdrawals": withdrawals,
                "realized_pnl": realized_pnl,
                "unrealized_pnl": unrealized_pnl,
                "commissions": commissions,
                "ending_equity": ending_equity
            }
        except SQLAlchemyError as e:
            raise e
        finally:
            db.close()
    
    def get_closed_trades_for_settlement(self, account_id: int, period_start: datetime, period_end: datetime) -> List[dict]:
        """获取结算周期内的已平仓交易明细"""
        db = self.SessionLocal()
        try:
            # 获取周期内的平仓交易
            closed_trades = db.query(Trade).filter(
                Trade.account_id == account_id,
                Trade.action == "平仓",
                Trade.trade_date >= period_start,
                Trade.trade_date <= period_end
            ).order_by(Trade.trade_date.desc()).all()
            
            trade_details = []
            for trade in closed_trades:
                # 查找对应的开仓交易
                open_trade = db.query(Trade).filter(
                    Trade.account_id == account_id,
                    Trade.contract == trade.contract,
                    Trade.month == trade.month,
                    Trade.strategy == trade.strategy,
                    Trade.buy_sell != trade.buy_sell,  # 相反方向
                    Trade.action == "开仓",
                    Trade.trade_date < trade.trade_date
                ).order_by(Trade.trade_date.desc()).first()
                
                if open_trade:
                    trade_detail = {
                        "closing_date": trade.trade_date or trade.created_at,
                        "contract": trade.contract or trade.contract_type or "",
                        "month": trade.month or trade.contract_month or "",
                        "strategy": trade.strategy or "",
                        "buy_sell": trade.buy_sell or "",
                        "open_date": open_trade.trade_date or open_trade.created_at,
                        "open_future_price": open_trade.future_price or open_trade.price or 0.0,
                        "strike_price": open_trade.strike_price,
                        "open_premium": open_trade.premium,
                        "close_future_price": trade.future_price or trade.price or 0.0,
                        "close_premium": trade.premium,
                        "realized_pnl": trade.trade_pnl or 0.0,
                        "volume": trade.volume or 0,
                        "commissions": trade.commissions or 0.0
                    }
                    trade_details.append(trade_detail)
            
            return trade_details
        except SQLAlchemyError as e:
            raise e
        finally:
            db.close()
    
    def get_settlement_statement_detail(self, statement_id: int) -> dict:
        """获取结算单详情（包含交易明细）"""
        db = self.SessionLocal()
        try:
            # 获取结算单
            statement = db.query(SettlementStatement).filter(
                SettlementStatement.id == statement_id
            ).first()
            
            if not statement:
                raise ValueError("结算单不存在")
            
            # 获取交易明细
            closed_trades = self.get_closed_trades_for_settlement(
                statement.account_id,
                statement.period_start,
                statement.period_end
            )
            
            # 计算统计信息
            total_trades = len(closed_trades)
            total_volume = sum(trade["volume"] for trade in closed_trades)
            avg_realized_pnl = sum(trade["realized_pnl"] for trade in closed_trades) / total_trades if total_trades > 0 else 0.0
            
            return {
                "settlement": statement,
                "closed_trades": closed_trades,
                "total_trades": total_trades,
                "total_volume": total_volume,
                "avg_realized_pnl": avg_realized_pnl
            }
        except SQLAlchemyError as e:
            raise e
        finally:
            db.close()
    
    def get_floating_pnl_data(self, account_id: int, days: int = 30) -> List[dict]:
        """获取浮动盈亏曲线数据"""
        db = self.SessionLocal()
        try:
            from datetime import datetime, timedelta
            
            # 获取指定天数内的持仓数据
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=days)
            
            # 查询持仓数据，按更新时间排序
            positions = db.query(Position).filter(
                Position.account_id == account_id,
                Position.updated_at >= start_date
            ).order_by(Position.updated_at.asc()).all()
            
            # 如果没有历史数据，使用当前持仓数据
            if not positions:
                current_positions = db.query(Position).filter(
                    Position.account_id == account_id
                ).all()
                
                if current_positions:
                    # 创建当前时间的数据点
                    current_time = datetime.utcnow()
                    total_floating_pnl = sum(p.unrealized_pnl or 0.0 for p in current_positions)
                    floating_pnl_data = [{
                        'timestamp': current_time,
                        'total_floating_pnl': total_floating_pnl,
                        'position_count': len(current_positions)
                    }]
                else:
                    floating_pnl_data = []
            else:
                # 按时间分组计算总浮动盈亏
                floating_pnl_data = []
                position_groups = {}
                
                for position in positions:
                    update_time = position.updated_at
                    time_key = update_time.strftime('%Y-%m-%d %H:%M')
                    
                    if time_key not in position_groups:
                        position_groups[time_key] = {
                            'timestamp': update_time,
                            'total_floating_pnl': 0.0,
                            'position_count': 0
                        }
                    
                    position_groups[time_key]['total_floating_pnl'] += position.unrealized_pnl or 0.0
                    position_groups[time_key]['position_count'] += 1
                
                # 转换为列表并排序
                for time_key in sorted(position_groups.keys()):
                    group = position_groups[time_key]
                    floating_pnl_data.append({
                        'timestamp': group['timestamp'],
                        'total_floating_pnl': group['total_floating_pnl'],
                        'position_count': group['position_count']
                    })
            
            return floating_pnl_data
        except SQLAlchemyError as e:
            raise e
        finally:
            db.close()
    
    def get_cumulative_pnl_data(self, account_id: int, days: int = 30) -> List[dict]:
        """获取累计实际盈亏曲线数据"""
        db = self.SessionLocal()
        try:
            from datetime import datetime, timedelta
            
            # 获取指定天数内的平仓交易数据
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=days)
            
            # 查询平仓交易数据，按平仓日期排序
            closed_trades = db.query(Trade).filter(
                Trade.account_id == account_id,
                Trade.action == "平仓",
                Trade.trade_date >= start_date,
                Trade.trade_date <= end_date
            ).order_by(Trade.trade_date.asc()).all()
            
            # 计算累计盈亏
            cumulative_pnl_data = []
            cumulative_pnl = 0.0
            trade_count = 0
            
            for trade in closed_trades:
                trade_pnl = trade.trade_pnl or 0.0
                cumulative_pnl += trade_pnl
                trade_count += 1
                
                cumulative_pnl_data.append({
                    'closing_date': trade.trade_date or trade.created_at,
                    'realized_pnl': trade_pnl,
                    'cumulative_pnl': cumulative_pnl,
                    'trade_count': trade_count
                })
            
            return cumulative_pnl_data
        except SQLAlchemyError as e:
            raise e
        finally:
            db.close()
    
    def get_pnl_chart_data(self, account_id: int, days: int = 30) -> dict:
        """获取盈亏曲线图表数据"""
        try:
            # 获取浮动盈亏数据
            floating_pnl_data = self.get_floating_pnl_data(account_id, days)
            
            # 获取累计盈亏数据
            cumulative_pnl_data = self.get_cumulative_pnl_data(account_id, days)
            
            # 计算当前浮动盈亏
            current_floating_pnl = 0.0
            if floating_pnl_data:
                current_floating_pnl = floating_pnl_data[-1]['total_floating_pnl']
            
            # 计算总实际盈亏
            total_realized_pnl = 0.0
            if cumulative_pnl_data:
                total_realized_pnl = cumulative_pnl_data[-1]['cumulative_pnl']
            
            # 计算最大值和最小值
            max_floating_pnl = max([point['total_floating_pnl'] for point in floating_pnl_data], default=0.0)
            min_floating_pnl = min([point['total_floating_pnl'] for point in floating_pnl_data], default=0.0)
            max_cumulative_pnl = max([point['cumulative_pnl'] for point in cumulative_pnl_data], default=0.0)
            min_cumulative_pnl = min([point['cumulative_pnl'] for point in cumulative_pnl_data], default=0.0)
            
            return {
                'floating_pnl_data': floating_pnl_data,
                'cumulative_pnl_data': cumulative_pnl_data,
                'current_floating_pnl': current_floating_pnl,
                'total_realized_pnl': total_realized_pnl,
                'max_floating_pnl': max_floating_pnl,
                'min_floating_pnl': min_floating_pnl,
                'max_cumulative_pnl': max_cumulative_pnl,
                'min_cumulative_pnl': min_cumulative_pnl
            }
        except Exception as e:
            raise e
