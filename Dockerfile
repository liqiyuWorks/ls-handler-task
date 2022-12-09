FROM python:3.8

ENV TZ=Asia/Shanghai
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

ENV RELEASE_MODE=1

RUN mkdir -p /app/log
ENV app /app
ADD . ${app}
WORKDIR ${app}
RUN pip install --upgrade pip -i http://pypi.doubanio.com/simple/  --trusted-host pypi.doubanio.com
RUN pip install -r requirements.txt -i http://pypi.doubanio.com/simple/  --trusted-host pypi.doubanio.com

CMD ["python3", "main.py"]