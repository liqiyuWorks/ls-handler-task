# FIS Token更新指南

## 问题诊断

当前所有FIS API都返回401认证失败，这是因为认证token已过期。

## 解决方案

### 1. 检查当前Token状态

```bash
python check_token.py
```

### 2. 更新Token

```bash
python update_fis_token.py
```

按照提示输入新的FIS token。

### 3. 测试修复结果

```bash
python test_fis_products.py
```

## 获取新Token的步骤

1. **访问FIS系统**
   - 登录到FIS管理后台
   - 或者联系FIS技术支持

2. **获取认证Token**
   - 从FIS系统获取新的JWT token
   - 确保token有足够的权限访问API

3. **更新Token**
   - 运行 `python update_fis_token.py`
   - 输入新的token
   - 系统会自动测试token有效性

## 验证修复

运行以下命令验证所有产品类型都能正常工作：

```bash
# 测试单个产品
python -c "
from tasks.aquabridge.subtasks.spider_fis_trade_data import SpiderFisDailyTradeData
spider = SpiderFisDailyTradeData('C5TC')
result = spider.run()
print(f'C5TC: {\"成功\" if result else \"失败\"}')
"

# 测试所有产品
python -c "
from tasks.aquabridge.subtasks.spider_fis_trade_data import SpiderAllFisDailyTradeData
all_spider = SpiderAllFisDailyTradeData()
results = all_spider.run_all()
for product, success in results.items():
    print(f'{product}: {\"成功\" if success else \"失败\"}')
"
```

## 常见问题

### Q: Token在哪里获取？
A: 需要从FIS系统管理员或技术支持处获取新的认证token。

### Q: Token多久过期？
A: 根据JWT标准，token通常有24小时的过期时间。

### Q: 如何自动更新Token？
A: 目前需要手动更新。未来可以考虑实现自动刷新机制。

## 技术细节

- **认证方式**: JWT Bearer Token
- **API端点**: `https://livepricing-prod2.azurewebsites.net/api/v1/chartData/`
- **产品ID**: C5TC(1), P4TC(12), P5TC(39)
- **Token存储**: 环境变量 `FIS_FALLBACK_TOKEN`
