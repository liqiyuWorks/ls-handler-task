#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FFA模拟交易系统简化演示
不依赖外部库，展示核心交易逻辑
"""

from datetime import datetime
from typing import Dict, Tuple, Optional
import json

class SimpleFFASystem:
    """简化的FFA交易系统"""
    
    def __init__(self):
        self.initial_equity = 1000000
        self.current_equity = 1000000
        self.commission_rate = 0.001  # 0.1%
        self.clearing_fee = 20
        self.trades = []
        self.positions = {}
        
    def calculate_fees(self, price: float, volume: int) -> Tuple[float, float, float]:
        """计算交易费用"""
        commission = price * volume * self.commission_rate
        clearing_fee = self.clearing_fee
        total_fees = commission + clearing_fee
        return commission, clearing_fee, total_fees
    
    def calculate_trade_amount(self, price: float, volume: int, strategy: str) -> float:
        """计算交易总额"""
        _, _, total_fees = self.calculate_fees(price, volume)
        
        if strategy in ["开多", "平空"]:  # 买入
            return price * volume - total_fees
        else:  # 卖出
            return price * volume - total_fees
    
    def execute_trade(self, contract_type: str, contract_month: str, 
                     strategy: str, price: float, volume: int) -> Dict:
        """执行交易"""
        # 生成交易ID
        trade_id = str(int(datetime.now().timestamp() * 1000))
        
        # 计算费用
        commission, clearing_fee, total_fees = self.calculate_fees(price, volume)
        total_amount = self.calculate_trade_amount(price, volume, strategy)
        
        # 获取当前持仓
        position_key = f"{contract_type}_{contract_month}"
        current_position = self.positions.get(position_key, 0)
        
        # 计算新持仓
        if strategy in ["开多", "平空"]:
            new_position = current_position + volume
        else:
            new_position = current_position - volume
        
        # 创建交易记录
        trade = {
            "trade_id": trade_id,
            "contract_type": contract_type,
            "contract_month": contract_month,
            "contract_name": f"{contract_month}合约",
            "strategy": strategy,
            "price": price,
            "volume": volume,
            "commission": commission,
            "clearing_fee": clearing_fee,
            "total_fees": total_fees,
            "total_amount": total_amount,
            "previous_position": current_position,
            "current_position": new_position,
            "trade_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        # 更新持仓
        if new_position != 0:
            self.positions[position_key] = new_position
        else:
            self.positions.pop(position_key, None)
        
        # 更新权益
        self.current_equity -= total_fees
        
        # 记录交易
        self.trades.append(trade)
        
        return {
            "success": True,
            "message": "交易执行成功",
            "trade": trade
        }
    
    def get_account_summary(self) -> Dict:
        """获取账户汇总"""
        total_pnl = self.current_equity - self.initial_equity
        recommended_volume = max(1, int(self.current_equity / 10000))
        
        return {
            "initial_equity": self.initial_equity,
            "current_equity": self.current_equity,
            "total_pnl": total_pnl,
            "recommended_volume": recommended_volume,
            "positions": self.positions,
            "total_trades": len(self.trades)
        }
    
    def print_trade_result(self, result: Dict):
        """打印交易结果"""
        trade = result["trade"]
        print(f"\n交易ID: {trade['trade_id']}")
        print(f"合约: {trade['contract_type']} - {trade['contract_month']}")
        print(f"策略: {trade['strategy']}")
        print(f"价格: ¥{trade['price']:.2f}")
        print(f"数量: {trade['volume']}手")
        print(f"佣金: ¥{trade['commission']:.2f}")
        print(f"清算费: ¥{trade['clearing_fee']:.2f}")
        print(f"总费用: ¥{trade['total_fees']:.2f}")
        print(f"交易总额: ¥{trade['total_amount']:.2f}")
        print(f"持仓变化: {trade['previous_position']} → {trade['current_position']}")
        print(f"交易时间: {trade['trade_date']}")
    
    def print_account_summary(self):
        """打印账户汇总"""
        summary = self.get_account_summary()
        print(f"\n账户汇总:")
        print(f"初始权益: ¥{summary['initial_equity']:,}")
        print(f"当前权益: ¥{summary['current_equity']:,}")
        print(f"累计盈亏: ¥{summary['total_pnl']:,}")
        print(f"推荐手数: {summary['recommended_volume']}")
        print(f"总交易次数: {summary['total_trades']}")
        
        if summary['positions']:
            print(f"\n当前持仓:")
            for key, position in summary['positions'].items():
                print(f"  {key}: {position}手")
        else:
            print(f"\n当前无持仓")

def demo_trading():
    """演示交易流程"""
    print("=" * 60)
    print("FFA模拟交易系统 - 交易演示")
    print("=" * 60)
    
    # 创建交易系统
    system = SimpleFFASystem()
    
    # 显示初始状态
    system.print_account_summary()
    
    # 演示交易1: 开多C5TC 10月合约
    print(f"\n{'='*20} 交易1: 开多C5TC 10月合约 {'='*20}")
    result1 = system.execute_trade("C5TC", "10月", "开多", 100, 100)
    system.print_trade_result(result1)
    
    # 显示交易后状态
    system.print_account_summary()
    
    # 演示交易2: 加仓开多
    print(f"\n{'='*20} 交易2: 加仓开多C5TC 10月合约 {'='*20}")
    result2 = system.execute_trade("C5TC", "10月", "开多", 105, 50)
    system.print_trade_result(result2)
    
    # 显示交易后状态
    system.print_account_summary()
    
    # 演示交易3: 开空P4TC 11月合约
    print(f"\n{'='*20} 交易3: 开空P4TC 11月合约 {'='*20}")
    result3 = system.execute_trade("P4TC", "11月", "开空", 95, 80)
    system.print_trade_result(result3)
    
    # 显示交易后状态
    system.print_account_summary()
    
    # 演示交易4: 部分平仓
    print(f"\n{'='*20} 交易4: 部分平仓C5TC 10月合约 {'='*20}")
    result4 = system.execute_trade("C5TC", "10月", "平多", 110, 75)
    system.print_trade_result(result4)
    
    # 显示最终状态
    system.print_account_summary()
    
    # 显示所有交易记录
    print(f"\n{'='*20} 交易记录汇总 {'='*20}")
    for i, trade in enumerate(system.trades, 1):
        print(f"\n交易{i}:")
        print(f"  ID: {trade['trade_id']}")
        print(f"  {trade['contract_type']} {trade['contract_month']} {trade['strategy']}")
        print(f"  价格: ¥{trade['price']:.2f} × {trade['volume']}手 = ¥{trade['total_amount']:.2f}")
        print(f"  费用: ¥{trade['total_fees']:.2f}")

def demo_calculation():
    """演示计算逻辑"""
    print(f"\n{'='*20} 费用计算演示 {'='*20}")
    
    system = SimpleFFASystem()
    
    # 测试不同价格的费用计算
    test_cases = [
        (100, 100),  # 价格100，数量100
        (150, 50),   # 价格150，数量50
        (80, 200),   # 价格80，数量200
    ]
    
    for price, volume in test_cases:
        commission, clearing_fee, total_fees = system.calculate_fees(price, volume)
        trade_amount_buy = system.calculate_trade_amount(price, volume, "开多")
        trade_amount_sell = system.calculate_trade_amount(price, volume, "开空")
        
        print(f"\n价格: ¥{price:.2f}, 数量: {volume}手")
        print(f"  佣金: ¥{commission:.2f} (0.1%)")
        print(f"  清算费: ¥{clearing_fee:.2f}")
        print(f"  总费用: ¥{total_fees:.2f}")
        print(f"  买入总额: ¥{trade_amount_buy:.2f}")
        print(f"  卖出总额: ¥{trade_amount_sell:.2f}")

if __name__ == "__main__":
    # 运行演示
    demo_trading()
    demo_calculation()
    
    print(f"\n{'='*60}")
    print("演示完成！")
    print("这个简化版本展示了FFA交易系统的核心逻辑:")
    print("1. 交易费用计算 (佣金0.1% + 清算费¥20)")
    print("2. 持仓管理 (开多/开空/平多/平空)")
    print("3. 账户权益跟踪")
    print("4. 交易记录管理")
    print(f"{'='*60}")
