"""
测试MCP工具调用机制
"""

import os
import sys

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# 设置测试环境
os.environ['DEBUG_MODE'] = 'False'

from mcp_config import MCPConfig
from mcp_context_manager import MCPContextManager

def test_tool_call_parsing():
    """测试工具调用解析"""
    print("=" * 60)
    print("测试工具调用解析")
    print("=" * 60)
    
    import re
    import json
    
    # 测试响应包含工具调用
    response = '''好的，让我查一下当前时间！

```tool
工具名称: get_current_time
参数: {}
```
'''
    
    tool_pattern = r'```tool\s*\n工具名称:\s*(\w+)\s*\n参数:\s*(\{[^}]*\})\s*\n```'
    match = re.search(tool_pattern, response)
    
    assert match is not None, "应该匹配到工具调用"
    
    tool_name = match.group(1).strip()
    tool_args = json.loads(match.group(2).strip())
    
    print(f"✓ 工具名称: {tool_name}")
    print(f"✓ 工具参数: {tool_args}")
    
    # 测试工具执行
    config = MCPConfig()
    config.set_enabled(True)
    
    manager = MCPContextManager()
    result = manager.call_tool(tool_name, tool_args)
    
    assert result['success'], "工具调用应该成功"
    print(f"✓ 工具执行结果: {result['result']}")
    
    print("\n✓ 工具调用解析测试通过\n")

def test_calculate_tool():
    """测试计算工具"""
    print("=" * 60)
    print("测试计算工具")
    print("=" * 60)
    
    config = MCPConfig()
    config.set_enabled(True)
    
    manager = MCPContextManager()
    
    # 测试计算
    result = manager.call_tool("calculate", {"expression": "15 + 27"})
    
    assert result['success'], "计算应该成功"
    assert result['result'] == 42.0, f"计算结果应该是42.0，实际是{result['result']}"
    
    print(f"✓ 15 + 27 = {result['result']}")
    
    print("\n✓ 计算工具测试通过\n")

if __name__ == "__main__":
    try:
        test_tool_call_parsing()
        test_calculate_tool()
        
        print("=" * 60)
        print("✓ 所有测试通过！")
        print("=" * 60)
    except AssertionError as e:
        print(f"\n✗ 测试失败: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ 测试出错: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
