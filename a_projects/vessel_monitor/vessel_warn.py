"""
智能航运监控系统 - 基于AIS数据的船舶航速监控与预警
支持多船监控、智能预警、时效性优化和操作效率提升
"""

import requests
import time
import json
from datetime import datetime
from typing import Dict, Optional, Tuple
import logging
from dataclasses import dataclass
from enum import Enum


# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('vessel_monitor.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class AlertType(Enum):
    """预警类型枚举"""
    STOPPED = "停航"
    SLOW_DOWN = "降速"
    SPEED_RECOVERY = "航速恢复"
    DATA_ERROR = "数据异常"


@dataclass
class VesselConfig:
    """船舶监控配置"""
    mmsi: str
    name: str = ""
    speed_threshold: float = 1.0  # 停航阈值(节)
    slow_down_threshold: float = 5.0  # 降速阈值(节)
    normal_speed: float = 10.0  # 正常航速(节)
    check_interval: int = 30  # 检查间隔(秒)
    alert_cooldown: int = 300  # 预警冷却时间(秒)


@dataclass
class VesselStatus:
    """船舶状态"""
    mmsi: str
    speed: float
    timestamp: datetime
    position: Optional[Tuple[float, float]] = None
    heading: Optional[float] = None
    status: str = "unknown"


class VesselMonitor:
    """船舶监控器"""
    
    def __init__(self):
        self.vessels: Dict[str, VesselConfig] = {}
        self.vessel_status: Dict[str, VesselStatus] = {}
        self.last_alerts: Dict[str, datetime] = {}
        self.api_token = 'NAVGREEN_eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJleHAiOjE3NTg2OTQyNjMsIm5hbWUiOiJcdTY3NGVcdTY2MDciLCJ1c2VybmFtZSI6IjE1MTUyNjI3MTYxIiwiY3JlYXRlZF9hdCI6IjIwMjUtMDUtMDkgMjA6MjE6MzAuODU2NDEzIiwiaXNfYWN0aXZlIjp0cnVlLCJwZXJtaXNzaW9uIjoxLCJtb2JpbGUiOiIxNTE1MjYyNzE2MSIsImNvbXBhbnkiOiJOQVZHcmVlbiIsInJvbGUiOlsib3duZXIiLCJjaGFydGVyZXIiLCJicm9rZXIiXSwiaXNfbG9nZ2VkX3d4IjoxfQ.0e6u0kXRNjNO7w8JoD8fFpdRa-8kPrMl28D8uij9DSU'
        self.api_base_url = "https://api.navgreen.cn/api/vessel/status/location"
        
    def add_vessel(self, config: VesselConfig):
        """添加船舶到监控列表"""
        self.vessels[config.mmsi] = config
        logger.info("添加船舶监控: %s - %s", config.mmsi, config.name)
        
    def get_vessel_data(self, mmsi: str) -> Optional[VesselStatus]:
        """获取船舶数据"""
        url = f"{self.api_base_url}?mmsi={mmsi}"
        headers = {
            'accept': 'application/json',
            'token': self.api_token
        }
        
        try:
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            # 解析船舶数据
            speed = data.get('speed', 0)
            lat = data.get('latitude')
            lon = data.get('longitude')
            heading = data.get('heading')
            
            position = (lat, lon) if lat is not None and lon is not None else None
            
            return VesselStatus(
                mmsi=mmsi,
                speed=speed,
                timestamp=datetime.now(),
                position=position,
                heading=heading,
                status=data.get('status', 'unknown')
            )
            
        except requests.exceptions.RequestException as e:
            logger.error("获取船舶 %s 数据失败: %s", mmsi, e)
            return None
        except (KeyError, ValueError, TypeError) as e:
            logger.error("解析船舶 %s 数据失败: %s", mmsi, e)
            return None
    
    def analyze_speed_change(self, mmsi: str, current_status: VesselStatus) -> Optional[AlertType]:
        """分析航速变化并判断预警类型"""
        config = self.vessels.get(mmsi)
        if not config:
            return None
            
        previous_status = self.vessel_status.get(mmsi)
        
        # 检查是否在冷却期内
        last_alert = self.last_alerts.get(mmsi)
        if last_alert and (datetime.now() - last_alert).seconds < config.alert_cooldown:
            return None
        
        # 停航检测
        if current_status.speed <= config.speed_threshold:
            if not previous_status or previous_status.speed > config.speed_threshold:
                return AlertType.STOPPED
        
        # 降速检测
        elif current_status.speed <= config.slow_down_threshold:
            if previous_status and previous_status.speed > config.slow_down_threshold:
                return AlertType.SLOW_DOWN
        
        # 航速恢复检测
        elif current_status.speed > config.normal_speed:
            if previous_status and previous_status.speed <= config.slow_down_threshold:
                return AlertType.SPEED_RECOVERY
        
        return None
    
    def send_alert(self, mmsi: str, alert_type: AlertType, vessel_status: VesselStatus):
        """发送预警信息"""
        config = self.vessels.get(mmsi)
        vessel_name = config.name if config else mmsi
        
        # 构建预警消息
        message = self._build_alert_message(vessel_name, mmsi, alert_type, vessel_status)
        
        # 记录预警
        logger.warning(message)
        
        # 更新最后预警时间
        self.last_alerts[mmsi] = datetime.now()
        
        # 这里可以添加其他通知方式，如邮件、短信、钉钉等
        self._send_notification(message)
    
    def _build_alert_message(self, vessel_name: str, mmsi: str, alert_type: AlertType, status: VesselStatus) -> str:
        """构建预警消息"""
        timestamp = status.timestamp.strftime("%Y-%m-%d %H:%M:%S")
        speed = status.speed
        
        base_msg = f"[{timestamp}] 船舶预警 - {vessel_name}({mmsi})"
        
        if alert_type == AlertType.STOPPED:
            return f"{base_msg} - 🛑 停航预警: 当前航速 {speed} 节"
        elif alert_type == AlertType.SLOW_DOWN:
            return f"{base_msg} - ⚠️ 降速预警: 当前航速 {speed} 节"
        elif alert_type == AlertType.SPEED_RECOVERY:
            return f"{base_msg} - ✅ 航速恢复: 当前航速 {speed} 节"
        else:
            return f"{base_msg} - ❌ 数据异常: 当前航速 {speed} 节"
    
    def _send_notification(self, message: str):
        """发送通知（可扩展为邮件、短信等）"""
        # 这里可以实现具体的通知逻辑
        print(f"📢 通知: {message}")
    
    def monitor_vessels(self):
        """监控所有船舶"""
        logger.info("开始监控船舶...")
        
        while True:
            for mmsi, config in self.vessels.items():
                try:
                    # 获取船舶数据
                    current_status = self.get_vessel_data(mmsi)
                    if not current_status:
                        continue
                    
                    # 分析航速变化
                    alert_type = self.analyze_speed_change(mmsi, current_status)
                    
                    # 发送预警
                    if alert_type:
                        self.send_alert(mmsi, alert_type, current_status)
                    
                    # 更新船舶状态
                    self.vessel_status[mmsi] = current_status
                    
                    # 记录状态信息
                    logger.info("船舶 %s: 航速 %s 节, 状态 %s", mmsi, current_status.speed, current_status.status)
                    
                except (ValueError, TypeError, KeyError) as e:
                    logger.error("监控船舶 %s 时发生错误: %s", mmsi, e)
                
                # 根据配置的检查间隔等待
                time.sleep(config.check_interval)
    
    def get_monitoring_summary(self) -> Dict:
        """获取监控摘要"""
        summary = {
            "total_vessels": len(self.vessels),
            "monitored_vessels": [],
            "timestamp": datetime.now().isoformat()
        }
        
        for mmsi, config in self.vessels.items():
            status = self.vessel_status.get(mmsi)
            vessel_info = {
                "mmsi": mmsi,
                "name": config.name,
                "last_speed": status.speed if status else None,
                "last_update": status.timestamp.isoformat() if status else None,
                "status": status.status if status else "unknown"
            }
            summary["monitored_vessels"].append(vessel_info)
        
        return summary


def main():
    """主函数 - 演示如何使用监控系统"""
    monitor = VesselMonitor()
    
    # 添加要监控的船舶
    vessels_to_monitor = [
        VesselConfig(
            mmsi="367560102",
            name="货轮001",
            speed_threshold=1.0,
            slow_down_threshold=5.0,
            normal_speed=12.0,
            check_interval=30,
            alert_cooldown=300
        ),
        VesselConfig(
            mmsi="414281000",
            name="货轮002", 
            speed_threshold=0.5,
            slow_down_threshold=3.0,
            normal_speed=15.0,
            check_interval=60,
            alert_cooldown=600
        )
    ]
    
    for vessel in vessels_to_monitor:
        monitor.add_vessel(vessel)
    
    # 开始监控
    try:
        monitor.monitor_vessels()
    except KeyboardInterrupt:
        logger.info("监控已停止")
        # 输出监控摘要
        summary = monitor.get_monitoring_summary()
        print("\n=== 监控摘要 ===")
        print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()