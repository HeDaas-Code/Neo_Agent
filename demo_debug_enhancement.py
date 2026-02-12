#!/usr/bin/env python3
"""
演示增强的错误信息显示
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

print("=" * 80)
print("Neo Agent - 增强Debug功能演示")
print("=" * 80)
print()

# 示例1: 显示修改前后的对比
print("【示例1: 错误信息对比】")
print()
print("修改前:")
print("-" * 40)
print("初始化聊天代理时出错：")
print("'name'")
print()

print("修改后:")
print("-" * 40)
print("初始化聊天代理时出错：")
print()
print("TypeError: __init__() got an unexpected keyword argument 'name'")
print("位置: /home/runner/Neo_Agent/src/nps/nps_registry.py:25")
print("函数: __init__()")
print("代码: def __init__(self, tool_id, name, description, ...")
print()
print("完整堆栈跟踪:")
print("  1. chat_agent.py:412 in __init__()")
print("     self.nps_registry = NPSRegistry()")
print("  2. nps_registry.py:105 in __init__()")
print("     self.tools_dir = tools_dir or os.path.join(...)")
print("  3. nps_registry.py:197 in _register_from_nps_file()")
print("     tool = NPSTool(tool_id=..., name=..., ...)")
print("  4. nps_registry.py:25 in __init__()")
print("     def __init__(self, tool_id, name, description, ...)")
print()

# 示例2: 实际错误捕获
print("=" * 80)
print("【示例2: 实际错误捕获演示】")
print("=" * 80)
print()

from src.tools.debug_logger import DebugLogger, init_debug_logger

# 初始化logger（不输出到文件，只演示）
logger = init_debug_logger(debug_mode=False)  # 关闭文件输出

def demo_error():
    """演示函数"""
    data = {'user': 'test', 'message': 'hello'}
    # 故意访问不存在的键
    return data['missing_key']

print("运行会产生错误的代码...")
print()

try:
    demo_error()
except Exception as e:
    # 格式化错误信息
    error_msg = DebugLogger.format_exception_with_location(e, include_traceback=True)
    print("捕获到的错误信息:")
    print("-" * 80)
    print(error_msg)
    print("-" * 80)

print()
print("=" * 80)
print("✓ 演示完成！")
print()
print("现在错误信息包含:")
print("  1. 错误类型和消息")
print("  2. 文件名和行号")
print("  3. 函数名")
print("  4. 出错的代码行")
print("  5. 完整的调用堆栈")
print()
print("这些信息将帮助您快速定位和修复问题！")
print("=" * 80)
