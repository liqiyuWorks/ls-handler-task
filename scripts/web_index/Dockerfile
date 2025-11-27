FROM nginx:alpine

# 接受构建参数，指定要服务的HTML文件名
ARG HTML_FILE

# 复制指定的HTML文件到nginx默认目录
COPY "${HTML_FILE}" /usr/share/nginx/html/index.html

# 暴露80端口
EXPOSE 80

# nginx默认启动命令已包含在基础镜像中

