# Rancher API Client

这个目录包含用于与Rancher v1.6.30进行API交互的Python客户端。

## 文件说明

- `rancher_api.py` - 主要的Rancher API客户端类
- `rancher_examples.py` - 使用示例和常见操作演示
- `requirements.txt` - Python依赖包
- `README.md` - 本说明文件

## 安装依赖

```bash
pip install -r requirements.txt
```

## 配置

在使用之前，请修改以下配置：

1. **Rancher服务器URL**: 在代码中将 `http://your-rancher-server:8080` 替换为你的实际Rancher服务器地址
2. **API密钥**: 代码中已包含你提供的API密钥
   - Access Key: `C5EA6259A878D3404231`
   - Secret Key: `Sy8e4rAxitsqNqzKaAfP7D4f3B1NWdEdttnsBF3X`

## 快速开始

```python
from rancher_api import RancherAPIClient

# 初始化客户端
rancher_url = "http://your-rancher-server:8080"
client = RancherAPIClient(rancher_url)

# 获取项目列表
projects = client.get_projects()
print(f"找到 {len(projects)} 个项目")

# 获取服务列表
services = client.get_services()
for service in services:
    print(f"服务: {service['name']} - 状态: {service['state']}")
```

## 主要功能

### 项目管理
- `get_projects()` - 获取项目列表
- `get_project(project_id)` - 获取特定项目
- `create_project(name, description)` - 创建项目

### 环境管理
- `get_environments()` - 获取环境列表

### 服务管理
- `get_services()` - 获取服务列表
- `get_service(service_id)` - 获取特定服务
- `create_service()` - 创建服务
- `upgrade_service()` - 升级服务
- `scale_service()` - 扩缩容服务
- `restart_service()` - 重启服务
- `delete_service()` - 删除服务

### 容器管理
- `get_containers()` - 获取容器列表
- `restart_container()` - 重启容器
- `stop_container()` - 停止容器
- `start_container()` - 启动容器

### 主机管理
- `get_hosts()` - 获取主机列表
- `get_host(host_id)` - 获取特定主机

### 实用工具
- `wait_for_service_active()` - 等待服务变为活跃状态
- `get_service_logs()` - 获取服务日志

## 使用示例

运行示例脚本查看详细的使用演示：

```bash
python rancher_examples.py
```

⚠️ **安全说明**: 示例脚本仅包含查看和监控功能，不会对现有容器和服务进行任何修改操作。

示例包括：
1. 集群总体状态查看
2. 项目详细信息
3. 环境状态监控  
4. 服务状态详细监控
5. 容器状态监控
6. 主机状态监控
7. 服务日志查看
8. 资源使用情况监控
9. 服务健康状态检查
10. 持续监控示例

## API版本兼容性

本客户端专为以下版本设计：
- Rancher: v1.6.30
- Cattle: v0.183.83
- 用户界面: v1.6.52
- Rancher CLI: v0.6.14
- Rancher Compose: v0.12.5

## 注意事项

1. 请确保Rancher服务器可访问
2. 确认API密钥有足够的权限
3. **示例脚本仅用于查看和监控，不会修改任何现有资源**
4. 某些查看操作可能需要特定的环境或服务存在
5. 日志功能可能需要WebSocket支持（当前版本提供基础REST API调用）
6. 如需执行修改操作，请直接调用API客户端的相应方法

## 错误处理

客户端包含基础的错误处理和日志记录。如果遇到问题：

1. 检查网络连接
2. 验证Rancher服务器地址
3. 确认API密钥正确
4. 查看日志输出获取详细错误信息

## 扩展

你可以根据需要扩展客户端功能：

1. 添加更多API端点
2. 实现WebSocket支持用于实时日志
3. 添加更多错误处理逻辑
4. 实现配置文件支持
5. 添加单元测试
