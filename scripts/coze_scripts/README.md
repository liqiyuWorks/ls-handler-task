# Coze 知识库管理脚本

这个脚本用于通过 Coze Open API 管理知识库，包括查看知识库列表和知识库中的文件列表。

## 功能特性

- ✅ **查看知识库列表**：获取所有可用的知识库（数据集）
- ✅ **查看知识库文件**：获取指定知识库中的文件列表（支持分页）
- ✅ **自动翻页**：自动获取所有数据，无需手动翻页
- ✅ **详细信息展示**：显示知识库和文件的详细信息（ID、名称、类型、大小、创建/更新时间等）
- ✅ **结果导出**：将结果导出为 JSON 文件，方便后续处理
- ✅ **灵活配置**：支持环境变量和命令行参数配置
- ✅ **多种使用模式**：支持命令行模式和代码调用模式

## 安装依赖

```bash
pip install requests
```

## 使用方法

### 模式 1: 查看知识库列表

列出所有可用的知识库（若接口要求「指定空间」，需设置 `COZE_WORKSPACE_ID`）：

```bash
# 使用环境变量
export COZE_TOKEN='your_access_token'
python sync_rag.py list

# 401 时可按文档要求传入空间 ID
export COZE_WORKSPACE_ID='your_workspace_id'   # 从空间 URL 获取，如 .../space/7439012204332711970/library
python sync_rag.py list
```

### 模式 2: 查看知识库文件列表

查看指定知识库中的文件：

```bash
# 使用环境变量
export COZE_TOKEN='your_pat_token'
export COZE_KNOWLEDGE_ID='your_knowledge_id'
python sync_rag.py files

# 或者指定知识库 ID
python sync_rag.py files <knowledge_id>

# 兼容旧版本用法（直接传入 token 和 knowledge_id）
python sync_rag.py <token> [knowledge_id>
```

### 示例

```bash
# 查看所有知识库
export COZE_TOKEN='your_token'
python sync_rag.py list

# 查看指定知识库的文件
export COZE_KNOWLEDGE_ID='7598823790127366163'
python sync_rag.py files

# 或直接传参
python sync_rag.py files 7598823790127366163
```

### 方法 3: 作为 Python 库使用

#### 安装

将 `coze_scripts` 目录添加到 Python 路径，或使用以下方式导入：

```python
# 方式 1: 直接导入模块
import sys
sys.path.append('/path/to/coze_scripts')
from sync_rag import CozeKnowledgeAPI

# 方式 2: 作为包导入（推荐）
from coze_scripts import CozeKnowledgeAPI
```

#### 使用示例

```python
from coze_scripts import CozeKnowledgeAPI

# 初始化 API 客户端（推荐同时提供 space_id）
api = CozeKnowledgeAPI(
    token="your_pat_token",
    space_id="your_space_id"  # 可选，但文件列表 API 需要
)

# 1. 获取所有知识库列表
datasets = api.get_all_datasets(space_id="your_space_id")
for dataset in datasets:
    print(f"知识库: {dataset.get('name')}, ID: {dataset.get('dataset_id')}")

# 2. 获取指定知识库的文件列表（需要 space_id）
files = api.get_all_knowledge_files(
    dataset_id="7598823790127366163",
    space_id="your_space_id"  # 必需
)
for file in files:
    print(f"文件: {file.get('name')}, 大小: {file.get('size')} 字节")

# 3. 获取单页知识库列表
datasets_result = api.list_datasets(
    space_id="your_space_id",
    page=1,
    page_size=20
)
print(f"共 {datasets_result.get('data', {}).get('total', 0)} 个知识库")

# 4. 获取单页文件列表
files_result = api.list_knowledge_files(
    dataset_id="your_dataset_id",
    space_id="your_space_id",  # 必需
    page=0,  # 从 0 开始
    size=10
)
print(f"共 {files_result.get('total', 0)} 个文件")
```
```

## 获取 Token 和 Knowledge ID

### 获取 Coze API Token (PAT)

1. 登录 [Coze 平台](https://www.coze.cn)
2. 进入「开发者中心」或「API 管理」
3. 创建 Personal Access Token (PAT)
4. 复制生成的 Token（格式类似：`pat_xxxxx...` 或 `sk-xxxxx...`）
5. **重要**：确保 Token 已开通 `listKnowledge` 权限（用于查看知识库列表）

### 获取 Knowledge ID（知识库 ID）

1. 在 Coze 平台中进入你的知识库
2. 从浏览器地址栏或知识库设置中获取知识库 ID
3. 知识库 ID 通常是一个数字字符串（如 `7598823790127366163`）

### 获取 Workspace ID（空间 ID，可选）

若接口要求「指定空间」或出现 401，可设置空间 ID：

1. 打开 Coze 控制台，进入目标空间
2. 从 URL 获取：`https://www.coze.cn/space/7439012204332711970/library` → `7439012204332711970`
3. 设置环境变量：`export COZE_WORKSPACE_ID='7439012204332711970'`

## API 端点说明

脚本使用的 API 端点：

### 知识库（数据集）相关
- **知识库列表**: `GET https://api.coze.cn/v1/datasets`
  - 权限要求：`listKnowledge`
  - 参考文档：[获取知识库列表](https://www.coze.cn/open/docs/developer_guides/list_dataset)
- **知识库详情**: `GET https://api.coze.cn/v1/datasets/{dataset_id}`

### 文件相关
- **文件列表**: `POST https://api.coze.cn/open_api/knowledge/document/list`
  - 权限要求: `listDocument`
  - 参考文档：[知识库文件列表](https://www.coze.cn/open/docs/developer_guides/list_knowledge_files)
  - 说明: 仅支持扣子知识库，不支持火山知识库
  - 请求头: `X-Coze-Space-Id`（必需）
  - 请求体: `dataset_id`（必需）, `page`（默认 0）, `size`（默认 10）

### 请求头要求

所有 API 请求都需要以下请求头：
- `Authorization: Bearer {Access_Token}` - 用于验证客户端身份的访问令牌（PAT token）
- `Content-Type: application/json` - 请求正文的格式

文件列表 API 还需要：
- `X-Coze-Space-Id: {space_id}` - 扣子知识库所属的空间 ID

## 输出说明

脚本会根据不同的模式输出不同的内容：

### 查看知识库列表模式

1. 在控制台打印知识库列表摘要（包括 ID、名称、类型、文件数、描述等）
2. 生成 JSON 文件保存完整数据（文件名格式：`knowledge_datasets_{timestamp}.json`）

知识库列表 JSON 格式：
```json
{
  "export_time": "2026-01-24T10:30:00",
  "total": 5,
  "datasets": [
    {
      "id": "dataset_id",
      "name": "知识库名称",
      "type": "知识库类型",
      "file_count": 10,
      "description": "知识库描述",
      "created_at": "创建时间",
      "updated_at": "更新时间"
    }
  ]
}
```

### 查看文件列表模式

1. 在控制台打印文件列表摘要（包括 ID、名称、类型、大小、创建/更新时间等）
2. 生成 JSON 文件保存完整数据（文件名格式：`knowledge_files_{knowledge_id}_{timestamp}.json`）

文件列表 JSON 格式：
```json
{
  "export_time": "2026-01-24T10:30:00",
  "total": 10,
  "files": [
    {
      "id": "file_id",
      "name": "文件名",
      "type": "文件类型",
      "size": "文件大小",
      "created_at": "创建时间",
      "updated_at": "更新时间"
    }
  ]
}
```

## 注意事项

1. **API 响应格式**: 不同版本的 Coze API 可能返回不同的响应格式。脚本已经处理了多种常见的响应格式，如果遇到问题，请检查 API 文档或联系 Coze 技术支持。

2. **分页参数**: 
   - `page_size`: 每页数量，默认 20，最大可能有限制
   - `page_num`: 页码，从 1 开始

3. **错误处理**: 如果 API 返回错误，脚本会显示详细的错误信息，包括响应内容。

4. **网络超时**: 请求超时时间设置为 30 秒，如果网络较慢可能需要调整。

## 参考文档

- [Coze Open API 文档](https://www.coze.cn/open/docs)
- [知识库（数据集）列表 API](https://www.coze.cn/open/docs/developer_guides/list_dataset)
- [知识库文件列表 API](https://www.coze.cn/open/docs/developer_guides/list_knowledge_files)

## 故障排除

### 问题：401 Unauthorized（含 `authentication is invalid`、code 4100）

1. **Token**：确认 `COZE_TOKEN` 为有效的 Access Token（如 `sk-...` 或 PAT `pat_...`），无多余空格、未过期。
2. **权限**：查看知识库列表需要 `listKnowledge` 权限。在 [扣子控制台](https://www.coze.cn) → 开发者设置 → API 令牌 中创建/更新令牌，并勾选对应权限。
3. **空间 ID**：接口说明为「查看指定空间下的全部知识库」时，需传 `workspace_id`。设置 `COZE_WORKSPACE_ID` 后重试（从空间 URL 的 `.../space/{id}/...` 获取）。

### 问题：404 Not Found
- 检查知识库 ID 是否正确
- 确认知识库是否存在

### 问题：响应格式不符合预期
- 查看控制台输出的原始响应
- 根据实际 API 响应调整代码中的字段映射
