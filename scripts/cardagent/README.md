# 名片智能体

一个美观的名片展示页面，集成了智能体聊天功能。

## 功能特点

- 🎨 **现代化设计**：采用渐变色彩和卡片式布局，视觉效果优雅
- 📱 **响应式布局**：完美适配桌面端、平板和移动设备
- 💬 **智能体集成**：无缝嵌入智能体聊天窗口
- 🎯 **信息展示**：清晰展示名片信息，包括联系方式、职位等
- ✨ **交互体验**：流畅的动画效果和悬停交互

## 快速开始

### 安装依赖

确保已安装 Flask：

```bash
pip install flask
```

### 运行服务

**方式一：使用启动脚本（推荐）**

```bash
cd scripts/cardagent
./start.sh
```

**方式二：直接运行 Python**

```bash
cd scripts/cardagent
python3 app.py
```

服务将在 `http://localhost:8080` 启动。

### 访问页面

在浏览器中打开：`http://localhost:8080`

## 自定义名片信息

### 方法一：使用配置文件（推荐）

编辑 `config.py` 文件，修改 `CARD_INFO` 字典：

```python
CARD_INFO = {
    "name": "您的姓名",
    "title": "职位/头衔",
    "company": "公司名称",
    "email": "your.email@example.com",
    "phone": "+86 138 0000 0000",
    "website": "www.example.com",
    "address": "中国 · 城市",
    "tags": ["专业领域1", "专业领域2", "专业领域3"]
}
```

### 方法二：直接编辑模板

编辑 `templates/index.html` 文件，直接修改 HTML 内容。

## 配置智能体链接

在 `config.py` 文件中修改 `AGENT_URL` 变量：

```python
AGENT_URL = "你的智能体链接"
```

## 服务器配置

在 `config.py` 文件中修改 `SERVER_CONFIG` 字典：

```python
SERVER_CONFIG = {
    "host": "0.0.0.0",  # 监听地址
    "port": 8080,       # 端口号
    "debug": True        # 调试模式
}
```

## 目录结构

```
cardagent/
├── app.py              # Flask 应用主文件
├── config.py          # 配置文件（名片信息、智能体链接等）
├── start.sh           # 启动脚本
├── templates/          # HTML 模板目录
│   └── index.html     # 主页面模板
├── static/            # 静态文件目录
│   ├── style.css      # 样式文件
│   └── script.js      # JavaScript 脚本
└── README.md          # 说明文档
```

## 技术栈

- **后端**：Flask
- **前端**：HTML5, CSS3, JavaScript
- **设计**：响应式设计，CSS Grid 布局

## 浏览器支持

- Chrome (推荐)
- Firefox
- Safari
- Edge

## 注意事项

1. 确保智能体链接可以正常访问
2. 某些浏览器可能对 iframe 有安全限制，需要确保智能体网站允许嵌入
3. 建议在生产环境中使用 HTTPS

## 许可证

MIT License

