#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Rancher API查看和监控示例
仅用于查看集群状态，不进行任何实际操作
"""

from rancher_api import RancherAPIClient
import time
from datetime import datetime

def main():
    # 初始化客户端 - 请替换为你的实际Rancher服务器URL
    rancher_url = "http://your-rancher-server:8080"
    client = RancherAPIClient(rancher_url)
    
    print("=== Rancher 集群监控和查看示例 ===")
    print(f"监控时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    # 示例1: 查看集群总体状态
    print("1. 集群总体状态")
    try:
        projects = client.get_projects()
        print(f"   📁 项目总数: {len(projects)}")
        
        environments = client.get_environments()
        print(f"   🏗️  环境总数: {len(environments)}")
        
        services = client.get_services()
        print(f"   🚀 服务总数: {len(services)}")
        
        hosts = client.get_hosts()
        print(f"   🖥️  主机总数: {len(hosts)}")
        
    except Exception as e:
        print(f"   ❌ 错误: {e}")
    
    print("\n" + "="*60 + "\n")
    
    # 示例2: 详细查看项目信息
    print("2. 项目详细信息")
    try:
        projects = client.get_projects()
        if projects:
            for i, project in enumerate(projects[:3], 1):  # 只显示前3个项目
                print(f"   项目 {i}:")
                print(f"     📛 名称: {project['name']}")
                print(f"     🆔 ID: {project['id']}")
                print(f"     📝 描述: {project.get('description', '无描述')}")
                print(f"     📊 状态: {project.get('state', 'N/A')}")
                print(f"     📅 创建时间: {project.get('created', 'N/A')}")
                print()
        else:
            print("   没有找到项目")
            
    except Exception as e:
        print(f"   ❌ 错误: {e}")
    
    print("=" * 60 + "\n")
    
    # 示例3: 环境状态监控
    print("3. 环境状态监控")
    try:
        environments = client.get_environments()
        if environments:
            print(f"   找到 {len(environments)} 个环境:")
            for env in environments:
                print(f"     🏗️  {env['name']} (ID: {env['id']})")
                print(f"        状态: {env.get('state', 'N/A')}")
                print(f"        健康状态: {env.get('healthState', 'N/A')}")
                print(f"        创建时间: {env.get('created', 'N/A')}")
                print()
        else:
            print("   没有找到环境")
            
    except Exception as e:
        print(f"   ❌ 错误: {e}")
    
    print("=" * 60 + "\n")
    
    # 示例4: 服务状态详细监控
    print("4. 服务状态详细监控")
    try:
        services = client.get_services()
        if services:
            print(f"   找到 {len(services)} 个服务:")
            
            # 按状态分类统计
            status_count = {}
            for service in services:
                status = service.get('state', 'unknown')
                status_count[status] = status_count.get(status, 0) + 1
            
            print("   📊 服务状态统计:")
            for status, count in status_count.items():
                status_icon = {
                    'active': '✅',
                    'inactive': '⏸️',
                    'upgrading': '🔄',
                    'error': '❌',
                    'removed': '🗑️'
                }.get(status, '❓')
                print(f"     {status_icon} {status}: {count} 个服务")
            
            print("\n   📋 服务详细信息 (前5个):")
            for i, service in enumerate(services[:5], 1):
                print(f"     服务 {i}: {service['name']}")
                print(f"       🆔 ID: {service['id']}")
                print(f"       📊 状态: {service.get('state', 'N/A')}")
                print(f"       🏥 健康状态: {service.get('healthState', 'N/A')}")
                print(f"       📏 实例数: {service.get('scale', 'N/A')}")
                print(f"       🖼️  镜像: {service.get('launchConfig', {}).get('imageUuid', 'N/A')}")
                print(f"       🏗️  环境: {service.get('environmentId', 'N/A')}")
                print()
        else:
            print("   没有找到服务")
            
    except Exception as e:
        print(f"   ❌ 错误: {e}")
    
    print("=" * 60 + "\n")
    
    # 示例5: 容器状态监控
    print("5. 容器状态监控")
    try:
        containers = client.get_containers()
        if containers:
            print(f"   找到 {len(containers)} 个容器")
            
            # 按状态分类
            container_status = {}
            for container in containers:
                status = container.get('state', 'unknown')
                container_status[status] = container_status.get(status, 0) + 1
            
            print("   📊 容器状态统计:")
            for status, count in container_status.items():
                status_icon = {
                    'running': '🟢',
                    'stopped': '🔴', 
                    'starting': '🟡',
                    'error': '❌',
                    'removed': '🗑️'
                }.get(status, '❓')
                print(f"     {status_icon} {status}: {count} 个容器")
            
            print("\n   📋 容器详细信息 (前3个):")
            for i, container in enumerate(containers[:3], 1):
                print(f"     容器 {i}: {container['name']}")
                print(f"       🆔 ID: {container['id']}")
                print(f"       📊 状态: {container.get('state', 'N/A')}")
                print(f"       🖼️  镜像: {container.get('imageUuid', 'N/A')}")
                print(f"       🖥️  主机: {container.get('hostId', 'N/A')}")
                print(f"       📅 创建时间: {container.get('created', 'N/A')}")
                print()
        else:
            print("   没有找到容器")
            
    except Exception as e:
        print(f"   ❌ 错误: {e}")
    
    print("=" * 60 + "\n")
    
    # 示例6: 主机状态监控
    print("6. 主机状态监控")
    try:
        hosts = client.get_hosts()
        if hosts:
            print(f"   找到 {len(hosts)} 个主机:")
            
            for i, host in enumerate(hosts, 1):
                print(f"     主机 {i}: {host['name']}")
                print(f"       🆔 ID: {host['id']}")
                print(f"       📊 状态: {host.get('state', 'N/A')}")
                print(f"       🖥️  代理状态: {host.get('agentState', 'N/A')}")
                print(f"       🏷️  标签: {host.get('labels', {})}")
                print(f"       💾 内存: {host.get('info', {}).get('memoryInfo', {}).get('memTotal', 'N/A')}")
                print(f"       📅 创建时间: {host.get('created', 'N/A')}")
                print()
        else:
            print("   没有找到主机")
            
    except Exception as e:
        print(f"   ❌ 错误: {e}")
    
    print("=" * 60 + "\n")
    
    # 示例7: 服务日志查看 (只读取，不修改)
    print("7. 服务日志查看")
    try:
        services = client.get_services()
        if services:
            # 选择第一个active状态的服务
            active_service = None
            for service in services:
                if service.get('state') == 'active':
                    active_service = service
                    break
            
            if active_service:
                service_name = active_service['name']
                service_id = active_service['id']
                
                print(f"   📋 查看服务日志: {service_name}")
                print(f"   🆔 服务ID: {service_id}")
                
                # 获取服务的容器
                containers = client.get_containers(service_id)
                if containers:
                    print(f"   📦 该服务有 {len(containers)} 个容器")
                    for container in containers[:2]:  # 只显示前2个容器
                        print(f"     容器: {container['name']} - 状态: {container.get('state', 'N/A')}")
                else:
                    print("   该服务没有运行中的容器")
            else:
                print("   没有找到active状态的服务")
                
        else:
            print("   没有找到服务")
            
    except Exception as e:
        print(f"   ❌ 错误: {e}")
    
    print("=" * 60)
    print("✅ 集群监控查看完成!")
    print("⚠️  注意: 本示例仅进行查看操作，不会修改任何现有资源")


def resource_usage_monitoring():
    """资源使用情况监控"""
    rancher_url = "http://your-rancher-server:8080"
    client = RancherAPIClient(rancher_url)
    
    print("=== 资源使用情况监控 ===\n")
    
    try:
        # 获取所有服务和容器的资源使用统计
        services = client.get_services()
        containers = client.get_containers()
        hosts = client.get_hosts()
        
        print("📊 集群资源概览:")
        print(f"   🏗️  总环境数: {len(client.get_environments())}")
        print(f"   🚀 总服务数: {len(services)}")
        print(f"   📦 总容器数: {len(containers)}")
        print(f"   🖥️  总主机数: {len(hosts)}")
        
        # 分析服务分布
        print("\n📋 服务按环境分布:")
        env_services = {}
        for service in services:
            env_id = service.get('environmentId', 'unknown')
            if env_id not in env_services:
                env_services[env_id] = []
            env_services[env_id].append(service)
        
        environments = client.get_environments()
        env_name_map = {env['id']: env['name'] for env in environments}
        
        for env_id, env_services_list in env_services.items():
            env_name = env_name_map.get(env_id, f'Unknown({env_id})')
            print(f"   🏗️  {env_name}: {len(env_services_list)} 个服务")
        
        # 分析容器分布
        print("\n📦 容器按主机分布:")
        host_containers = {}
        for container in containers:
            host_id = container.get('hostId', 'unknown')
            if host_id not in host_containers:
                host_containers[host_id] = []
            host_containers[host_id].append(container)
        
        host_name_map = {host['id']: host['name'] for host in hosts}
        
        for host_id, host_containers_list in host_containers.items():
            host_name = host_name_map.get(host_id, f'Unknown({host_id})')
            running_count = sum(1 for c in host_containers_list if c.get('state') == 'running')
            print(f"   🖥️  {host_name}: {len(host_containers_list)} 个容器 ({running_count} 运行中)")
        
    except Exception as e:
        print(f"❌ 资源监控失败: {e}")


def service_health_check():
    """服务健康状态检查"""
    rancher_url = "http://your-rancher-server:8080"
    client = RancherAPIClient(rancher_url)
    
    print("=== 服务健康状态检查 ===\n")
    
    try:
        services = client.get_services()
        
        if not services:
            print("没有找到任何服务")
            return
        
        print("🏥 服务健康状态报告:")
        
        healthy_count = 0
        unhealthy_count = 0
        unknown_count = 0
        
        for service in services:
            name = service['name']
            state = service.get('state', 'unknown')
            health_state = service.get('healthState', 'unknown')
            scale = service.get('scale', 0)
            
            # 判断健康状态
            if state == 'active' and health_state == 'healthy':
                status_icon = '✅'
                healthy_count += 1
            elif state in ['error', 'removed'] or health_state == 'unhealthy':
                status_icon = '❌'
                unhealthy_count += 1
            else:
                status_icon = '⚠️'
                unknown_count += 1
            
            print(f"   {status_icon} {name}")
            print(f"      状态: {state} | 健康: {health_state} | 实例: {scale}")
            
            # 检查服务的容器状态
            try:
                containers = client.get_containers(service['id'])
                running_containers = [c for c in containers if c.get('state') == 'running']
                print(f"      容器: {len(running_containers)}/{len(containers)} 运行中")
            except:
                print(f"      容器: 无法获取信息")
            print()
        
        print("📊 健康状态汇总:")
        print(f"   ✅ 健康服务: {healthy_count}")
        print(f"   ❌ 异常服务: {unhealthy_count}")
        print(f"   ⚠️  未知状态: {unknown_count}")
        
        health_percentage = (healthy_count / len(services)) * 100 if services else 0
        print(f"   📈 整体健康率: {health_percentage:.1f}%")
        
    except Exception as e:
        print(f"❌ 健康检查失败: {e}")


def continuous_monitoring():
    """持续监控示例"""
    rancher_url = "http://your-rancher-server:8080"
    client = RancherAPIClient(rancher_url)
    
    print("=== 持续监控示例 ===")
    print("⚠️  这是一个监控循环示例，实际使用时请根据需要调整监控间隔")
    print("⚠️  此示例只运行3次，每次间隔10秒\n")
    
    for i in range(3):
        try:
            print(f"📊 第 {i+1} 次监控 - {datetime.now().strftime('%H:%M:%S')}")
            
            # 快速状态检查
            services = client.get_services()
            containers = client.get_containers()
            
            active_services = [s for s in services if s.get('state') == 'active']
            running_containers = [c for c in containers if c.get('state') == 'running']
            
            print(f"   🚀 活跃服务: {len(active_services)}/{len(services)}")
            print(f"   📦 运行容器: {len(running_containers)}/{len(containers)}")
            
            # 检查是否有异常
            error_services = [s for s in services if s.get('state') == 'error']
            if error_services:
                print(f"   ❌ 发现 {len(error_services)} 个异常服务:")
                for service in error_services:
                    print(f"      - {service['name']}")
            else:
                print("   ✅ 所有服务状态正常")
            
            if i < 2:  # 不是最后一次
                print("   ⏳ 等待10秒...")
                time.sleep(10)
            
        except Exception as e:
            print(f"   ❌ 监控失败: {e}")
        
        print()
    
    print("✅ 监控示例完成")


if __name__ == "__main__":
    # 运行基础监控示例
    main()
    
    print("\n" + "="*70 + "\n")
    
    # 运行资源使用监控
    resource_usage_monitoring()
    
    print("\n" + "="*70 + "\n")
    
    # 运行服务健康检查
    service_health_check()
    
    print("\n" + "="*70 + "\n")
    
    # 运行持续监控示例
    continuous_monitoring()
