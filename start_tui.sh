#!/bin/bash
# Neo Agent TUI 快速启动脚本

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# 激活虚拟环境
source venv/bin/activate

# 检查服务是否运行
if pgrep -f "neo_agent.service.daemon" > /dev/null; then
    echo "✓ 服务已在运行"
else
    echo "启动服务..."
    setsid python -m neo_agent.service.daemon > /home/hedass/.neo_agent/agent.log 2>&1 < /dev/null &
    sleep 2
    
    if pgrep -f "neo_agent.service.daemon" > /dev/null; then
        echo "✓ 服务启动成功"
    else
        echo "✗ 服务启动失败，查看日志："
        tail -20 /home/hedass/.neo_agent/agent.log
        exit 1
    fi
fi

# 启动 TUI
echo "启动 TUI..."
python -m neo_agent.ui.v2
