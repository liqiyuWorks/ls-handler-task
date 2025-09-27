# FFA模拟交易系统

基于FastAPI和现代前端技术的FFA（Forward Freight Agreement）模拟交易系统，提供完整的交易下单、持仓管理、盈亏计算等功能。
## 虚拟环境nav310
## 功能特点

### 🚢 交易功能
- **合约交易**: 支持C5TC、P4TC、S5TC等主要FFA合约
- **交易策略**: 开多、开空、平多、平空四种交易策略
- **实时计算**: 自动计算佣金、清算费、交易总额
- **持仓管理**: 实时更新持仓数量和平均价格

### 📊 账户管理
- **权益跟踪**: 实时显示初始权益、当前权益、累计盈亏
- **费用计算**: 自动计算佣金（0.1%）和清算费（¥20）
- **风险评估**: 提供推荐交易手数

### 💹 数据展示
- **持仓汇总**: 清晰显示当前所有持仓情况
- **交易历史**: 完整的交易记录和详情
- **实时更新**: 交易后自动刷新相关数据

## 技术架构

### 后端技术栈
- **FastAPI**: 现代高性能Python Web框架
- **SQLAlchemy**: ORM数据库操作
- **SQLite**: 轻量级数据库
- **Pydantic**: 数据验证和序列化

### 前端技术栈
- **HTML5/CSS3**: 现代Web标准
- **Bootstrap 5**: 响应式UI框架
- **JavaScript ES6**: 原生JavaScript
- **Font Awesome**: 图标库

## 项目结构

```
ffa_simulation/
├── main.py              # FastAPI主程序
├── models.py            # 数据模型定义
├── database.py          # 数据库连接和操作
├── trading_engine.py    # 交易引擎核心逻辑
├── config.py            # 系统配置
├── run.py               # 启动脚本
├── requirements.txt     # 依赖包列表
├── README.md           # 项目说明
├── templates/          # HTML模板
│   └── index.html      # 主页面
└── static/             # 静态资源
```

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 启动系统

```bash
python run.py
```

### 3. 访问系统

打开浏览器访问: http://localhost:8000

## 使用说明

### 交易下单
1. 选择合约类型（C5TC、P4TC、S5TC）
2. 选择合约月份（1月-12月）
3. 选择交易策略（开多、开空、平多、平空）
4. 输入交易价格和数量
5. 点击"提交交易"

### 查看持仓
- 切换到"持仓汇总"标签页
- 查看当前所有持仓的详细信息
- 包括持仓量、平均价格、未实现盈亏等

### 交易记录
- 切换到"交易记录"标签页
- 查看所有历史交易记录
- 包括交易ID、价格、数量、时间等详细信息

## 交易规则

### 合约配置
- **C5TC**: 5万吨级巴拿马型散货船航线
- **P4TC**: 7.4万吨级巴拿马型散货船航线  
- **S5TC**: 5.8万吨级超灵便型散货船航线

### 费用计算
- **佣金**: 交易价格 × 交易量 × 0.1%
- **清算费**: 固定¥20
- **总额**: 交易价格 × 交易量 - 佣金 - 清算费

### 交易限制
- 最小交易量: 1手
- 最大交易量: 10,000手
- 平仓数量不能超过持仓数量

## API接口

### 账户管理
- `GET /api/accounts` - 获取所有账户
- `GET /api/accounts/{id}` - 获取指定账户
- `POST /api/accounts` - 创建新账户
- `GET /api/accounts/{id}/summary` - 获取账户汇总

### 交易管理
- `POST /api/trades` - 执行交易
- `GET /api/trades` - 获取交易记录
- `DELETE /api/trades/{id}` - 删除交易记录

### 持仓管理
- `GET /api/positions` - 获取持仓信息

### 系统配置
- `GET /api/contracts` - 获取合约配置

## 配置说明

### 交易配置
```python
TRADING_CONFIG = {
    "initial_equity": 1000000,  # 初始权益
    "commission_rate": 0.001,   # 佣金比例 0.1%
    "clearing_fee": 20,         # 清算费
    "min_trade_volume": 1,      # 最小交易手数
    "max_trade_volume": 10000,  # 最大交易手数
}
```

### 合约配置
```python
CONTRACT_CONFIG = {
    "C5TC": {
        "name": "C5TC",
        "description": "C5TC航线",
        "multiplier": 100,
        "min_price_tick": 1,
    },
    # ... 其他合约
}
```

## 开发说明

### 数据库设计
- **accounts**: 账户信息表
- **trades**: 交易记录表
- **positions**: 持仓信息表

### 核心类说明
- **TradingEngine**: 交易引擎，处理所有交易逻辑
- **DatabaseManager**: 数据库管理器，处理数据持久化
- **Account/Trade/Position**: 数据模型类

### 扩展功能
- 可以添加更多FFA合约类型
- 可以实现实时价格数据接口
- 可以添加风险管理和风控功能
- 可以实现用户认证和权限管理

## 注意事项

1. **模拟交易**: 本系统为模拟交易系统，不涉及真实资金
2. **数据持久化**: 使用SQLite数据库，数据保存在本地
3. **价格数据**: 当前使用手动输入价格，实际应用中应接入实时行情
4. **风险控制**: 建议添加更完善的风险控制机制

## 许可证

MIT License

## 联系方式

如有问题或建议，请联系开发团队。
