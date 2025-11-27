# 三维一体交易体系 - 容器部署

极简的Docker容器部署方案。

## 快速部署

### 方式一：使用 docker-compose（推荐）

```bash
cd scripts/sanweiyiti_index
docker-compose up -d
```

访问：http://localhost:8080

### 方式二：使用 Docker 命令

```bash
cd scripts/sanweiyiti_index

# 构建镜像
docker build -t sanweiyiti-trading .

# 运行容器
docker run -d -p 8080:80 --name sanweiyiti-trading sanweiyiti-trading
```

访问：http://localhost:8080

## 停止服务

```bash
docker-compose down
```

或

```bash
docker stop sanweiyiti-trading
docker rm sanweiyiti-trading
```

## 重启服务

### 重启 docker-compose 服务

```bash
cd scripts/sanweiyiti_index
docker-compose restart
```

### 停止后重新启动

```bash
cd scripts/sanweiyiti_index
docker-compose down
docker-compose up -d
```

## 更新服务

### 重新构建并启动（代码更新后）

```bash
cd scripts/sanweiyiti_index

# 停止并删除旧容器
docker-compose down

# 重新构建镜像（不缓存）
docker-compose build --no-cache

# 启动服务
docker-compose up -d
```

### 快速更新（推荐）

```bash
cd scripts/sanweiyiti_index
docker-compose up -d --build
```

## 常用命令

### 查看服务状态

```bash
docker-compose ps
```

### 查看日志

```bash
# 查看所有日志
docker-compose logs

# 实时查看日志
docker-compose logs -f

# 查看最近100行日志
docker-compose logs --tail=100
```

### 进入容器

```bash
docker-compose exec <service_name> sh
```

## 修改端口

编辑 `docker-compose.yml` 中的端口映射，例如改为 `3000:80`：

```yaml
ports:
  - "3000:80"
```

修改后需要重启服务：

```bash
docker-compose down
docker-compose up -d
```

