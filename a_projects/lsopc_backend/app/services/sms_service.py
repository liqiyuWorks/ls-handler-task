# -*- coding: utf-8 -*-
"""互亿无线（ihuyi）短信验证码发送"""

import http.client
import logging
import urllib.parse

from app.config import settings

logger = logging.getLogger(__name__)


def send_sms_code(phone: str, code: str) -> bool:
    """
    发送短信验证码到指定手机号。
    使用互亿无线 API，内容为模板：您的验证码是：【变量】。请不要把验证码泄露给其他人。
    :return: True 发送成功，False 发送失败（记录日志）
    """
    content = f"您的验证码是：{code}。请不要把验证码泄露给其他人。"
    values = {
        "account": settings.IHUYI_ACCOUNT,
        "password": settings.IHUYI_PASSWORD,
        "mobile": phone,
        "content": content,
    }
    params = urllib.parse.urlencode(values).encode("utf-8")
    headers = {
        "Content-type": "application/x-www-form-urlencoded",
        "Accept": "text/plain",
    }
    try:
        conn = http.client.HTTPConnection(settings.IHUYI_SMS_HOST, timeout=10)
        conn.request("POST", settings.IHUYI_SMS_URI, params, headers)
        response = conn.getresponse()
        body = response.read().decode("utf-8")
        conn.close()
        if response.status != 200:
            logger.warning("ihuyi sms http status=%s body=%s", response.status, body)
            return False
        # 互亿返回 JSON 如 {"code":2,"msg":"提交成功"}，code=2 表示成功
        import json
        try:
            data = json.loads(body)
            if data.get("code") == 2:
                logger.info("SMS sent to %s successfully", phone[:3] + "****" + phone[-4:])
                return True
            logger.warning("ihuyi sms result: %s", data)
            return False
        except json.JSONDecodeError:
            logger.warning("ihuyi sms non-json body: %s", body)
            return False
    except Exception as e:  # pylint: disable=broad-exception-caught
        logger.exception("ihuyi sms request failed: %s", e)
        return False
