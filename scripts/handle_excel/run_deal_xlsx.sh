#!/bin/bash
# Excel 回测数据处理脚本运行器

# 获取脚本所在目录
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/../.." && pwd )"

# 加载 MongoDB 环境变量配置
ENV_FILE="$PROJECT_ROOT/env/aquabridge/.once_spider_jinzheng_pages2mgo.sh"
if [ -f "$ENV_FILE" ]; then
    source "$ENV_FILE"
    echo "已加载环境变量配置: $ENV_FILE"
else
    echo "警告: 环境变量配置文件不存在: $ENV_FILE"
    echo "将使用脚本中的默认配置"
fi

# 切换到项目根目录
cd "$PROJECT_ROOT"

# 运行 Python 脚本
python3 "$SCRIPT_DIR/deal_xlsx.py"

