#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
策略盈亏计算模块
实现各种交易策略的盈亏计算公式
"""

from typing import Optional
import logging

class PnLCalculator:
    """盈亏计算器"""
    
    @staticmethod
    def calculate_futures_pnl(strategy: str, opening_price: float, settlement_price: float, volume: int) -> float:
        """
        计算期货盈亏
        
        Args:
            strategy: 交易方向 ("多头" 或 "空头")
            opening_price: 开仓价格
            settlement_price: 结算价格
            volume: 手数
            
        Returns:
            盈亏金额
        """
        if strategy == "多头":
            # 多头: (结算价 - 开仓价) × 手数
            return (settlement_price - opening_price) * volume
        elif strategy == "空头":
            # 空头: (开仓价 - 结算价) × 手数
            return (opening_price - settlement_price) * volume
        else:
            logging.warning(f"未知的期货策略: {strategy}")
            return 0.0
    
    @staticmethod
    def calculate_call_option_pnl(is_long: bool, strike_price: float, settlement_price: float, 
                                volume: int, premium: float) -> float:
        """
        计算看涨期权盈亏
        
        Args:
            is_long: 是否为多头 (True: 买入看涨期权, False: 卖出看涨期权)
            strike_price: 行权价
            settlement_price: 结算价格
            volume: 手数
            premium: 权利金
            
        Returns:
            盈亏金额
        """
        # 计算内在价值
        intrinsic_value = max(0, settlement_price - strike_price)
        
        if is_long:
            # 买入看涨期权: Max(0, 结算价 - 行权价) × 手数 - 权利金
            # 这里的premium是总权利金
            return intrinsic_value * volume - premium
        else:
            # 卖出看涨期权: 权利金 - Max(0, 结算价 - 行权价) × 手数
            # 这里的premium是总权利金
            return premium - intrinsic_value * volume
    
    @staticmethod
    def calculate_put_option_pnl(is_long: bool, strike_price: float, settlement_price: float, 
                               volume: int, premium: float) -> float:
        """
        计算看跌期权盈亏
        
        Args:
            is_long: 是否为多头 (True: 买入看跌期权, False: 卖出看跌期权)
            strike_price: 行权价
            settlement_price: 结算价格
            volume: 手数
            premium: 权利金
            
        Returns:
            盈亏金额
        """
        # 计算内在价值
        intrinsic_value = max(0, strike_price - settlement_price)
        
        if is_long:
            # 买入看跌期权: Max(0, 行权价 - 结算价) × 手数 - 权利金
            # 这里的premium是总权利金
            return intrinsic_value * volume - premium
        else:
            # 卖出看跌期权: 权利金 - Max(0, 行权价 - 结算价) × 手数
            # 这里的premium是总权利金
            return premium - intrinsic_value * volume
    
    @classmethod
    def calculate_position_pnl(cls, strategy: str, buy_sell: str, opening_price: float, 
                             settlement_price: float, volume: int, 
                             strike_price: Optional[float] = None, 
                             premium: Optional[float] = None) -> float:
        """
        计算持仓盈亏
        
        Args:
            strategy: 交易类型 ("Future", "Call", "Put")
            buy_sell: 交易方向 ("多头", "空头")
            opening_price: 开仓价格
            settlement_price: 结算价格
            volume: 手数
            strike_price: 行权价 (期权需要)
            premium: 权利金 (期权需要)
            
        Returns:
            盈亏金额
        """
        try:
            if strategy == "Future":
                return cls.calculate_futures_pnl(buy_sell, opening_price, settlement_price, volume)
            
            elif strategy == "Call":
                if strike_price is None or premium is None:
                    logging.warning("看涨期权缺少行权价或权利金信息")
                    return 0.0
                is_long = (buy_sell == "多头")
                return cls.calculate_call_option_pnl(is_long, strike_price, settlement_price, volume, premium)
            
            elif strategy == "Put":
                if strike_price is None or premium is None:
                    logging.warning("看跌期权缺少行权价或权利金信息")
                    return 0.0
                is_long = (buy_sell == "多头")
                return cls.calculate_put_option_pnl(is_long, strike_price, settlement_price, volume, premium)
            
            else:
                logging.warning(f"未知的交易类型: {strategy}")
                return 0.0
                
        except Exception as e:
            logging.error(f"计算盈亏时发生错误: {str(e)}")
            return 0.0
    
    @staticmethod
    def calculate_weighted_average_price(existing_price: float, existing_volume: int, 
                                       new_price: float, new_volume: int) -> float:
        """
        计算加权平均价格
        
        Args:
            existing_price: 现有平均价格
            existing_volume: 现有持仓量
            new_price: 新开仓价格
            new_volume: 新开仓量
            
        Returns:
            加权平均价格
        """
        if existing_volume == 0:
            return new_price
        
        total_cost = (existing_price * existing_volume) + (new_price * new_volume)
        total_volume = existing_volume + new_volume
        
        return total_cost / total_volume if total_volume > 0 else 0.0
