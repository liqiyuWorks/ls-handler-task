import requests
import json

# --- 1. 配置参数 (已填入你提供的信息) ---
COZE_API_TOKEN = "pat_ESpGyZR84pzIr8AMLhdpMbeFYxpZndnLNdOOaDpEvuVnD6ctWEh1yg6d71JnzOLl"
DATASET_ID = "7598823790127366163" 
SPACE_ID = "7487472502496231460" # 注意：创建文档接口通常只需要 Dataset ID，Space ID 这里作为备用

# 你想上传的目标网页 URL
TARGET_URL = "https://mp.weixin.qq.com/s/6XMjjU9-gBzjNHtAbH6yZQ"

def debug_add_web_page():
    """
    调试函数：向 Coze 知识库添加在线网页
    """
    # Coze CN (国内版) 接口地址
    url = "https://api.coze.cn/open_api/knowledge/document/create"
    
    # 设置请求头
    headers = {
        'Authorization': f'Bearer {COZE_API_TOKEN}',
        'Content-Type': 'application/json',
        'Agw-Js-Conv': '1'
    }
    
    # 构造请求体 Payload
    payload = {
        "dataset_id": DATASET_ID,
        "document_bases": [
            {
                "name": "商业航天大消息！刚刚，北京发布！", # 你可以自定义这个文件名
                "source_info": {
                    "source_type": 1,        # 【关键】1 代表在线网页
                    "web_url": TARGET_URL    # 网页地址
                },
                "update_rule": {
                    "update_type": 1,        # 1 代表自动更新
                    "update_interval": 24          # 每 24 小时自动抓取一次
                },
                "chunk_strategy": {
                    "chunk_type": 0
                }
            }
        ]
    }

    print(f"🚀 正在开始测试...")
    print(f"目标知识库 ID: {DATASET_ID}")
    print(f"准备上传网页: {TARGET_URL}")
    print("-" * 30)

    try:
        # 发送 POST 请求
        response = requests.post(url, headers=headers, json=payload)
        
        # 调试: 打印状态码和原始文本
        print(f"📡 HTTP 状态码: {response.status_code}")
        print(f"📄 原始返回内容: {response.text}")

        try:
            response_data = response.json()
        except json.JSONDecodeError:
            print("❌ 无法解析 JSON 内容")
            return
        
        # 打印完整的响应结果以便调试
        print("📄 接口返回内容:")
        print(json.dumps(response_data, indent=4, ensure_ascii=False))
        
        # 结果判断
        if response_data.get('code') == 0:
            print("\n✅ 测试通过：网页已成功添加到知识库！")
            doc_infos = response_data.get('document_infos', [])
            if doc_infos:
                print(f"生成的文件 ID: {doc_infos[0].get('document_id')}")
        else:
            print("\n❌ 测试失败：接口返回错误。")
            print(f"错误信息 (msg): {response_data.get('msg')}")
            print(f"日志 ID (log_id): {response_data.get('log_id')}")

    except Exception as e:
        print(f"\n❌ 程序执行异常: {str(e)}")

if __name__ == "__main__":
    # 确保你已经安装了 requests 库 (pip install requests)
    debug_add_web_page()