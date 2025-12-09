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
            "AUTHORIZATION", "WB-SUT _2A95EM5iQDeRxGeNI6VUU-CnJyjmIHXVlaKtYrDV6PUJbkdAbLVfGkWpNSJyouxsGtoPfn7F_HZQsWADJWGywazUA")
        self.X_SESSIONID = os.getenv("X_SESSIONID", "FB8B58EC-EF75-4E7B-8B3B-39FA9F3FD4C4")
        self.X_LOG_UID = os.getenv("X_LOG_UID", "5627587515")
        self.X_SHANHAI_PASS = os.getenv("X_SHANHAI_PASS", "3.DO5d_NHURFe8F1d5hYGAh4Ad3lc")
        self.X_VALIDATOR = os.getenv("X_VALIDATOR", "i2aluK9XPAyaavYbU1yxcVTYIVKhk8qlvE5FahsN27E=")
        self.GSID = os.getenv("GSID", "_2A25EM5iQDeRxGeNI6VUU-CnJyjmIHXVlaKtYrDV6PUJbkdAbLU_8kWpNSJyou3pblgVSLko_7QZyr3L3HW_B9UUi")
        
        # 更新请求头以匹配curl命令
        self.HEADER = {
            'Accept-Language': 'en-US,en',
            'X-Sessionid': self.X_SESSIONID,
            'SNRT': 'normal',
            'cronet_rid': '7557284',
            'x-shanhai-pass': self.X_SHANHAI_PASS,
            'User-Agent': 'Weibo/97034 (iPhone; iOS 26.1; Scale/3.00)',
            'Authorization': self.AUTHORIZATION,
            'X-Log-Uid': self.X_LOG_UID,
            'Content-Type': 'application/x-www-form-urlencoded; charset=utf-8',
            'Accept': '*/*',
            'Host': 'api.weibo.cn',
            'X-Validator': self.X_VALIDATOR,
            'x-engine-type': 'cronet-114.0.5735.246'
        }
        self.count = 10  # 默认每页10条，匹配curl命令
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
        super(WeiboSpider, self).__init__(config)
        print("init end ......")

    def parse_url(self, url_params, post_data):
        """
        发起POST请求
        url_params: URL查询参数字典
        post_data: POST请求的form数据字典
        """
        try:
            time.sleep(1)  # 避免请求过快
            
            # 构建完整的URL（包含查询参数）
            url = self.base_url + '?' + urllib.parse.urlencode(url_params)
            
            # 打印完整的URL和请求信息
            logging.info('=' * 80)
            logging.info('完整请求URL: {}'.format(url))
            logging.info('请求页码: {}, 搜索词: {}'.format(
                post_data.get('page', 'N/A'), post_data.get('containerid', '')[:100]))
            logging.info('=' * 80)
            
            # 调试：打印POST数据（前500字符）
            data_str = '&'.join(['{}={}'.format(k, str(v)[:50]) for k, v in post_data.items()])
            logging.debug('POST数据: {}'.format(data_str[:500]))
            
            # 发送POST请求
            # 注意：post_data中的值已经是URL编码的字符串
            # 但requests.post(data=dict)会自动对值进行URL编码
            # 所以我们需要先解码，再让requests编码，或者手动构建请求体
            # 这里我们手动构建请求体字符串，完全匹配curl命令的格式
            form_data_parts = []
            for k, v in post_data.items():
                # 值已经是URL编码的，直接使用
                form_data_parts.append('{}={}'.format(urllib.parse.quote(str(k), safe=''), str(v)))
            
            request_body = '&'.join(form_data_parts)
            
            res = requests.post(
                url,
                headers=self.HEADER,
                data=request_body,
                timeout=10
            )
            
            # 记录响应状态和部分内容（用于调试）
            logging.info('响应状态码: {}, 响应长度: {}'.format(
                res.status_code, len(res.text)))
            if res.status_code != 200:
                logging.warning('响应内容: {}'.format(res.text[:500]))
            
            return res
        except Exception as e:
            logging.error('请求失败, 报错信息: {}'.format(e))
            # 重试一次
            try:
                time.sleep(2)
                url = self.base_url + '?' + urllib.parse.urlencode(url_params)
                form_data_parts = []
                for k, v in post_data.items():
                    form_data_parts.append('{}={}'.format(urllib.parse.quote(str(k), safe=''), str(v)))
                request_body = '&'.join(form_data_parts)
                res = requests.post(
                    url,
                    headers=self.HEADER,
                    data=request_body,
                    timeout=10
                )
                return res
            except Exception as e2:
                logging.error('重试请求也失败: {}'.format(e2))
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
            
            # 只处理2024和2025年的数据
            if year not in [2024, 2025]:
                skipped_count += 1
                logging.debug('跳过非目标年份数据: year={}, date={}, id={}'.format(
                    year, created_at, mblog_data.get('id')))
                continue
            
            # 构建数据项
            item = {}
            item['id'] = mblog_data.get('id')
            item['date'] = created_at
            item['text'] = mblog_data.get('text', '')
            item['location'], item['coordinates'] = self.get_location(mblog_data)
            item['user'] = self.get_user(mblog_data)
            
            # 保存数据
            try:
                self.mgo.set(None, item)
                saved_count += 1
                logging.debug('保存数据成功: id={}, year={}, date={}, user={}'.format(
                    item['id'], year, item['date'], item['user']))
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
        # 构建flowId参数（格式：100103type=1&q=关键词&t=0，需要双重URL编码）
        flowid_str = '100103type={}&q={}&t=0'.format(search_type, word)
        flowid_encoded = urllib.parse.quote(flowid_str, safe='')
        flowid_double_encoded = urllib.parse.quote(flowid_encoded, safe='')
        
        # 构建URL查询参数
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
            'from': '10FC093010',
            'ft': '0',
            'gsid': self.GSID,
            'lang': 'zh_CN',
            'launchid': '10000365--x',
            'networktype': '5g',
            's': 'c9ea397b',
            'sflag': '1',
            'skin': 'default',
            'ua': 'iPhone18,1__weibo__15.12.0__iphone__os26.1',
            'v_f': '1',
            'v_p': '93',
            'wm': '3333_2001',
            'ul_sid': 'AB1C2BA6-278C-44C4-8185-DC0DFB847F94',
            'ul_hid': 'AD401B8C-CEF9-4E91-9ABF-165CCD3D9A32',
            'ul_ctime': str(int(time.time() * 1000))  # 当前时间戳（毫秒）
        }
        return url_params

    def build_post_data(self, word, search_type="1", page=1, max_id=0):
        """
        构建POST请求的form数据
        word: 搜索关键词
        search_type: 搜索类型，默认为"1"
        page: 页码，从1开始
        max_id: 最大ID，用于分页，默认为0
        """
        # 构建containerid和fid参数（格式：100103type=1&q=关键词&t=0）
        # 注意：这些值需要URL编码
        containerid_str = '100103type={}&q={}&t=0'.format(search_type, word)
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
            'blog_text_size': '16',
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
            'flowId': flowid_encoded,
            'flowVersion': '0.0.1',
            'flow_width': '402',
            'hot_feed_push': '0',
            'image_type': 'heif',
            'interval_weibo_count': '15',
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
            'source_t': '0',
            'stream_entry_id': '1',
            'sys_notify_open': '0',
            'taskType': 'loadMore',
            'topn_pos': '17',
            'transparent_background_height': '0',
            'uicode': '10000003',
            'unify_new_bubble_opt': '1',
        }
        
        # 添加用户信息（可选，可通过环境变量配置）
        user_avatar = os.getenv('USER_AVATAR', 'https://tvax1.sinaimg.cn/crop.0.0.1080.1080.180/0068QMAzly8i81lqbculij30u00u0wju.jpg?KID=imgbed,tva&Expires=1765283558&ssig=0XP%2B8hLNcx')
        user_nickname = os.getenv('USER_NICKNAME', '李琦玉Works')
        if user_avatar:
            post_data['user_avatar'] = urllib.parse.quote(user_avatar, safe='')
        if user_nickname:
            post_data['user_nickname'] = urllib.parse.quote(user_nickname, safe='')
        
        return post_data

    @decorate.exception_capture_close_datebase
    def run(self, task={}):
        for word in self.words_list:
            logging.info('搜索关键词: {}'.format(word))
            # 搜索类型，目前只使用"1"
            for search_type in ["1"]:  # 可以扩展: "61", "3", "62", "64", "63", "60", "38", "98", "92"
                logging.info('搜索类型: {}'.format(search_type))
                
                # 构建URL查询参数
                url_params = self.build_url_params(word, search_type)
                
                page = 1  # 从第1页开始
                max_id = 0  # 初始max_id为0
                max_pages = 100  # 最大页数限制
                
                while page <= max_pages:
                    logging.info('当前页码: {}, max_id: {}'.format(page, max_id))
                    
                    # 构建POST数据
                    post_data = self.build_post_data(word, search_type, page, max_id)
                    
                    try:
                        r = self.parse_url(url_params, post_data)
                    
                        if r.status_code == 200:
                            try:
                                response_json = json.loads(r.text)
                                
                                # 打印响应结构的所有顶级键
                                if isinstance(response_json, dict):
                                    logging.info('响应结构顶级键: {}'.format(list(response_json.keys())))
                                    # 记录响应结构（前2000字符，用于调试）
                                    logging.debug('API响应结构: {}'.format(
                                        json.dumps(response_json, ensure_ascii=False)[:2000]))
                                else:
                                    logging.warning('响应不是字典格式: {}'.format(type(response_json)))
                                
                                # 检查响应结构 - 尝试多种可能的数据字段
                                items_list = None
                                
                                # 方式1: 查找items字段（新API格式）
                                if 'items' in response_json:
                                    items_list = response_json.get('items', [])
                                    logging.info('找到items字段，items数量: {}'.format(len(items_list)))
                                # 方式2: 直接查找cards字段（旧格式）
                                elif 'cards' in response_json:
                                    items_list = response_json.get('cards', [])
                                    logging.info('找到cards字段，cards数量: {}'.format(len(items_list)))
                                # 方式3: 查找data.cards
                                elif 'data' in response_json and isinstance(response_json.get('data'), dict):
                                    data = response_json.get('data', {})
                                    if 'cards' in data:
                                        items_list = data.get('cards', [])
                                    elif 'statuses' in data:
                                        items_list = data.get('statuses', [])
                                # 方式4: 查找statuses字段
                                elif 'statuses' in response_json:
                                    items_list = response_json.get('statuses', [])
                                
                                if items_list is not None:
                                    total = len(items_list)
                                    logging.info('找到数据，该页数据条数: {}, 页码: {}'.format(total, page))
                                    
                                    if total > 0:
                                        # 处理数据
                                        processed_count = self.get_data_way_2(items_list)
                                        
                                        # 尝试获取下一页的max_id（从响应中提取）
                                        # 从最后一个item中提取id作为max_id
                                        if items_list and len(items_list) > 0:
                                            try:
                                                last_item = items_list[-1]
                                                # 新格式：从items[].items[].data中提取
                                                if 'items' in last_item:
                                                    inner_items = last_item.get('items', [])
                                                    for inner_item in inner_items:
                                                        if inner_item.get('category') == 'feed' and 'data' in inner_item:
                                                            data = inner_item.get('data', {})
                                                            if data and data.get('id'):
                                                                max_id = int(data.get('id'))
                                                                logging.info('更新max_id: {}'.format(max_id))
                                                                break
                                                # 旧格式：从mblog中提取
                                                elif 'mblog' in last_item:
                                                    mblog = last_item.get('mblog', {})
                                                    if mblog and mblog.get('id'):
                                                        max_id = int(mblog.get('id'))
                                                        logging.info('更新max_id: {}'.format(max_id))
                                                elif last_item.get('id'):
                                                    max_id = int(last_item.get('id'))
                                                    logging.info('更新max_id: {}'.format(max_id))
                                            except Exception as e:
                                                logging.debug('提取max_id失败: {}'.format(e))
                                                pass
                                        
                                        # 如果返回的数据少于count，可能已经是最后一页
                                        if total < self.count:
                                            logging.info('已到达最后一页（返回数据少于count）')
                                            break
                                    else:
                                        logging.info('没有更多数据，停止翻页')
                                        break
                                        
                                elif 'ok' in response_json:
                                    # 可能返回了错误信息
                                    ok_status = response_json.get('ok', 0)
                                    if ok_status != 1:
                                        error_msg = response_json.get('msg', '未知错误')
                                        logging.warning('API返回错误: ok={}, msg={}'.format(ok_status, error_msg))
                                        break
                                    else:
                                        # ok=1但没有cards字段，可能是其他格式
                                        logging.warning('响应格式异常: ok=1但没有cards字段，响应内容: {}'.format(
                                            json.dumps(response_json, ensure_ascii=False)[:500]))
                                        break
                                else:
                                    # 尝试打印完整的响应结构以便调试
                                    logging.warning('响应中没有找到items/cards/statuses字段')
                                    logging.warning('响应结构: {}'.format(
                                        json.dumps(response_json, ensure_ascii=False, indent=2)[:2000] if isinstance(response_json, dict) else r.text[:2000]))
                                    
                                    # 尝试查找其他可能包含数据的字段
                                    if isinstance(response_json, dict):
                                        for key in response_json.keys():
                                            value = response_json[key]
                                            if isinstance(value, list) and len(value) > 0:
                                                logging.info('发现列表字段 "{}"，长度: {}'.format(key, len(value)))
                                                # 检查第一个元素的结构
                                                if len(value) > 0:
                                                    logging.info('第一个元素结构: {}'.format(
                                                        json.dumps(value[0], ensure_ascii=False)[:500] if isinstance(value[0], dict) else str(value[0])[:500]))
                                    break
                                    
                            except json.JSONDecodeError as e:
                                logging.error('JSON解析失败: {}, 响应内容: {}'.format(e, r.text[:500]))
                                break
                            except Exception as e:
                                logging.error('处理响应时出错: {}, 响应内容: {}'.format(e, r.text[:500]))
                                break
                        elif r.status_code == 401:
                            logging.error('认证失败，请检查Authorization等认证信息')
                            break
                        elif r.status_code == 403:
                            logging.error('访问被拒绝，可能需要更新认证信息')
                            break
                        else:
                            logging.warning('请求返回状态码: {}, 响应内容: {}'.format(r.status_code, r.text[:200]))
                            break
                                
                    except Exception as e:
                        logging.error('处理请求时出错: {}'.format(e))
                        break
                    
                    page += 1
                    
                logging.info('关键词 "{}" 搜索完成'.format(word))

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
