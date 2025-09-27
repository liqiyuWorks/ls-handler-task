# FFA模拟交易系统部署指南

## 📋 项目概述

FFA模拟交易系统是一个基于FastAPI的Web应用程序，提供FFA（Forward Freight Agreement）模拟交易功能。

## 🏗️ 项目结构

```
ffa_simulation/
├── main.py                 # 主应用程序
├── models.py              # 数据模型
├── database.py            # 数据库操作
├── trading_engine.py      # 交易引擎
├── pnl_calculator.py      # 盈亏计算器
├── auth.py                # 认证模块
├── config.py              # 配置模块
├── production.py          # 生产环境配置
├── requirements.txt       # Python依赖
├── Dockerfile            # Docker镜像构建文件
├── docker-compose.yml    # Docker Compose配置
├── start.sh              # 启动脚本
├── .dockerignore         # Docker忽略文件
├── templates/            # HTML模板
│   ├── index.html        # 主页面
│   └── login.html        # 登录页面
├── static/               # 静态文件
├── data/                 # 数据目录
└── logs/                 # 日志目录
```

## 🐳 Docker部署

### 方法一：使用Docker Compose（推荐）

1. **克隆项目**
```bash
git clone <repository-url>
cd ffa_simulation
```

2. **构建并启动服务**
```bash
docker-compose up -d
```

3. **查看服务状态**
```bash
docker-compose ps
```

4. **查看日志**
```bash
docker-compose logs -f
```

5. **停止服务**
```bash
docker-compose down
```

### 方法二：直接使用Docker

1. **构建镜像**
```bash
docker build -t ffa-simulation .
```

2. **运行容器**
```bash
docker run -d \
  --name ffa-simulation \
  -p 8000:8000 \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/logs:/app/log \
  ffa-simulation
```

## 🚀 直接部署

### 环境要求

- Python 3.11+
- pip
- 系统依赖：gcc, g++

### 安装步骤

1. **安装系统依赖**
```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install -y gcc g++

# CentOS/RHEL
sudo yum install -y gcc gcc-c++
```

2. **安装Python依赖**
```bash
pip install -r requirements.txt
```

3. **初始化数据库**
```bash
python3 -c "from database import create_tables; create_tables()"
```

4. **启动服务**
```bash
# 开发环境
python3 main.py

# 生产环境
./start.sh
```

## 🔧 配置说明

### 环境变量

| 变量名 | 默认值 | 说明 |
|--------|--------|------|
| `DATABASE_URL` | `sqlite:///./data/ffa_simulation.db` | 数据库连接URL |
| `SECRET_KEY` | `your-secret-key-change-in-production` | JWT密钥 |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `30` | Token过期时间（分钟） |
| `LOG_LEVEL` | `INFO` | 日志级别 |
| `MAX_WORKERS` | `4` | 最大工作进程数 |

### 生产环境配置

1. **修改密钥**
```bash
export SECRET_KEY="your-very-secure-secret-key"
```

2. **配置数据库**
```bash
export DATABASE_URL="postgresql://user:password@localhost/ffa_simulation"
```

3. **设置日志级别**
```bash
export LOG_LEVEL="WARNING"
```

## 📊 监控和健康检查

### 健康检查端点

```bash
curl http://localhost:8000/health
```

响应示例：
```json
{
  "status": "healthy",
  "message": "服务正常运行"
}
```

### 日志监控

```bash
# Docker环境
docker-compose logs -f

# 直接部署
tail -f logs/app.log
```

## 🔒 安全建议

1. **修改默认密钥**
   - 更改`SECRET_KEY`环境变量
   - 使用强密码策略

2. **数据库安全**
   - 使用生产级数据库（PostgreSQL/MySQL）
   - 配置数据库访问控制

3. **网络安全**
   - 使用HTTPS
   - 配置防火墙规则
   - 限制访问IP

4. **容器安全**
   - 定期更新基础镜像
   - 扫描安全漏洞
   - 使用非root用户运行

## 📈 性能优化

1. **数据库优化**
   - 添加索引
   - 配置连接池
   - 定期清理数据

2. **应用优化**
   - 启用缓存
   - 优化查询
   - 使用CDN

3. **容器优化**
   - 多阶段构建
   - 镜像大小优化
   - 资源限制

## 🐛 故障排除

### 常见问题

1. **端口被占用**
```bash
# 查找占用端口的进程
lsof -i :8000
# 杀死进程
kill -9 <PID>
```

2. **数据库连接失败**
```bash
# 检查数据库文件权限
ls -la data/
# 重新初始化数据库
python3 -c "from database import create_tables; create_tables()"
```

3. **内存不足**
```bash
# 检查内存使用
free -h
# 增加swap空间
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

### 日志分析

```bash
# 查看错误日志
grep -i error logs/app.log

# 查看访问日志
grep -i "GET\|POST" logs/app.log
```

## 📞 技术支持

如有问题，请检查：
1. 日志文件：`logs/app.log`
2. 健康检查：`http://localhost:8000/health`
3. 系统资源使用情况
4. 网络连接状态

## 🔄 更新部署

1. **停止服务**
```bash
docker-compose down
```

2. **更新代码**
```bash
git pull origin main
```

3. **重新构建**
```bash
docker-compose build
```

4. **启动服务**
```bash
docker-compose up -d
```

## 📝 版本信息

- 应用版本：1.0.0
- Python版本：3.11+
- FastAPI版本：0.104.1
- 数据库：SQLite（开发）/ PostgreSQL（生产）
