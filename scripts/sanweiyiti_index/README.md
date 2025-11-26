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

## 修改端口

编辑 `docker-compose.yml` 中的端口映射，例如改为 `3000:80`：

```yaml
ports:
  - "3000:80"
```

