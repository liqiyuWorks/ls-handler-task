#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Rancher 简单监控脚本
快速查看集群状态，只读操作，不修改任何资源
"""

from rancher_api import RancherAPIClient
from datetime import datetime

def simple_monitor():
    """简单的集群状态监控"""
    
    # 初始化客户端 - 请替换为你的实际Rancher服务器URL
    rancher_url = "http://124.70.16.88:21680"
    client = RancherAPIClient(rancher_url)
    
    print("🔍 Rancher 集群快速状态检查")
    print("=" * 50)
    print(f"⏰ 检查时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    try:
        # 1. 获取基础统计信息
        print("📊 集群概览:")
        
        projects = client.get_projects()
        environments = client.get_environments()
        services = client.get_services()
        containers = client.get_containers()
        hosts = client.get_hosts()
        
        print(f"   📁 项目: {len(projects)}")
        print(f"   🏗️  环境: {len(environments)}")
        print(f"   🚀 服务: {len(services)}")
        print(f"   📦 容器: {len(containers)}")
        print(f"   🖥️  主机: {len(hosts)}")
        print()
        
        # 2. 服务状态统计
        print("🚀 服务状态:")
        service_states = {}
        for service in services:
            state = service.get('state', 'unknown')
            service_states[state] = service_states.get(state, 0) + 1
        
        for state, count in service_states.items():
            icon = {
                'active': '✅',
                'inactive': '⏸️',
                'error': '❌',
                'upgrading': '🔄',
                'removed': '🗑️'
            }.get(state, '❓')
            print(f"   {icon} {state}: {count}")
        print()
        
        # 3. 容器状态统计
        print("📦 容器状态:")
        container_states = {}
        for container in containers:
            state = container.get('state', 'unknown')
            container_states[state] = container_states.get(state, 0) + 1
        
        for state, count in container_states.items():
            icon = {
                'running': '🟢',
                'stopped': '🔴',
                'starting': '🟡',
                'error': '❌',
                'removed': '🗑️'
            }.get(state, '❓')
            print(f"   {icon} {state}: {count}")
        print()
        
        # 4. 主机状态
        print("🖥️  主机状态:")
        active_hosts = [h for h in hosts if h.get('state') == 'active']
        print(f"   ✅ 活跃主机: {len(active_hosts)}/{len(hosts)}")
        
        for host in hosts:
            agent_state = host.get('agentState', 'unknown')
            icon = '✅' if agent_state == 'active' else '❌'
            print(f"   {icon} {host['name']}: {host.get('state', 'N/A')} (Agent: {agent_state})")
        print()
        
        # 5. 异常检测
        print("⚠️  异常检测:")
        error_services = [s for s in services if s.get('state') == 'error']
        error_containers = [c for c in containers if c.get('state') == 'error']
        inactive_hosts = [h for h in hosts if h.get('state') != 'active']
        
        if error_services:
            print(f"   ❌ 异常服务 ({len(error_services)}):")
            for service in error_services[:5]:  # 只显示前5个
                print(f"      - {service['name']} (ID: {service['id']})")
        
        if error_containers:
            print(f"   ❌ 异常容器 ({len(error_containers)}):")
            for container in error_containers[:5]:  # 只显示前5个
                print(f"      - {container['name']} (ID: {container['id']})")
        
        if inactive_hosts:
            print(f"   ❌ 非活跃主机 ({len(inactive_hosts)}):")
            for host in inactive_hosts:
                print(f"      - {host['name']} (状态: {host.get('state', 'N/A')})")
        
        if not (error_services or error_containers or inactive_hosts):
            print("   ✅ 未发现异常，集群状态良好")
        
        print()
        
        # 6. 健康度评分
        total_services = len(services)
        total_containers = len(containers)
        total_hosts = len(hosts)
        
        healthy_services = len([s for s in services if s.get('state') == 'active'])
        running_containers = len([c for c in containers if c.get('state') == 'running'])
        active_hosts = len([h for h in hosts if h.get('state') == 'active'])
        
        service_health = (healthy_services / total_services * 100) if total_services > 0 else 100
        container_health = (running_containers / total_containers * 100) if total_containers > 0 else 100
        host_health = (active_hosts / total_hosts * 100) if total_hosts > 0 else 100
        
        overall_health = (service_health + container_health + host_health) / 3
        
        print("📈 集群健康度:")
        print(f"   🚀 服务健康度: {service_health:.1f}%")
        print(f"   📦 容器健康度: {container_health:.1f}%")
        print(f"   🖥️  主机健康度: {host_health:.1f}%")
        print(f"   🏆 总体健康度: {overall_health:.1f}%")
        
        # 健康度等级
        if overall_health >= 95:
            health_status = "🟢 优秀"
        elif overall_health >= 80:
            health_status = "🟡 良好"
        elif overall_health >= 60:
            health_status = "🟠 一般"
        else:
            health_status = "🔴 需要关注"
        
        print(f"   📊 健康等级: {health_status}")
        
    except Exception as e:
        print(f"❌ 监控检查失败: {e}")
        return False
    
    print("\n" + "=" * 50)
    print("✅ 监控检查完成")
    print("⚠️  注意: 本脚本仅进行只读查看，不会修改任何资源")
    return True

if __name__ == "__main__":
    simple_monitor()
