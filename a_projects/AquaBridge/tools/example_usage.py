#!/usr/bin/env python3
"""
AquaBridge 使用示例
演示如何在代码中使用不同的浏览器配置
"""

from playwright.sync_api import sync_playwright
from data_scraper import DataScraper


def example_1_default():
    """示例 1: 使用默认配置（生产环境 Chromium）"""
    print("=" * 60)
    print("示例 1: 默认配置（生产环境 Chromium）")
    print("=" * 60)
    
    with sync_playwright() as playwright:
        # 默认使用 Chromium，无头模式
        scraper = DataScraper()
        scraper.create_browser(playwright)
        
        print("✓ 浏览器已启动")
        print(f"  类型: {scraper.browser_config.browser_type.value}")
        print(f"  无头模式: {scraper.browser_config.headless}")
        
        scraper.cleanup()
        print("✓ 清理完成\n")


def example_2_firefox():
    """示例 2: 使用 Firefox 浏览器"""
    print("=" * 60)
    print("示例 2: 指定 Firefox 浏览器")
    print("=" * 60)
    
    with sync_playwright() as playwright:
        # 指定使用 Firefox
        scraper = DataScraper(browser_type="firefox")
        scraper.create_browser(playwright)
        
        print("✓ 浏览器已启动")
        print(f"  类型: {scraper.browser_config.browser_type.value}")
        print(f"  无头模式: {scraper.browser_config.headless}")
        
        scraper.cleanup()
        print("✓ 清理完成\n")


def example_3_testing_env():
    """示例 3: 使用测试环境配置"""
    print("=" * 60)
    print("示例 3: 测试环境配置（自动使用 Firefox）")
    print("=" * 60)
    
    with sync_playwright() as playwright:
        # 使用测试环境配置（自动选择 Firefox）
        scraper = DataScraper(environment="testing")
        scraper.create_browser(playwright)
        
        print("✓ 浏览器已启动")
        print(f"  类型: {scraper.browser_config.browser_type.value}")
        print(f"  无头模式: {scraper.browser_config.headless}")
        
        scraper.cleanup()
        print("✓ 清理完成\n")


def example_4_headless_false():
    """示例 4: 显示浏览器窗口（调试模式）"""
    print("=" * 60)
    print("示例 4: 显示浏览器窗口（调试）")
    print("=" * 60)
    print("提示: 浏览器窗口将会显示，请在3秒后手动关闭或等待自动关闭")
    print()
    
    with sync_playwright() as playwright:
        import time
        
        # 显示浏览器窗口
        scraper = DataScraper(headless=False)
        scraper.create_browser(playwright)
        
        print("✓ 浏览器已启动（窗口模式）")
        print(f"  类型: {scraper.browser_config.browser_type.value}")
        print(f"  无头模式: {scraper.browser_config.headless}")
        
        # 创建一个页面用于演示
        page = scraper.context.new_page()
        page.goto("https://www.example.com")
        print("✓ 已访问示例网站")
        
        # 等待一会儿让用户看到
        print("  等待 3 秒...")
        time.sleep(3)
        
        scraper.cleanup()
        print("✓ 清理完成\n")


def example_5_complete_usage():
    """示例 5: 完整的数据抓取示例（模拟）"""
    print("=" * 60)
    print("示例 5: 完整使用流程（不实际抓取数据）")
    print("=" * 60)
    
    with sync_playwright() as playwright:
        # 创建抓取器
        scraper = DataScraper(
            browser_type="chromium",
            headless=True
        )
        
        print("1. 创建抓取器")
        print(f"   浏览器: {scraper.browser_config.browser_type.value}")
        
        # 创建浏览器
        scraper.create_browser(playwright)
        print("2. 浏览器已启动")
        
        # 创建页面
        scraper.page = scraper.context.new_page()
        scraper.page.set_default_timeout(12000)
        print("3. 页面已创建")
        
        # 访问示例网站
        scraper.page.goto("https://www.example.com")
        title = scraper.page.title()
        print(f"4. 已访问网站: {title}")
        
        # 清理
        scraper.cleanup()
        print("5. 清理完成\n")


def example_6_environment_variable():
    """示例 6: 使用环境变量配置"""
    print("=" * 60)
    print("示例 6: 环境变量配置")
    print("=" * 60)
    
    import os
    
    # 设置环境变量（仅在当前进程中有效）
    os.environ["BROWSER_TYPE"] = "chromium"
    os.environ["ENVIRONMENT"] = "production"
    
    print("已设置环境变量:")
    print(f"  BROWSER_TYPE: {os.environ.get('BROWSER_TYPE')}")
    print(f"  ENVIRONMENT: {os.environ.get('ENVIRONMENT')}")
    print()
    
    with sync_playwright() as playwright:
        # 不指定参数，从环境变量读取
        scraper = DataScraper()
        scraper.create_browser(playwright)
        
        print("✓ 浏览器已启动（使用环境变量配置）")
        print(f"  类型: {scraper.browser_config.browser_type.value}")
        
        scraper.cleanup()
        print("✓ 清理完成\n")


def main():
    """运行所有示例"""
    print("\n" + "#" * 60)
    print("  AquaBridge 使用示例")
    print("#" * 60 + "\n")
    
    try:
        # 示例 1: 默认配置
        example_1_default()
        
        # 示例 2: Firefox
        print("提示: 如果 Firefox 未安装，示例 2 和 3 将失败")
        print("      请运行: playwright install firefox")
        print()
        
        try:
            example_2_firefox()
        except Exception as e:
            print(f"⚠ Firefox 示例跳过: {e}\n")
        
        # 示例 3: 测试环境
        try:
            example_3_testing_env()
        except Exception as e:
            print(f"⚠ 测试环境示例跳过: {e}\n")
        
        # 示例 4: 显示窗口
        answer = input("是否运行显示窗口示例？(y/n): ").lower()
        if answer == 'y':
            example_4_headless_false()
        else:
            print("跳过显示窗口示例\n")
        
        # 示例 5: 完整流程
        example_5_complete_usage()
        
        # 示例 6: 环境变量
        example_6_environment_variable()
        
        print("=" * 60)
        print("  所有示例运行完成！")
        print("=" * 60)
        print()
        print("更多信息:")
        print("  - 查看 README.md 了解基本使用")
        print("  - 查看 BROWSER_CONFIGURATION.md 了解详细配置")
        print("  - 查看 BROWSER_QUICK_REFERENCE.md 快速参考")
        print()
        
    except KeyboardInterrupt:
        print("\n\n用户中断")
    except Exception as e:
        print(f"\n错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()

