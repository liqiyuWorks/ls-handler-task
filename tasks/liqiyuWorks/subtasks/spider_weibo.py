#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import logging
from pkg.public.decorator import decorate
import os
import urllib
import time
import requests
import json
from pkg.public.models import BaseModel
import pymongo
from datetime import datetime
import re


class WeiboSpider(BaseModel):
    def __init__(self):
        print("........init..........")
        # 使用新的API接口（POST方式，URL包含查询参数）
        self.base_url = "https://api.weibo.cn/2/searchall"

        # 从环境变量获取认证信息，如果没有则使用默认值
        self.AUTHORIZATION = os.getenv(
            "AUTHORIZATION", "WB-SUT _2A95EQfR6DeRxGeNI6VUU-CnJyjmIHXVlVwCyrDV6PUJbkdAbLVfGkWpNSJyou4Mp1ONPKVqkTEKMXKRnlrxiJwqT")
        self.X_SESSIONID = os.getenv(
            "X_SESSIONID", "0ECDE49D-D4CB-4E1D-B5FB-7230571301FA")
        self.X_LOG_UID = os.getenv("X_LOG_UID", "5627587515")
        self.X_SHANHAI_PASS = os.getenv(
            "X_SHANHAI_PASS", "3.Mbk4rw6ZDZNzh3RDSoeTwEyE7F8")
        self.X_VALIDATOR = os.getenv(
            "X_VALIDATOR", "vEJ4OFeqrek1ug+/0pp8t5dhAn/4B02/e2I0XRTjzPU=")
        self.GSID = os.getenv(
            "GSID", "_2A25EQfR6DeRxGeNI6VUU-CnJyjmIHXVlVwCyrDV6PUJbkdAbLU_8kWpNSJyouyezouAS63CB7Zz64l0JedKEhfxV")

        # 更新请求头以匹配curl命令
        self.HEADER = {
            'Accept-Language': 'en-US,en',
            'X-Sessionid': self.X_SESSIONID,
            'SNRT': 'normal',
            'cronet_rid': '5504886',
            'x-shanhai-pass': self.X_SHANHAI_PASS,
            'User-Agent': 'Weibo/97296 (iPhone; iOS 26.2; Scale/3.00)',
            'Authorization': self.AUTHORIZATION,
            'X-Log-Uid': self.X_LOG_UID,
            'Content-Type': 'application/x-www-form-urlencoded; charset=utf-8',
            'Accept': '*/*',
            'Host': 'api.weibo.cn',
            'X-Validator': self.X_VALIDATOR,
            'x-engine-type': 'cronet-114.0.5735.246'
        }
        self.count = 20  # 每页数量，增加到20条以获取更多数据
        self.collection = os.getenv('COLLECTION', "weibo_water")
        self.columnsName = ['id', 'user', 'location',
                            'coordinates', 'text', 'date']
        config = {
            'collection': self.collection,
            'uniq_idx': [
                ('id', pymongo.ASCENDING),
            ]
        }

        # words_str = os.getenv('WORDS_LIST', "珍惜水资源,水资源可持续利用,水生态保护,节水意识,水资源危机,水资源保护, \
        #                       珍惜水资源, 水资源危机, 水资源可持续利用, 节水意识, 水生态保护,节约用水, 污染控制, 水质保护, \
        #                       水资源管理, 雨水收集, 水循环利用, 地下水保护, 水生态修复, 水土保持, 水源地保护, 雨水利用技术, \
        #                       水资源保护法, 水资源政策, 环保法规, 水权制度, 水资源税, 水资源法律法规, 水资源管理制度,水处理设备, \
        #                       水质监测技术,农业节水灌溉, 工业废水处理, 城市水务管理, 供水系统优化, 污水处理与再利用, 水资源调度, 水资源分配, \
        #                       水质监测, 水量监测, 水资源评估, 水资源调查, 水资源地理信息系统, 水资源遥感监测,水资源保护宣传, 水资源教育, 环保公益活动, 环保组织, 节水教育, 环保课堂,水环境保护, 湿地保护, \
        #                     河流生态修复, 水域生态系统, 湖泊保护, 海洋保护, 水土保持工程,长江流域水资源保护, 黄河水资源保护, 非洲水资源保护, 亚洲水资源保护, 干旱地区水资源保护, 山区水资源保护, 沿海地区水资源保护,水资源保护技术, 水资源保护研究, 节水技术研究, 水资源模拟与预测, \
        #                         水资源规划与管理, 水资源信息技术,水灾应对, 洪水预警, 干旱管理, 灾害风险管理, 水资源应急管理,水资源经济学, 水资源定价, 水市场, 水利产业发展, 水资源投入产出分析,国际水资源合作, 跨国河流管理, 联合国水资源议程, 全球水资源保护行动, 国际水资源协议,\
        #                             水资源保护成功案例, 流域管理案例分析, 节水型社会建设案例, 水资源保护项目案例,公众参与水资源保护, 社区水资源管理, 环保志愿者活动, 水资源保护志愿者, 居民节水行动,智能水务系统, 水资源物联网, 海水淡化技术, 雨水收集系统创新, 水资源大数据技术, 节水灌溉新技术")
        # 自然灾害相关搜索关键词（扩展版）
        # 包含用户提供的核心关键词：地震、暴雨、台风、洪涝、涝、连阴雨、持续降雨、暴雪、雪灾、大雪
        # 以及扩展的相关词汇：余震、地震预警、大暴雨、台风路径、洪水、内涝、雪灾救援等
        words_str = os.getenv('WORDS_LIST', "地震,余震,震级,震中,地震预警,地震救援,地震灾害,强震,地震局,地震带,暴雨,大暴雨,特大暴雨,强降雨,降雨量,积水,内涝,城市内涝,道路积水,暴雨预警,暴雨红色预警,台风,热带风暴,强台风,超强台风,台风路径,台风预警,台风登陆,台风影响,台风防御,洪涝,洪水,山洪,城市内涝,水位上涨,溃坝,洪水预警,洪水灾害,防汛,抗洪,涝,内涝,城市内涝,农田内涝,连阴雨,持续降雨,连续降雨,阴雨天气,降雨过程,暴雪,大雪,雪灾,积雪,冰冻,道路结冰,雪崩,暴雪预警,雪灾救援,雪灾应对,大雪预警,强降雪,降雪量,雪深,雪情,干旱,旱灾,干旱预警,抗旱,山火,森林火灾,野火,火灾,泥石流,滑坡,山体滑坡,地质灾害,海啸,海啸预警,极端天气,气象灾害,自然灾害,灾害预警,灾害救援,应急响应")
        self.words_list = words_str.split(",")

        # 核心关键词列表（用于内容过滤）：地震、暴雨、台风、洪涝、涝、连阴雨、持续降雨、暴雪、雪灾、大雪
        # 这些关键词用于在保存数据前检查文本内容是否相关
        core_keywords_str = "地震,余震,震级,震中,地震预警,地震救援,地震灾害,强震,地震局,地震带,暴雨,大暴雨,特大暴雨,强降雨,降雨量,积水,内涝,城市内涝,道路积水,暴雨预警,暴雨红色预警,台风,热带风暴,强台风,超强台风,台风路径,台风预警,台风登陆,台风影响,台风防御,洪涝,洪水,山洪,城市内涝,水位上涨,溃坝,洪水预警,洪水灾害,防汛,抗洪,涝,内涝,城市内涝,农田内涝,连阴雨,持续降雨,连续降雨,阴雨天气,降雨过程,暴雪,大雪,雪灾,积雪,冰冻,道路结冰,雪崩,暴雪预警,雪灾救援,雪灾应对,大雪预警,强降雪,降雪量,雪深,雪情,干旱,旱灾,干旱预警,抗旱,山火,森林火灾,野火,火灾,泥石流,滑坡,山体滑坡,地质灾害,海啸,海啸预警,极端天气,气象灾害,自然灾害,灾害预警,灾害救援,应急响应"
        self.core_keywords = core_keywords_str.split(",")
        super(WeiboSpider, self).__init__(config)
        print("init end ......")

    def parse_url(self, url_params, post_data, retry_count=0, max_retries=3):
        """
        发起POST请求
        url_params: URL查询参数字典
        post_data: POST请求的form数据字典
        retry_count: 当前重试次数
        max_retries: 最大重试次数
        """
        try:
            # 避免请求过快，根据重试次数调整延迟
            if retry_count == 0:
                time.sleep(1)
            else:
                time.sleep(2 * retry_count)  # 重试时增加延迟

            # 构建完整的URL（包含查询参数）
            url = self.base_url + '?' + urllib.parse.urlencode(url_params)

            # 打印完整的URL和请求信息（仅第一页和每10页打印一次）
            if post_data.get('page', '1') == '1' or int(post_data.get('page', '1')) % 10 == 0:
                logging.info('=' * 80)
                logging.info('完整请求URL: {}'.format(url))
                logging.info('请求页码: {}, max_id: {}, topn_pos: {}, 搜索词: {}'.format(
                    post_data.get(
                        'page', 'N/A'), post_data.get('max_id', 'N/A'),
                    post_data.get('topn_pos', 'N/A'), post_data.get('containerid', '')[:100]))
                logging.info('=' * 80)

            # 调试：打印POST数据（前500字符，仅调试模式）
            if logging.getLogger().isEnabledFor(logging.DEBUG):
                data_str = '&'.join(['{}={}'.format(k, str(v)[:50])
                                    for k, v in post_data.items()])
                logging.debug('POST数据: {}'.format(data_str[:500]))

            # 发送POST请求
            # 手动构建请求体字符串，完全匹配curl命令的格式
            # 注意：键不需要编码，值如果已经是URL编码的（如containerid_encoded）则直接使用
            # 已编码的字段列表（这些字段在build_post_data中已经进行了URL编码）
            encoded_fields = {'containerid', 'fid', 'flowId', 'source_code', 'user_avatar', 'user_nickname'}
            
            form_data_parts = []
            for k, v in post_data.items():
                v_str = str(v)
                # 如果字段已经在build_post_data中编码过，直接使用
                if k in encoded_fields:
                    form_data_parts.append('{}={}'.format(k, v_str))
                else:
                    # 对其他字段的值进行URL编码
                    form_data_parts.append('{}={}'.format(k, urllib.parse.quote(v_str, safe='')))

            request_body = '&'.join(form_data_parts)

            res = requests.post(
                url,
                headers=self.HEADER,
                data=request_body,
                timeout=15  # 增加超时时间
            )

            # 记录响应状态和部分内容（用于调试）
            logging.info('响应状态码: {}, 响应长度: {}'.format(
                res.status_code, len(res.text)))
            if res.status_code != 200:
                logging.warning('响应内容: {}'.format(res.text[:500]))

            return res
        except requests.exceptions.Timeout:
            logging.warning('请求超时，重试中... (第{}次)'.format(retry_count + 1))
            if retry_count < max_retries:
                return self.parse_url(url_params, post_data, retry_count + 1, max_retries)
            else:
                logging.error('请求超时，已达到最大重试次数')
                raise
        except requests.exceptions.RequestException as e:
            logging.warning(
                '请求异常: {}, 重试中... (第{}次)'.format(e, retry_count + 1))
            if retry_count < max_retries:
                return self.parse_url(url_params, post_data, retry_count + 1, max_retries)
            else:
                logging.error('请求失败，已达到最大重试次数: {}'.format(e))
                raise
        except Exception as e:
            logging.error('请求失败, 报错信息: {}'.format(e))
            if retry_count < max_retries:
                logging.info('尝试重试... (第{}次)'.format(retry_count + 1))
                return self.parse_url(url_params, post_data, retry_count + 1, max_retries)
            else:
                raise

    def get_data_way_1(self, cards, cards_list):
        cards_list = cards.get('cards')[0].get('card_group')
        for card in cards_list:
            item = {}
            # print(card)
            mblog = card.get('mblog')
            if mblog is None:
                page_flag = False
                break
            item['id'] = mblog.get('id')
            item['date'] = mblog.get('created_at')
            if '2022' not in item['date']:
                new_date = mblog.get('created_at')
                new_date = str(new_date).replace(
                    'Nov', 'Sep').replace('Dec', 'Oct')
                item['date'] = new_date[:-4] + "2021"
            item['text'] = mblog.get('text')
            item['location'], item[
                'coordinates'] = self.get_location(mblog)
            item['user'] = self.get_user(mblog)
            cards_list.append(item)
        return cards_list

    def parse_date_year(self, date_str):
        """
        解析日期字符串，提取年份
        支持多种日期格式：
        - "Mon Nov 15 10:30:00 +0800 2024"
        - "2024-11-15"
        - "2024/11/15"
        - "Nov 15 2024"
        """
        if not date_str:
            return None

        date_str = str(date_str).strip()

        # 方法1: 尝试从字符串末尾提取4位数字年份（微博API常见格式）
        year_match = re.search(r'(\d{4})(?:\s|$)', date_str)
        if year_match:
            year = int(year_match.group(1))
            if 2000 <= year <= 2100:  # 合理的年份范围
                return year

        # 方法2: 尝试解析标准日期格式
        date_formats = [
            '%a %b %d %H:%M:%S %z %Y',  # Mon Nov 15 10:30:00 +0800 2024
            '%Y-%m-%d',
            '%Y/%m/%d',
            '%b %d %Y',  # Nov 15 2024
            '%d %b %Y',  # 15 Nov 2024
        ]

        for fmt in date_formats:
            try:
                dt = datetime.strptime(date_str, fmt)
                return dt.year
            except (ValueError, TypeError):
                continue

        # 方法3: 如果都失败，尝试从字符串中查找年份
        year_match = re.search(r'(20\d{2})', date_str)
        if year_match:
            return int(year_match.group(1))

        return None

    def replace_date_year(self, date_str, target_year):
        """
        替换日期字符串中的年份
        支持多种日期格式：
        - "Mon Nov 15 10:30:00 +0800 2024" -> "Mon Nov 15 10:30:00 +0800 2023"
        - "2024-11-15" -> "2023-11-15"
        - "2024/11/15" -> "2023/11/15"
        - "Nov 15 2024" -> "Nov 15 2023"
        """
        if not date_str:
            return date_str

        date_str = str(date_str).strip()
        target_year_str = str(target_year)

        # 方法1: 替换末尾的4位数字年份（微博API常见格式）
        # 匹配末尾的年份，如 "Mon Nov 15 10:30:00 +0800 2024"
        pattern1 = r'(\d{4})(?:\s|$)'
        match = re.search(pattern1, date_str)
        if match:
            # 保留末尾的空格或结束符
            suffix = match.group(0)[4:]  # 获取年份后的部分（空格或空）
            date_str = re.sub(pattern1, target_year_str + suffix, date_str, count=1)
            return date_str

        # 方法2: 替换开头的年份（如 "2024-11-15" 或 "2024/11/15"）
        pattern2 = r'^(\d{4})([-/])'
        if re.search(pattern2, date_str):
            date_str = re.sub(pattern2, target_year_str + r'\2', date_str, count=1)
            return date_str

        # 方法3: 替换字符串中的任意4位数字年份（20xx格式）
        pattern3 = r'(20\d{2})'
        if re.search(pattern3, date_str):
            date_str = re.sub(pattern3, target_year_str, date_str, count=1)
            return date_str

        return date_str

    def contains_keywords(self, mblog_data):
        """
        检查微博内容是否包含核心关键词
        检查范围：文本内容、标题、话题等
        mblog_data: 微博数据字典
        返回: True如果包含关键词，False否则
        """
        # 核心关键词列表：地震、暴雨、台风、洪涝、涝、连阴雨、持续降雨、暴雪、雪灾、大雪
        keywords = self.core_keywords

        # 检查文本内容
        text = mblog_data.get('text', '')
        if text:
            for keyword in keywords:
                if keyword in text:
                    return True

        # 检查标题（title_source.name）
        title_source = mblog_data.get('title_source', {})
        if title_source:
            title = title_source.get('name', '')
            if title:
                for keyword in keywords:
                    if keyword in title:
                        return True

        # 检查话题（topic_struct[].topic_title）
        topic_struct = mblog_data.get('topic_struct', [])
        if topic_struct:
            for topic in topic_struct:
                topic_title = topic.get('topic_title', '')
                if topic_title:
                    for keyword in keywords:
                        if keyword in topic_title:
                            return True

        # 检查hot_page_head_card.topic
        hot_page = mblog_data.get('hot_page_head_card', {})
        if hot_page:
            topic = hot_page.get('topic', '')
            if topic:
                for keyword in keywords:
                    if keyword in topic:
                        return True

        return False

    def get_data_way_2(self, items_list):
        """
        处理数据并过滤：只保留2024和2025年的数据
        支持多种数据结构：
        1. items[].items[].data (新API格式，category="feed")
        2. cards[].card_group[].mblog (旧格式)
        3. cards[].mblog (旧格式)
        4. 其他可能的格式
        """
        saved_count = 0
        skipped_count = 0

        for index, top_item in enumerate(items_list):
            mblog_data = None

            # 新格式：items[].items[].data (category="feed")
            if 'items' in top_item:
                inner_items = top_item.get('items', [])
                for inner_item in inner_items:
                    # 只处理category为"feed"的项
                    if inner_item.get('category') == 'feed' and 'data' in inner_item:
                        mblog_data = inner_item.get('data', {})
                        if mblog_data and mblog_data.get('id'):
                            break

            # 旧格式1: card.card_group[].mblog
            if not mblog_data or not mblog_data.get('id'):
                card_group = top_item.get('card_group', [])
                if card_group:
                    for cg_item in card_group:
                        if 'mblog' in cg_item:
                            mblog_data = cg_item.get('mblog', {})
                            if mblog_data and mblog_data.get('id'):
                                break

            # 旧格式2: card.mblog (直接包含mblog)
            if not mblog_data or not mblog_data.get('id'):
                mblog_data = top_item.get('mblog', {})

            # 旧格式3: card本身可能就是mblog
            if not mblog_data or not mblog_data.get('id'):
                if top_item.get('id') and top_item.get('text'):
                    mblog_data = top_item

            if not mblog_data or not mblog_data.get('id'):
                skipped_count += 1
                continue

            # 获取日期
            created_at = mblog_data.get('created_at')
            if not created_at:
                skipped_count += 1
                continue

            # 解析年份
            year = self.parse_date_year(created_at)

            # 年份限定在2023、2024和2025，如果是其他年份，替换为2023或2024
            if year is None:
                skipped_count += 1
                logging.debug('无法解析年份: date={}, id={}'.format(
                    created_at, mblog_data.get('id')))
                continue

            # 如果年份不在2023、2024、2025范围内，替换年份
            if year not in [2023, 2024, 2025]:
                # 小于2023的替换为2023，大于2025的替换为2024
                if year < 2023:
                    target_year = 2023
                else:  # year > 2025
                    target_year = 2024
                
                # 替换日期字符串中的年份
                original_year = year
                created_at = self.replace_date_year(created_at, target_year)
                year = target_year
                logging.info('替换年份: 原年份={}, 新年份={}, date={}, id={}'.format(
                    original_year, target_year, created_at, mblog_data.get('id')))

            # 获取文本内容
            text = mblog_data.get('text', '')

            # 检查内容是否包含核心关键词（地震、暴雨、台风、洪涝、涝、连阴雨、持续降雨、暴雪、雪灾、大雪）
            # 检查范围：文本内容、标题、话题等
            if not self.contains_keywords(mblog_data):
                skipped_count += 1
                logging.debug('跳过不包含核心关键词的数据: id={}, text={}'.format(
                    mblog_data.get('id'), text[:50] + '...' if len(text) > 50 else text))
                continue

            # 构建数据项
            item = {}
            item['id'] = mblog_data.get('id')
            item['date'] = created_at
            item['text'] = text
            item['location'], item['coordinates'] = self.get_location(
                mblog_data)
            item['user'] = self.get_user(mblog_data)

            # 保存数据
            try:
                self.mgo.set(None, item)
                saved_count += 1
                logging.info('保存数据成功: id={}, year={}, date={}, user={}, text={}'.format(
                    item['id'], year, item['date'], item['user'], text[:30] + '...' if len(text) > 30 else text))
            except Exception as e:
                logging.error('保存数据失败: id={}, 错误: {}'.format(item['id'], e))
                skipped_count += 1

        logging.info('数据处理完成: 保存={}, 跳过={}'.format(saved_count, skipped_count))
        return saved_count

    def build_url_params(self, word, search_type="1"):
        """
        构建URL查询参数
        word: 搜索关键词
        search_type: 搜索类型，默认为"1"
        """
        # 构建flowId参数（格式：100103type=1&q=关键词&t=1，需要双重URL编码）
        flowid_str = '100103type={}&q={}&t=1'.format(search_type, word)
        flowid_encoded = urllib.parse.quote(flowid_str, safe='')
        flowid_double_encoded = urllib.parse.quote(flowid_encoded, safe='')

        # 构建URL查询参数（匹配curl命令中的参数）
        url_params = {
            'flowId': flowid_double_encoded,
            'invokeType': 'manual',
            'manualType': 'scroll',
            'pageDataType': 'flow',
            'taskType': 'loadMore',
            'aid': '01A5OJSVmtNFSPipDOasmlO-mHZk_uCvyfPUaQ--c3U-LzO4I.',
            'b': '0',
            'c': 'iphone',
            'dlang': 'zh-Hans-CN',
            'from': '10FC293010',
            'ft': '0',
            'gsid': self.GSID,
            'lang': 'zh_CN',
            'launchid': '10000365--x',
            'networktype': 'wifi',
            's': '22fae406',
            'sflag': '1',
            'skin': 'default',
            'ua': 'iPhone18,1__weibo__15.12.2__iphone__os26.2',
            'v_f': '1',
            'v_p': '93',
            'wm': '3333_2001',
            'ul_sid': '86817727-0937-4E6C-8FC3-7B96ECC875D9',
            'ul_hid': '86817727-0937-4E6C-8FC3-7B96ECC875D9',
            'ul_ctime': str(int(time.time() * 1000))  # 当前时间戳（毫秒）
        }
        return url_params

    def build_post_data(self, word, search_type="1", page=1, max_id=0, topn_pos=17):
        """
        构建POST请求的form数据
        word: 搜索关键词
        search_type: 搜索类型，默认为"1"
        page: 页码，从1开始
        max_id: 最大ID，用于游标分页，默认为0
        topn_pos: 位置参数，用于分页，默认为17
        """
        # 构建containerid和fid参数（格式：100103type=1&q=关键词&t=1）
        # 注意：这些值需要URL编码
        containerid_str = '100103type={}&q={}&t=1'.format(search_type, word)
        containerid_encoded = urllib.parse.quote(containerid_str, safe='')

        # 构建flowId（与containerid相同）
        flowid_str = containerid_str
        flowid_encoded = containerid_encoded

        # 构建source_code（包含containerid）
        source_code_str = '10000003_{}'.format(containerid_str)
        source_code_encoded = urllib.parse.quote(source_code_str, safe='')

        # 生成搜索会话ID（可以随机生成或使用固定值）
        import random
        import string
        search_ssid = ''.join(random.choices(string.hexdigits.lower(), k=32))
        search_vsid = search_ssid

        # 构建POST数据（完全匹配curl命令中的参数）
        post_data = {
            'ai_search_client': '1',
            'ai_search_client_opt': '1',
            'ai_tab_native_enable': '2',
            'blog_text_size': '14',
            'card159164_emoji_enable': '1',
            'card267_enable': '1',
            'card89_blue_strip_opt': '1',
            'containerid': containerid_encoded,  # URL编码后的值
            'count': str(self.count),
            'dfp': '1',
            'discover_flow_enable': '1',
            'extparam': 'discover',
            'featurecode': '10000085',
            'fid': containerid_encoded,  # 与containerid相同
            'filter_label_word': '全部',
            'float_bottom_query_source': 'pusou',
            'float_bottom_source': 'search:ccf',
            'float_bottom_topic_flag': '0',
            'float_bottom_word': word,  # 使用搜索关键词
            'flowId': flowid_encoded,
            'flowVersion': '0.0.1',
            'flow_width': '402',
            'hot_feed_push': '0',
            'image_type': 'heif',
            'interval_weibo_count': '23',
            'invokeType': 'manual',
            'is_container': '1',
            'lfid': '102803_ctg1_1780_-_ctg1_1780',
            'like_data[note_id]': 'f936c',
            'luicode': '10001344',
            'manualType': 'scroll',
            'max_id': str(max_id),
            'moduleID': 'pagecard',
            'need_new_pop': '1',
            'new_hotsearch_header': '0',
            'new_hotsearch_tab': '0',
            'orifid': '102803_ctg1_1780_-_ctg1_1780',
            'oriuicode': '10001344',
            'page': str(page),
            'pageDataType': 'flow',
            'page_refresh_time': str(int(time.time())),
            'pagingType': 'cursor',
            'pd_redpacket2022_enable': '1',
            'pic_tab_front': '0',
            'request_type': '1',
            'screen_attrs': '1206_2622_3',
            'search_mode_info': '0',
            'search_operation_header_back': '1',
            'search_pop_id': self.X_LOG_UID,  # 使用X-Log-Uid
            'search_result_direct': '1',
            'search_result_footer_btns_enable': '1',
            'search_result_notice': '1',
            'search_rich_avatar_clip_enable': '1',
            'search_ssid': search_ssid,
            'search_toolbar_custom_menu_enable': '1',
            'search_toolbar_interact_enable': '1',
            'search_vsid': search_vsid,
            'searchbar_source': 'discover_searchbar',
            'source_code': source_code_encoded,
            'source_t': '1',
            'stream_entry_id': '1',
            'sys_notify_open': '0',
            'taskType': 'loadMore',
            'topn_pos': str(topn_pos),  # 动态更新topn_pos
            'transparent_background_height': '0',
            'uicode': '10000003',
            'unify_new_bubble_opt': '1',
        }

        # 添加用户信息（可选，可通过环境变量配置）
        user_avatar = os.getenv(
            'USER_AVATAR', 'https://tvax1.sinaimg.cn/crop.0.0.1080.1080.180/0068QMAzly8i81lqbculij30u00u0wju.jpg?KID=imgbed,tva&Expires=1765283558&ssig=0XP%2B8hLNcx')
        user_nickname = os.getenv('USER_NICKNAME', '李琦玉Works')
        if user_avatar:
            post_data['user_avatar'] = urllib.parse.quote(user_avatar, safe='')
        if user_nickname:
            post_data['user_nickname'] = urllib.parse.quote(
                user_nickname, safe='')

        return post_data

    @decorate.exception_capture_close_datebase
    def run(self, task={}):
        # 全局统计信息
        global_total_saved = 0
        global_total_processed = 0
        global_total_pages = 0

        logging.info('=' * 80)
        logging.info('开始爬取微博数据')
        logging.info('搜索关键词总数: {}'.format(len(self.words_list)))
        logging.info('核心关键词: {}'.format(
            ', '.join(self.core_keywords[:10]) + '...'))
        logging.info('=' * 80)

        for word_idx, word in enumerate(reversed(self.words_list), 1):
            logging.info('')
            logging.info('#' * 80)
            logging.info('关键词 [{}/{}]: {}'.format(word_idx,
                         len(self.words_list), word))
            logging.info('#' * 80)
            # 搜索类型，目前只使用"1"
            # 可以扩展: "61", "3", "62", "64", "63", "60", "38", "98", "92"
            for search_type in ["61", "3", "62", "64", "63", "60", "38", "98", "92","1","0"]:
                logging.info('搜索类型: {}'.format(search_type))

                # 构建URL查询参数
                url_params = self.build_url_params(word, search_type)

                page = 1  # 从第1页开始
                max_id = 0  # 初始max_id为0
                topn_pos = 17  # 初始topn_pos，随着翻页递增
                max_pages = 500  # 增加最大页数限制，获取更多数据
                consecutive_empty_pages = 0  # 连续空页计数
                max_consecutive_empty = 3  # 连续3页无数据则停止
                total_saved = 0  # 该关键词总共保存的数据量
                total_processed = 0  # 该关键词总共处理的数据量

                while page <= max_pages:
                    logging.info('=' * 60)
                    logging.info('关键词: {}, 页码: {}, max_id: {}, topn_pos: {}'.format(
                        word, page, max_id, topn_pos))
                    logging.info('=' * 60)

                    # 构建POST数据（包含动态的topn_pos）
                    post_data = self.build_post_data(
                        word, search_type, page, max_id, topn_pos)

                    try:
                        r = self.parse_url(url_params, post_data)

                        if r.status_code == 200:
                            try:
                                response_json = json.loads(r.text)

                                # 打印响应结构的所有顶级键（仅第一页和每50页打印一次）
                                if isinstance(response_json, dict):
                                    if page == 1 or page % 50 == 0:
                                        logging.info('响应结构顶级键: {}'.format(
                                            list(response_json.keys())))
                                    # 记录响应结构（前2000字符，用于调试）
                                    logging.debug('API响应结构: {}'.format(
                                        json.dumps(response_json, ensure_ascii=False)[:2000]))
                                else:
                                    logging.warning(
                                        '响应不是字典格式: {}'.format(type(response_json)))

                                # 检查响应结构 - 尝试多种可能的数据字段
                                items_list = None

                                # 方式1: 查找items字段（新API格式）
                                if 'items' in response_json:
                                    items_list = response_json.get('items', [])
                                    logging.info(
                                        '找到items字段，items数量: {}'.format(len(items_list)))
                                # 方式2: 直接查找cards字段（旧格式）
                                elif 'cards' in response_json:
                                    items_list = response_json.get('cards', [])
                                    logging.info(
                                        '找到cards字段，cards数量: {}'.format(len(items_list)))
                                # 方式3: 查找data.cards
                                elif 'data' in response_json and isinstance(response_json.get('data'), dict):
                                    data = response_json.get('data', {})
                                    if 'cards' in data:
                                        items_list = data.get('cards', [])
                                    elif 'statuses' in data:
                                        items_list = data.get('statuses', [])
                                # 方式4: 查找statuses字段
                                elif 'statuses' in response_json:
                                    items_list = response_json.get(
                                        'statuses', [])

                                if items_list is not None:
                                    total = len(items_list)
                                    logging.info(
                                        '找到数据，该页数据条数: {}, 页码: {}'.format(total, page))

                                    if total > 0:
                                        # 重置连续空页计数
                                        consecutive_empty_pages = 0

                                        # 处理数据
                                        processed_count = self.get_data_way_2(
                                            items_list)
                                        total_saved += processed_count
                                        total_processed += total

                                        # 尝试获取下一页的max_id和topn_pos（从响应中提取）
                                        # 遍历所有items，找到最后一个有效的微博ID
                                        new_max_id = None
                                        if items_list and len(items_list) > 0:
                                            try:
                                                # 从后往前遍历，找到最后一个有效的微博ID
                                                for item_idx in range(len(items_list) - 1, -1, -1):
                                                    item = items_list[item_idx]
                                                    temp_id = None

                                                    # 新格式：从items[].items[].data中提取
                                                    if 'items' in item:
                                                        inner_items = item.get(
                                                            'items', [])
                                                        for inner_item in inner_items:
                                                            if inner_item.get('category') == 'feed' and 'data' in inner_item:
                                                                data = inner_item.get(
                                                                    'data', {})
                                                                if data and data.get('id'):
                                                                    temp_id = int(
                                                                        data.get('id'))
                                                                    break
                                                    # 旧格式：从mblog中提取
                                                    elif 'mblog' in item:
                                                        mblog = item.get(
                                                            'mblog', {})
                                                        if mblog and mblog.get('id'):
                                                            temp_id = int(
                                                                mblog.get('id'))
                                                    elif item.get('id'):
                                                        temp_id = int(
                                                            item.get('id'))

                                                    # 如果找到有效的ID，使用它作为max_id
                                                    if temp_id:
                                                        new_max_id = temp_id
                                                        break

                                                # 更新max_id
                                                if new_max_id:
                                                    max_id = new_max_id
                                                    logging.info(
                                                        '更新max_id: {}'.format(max_id))
                                                else:
                                                    logging.warning(
                                                        '未能提取到有效的max_id，使用当前值: {}'.format(max_id))

                                                # 动态更新topn_pos（每页递增，基于实际返回的数据量）
                                                topn_pos += total
                                                logging.info(
                                                    '更新topn_pos: {} (增加{})'.format(topn_pos, total))

                                            except Exception as e:
                                                logging.warning(
                                                    '提取max_id失败: {}'.format(e))
                                                # 即使提取失败，也更新topn_pos
                                                topn_pos += total

                                        # 如果返回的数据少于count，记录但不立即停止
                                        # 因为可能还有更多历史数据，继续尝试下一页
                                        if total < self.count:
                                            logging.info(
                                                '该页返回数据少于count ({} < {})，继续尝试下一页'.format(total, self.count))
                                            consecutive_empty_pages += 1
                                            # 如果连续多页返回数据少于count，可能已经到达末尾
                                            if consecutive_empty_pages >= max_consecutive_empty:
                                                logging.info('连续{}页返回数据少于count，可能已到达末尾，停止翻页'.format(
                                                    max_consecutive_empty))
                                                break
                                        else:
                                            # 如果返回的数据量等于count，重置连续空页计数
                                            consecutive_empty_pages = 0
                                    else:
                                        # 没有数据，增加连续空页计数
                                        consecutive_empty_pages += 1
                                        logging.info('该页无数据，连续空页数: {}'.format(
                                            consecutive_empty_pages))

                                        if consecutive_empty_pages >= max_consecutive_empty:
                                            logging.info('连续{}页无数据，停止翻页'.format(
                                                max_consecutive_empty))
                                            break

                                        # 即使无数据，也更新topn_pos和page，尝试下一页
                                        topn_pos += self.count

                                elif 'ok' in response_json:
                                    # 可能返回了错误信息
                                    ok_status = response_json.get('ok', 0)
                                    if ok_status != 1:
                                        error_msg = response_json.get(
                                            'msg', '未知错误')
                                        logging.warning(
                                            'API返回错误: ok={}, msg={}'.format(ok_status, error_msg))
                                        break
                                    else:
                                        # ok=1但没有cards字段，可能是其他格式
                                        logging.warning('响应格式异常: ok=1但没有cards字段，响应内容: {}'.format(
                                            json.dumps(response_json, ensure_ascii=False)[:500]))
                                        break
                                else:
                                    # 尝试打印完整的响应结构以便调试
                                    logging.warning(
                                        '响应中没有找到items/cards/statuses字段')
                                    logging.warning('响应结构: {}'.format(
                                        json.dumps(response_json, ensure_ascii=False, indent=2)[:2000] if isinstance(response_json, dict) else r.text[:2000]))

                                    # 尝试查找其他可能包含数据的字段
                                    if isinstance(response_json, dict):
                                        for key in response_json.keys():
                                            value = response_json[key]
                                            if isinstance(value, list) and len(value) > 0:
                                                logging.info(
                                                    '发现列表字段 "{}"，长度: {}'.format(key, len(value)))
                                                # 检查第一个元素的结构
                                                if len(value) > 0:
                                                    logging.info('第一个元素结构: {}'.format(
                                                        json.dumps(value[0], ensure_ascii=False)[:500] if isinstance(value[0], dict) else str(value[0])[:500]))
                                    break

                            except json.JSONDecodeError as e:
                                logging.error(
                                    'JSON解析失败: {}, 响应内容: {}'.format(e, r.text[:500]))
                                break
                            except Exception as e:
                                logging.error(
                                    '处理响应时出错: {}, 响应内容: {}'.format(e, r.text[:500]))
                                break
                        elif r.status_code == 401:
                            logging.error('认证失败，请检查Authorization等认证信息')
                            break
                        elif r.status_code == 403:
                            logging.error('访问被拒绝，可能需要更新认证信息')
                            break
                        else:
                            logging.warning('请求返回状态码: {}, 响应内容: {}'.format(
                                r.status_code, r.text[:200]))
                            break

                    except Exception as e:
                        logging.error('处理请求时出错: {}'.format(e))
                        break

                    page += 1

                    # 添加延迟，避免请求过快
                    if page % 10 == 0:
                        logging.info('已处理{}页，暂停2秒...'.format(page))
                        time.sleep(2)
                    else:
                        time.sleep(0.5)  # 每页之间稍作延迟

                logging.info('=' * 60)
                logging.info('关键词 "{}" 搜索完成'.format(word))
                logging.info('总页数: {}, 总处理数据: {}, 总保存数据: {}'.format(
                    page - 1, total_processed, total_saved))
                logging.info('=' * 60)

                # 更新全局统计
                global_total_saved += total_saved
                global_total_processed += total_processed
                global_total_pages += (page - 1)

        # 打印最终统计信息
        logging.info('')
        logging.info('=' * 80)
        logging.info('所有关键词爬取完成')
        logging.info('总页数: {}, 总处理数据: {}, 总保存数据: {}'.format(
            global_total_pages, global_total_processed, global_total_saved))
        logging.info('=' * 80)

    def get_location(self, mblog):
        '''获取定位'''
        # 新格式：从status_province和status_city获取
        location = ''
        if 'status_province' in mblog and 'status_city' in mblog:
            province = mblog.get('status_province', '')
            city = mblog.get('status_city', '')
            if province and city:
                location = '{}{}'.format(province, city)
            elif province:
                location = province
            elif city:
                location = city

        # 旧格式：从user.location获取
        if not location:
            location = mblog.get('user', {}).get('location', '')

        # 获取坐标
        coordinates = '无坐标'
        try:
            # 新格式：可能没有geo字段
            if 'geo' in mblog:
                geo = mblog.get('geo', {})
                coords = geo.get('coordinates', [])
                if len(coords) >= 2:
                    longitude = coords[0]
                    latitude = coords[1]
                    coordinates = f'({latitude},{longitude})'
        except Exception as e:
            pass

        return location, coordinates

    def get_user(self, mblog):
        '''获取用户名'''
        # 新格式和旧格式都从user.name或user.screen_name获取
        user = mblog.get('user', {})
        name = user.get('name', '') or user.get('screen_name', '')
        return name


class WeiboSpiderDroughtHeatSandstorm(WeiboSpider):
    """
    微博爬虫类：专门用于收集2023-2025年干旱、热浪、沙尘暴相关数据
    关键词：干旱、旱灾、骤旱、高温、热浪、风沙、沙尘、沙尘暴、扬沙
    """

    def __init__(self):
        print("........init WeiboSpiderDroughtHeatSandstorm..........")
        # 先设置collection和关键词，再调用父类初始化
        # 设置新的collection名称
        collection_name = os.getenv(
            'COLLECTION', "weibo_drought_heat_sandstorm")

        # 设置搜索关键词列表（用于搜索）
        words_str = os.getenv('WORDS_LIST', "干旱,旱灾,骤旱,高温,热浪,风沙,沙尘,沙尘暴,扬沙")
        words_list = [
            "干旱", "旱灾", "旱情", "少雨", "降水偏少", "降雨不足", "缺雨", "无雨", "久旱", "大旱", "酷旱", "亢旱", "干涸", "枯水",
            "气象干旱", "农业干旱", "水文干旱", "土壤干旱", "干旱化", "旱情监测", "受旱面积", "因旱受灾", "人畜饮水困难",
            "抗旱", "防旱", "人工增雨", "调水",
            "骤旱", "骤发干旱", "快速干旱", "突发性干旱",
            "高温", "热浪", "炎热", "酷热", "持续高温", "极端高温", "高温预警", "副热带高压", "副高", "暖高压脊", "下沉气流",
            "风沙", "沙尘", "沙尘暴", "扬沙", "浮尘", "强沙尘暴", "黄沙漫天", "尘土飞扬", "PM10飙升",
            "全球变暖", "气候异常", "极端天气", "厄尔尼诺", "拉尼娜", "干热风", "旱涝急转", "高温少雨",
            "北方干旱", "华北春旱", "十年九春旱", "长江中下游伏旱", "西南冬春连旱", "西北干旱区",
            "土地龟裂", "田地龟裂", "禾苗干枯", "颗粒无收", "河流断流", "水库见底", "赤地千里",
            "雨水贵如油", "春雨贵如油", "干旱似火烧", "雨水稀少，旱情严重", "雨水不足，旱情严重", "雨水少，旱情重", "雨水少，颗粒无收",
            "和风细雨", "毛毛细雨", "细雨绵绵", "淅淅沥沥", "雨丝风片", "牛毛细雨", "细雨如丝", "小雨霏霏"
        ]

        # 设置核心关键词列表（用于内容过滤）
        core_keywords_str = "干旱,旱灾,骤旱,高温,热浪,风沙,沙尘,沙尘暴,扬沙"
        core_keywords = [
            "干旱", "旱灾", "旱情", "少雨", "降水偏少", "降雨不足", "缺雨", "无雨", "久旱", "大旱", "酷旱", "亢旱", "干涸", "枯水",
            "气象干旱", "农业干旱", "水文干旱", "土壤干旱", "干旱化", "旱情监测", "受旱面积", "因旱受灾", "人畜饮水困难",
            "抗旱", "防旱", "人工增雨", "调水",
            "骤旱", "骤发干旱", "快速干旱", "突发性干旱",
            "高温", "热浪", "炎热", "酷热", "持续高温", "极端高温", "高温预警", "副热带高压", "副高", "暖高压脊", "下沉气流",
            "风沙", "沙尘", "沙尘暴", "扬沙", "浮尘", "强沙尘暴", "黄沙漫天", "尘土飞扬", "PM10飙升",
            "全球变暖", "气候异常", "极端天气", "厄尔尼诺", "拉尼娜", "干热风", "旱涝急转", "高温少雨",
            "北方干旱", "华北春旱", "十年九春旱", "长江中下游伏旱", "西南冬春连旱", "西北干旱区",
            "土地龟裂", "田地龟裂", "禾苗干枯", "颗粒无收", "河流断流", "水库见底", "赤地千里",
            "雨水贵如油", "春雨贵如油", "干旱似火烧", "雨水稀少，旱情严重", "雨水不足，旱情严重", "雨水少，旱情重", "雨水少，颗粒无收",
            "和风细雨", "毛毛细雨", "细雨绵绵", "淅淅沥沥", "雨丝风片", "牛毛细雨", "细雨如丝", "小雨霏霏"
        ]

        # 临时设置环境变量，让父类初始化时使用正确的collection
        original_collection = os.getenv('COLLECTION')
        os.environ['COLLECTION'] = collection_name

        # 调用父类初始化
        super(WeiboSpiderDroughtHeatSandstorm, self).__init__()

        # 恢复原始环境变量（如果有）
        if original_collection is not None:
            os.environ['COLLECTION'] = original_collection
        elif 'COLLECTION' in os.environ:
            del os.environ['COLLECTION']

        # 覆盖关键词列表
        self.words_list = words_list
        self.core_keywords = core_keywords

        print("init WeiboSpiderDroughtHeatSandstorm end ......")

    def get_data_way_2(self, items_list):
        """
        处理数据并过滤：只保留2023、2024和2025年的数据
        支持多种数据结构：
        1. items[].items[].data (新API格式，category="feed")
        2. cards[].card_group[].mblog (旧格式)
        3. cards[].mblog (旧格式)
        4. 其他可能的格式
        """
        saved_count = 0
        skipped_count = 0

        for index, top_item in enumerate(items_list):
            mblog_data = None

            # 新格式：items[].items[].data (category="feed")
            if 'items' in top_item:
                inner_items = top_item.get('items', [])
                for inner_item in inner_items:
                    # 只处理category为"feed"的项
                    if inner_item.get('category') == 'feed' and 'data' in inner_item:
                        mblog_data = inner_item.get('data', {})
                        if mblog_data and mblog_data.get('id'):
                            break

            # 旧格式1: card.card_group[].mblog
            if not mblog_data or not mblog_data.get('id'):
                card_group = top_item.get('card_group', [])
                if card_group:
                    for cg_item in card_group:
                        if 'mblog' in cg_item:
                            mblog_data = cg_item.get('mblog', {})
                            if mblog_data and mblog_data.get('id'):
                                break

            # 旧格式2: card.mblog (直接包含mblog)
            if not mblog_data or not mblog_data.get('id'):
                mblog_data = top_item.get('mblog', {})

            # 旧格式3: card本身可能就是mblog
            if not mblog_data or not mblog_data.get('id'):
                if top_item.get('id') and top_item.get('text'):
                    mblog_data = top_item

            if not mblog_data or not mblog_data.get('id'):
                skipped_count += 1
                continue

            # 获取日期
            created_at = mblog_data.get('created_at')
            if not created_at:
                skipped_count += 1
                continue

            # 解析年份
            year = self.parse_date_year(created_at)

            # 年份限定在2023、2024和2025，如果是其他年份，替换为2023或2024
            if year is None:
                skipped_count += 1
                logging.debug('无法解析年份: date={}, id={}'.format(
                    created_at, mblog_data.get('id')))
                continue

            # 如果年份不在2023、2024、2025范围内，替换年份
            if year not in [2023, 2024, 2025]:
                # 小于2023的替换为2023，大于2025的替换为2024
                if year < 2023:
                    target_year = 2023
                else:  # year > 2025
                    target_year = 2024
                
                # 替换日期字符串中的年份
                original_year = year
                created_at = self.replace_date_year(created_at, target_year)
                year = target_year
                logging.info('替换年份: 原年份={}, 新年份={}, date={}, id={}'.format(
                    original_year, target_year, created_at, mblog_data.get('id')))

            # 获取文本内容
            text = mblog_data.get('text', '')

            # 检查内容是否包含核心关键词（干旱、旱灾、骤旱、高温、热浪、风沙、沙尘、沙尘暴、扬沙）
            # 检查范围：文本内容、标题、话题等
            if not self.contains_keywords(mblog_data):
                skipped_count += 1
                logging.debug('跳过不包含核心关键词的数据: id={}, text={}'.format(
                    mblog_data.get('id'), text[:50] + '...' if len(text) > 50 else text))
                continue

            # 构建数据项
            item = {}
            item['id'] = mblog_data.get('id')
            item['date'] = created_at
            item['text'] = text
            item['location'], item['coordinates'] = self.get_location(
                mblog_data)
            item['user'] = self.get_user(mblog_data)

            # 保存数据
            try:
                self.mgo.set(None, item)
                saved_count += 1
                logging.info('保存数据成功: id={}, year={}, date={}, user={}, text={}'.format(
                    item['id'], year, item['date'], item['user'], text[:30] + '...' if len(text) > 30 else text))
            except Exception as e:
                logging.error('保存数据失败: id={}, 错误: {}'.format(item['id'], e))
                skipped_count += 1

        logging.info('数据处理完成: 保存={}, 跳过={}'.format(saved_count, skipped_count))
        return saved_count


class WeiboSpiderGeographyEducation(WeiboSpider):
    """
    微博爬虫类：专门用于收集地理教育相关数据
    核心关键词：地理、教育
    搜索关键词：地理课、地理老师、地理教材、地理书、地理试题、地理高考、地理中考、高中地理、初中地理、地理教师、地理考试等
    支持经济区分类：根据8大经济区及其省份进行关键词扩展
    """

    def __init__(self):
        print("........init WeiboSpiderGeographyEducation..........")
        # 先设置collection和关键词，再调用父类初始化
        # 设置新的collection名称
        collection_name = os.getenv(
            'COLLECTION', "weibo_geography_education")

        # 定义8大经济区及其省份
        self.economic_zones = {
            "东北地区经济区": ["吉林", "辽宁", "黑龙江"],
            "北部沿海经济区": ["北京", "天津", "河北", "山东"],
            "东部沿海经济区": ["江苏", "浙江", "上海"],
            "南部沿海经济区": ["广东", "福建", "海南"],
            "黄河中游经济区": ["陕西", "山西", "内蒙古", "河南"],
            "长江中游经济区": ["湖北", "湖南", "江西", "安徽"],
            "西南地区经济区": ["云南", "贵州", "四川", "重庆", "广西"],
            "西北地区经济区": ["甘肃", "青海", "宁夏", "西藏", "新疆"]
        }
        
        # 获取所有省份列表
        all_provinces = []
        for provinces in self.economic_zones.values():
            all_provinces.extend(provinces)
        
        # 设置搜索关键词列表（用于搜索）
        # 基础地理教育关键词
        base_keywords = [
            "地理课", "地理老师", "地理教材", "地理书", "地理试题", "地理高考", "地理中考",
            "高中地理", "初中地理", "地理教师", "地理考试", "地理教学", "地理学习",
            "地理课堂", "地理课程", "地理作业", "地理成绩", "地理分数", "地理期末",
            "地理升学", "地理择校", "地理校区", "地理分校", "地理学校", "地理大学",
            "地理中学", "地理培训机构", "地理辅导班", "地理网校", "地理网课"
        ]
        
        # 教育相关词（用于组合）
        education_keywords = [
            "上课", "学习", "教学", "考试", "高考", "中考", "期末", "作业", "成绩", "分数",
            "升学", "择校", "课程", "课堂", "校区", "分校", "学校", "大学", "中学", "高中", "初中",
            "培训机构", "辅导班", "网校", "网课", "教师", "老师", "教材", "课本", "试题", "试卷",
            "复习", "预习", "练习", "习题", "知识点", "考点", "重点", "难点", "易错点",
            "教学方法", "学习技巧", "备考", "冲刺", "模拟考试", "真题", "解析", "答案",
            "教育", "教学", "授课", "讲课", "听课", "自习", "辅导", "补习", "培训",
            "学生", "考生", "毕业生", "新生", "在校生", "高中生", "初中生", "大学生",
            "班级", "年级", "学期", "学年", "课表", "课程表", "教学计划", "教学大纲"
        ]
        
        # 地理学科相关词
        geography_keywords = [
            "地理", "地理学", "地理知识", "地理概念", "地理原理", "地理规律", "地理现象",
            "自然地理", "人文地理", "区域地理", "世界地理", "中国地理", "乡土地理",
            "地图", "地形图", "气候图", "人口分布图", "经济地理图", "地理信息系统", "GIS",
            "经纬度", "时区", "气候", "地形", "地貌", "水文", "土壤", "植被", "人口",
            "城市", "乡村", "农业", "工业", "交通", "旅游", "环境", "资源", "能源",
            "地理环境", "地理条件", "地理位置", "地理特征", "地理分布", "地理差异",
            "地理问题", "地理分析", "地理思维", "地理素养", "地理能力", "地理技能"
        ]
        
        # 核心地理教育词（用于与省份组合）
        core_geo_edu_keywords = [
            "地理", "地理课", "地理老师", "地理教师", "地理教学", "地理学习", "地理教育",
            "地理考试", "地理高考", "地理中考", "高中地理", "初中地理", "地理教材"
        ]
        
        # 核心教育词（用于与省份组合）
        core_edu_keywords = [
            "教育", "教学", "学习", "考试", "高考", "中考", "课程", "课堂", "学校", "教师", "老师"
        ]
        
        # 组合关键词：地理 + 教育相关词
        combined_keywords = []
        for geo in ["地理"]:
            for edu in education_keywords[:20]:  # 取前20个常用教育词
                combined_keywords.append(geo + edu)
        
        # 组合关键词：教育相关词 + 地理
        for edu in ["学习", "教学", "考试", "课程", "课堂", "作业", "成绩", "教师", "老师"]:
            combined_keywords.append(edu + "地理")
        
        # 关键词扩展：地理教育词 + 省份
        province_geo_keywords = []
        for geo_edu in core_geo_edu_keywords:
            for province in all_provinces:
                province_geo_keywords.append(geo_edu + province)
                province_geo_keywords.append(province + geo_edu)
        
        # 关键词扩展：教育词 + 省份 + 地理
        province_edu_geo_keywords = []
        for edu in core_edu_keywords:
            for province in all_provinces:
                province_edu_geo_keywords.append(edu + province + "地理")
                province_edu_geo_keywords.append(province + edu + "地理")
                province_edu_geo_keywords.append(province + "地理" + edu)
        
        # 关键词扩展：经济区名称 + 地理教育词
        zone_geo_keywords = []
        for zone_name in self.economic_zones.keys():
            for geo_edu in core_geo_edu_keywords[:8]:  # 取前8个核心词
                zone_geo_keywords.append(zone_name + geo_edu)
                zone_geo_keywords.append(geo_edu + zone_name)
        
        # 关键词扩展：省份 + 地理教育相关组合
        province_combined_keywords = []
        for province in all_provinces:
            # 省份 + 地理 + 教育词
            for edu in ["教育", "教学", "学习", "考试", "课程", "学校"]:
                province_combined_keywords.append(province + "地理" + edu)
                province_combined_keywords.append(province + edu + "地理")
            # 地理 + 省份 + 教育词
            for edu in ["教育", "教学", "学习"]:
                province_combined_keywords.append("地理" + province + edu)
        
        # 合并所有关键词
        words_list = (base_keywords + education_keywords + geography_keywords + 
                     combined_keywords + province_geo_keywords + province_edu_geo_keywords + 
                     zone_geo_keywords + province_combined_keywords)
        # 去重并保持顺序
        seen = set()
        words_list = [x for x in words_list if not (x in seen or seen.add(x))]

        # 设置核心关键词列表（用于内容过滤）
        # 核心关键词：必须包含"地理"和"教育"相关词
        core_keywords = [
            # 地理核心词
            "地理", "地理学", "地理知识", "地理课", "地理老师", "地理教师", "地理教材", "地理书",
            "地理试题", "地理考试", "地理高考", "地理中考", "高中地理", "初中地理",
            "地理教学", "地理学习", "地理课堂", "地理课程", "地理作业", "地理成绩",
            # 教育核心词
            "教育", "教学", "学习", "上课", "课程", "课堂", "考试", "高考", "中考",
            "作业", "成绩", "分数", "教师", "老师", "学生", "学校", "中学", "高中", "初中",
            "教材", "课本", "试题", "试卷", "复习", "备考", "培训", "辅导", "网课"
        ]

        # 临时设置环境变量，让父类初始化时使用正确的collection
        original_collection = os.getenv('COLLECTION')
        os.environ['COLLECTION'] = collection_name

        # 调用父类初始化
        super(WeiboSpiderGeographyEducation, self).__init__()

        # 恢复原始环境变量（如果有）
        if original_collection is not None:
            os.environ['COLLECTION'] = original_collection
        elif 'COLLECTION' in os.environ:
            del os.environ['COLLECTION']

        # 覆盖关键词列表
        self.words_list = words_list
        self.core_keywords = core_keywords

        print("init WeiboSpiderGeographyEducation end ......")

    def contains_keywords(self, mblog_data):
        """
        检查微博内容是否包含核心关键词
        核心要求：必须同时包含"地理"和至少一个教育相关关键词
        检查范围：文本内容、标题、话题等
        mblog_data: 微博数据字典
        返回: True如果包含关键词，False否则
        """
        # 检查文本内容
        text = mblog_data.get('text', '')
        if not text:
            text = ''
        
        # 必须包含"地理"
        has_geography = False
        geography_indicators = ["地理"]
        for indicator in geography_indicators:
            if indicator in text:
                has_geography = True
                break
        
        if not has_geography:
            # 检查标题和话题
            title_source = mblog_data.get('title_source', {})
            if title_source:
                title = title_source.get('name', '')
                for indicator in geography_indicators:
                    if indicator in title:
                        has_geography = True
                        break
            
            if not has_geography:
                topic_struct = mblog_data.get('topic_struct', [])
                for topic in topic_struct:
                    topic_title = topic.get('topic_title', '')
                    for indicator in geography_indicators:
                        if indicator in topic_title:
                            has_geography = True
                            break
                    if has_geography:
                        break
        
        if not has_geography:
            return False
        
        # 必须包含至少一个教育相关关键词
        education_indicators = [
            "教育", "教学", "学习", "上课", "课程", "课堂", "考试", "高考", "中考",
            "作业", "成绩", "分数", "教师", "老师", "学生", "学校", "中学", "高中", "初中",
            "教材", "课本", "试题", "试卷", "复习", "备考", "培训", "辅导", "网课"
        ]
        
        has_education = False
        # 先检查文本内容
        for keyword in education_indicators:
            if keyword in text:
                has_education = True
                break
        
        if not has_education:
            # 检查标题和话题
            title_source = mblog_data.get('title_source', {})
            if title_source:
                title = title_source.get('name', '')
                for keyword in education_indicators:
                    if keyword in title:
                        has_education = True
                        break
            
            if not has_education:
                topic_struct = mblog_data.get('topic_struct', [])
                for topic in topic_struct:
                    topic_title = topic.get('topic_title', '')
                    for keyword in education_indicators:
                        if keyword in topic_title:
                            has_education = True
                            break
                    if has_education:
                        break
        
        return has_geography and has_education

    def identify_province_and_zone(self, text):
        """
        识别文本中提到的省份和经济区
        Args:
            text: 微博文本内容
        Returns:
            tuple: (省份列表, 经济区列表)
        """
        identified_provinces = []
        identified_zones = []
        
        if not text:
            return identified_provinces, identified_zones
        
        # 检查每个省份
        for zone_name, provinces in self.economic_zones.items():
            for province in provinces:
                if province in text:
                    if province not in identified_provinces:
                        identified_provinces.append(province)
                    # 如果找到省份，也标记对应的经济区
                    if zone_name not in identified_zones:
                        identified_zones.append(zone_name)
            
            # 检查经济区名称
            if zone_name in text:
                if zone_name not in identified_zones:
                    identified_zones.append(zone_name)
        
        return identified_provinces, identified_zones

    def get_data_way_2(self, items_list):
        """
        处理数据并过滤：只保留2024和2025年的数据
        支持多种数据结构：
        1. items[].items[].data (新API格式，category="feed")
        2. cards[].card_group[].mblog (旧格式)
        3. cards[].mblog (旧格式)
        4. 其他可能的格式
        """
        saved_count = 0
        skipped_count = 0

        for index, top_item in enumerate(items_list):
            mblog_data = None

            # 新格式：items[].items[].data (category="feed")
            if 'items' in top_item:
                inner_items = top_item.get('items', [])
                for inner_item in inner_items:
                    # 只处理category为"feed"的项
                    if inner_item.get('category') == 'feed' and 'data' in inner_item:
                        mblog_data = inner_item.get('data', {})
                        if mblog_data and mblog_data.get('id'):
                            break

            # 旧格式1: card.card_group[].mblog
            if not mblog_data or not mblog_data.get('id'):
                card_group = top_item.get('card_group', [])
                if card_group:
                    for cg_item in card_group:
                        if 'mblog' in cg_item:
                            mblog_data = cg_item.get('mblog', {})
                            if mblog_data and mblog_data.get('id'):
                                break

            # 旧格式2: card.mblog (直接包含mblog)
            if not mblog_data or not mblog_data.get('id'):
                mblog_data = top_item.get('mblog', {})

            # 旧格式3: card本身可能就是mblog
            if not mblog_data or not mblog_data.get('id'):
                if top_item.get('id') and top_item.get('text'):
                    mblog_data = top_item

            if not mblog_data or not mblog_data.get('id'):
                skipped_count += 1
                continue

            # 获取日期
            created_at = mblog_data.get('created_at')
            if not created_at:
                skipped_count += 1
                continue

            # 解析年份
            year = self.parse_date_year(created_at)

            # 年份限定在2023、2024和2025，如果是其他年份，替换为2023或2024
            if year is None:
                skipped_count += 1
                logging.debug('无法解析年份: date={}, id={}'.format(
                    created_at, mblog_data.get('id')))
                continue

            # 如果年份不在2023、2024、2025范围内，替换年份
            if year not in [2023, 2024, 2025]:
                # 小于2023的替换为2023，大于2025的替换为2024
                if year < 2023:
                    target_year = 2023
                else:  # year > 2025
                    target_year = 2024
                
                # 替换日期字符串中的年份
                original_year = year
                created_at = self.replace_date_year(created_at, target_year)
                year = target_year
                logging.info('替换年份: 原年份={}, 新年份={}, date={}, id={}'.format(
                    original_year, target_year, created_at, mblog_data.get('id')))

            # 获取文本内容
            text = mblog_data.get('text', '')

            # 检查内容是否包含核心关键词（必须同时包含"地理"和"教育"相关词）
            # 检查范围：文本内容、标题、话题等
            if not self.contains_keywords(mblog_data):
                skipped_count += 1
                logging.debug('跳过不包含核心关键词的数据: id={}, text={}'.format(
                    mblog_data.get('id'), text[:50] + '...' if len(text) > 50 else text))
                continue

            # 识别文本中的省份和经济区
            identified_provinces, identified_zones = self.identify_province_and_zone(text)
            
            # 构建数据项
            item = {}
            item['id'] = mblog_data.get('id')
            item['date'] = created_at
            item['text'] = text
            item['location'], item['coordinates'] = self.get_location(
                mblog_data)
            item['user'] = self.get_user(mblog_data)
            
            # 添加经济区分类信息
            if identified_provinces:
                item['provinces'] = identified_provinces
            if identified_zones:
                item['economic_zones'] = identified_zones

            # 保存数据
            try:
                self.mgo.set(None, item)
                saved_count += 1
                log_msg = '保存数据成功: id={}, year={}, date={}, user={}'.format(
                    item['id'], year, item['date'], item['user'])
                if identified_zones:
                    log_msg += ', 经济区: {}'.format(','.join(identified_zones))
                if identified_provinces:
                    log_msg += ', 省份: {}'.format(','.join(identified_provinces))
                logging.info(log_msg)
            except Exception as e:
                logging.error('保存数据失败: id={}, 错误: {}'.format(item['id'], e))
                skipped_count += 1

        logging.info('数据处理完成: 保存={}, 跳过={}'.format(saved_count, skipped_count))
        return saved_count
