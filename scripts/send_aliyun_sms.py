#!/usr/bin/env python3
"""
基于阿里云短信服务发送短信的工具脚本。

依赖：
    pip install aliyun-python-sdk-core aliyun-python-sdk-dysmsapi

凭证优先级：
    1. 命令行参数
    2. 环境变量：
        - ALIYUN_SMS_ACCESS_KEY_ID
        - ALIYUN_SMS_ACCESS_KEY_SECRET
        - ALIYUN_SMS_REGION (可选，默认 cn-hangzhou)
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from typing import Dict, Iterable, Sequence

from aliyunsdkcore.client import AcsClient
from aliyunsdkcore.acs_exception.exceptions import ClientException, ServerException
from aliyunsdkcore.request import CommonRequest

DEFAULT_VERIFICATION_TEMPLATE_CODE = "SMS_498085055"
VERIFICATION_TEMPLATE_TEXT = "您的验证码为：${code}，该验证码5分钟内有效，请勿泄露于他人！"

LOG = logging.getLogger(__name__)


def _init_logging(verbose: bool = False) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    )


def _load_credentials(
    access_key_id: str | None,
    access_key_secret: str | None,
    region_id: str | None,
) -> tuple[str, str, str]:
    access_key_id = access_key_id or os.getenv("ALIYUN_SMS_ACCESS_KEY_ID",os.getenv("ALIYUN_SMS_ACCESS_KEY_ID"))
    access_key_secret = access_key_secret or os.getenv("ALIYUN_SMS_ACCESS_KEY_SECRET",os.getenv("ALIYUN_SMS_ACCESS_KEY_SECRET"))
    region_id = region_id or os.getenv("ALIYUN_SMS_REGION", "cn-hangzhou")

    missing = [
        name
        for name, value in [
            ("access_key_id", access_key_id),
            ("access_key_secret", access_key_secret),
        ]
        if not value
    ]
    if missing:
        raise ValueError(f"缺少阿里云凭证字段: {', '.join(missing)}")

    return access_key_id, access_key_secret, region_id


def _create_client(access_key_id: str, access_key_secret: str, region_id: str) -> AcsClient:
    return AcsClient(
        ak=access_key_id,
        secret=access_key_secret,
        region_id=region_id,
    )


def send_sms(
    client: AcsClient,
    phone_numbers: Sequence[str],
    sign_name: str,
    template_code: str,
    template_param: Dict[str, str] | None = None,
) -> Dict[str, object]:
    """
    调用阿里云短信服务发送短信。

    :param client: 已初始化的 AcsClient 对象。
    :param phone_numbers: 待发送的手机号列表，最多 100 个。
    :param sign_name: 短信签名。
    :param template_code: 短信模板编号。
    :param template_param: 模板变量字典。
    :return: 阿里云返回的原始响应（dict）。
    """
    if not phone_numbers:
        raise ValueError("phone_numbers 不能为空")

    request = CommonRequest()
    request.set_accept_format("json")
    request.set_domain("dysmsapi.aliyuncs.com")
    request.set_method("POST")
    request.set_protocol_type("https")
    request.set_version("2017-05-25")
    request.set_action_name("SendSms")

    request.add_query_param("PhoneNumbers", ",".join(phone_numbers))
    request.add_query_param("SignName", sign_name)
    request.add_query_param("TemplateCode", template_code)

    if template_param:
        request.add_query_param("TemplateParam", json.dumps(template_param, ensure_ascii=False))

    LOG.debug(
        "发送短信，请求参数 phone_numbers=%s sign_name=%s template_code=%s template_param=%s",
        phone_numbers,
        sign_name,
        template_code,
        template_param,
    )

    response = client.do_action_with_exception(request)
    decoded = json.loads(response.decode("utf-8"))

    LOG.debug("短信发送返回: %s", decoded)
    return decoded


def _parse_template_params(pairs: Iterable[str]) -> Dict[str, str]:
    params: Dict[str, str] = {}
    for pair in pairs:
        if "=" not in pair:
            raise ValueError(f"模板参数格式错误，应为 key=value，实际为: {pair}")
        key, value = pair.split("=", 1)
        params[key] = value
    return params


def _parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="使用阿里云短信服务发送短信。",
    )
    parser.add_argument(
        "--phone",
        dest="phones",
        action="append",
        required=True,
        help="目标手机号，可重复传入多次。",
    )
    parser.add_argument(
        "--sign-name",
        required=True,
        help="短信签名。",
    )
    parser.add_argument(
        "--template-code",
        required=False,
        help="短信模板代码。",
    )
    parser.add_argument(
        "--verification-code",
        help=(
            "验证码模板变量，使用默认模板 "
            f"{DEFAULT_VERIFICATION_TEMPLATE_CODE}（{VERIFICATION_TEMPLATE_TEXT}）。"
        ),
    )
    parser.add_argument(
        "--param",
        dest="params",
        action="append",
        default=[],
        help="模板变量，格式 key=value，可重复传入。",
    )
    parser.add_argument(
        "--param-json",
        dest="param_json",
        help="模板变量 JSON 字符串，如果同时使用 --param，会与其合并，后者覆盖前者。",
    )
    parser.add_argument(
        "--access-key-id",
        help="阿里云 AccessKeyId，默认读取环境变量。",
    )
    parser.add_argument(
        "--access-key-secret",
        help="阿里云 AccessKeySecret，默认读取环境变量。",
    )
    parser.add_argument(
        "--region-id",
        help="阿里云 RegionId，默认 cn-hangzhou 或环境变量 ALIYUN_SMS_REGION。",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="输出调试日志。",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv or sys.argv[1:])
    _init_logging(args.verbose)

    try:
        access_key_id, access_key_secret, region_id = _load_credentials(
            args.access_key_id,
            args.access_key_secret,
            args.region_id,
        )
        client = _create_client(access_key_id, access_key_secret, region_id)

        params = {}
        if args.param_json:
            params.update(json.loads(args.param_json))
        if args.params:
            params.update(_parse_template_params(args.params))
        if args.verification_code:
            params["code"] = args.verification_code
            if not args.template_code:
                args.template_code = DEFAULT_VERIFICATION_TEMPLATE_CODE
            elif args.template_code != DEFAULT_VERIFICATION_TEMPLATE_CODE:
                LOG.warning(
                    "检测到同时传入验证码变量与非默认模板代码，"
                    "请确认模板 %s 能否识别参数 code。默认模板文本: %s",
                    args.template_code,
                    VERIFICATION_TEMPLATE_TEXT,
                )

        template_code = args.template_code
        if not template_code:
            if args.verification_code:
                template_code = DEFAULT_VERIFICATION_TEMPLATE_CODE
            else:
                raise ValueError(
                    "必须指定 --template-code，或提供 --verification-code 以使用默认验证码模板。"
                )

        response = send_sms(
            client=client,
            phone_numbers=args.phones,
            sign_name=args.sign_name,
            template_code=template_code,
            template_param=params or None,
        )
        status = response.get("Code")

        if status == "OK":
            LOG.info("短信发送成功。RequestId=%s BizId=%s", response.get("RequestId"), response.get("BizId"))
            return 0

        LOG.error("短信发送失败: Code=%s Message=%s", response.get("Code"), response.get("Message"))
        return 2

    except (ValueError, ClientException, ServerException) as exc:
        LOG.error("短信发送异常: %s", exc, exc_info=args.verbose)
        return 1


if __name__ == "__main__":
    sys.exit(main())


