"""
AquaBridge 综合测试套件
测试所有模块的功能和正确性
"""
import sys
import traceback
from datetime import datetime

def print_section(title):
    """打印章节标题"""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}\n")

def test_imports():
    """测试1: 验证所有依赖导入"""
    print_section("测试 1: 验证依赖导入")
    
    try:
        from playwright.sync_api import sync_playwright, Playwright, FrameLocator
        print("✓ Playwright 导入成功")
    except ImportError as e:
        print(f"✗ Playwright 导入失败: {e}")
        return False
    
    try:
        import json
        print("✓ JSON 模块可用")
    except ImportError as e:
        print(f"✗ JSON 模块导入失败: {e}")
        return False
    
    try:
        from page_config import PageConfig, get_page_config, get_page_info
        print("✓ page_config 模块导入成功")
    except ImportError as e:
        print(f"✗ page_config 模块导入失败: {e}")
        return False
    
    try:
        from data_scraper import DataScraper
        print("✓ data_scraper 模块导入成功")
    except ImportError as e:
        print(f"✗ data_scraper 模块导入失败: {e}")
        return False
    
    print("\n✓ 所有依赖导入成功")
    return True

def test_page_config():
    """测试2: 验证页面配置"""
    print_section("测试 2: 验证页面配置")
    
    try:
        from page_config import get_page_config, get_page_info, list_available_pages
        
        # 测试获取所有页面信息
        pages = list_available_pages()
        print(f"✓ 可用页面数量: {len(pages)}")
        print(f"  页面列表: {pages}")
        
        # 测试获取页面信息
        page_info = get_page_info()
        print(f"\n✓ 页面信息:")
        for key, info in page_info.items():
            print(f"  - {key}:")
            print(f"      名称: {info['name']}")
            print(f"      描述: {info['description']}")
        
        # 测试获取具体页面配置
        for page_key in pages:
            config = get_page_config(page_key)
            if config:
                print(f"\n✓ {page_key} 配置验证:")
                print(f"  - 导航步骤数: {len(config.navigation_path)}")
                print(f"  - 查询按钮选择器数: {len(config.query_button_selectors)}")
                print(f"  - 数据提取配置: {config.data_extraction_config}")
            else:
                print(f"✗ {page_key} 配置获取失败")
                return False
        
        print("\n✓ 页面配置验证成功")
        return True
    
    except Exception as e:
        print(f"✗ 页面配置验证失败: {e}")
        traceback.print_exc()
        return False

def test_data_scraper_init():
    """测试3: 验证DataScraper初始化"""
    print_section("测试 3: 验证 DataScraper 初始化")
    
    try:
        from data_scraper import DataScraper
        
        # 测试创建实例
        scraper = DataScraper(headless=True)
        print("✓ DataScraper 实例创建成功")
        
        # 验证浏览器配置属性
        assert hasattr(scraper, 'browser_config'), "应该有 browser_config 属性"
        print("✓ browser_config 属性存在")
        
        assert scraper.browser_config.headless == True, "headless 配置设置错误"
        print("✓ headless 配置正确")
        
        assert scraper.browser is None, "browser 应该初始化为 None"
        print("✓ browser 属性初始化正确")
        
        assert scraper.context is None, "context 应该初始化为 None"
        print("✓ context 属性初始化正确")
        
        assert scraper.page is None, "page 应该初始化为 None"
        print("✓ page 属性初始化正确")
        
        # 测试浏览器类型参数
        scraper2 = DataScraper(browser_type="firefox")
        assert scraper2.browser_config.browser_type.value == "firefox"
        print("✓ 浏览器类型参数工作正常")
        
        # 测试环境参数
        scraper3 = DataScraper(environment="testing")
        assert scraper3.browser_config.browser_type.value == "firefox"
        print("✓ 环境参数工作正常")
        
        print("\n✓ DataScraper 初始化验证成功")
        return True
    
    except Exception as e:
        print(f"✗ DataScraper 初始化验证失败: {e}")
        traceback.print_exc()
        return False

def test_browser_creation():
    """测试4: 验证浏览器创建"""
    print_section("测试 4: 验证浏览器创建")
    
    try:
        from playwright.sync_api import sync_playwright
        from data_scraper import DataScraper
        
        with sync_playwright() as playwright:
            scraper = DataScraper(headless=True)
            print("✓ DataScraper 实例创建")
            
            scraper.create_browser(playwright)
            print("✓ 浏览器创建成功")
            
            # 验证浏览器对象
            assert scraper.browser is not None, "browser 应该已创建"
            print("✓ browser 对象已创建")
            
            assert scraper.context is not None, "context 应该已创建"
            print("✓ context 对象已创建")
            
            # 创建测试页面
            scraper.page = scraper.context.new_page()
            print("✓ 测试页面创建成功")
            
            # 清理
            scraper.cleanup()
            print("✓ 清理成功")
        
        print("\n✓ 浏览器创建验证成功")
        return True
    
    except Exception as e:
        print(f"✗ 浏览器创建验证失败: {e}")
        traceback.print_exc()
        return False

def test_data_scraper_methods():
    """测试5: 验证DataScraper方法"""
    print_section("测试 5: 验证 DataScraper 方法")
    
    try:
        from data_scraper import DataScraper
        
        scraper = DataScraper()
        
        # 验证方法存在
        methods = [
            'create_browser',
            'try_click',
            'extract_table_data',
            'navigate_to_page',
            'find_target_frame',
            'query_data',
            'scrape_page_data',
            'save_data',
            'cleanup'
        ]
        
        for method_name in methods:
            assert hasattr(scraper, method_name), f"缺少方法: {method_name}"
            assert callable(getattr(scraper, method_name)), f"{method_name} 不可调用"
            print(f"✓ 方法 {method_name} 存在且可调用")
        
        print("\n✓ DataScraper 方法验证成功")
        return True
    
    except Exception as e:
        print(f"✗ DataScraper 方法验证失败: {e}")
        traceback.print_exc()
        return False

def test_original_script():
    """测试6: 测试原始脚本结构"""
    print_section("测试 6: 验证原始脚本")
    
    try:
        # 导入并检查原始脚本的函数
        import test_case_chromium as original
        
        functions = [
            'extract_table_data',
            'create_browser',
            'try_click',
            'save_data',
            'save_data_as_txt',
            'run'
        ]
        
        for func_name in functions:
            assert hasattr(original, func_name), f"原始脚本缺少函数: {func_name}"
            assert callable(getattr(original, func_name)), f"{func_name} 不可调用"
            print(f"✓ 函数 {func_name} 存在且可调用")
        
        print("\n✓ 原始脚本结构验证成功")
        return True
    
    except Exception as e:
        print(f"✗ 原始脚本验证失败: {e}")
        traceback.print_exc()
        return False

def test_dry_run():
    """测试7: 干运行测试（不实际访问网站）"""
    print_section("测试 7: 干运行测试")
    
    try:
        from playwright.sync_api import sync_playwright
        from data_scraper import DataScraper
        from page_config import get_page_config
        
        with sync_playwright() as playwright:
            scraper = DataScraper(headless=True)
            scraper.create_browser(playwright)
            scraper.page = scraper.context.new_page()
            scraper.page.set_default_timeout(5000)
            
            print("✓ 浏览器环境设置完成")
            
            # 测试访问一个简单的页面
            try:
                scraper.page.goto("about:blank")
                print("✓ 页面导航功能正常")
            except Exception as e:
                print(f"✗ 页面导航失败: {e}")
                return False
            
            # 测试配置读取
            config = get_page_config("p4tc_spot_decision")
            if config:
                print(f"✓ 读取到配置: {config.name}")
            else:
                print("✗ 配置读取失败")
                return False
            
            scraper.cleanup()
            print("✓ 清理完成")
        
        print("\n✓ 干运行测试成功")
        return True
    
    except Exception as e:
        print(f"✗ 干运行测试失败: {e}")
        traceback.print_exc()
        return False

def main():
    """运行所有测试"""
    print(f"\n{'#'*60}")
    print(f"  AquaBridge 综合测试套件")
    print(f"  时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'#'*60}")
    
    tests = [
        ("依赖导入", test_imports),
        ("页面配置", test_page_config),
        ("DataScraper初始化", test_data_scraper_init),
        ("浏览器创建", test_browser_creation),
        ("DataScraper方法", test_data_scraper_methods),
        ("原始脚本", test_original_script),
        ("干运行", test_dry_run)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"\n✗ 测试 '{test_name}' 发生异常: {e}")
            traceback.print_exc()
            results.append((test_name, False))
    
    # 打印测试总结
    print_section("测试总结")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    print(f"总测试数: {total}")
    print(f"通过: {passed}")
    print(f"失败: {total - passed}")
    print(f"成功率: {passed/total*100:.1f}%\n")
    
    for test_name, result in results:
        status = "✓ 通过" if result else "✗ 失败"
        print(f"{status}: {test_name}")
    
    print(f"\n{'='*60}\n")
    
    if passed == total:
        print("🎉 所有测试通过！")
        return 0
    else:
        print("⚠️  部分测试失败，请检查上述输出。")
        return 1

if __name__ == "__main__":
    sys.exit(main())

