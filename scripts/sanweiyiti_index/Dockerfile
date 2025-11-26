FROM nginx:alpine

# 复制HTML文件到临时位置
COPY *.html /tmp/

# 重命名并移动到nginx默认目录
RUN mv /tmp/*.html /usr/share/nginx/html/index.html

# 暴露80端口
EXPOSE 80

# nginx默认启动命令已包含在基础镜像中

