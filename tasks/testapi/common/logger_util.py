import os
import logging
import logging.handlers

LOG_FILE = os.getcwd()+"/testapi/log/run.log"


def check_create_path(file):
    file_path = os.path.dirname(file)
    if not os.path.exists(file_path):
        os.makedirs(file_path, 0o777)


check_create_path(LOG_FILE)
logger = logging.getLogger()
formatter = logging.Formatter(
    '%(asctime)s - %(pathname)s[line:%(lineno)d] - %(levelname)s: %(message)s')
# sh = logging.StreamHandler()  # 往屏幕上输出
# sh.setFormatter(formatter)  # 设置屏幕上显示的格式
th = logging.handlers.TimedRotatingFileHandler(LOG_FILE, when='H', interval=1, backupCount=40)
th.setFormatter(formatter)
# logger.addHandler(sh)
logger.addHandler(th)
logger.setLevel(logging.ERROR)

