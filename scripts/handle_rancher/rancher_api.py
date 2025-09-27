#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Rancher API Client
Rancher v1.6.30, Cattle v0.183.83
Author: Generated for ls-handler-task
"""

import requests
import json
import logging
from typing import Dict, List, Optional, Any
from urllib.parse import urljoin
import time


class RancherAPIClient:
    """
    Rancher API客户端，用于与Rancher v1.6.30进行交互
    """
    
    def __init__(self, rancher_url: str, access_key: str = "C5EA6259A878D3404231", 
                 secret_key: str = "Sy8e4rAxitsqNqzKaAfP7D4f3B1NWdEdttnsBF3X"):
        """
        初始化Rancher API客户端
        
        Args:
            rancher_url: Rancher服务器URL (例如: http://rancher.example.com:8080)
            access_key: API访问密钥
            secret_key: API密钥
        """
        self.rancher_url = rancher_url.rstrip('/')
        self.access_key = access_key
        self.secret_key = secret_key
        self.api_version = "v1"
        self.base_url = f"{self.rancher_url}/{self.api_version}"
        
        # 配置日志
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        
        # 创建session
        self.session = requests.Session()
        self.session.auth = (self.access_key, self.secret_key)
        self.session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })
    
    def _make_request(self, method: str, endpoint: str, data: Optional[Dict] = None, 
                     params: Optional[Dict] = None) -> Dict:
        """
        发送API请求
        
        Args:
            method: HTTP方法 (GET, POST, PUT, DELETE)
            endpoint: API端点
            data: 请求数据
            params: 查询参数
            
        Returns:
            API响应数据
        """
        url = urljoin(self.base_url + '/', endpoint.lstrip('/'))
        
        try:
            if method.upper() == 'GET':
                response = self.session.get(url, params=params)
            elif method.upper() == 'POST':
                response = self.session.post(url, json=data, params=params)
            elif method.upper() == 'PUT':
                response = self.session.put(url, json=data, params=params)
            elif method.upper() == 'DELETE':
                response = self.session.delete(url, params=params)
            else:
                raise ValueError(f"不支持的HTTP方法: {method}")
            
            response.raise_for_status()
            return response.json() if response.content else {}
            
        except requests.exceptions.RequestException as e:
            self.logger.error(f"API请求失败: {e}")
            raise
    
    def get_projects(self) -> List[Dict]:
        """获取所有项目(环境)列表"""
        return self._make_request('GET', '/projects')['data']
    
    def get_project(self, project_id: str) -> Dict:
        """获取特定项目信息"""
        return self._make_request('GET', f'/projects/{project_id}')
    
    def create_project(self, name: str, description: str = "") -> Dict:
        """
        创建新项目
        
        Args:
            name: 项目名称
            description: 项目描述
        """
        data = {
            "name": name,
            "description": description
        }
        return self._make_request('POST', '/projects', data)
    
    def get_environments(self, project_id: Optional[str] = None) -> List[Dict]:
        """获取环境列表"""
        endpoint = '/environments'
        params = {'projectId': project_id} if project_id else None
        return self._make_request('GET', endpoint, params=params)['data']
    
    def get_services(self, environment_id: Optional[str] = None) -> List[Dict]:
        """获取服务列表"""
        endpoint = '/services'
        params = {'environmentId': environment_id} if environment_id else None
        return self._make_request('GET', endpoint, params=params)['data']
    
    def get_service(self, service_id: str) -> Dict:
        """获取特定服务信息"""
        return self._make_request('GET', f'/services/{service_id}')
    
    def create_service(self, environment_id: str, name: str, image: str, 
                      scale: int = 1, **kwargs) -> Dict:
        """
        创建服务
        
        Args:
            environment_id: 环境ID
            name: 服务名称
            image: Docker镜像
            scale: 服务实例数量
            **kwargs: 其他服务配置参数
        """
        data = {
            "name": name,
            "environmentId": environment_id,
            "launchConfig": {
                "imageUuid": f"docker:{image}",
                **kwargs
            },
            "scale": scale
        }
        return self._make_request('POST', '/services', data)
    
    def upgrade_service(self, service_id: str, image: str, **kwargs) -> Dict:
        """
        升级服务
        
        Args:
            service_id: 服务ID
            image: 新的Docker镜像
            **kwargs: 其他配置参数
        """
        service = self.get_service(service_id)
        
        data = {
            "inServiceStrategy": {
                "launchConfig": {
                    "imageUuid": f"docker:{image}",
                    **service['launchConfig'],
                    **kwargs
                }
            }
        }
        return self._make_request('POST', f'/services/{service_id}?action=upgrade', data)
    
    def finish_upgrade_service(self, service_id: str) -> Dict:
        """完成服务升级"""
        return self._make_request('POST', f'/services/{service_id}?action=finishupgrade')
    
    def rollback_service(self, service_id: str) -> Dict:
        """回滚服务"""
        return self._make_request('POST', f'/services/{service_id}?action=rollback')
    
    def restart_service(self, service_id: str) -> Dict:
        """重启服务"""
        return self._make_request('POST', f'/services/{service_id}?action=restart')
    
    def scale_service(self, service_id: str, scale: int) -> Dict:
        """
        扩缩容服务
        
        Args:
            service_id: 服务ID
            scale: 目标实例数量
        """
        service = self.get_service(service_id)
        service['scale'] = scale
        return self._make_request('PUT', f'/services/{service_id}', service)
    
    def delete_service(self, service_id: str) -> Dict:
        """删除服务"""
        return self._make_request('DELETE', f'/services/{service_id}')
    
    def get_containers(self, service_id: Optional[str] = None) -> List[Dict]:
        """获取容器列表"""
        endpoint = '/containers'
        params = {'serviceId': service_id} if service_id else None
        return self._make_request('GET', endpoint, params=params)['data']
    
    def get_container(self, container_id: str) -> Dict:
        """获取特定容器信息"""
        return self._make_request('GET', f'/containers/{container_id}')
    
    def restart_container(self, container_id: str) -> Dict:
        """重启容器"""
        return self._make_request('POST', f'/containers/{container_id}?action=restart')
    
    def stop_container(self, container_id: str) -> Dict:
        """停止容器"""
        return self._make_request('POST', f'/containers/{container_id}?action=stop')
    
    def start_container(self, container_id: str) -> Dict:
        """启动容器"""
        return self._make_request('POST', f'/containers/{container_id}?action=start')
    
    def get_stacks(self, environment_id: Optional[str] = None) -> List[Dict]:
        """获取应用栈列表"""
        endpoint = '/environments'
        params = {'environmentId': environment_id} if environment_id else None
        return self._make_request('GET', endpoint, params=params)['data']
    
    def create_stack(self, environment_id: str, name: str, 
                    docker_compose: str, rancher_compose: str = "") -> Dict:
        """
        创建应用栈
        
        Args:
            environment_id: 环境ID
            name: 栈名称
            docker_compose: docker-compose.yml内容
            rancher_compose: rancher-compose.yml内容
        """
        data = {
            "name": name,
            "environment": {"environmentId": environment_id},
            "dockerCompose": docker_compose,
            "rancherCompose": rancher_compose
        }
        return self._make_request('POST', '/environments', data)
    
    def get_hosts(self) -> List[Dict]:
        """获取主机列表"""
        return self._make_request('GET', '/hosts')['data']
    
    def get_host(self, host_id: str) -> Dict:
        """获取特定主机信息"""
        return self._make_request('GET', f'/hosts/{host_id}')
    
    def wait_for_service_active(self, service_id: str, timeout: int = 300) -> bool:
        """
        等待服务变为active状态
        
        Args:
            service_id: 服务ID
            timeout: 超时时间(秒)
            
        Returns:
            是否成功变为active状态
        """
        start_time = time.time()
        while time.time() - start_time < timeout:
            service = self.get_service(service_id)
            state = service.get('state', '')
            
            if state == 'active':
                return True
            elif state in ['removed', 'error']:
                return False
            
            time.sleep(5)
        
        return False
    
    def get_service_logs(self, service_id: str, lines: int = 100) -> str:
        """
        获取服务日志
        
        Args:
            service_id: 服务ID
            lines: 日志行数
            
        Returns:
            日志内容
        """
        containers = self.get_containers(service_id)
        logs = []
        
        for container in containers:
            container_id = container['id']
            try:
                # 注意: Rancher v1.6的日志API可能需要WebSocket连接
                # 这里提供基本的REST API调用示例
                log_response = self._make_request('GET', f'/containers/{container_id}/logs', 
                                                params={'lines': lines})
                logs.append(f"=== Container {container['name']} ===")
                logs.append(log_response.get('data', ''))
            except Exception as e:
                self.logger.error(f"获取容器 {container_id} 日志失败: {e}")
        
        return '\n'.join(logs)


# 使用示例
if __name__ == "__main__":
    # 初始化客户端 - 请替换为你的Rancher服务器URL
    rancher_url = "http://your-rancher-server:8080"  # 请修改为实际的Rancher URL
    client = RancherAPIClient(rancher_url)
    
    try:
        # 获取项目列表
        print("=== 获取项目列表 ===")
        projects = client.get_projects()
        for project in projects:
            print(f"项目: {project['name']} (ID: {project['id']})")
        
        # 获取环境列表
        print("\n=== 获取环境列表 ===")
        environments = client.get_environments()
        for env in environments:
            print(f"环境: {env['name']} (ID: {env['id']})")
        
        # 获取服务列表
        print("\n=== 获取服务列表 ===")
        services = client.get_services()
        for service in services:
            print(f"服务: {service['name']} (ID: {service['id']}, 状态: {service['state']})")
        
        # 获取主机列表
        print("\n=== 获取主机列表 ===")
        hosts = client.get_hosts()
        for host in hosts:
            print(f"主机: {host['name']} (ID: {host['id']}, 状态: {host['state']})")
            
    except Exception as e:
        print(f"API调用失败: {e}")
        
    # 更多使用示例:
    """
    # 创建服务示例
    service = client.create_service(
        environment_id="1e1",
        name="my-web-service",
        image="nginx:latest",
        scale=2,
        ports=["80:80/tcp"]
    )
    
    # 升级服务示例
    client.upgrade_service("1s1", "nginx:1.20")
    
    # 等待服务激活
    if client.wait_for_service_active("1s1"):
        print("服务升级成功")
        client.finish_upgrade_service("1s1")
    
    # 扩缩容服务
    client.scale_service("1s1", 5)
    
    # 重启服务
    client.restart_service("1s1")
    """