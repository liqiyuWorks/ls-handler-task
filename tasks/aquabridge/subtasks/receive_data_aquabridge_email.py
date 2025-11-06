#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
阿里邮箱实时接收邮件脚本
支持通过IMAP实时监控新邮件并处理
"""

import imaplib
import email
from email import message
import time
import logging
import sys
import os
from email.header import decode_header
from email.utils import parsedate_to_datetime
from typing import Optional, Dict, Any, Callable, List
import ssl
import csv
import io
import pymongo
from datetime import datetime
from pkg.db.mongo import MgoStore

# 添加路径以导入BaseModel
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

from pkg.public.models import BaseModel


# 邮箱配置
EMAIL_CONFIG = {
    "server": "imap.mxhichina.com",  # 阿里企业邮箱IMAP服务器
    "port": 993,  # SSL端口
    "username": "data@aquabridge.ai",
    "password": "Aqua,88000",
    "mailbox": "INBOX",  # 监控的邮箱文件夹
}

# 日志配置
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
LOG_FILE = "./log/mail_realtime_receipt.log"


def setup_logger():
    """设置日志记录器"""
    mail_logger = logging.getLogger('MailRealtimeReceipt')
    mail_logger.setLevel(logging.INFO)
    
    # 避免重复添加处理器
    if mail_logger.handlers:
        return mail_logger
    
    formatter = logging.Formatter(LOG_FORMAT)
    
    # 控制台处理器
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    mail_logger.addHandler(console_handler)
    
    # 文件处理器
    import os
    log_dir = os.path.dirname(LOG_FILE)
    if log_dir and not os.path.exists(log_dir):
        os.makedirs(log_dir, exist_ok=True)
    
    file_handler = logging.FileHandler(LOG_FILE, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    mail_logger.addHandler(file_handler)
    
    return mail_logger


logger = setup_logger()


class MailReceiver:
    """邮件实时接收器"""
    
    def __init__(self, config: Dict[str, Any], mgo: Optional[MgoStore] = None):
        """
        初始化邮件接收器
        
        Args:
            config: 邮箱配置字典
            mgo: MongoDB存储对象（可选，用于保存数据）
        """
        self.config = config
        self.mgo = mgo
        self.imap: Optional[imaplib.IMAP4_SSL] = None
        self.last_uid = None
        self.is_connected = False
        self._processed_uids = set()  # 已处理的邮件UID集合
        
    def connect(self) -> bool:
        """
        连接到IMAP服务器
        
        Returns:
            bool: 连接是否成功
        """
        try:
            # 创建SSL上下文
            context = ssl.create_default_context()
            
            # 连接到IMAP服务器
            self.imap = imaplib.IMAP4_SSL(
                self.config['server'],
                self.config['port'],
                ssl_context=context
            )
            
            # 登录
            self.imap.login(self.config['username'], self.config['password'])
            
            # 选择邮箱文件夹
            status, messages = self.imap.select(self.config['mailbox'])
            if status != 'OK':
                logger.error("无法选择邮箱文件夹: %s", self.config['mailbox'])
                return False
            
            # 获取当前邮箱中的最后一条邮件UID
            status, messages = self.imap.search(None, 'ALL')
            if status == 'OK' and messages[0]:
                uids = messages[0].split()
                if uids:
                    self.last_uid = uids[-1].decode('utf-8')
            
            self.is_connected = True
            return True
            
        except imaplib.IMAP4.error as e:
            logger.error(f"IMAP连接错误: {str(e)}")
            self.is_connected = False
            return False
        except Exception as e:
            logger.error(f"连接邮箱失败: {str(e)}")
            self.is_connected = False
            return False
    
    def disconnect(self):
        """断开IMAP连接"""
        if self.imap:
            try:
                self.imap.close()
                self.imap.logout()
            except Exception as e:
                logger.debug("断开连接时出错: %s", str(e))
            finally:
                self.imap = None
                self.is_connected = False
    
    def decode_mime_words(self, s: str) -> str:
        """
        解码MIME编码的字符串
        
        Args:
            s: 待解码的字符串
            
        Returns:
            str: 解码后的字符串
        """
        decoded_parts = decode_header(s)
        decoded_str = ''
        for part, encoding in decoded_parts:
            if isinstance(part, bytes):
                try:
                    decoded_str += part.decode(encoding or 'utf-8', errors='ignore')
                except:
                    decoded_str += part.decode('utf-8', errors='ignore')
            else:
                decoded_str += part
        return decoded_str
    
    def parse_email(self, msg_data: bytes) -> Dict[str, Any]:
        """
        解析邮件内容
        
        Args:
            msg_data: 邮件原始数据
            
        Returns:
            Dict: 解析后的邮件信息
        """
        try:
            msg = email.message_from_bytes(msg_data)
            
            # 获取邮件基本信息
            subject = self.decode_mime_words(msg.get('Subject', ''))
            from_addr = self.decode_mime_words(msg.get('From', ''))
            to_addr = self.decode_mime_words(msg.get('To', ''))
            date_str = msg.get('Date', '')
            
            # 解析日期
            date_obj = None
            if date_str:
                try:
                    date_obj = parsedate_to_datetime(date_str)
                except:
                    pass
            
            # 获取邮件正文
            body = self._get_email_body(msg)
            
            # 获取附件信息（包括数据）
            attachments = self._get_attachments(msg, read_data=True)
            
            email_info = {
                'subject': subject,
                'from': from_addr,
                'to': to_addr,
                'date': date_obj.isoformat() if date_obj else date_str,
                'body': body,
                'attachments': attachments,
            }
            
            return email_info
            
        except Exception as e:
            logger.error(f"解析邮件失败: {str(e)}")
            return {}
    
    def _get_email_body(self, msg: message.Message) -> str:
        """
        获取邮件正文内容
        
        Args:
            msg: 邮件消息对象
            
        Returns:
            str: 邮件正文
        """
        body = ""
        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                content_disposition = str(part.get("Content-Disposition"))
                
                # 跳过附件
                if "attachment" in content_disposition:
                    continue
                
                # 获取文本内容
                if content_type in ["text/plain", "text/html"]:
                    try:
                        charset = part.get_content_charset() or 'utf-8'
                        payload = part.get_payload(decode=True)
                        if payload:
                            body += payload.decode(charset, errors='ignore')
                    except Exception as e:
                        logger.warning(f"解码邮件正文失败: {str(e)}")
        else:
            # 单部分邮件
            try:
                charset = msg.get_content_charset() or 'utf-8'
                payload = msg.get_payload(decode=True)
                if payload:
                    body = payload.decode(charset, errors='ignore')
            except Exception as e:
                logger.warning(f"解码邮件正文失败: {str(e)}")
        
        return body
    
    def _get_attachments(self, msg: message.Message, read_data: bool = False) -> list:
        """
        获取附件信息
        
        Args:
            msg: 邮件消息对象
            read_data: 是否读取附件数据，默认False（只读取元信息）
            
        Returns:
            list: 附件信息列表，每个附件包含:
                - filename: 文件名
                - content_type: 内容类型
                - size: 文件大小（字节）
                - data: 附件二进制数据（如果read_data=True）
                - text: 附件文本内容（如果是文本文件且read_data=True）
                - csv_data: CSV解析后的数据（如果是CSV文件且read_data=True）
        """
        attachments = []
        if msg.is_multipart():
            for part in msg.walk():
                content_disposition = str(part.get("Content-Disposition"))
                if "attachment" in content_disposition:
                    filename = part.get_filename()
                    if filename:
                        filename = self.decode_mime_words(filename)
                        attachment_info = {
                            'filename': filename,
                            'content_type': part.get_content_type(),
                            'size': len(part.get_payload(decode=True) or b'')
                        }
                        
                        # 如果需要读取附件数据
                        if read_data:
                            try:
                                # 获取附件二进制数据
                                payload = part.get_payload(decode=True)
                                if payload:
                                    attachment_info['data'] = payload
                                    
                                    # 如果是文本类型，尝试解码为文本
                                    content_type = part.get_content_type()
                                    if content_type.startswith('text/') or 'csv' in filename.lower():
                                        try:
                                            # 尝试获取字符集
                                            charset = part.get_content_charset() or 'utf-8'
                                            text_content = payload.decode(charset, errors='ignore')
                                            attachment_info['text'] = text_content
                                            
                                            # 如果是CSV文件，尝试解析
                                            if filename.lower().endswith('.csv'):
                                                csv_data = self._parse_csv(text_content)
                                                attachment_info['csv_data'] = csv_data
                                                
                                                # 1、如果是Baltic Exchange文件，进行专门的结构化解析
                                                if self._is_baltic_exchange_file(filename):
                                                    structured_data = self._parse_baltic_exchange(csv_text=text_content, csv_data=csv_data)
                                                    # 如果有MongoDB连接，保存数据
                                                    if self.mgo:
                                                        for index in structured_data["indices"]:
                                                            # 解析日期字符串（格式如 "05-Nov-2025"）并格式化为 "2025-11-05"
                                                            date_str = str(index.get("date", "")).strip()
                                                            if date_str:
                                                                try:
                                                                    # 尝试解析日期字符串（支持多种格式）
                                                                    date_obj = None
                                                                    # 尝试常见格式: "05-Nov-2025", "5-Nov-2025", "05-November-2025" 等
                                                                    date_formats = [
                                                                        "%d-%b-%Y",      # 05-Nov-2025
                                                                        "%d-%B-%Y",      # 05-November-2025
                                                                        "%Y-%m-%d",      # 2025-11-05 (如果已经是标准格式)
                                                                        "%Y/%m/%d",      # 2025/11/05
                                                                        "%d/%m/%Y",      # 05/11/2025
                                                                    ]
                                                                    
                                                                    for fmt in date_formats:
                                                                        try:
                                                                            date_obj = datetime.strptime(date_str, fmt)
                                                                            break
                                                                        except ValueError:
                                                                            continue
                                                                    
                                                                    # 如果标准格式都失败，尝试使用 parsedate_to_datetime（更灵活）
                                                                    if not date_obj:
                                                                        try:
                                                                            date_obj = parsedate_to_datetime(date_str)
                                                                        except (ValueError, TypeError):
                                                                            pass
                                                                    
                                                                    if date_obj:
                                                                        # 格式化为标准日期格式
                                                                        formatted_date = date_obj.strftime("%Y-%m-%d")
                                                                        index["date"] = formatted_date
                                                                        # 保存到MongoDB，以日期为查询条件（使用字典格式）
                                                                        self.mgo.set({"date": formatted_date}, index)
                                                                    else:
                                                                        logger.warning("无法解析日期格式: %s", date_str)
                                                                except Exception as e:
                                                                    logger.warning("日期解析失败: %s, 错误: %s", date_str, str(e))
                                                    attachment_info['structured_data'] = structured_data
                                                
                                                logger.debug("成功解析CSV附件: %s, 行数: %d", filename, len(csv_data))
                                        except Exception as e:
                                            logger.warning(f"解码附件文本失败 {filename}: {str(e)}")
                                    
                            except Exception as e:
                                logger.warning(f"读取附件数据失败 {filename}: {str(e)}")
                        
                        attachments.append(attachment_info)
        return attachments
    
    def _parse_csv(self, csv_text: str) -> List[Dict[str, Any]]:
        """
        解析CSV文本内容
        
        Args:
            csv_text: CSV文本内容
            
        Returns:
            List[Dict]: CSV数据列表，每行作为字典
        """
        csv_data = []
        try:
            # 使用StringIO来读取CSV文本
            csv_file = io.StringIO(csv_text)
            
            # 尝试检测分隔符（常见的有逗号、分号、制表符）
            first_line = csv_text.split('\n')[0] if csv_text else ''
            delimiter = ','
            if ';' in first_line and first_line.count(';') > first_line.count(','):
                delimiter = ';'
            elif '\t' in first_line:
                delimiter = '\t'
            
            # 尝试检测编码（处理BOM）
            if csv_text.startswith('\ufeff'):
                csv_file = io.StringIO(csv_text.lstrip('\ufeff'))
            
            # 读取CSV
            reader = csv.DictReader(csv_file, delimiter=delimiter)
            
            for row in reader:
                csv_data.append(row)
                
        except Exception as e:
            logger.warning(f"解析CSV失败: {str(e)}")
            # 如果DictReader失败，尝试按行读取
            try:
                lines = csv_text.strip().split('\n')
                if lines:
                    # 第一行作为表头
                    headers = [h.strip() for h in lines[0].split(delimiter)]
                    for line in lines[1:]:
                        if line.strip():
                            values = [v.strip() for v in line.split(delimiter)]
                            row = dict(zip(headers, values))
                            csv_data.append(row)
            except Exception as e2:
                logger.error(f"备选CSV解析方法也失败: {str(e2)}")
        
        return csv_data
    
    def _is_baltic_exchange_file(self, filename: str) -> bool:
        """
        判断是否是Baltic Exchange历史数据文件
        
        Args:
            filename: 文件名
            
        Returns:
            bool: 是否是Baltic Exchange文件
        """
        filename_lower = filename.lower()
        return 'baltic exchange index' in filename_lower and 'historic data' in filename_lower
    
    def _parse_baltic_exchange(self, csv_text: str, csv_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        解析Baltic Exchange历史数据文件，转换为结构化数据
        
        Args:
            csv_text: CSV原始文本
            csv_data: 已解析的CSV数据
            
        Returns:
            Dict: 结构化数据，包含：
                - metadata: 元数据（日期范围等）
                - indices: 指数数据列表
                - summary: 摘要信息
        """
        structured = {
            'metadata': {},
            'indices': [],
            'summary': {}
        }
        
        try:
            # 解析数据结构
            if csv_data:
                # 获取所有列名
                headers = list(csv_data[0].keys()) if csv_data and csv_data[0] else []
                
                # 查找日期列和数值列
                date_column = None
                value_columns = []
                
                
                # 如果没有找到明确的日期列，使用第一列
                if not date_column and headers:
                    date_column = headers[0]
                
                # 如果没有找到数值列，使用除日期列外的其他列
                if not value_columns:
                    value_columns = [h for h in headers if h != date_column]
                
                # 构建结构化数据
                indices = []
                for row in csv_data:
                    index_entry = {
                        'date': row.get(date_column, '') if date_column else '',
                    }
                    
                    # 添加所有数值列
                    for col in value_columns:
                        if col in row:
                            value_str = str(row[col]).strip()
                            # 尝试转换为数字
                            try:
                                if '.' in value_str:
                                    index_entry[col] = float(value_str)
                                else:
                                    index_entry[col] = int(value_str)
                            except (ValueError, TypeError):
                                index_entry[col] = value_str
                    
                    indices.append(index_entry)
                
                structured['indices'] = indices
                
                # 添加列信息
                structured['metadata']['columns'] = {
                    'date_column': date_column,
                    'value_columns': value_columns,
                    'all_columns': headers
                }
        
        except Exception as e:
            logger.warning(f"解析Baltic Exchange结构化数据失败: {str(e)}")
            structured['error'] = str(e)
        
        return structured
    
    def list_emails(self, limit: int = 20, start_from: int = 0) -> list:
        """
        列出收件箱中的邮件列表
        
        Args:
            limit: 返回的邮件数量限制，默认20
            start_from: 起始位置，默认0（从最新的开始）
            
        Returns:
            list: 邮件信息列表，每个元素包含基本信息（uid, subject, from, date等）
        """
        if not self.is_connected:
            logger.warning("未连接到邮箱服务器，无法列出邮件")
            return []
        
        emails_list = []
        try:
            # 重新选择邮箱以确保同步
            self.imap.select(self.config['mailbox'])
            
            # 搜索所有邮件
            status, messages = self.imap.search(None, 'ALL')
            
            if status != 'OK':
                logger.warning("搜索邮件失败")
                return []
            
            if not messages[0]:
                logger.info("收件箱为空")
                return []
            
            uids = messages[0].split()
            
            # 反转列表，从最新的开始
            uids = list(reversed(uids))
            
            # 计算实际要获取的范围
            total_count = len(uids)
            end_pos = min(start_from + limit, total_count)
            target_uids = uids[start_from:end_pos]
            
            logger.info(f"收件箱共有 {total_count} 封邮件，显示第 {start_from + 1} 到 {end_pos} 封")
            
            # 获取邮件的基本信息
            for uid in target_uids:
                try:
                    uid_str = uid.decode('utf-8')
                    
                    # 获取邮件头信息（只获取头部，不获取正文，速度更快）
                    status, email_data = self.imap.fetch(uid_str, '(RFC822.HEADER)')
                    
                    if status != 'OK' or not email_data:
                        continue
                    
                    headers = email_data[0][1]
                    msg = email.message_from_bytes(headers)
                    
                    subject = self.decode_mime_words(msg.get('Subject', ''))
                    from_addr = self.decode_mime_words(msg.get('From', ''))
                    to_addr = self.decode_mime_words(msg.get('To', ''))
                    date_str = msg.get('Date', '')
                    
                    # 解析日期
                    date_obj = None
                    if date_str:
                        try:
                            date_obj = parsedate_to_datetime(date_str)
                        except:
                            pass
                    
                    email_info = {
                        'uid': uid_str,
                        'subject': subject or '(无主题)',
                        'from': from_addr or '(未知)',
                        'to': to_addr or '(未知)',
                        'date': date_obj.isoformat() if date_obj else date_str,
                    }
                    emails_list.append(email_info)
                    
                except Exception as e:
                    logger.warning(f"解析邮件 {uid.decode('utf-8')} 失败: {str(e)}")
                    continue
            
        except imaplib.IMAP4.error as e:
            logger.error(f"列出邮件时IMAP错误: {str(e)}")
            self.is_connected = False
        except Exception as e:
            logger.error(f"列出邮件时出错: {str(e)}")
        
        return emails_list
    
    def search_emails(self, sender: Optional[str] = None, subject: Optional[str] = None, 
                     limit: int = 20, search_recent: int = 100) -> list:
        """
        搜索收件箱中的邮件
        
        Args:
            sender: 发件人关键词（模糊匹配，可选）
            subject: 主题关键词（模糊匹配，可选）
            limit: 返回的结果数量限制，默认20
            search_recent: 在最近多少封邮件中搜索，默认100
            
        Returns:
            list: 匹配的邮件信息列表
        """
        if not self.is_connected:
            logger.warning("未连接到邮箱服务器，无法搜索邮件")
            return []
        
        emails_list = []
        try:
            # 重新选择邮箱以确保同步
            self.imap.select(self.config['mailbox'])
            
            # 搜索所有邮件
            status, messages = self.imap.search(None, 'ALL')
            
            if status != 'OK':
                logger.warning("搜索邮件失败")
                return []
            
            if not messages[0]:
                logger.info("收件箱为空")
                return []
            
            uids = messages[0].split()
            
            # 反转列表，从最新的开始，只搜索最近的邮件
            uids = list(reversed(uids))[:search_recent]
            
            matched_count = 0
            
            # 获取邮件的基本信息并进行过滤
            for uid in uids:
                if matched_count >= limit:
                    break
                    
                try:
                    uid_str = uid.decode('utf-8')
                    
                    # 获取邮件头信息
                    status, email_data = self.imap.fetch(uid_str, '(RFC822.HEADER)')
                    
                    if status != 'OK' or not email_data:
                        continue
                    
                    headers = email_data[0][1]
                    msg = email.message_from_bytes(headers)
                    
                    subject_text = self.decode_mime_words(msg.get('Subject', ''))
                    from_addr = self.decode_mime_words(msg.get('From', ''))
                    to_addr = self.decode_mime_words(msg.get('To', ''))
                    date_str = msg.get('Date', '')
                    
                    # 匹配条件
                    match = True
                    
                    # 按发件人过滤
                    if sender:
                        sender_lower = sender.lower()
                        from_lower = from_addr.lower() if from_addr else ''
                        if sender_lower not in from_lower:
                            match = False
                    
                    # 按主题过滤
                    if subject and match:
                        subject_lower = subject.lower()
                        subject_text_lower = subject_text.lower() if subject_text else ''
                        if subject_lower not in subject_text_lower:
                            match = False
                    
                    if not match:
                        continue
                    
                    # 解析日期
                    date_obj = None
                    if date_str:
                        try:
                            date_obj = parsedate_to_datetime(date_str)
                        except:
                            pass
                    
                    email_info = {
                        'uid': uid_str,
                        'subject': subject_text or '(无主题)',
                        'from': from_addr or '(未知)',
                        'to': to_addr or '(未知)',
                        'date': date_obj.isoformat() if date_obj else date_str,
                    }
                    emails_list.append(email_info)
                    matched_count += 1
                    
                except Exception as e:
                    logger.warning("解析邮件失败: %s", str(e))
                    continue
            
        except imaplib.IMAP4.error as e:
            logger.error(f"搜索邮件时IMAP错误: {str(e)}")
            self.is_connected = False
        except Exception as e:
            logger.error(f"搜索邮件时出错: {str(e)}")
        
        return emails_list
    
    def get_email_content(self, uid: str) -> Optional[Dict[str, Any]]:
        """
        获取指定UID邮件的完整内容（包括正文和附件信息）
        
        Args:
            uid: 邮件UID
            
        Returns:
            Dict: 完整的邮件信息，包含subject, from, to, date, body, attachments等
        """
        if not self.is_connected:
            logger.warning("未连接到邮箱服务器，无法获取邮件内容")
            return None
        
        try:
            # 重新选择邮箱以确保同步
            self.imap.select(self.config['mailbox'])
            
            # 获取邮件完整内容
            status, msg_data = self.imap.fetch(uid, '(RFC822)')
            
            if status != 'OK' or not msg_data:
                logger.warning(f"无法获取邮件 {uid} 的内容")
                return None
            
            # 解析邮件
            email_info = self.parse_email(msg_data[0][1])
            if email_info:
                email_info['uid'] = uid
                return email_info
            
        except imaplib.IMAP4.error as e:
            logger.error(f"获取邮件内容时IMAP错误: {str(e)}")
            self.is_connected = False
        except Exception as e:
            logger.error(f"获取邮件内容时出错: {str(e)}")
        
        return None
    
    def get_new_emails(self) -> list:
        """
        获取新邮件
        
        Returns:
            list: 新邮件列表
        """
        if not self.is_connected:
            return []
        
        new_emails = []
        try:
            # 重新选择邮箱以确保同步
            self.imap.select(self.config['mailbox'])
            
            # 搜索新邮件（UID大于last_uid的邮件）
            if self.last_uid:
                search_criteria = f'UID {int(self.last_uid) + 1}:*'
            else:
                search_criteria = 'ALL'
            
            status, messages = self.imap.search(None, search_criteria)
            
            if status != 'OK':
                logger.warning("搜索邮件失败")
                return []
            
            if not messages[0]:
                return []
            
            uids = messages[0].split()
            
            # 过滤已处理的邮件
            new_uids = [uid for uid in uids if uid.decode('utf-8') not in self._processed_uids]
            
            for uid in new_uids:
                uid_str = uid.decode('utf-8')
                
                # 获取邮件
                status, msg_data = self.imap.fetch(uid, '(RFC822)')
                
                if status != 'OK' or not msg_data:
                    continue
                
                # 解析邮件
                email_info = self.parse_email(msg_data[0][1])
                if email_info:
                    email_info['uid'] = uid_str
                    new_emails.append(email_info)
                    self._processed_uids.add(uid_str)
                    logger.info(f"收到新邮件 - UID: {uid_str}, 主题: {email_info.get('subject', 'N/A')}")
            
            # 更新最后处理的UID
            if uids:
                self.last_uid = uids[-1].decode('utf-8')
                
        except imaplib.IMAP4.error as e:
            logger.error(f"获取新邮件时IMAP错误: {str(e)}")
            # 标记连接断开
            self.is_connected = False
        except (OSError, ConnectionError, ssl.SSLError) as e:
            logger.error(f"获取新邮件时连接错误: {str(e)}")
            # 标记连接断开
            self.is_connected = False
        except Exception as e:
            error_msg = str(e).lower()
            # 检查是否是连接相关的错误
            if any(keyword in error_msg for keyword in ['closed', 'connection', 'eof', 'socket', 'ssl']):
                logger.error(f"获取新邮件时连接断开: {str(e)}")
                self.is_connected = False
            else:
                logger.error(f"获取新邮件时出错: {str(e)}")
        
        return new_emails
    
    def monitor(self, callback: Optional[Callable[[Dict[str, Any]], None]] = None, 
                poll_interval: int = 10, use_idle: bool = False):
        """
        实时监控新邮件
        
        Args:
            callback: 新邮件回调函数，接收邮件信息字典作为参数
            poll_interval: 轮询间隔（秒），默认10秒
            use_idle: 是否尝试使用IDLE模式，默认False（因为SSL连接可能有问题）
        """
        if not self.is_connected:
            logger.error("未连接到邮箱服务器，无法开始监控")
            return
        
        logger.info(f"开始监控新邮件，轮询间隔: {poll_interval}秒")
        
        try:
            # 尝试使用IDLE模式（如果支持且启用）
            if use_idle:
                try:
                    logger.info("尝试使用IDLE模式实时监控...")
                    self._monitor_with_idle(callback)
                except Exception as e:
                    logger.warning(f"IDLE模式不可用，切换到轮询模式: {str(e)}")
                    # IDLE失败可能导致连接断开，需要重新连接
                    if not self.is_connected:
                        logger.info("连接已断开，正在重新连接...")
                        self.disconnect()
                        if not self.connect():
                            logger.error("重新连接失败，程序退出")
                            return
                    self._monitor_with_polling(callback, poll_interval)
            else:
                # 直接使用轮询模式
                logger.info("使用轮询模式监控新邮件")
                self._monitor_with_polling(callback, poll_interval)
        except KeyboardInterrupt:
            logger.info("收到停止信号，正在退出...")
        except Exception as e:
            logger.error(f"监控过程中出错: {str(e)}")
        finally:
            self.disconnect()
    
    def _monitor_with_idle(self, callback: Optional[Callable[[Dict[str, Any]], None]] = None):
        """
        使用IDLE模式监控新邮件（需要IMAP服务器支持）
        
        Args:
            callback: 新邮件回调函数
        """
        # 检查是否支持IDLE
        capabilities = self.imap.capability()
        if b'IDLE' not in capabilities[1][0]:
            raise Exception("IMAP服务器不支持IDLE命令")
        
        logger.info("使用IDLE模式监控新邮件")
        
        while True:
            try:
                # 发送IDLE命令
                self.imap.send(b'IDLE\r\n')
                response = self.imap.readline()
                
                if response.startswith(b'+'):
                    logger.debug("进入IDLE模式，等待新邮件...")
                    
                    # 等待新邮件通知
                    while True:
                        response = self.imap.readline()
                        
                        if b'EXISTS' in response:
                            logger.debug(f"收到新邮件通知: {response.decode('utf-8', errors='ignore')}")
                            # 退出IDLE模式
                            self.imap.send(b'DONE\r\n')
                            self.imap.readline()
                            break
                        
                        # 检查是否需要退出
                        if not response:
                            time.sleep(1)
                            continue
                    
                    # 处理新邮件
                    new_emails = self.get_new_emails()
                    for email_info in new_emails:
                        if callback:
                            try:
                                callback(email_info)
                            except Exception as e:
                                logger.error(f"回调函数执行失败: {str(e)}")
                        else:
                            self._default_email_handler(email_info)
                
            except KeyboardInterrupt:
                # 退出IDLE模式
                try:
                    self.imap.send(b'DONE\r\n')
                    self.imap.readline()
                except:
                    pass
                raise
            except Exception as e:
                logger.error(f"IDLE模式出错: {str(e)}")
                logger.info("切换到轮询模式...")
                raise
    
    def _monitor_with_polling(self, callback: Optional[Callable[[Dict[str, Any]], None]] = None,
                              poll_interval: int = 10):
        """
        使用轮询模式监控新邮件
        
        Args:
            callback: 新邮件回调函数
            poll_interval: 轮询间隔（秒）
        """
        logger.info(f"使用轮询模式监控新邮件，间隔: {poll_interval}秒")
        
        consecutive_errors = 0
        max_consecutive_errors = 5
        
        while True:
            try:
                # 检查连接状态，如果断开则重连
                if not self.is_connected:
                    logger.warning("连接已断开，正在重新连接...")
                    self.disconnect()
                    if not self.connect():
                        consecutive_errors += 1
                        if consecutive_errors >= max_consecutive_errors:
                            logger.error("连续重连失败，程序退出")
                            return
                        logger.warning(f"重连失败，等待 {poll_interval} 秒后重试 ({consecutive_errors}/{max_consecutive_errors})...")
                        time.sleep(poll_interval)
                        continue
                    else:
                        consecutive_errors = 0
                        logger.info("重新连接成功")
                
                # 检查新邮件
                new_emails = self.get_new_emails()
                
                # 如果获取邮件后连接断开，在下次循环中会自动重连
                if not self.is_connected:
                    continue
                
                if new_emails:
                    logger.info(f"检测到 {len(new_emails)} 封新邮件")
                    for email_info in new_emails:
                        if callback:
                            try:
                                callback(email_info)
                            except Exception as e:
                                logger.error(f"回调函数执行失败: {str(e)}")
                        else:
                            self._default_email_handler(email_info)
                
                # 重置错误计数
                consecutive_errors = 0
                
                # 等待下次轮询
                time.sleep(poll_interval)
                
            except KeyboardInterrupt:
                raise
            except Exception as e:
                consecutive_errors += 1
                logger.error(f"轮询过程中出错: {str(e)}")
                
                if consecutive_errors >= max_consecutive_errors:
                    logger.error(f"连续 {max_consecutive_errors} 次错误，程序退出")
                    return
                
                # 标记连接可能断开
                error_msg = str(e).lower()
                if any(keyword in error_msg for keyword in ['closed', 'connection', 'eof', 'socket', 'ssl']):
                    self.is_connected = False
                
                logger.info(f"等待 {poll_interval} 秒后重试 ({consecutive_errors}/{max_consecutive_errors})...")
                time.sleep(poll_interval)


    def _print_baltic_exchange_data(self, filename: str, structured_data: Dict[str, Any]):
        """
        打印Baltic Exchange结构化数据
        
        Args:
            filename: 文件名
            structured_data: 结构化数据字典
        """
        logger.info(f"  📊 Baltic Exchange文件: {filename}")
        
        # 显示元数据
        metadata = structured_data.get('metadata', {})
        if 'date_range' in metadata:
            date_range = metadata['date_range']
            logger.info(f"     日期范围: {date_range.get('start', 'N/A')} 至 {date_range.get('end', 'N/A')}")
            logger.info(f"     数据天数: {date_range.get('total_days', 0)}")
        
        # 显示列信息
        if 'columns' in metadata:
            cols = metadata['columns']
            logger.info(f"     日期列: {cols.get('date_column', 'N/A')}")
            logger.info(f"     数值列: {', '.join(cols.get('value_columns', [])[:5])}{'...' if len(cols.get('value_columns', [])) > 5 else ''}")
        
        # 显示摘要统计
        summary = structured_data.get('summary', {})
        if summary:
            logger.info(f"     统计摘要:")
            for col_name, stats in list(summary.items())[:3]:  # 最多显示3个列的统计
                logger.info(f"       {col_name}:")
                logger.info(f"         数量: {stats.get('count', 0)} | 最小: {stats.get('min', 'N/A')} | 最大: {stats.get('max', 'N/A')} | 平均: {stats.get('avg', 0):.2f}")
        
        # 显示前几条数据
        indices = structured_data.get('indices', [])
        if indices:
            preview_count = min(3, len(indices))
            logger.info(f"     数据预览 ({preview_count}/{len(indices)} 条):")
            for i, idx in enumerate(indices[:preview_count], 1):
                idx_str = ' | '.join([f"{k}: {v}" for k, v in idx.items()][:5])
                logger.info(f"       [{i}] {idx_str}")
            if len(indices) > preview_count:
                logger.info(f"       ... (还有 {len(indices) - preview_count} 条)")
    
    def _default_email_handler(self, email_info: Dict[str, Any]):
        """
        默认邮件处理函数 - 仅显示附件数据
        
        Args:
            email_info: 邮件信息字典
        """
        attachments = email_info.get('attachments', [])
        if not attachments:
            logger.info(f"邮件 [{email_info.get('subject', 'N/A')}] - 无附件")
            return
        
        logger.info(f"邮件: {email_info.get('subject', 'N/A')} | 附件数: {len(attachments)}")
        
        for idx, att in enumerate(attachments, 1):
            filename = att.get('filename', 'N/A')
            
            # 优先显示Baltic Exchange结构化数据
            if 'structured_data' in att and att['structured_data']:
                # self._print_baltic_exchange_data(filename, att['structured_data'])
                print(att['structured_data'])
            # 显示CSV数据
            elif 'csv_data' in att and att['csv_data']:
                csv_data = att['csv_data']
                headers = list(csv_data[0].keys()) if csv_data and csv_data[0] else []
                logger.info(f"  [{idx}] {filename} | {len(csv_data)}行 | {len(headers)}列")
                logger.info(f"      列: {', '.join(headers[:8])}{'...' if len(headers) > 8 else ''}")
            else:
                size = att.get('size', 0)
                logger.info(f"  [{idx}] {filename} | {size} bytes")


def print_email_list(emails: list):
    """
    格式化打印邮件列表（简约版）
    
    Args:
        emails: 邮件信息列表
    """
    if not emails:
        logger.info("未找到匹配邮件")
        return
    
    logger.info("找到 %d 封匹配邮件:", len(emails))
    for idx, email_info in enumerate(emails, 1):
        subject = email_info.get('subject', 'N/A')
        date = email_info.get('date', 'N/A')
        if 'T' in date:
            date = date.split('T')[0]
        logger.info("  [%d] %s | %s", idx, date, subject)


def print_email_content(email_info: Dict[str, Any]):
    """
    打印邮件的附件数据（简约版）
    
    Args:
        email_info: 完整的邮件信息字典（包含attachments）
    """
    if not email_info:
        return
    
    subject = email_info.get('subject', 'N/A')
    attachments = email_info.get('attachments', [])
    
    if not attachments:
        logger.info("邮件无附件")
        return
    
    logger.info("邮件: %s | 附件数: %d", subject, len(attachments))
    
    for idx, att in enumerate(attachments, 1):
        filename = att.get('filename', 'N/A')
        
        # 优先显示Baltic Exchange结构化数据
        if 'structured_data' in att and att['structured_data']:
            structured_data = att['structured_data']
            indices = structured_data.get('indices', [])
            metadata = structured_data.get('metadata', {})
            
            # 显示关键信息
            cols_info = ""
            if 'columns' in metadata:
                cols = metadata['columns']
                value_cols = cols.get('value_columns', [])[:3]
                cols_info = f" | 列: {', '.join(value_cols)}"
            
            logger.info("  附件 %d: %s | 数据条数: %d%s", idx, filename, len(indices), cols_info)
            
            # 只显示最新一条数据
            if indices:
                latest = indices[-1]
                key_items = list(latest.items())[:5]
                data_str = ' | '.join([f"{k}: {v}" for k, v in key_items])
                logger.info("    最新数据: %s", data_str)
        
        # CSV附件 - 显示关键数据
        elif 'csv_data' in att and att['csv_data']:
            csv_data = att['csv_data']
            headers = list(csv_data[0].keys()) if csv_data and csv_data[0] else []
            logger.info("  附件 %d: %s | 行数: %d | 列数: %d", idx, filename, len(csv_data), len(headers))
            
            # 只显示最新一行数据
            if csv_data:
                latest_row = csv_data[-1]
                key_items = list(latest_row.items())[:5]
                data_str = ' | '.join([f"{k}: {v}" for k, v in key_items])
                logger.info("    最新数据: %s", data_str)
        
        # 其他类型附件
        else:
            size = att.get('size', 0)
            logger.info("  附件 %d: %s | %d bytes", idx, filename, size)


def custom_email_handler(email_info: Dict[str, Any]):
    """
    自定义邮件处理函数示例
    用户可以在这里添加自己的邮件处理逻辑
    
    Args:
        email_info: 邮件信息字典，包含:
            - uid: 邮件UID
            - subject: 主题
            - from: 发件人
            - to: 收件人
            - date: 日期
            - body: 正文
            - attachments: 附件列表
    """
    logger.info(f"[自定义处理] 收到邮件: {email_info.get('subject')}")
    # 在这里添加您的自定义处理逻辑
    # 例如：保存邮件、发送通知、解析内容等


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='阿里邮箱实时接收脚本')
    parser.add_argument('--list', '-l', action='store_true', help='列出收件箱邮件列表')
    parser.add_argument('--search', '-s', action='store_true', help='搜索邮件')
    parser.add_argument('--sender', type=str, help='按发件人搜索（支持关键词模糊匹配）')
    parser.add_argument('--subject', type=str, help='按主题搜索（支持关键词模糊匹配）')
    parser.add_argument('--limit', type=int, default=20, help='列出或搜索邮件的数量限制（默认20）')
    parser.add_argument('--start', type=int, default=0, help='起始位置（默认0，从最新开始）')
    parser.add_argument('--search-recent', type=int, default=100, help='在最近多少封邮件中搜索（默认100）')
    parser.add_argument('--show-content', action='store_true', help='显示最新匹配邮件的完整内容（包括正文）')
    args = parser.parse_args()
    
    logger.info("=" * 80)
    logger.info("阿里邮箱实时接收脚本启动")
    logger.info(f"邮箱: {EMAIL_CONFIG['username']}")
    logger.info(f"服务器: {EMAIL_CONFIG['server']}:{EMAIL_CONFIG['port']}")
    logger.info("=" * 80)
    
    # 创建邮件接收器
    receiver = MailReceiver(EMAIL_CONFIG)
    
    # 连接邮箱
    if not receiver.connect():
        logger.error("无法连接到邮箱服务器，程序退出")
        return
    
    try:
        # 如果指定了 --search 参数，则搜索邮件后退出
        if args.search or args.sender or args.subject:
            logger.info("正在搜索邮件...")
            emails = receiver.search_emails(
                sender=args.sender,
                subject=args.subject,
                limit=args.limit,
                search_recent=args.search_recent
            )
            print_email_list(emails)
            
            # 如果指定了 --show-content 且有匹配结果，显示最新邮件的完整内容
            if args.show_content and emails:
                latest_email = emails[0]  # 第一封是最新的
                logger.info("")
                logger.info("正在获取最新匹配邮件的完整内容...")
                full_content = receiver.get_email_content(latest_email.get('uid'))
                if full_content:
                    print_email_content(full_content)
            
            return
        
        # 如果指定了 --list 参数，则列出邮件列表后退出
        if args.list:
            logger.info("正在列出收件箱邮件...")
            emails = receiver.list_emails(limit=args.limit, start_from=args.start)
            print_email_list(emails)
            return
        
        # 否则开始监控新邮件
        # 使用自定义回调函数（如果需要）
        # receiver.monitor(callback=custom_email_handler, poll_interval=10)
        
        # 使用默认处理函数
        receiver.monitor(poll_interval=10)
        
    except KeyboardInterrupt:
        logger.info("\n收到退出信号，程序正常退出")
    except Exception as e:
        logger.error(f"程序运行出错: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
    finally:
        receiver.disconnect()


if __name__ == "__main__":
    main()


class ReceiveDataAquabridgeEmail(BaseModel):
    """
    接收 data.aquabridge.com 邮件的任务类
    适配任务系统，继承BaseModel并实现run方法
    默认搜索发件人为 "nora" 且主题包含 "BALTIC EXCHANGE DRY INDICES & FFA DATA" 的邮件
    """
    
    def __init__(self):
        """初始化任务类"""
        # 初始化BaseModel（不需要数据库配置）
        config = {
            "handle_db": "mgo",
            'collection': 'baltic_exchange_index_history',
            'uniq_idx': [('date', pymongo.ASCENDING)]
        }
        super(ReceiveDataAquabridgeEmail, self).__init__(config)
        
        # 邮件配置
        self.email_config = EMAIL_CONFIG.copy()
        
        # 默认搜索条件（可通过环境变量或任务参数覆盖）
        self.default_sender = os.getenv('EMAIL_SEARCH_SENDER', 'nora')
        self.default_subject = os.getenv('EMAIL_SEARCH_SUBJECT', 'BALTIC EXCHANGE DRY INDICES & FFA DATA')
        
        # 搜索参数
        self.search_limit = int(os.getenv('EMAIL_SEARCH_LIMIT', '20'))
        self.search_recent = int(os.getenv('EMAIL_SEARCH_RECENT', '100'))
        self.show_content = os.getenv('EMAIL_SHOW_CONTENT', 'true').lower() == 'true'
        
        # 轮询间隔（秒），用于监控模式
        self.poll_interval = int(os.getenv('EMAIL_POLL_INTERVAL', '10'))
        
        # 邮件接收器
        self.receiver = None
    
    def run(self, task: Optional[Dict[str, Any]] = None, rds=None):  # noqa: ARG002
        """
        运行邮件接收任务
        默认执行搜索并显示匹配邮件的完整内容
        
        Args:
            task: 任务字典（可选），可包含以下配置：
                - sender: 发件人关键词（默认: "nora"）
                - subject: 主题关键词（默认: "BALTIC EXCHANGE DRY INDICES & FFA DATA"）
                - limit: 搜索结果数量限制（默认: 20）
                - search_recent: 在最近多少封邮件中搜索（默认: 100）
                - show_content: 是否显示邮件完整内容（默认: True）
                - mode: 运行模式，'search'（搜索模式，默认）或 'monitor'（监控模式）
                - poll_interval: 监控模式下的轮询间隔（秒）
                - use_idle: 监控模式下是否使用IDLE模式
            rds: Redis连接（可选，当前未使用）
        """
        # 从任务配置中获取参数
        sender = self.default_sender
        subject = self.default_subject
        limit = self.search_limit
        search_recent = self.search_recent
        show_content = self.show_content
        mode = 'search'  # 默认搜索模式
        
        if task:
            sender = task.get('sender', sender)
            subject = task.get('subject', subject)
            limit = task.get('limit', limit)
            search_recent = task.get('search_recent', search_recent)
            show_content = task.get('show_content', show_content)
            mode = task.get('mode', mode)
            self.poll_interval = task.get('poll_interval', self.poll_interval)
            use_idle = task.get('use_idle', False)
        else:
            use_idle = False
        
        logger.info("邮件任务启动 | 邮箱: %s", self.email_config['username'])
        
        # 创建邮件接收器
        self.receiver = MailReceiver(self.email_config, self.mgo)
        
        # 连接邮箱
        if not self.receiver.connect():
            logger.error("无法连接到邮箱服务器，任务退出")
            return
        
        try:
            # 根据模式执行不同操作
            if mode == 'monitor':
                # 监控模式：实时监控新邮件
                logger.info("监控模式启动 | 轮询间隔: %d秒", self.poll_interval)
                self.receiver.monitor(
                    callback=None,  # 使用默认处理函数
                    poll_interval=self.poll_interval,
                    use_idle=use_idle
                )
            else:
                # 搜索模式：搜索并显示匹配邮件（默认模式）
                logger.info("搜索邮件 | 发件人: %s | 主题: %s", sender, subject)
                
                # 搜索邮件
                emails = self.receiver.search_emails(
                    sender=sender,
                    subject=subject,
                    limit=limit,
                    search_recent=search_recent
                )
                
                # 显示邮件列表
                print_email_list(emails)
                
                # 如果指定显示内容且有匹配结果，显示最新邮件的完整内容
                if show_content and emails:
                    latest_email = emails[0]  # 第一封是最新的
                    full_content = self.receiver.get_email_content(latest_email.get('uid'))
                    if full_content:
                        print_email_content(full_content)
                elif not emails:
                    logger.info("未找到匹配的邮件")
                
        except KeyboardInterrupt:
            logger.info("\n收到退出信号，任务正常退出")
        except Exception as e:
            logger.error(f"任务运行出错: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
        finally:
            if self.receiver:
                self.receiver.disconnect()
            # 关闭BaseModel的数据库连接
            self.close()

