#!/bin/bash
# Neo Agent 服务停止脚本

echo "正在停止 Neo Agent 服务..."

if pgrep -f "neo_agent.service.daemon" > /dev/null; then
    pkill -f "neo_agent.service.daemon"
    sleep 1
    
    if pgrep -f "neo_agent.service.daemon" > /dev/null; then
        echo "✗ 服务未能停止，尝试强制终止..."
        pkill -9 -f "neo_agent.service.daemon"
        sleep 1
    fi
    
    if pgrep -f "neo_agent.service.daemon" > /dev/null; then
        echo "✗ 服务无法停止"
        exit 1
    else
        echo "✓ 服务已停止"
    fi
else
    echo "✓ 服务未在运行"
fi
