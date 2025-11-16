# 使用轻量级 Python 3.11 官方镜像作为基础镜像
FROM python:3.11-slim AS base

# 定义版本号参数
ARG VERSION=latest
ARG BUILD_DATE
ARG GIT_COMMIT

# 设置标签
LABEL maintainer="AquaBridge Team"
LABEL version=$VERSION
LABEL build-date=$BUILD_DATE
LABEL git-commit=$GIT_COMMIT

# 设置工作目录
WORKDIR /app

# 设置环境变量
ENV PYTHONPATH=/app \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    TZ=Asia/Shanghai

# 仅复制依赖文件并安装 Python 依赖
COPY requirements.txt /app/requirements.txt
RUN pip install --upgrade pip -i https://pypi.tuna.tsinghua.edu.cn/simple/ --trusted-host pypi.tuna.tsinghua.edu.cn \
    && pip install --no-cache-dir -r /app/requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple/ --trusted-host pypi.tuna.tsinghua.edu.cn

# 复制项目文件（只在依赖安装完成后再复制，提升缓存命中率）
COPY . /app

# 创建非 root 用户并调整权限
RUN useradd --create-home --shell /bin/bash app \
    && mkdir -p /app/log \
    && chown -R app:app /app
USER app

# 暴露服务端口
EXPOSE 8080

# 启动命令
CMD ["python", "app.py"]
