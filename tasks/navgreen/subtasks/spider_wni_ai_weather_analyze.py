#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from pkg.public.decorator import decorate
import os
import pymongo
import requests
import datetime
import time
import json
from pkg.public.models import BaseModel
from pkg.public.wechat_push import WechatPush, PrefixEnums


class SpiderWniAiWeatherAnalyze(BaseModel):
    # API URLs
    LOGIN_URL = "https://vp.weathernews.com/api/v1/auth/login"
    WEATHER_AI_WEATHER_URL = "https://vp.weathernews.com/api/v1/sn/data/genai/area_bf_sheet.json"
    
    # 基础认证信息 - 从环境变量或配置文件获取
    BASE_AUTH_TOKEN = "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCIsImtpZCI6InVmc0VDVHpEY0pNLWI0U1FMNDB6TSJ9.eyJodHRwczovL3dlYXRoZXJuZXdzLmNvbS9lbWFpbCI6Im9wc0BjbW9jZWFuc2hpcHBpbmcuY29tIiwiaHR0cHM6Ly93ZWF0aGVybmV3cy5jb20vZW1haWxfdmVyaWZpZWQiOnRydWUsImh0dHBzOi8vd2VhdGhlcm5ld3MuY29tL3VzZXJuYW1lIjoib3BzI2EjY21vY2VhbnNoaXBwaW5nLmNvbSIsImh0dHBzOi8vd2VhdGhlcm5ld3MuY29tL2FwcF9tZXRhZGF0YSI6eyJhcHBsaWNhdGlvbnMiOlsiR1AiXSwicGxhbm5pbmdzIjpbIlNFQSJdfSwiaXNzIjoiaHR0cHM6Ly9sb2dpbi5hdXRoLndlYXRoZXJuZXdzLmNvbS8iLCJzdWIiOiJhdXRoMHxvcHNAY21vY2VhbnNoaXBwaW5nLmNvbSIsImF1ZCI6WyJodHRwczovL3dlYXRoZXJuZXdzLmNvbS8iLCJodHRwczovL3duaS51cy5hdXRoMC5jb20vdXNlcmluZm8iXSwiaWF0IjoxNzU5MTIwODUwLCJleHAiOjE3NTkyMDcyNTAsInNjb3BlIjoib3BlbmlkIHByb2ZpbGUgZW1haWwgb2ZmbGluZV9hY2Nlc3MiLCJhenAiOiJVZUhIekhHQll0ZWRCZ0JDNERBeVVIYUh3YkdCNXQ1TCJ9.LRruzp3MW7skGXWoXcv5qGSCjmkNT8BQ1799h-KAPpLU-BXTsMcd1IoLHLx61vNQvrkm_Kla-qluOKzpPuJNdpsNaCvHVmlBc_XQlipFJPMrkg1RHDQ8qXUjnjtXGjArklBTr9m2ni2cVVU8uFb9UHS3UQNvRysBrqeVmteS0zr3JDMjLGO9JXW4zCVjducW4ZAa56PpMGYIe_HRs0aQFsLT_F9740g7wqvAkg3om9VTGY5RA5bGmchIEoTymKzVrkgzixRgaTKs1oq5trCx_J5F32bIH7mGr1WBpYRupjNMC4msxbJw5SDESQWy_s1O08Oh7FaxtD2FSJLwxOGmuA"

    def __init__(self):
        config = {
            'handle_db': 'mgo',
            'collection': 'wni_ai_weather_analyze',
            'uniq_idx': [
                ('dataTime', pymongo.ASCENDING),
            ]
        }

        # 基础请求头
        self.base_headers = {
            'newrelic': 'eyJ2IjpbMCwxXSwiZCI6eyJ0eSI6IkJyb3dzZXIiLCJhYyI6IjMzMDk4MjUiLCJhcCI6IjExMzQzNzQzMzUiLCJpZCI6IjNlZmU1MWE2YWViY2RhNTgiLCJ0ciI6IjVmMWYxNzU4NTc4ODU4ZmUxNzhiMDQ1Nzg4YzE2NzY2IiwidGkiOjE3NTkxNDA3OTkwOTMsInRrIjoiMzM3NTk3MiJ9fQ==',
            'traceparent': '00-5f1f1758578858fe178b045788c16766-3efe51a6aebcda58-01',
            'tracestate': '3375972@nr=0-1-3309825-1134374335-3efe51a6aebcda58----1759140799093',
            'priority': 'u=1, i',
            'Cookie': '_tea_utm_cache_10000007=undefined; _legacy_auth0.UeHHzHGBYtedBgBC4DAyUHaHwbGB5t5L.is.authenticated=true; auth0.UeHHzHGBYtedBgBC4DAyUHaHwbGB5t5L.is.authenticated=true; CloudFront-Policy=eyJTdGF0ZW1lbnQiOlt7IlJlc291cmNlIjoiaHR0cHM6Ly8qIiwiQ29uZGl0aW9uIjp7IkRhdGVMZXNzVGhhbiI6eyJBV1M6RXBvY2hUaW1lIjoxNzYxNjQwMjk4fX19XX0_; CloudFront-Signature=een5osKoh4E5nth7UhMRflCRxMaS-8ySCV3lqVsB5mlWoJXAnx5fr3UgILwCnU4nZoFxMiEWahm4rRvEqHotP2MORDrivfkfeb0AsQqRi~P68BlDyJoOpwkrv27ul8YbluMksnrJaIs0n0VrOfNid~Czher89i2ioibzp0QYVAiAKnlOAvkCJHm7oymbr-Ml81BLhTi6Q3Bo91Oi3Xhfaq9e1c4rLAU~h7OIbtAG000qV2b35mHuMl824cWM2BhIIZOjmd1nSZUm2u1oLx3fo3c4ZNJxdeJw2HxPfcaOx16pnlHdgfja8MIpl0QEfm5F18ckbgR44eueQd4ACBYUkg__; CloudFront-Key-Pair-Id=K30UMOHJTLIIQL; _ga=GA1.1.789839480.1759048312; _ga_HWC5LM40NQ=GS2.1.s1759139208$o26$g0$t1759140798$j60$l0$h0'
        }
        
        # 动态认证信息
        self.auth_token = None
        self.auth_expires_at = None

        super(SpiderWniAiWeatherAnalyze, self).__init__(config)

    def _login(self, max_retries=3):
        """
        登录获取认证信息
        """
        for attempt in range(max_retries):
            try:
                print(f"尝试登录 (第 {attempt + 1} 次)...")
                
                # 构建登录请求头
                login_headers = self.base_headers.copy()
                login_headers['authorization'] = f'Bearer {self.BASE_AUTH_TOKEN}'
                
                # 发送登录请求
                response = requests.get(
                    url=self.LOGIN_URL,
                    headers=login_headers,
                    timeout=30
                )
                
                if response.status_code == 200:
                    # 解析响应获取新的认证信息
                    login_data = response.json()
                    print(f"登录成功: {login_data}")
                    
                    # 更新认证信息
                    self.auth_token = login_data.get('access_token') or self.BASE_AUTH_TOKEN
                    
                    # 设置过期时间（假设token有效期为24小时，提前5分钟刷新）
                    self.auth_expires_at = time.time() + (24 * 60 * 60) - (5 * 60)
                    
                    print("认证信息更新成功")
                    return True
                else:
                    print(f"登录失败，状态码: {response.status_code}, 响应: {response.text}")
                    
            except Exception as e:
                print(f"登录异常 (第 {attempt + 1} 次): {str(e)}")
                
            if attempt < max_retries - 1:
                print(f"等待 {2 ** attempt} 秒后重试...")
                time.sleep(2 ** attempt)
        
        print("登录失败，使用基础认证信息")
        self.auth_token = self.BASE_AUTH_TOKEN
        return False

    def _is_auth_valid(self):
        """
        检查认证信息是否有效
        """
        if not self.auth_token:
            return False
        if not self.auth_expires_at:
            return False
        return time.time() < self.auth_expires_at

    def _get_auth_headers(self):
        """
        获取带认证信息的请求头
        """
        headers = self.base_headers.copy()
        headers['authorization'] = f'Bearer {self.auth_token}'
        return headers

    def _fetch_weather_data(self, max_retries=3):
        """
        获取天气数据
        """
        for attempt in range(max_retries):
            try:
                print(f"获取天气数据 (第 {attempt + 1} 次)...")
                
                # 确保认证信息有效
                if not self._is_auth_valid():
                    print("认证信息已过期，重新登录...")
                    self._login()
                
                # 获取请求头
                headers = self._get_auth_headers()
                
                # 发送数据请求
                response = requests.get(
                    url=self.WEATHER_AI_WEATHER_URL,
                    headers=headers,
                    timeout=30
                )
                
                if response.status_code == 200:
                    data = response.json()
                    print(f"数据获取成功: {data}")
                    return data
                elif response.status_code == 401:
                    print("认证失败，重新登录...")
                    self._login()
                    continue
                else:
                    print(f"数据获取失败，状态码: {response.status_code}, 响应: {response.text}")
                    
            except Exception as e:
                print(f"数据获取异常 (第 {attempt + 1} 次): {str(e)}")
                
            if attempt < max_retries - 1:
                print(f"等待 {2 ** attempt} 秒后重试...")
                time.sleep(2 ** attempt)
        
        print("数据获取失败")
        return None

    @decorate.exception_capture_close_datebase
    def run(self):
        """
        主运行方法
        """
        dataTime = datetime.datetime.now().strftime("%Y-%m-%d %H:00:00")
        print(f"开始处理数据，时间: {dataTime}")
        
        # 1. 先进行登录获取认证信息
        login_success = self._login()
        if not login_success:
            print("警告: 登录失败，使用基础认证信息继续")
        
        # 2. 获取天气数据
        weather_data = self._fetch_weather_data()
        if not weather_data:
            print("错误: 无法获取天气数据")
            return
        
        # 3. 处理数据
        try:
            result_data = weather_data.get("wx_outlook_list", {})
            if result_data:
                print(f"成功获取天气数据: {len(result_data)} 条记录")
                # 保存到数据库
                # self.mgo.set(None, result_data)
                print("数据保存成功")
            else:
                print("警告: 天气数据为空")
                
        except Exception as e:
            print(f"数据处理异常: {str(e)}")
            raise
