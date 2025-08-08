# 使用国内镜像源加速基础镜像下载
FROM mcr.microsoft.com/playwright:v1.40.0-focal

# 设置环境变量
ENV TZ=Asia/Shanghai
ENV RELEASE_MODE=1
ENV PYTHONPATH=/app
ENV FLASK_APP=car_report_modifier_web.py
ENV DEBIAN_FRONTEND=noninteractive

# Playwright 浏览器下载加速 - 使用国内镜像
ENV PLAYWRIGHT_DOWNLOAD_HOST=https://npmmirror.com/mirrors/playwright
ENV PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1

# 设置工作目录
WORKDIR /app

# 配置apt使用国内镜像源并安装依赖
RUN sed -i 's/archive.ubuntu.com/mirrors.aliyun.com/g' /etc/apt/sources.list && \
    sed -i 's/security.ubuntu.com/mirrors.aliyun.com/g' /etc/apt/sources.list && \
    apt-get update && \
    apt-get install -y --no-install-recommends \
        fonts-noto-cjk \
        fonts-noto-cjk-extra \
        fonts-wqy-microhei \
        fonts-wqy-zenhei \
        xvfb \
        ca-certificates \
        && apt-get clean \
        && rm -rf /var/lib/apt/lists/* \
        && ln -snf /usr/share/zoneinfo/$TZ /etc/localtime \
        && echo $TZ > /etc/timezone

# 创建必要的目录
RUN mkdir -p static/screenshots templates

# 复制依赖文件
COPY requirements.txt .

# 配置pip使用国内镜像源并安装Python依赖
RUN pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple/ && \
    pip config set global.trusted-host pypi.tuna.tsinghua.edu.cn && \
    pip install --upgrade pip && \
    pip install -r requirements.txt

# 安装 Playwright 浏览器 - 使用国内镜像加速
RUN playwright install chromium --with-deps

# 复制应用代码
COPY . .

# 设置权限
RUN chmod -R 755 /app/static/screenshots && \
    chmod +x /app/docker_start.sh

# 暴露端口
EXPOSE 8090

# 启动命令
CMD ["/app/docker_start.sh"]