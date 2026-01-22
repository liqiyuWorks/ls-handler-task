# Alpaca 实时股票价格集成说明

## 概述

本项目已集成 Alpaca Market Data API，可以通过 WebSocket 实时获取股票价格数据。

## 功能特性

- ✅ 实时股票价格流（通过 Alpaca WebSocket API）
- ✅ 自动重连机制
- ✅ 失败时自动回退到模拟数据
- ✅ 支持多股票符号订阅
- ✅ 自动计算涨跌幅

## 配置

API 密钥已配置在 `config/alpacaConfig.ts` 文件中：

```typescript
export const ALPACA_CONFIG = {
  API_KEY: 'PKRWSF2TIWC7Q5N5A5YA25ZI5X',
  SECRET_KEY: '9hWKiNHwb3Ls7wk1bNwybUB4yHArddYsDvRLT8PKuLu4',
  // ...
};
```

### 安全提示

⚠️ **重要**：在生产环境中，建议：
1. 使用环境变量存储 API keys
2. 不要将包含 API keys 的代码提交到公共仓库
3. 考虑使用后端代理来保护 API keys

## 使用方法

### 自动集成

系统已自动集成到 `MarketDataService`，无需额外配置。当应用启动时：

1. 自动尝试连接到 Alpaca WebSocket
2. 如果连接成功，使用实时数据
3. 如果连接失败，自动回退到模拟数据

### 在代码中使用

```typescript
import { marketDataService } from './services/marketDataService';

// 订阅价格更新
const unsubscribe = marketDataService.subscribe((quotes) => {
  console.log('实时价格更新:', quotes);
  // quotes 格式: { [symbol]: { price, change, changePercent } }
});

// 添加要跟踪的股票
marketDataService.addSymbol('AAPL');
marketDataService.addSymbol('GOOGL');

// 取消订阅
unsubscribe();
```

## 架构说明

### 文件结构

```
services/
  ├── alpacaService.ts      # Alpaca WebSocket 服务
  └── marketDataService.ts  # 统一的市场数据服务（集成 Alpaca）

config/
  └── alpacaConfig.ts       # Alpaca API 配置
```

### 工作流程

1. **初始化**：`MarketDataService` 创建 `AlpacaService` 实例
2. **连接**：尝试连接到 Alpaca WebSocket
3. **认证**：发送 API key 和 secret key 进行认证
4. **订阅**：当添加股票符号时，自动订阅实时报价
5. **更新**：收到实时数据后，更新价格并通知所有订阅者
6. **重连**：连接断开时自动尝试重连（最多5次）

### 数据格式

Alpaca 返回的实时数据格式：

```typescript
interface Quote {
  symbol: string;
  price: number;        // 当前价格
  change: number;       // 涨跌金额（相对于基础价格）
  changePercent: number; // 涨跌百分比
}
```

## 故障排除

### 连接失败

如果 Alpaca 连接失败，系统会自动：
- 回退到模拟数据
- 在控制台输出错误信息
- 继续正常运行（使用模拟价格）

### 常见问题

1. **没有收到价格更新**
   - 检查浏览器控制台是否有错误
   - 确认 API keys 是否正确
   - 确认股票符号格式正确（例如：'AAPL' 而不是 'AAPL.US'）

2. **连接频繁断开**
   - 检查网络连接
   - 确认 Alpaca 账户状态正常
   - 查看控制台的错误信息

3. **价格不更新**
   - 确认股票代码在 Alpaca 支持的市场中
   - 检查是否在交易时间内（某些数据可能只在交易时间更新）

## API 限制

请注意 Alpaca API 的使用限制：
- 免费账户可能有请求频率限制
- 某些数据可能需要付费订阅
- 实时数据可能只在交易时间内可用

## 更多信息

- [Alpaca Market Data API 文档](https://alpaca.markets/docs/market-data/)
- [Alpaca WebSocket API 文档](https://alpaca.markets/docs/api-documentation/api-v2/market-data/streaming/)
