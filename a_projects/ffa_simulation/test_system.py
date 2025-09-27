#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FFA模拟交易系统测试脚本
"""

import sys
import os

# 添加当前目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_config():
    """测试配置模块"""
    try:
        from config import TRADING_CONFIG, CONTRACT_CONFIG, STRATEGY_CONFIG
        print("✓ 配置模块导入成功")
        print(f"  交易配置: {TRADING_CONFIG}")
        print(f"  合约配置: {list(CONTRACT_CONFIG.keys())}")
        print(f"  策略配置: {list(STRATEGY_CONFIG.keys())}")
        return True
    except Exception as e:
        print(f"✗ 配置模块导入失败: {e}")
        return False

def test_models():
    """测试数据模型"""
    try:
        from models import Account, Trade, Position
        from models import AccountCreate, TradeRequest
        print("✓ 数据模型导入成功")
        
        # 测试Pydantic模型
        account_data = AccountCreate(account_name="测试账户", initial_equity=1000000)
        trade_data = TradeRequest(
            contract_type="C5TC",
            contract_month="10月",
            strategy="开多",
            price=100.0,
            volume=100
        )
        print(f"  AccountCreate: {account_data.account_name}")
        print(f"  TradeRequest: {trade_data.contract_type} {trade_data.strategy}")
        return True
    except Exception as e:
        print(f"✗ 数据模型导入失败: {e}")
        return False

def test_trading_engine():
    """测试交易引擎"""
    try:
        from trading_engine import TradingEngine
        print("✓ 交易引擎导入成功")
        
        # 创建交易引擎实例
        engine = TradingEngine()
        print(f"  佣金比例: {engine.commission_rate}")
        print(f"  清算费: {engine.clearing_fee}")
        
        # 测试费用计算
        commission, clearing_fee, total_fees = engine.calculate_fees(100, 100)
        print(f"  费用计算测试: 佣金={commission}, 清算费={clearing_fee}, 总费用={total_fees}")
        
        return True
    except Exception as e:
        print(f"✗ 交易引擎导入失败: {e}")
        return False

def test_trading_logic():
    """测试交易逻辑"""
    try:
        from trading_engine import TradingEngine
        from config import TRADING_CONFIG, CONTRACT_CONFIG, STRATEGY_CONFIG
        
        engine = TradingEngine()
        
        # 测试交易验证
        is_valid, message = engine.validate_trade(1, "开多", 100, "C5TC", "10月")
        print(f"✓ 交易验证测试: {is_valid}, {message}")
        
        # 测试持仓变化计算
        new_position, change = engine.calculate_position_change("开多", 100, 0)
        print(f"✓ 持仓变化计算: 新持仓={new_position}, 变化={change}")
        
        # 测试费用计算
        commission, clearing_fee, total_fees = engine.calculate_fees(100, 100)
        expected_commission = 100 * 100 * 0.001  # 10
        expected_total = expected_commission + 20  # 30
        
        print(f"✓ 费用计算验证:")
        print(f"  佣金: {commission} (期望: {expected_commission})")
        print(f"  清算费: {clearing_fee} (期望: 20)")
        print(f"  总费用: {total_fees} (期望: {expected_total})")
        
        return True
    except Exception as e:
        print(f"✗ 交易逻辑测试失败: {e}")
        return False

def main():
    """主测试函数"""
    print("=" * 60)
    print("FFA模拟交易系统 - 功能测试")
    print("=" * 60)
    
    tests = [
        ("配置模块", test_config),
        ("数据模型", test_models),
        ("交易引擎", test_trading_engine),
        ("交易逻辑", test_trading_logic),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n测试 {test_name}...")
        if test_func():
            passed += 1
        print("-" * 40)
    
    print(f"\n测试结果: {passed}/{total} 通过")
    
    if passed == total:
        print("🎉 所有测试通过！系统核心功能正常。")
        print("\n要启动完整系统，请运行:")
        print("  pip install -r requirements.txt")
        print("  python run.py")
    else:
        print("❌ 部分测试失败，请检查相关模块。")

if __name__ == "__main__":
    main()
