#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FFA交易引擎 - 核心交易逻辑
"""

import uuid
from datetime import datetime
from typing import Dict, Tuple, Optional
from config import TRADING_CONFIG, CONTRACT_CONFIG, STRATEGY_CONFIG, MONTH_CONFIG
from database import DatabaseManager
from models import Account, Trade, Position
from pnl_calculator import PnLCalculator
import logging

class TradingEngine:
    """FFA交易引擎"""
    
    def __init__(self):
        self.db_manager = DatabaseManager()
        self.commission_rate = TRADING_CONFIG["commission_rate"]
        self.clearing_fee = TRADING_CONFIG["clearing_fee"]
    
    def calculate_fees(self, price: float, volume: int) -> Tuple[float, float, float]:
        """计算交易费用"""
        # 佣金 = 价格 * 手数 * 佣金比例
        commission = price * volume * self.commission_rate
        # 清算费固定
        clearing_fee = self.clearing_fee
        # 总费用
        total_fees = commission + clearing_fee
        
        return commission, clearing_fee, total_fees
    
    def calculate_trade_amount(self, price: float, volume: int, strategy: str) -> float:
        """计算交易总额"""
        _, _, total_fees = self.calculate_fees(price, volume)
        
        # 交易总额 = 价格 * 手数 - 费用
        if strategy in ["开多", "平空"]:  # 买入
            return price * volume - total_fees
        else:  # 卖出
            return price * volume - total_fees
    
    def get_current_position(self, account_id: int, contract_type: str, contract_month: str) -> Optional[Position]:
        """获取当前持仓"""
        return self.db_manager.get_position(account_id, contract_type, contract_month)
    
    def calculate_position_change(self, action: str, buy_sell: str, volume: int, current_position: int) -> Tuple[int, int]:
        """计算持仓变化"""
        if action == "开仓" and buy_sell == "多头":
            # 开多仓
            new_position = current_position + volume
            position_change = volume
        elif action == "开仓" and buy_sell == "空头":
            # 开空仓
            new_position = current_position - volume
            position_change = -volume
        elif action == "平仓" and buy_sell == "多头":
            # 平多仓
            new_position = current_position - volume
            position_change = -volume
        elif action == "平仓" and buy_sell == "空头":
            # 平空仓
            new_position = current_position + volume
            position_change = volume
        else:
            # 默认情况
            new_position = current_position
            position_change = 0
        
        return new_position, position_change
    
    def validate_trade(self, account_id: int, strategy: str, volume: int, 
                      contract_type: str, contract_month: str, action: str = None, buy_sell: str = None) -> Tuple[bool, str]:
        """验证交易是否有效"""
        # 检查合约类型
        if contract_type not in CONTRACT_CONFIG:
            return False, f"不支持的合约类型: {contract_type}"
        
        # 检查交易量
        if volume < TRADING_CONFIG["min_trade_volume"]:
            return False, f"交易量不能小于{TRADING_CONFIG['min_trade_volume']}手"
        
        if volume > TRADING_CONFIG["max_trade_volume"]:
            return False, f"交易量不能大于{TRADING_CONFIG['max_trade_volume']}手"
        
        # 检查策略
        if strategy not in STRATEGY_CONFIG:
            return False, f"不支持的交易策略: {strategy}"
        
        # 获取当前持仓
        current_position = self.get_current_position(account_id, contract_type, contract_month)
        current_volume = current_position.position_volume if current_position else 0
        
        # 检查平仓操作
        if action and buy_sell:
            if action == "平仓" and buy_sell == "多头" and current_volume <= 0:
                return False, "没有多头持仓可平"
            
            if action == "平仓" and buy_sell == "空头" and current_volume >= 0:
                return False, "没有空头持仓可平"
            
            # 检查平仓数量
            if action == "平仓" and buy_sell == "多头" and volume > current_volume:
                return False, f"平仓数量({volume})不能超过持仓数量({current_volume})"
            
            if action == "平仓" and buy_sell == "空头" and volume > abs(current_volume):
                return False, f"平仓数量({volume})不能超过持仓数量({abs(current_volume)})"
        
        return True, "验证通过"
    
    def execute_trade(self, account_id: int, trade_request: Dict) -> Tuple[bool, str, Optional[Trade]]:
        """执行交易"""
        try:
            # 提取新字段参数
            contract = trade_request["contract"]
            month = trade_request["month"]
            trade_date = trade_request.get("trade_date")
            strategy = trade_request["strategy"]
            action = trade_request["action"]
            buy_sell = trade_request["buy_sell"]
            future_price = trade_request["future_price"]
            strike_price = trade_request.get("strike_price")
            premium = trade_request.get("premium")
            volume = trade_request["volume"]
            short_volume = trade_request.get("short_volume", 0)
            long_volume = trade_request.get("long_volume", 0)
            commissions = trade_request.get("commissions", 0)
            
            # 兼容性字段
            contract_type = trade_request.get("contract_type", contract)
            contract_month = trade_request.get("contract_month", month)
            contract_name = trade_request.get("contract_name", f"{contract}{month}合约")
            price = trade_request.get("price", future_price)
            
            # 验证交易
            is_valid, message = self.validate_trade(
                account_id, strategy, volume, contract_type, contract_month, action, buy_sell
            )
            
            if not is_valid:
                return False, message, None
            
            # 获取当前持仓
            current_position = self.get_current_position(account_id, contract, month)
            current_volume = current_position.position_volume if current_position else 0
            
            # 计算费用和总额
            commission, clearing_fee, total_fees = self.calculate_fees(price, volume)
            # 使用用户输入的手续费或计算的手续费
            final_commissions = commissions if commissions > 0 else total_fees
            total_amount = self.calculate_trade_amount(price, volume, strategy)
            
            # 计算新持仓
            new_position_volume, position_change = self.calculate_position_change(
                action, buy_sell, volume, current_volume
            )
            
            # 生成交易ID
            trade_id = str(int(datetime.now().timestamp() * 1000))
            
            # 处理交易日期
            if trade_date:
                if isinstance(trade_date, str):
                    trade_date = datetime.fromisoformat(trade_date)
            else:
                trade_date = datetime.utcnow()
            
            # 创建交易记录
            trade_data = {
                "trade_id": trade_id,
                "account_id": account_id,
                
                # 新字段
                "contract": contract,
                "month": month,
                "trade_date": trade_date,
                "strategy": strategy,
                "action": action,
                "buy_sell": buy_sell,
                "future_price": future_price,
                "strike_price": strike_price,
                "premium": premium,
                "volume": volume,
                "short_volume": short_volume,
                "long_volume": long_volume,
                "commissions": final_commissions,
                
                # 兼容性字段
                "contract_type": contract_type,
                "contract_month": contract_month,
                "contract_name": contract_name,
                "price": price,
                "commission": commission,
                "clearing_fee": clearing_fee,
                "total_fees": total_fees,
                "trade_pnl": 0,  # 暂时设为0，平仓时计算
                "total_amount": total_amount,
                "previous_position": current_volume,
                "current_position": new_position_volume
            }
            
            trade = self.db_manager.create_trade(trade_data)
            
            # 更新或创建持仓
            if new_position_volume != 0:
                # 计算加权平均价格
                if current_position:
                    weighted_avg_price = PnLCalculator.calculate_weighted_average_price(
                        current_position.future_price or current_position.average_price,
                        abs(current_volume),
                        price,
                        volume
                    )
                else:
                    weighted_avg_price = price
                
                # 计算当前浮动盈亏（使用当前价格作为结算价）
                # 对于期权，premium是单价，需要乘以手数得到总权利金
                total_premium = premium * abs(new_position_volume) if premium and strategy in ["Call", "Put"] else premium
                current_pnl = PnLCalculator.calculate_position_pnl(
                    strategy, buy_sell, weighted_avg_price, price, abs(new_position_volume),
                    strike_price, total_premium
                )
                
                position_data = {
                    "account_id": account_id,
                    
                    # 新字段
                    "contract": contract,
                    "month": month,
                    "strategy": strategy,
                    "buy_sell": buy_sell,
                    "open_interest": abs(new_position_volume),
                    "future_price": weighted_avg_price,
                    "strike_price": strike_price,
                    "premium": premium,
                    "daily_settlement_price": price,  # 使用当前价格作为结算价
                    "unrealized_pnl": current_pnl,
                    "commissions": final_commissions,
                    
                    # 兼容性字段
                    "contract_type": contract_type,
                    "contract_month": contract_month,
                    "position_volume": new_position_volume,
                    "average_price": weighted_avg_price
                }
                
                self.db_manager.update_or_create_position(position_data)
            else:
                # 平仓，计算盈亏并删除持仓记录
                if current_position:
                    # 计算平仓盈亏
                    if action == "平仓":
                        # 使用PnLCalculator计算盈亏
                        # 对于期权，premium是单价，需要乘以手数得到总权利金
                        position_strategy = current_position.strategy or "Future"
                        total_premium = current_position.premium * volume if current_position.premium and position_strategy in ["Call", "Put"] else current_position.premium
                        trade_pnl = PnLCalculator.calculate_position_pnl(
                            position_strategy,
                            current_position.buy_sell or "多头",
                            current_position.average_price,
                            price,
                            volume,
                            current_position.strike_price,
                            total_premium
                        )
                        
                        # 更新交易记录的盈亏
                        trade.trade_pnl = trade_pnl
                        self.db_manager.update_trade(trade.id, {"trade_pnl": trade_pnl})
                    
                    self.db_manager.delete_position(current_position.id)
            
            # 更新账户权益
            account = self.db_manager.get_account(account_id)
            if account:
                # 这里简化处理，实际应该根据当前市场价格计算未实现盈亏
                new_equity = account.current_equity - final_commissions
                self.db_manager.update_account_equity(account_id, new_equity)
            
            return True, "交易执行成功", trade
            
        except Exception as e:
            logging.error(f"交易执行失败: {str(e)}")
            return False, f"交易执行失败: {str(e)}", None
    
    def calculate_unrealized_pnl(self, position: Position, current_price: float) -> float:
        """计算未实现盈亏"""
        if position.open_interest == 0 and position.position_volume == 0:
            return 0
        
        # 使用新的盈亏计算器
        volume = position.open_interest if position.open_interest > 0 else abs(position.position_volume)
        opening_price = position.future_price if position.future_price > 0 else position.average_price
        
        # 对于期权，premium是单价，需要乘以手数得到总权利金
        position_strategy = position.strategy or "Future"
        total_premium = position.premium * volume if position.premium and position_strategy in ["Call", "Put"] else position.premium
        
        return PnLCalculator.calculate_position_pnl(
            position_strategy,
            position.buy_sell or "多头",
            opening_price,
            current_price,
            volume,
            position.strike_price,
            total_premium
        )
    
    def get_account_summary(self, account_id: int, current_prices: Dict = None) -> Dict:
        """获取账户汇总信息"""
        account = self.db_manager.get_account(account_id)
        if not account:
            return None
        
        # 获取持仓
        positions = self.db_manager.get_account_positions(account_id)
        
        # 获取最近交易
        recent_trades = self.db_manager.get_account_trades(account_id, 10)
        
        # 计算总未实现盈亏
        total_unrealized_pnl = 0
        if current_prices:
            for position in positions:
                key = f"{position.contract_type}_{position.contract_month}"
                if key in current_prices:
                    position.unrealized_pnl = self.calculate_unrealized_pnl(
                        position, current_prices[key]
                    )
                    total_unrealized_pnl += position.unrealized_pnl
        
        # 计算推荐交易量（简化算法）
        recommended_volume = max(1, int(account.current_equity / 10000))
        
        return {
            "account": account,
            "positions": positions,
            "recent_trades": recent_trades,
            "total_unrealized_pnl": total_unrealized_pnl,
            "recommended_volume": recommended_volume
        }
