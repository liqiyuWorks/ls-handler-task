#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FFA模拟交易系统主程序 - FastAPI后端
"""

from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from typing import List, Dict
from contextlib import asynccontextmanager
import uvicorn
import os

from database import get_db, create_tables, DatabaseManager
from models import AccountCreate, TradeRequest, AccountResponse, TradeResponse, PositionResponse, AccountSummary, UserCreate, UserLogin, UserResponse, Token, User, SettlementStatementRequest, SettlementStatementResponse, SettlementStatementDetail, ClosedTradeDetail, PnLChartData, FloatingPnLPoint, CumulativePnLPoint
from trading_engine import TradingEngine
from auth import authenticate_user, create_access_token, get_current_active_user_dependency, ACCESS_TOKEN_EXPIRE_MINUTES
from config import CONTRACT_CONFIG, STRATEGY_CONFIG, MONTH_CONFIG
from datetime import timedelta

# 创建模板和静态文件目录
templates = Jinja2Templates(directory="templates")
os.makedirs("static", exist_ok=True)
os.makedirs("templates", exist_ok=True)

# 初始化交易引擎
trading_engine = TradingEngine()
db_manager = DatabaseManager()

# 创建数据库表
create_tables()

# 默认账户ID（简化处理，实际应该有用户认证）
DEFAULT_ACCOUNT_ID = 1

@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时执行
    # 创建默认管理员用户（如果不存在）
    admin_user = db_manager.get_user_by_username("admin")
    if not admin_user:
        try:
            admin_user = db_manager.create_user(
                username="admin",
                email="admin@ffa.com",
                password="admin123",
                full_name="系统管理员",
                is_admin=True
            )
            print("✅ 创建默认管理员用户: admin/admin123")
        except Exception as e:
            print(f"⚠️ 创建默认管理员用户失败: {e}")
    
    # 为管理员创建默认账户（如果不存在）
    if admin_user:
        account = db_manager.get_account_by_name("默认账户")
        if not account:
            try:
                db_manager.create_account("默认账户", 1000000, admin_user.id)
                print("✅ 创建默认账户")
            except Exception as e:
                print(f"⚠️ 创建默认账户失败: {e}")
    
    yield
    # 关闭时执行（如果需要清理资源）

# 创建FastAPI应用
app = FastAPI(title="FFA模拟交易系统", version="1.0.0", lifespan=lifespan)

# 获取依赖函数
get_current_active_user = get_current_active_user_dependency()

# API路由
@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    """主页"""
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """登录页面"""
    return templates.TemplateResponse("login.html", {"request": request})

@app.post("/api/register", response_model=UserResponse)
async def register(user: UserCreate, db: Session = Depends(get_db)):
    """用户注册"""
    try:
        new_user = db_manager.create_user(
            username=user.username,
            email=user.email,
            password=user.password,
            full_name=user.full_name
        )
        return new_user
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="注册失败")

@app.post("/api/login")
async def login(user_credentials: UserLogin, db: Session = Depends(get_db)):
    """用户登录"""
    try:
        print(f"Login attempt for user: {user_credentials.username}")
        
        # 直接查询用户
        user = db.query(User).filter(User.username == user_credentials.username).first()
        print(f"User found: {user is not None}")
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="用户名或密码错误",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # 验证密码
        if not user.check_password(user_credentials.password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="用户名或密码错误",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        print(f"Password verified for user: {user.username}")
        
        # 创建简单的token
        access_token = create_access_token(data={"sub": user.username})
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"Login error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"登录失败: {str(e)}")

@app.get("/api/me", response_model=UserResponse)
async def read_users_me(current_user: User = Depends(get_current_active_user)):
    """获取当前用户信息"""
    return current_user

@app.get("/api/users/me/accounts")
async def get_my_accounts(current_user: User = Depends(get_current_active_user)):
    """获取当前用户的所有账户"""
    accounts = db_manager.get_user_accounts(current_user.id)
    return accounts

@app.post("/api/accounts/{account_id}/reset")
async def reset_account_data(account_id: int, current_user: User = Depends(get_current_active_user)):
    """重置账户数据到初始状态"""
    try:
        result = db_manager.reset_account_data(account_id, current_user.id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"重置失败: {str(e)}")

@app.get("/api/accounts", response_model=List[AccountResponse])
async def get_accounts(current_user: User = Depends(get_current_active_user)):
    """获取当前用户的所有账户"""
    accounts = db_manager.get_user_accounts(current_user.id)
    return accounts

@app.get("/api/accounts/{account_id}", response_model=AccountResponse)
async def get_account(account_id: int, current_user: User = Depends(get_current_active_user)):
    """获取指定账户"""
    account = db_manager.get_account(account_id)
    if not account:
        raise HTTPException(status_code=404, detail="账户不存在")
    if account.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权访问此账户")
    return account

@app.post("/api/accounts", response_model=AccountResponse)
async def create_account(account: AccountCreate, current_user: User = Depends(get_current_active_user)):
    """创建新账户"""
    try:
        new_account = db_manager.create_account(account.account_name, account.initial_equity, current_user.id)
        return new_account
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/accounts/{account_id}/summary")
async def get_account_summary(account_id: int, current_user: User = Depends(get_current_active_user)):
    """获取账户汇总信息"""
    account = db_manager.get_account(account_id)
    if not account:
        raise HTTPException(status_code=404, detail="账户不存在")
    if account.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权访问此账户")
    
    summary = trading_engine.get_account_summary(account_id)
    return summary

# 结算单相关API
@app.post("/api/settlement-statements", response_model=SettlementStatementResponse)
async def create_settlement_statement(
    settlement_request: SettlementStatementRequest,
    current_user: User = Depends(get_current_active_user)
):
    """创建结算单"""
    # 验证账户权限
    account = db_manager.get_account(settlement_request.account_id)
    if not account or account.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权访问此账户")
    
    # 计算结算单数据
    settlement_data = db_manager.calculate_settlement_data(
        settlement_request.account_id,
        settlement_request.period_start,
        settlement_request.period_end
    )
    
    # 创建结算单
    settlement_data.update({
        "account_id": settlement_request.account_id,
        "statement_period": settlement_request.statement_period,
        "period_start": settlement_request.period_start,
        "period_end": settlement_request.period_end
    })
    
    settlement = db_manager.create_settlement_statement(settlement_data)
    return settlement

@app.get("/api/settlement-statements", response_model=List[SettlementStatementResponse])
async def get_settlement_statements(
    account_id: int,
    current_user: User = Depends(get_current_active_user)
):
    """获取账户的结算单列表"""
    # 验证账户权限
    account = db_manager.get_account(account_id)
    if not account or account.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权访问此账户")
    
    statements = db_manager.get_settlement_statements(account_id)
    return statements

@app.get("/api/settlement-statements/{statement_id}", response_model=SettlementStatementResponse)
async def get_settlement_statement(
    statement_id: int,
    current_user: User = Depends(get_current_active_user)
):
    """获取特定结算单"""
    statement = db_manager.get_settlement_statement(statement_id)
    if not statement:
        raise HTTPException(status_code=404, detail="结算单不存在")
    
    # 验证账户权限
    account = db_manager.get_account(statement.account_id)
    if not account or account.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权访问此结算单")
    
    return statement

@app.get("/api/settlement-statements/{statement_id}/detail", response_model=SettlementStatementDetail)
async def get_settlement_statement_detail(
    statement_id: int,
    current_user: User = Depends(get_current_active_user)
):
    """获取结算单详情（包含交易明细）"""
    statement = db_manager.get_settlement_statement(statement_id)
    if not statement:
        raise HTTPException(status_code=404, detail="结算单不存在")
    
    # 验证账户权限
    account = db_manager.get_account(statement.account_id)
    if not account or account.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权访问此结算单")
    
    detail = db_manager.get_settlement_statement_detail(statement_id)
    return detail

@app.get("/api/settlement-statements/{statement_id}/closed-trades", response_model=List[ClosedTradeDetail])
async def get_settlement_closed_trades(
    statement_id: int,
    current_user: User = Depends(get_current_active_user)
):
    """获取结算单的已平仓交易明细"""
    statement = db_manager.get_settlement_statement(statement_id)
    if not statement:
        raise HTTPException(status_code=404, detail="结算单不存在")
    
    # 验证账户权限
    account = db_manager.get_account(statement.account_id)
    if not account or account.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权访问此结算单")
    
    closed_trades = db_manager.get_closed_trades_for_settlement(
        statement.account_id,
        statement.period_start,
        statement.period_end
    )
    return closed_trades

@app.get("/api/pnl-chart-data", response_model=PnLChartData)
async def get_pnl_chart_data(
    account_id: int,
    days: int = 30,
    current_user: User = Depends(get_current_active_user)
):
    """获取盈亏曲线图表数据"""
    # 验证账户权限
    account = db_manager.get_account(account_id)
    if not account or account.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权访问此账户")
    
    chart_data = db_manager.get_pnl_chart_data(account_id, days)
    return chart_data

@app.get("/api/floating-pnl-data", response_model=List[FloatingPnLPoint])
async def get_floating_pnl_data(
    account_id: int,
    days: int = 30,
    current_user: User = Depends(get_current_active_user)
):
    """获取浮动盈亏曲线数据"""
    # 验证账户权限
    account = db_manager.get_account(account_id)
    if not account or account.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权访问此账户")
    
    floating_pnl_data = db_manager.get_floating_pnl_data(account_id, days)
    return floating_pnl_data

@app.get("/api/cumulative-pnl-data")
async def get_cumulative_pnl_data(
    account_id: int,
    days: int = 30,
    current_user: User = Depends(get_current_active_user)
):
    """获取累计实际盈亏曲线数据"""
    # 验证账户权限
    account = db_manager.get_account(account_id)
    if not account or account.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权访问此账户")
    
    cumulative_pnl_data = db_manager.get_cumulative_pnl_data(account_id, days)
    return cumulative_pnl_data

@app.post("/api/trades")
async def execute_trade(trade_request: TradeRequest, account_id: int, current_user: User = Depends(get_current_active_user)):
    """执行交易"""
    # 验证账户权限
    account = db_manager.get_account(account_id)
    if not account or account.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权访问此账户")
    
    # 构建交易数据，包含所有新字段
    trade_data = {
        # 新字段
        "contract": trade_request.contract,
        "month": trade_request.month,
        "trade_date": trade_request.trade_date,
        "strategy": trade_request.strategy,
        "action": trade_request.action,
        "buy_sell": trade_request.buy_sell,
        "future_price": trade_request.future_price,
        "strike_price": trade_request.strike_price,
        "premium": trade_request.premium,
        "volume": trade_request.volume,
        "short_volume": trade_request.short_volume,
        "long_volume": trade_request.long_volume,
        "commissions": trade_request.commissions,
        
        # 兼容性字段
        "contract_type": trade_request.contract_type or trade_request.contract,
        "contract_month": trade_request.contract_month or trade_request.month,
        "contract_name": f"{trade_request.contract}{trade_request.month}合约",
        "price": trade_request.price or trade_request.future_price
    }
    
    success, message, trade = trading_engine.execute_trade(account_id, trade_data)
    
    if success:
        return {"success": True, "message": message, "trade": trade}
    else:
        raise HTTPException(status_code=400, detail=message)

@app.get("/api/trades", response_model=List[TradeResponse])
async def get_trades(account_id: int, current_user: User = Depends(get_current_active_user), limit: int = 10):
    """获取交易记录"""
    # 验证账户权限
    account = db_manager.get_account(account_id)
    if not account or account.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权访问此账户")
    
    trades = db_manager.get_account_trades(account_id, limit)
    return trades

@app.get("/api/positions", response_model=List[PositionResponse])
async def get_positions(account_id: int, current_user: User = Depends(get_current_active_user)):
    """获取持仓信息"""
    # 验证账户权限
    account = db_manager.get_account(account_id)
    if not account or account.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权访问此账户")
    
    positions = db_manager.get_account_positions(account_id)
    return positions

@app.get("/api/contracts")
async def get_contracts():
    """获取合约配置"""
    return {
        "contract_types": CONTRACT_CONFIG,
        "strategies": STRATEGY_CONFIG,
        "months": MONTH_CONFIG
    }

@app.put("/api/positions/{position_id}/settlement")
async def update_settlement_price(position_id: int, settlement_price: float, account_id: int = DEFAULT_ACCOUNT_ID):
    """更新持仓的结算价并重新计算盈亏"""
    try:
        # 获取持仓
        position = db_manager.get_position_by_id(position_id)
        if not position or position.account_id != account_id:
            raise HTTPException(status_code=404, detail="持仓不存在")
        
        # 更新结算价
        position.daily_settlement_price = settlement_price
        
        # 重新计算盈亏
        volume = position.open_interest if position.open_interest > 0 else abs(position.position_volume)
        opening_price = position.future_price if position.future_price > 0 else position.average_price
        
        from trading_engine import TradingEngine
        trading_engine = TradingEngine()
        
        unrealized_pnl = trading_engine.calculate_unrealized_pnl(position, settlement_price)
        position.unrealized_pnl = unrealized_pnl
        
        # 保存更新
        db_manager.update_position(position)
        
        return {"success": True, "message": "结算价更新成功", "unrealized_pnl": unrealized_pnl}
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.delete("/api/trades/{trade_id}")
async def delete_trade(trade_id: str, account_id: int = DEFAULT_ACCOUNT_ID):
    """删除交易记录（简化实现）"""
    # 这里简化处理，实际应该回滚交易并更新持仓
    return {"message": "交易删除功能待实现"}

# 静态文件服务
app.mount("/static", StaticFiles(directory="static"), name="static")

# 健康检查端点
@app.get("/health")
async def health_check():
    """健康检查端点"""
    try:
        # 检查数据库连接
        db = next(get_db())
        db.execute("SELECT 1")
        return {"status": "healthy", "message": "服务正常运行"}
    except Exception as e:
        return {"status": "unhealthy", "message": f"服务异常: {str(e)}"}

if __name__ == "__main__":
    uvicorn.run(
        "main:app", 
        host="0.0.0.0", 
        port=8000, 
        reload=False,
        loop="asyncio"  # 使用asyncio而不是uvloop
    )
