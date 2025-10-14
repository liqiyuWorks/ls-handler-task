# 微信群信息监控系统

基于 `wxauto` 库开发的微信群消息获取和监控系统，可以实时获取微信群聊的文本信息并进行过滤、保存和导出。

## 功能特性

- 🔍 **群聊消息获取**: 获取指定群聊的最新消息
- 📝 **消息过滤**: 支持关键词过滤、发送者过滤等
- 💾 **消息保存**: 自动保存消息到JSON文件
- 📊 **消息导出**: 支持导出为CSV格式
- 🔍 **消息搜索**: 在历史消息中搜索关键词
- 📈 **实时监控**: 持续监控指定群聊的新消息
- ⚙️ **灵活配置**: 通过配置文件自定义监控行为
- 🛠️ **群聊管理**: 动态添加/移除监控群聊
- 🎯 **图形界面**: 提供交互式群聊管理工具

## 安装依赖

```bash
pip install -r requirements.txt
```

主要依赖：
- `wxauto>=3.9.0` - 微信自动化库
- `dataclasses-json>=0.6.0` - 数据类JSON支持

## 快速开始

### 1. 使用群聊管理工具（推荐）

```bash
python group_manager.py
```

这是一个交互式工具，提供图形化菜单来管理群聊和监控。

### 1.1 使用配置管理工具

```bash
python config_manager.py
```

专门用于管理配置文件，包括群聊列表、过滤条件等。

### 2. 运行快速开始脚本

```bash
python quick_start.py
```

### 3. 查看使用示例

```bash
python example.py
```

### 4. 基本使用

```python
from wechat_monitor import WeChatGroupMonitor

# 创建监控器
monitor = WeChatGroupMonitor()

# 连接微信客户端
if monitor.connect_wechat():
    # 获取群聊列表
    groups = monitor.get_group_list()
    print(f"找到 {len(groups)} 个群聊")
    
    # 添加监控群聊
    if groups:
        monitor.add_monitor_group(groups[0])
        
        # 获取消息
        messages = monitor.get_group_messages(groups[0], limit=10)
        for msg in messages:
            print(f"{msg.sender}: {msg.content}")
```

## 配置文件说明

`config.json` 配置文件包含以下选项：

```json
{
  "monitor_groups": ["win_wechat_bot_test"],  // 要监控的群聊名称列表
  "save_messages": true,                      // 是否保存消息到文件
  "output_dir": "messages",                   // 消息保存目录
  "log_level": "INFO",                        // 日志级别
  "check_interval": 10,                       // 检查间隔（秒）
  "max_messages_per_file": 1000,              // 每个文件最大消息数
  "message_filters": {
    "keywords": [],                           // 关键词过滤（只保留包含这些词的消息）
    "exclude_keywords": [                     // 排除关键词
      "撤回了一条消息",
      "拍了拍",
      "加入了群聊",
      "退出了群聊"
    ],
    "sender_whitelist": [],                   // 发送者白名单
    "sender_blacklist": []                    // 发送者黑名单
  },
  "auto_save": true,                          // 自动保存
  "export_format": "json"                     // 导出格式
}
```

### 配置文件管理

1. **直接编辑**: 手动编辑 `config.json` 文件
2. **使用配置管理工具**: 运行 `python config_manager.py`
3. **程序化管理**: 使用 `monitor.add_monitor_group()` 等方法
4. **重新加载配置**: 使用 `monitor.reload_config()` 方法

## 主要功能

### 1. 群聊管理

```python
# 添加监控群聊
monitor.add_monitor_group("群聊名称")

# 移除监控群聊
monitor.remove_monitor_group("群聊名称")

# 获取监控列表
monitored_groups = monitor.get_monitor_groups()

# 重新加载配置文件
monitor.reload_config()
```

### 2. 获取群聊消息

```python
# 获取指定群聊的最新消息
messages = monitor.get_group_messages("群聊名称", limit=50)

# 获取所有群聊列表
groups = monitor.get_group_list()
```

### 3. 消息搜索

```python
# 搜索包含关键词的消息
matched_messages = monitor.search_messages("关键词", "群聊名称")
```

### 4. 消息导出

```python
# 导出消息到CSV文件
monitor.export_messages_to_csv(messages, "output.csv")
```

### 5. 实时监控

```python
# 开始监控配置的群聊
monitor.start_monitoring()
```

## 使用注意事项

### 环境要求

1. **Windows系统**: wxauto库仅支持Windows系统
2. **微信客户端**: 需要安装并登录微信PC版客户端
3. **Python版本**: 建议使用Python 3.7+

### 使用前准备

1. 确保微信PC版客户端已打开并登录
2. 安装必要的Python依赖包
3. 根据需要修改 `config.json` 配置文件

### 安全提醒

- 本工具仅用于个人学习和研究目的
- 请遵守相关法律法规和微信使用条款
- 不要用于商业用途或侵犯他人隐私
- 建议在测试环境中使用

## 文件结构

```
win_wechat_bot/
├── wechat_monitor.py         # 主要监控模块
├── group_manager.py          # 群聊管理工具
├── config_manager.py         # 配置管理工具
├── config.json               # 配置文件
├── requirements.txt          # 依赖包列表
├── quick_start.py           # 快速开始脚本
├── example.py               # 使用示例
├── README.md                # 说明文档
└── messages/                # 消息保存目录（自动创建）
```

## 问题修复

### 修复了 wxauto 兼容性问题

原版本存在以下问题：
- `'TimeMessage' object has no attribute 'get'` 错误
- 无法正确获取群聊列表
- 消息对象属性访问错误

**修复方案**：
1. 优化了 `wechat_monitor.py` 主模块
2. 使用 `GetContactGroups()` 方法获取群聊列表
3. 改进了消息对象的属性访问方式
4. 添加了多种获取群聊的方法作为备选
5. 增强了错误处理和兼容性
6. 添加了群聊管理功能

### 使用优化后的版本

```python
# 使用优化后的版本
from wechat_monitor import WeChatGroupMonitor

monitor = WeChatGroupMonitor()
```

## 常见问题

### Q: 连接微信失败怎么办？

A: 请检查：
1. 微信PC版客户端是否已打开并登录
2. 是否已正确安装wxauto库
3. 微信版本是否过旧（建议使用最新版本）

### Q: 获取不到群聊消息？

A: 可能的原因：
1. 群聊名称配置错误
2. 群聊权限不足
3. 网络连接问题
4. 使用旧版本代码（请使用 `wechat_monitor.py`）

### Q: 出现 'TimeMessage' object has no attribute 'get' 错误？

A: 这是 wxauto 库兼容性问题，请使用优化后的版本：
```bash
python group_manager.py  # 使用群聊管理工具
python wechat_monitor.py  # 使用优化后的版本
```

### Q: 如何添加新的过滤条件？

A: 修改 `config.json` 中的 `message_filters` 部分，添加相应的关键词或发送者列表。

## 开发说明

### 扩展功能

可以通过继承 `WeChatGroupMonitor` 类来添加自定义功能：

```python
class CustomMonitor(WeChatGroupMonitor):
    def custom_message_handler(self, message):
        # 自定义消息处理逻辑
        pass
```

### 消息数据结构

```python
@dataclass
class GroupMessage:
    timestamp: str      # 时间戳
    sender: str         # 发送者
    content: str        # 消息内容
    group_name: str     # 群聊名称
    message_type: str   # 消息类型
    raw_data: Dict      # 原始数据
```

## 许可证

本项目仅供学习和研究使用，请遵守相关法律法规。

## 更新日志

- v1.0.0: 初始版本，支持基本的群聊消息获取和监控功能
