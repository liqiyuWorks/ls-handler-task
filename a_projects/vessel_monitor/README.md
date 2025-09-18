# 智能航运监控系统

## 功能特点

### 🚢 多船监控
- 支持同时监控多艘船舶
- 每艘船可独立配置监控参数
- 实时状态跟踪和历史记录

### ⚡ 智能预警
- **停航检测**: 航速低于停航阈值时触发
- **降速预警**: 航速显著下降时提醒
- **航速恢复**: 船舶恢复正常航速时通知
- **数据异常**: API数据异常时告警

### ⏰ 时效性优化
- 可配置检查间隔（30秒-10分钟）
- 预警冷却机制避免重复告警
- 实时日志记录和状态追踪
- 支持不同船舶不同监控频率

### 📊 操作效率提升
- 结构化数据存储和查询
- 详细的监控摘要报告
- 可扩展的通知系统（邮件、钉钉、短信）
- 完整的错误处理和日志记录

## 使用方法

### 1. 基本使用
```python
from vessel_warn import VesselMonitor, VesselConfig

# 创建监控器
monitor = VesselMonitor()

# 添加船舶
vessel = VesselConfig(
    mmsi="367560102",
    name="货轮001",
    speed_threshold=1.0,      # 停航阈值(节)
    slow_down_threshold=5.0,  # 降速阈值(节)
    normal_speed=12.0,        # 正常航速(节)
    check_interval=30,        # 检查间隔(秒)
    alert_cooldown=300        # 预警冷却时间(秒)
)

monitor.add_vessel(vessel)

# 开始监控
monitor.monitor_vessels()
```

### 2. 配置文件使用
```python
import json
from vessel_warn import VesselMonitor, VesselConfig

# 加载配置
with open('vessel_config.json', 'r', encoding='utf-8') as f:
    config = json.load(f)

monitor = VesselMonitor()

# 从配置文件添加船舶
for vessel_data in config['vessels']:
    vessel = VesselConfig(**vessel_data)
    monitor.add_vessel(vessel)

monitor.monitor_vessels()
```

### 3. 直接运行
```bash
python vessel_warn.py
```

## 配置参数说明

### VesselConfig 参数
- `mmsi`: 船舶MMSI号（必填）
- `name`: 船舶名称（可选）
- `speed_threshold`: 停航阈值，单位节（默认1.0）
- `slow_down_threshold`: 降速阈值，单位节（默认5.0）
- `normal_speed`: 正常航速，单位节（默认10.0）
- `check_interval`: 检查间隔，单位秒（默认30）
- `alert_cooldown`: 预警冷却时间，单位秒（默认300）

## 监控逻辑

1. **停航检测**: 当前航速 ≤ 停航阈值 且 上次航速 > 停航阈值
2. **降速检测**: 当前航速 ≤ 降速阈值 且 上次航速 > 降速阈值
3. **航速恢复**: 当前航速 > 正常航速 且 上次航速 ≤ 降速阈值
4. **冷却机制**: 同一船舶在冷却期内不会重复发送相同类型预警

## 日志和监控

- 所有操作记录到 `vessel_monitor.log` 文件
- 支持不同日志级别（DEBUG, INFO, WARNING, ERROR）
- 实时控制台输出和文件记录
- 监控摘要包含所有船舶状态信息

## 扩展功能

### 通知系统
可以扩展 `_send_notification` 方法支持：
- 邮件通知
- 钉钉/企业微信机器人
- 短信通知
- 数据库存储

### 数据存储
可以扩展数据存储功能：
- 历史航速数据
- 预警记录
- 船舶轨迹数据

## 注意事项

1. 确保API token有效且有足够权限
2. 根据实际业务需求调整监控参数
3. 建议在生产环境中使用配置文件管理
4. 定期检查日志文件大小，避免磁盘空间不足
