#!/usr/bin/env python3
"""测试服务层基础功能"""
import asyncio
import json
import tempfile
from pathlib import Path

from neo_agent.service.daemon import AgentDaemon


async def test_daemon_basic():
    """测试守护进程基本功能"""
    with tempfile.TemporaryDirectory() as tmpdir:
        data_dir = Path(tmpdir)
        daemon = AgentDaemon(data_dir)
        
        print(f"✓ 守护进程初始化成功")
        print(f"  数据目录: {daemon.data_dir}")
        print(f"  Socket: {daemon.socket_path}")
        print(f"  PID 文件: {daemon.pid_file}")
        print(f"  日志文件: {daemon.log_file}")
        
        # 测试状态检查
        status = daemon.status()
        assert not status["running"], "服务不应该在运行"
        print(f"✓ 状态检查正常")
        
        print("\n所有基础测试通过！")


if __name__ == "__main__":
    asyncio.run(test_daemon_basic())
