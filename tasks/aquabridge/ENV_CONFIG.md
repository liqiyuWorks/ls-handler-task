# Spider Jinzheng Pages2Mgo 环境变量配置说明

## 环境变量列表

以下环境变量可用于配置 `spider_jinzheng_pages2mgo` 任务的运行参数：

| 环境变量 | 类型 | 默认值 | 说明 |
|---------|------|--------|------|
| `SPIDER_PAGE_KEY` | string | `p4tc_spot_decision` | 要处理的页面键，可选值：`p4tc_spot_decision`, `ffa_price_signals`, `all` |
| `SPIDER_BROWSER` | string | `chromium` | 浏览器类型，可选值：`chromium`, `firefox`, `webkit` |
| `SPIDER_HEADLESS` | boolean | `false` | 是否使用无头模式，可选值：`true`, `false`, `1`, `0`, `yes`, `no`, `on`, `off` |
| `SPIDER_SAVE_FILE` | boolean | `true` | 是否保存文件，可选值：`true`, `false`, `1`, `0`, `yes`, `no`, `on`, `off` |
| `SPIDER_STORE_MONGODB` | boolean | `true` | 是否存储到MongoDB，可选值：`true`, `false`, `1`, `0`, `yes`, `no`, `on`, `off` |
| `SPIDER_PARALLEL` | boolean | `false` | 是否使用并行处理，可选值：`true`, `false`, `1`, `0`, `yes`, `no`, `on`, `off` |
| `SPIDER_MAX_WORKERS` | integer | `2` | 最大工作进程数（仅在并行模式下有效） |
| `SPIDER_FAST_MODE` | boolean | `false` | 是否使用快速模式，可选值：`true`, `false`, `1`, `0`, `yes`, `no`, `on`, `off` |
| `SPIDER_STABLE_MODE` | boolean | `true` | 是否使用稳定模式，可选值：`true`, `false`, `1`, `0`, `yes`, `no`, `on`, `off` |

## 配置优先级

配置值的优先级（从高到低）：
1. **环境变量** - 最高优先级
2. **task 参数** - 通过代码传入的参数
3. **默认值** - 如果以上都没有，使用默认值

## 使用示例

### 示例1: 使用环境变量运行

```bash
# 设置环境变量
export SPIDER_PAGE_KEY=ffa_price_signals
export SPIDER_HEADLESS=true
export SPIDER_FAST_MODE=true

# 运行任务
python main.py spider_jinzheng_pages2mgo
```

### 示例2: 一次性设置多个环境变量

```bash
SPIDER_PAGE_KEY=all \
SPIDER_BROWSER=chromium \
SPIDER_HEADLESS=false \
SPIDER_SAVE_FILE=true \
SPIDER_STORE_MONGODB=true \
SPIDER_PARALLEL=false \
SPIDER_MAX_WORKERS=2 \
SPIDER_FAST_MODE=false \
SPIDER_STABLE_MODE=true \
python main.py spider_jinzheng_pages2mgo
```

### 示例3: 在脚本中设置环境变量

```bash
#!/bin/bash
export SPIDER_PAGE_KEY=p4tc_spot_decision
export SPIDER_HEADLESS=true
export SPIDER_SAVE_FILE=true
export SPIDER_STORE_MONGODB=false

python main.py spider_jinzheng_pages2mgo
```

### 示例4: 在 Docker 中使用

```dockerfile
ENV SPIDER_PAGE_KEY=all
ENV SPIDER_HEADLESS=true
ENV SPIDER_SAVE_FILE=true
ENV SPIDER_STORE_MONGODB=true
ENV SPIDER_STABLE_MODE=true
```

或在 docker-compose.yml 中：

```yaml
services:
  spider:
    environment:
      - SPIDER_PAGE_KEY=all
      - SPIDER_HEADLESS=true
      - SPIDER_SAVE_FILE=true
      - SPIDER_STORE_MONGODB=true
      - SPIDER_STABLE_MODE=true
```

## 布尔值转换规则

环境变量中的布尔值支持以下格式（不区分大小写）：
- `true`: `true`, `1`, `yes`, `on`
- `false`: `false`, `0`, `no`, `off`

## 注意事项

1. 环境变量优先级高于代码传入的 task 参数
2. 如果环境变量值无效（如数字格式错误），将使用默认值
3. 环境变量名称使用大写字母和下划线，遵循常见的环境变量命名规范
4. 所有环境变量都是可选的，如果不设置将使用默认值或 task 参数

