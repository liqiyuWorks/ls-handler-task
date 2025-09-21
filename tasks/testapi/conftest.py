'''
Author: lisheng
Date: 2022-12-07 21:20:23
LastEditTime: 2023-01-04 10:17:28
LastEditors: lisheng
Description: 用于错误信息的推送
FilePath: /ls-handler-task/tasks/testapi/conftest.py
'''
import logging
from pkg.public.wechat_push import WechatPush


def pytest_terminal_summary(terminalreporter, exitstatus, config):
    '''
    收集用例执行结果
    :param terminalreporter:
    :param exitstatus:
    :param config:
    :return:
    '''
    faild_object = terminalreporter.stats.get("failed", [])
    if faild_object != []:
        for i in faild_object:
            logging.error(f">> 获取失败用例集对象名称location: {i.location}")
            message = i.longrepr.chain[0][1].message
            notify_user = WechatPush()
            a = str(i.location[0]).split("/")[-2:]
            msg = f"""报错: {a[0]}/{a[1]}:{i.location[1]}\n详情: {i.location[2]}:<{message}>"""
            notify_user.notify(msg=msg)