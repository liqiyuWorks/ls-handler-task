FROM python:3.8

ENV TZ=Asia/Shanghai
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

ENV app=/app
ADD . ${app}
WORKDIR ${app}
# RUN pip install --upgrade pip -i http://mirrors.aliyun.com/pypi/simple/ --trusted-host mirrors.aliyun.com
RUN pip install -r requirements.txt -i http://mirrors.aliyun.com/pypi/simple/ --trusted-host mirrors.aliyun.com


# 使用gunicorn更加成熟和稳定,虽然用["python", "main.py"]也可以运行
CMD ["python3", "fastapi_server.py"]