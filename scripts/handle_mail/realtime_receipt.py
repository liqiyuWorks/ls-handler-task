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
from email.header import decode_header
from email.utils import parsedate_to_datetime
from typing import Optional, Dict, Any, Callable
import ssl


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
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化邮件接收器
        
        Args:
            config: 邮箱配置字典
        """
        self.config = config
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
            logger.info(f"正在连接到邮箱服务器: {self.config['server']}:{self.config['port']}")
            
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
            logger.info("邮箱登录成功")
            
            # 选择邮箱文件夹
            status, messages = self.imap.select(self.config['mailbox'])
            if status != 'OK':
                logger.error(f"无法选择邮箱文件夹: {self.config['mailbox']}")
                return False
            
            # 获取当前邮箱中的最后一条邮件UID
            status, messages = self.imap.search(None, 'ALL')
            if status == 'OK' and messages[0]:
                uids = messages[0].split()
                if uids:
                    self.last_uid = uids[-1].decode('utf-8')
                    logger.info(f"初始邮件UID: {self.last_uid}")
            
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
                logger.info("已断开邮箱连接")
            except Exception as e:
                logger.error(f"断开连接时出错: {str(e)}")
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
            
            # 获取附件信息
            attachments = self._get_attachments(msg)
            
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
    
    def _get_attachments(self, msg: message.Message) -> list:
        """
        获取附件信息
        
        Args:
            msg: 邮件消息对象
            
        Returns:
            list: 附件信息列表
        """
        attachments = []
        if msg.is_multipart():
            for part in msg.walk():
                content_disposition = str(part.get("Content-Disposition"))
                if "attachment" in content_disposition:
                    filename = part.get_filename()
                    if filename:
                        filename = self.decode_mime_words(filename)
                        attachments.append({
                            'filename': filename,
                            'content_type': part.get_content_type(),
                            'size': len(part.get_payload(decode=True) or b'')
                        })
        return attachments
    
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
            
            logger.info(f"在最近 {len(uids)} 封邮件中搜索...")
            if sender:
                logger.info(f"  发件人关键词: {sender}")
            if subject:
                logger.info(f"  主题关键词: {subject}")
            
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
                    logger.warning(f"解析邮件 {uid.decode('utf-8')} 失败: {str(e)}")
                    continue
            
            logger.info(f"找到 {matched_count} 封匹配的邮件")
            
        except imaplib.IMAP4.error as e:
            logger.error(f"搜索邮件时IMAP错误: {str(e)}")
            self.is_connected = False
        except Exception as e:
            logger.error(f"搜索邮件时出错: {str(e)}")
        
        return emails_list
    
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


    def _default_email_handler(self, email_info: Dict[str, Any]):
        """
        默认邮件处理函数
        
        Args:
            email_info: 邮件信息字典
        """
        logger.info("=" * 80)
        logger.info(f"收到新邮件:")
        logger.info(f"  UID: {email_info.get('uid', 'N/A')}")
        logger.info(f"  主题: {email_info.get('subject', 'N/A')}")
        logger.info(f"  发件人: {email_info.get('from', 'N/A')}")
        logger.info(f"  收件人: {email_info.get('to', 'N/A')}")
        logger.info(f"  日期: {email_info.get('date', 'N/A')}")
        logger.info(f"  附件数量: {len(email_info.get('attachments', []))}")
        if email_info.get('attachments'):
            for att in email_info.get('attachments', []):
                logger.info(f"    - {att.get('filename')} ({att.get('size', 0)} bytes)")
        logger.info(f"  正文预览: {email_info.get('body', '')[:200]}...")
        logger.info("=" * 80)


def print_email_list(emails: list):
    """
    格式化打印邮件列表
    
    Args:
        emails: 邮件信息列表
    """
    if not emails:
        logger.info("没有邮件可显示")
        return
    
    logger.info("=" * 100)
    logger.info(f"{'序号':<6} {'UID':<10} {'发件人':<30} {'主题':<40} {'日期':<20}")
    logger.info("-" * 100)
    
    for idx, email_info in enumerate(emails, 1):
        uid = email_info.get('uid', 'N/A')[:10]
        from_addr = email_info.get('from', 'N/A')
        if len(from_addr) > 28:
            from_addr = from_addr[:25] + "..."
        
        subject = email_info.get('subject', 'N/A')
        if len(subject) > 38:
            subject = subject[:35] + "..."
        
        date = email_info.get('date', 'N/A')
        if 'T' in date:
            date = date.split('T')[0] + ' ' + date.split('T')[1].split('.')[0][:5]
        
        logger.info(f"{idx:<6} {uid:<10} {from_addr:<30} {subject:<40} {date:<20}")
    
    logger.info("=" * 100)
    logger.info(f"共显示 {len(emails)} 封邮件")


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

