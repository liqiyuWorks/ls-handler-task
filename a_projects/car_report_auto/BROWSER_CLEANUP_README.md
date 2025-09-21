# 浏览器进程清理优化说明

## 问题描述
原系统在使用 Playwright 进行浏览器自动化时，经常出现 Chrome 僵尸进程问题，导致：
- 系统资源浪费
- 内存泄漏
- 进程数量过多影响系统性能

## 优化方案

### 1. 进程清理机制
- **任务完成后自动清理**：每个任务完成后强制清理所有 Chrome 进程
- **异常处理清理**：即使任务失败也会清理 Chrome 进程
- **启动时清理**：程序启动时清理可能存在的僵尸进程

### 2. 浏览器启动参数优化
添加了以下参数来减少资源占用和防止僵尸进程：
```bash
--single-process          # 单进程模式，减少子进程
--no-zygote              # 禁用zygote进程
--disable-background-timer-throttling  # 禁用后台定时器节流
--disable-backgrounding-occluded-windows  # 禁用被遮挡窗口的后台处理
--disable-renderer-backgrounding  # 禁用渲染器后台处理
--memory-pressure-off    # 关闭内存压力检测
--max_old_space_size=512 # 限制V8堆内存大小
```

### 3. 进程监控和自动清理
- **后台监控线程**：每30秒检查一次Chrome进程数量
- **自动清理触发**：当Chrome进程超过10个时自动清理
- **信号处理**：程序退出时自动清理所有Chrome进程

### 4. 新增API接口

#### 获取进程状态
```http
GET /api/system/process-status
```
返回当前Chrome进程数量和详细信息。

#### 手动清理Chrome进程
```http
POST /api/system/cleanup-chrome
```
手动触发Chrome进程清理。

## 使用方法

### 1. 安装依赖
```bash
pip install psutil~=5.9.0
```

### 2. 运行测试
```bash
cd car_report_auto
python test_browser_cleanup.py
```

### 3. 启动服务
```bash
python car_report_modifier_web.py
```

## 监控和调试

### 1. 查看进程状态
访问 `http://localhost:8090/api/system/process-status` 查看当前Chrome进程状态。

### 2. 手动清理进程
发送POST请求到 `http://localhost:8090/api/system/cleanup-chrome` 手动清理Chrome进程。

### 3. 日志监控
程序会输出详细的清理日志，包括：
- 进程启动和关闭
- 清理操作结果
- 进程数量变化

## 优化效果

### 1. 资源使用优化
- 减少Chrome进程数量
- 降低内存占用
- 提高系统稳定性

### 2. 自动化程度提升
- 无需手动清理进程
- 自动监控和清理
- 异常情况自动处理

### 3. 监控能力增强
- 实时进程状态监控
- 详细的清理日志
- API接口支持

## 注意事项

1. **权限要求**：需要足够的权限来终止Chrome进程
2. **系统兼容性**：在Linux系统上测试通过，其他系统可能需要调整
3. **性能影响**：进程监控会消耗少量系统资源
4. **清理策略**：可以根据实际需求调整清理阈值和频率

## 故障排除

### 1. 进程清理失败
- 检查权限是否足够
- 查看日志中的错误信息
- 尝试手动清理

### 2. 监控线程异常
- 检查日志中的监控错误
- 重启服务
- 检查系统资源

### 3. 浏览器启动失败
- 检查Chrome/Chromium是否正确安装
- 查看启动参数是否兼容
- 检查系统资源是否充足

## 配置调整

可以通过修改以下参数来调整清理策略：

```python
# 进程数量阈值
if chrome_count > 10:  # 可以调整这个数值

# 监控频率
time.sleep(30)  # 可以调整监控间隔

# 清理超时时间
process.wait(timeout=2)  # 可以调整等待时间
```
