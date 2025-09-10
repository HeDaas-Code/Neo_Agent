#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
游戏启动入口

负责游戏的启动和主循环控制，提供统一的程序入口点。

Author: AI Assistant
Date: 2024
"""

import asyncio
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from game_controller import AVGGame


async def main():
    """主函数"""
    try:
        print("🚀 正在启动《深空迷航：记忆碎片》...")
        game = AVGGame()
        await game.run()
    except Exception as e:
        print(f"\n❌ 游戏运行错误: {e}")
        import traceback
        traceback.print_exc()
        print("\n请检查配置文件和依赖是否正确安装")


def start_game():
    """游戏启动函数"""
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n👋 游戏已退出")
    except Exception as e:
        print(f"\n❌ 启动失败: {e}")
        print("请检查配置文件和依赖是否正确安装")


if __name__ == "__main__":
    start_game()