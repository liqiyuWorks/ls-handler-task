#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
阿里邮箱实时接收邮件脚本
支持通过IMAP实时监控新邮件并处理
"""

from pkg.public.models import BaseModel
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
    # 防止日志向上传播，避免重复输出
    mail_logger.propagate = False

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
        self._mgo_stores = {}  # 缓存不同表的MgoStore实例

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
            logger.error("IMAP连接错误: %s", str(e))
            self.is_connected = False
            return False
        except Exception as e:
            logger.error("连接邮箱失败: %s", str(e))
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
                    decoded_str += part.decode(encoding or 'utf-8',
                                               errors='ignore')
                except:
                    decoded_str += part.decode('utf-8', errors='ignore')
            else:
                decoded_str += part
        return decoded_str

    def parse_email(self, msg_data: bytes, read_attachments: bool = True) -> Dict[str, Any]:
        """
        解析邮件内容

        Args:
            msg_data: 邮件原始数据
            read_attachments: 是否读取附件数据（默认True）

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

            # 获取附件信息
            attachments = self._get_attachments(
                msg, read_data=read_attachments)

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
            logger.error("解析邮件失败: %s", str(e))
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
                        logger.debug("解码邮件正文失败: %s", str(e))
        else:
            # 单部分邮件
            try:
                charset = msg.get_content_charset() or 'utf-8'
                payload = msg.get_payload(decode=True)
                if payload:
                    body = payload.decode(charset, errors='ignore')
            except Exception as e:
                logger.debug("解码邮件正文失败: %s", str(e))

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
                                            text_content = payload.decode(
                                                charset, errors='ignore')
                                            attachment_info['text'] = text_content

                                            # 如果是CSV文件，尝试解析
                                            if filename.lower().endswith('.csv'):
                                                csv_data = self._parse_csv(
                                                    text_content)
                                                attachment_info['csv_data'] = csv_data

                                                # 1、如果是Baltic Exchange文件，进行专门的结构化解析
                                                structured_data = self._dispatch_csv_to_mongodb(
                                                    filename, text_content, csv_data)
                                                attachment_info['structured_data'] = structured_data

                                        except Exception as e:
                                            logger.debug(
                                                "解码附件文本失败 %s: %s", filename, str(e))

                            except Exception as e:
                                logger.debug("读取附件数据失败 %s: %s",
                                             filename, str(e))

                        attachments.append(attachment_info)
        return attachments

    def _extract_table_name(self, filename: str) -> str:
        """
        从文件名中提取表名
        
        Args:
            filename: 文件名，如 "bfa_supramax_52_20060103_20251105.csv"
            
        Returns:
            str: 表名，如 "bfa_supramax_52"
        """
        filename_lower = filename.lower()
        # 移除文件扩展名
        name_without_ext = filename_lower.rsplit('.', 1)[0]
        
        # 提取表名（文件名中以下划线分隔的第一部分到第一个日期部分之前）
        # 例如: bfa_supramax_52_20060103_20251105 -> bfa_supramax_52
        # 例如: bfa_supramax_52.csv -> bfa_supramax_52
        parts = name_without_ext.split('_')
        
        # 查找第一个看起来像日期的部分（8位数字，如20060103）
        table_parts = []
        for part in parts:
            # 如果遇到8位数字（可能是日期），停止
            if part.isdigit() and len(part) == 8:
                break
            table_parts.append(part)
        
        if table_parts:
            table_name = '_'.join(table_parts)
            # 确保表名不为空
            if table_name:
                return table_name
        
        # 如果没有找到日期部分或表名为空，返回去掉扩展名的文件名
        return name_without_ext

    def _get_mgo_store_for_table(self, table_name: str, uniq_idx: List) -> Optional[MgoStore]:
        """
        获取或创建指定表的MgoStore实例
        
        Args:
            table_name: 表名
            uniq_idx: 唯一索引字段列表
            
        Returns:
            MgoStore: MgoStore实例，如果无法创建则返回None
        """
        # 如果已缓存，直接返回
        if table_name in self._mgo_stores:
            return self._mgo_stores[table_name]
        
        # 如果没有mgo实例，无法创建新的
        if not self.mgo:
            return None
        
        try:
            # 从现有mgo实例获取连接信息
            mgo_client = self.mgo.mgo_client
            mgo_db = self.mgo.mgo_db
            
            # 创建新的MgoStore配置
            config = {
                'mgo_client': mgo_client,
                'mgo_db': mgo_db,
                'collection': table_name,
                'uniq_idx': uniq_idx,
                'idx_dic': {}
            }
            
            # 创建MgoStore实例
            mgo_store = MgoStore(config)
            self._mgo_stores[table_name] = mgo_store
            logger.debug("创建MgoStore实例: %s", table_name)
            return mgo_store
        except Exception as e:
            logger.error("创建MgoStore实例失败 [%s]: %s", table_name, str(e))
            return None

    def _dispatch_csv_to_mongodb(self, filename: str, text_content: str, csv_data: List[Dict[str, Any]]):
        """
        解析CSV文件并保存到MongoDB

        Args:
            filename: 文件名
            text_content: 文本内容
            csv_data: CSV数据
        """
        filename_lower = filename.lower()

        if filename_lower.startswith('baltic exchange') and 'historic data' in filename_lower:
            """
            解析Baltic Exchange历史数据文件，转换为结构化数据
            """
            structured_data = self._parse_baltic_exchange(
                csv_text=text_content, csv_data=csv_data)
            # 如果有MongoDB连接，保存数据
            if self.mgo:
                saved_count = 0
                failed_count = 0
                for index in structured_data["indices"]:
                    # 解析日期字符串（格式如 "05-Nov-2025"）并格式化为 "2025-11-05"
                    date_str = str(index.get("date", "")).strip()
                    if date_str:
                        try:
                            # 尝试解析日期字符串（支持多种格式）
                            date_obj = None
                            date_formats = [
                                "%d-%b-%Y", "%d-%B-%Y", "%Y-%m-%d",
                                "%Y/%m/%d", "%d/%m/%Y"
                            ]

                            for fmt in date_formats:
                                try:
                                    date_obj = datetime.strptime(date_str, fmt)
                                    break
                                except ValueError:
                                    continue

                            if not date_obj:
                                try:
                                    date_obj = parsedate_to_datetime(date_str)
                                except (ValueError, TypeError):
                                    pass

                            if date_obj:
                                formatted_date = date_obj.strftime("%Y-%m-%d")
                                index["date"] = formatted_date
                                # 保存到MongoDB
                                result = self.mgo.set(
                                    {"date": formatted_date}, index)
                                if result:
                                    saved_count += 1
                                else:
                                    failed_count += 1
                            else:
                                failed_count += 1
                                logger.debug("无法解析日期格式: %s", date_str)
                        except Exception as e:
                            failed_count += 1
                            logger.debug("日期解析失败: %s, 错误: %s",
                                         date_str, str(e))

                if saved_count > 0:
                    logger.info("✓ 附件: %s | 已保存 %d 条数据到MongoDB",
                                filename, saved_count)
                if failed_count > 0:
                    logger.warning("✗ 附件: %s | %d 条数据保存失败",
                                   filename, failed_count)
            logger.debug("成功解析CSV附件: %s, 行数: %d", filename, len(csv_data))
            return structured_data

        elif filename_lower.startswith('bfa_supramax_52'):
            """
            解析bfa_supramax_52数据文件，转换为结构化数据
            """
            structured_data = self._parse_bfa_supramax_52(
                csv_text=text_content, csv_data=csv_data)
            # 保存数据到MongoDB
            self._save_bfa_data_to_mongodb(filename, structured_data)
            logger.debug("成功解析CSV附件: %s, 行数: %d", filename, len(csv_data))
            return structured_data
            
        elif filename_lower.startswith('bfa_supramax'):
            """
            解析bfa_supramax数据文件，转换为结构化数据
            """
            structured_data = self._parse_bfa_data(
                csv_text=text_content, csv_data=csv_data)
            # 保存数据到MongoDB
            self._save_bfa_data_to_mongodb(filename, structured_data)
            logger.debug("成功解析CSV附件: %s, 行数: %d", filename, len(csv_data))
            return structured_data
            
        elif filename_lower.startswith('bfa_panamax_74'):
            """
            解析bfa_panamax_74数据文件，转换为结构化数据
            """
            structured_data = self._parse_bfa_data(
                csv_text=text_content, csv_data=csv_data)
            # 保存数据到MongoDB
            self._save_bfa_data_to_mongodb(filename, structured_data)
            logger.debug("成功解析CSV附件: %s, 行数: %d", filename, len(csv_data))
            return structured_data
            
        elif filename_lower.startswith('bfa_panamax'):
            """
            解析bfa_panamax数据文件，转换为结构化数据
            """
            structured_data = self._parse_bfa_data(
                csv_text=text_content, csv_data=csv_data)
            # 保存数据到MongoDB
            self._save_bfa_data_to_mongodb(filename, structured_data)
            logger.debug("成功解析CSV附件: %s, 行数: %d", filename, len(csv_data))
            return structured_data
            
        elif filename_lower.startswith('bfa_handysize'):
            """
            解析bfa_handysize数据文件，转换为结构化数据
            """
            structured_data = self._parse_bfa_data(
                csv_text=text_content, csv_data=csv_data)
            # 保存数据到MongoDB
            self._save_bfa_data_to_mongodb(filename, structured_data)
            logger.debug("成功解析CSV附件: %s, 行数: %d", filename, len(csv_data))
            return structured_data
            
        elif filename_lower.startswith('bfa_cape'):
            """
            解析bfa_cape数据文件，转换为结构化数据
            """
            structured_data = self._parse_bfa_data(
                csv_text=text_content, csv_data=csv_data)
            # 保存数据到MongoDB
            self._save_bfa_data_to_mongodb(filename, structured_data)
            logger.debug("成功解析CSV附件: %s, 行数: %d", filename, len(csv_data))
            return structured_data
        else:
            return None

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
            logger.debug("解析CSV失败: %s", str(e))
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
                logger.warning("备选CSV解析方法也失败: %s", str(e2))

        return csv_data

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
                headers = list(csv_data[0].keys()
                               ) if csv_data and csv_data[0] else []

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
            logger.debug("解析Baltic Exchange结构化数据失败: %s", str(e))
            structured['error'] = str(e)

        return structured

    def _parse_bfa_data(self, csv_text: str, csv_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        解析BFA数据文件（通用方法），转换为结构化数据
        适用于所有BFA类型：bfa_supramax_52, bfa_supramax, bfa_panamax_74, bfa_panamax, bfa_handysize, bfa_cape

        Args:
            csv_text: CSV原始文本
            csv_data: 已解析的CSV数据

        Returns:
            Dict: 结构化数据，包含：
                - metadata: 元数据（组描述、日期范围等）
                - routes: 路线数据列表
                - summary: 摘要信息
        """
        structured = {
            'metadata': {},
            'routes': [],
            'summary': {}
        }

        try:
            if csv_data:
                # 获取所有列名
                headers = list(csv_data[0].keys()) if csv_data and csv_data[0] else []
                
                # 构建路线数据
                routes = []
                group_desc = None
                archive_dates = set()
                
                for row in csv_data:
                    route_entry = {}
                    
                    # 解析GroupDesc
                    group_desc = row.get('GroupDesc', '').strip()
                    if group_desc:
                        route_entry['group_desc'] = group_desc
                    
                    # 解析ArchiveDate
                    archive_date = row.get('ArchiveDate', '').strip()
                    if archive_date:
                        route_entry['archive_date'] = archive_date
                        archive_dates.add(archive_date)
                    
                    # 解析RouteIdentifier
                    route_identifier = row.get('RouteIdentifier', '').strip()
                    if route_identifier:
                        route_entry['route_identifier'] = route_identifier
                    
                    # 解析RouteAverage（数值）
                    route_average = row.get('RouteAverage', '').strip()
                    if route_average:
                        try:
                            route_entry['route_average'] = float(route_average)
                        except (ValueError, TypeError):
                            route_entry['route_average'] = route_average
                    else:
                        route_entry['route_average'] = None
                    
                    # 解析FFADescription
                    ffa_description = row.get('FFADescription', '').strip()
                    if ffa_description:
                        route_entry['ffa_description'] = ffa_description
                    
                    routes.append(route_entry)
                
                structured['routes'] = routes
                
                # 添加元数据
                structured['metadata']['group_desc'] = group_desc
                structured['metadata']['columns'] = headers
                if archive_dates:
                    structured['metadata']['archive_dates'] = sorted(list(archive_dates))
                    structured['metadata']['date_range'] = {
                        'min': min(archive_dates),
                        'max': max(archive_dates)
                    }
                
                # 添加摘要信息
                structured['summary']['total_routes'] = len(routes)
                structured['summary']['unique_dates'] = len(archive_dates)
                
        except Exception as e:
            logger.debug("解析BFA结构化数据失败: %s", str(e))
            structured['error'] = str(e)

        return structured

    def _parse_bfa_supramax_52(self, csv_text: str, csv_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        解析BFA Supramax 52数据文件，转换为结构化数据
        （使用通用解析方法）
        """
        return self._parse_bfa_data(csv_text, csv_data)

    def _save_bfa_data_to_mongodb(self, filename: str, structured_data: Dict[str, Any]) -> None:
        """
        将BFA结构化数据保存到MongoDB（通用保存方法）
        按archive_date分组，将同一天的所有路线数据合并到一个文档中
        
        Args:
            filename: 文件名
            structured_data: 结构化数据
        """
        if not self.mgo or not structured_data or "routes" not in structured_data:
            return
        
        # 从文件名提取表名
        table_name = self._extract_table_name(filename)
        # 定义唯一索引：只使用archive_date作为唯一键
        uniq_idx = [
            ('archive_date', pymongo.ASCENDING)
        ]
        # 获取对应表的MgoStore实例
        table_mgo = self._get_mgo_store_for_table(table_name, uniq_idx)
        
        if not table_mgo:
            logger.warning("无法获取MgoStore实例，表名: %s", table_name)
            return
        
        # 按日期分组数据
        date_groups = {}
        failed_routes = []
        
        for route in structured_data["routes"]:
            # 解析日期字符串（格式如 "05-Nov-2025"）并格式化为 "2025-11-05"
            date_str = str(route.get("archive_date", "")).strip()
            if not date_str:
                failed_routes.append(route)
                logger.debug("缺少archive_date字段: %s", route.get("route_identifier", "unknown"))
                continue
            
            try:
                # 尝试解析日期字符串（支持多种格式）
                date_obj = None
                date_formats = [
                    "%d-%b-%Y", "%d-%B-%Y", "%Y-%m-%d",
                    "%Y/%m/%d", "%d/%m/%Y"
                ]

                for fmt in date_formats:
                    try:
                        date_obj = datetime.strptime(date_str, fmt)
                        break
                    except ValueError:
                        continue

                if not date_obj:
                    try:
                        date_obj = parsedate_to_datetime(date_str)
                    except (ValueError, TypeError):
                        pass

                if date_obj:
                    formatted_date = date_obj.strftime("%Y-%m-%d")
                    
                    # 如果该日期还没有分组，创建新分组
                    if formatted_date not in date_groups:
                        date_groups[formatted_date] = {
                            "archive_date": formatted_date,
                            "routes": [],
                            "group_desc": route.get("group_desc", "")
                        }
                    
                    # 将路线数据添加到对应日期的分组中（不包含archive_date和group_desc）
                    route_data = {
                        "route_identifier": route.get("route_identifier", ""),
                        "route_average": route.get("route_average"),
                        "ffa_description": route.get("ffa_description", "")
                    }
                    date_groups[formatted_date]["routes"].append(route_data)
                else:
                    failed_routes.append(route)
                    logger.debug("无法解析日期格式: %s", date_str)
            except Exception as e:
                failed_routes.append(route)
                logger.debug("日期解析失败: %s, 错误: %s",
                             date_str, str(e))
        
        # 保存分组后的数据
        saved_count = 0
        failed_count = 0
        
        for formatted_date, date_data in date_groups.items():
            try:
                # 使用archive_date作为查询条件
                query = {"archive_date": formatted_date}
                
                # 检查该日期是否已存在数据
                existing_data = table_mgo.get(query)
                
                # 检查是否存在有效数据（不是空字典，且有routes字段）
                if existing_data and isinstance(existing_data, dict) and existing_data.get("routes"):
                    # 如果已存在，合并路线数据（去重）
                    existing_routes = existing_data.get("routes", [])
                    new_routes = date_data.get("routes", [])
                    
                    if not isinstance(existing_routes, list):
                        existing_routes = []
                    if not isinstance(new_routes, list):
                        new_routes = []
                    
                    # 创建现有路线的标识符集合（用于去重）
                    existing_route_ids = {
                        route.get("route_identifier", "") 
                        for route in existing_routes 
                        if route and isinstance(route, dict) and route.get("route_identifier")
                    }
                    
                    # 合并路线数据：先添加现有路线，再添加新路线（去重）
                    merged_routes = list(existing_routes)
                    for new_route in new_routes:
                        if not isinstance(new_route, dict):
                            continue
                        route_id = new_route.get("route_identifier", "")
                        if route_id and route_id not in existing_route_ids:
                            # 新路线，直接添加
                            merged_routes.append(new_route)
                            existing_route_ids.add(route_id)
                        elif route_id:
                            # 如果路线已存在，更新该路线数据
                            for i, existing_route in enumerate(merged_routes):
                                if (isinstance(existing_route, dict) and 
                                    existing_route.get("route_identifier") == route_id):
                                    merged_routes[i] = new_route
                                    break
                    
                    date_data["routes"] = merged_routes
                    logger.debug("合并日期 %s 的数据：原有 %d 条路线，新增 %d 条路线，合并后 %d 条路线",
                                 formatted_date, len(existing_routes), len(new_routes), len(merged_routes))
                else:
                    logger.debug("日期 %s 的数据不存在，将创建新记录，包含 %d 条路线",
                                 formatted_date, len(date_data.get("routes", [])))
                
                # 保存到MongoDB（使用对应表的MgoStore实例）
                result = table_mgo.set(query, date_data)
                if result:
                    saved_count += 1
                    logger.debug("成功保存日期 %s 的数据，包含 %d 条路线",
                                 formatted_date, len(date_data["routes"]))
                else:
                    failed_count += 1
                    logger.debug("保存日期 %s 的数据失败", formatted_date)
            except Exception as e:
                failed_count += 1
                logger.debug("保存日期 %s 的数据时出错: %s", formatted_date, str(e))
        
        # 统计失败的路线数量
        failed_count += len(failed_routes)

        if saved_count > 0:
            total_routes = sum(len(group["routes"]) for group in date_groups.values())
            logger.info("✓ 附件: %s | 表: %s | 已保存 %d 个日期的数据（共 %d 条路线）到MongoDB",
                        filename, table_name, saved_count, total_routes)
        if failed_count > 0:
            logger.warning("✗ 附件: %s | 表: %s | %d 条数据保存失败",
                           filename, table_name, failed_count)

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

            logger.debug("收件箱共有 %d 封邮件，显示第 %d 到 %d 封",
                         total_count, start_from + 1, end_pos)

            # 获取邮件的基本信息
            for uid in target_uids:
                try:
                    uid_str = uid.decode('utf-8')

                    # 获取邮件头信息（只获取头部，不获取正文，速度更快）
                    status, email_data = self.imap.fetch(
                        uid_str, '(RFC822.HEADER)')

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
                    logger.debug("解析邮件 %s 失败: %s", uid.decode('utf-8'), str(e))
                    continue

        except imaplib.IMAP4.error as e:
            logger.error("列出邮件时IMAP错误: %s", str(e))
            self.is_connected = False
        except Exception as e:
            logger.error("列出邮件时出错: %s", str(e))

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
                    status, email_data = self.imap.fetch(
                        uid_str, '(RFC822.HEADER)')

                    if status != 'OK' or not email_data:
                        continue

                    headers = email_data[0][1]
                    msg = email.message_from_bytes(headers)

                    subject_text = self.decode_mime_words(
                        msg.get('Subject', ''))
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
            logger.error("搜索邮件时IMAP错误: %s", str(e))
            self.is_connected = False
        except Exception as e:
            logger.error("搜索邮件时出错: %s", str(e))

        return emails_list

    def get_email_content(self, uid: str, read_attachments: bool = True) -> Optional[Dict[str, Any]]:
        """
        获取指定UID邮件的完整内容（包括正文和附件信息）

        Args:
            uid: 邮件UID
            read_attachments: 是否读取附件数据（默认True）

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
                logger.debug("无法获取邮件 %s 的内容", uid)
                return None

            # 解析邮件
            email_info = self.parse_email(
                msg_data[0][1], read_attachments=read_attachments)
            if email_info:
                email_info['uid'] = uid
                return email_info

        except imaplib.IMAP4.error as e:
            logger.error("获取邮件内容时IMAP错误: %s", str(e))
            self.is_connected = False
        except Exception as e:
            logger.error("获取邮件内容时出错: %s", str(e))

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
            new_uids = [uid for uid in uids if uid.decode(
                'utf-8') not in self._processed_uids]

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
                    logger.info("收到新邮件 - UID: %s, 主题: %s", uid_str,
                                email_info.get('subject', 'N/A'))

            # 更新最后处理的UID
            if uids:
                self.last_uid = uids[-1].decode('utf-8')

        except imaplib.IMAP4.error as e:
            logger.error("获取新邮件时IMAP错误: %s", str(e))
            self.is_connected = False
        except (OSError, ConnectionError, ssl.SSLError) as e:
            logger.error("获取新邮件时连接错误: %s", str(e))
            self.is_connected = False
        except Exception as e:
            error_msg = str(e).lower()
            if any(keyword in error_msg for keyword in ['closed', 'connection', 'eof', 'socket', 'ssl']):
                logger.error("获取新邮件时连接断开: %s", str(e))
                self.is_connected = False
            else:
                logger.error("获取新邮件时出错: %s", str(e))

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

        logger.info("开始监控新邮件，轮询间隔: %d秒", poll_interval)

        try:
            # 尝试使用IDLE模式（如果支持且启用）
            if use_idle:
                try:
                    logger.info("尝试使用IDLE模式实时监控...")
                    self._monitor_with_idle(callback)
                except Exception as e:
                    logger.debug("IDLE模式不可用，切换到轮询模式: %s", str(e))
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
            logger.error("监控过程中出错: %s", str(e))
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
                            logger.debug("收到新邮件通知: %s", response.decode(
                                'utf-8', errors='ignore'))
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
                                logger.error("回调函数执行失败: %s", str(e))
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
                logger.debug("IDLE模式出错: %s", str(e))
                raise

    def _monitor_with_polling(self, callback: Optional[Callable[[Dict[str, Any]], None]] = None,
                              poll_interval: int = 10):
        """
        使用轮询模式监控新邮件

        Args:
            callback: 新邮件回调函数
            poll_interval: 轮询间隔（秒）
        """
        logger.debug("使用轮询模式监控新邮件，间隔: %d秒", poll_interval)

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
                        logger.warning("重连失败，等待 %d 秒后重试 (%d/%d)", poll_interval,
                                       consecutive_errors, max_consecutive_errors)
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
                    logger.info("检测到 %d 封新邮件", len(new_emails))
                    for email_info in new_emails:
                        if callback:
                            try:
                                callback(email_info)
                            except Exception as e:
                                logger.error("回调函数执行失败: %s", str(e))
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
                logger.error("轮询过程中出错: %s", str(e))

                if consecutive_errors >= max_consecutive_errors:
                    logger.error("连续 %d 次错误，程序退出", max_consecutive_errors)
                    return

                # 标记连接可能断开
                error_msg = str(e).lower()
                if any(keyword in error_msg for keyword in ['closed', 'connection', 'eof', 'socket', 'ssl']):
                    self.is_connected = False

                logger.info("等待 %d 秒后重试 (%d/%d)", poll_interval,
                            consecutive_errors, max_consecutive_errors)
                time.sleep(poll_interval)

    def _default_email_handler(self, email_info: Dict[str, Any]):
        """
        默认邮件处理函数 - 仅显示附件数据

        Args:
            email_info: 邮件信息字典
        """
        attachments = email_info.get('attachments', [])
        if not attachments:
            return

        subject = email_info.get('subject', 'N/A')
        logger.info("收到邮件: %s | 附件数: %d", subject, len(attachments))

        for idx, att in enumerate(attachments, 1):
            filename = att.get('filename', 'N/A')

            # 优先显示Baltic Exchange结构化数据
            if 'structured_data' in att and att['structured_data']:
                structured_data = att['structured_data']
                indices = structured_data.get('indices', [])
                logger.info("  附件 %d: %s | 数据条数: %d",
                            idx, filename, len(indices))
            # 显示CSV数据
            elif 'csv_data' in att and att['csv_data']:
                csv_data = att['csv_data']
                headers = list(csv_data[0].keys()
                               ) if csv_data and csv_data[0] else []
                logger.info("  附件 %d: %s | 行数: %d | 列数: %d", idx,
                            filename, len(csv_data), len(headers))
            else:
                size = att.get('size', 0)
                logger.info("  附件 %d: %s | %d bytes", idx, filename, size)


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

    attachments = email_info.get('attachments', [])

    if not attachments:
        logger.info("邮件无附件")
        return

    for idx, att in enumerate(attachments, 1):
        filename = att.get('filename', 'N/A')

        # 优先显示Baltic Exchange结构化数据
        if 'structured_data' in att and att['structured_data']:
            structured_data = att['structured_data']
            indices = structured_data.get('indices', [])
            logger.debug("附件 %d: %s | 数据条数: %d", idx, filename, len(indices))

        # CSV附件
        elif 'csv_data' in att and att['csv_data']:
            csv_data = att['csv_data']
            headers = list(csv_data[0].keys()
                           ) if csv_data and csv_data[0] else []
            logger.debug("附件 %d: %s | 行数: %d | 列数: %d", idx,
                         filename, len(csv_data), len(headers))

        # 其他类型附件
        else:
            size = att.get('size', 0)
            logger.debug("附件 %d: %s | %d bytes", idx, filename, size)


def custom_email_handler(email_info: Dict[str, Any]):
    """
    自定义邮件处理函数示例

    Args:
        email_info: 邮件信息字典
    """
    logger.info("收到邮件: %s", email_info.get('subject'))


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description='阿里邮箱实时接收脚本')
    parser.add_argument('--list', '-l', action='store_true', help='列出收件箱邮件列表')
    parser.add_argument('--search', '-s', action='store_true', help='搜索邮件')
    parser.add_argument('--sender', type=str, help='按发件人搜索（支持关键词模糊匹配）')
    parser.add_argument('--subject', type=str, help='按主题搜索（支持关键词模糊匹配）')
    parser.add_argument('--limit', type=int, default=20,
                        help='列出或搜索邮件的数量限制（默认20）')
    parser.add_argument('--start', type=int, default=0, help='起始位置（默认0，从最新开始）')
    parser.add_argument('--search-recent', type=int,
                        default=100, help='在最近多少封邮件中搜索（默认100）')
    parser.add_argument('--show-content', action='store_true',
                        help='显示最新匹配邮件的完整内容（包括正文）')
    args = parser.parse_args()

    logger.info("邮件脚本启动 | 邮箱: %s", EMAIL_CONFIG['username'])

    # 创建邮件接收器
    receiver = MailReceiver(EMAIL_CONFIG)

    # 连接邮箱
    if not receiver.connect():
        logger.error("无法连接到邮箱服务器，程序退出")
        return

    try:
        # 如果指定了 --search 参数，则搜索邮件后退出
        if args.search or args.sender or args.subject:
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
                receiver.get_email_content(latest_email.get('uid'))

            return

        # 如果指定了 --list 参数，则列出邮件列表后退出
        if args.list:
            emails = receiver.list_emails(
                limit=args.limit, start_from=args.start)
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
        logger.error("程序运行出错: %s", str(e))
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
        self.default_subject = os.getenv(
            'EMAIL_SEARCH_SUBJECT', 'BALTIC EXCHANGE DRY INDICES & FFA DATA')

        # 搜索参数
        self.search_limit = int(os.getenv('EMAIL_SEARCH_LIMIT', '20'))
        self.search_recent = int(os.getenv('EMAIL_SEARCH_RECENT', '100'))
        self.show_content = os.getenv(
            'EMAIL_SHOW_CONTENT', 'true').lower() == 'true'

        # 处理邮件数量（默认处理最新的1封）
        self.process_count = int(os.getenv('EMAIL_PROCESS_COUNT', '3'))

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
                - process_count: 处理邮件数量（默认: 1，处理最新的1封；可设置为2处理最新的2封）
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
        process_count = self.process_count
        mode = 'search'  # 默认搜索模式

        if task:
            sender = task.get('sender', sender)
            subject = task.get('subject', subject)
            limit = task.get('limit', limit)
            search_recent = task.get('search_recent', search_recent)
            show_content = task.get('show_content', show_content)
            process_count = task.get('process_count', process_count)
            mode = task.get('mode', mode)
            self.poll_interval = task.get('poll_interval', self.poll_interval)
            use_idle = task.get('use_idle', False)
        else:
            use_idle = False

        # 创建邮件接收器
        self.receiver = MailReceiver(self.email_config, self.mgo)

        # 连接邮箱
        if not self.receiver.connect():
            logger.error("✗ 无法连接到邮箱服务器")
            return

        try:
            # 根据模式执行不同操作
            if mode == 'monitor':
                # 监控模式：实时监控新邮件
                logger.info("监控模式启动 | 轮询间隔: %d秒", self.poll_interval)
                self.receiver.monitor(
                    callback=None,
                    poll_interval=self.poll_interval,
                    use_idle=use_idle
                )
            else:
                # 搜索模式：搜索并显示匹配邮件（默认模式）
                # 搜索邮件
                emails = self.receiver.search_emails(
                    sender=sender,
                    subject=subject,
                    limit=limit,
                    search_recent=search_recent
                )

                # 先显示所有匹配的邮件名称
                print_email_list(emails)

                # 如果指定显示内容且有匹配结果，处理邮件
                if show_content and emails:
                    # 根据 process_count 决定处理多少封邮件
                    process_emails = emails[:process_count]
                    logger.info("")
                    logger.info("处理最新 %d 封邮件:", len(process_emails))

                    for idx, email_info in enumerate(process_emails, 1):
                        email_subject = email_info.get('subject', 'N/A')
                        logger.info("  [%d/%d] 处理邮件: %s", idx,
                                    len(process_emails), email_subject)

                        # 先获取邮件基本信息（不读取附件数据），检查附件数量
                        email_content_preview = self.receiver.get_email_content(
                            email_info.get('uid'), read_attachments=False)
                        if email_content_preview:
                            attachments = email_content_preview.get(
                                'attachments', [])
                            if attachments:
                                logger.info(
                                    "     发现 %d 个附件，开始处理...", len(attachments))
                                # 然后获取完整内容（包括附件数据），触发保存
                                self.receiver.get_email_content(
                                    email_info.get('uid'), read_attachments=True)
                            else:
                                logger.info("     邮件无附件")
                        else:
                            logger.warning("     无法获取邮件内容")

                        # 如果不是最后一封，添加分隔
                        if idx < len(process_emails):
                            logger.info("")
                elif not emails:
                    logger.info("未找到匹配的邮件")

        except KeyboardInterrupt:
            logger.info("\n收到退出信号，任务正常退出")
        except Exception as e:
            logger.error("任务运行出错: %s", str(e))
            import traceback
            logger.error(traceback.format_exc())
        finally:
            if self.receiver:
                self.receiver.disconnect()
            # 关闭BaseModel的数据库连接
            self.close()
