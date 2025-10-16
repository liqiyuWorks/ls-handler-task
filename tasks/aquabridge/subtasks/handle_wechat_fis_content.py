#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import re
from datetime import datetime
from pkg.public.models import BaseModel
from pkg.public.decorator import decorate
import pymongo


class HandleWechatFisContent(BaseModel):
    def __init__(self):
        config = {
            'collection': 'wechat_fis_ffa_content',
            'uniq_idx': [
                ('base_type', pymongo.ASCENDING),
                ('date', pymongo.ASCENDING)
            ]
        }
        super(HandleWechatFisContent, self).__init__(config)

    @decorate.exception_capture_close_datebase
    def run(self):
        # 从wechat_messages中获取今天的数据
        today = datetime.now().strftime('%Y-%m-%d')
        wechat_messages = self._query_today_messages(today)

        print(f"找到 {len(wechat_messages)} 条消息")
        for i, msg in enumerate(wechat_messages):
            # 如果内容中包含FIS相关关键词，则进行处理
            content = msg.get('content', '')
            
            if ('5TC' in content or '4TC' in content or '10TC' in content or 
                'Cape' in content or 'Pmx' in content or 'Smx' in content):
                print(f"处理消息 {i+1}: 包含FIS数据")
                # 解析并整理数据
                organized_data = self._process_fis_content(msg)
                
                # 保存整理后的数据
                if organized_data:
                    self._save_organized_data(organized_data)
                    print("数据保存完成")
                
                



    def _process_fis_content(self, msg):
        """处理包含FIS内容的消息"""
        content = msg.get('content', '')
        timestamp = msg.get('timestamp', '')
        
        # 解析内容中的表格数据
        parsed_data = self._parse_fis_table(content, timestamp)
        
        # 按价格类型整理数据
        organized_data = self._organize_data_by_price_type(parsed_data)
        
        return organized_data
    
    def _organize_data_by_price_type(self, parsed_data):
        """按价格类型整理数据，生成标准格式"""
        organized = {}
        
        for record in parsed_data:
            price_type = record['price_type']
            
            # 提取基础类型 (5TC, 4TC, 10TC)
            base_type = self._extract_base_type(price_type)
            
            if base_type not in organized:
                organized[base_type] = {
                    'base_type': base_type,
                    'date': record['date'],
                    'year': record['year'],
                    'month': record['month'],
                    'dataTime': record['dataTime'],
                    'created_at': record['created_at'],
                    'source': record['source'],
                    'price_records': []
                }
            
            # 添加价格记录，按照标准格式
            price_record = {
                'date': record['date'],
                'year': record['year'],
                'month': record['month'],
                'price_type': price_type,
                'price': record['price'],
                'futures_month': record['futures_month']
            }
            organized[base_type]['price_records'].append(price_record)
        
        # 按期货月份排序
        for base_type in organized:
            organized[base_type]['price_records'].sort(key=lambda x: x['futures_month'])
        
        return organized
    
    def _extract_base_type(self, price_type):
        """提取基础类型"""
        if '5TC' in price_type:
            return 'BFA-C5TC'
        elif '4TC' in price_type:
            return 'BFA-P4TC'
        elif '10TC' in price_type:
            return '10TC'
        else:
            return 'Unknown'
    
    def _save_organized_data(self, organized_data):
        """保存整理后的数据到MongoDB"""
        try:
            for base_type, data in organized_data.items():
                # 为每个基础类型保存一条完整记录
                record = {
                    'base_type': data['base_type'],
                    'date': data['date'],
                    'year': data['year'],
                    'month': data['month'],
                    'dataTime': data['dataTime'],
                    'created_at': data['created_at'],
                    'source': data['source'],
                    'price_count': len(data['price_records']),
                    'price_records': data['price_records']
                }
                
                # 保存到MongoDB，使用base_type和date作为唯一键
                key = {
                    'base_type': data['base_type'],
                    'date': data['date']
                }
                
                self.mgo.set(key, record)
                print(f"保存 {base_type} 数据: {len(data['price_records'])} 条价格记录")
                
        except Exception as e:
            print(f"保存整理后数据失败: {e}")
    
    
    def _parse_fis_table(self, content, timestamp):
        """解析FIS表格数据"""
        parsed_data = []
        
        # 提取日期信息
        date_info = self._extract_date_info(content, timestamp)
        
        # 查找包含价格数据的行
        lines = content.split('\n')
        current_section = None  # 跟踪当前处理的价格类型部分
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # 检测价格类型标题行 (如: Cape 5TC index 24,938)
            section_match = re.search(r'(Cape\s+5TC|Pmx\s+4TC|Smx\s+10TC)', line)
            if section_match:
                current_section = section_match.group(0).replace(' ', '_')
                continue
            
            # 匹配具体的价格行格式 (如: Oct25–BFA 25714 $/day)
            price_line_match = re.search(r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)(\d{2})–BFA\s+(\d{1,6}(?:,\d{3})*(?:\.\d+)?)', line)
            if price_line_match and current_section:
                month_name = price_line_match.group(1)
                price_str = price_line_match.group(3).replace(',', '')
                
                # 计算期货月份
                month_map = {
                    'Jan': 1, 'Feb': 2, 'Mar': 3, 'Apr': 4, 'May': 5, 'Jun': 6,
                    'Jul': 7, 'Aug': 8, 'Sep': 9, 'Oct': 10, 'Nov': 11, 'Dec': 12
                }
                futures_month = month_map.get(month_name, date_info['month'])
                
                # 计算相对月份偏移
                current_month = date_info['month']
                month_offset = self._calculate_month_offset(futures_month, current_month)
                
                # 生成标准化的价格类型
                price_type = self._generate_standard_price_type(current_section, month_offset)
                
                price = float(price_str)
                
                # 构建数据记录
                record = {
                    'date': date_info['date'],
                    'year': date_info['year'],
                    'month': date_info['month'],
                    'price_type': price_type,
                    'price': price,
                    'futures_month': futures_month,
                    'dataTime': timestamp,
                    'created_at': datetime.now(),
                    'source': 'wechat_message'
                }
                parsed_data.append(record)
        
        return parsed_data
    
    def _calculate_month_offset(self, futures_month, current_month):
        """计算期货月份相对于当前月份的偏移量"""
        if futures_month >= current_month:
            return futures_month - current_month
        else:
            # 跨年情况
            return (12 - current_month) + futures_month
    
    def _generate_standard_price_type(self, section, month_offset):
        """生成标准化的价格类型"""
        # 标准化价格类型前缀
        if 'Cape_5TC' in section:
            base_type = '5TC'
        elif 'Pmx_4TC' in section:
            base_type = '4TC'
        elif 'Smx_10TC' in section:
            base_type = '10TC'
        else:
            base_type = 'Unknown'
        
        # 生成月份后缀
        if month_offset == 0:
            month_suffix = 'CCURMON'
        else:
            month_suffix = f'C+{month_offset}MON'
        
        return f"{base_type}_{month_suffix}"
    
    
    def _extract_date_info(self, content, timestamp):
        """从消息内容中提取日期信息"""
        # 首先尝试从消息内容中提取日期
        date_from_content = self._extract_date_from_content(content)
        if date_from_content:
            return date_from_content
        
        # 如果内容中没有找到日期，使用时间戳
        try:
            dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            return {
                'date': dt.strftime('%Y/%m/%d'),
                'year': dt.year,
                'month': dt.month
            }
        except Exception:
            # 如果解析失败，使用当前日期
            now = datetime.now()
            return {
                'date': now.strftime('%Y/%m/%d'),
                'year': now.year,
                'month': now.month
            }
    
    def _extract_date_from_content(self, content):
        """从消息内容中提取日期信息"""
        # 匹配格式：Market closing 收盘小结：14/Oct
        date_match = re.search(r'Market closing 收盘小结：(\d{1,2})/(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)', content)
        if date_match:
            day = int(date_match.group(1))
            month_name = date_match.group(2)
            
            # 月份名称到数字的映射
            month_map = {
                'Jan': 1, 'Feb': 2, 'Mar': 3, 'Apr': 4, 'May': 5, 'Jun': 6,
                'Jul': 7, 'Aug': 8, 'Sep': 9, 'Oct': 10, 'Nov': 11, 'Dec': 12
            }
            month = month_map.get(month_name)
            
            if month:
                # 假设是当前年份
                current_year = datetime.now().year
                
                # 构建日期
                try:
                    date_obj = datetime(current_year, month, day)
                    return {
                        'date': date_obj.strftime('%Y/%m/%d'),
                        'year': date_obj.year,
                        'month': date_obj.month
                    }
                except ValueError:
                    # 如果日期无效（如2月30日），返回None
                    return None
        
        return None
    
    def _query_today_messages(self, today):
        """查询今天的消息"""
        db = self.mgo_client["aquabridge"]
        collection = db["wechat_messages"]

        # 使用正则表达式匹配日期部分（最优方式）
        return list(collection.find({
            'timestamp': {'$regex': f'^{today}'}
        }, limit=3))
