FROM mcr.microsoft.com/playwright:v1.40.0-focal

ENV TZ=Asia/Shanghai
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

ENV RELEASE_MODE=1

# Playwright 浏览器下载加速
ENV PLAYWRIGHT_DOWNLOAD_HOST=https://npmmirror.com/mirrors/playwright

# 创建必要的目录
RUN mkdir -p static/screenshots templates

# 安装pip
RUN apt-get update && apt-get install -y python3-pip

# 复制依赖文件
COPY requirements.txt .


# 复制应用代码
COPY . .

# 暴露端口
EXPOSE 8090

RUN pip3 install --upgrade pip -i https://pypi.tuna.tsinghua.edu.cn/simple/ --trusted-host pypi.tuna.tsinghua.edu.cn
RUN pip3 install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple/ --trusted-host pypi.tuna.tsinghua.edu.cn
RUN python3 -m playwright install

# 启动命令（使用结构化 app 入口）
CMD ["python3", "run.py"]