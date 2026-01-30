"""
测试MCP与ChatAgent的集成
"""

import os
import sys
from dotenv import load_dotenv

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# 加载环境变量
load_dotenv()

# 创建临时.env文件用于测试
test_env_path = os.path.join(project_root, '.env.test')
with open(test_env_path, 'w') as f:
    f.write("ENABLE_MCP=True\n")
    f.write("DEBUG_MODE=False\n")
    f.write("SILICONFLOW_API_KEY=test_key\n")

# 重新加载环境变量
load_dotenv(test_env_path, override=True)

# 导入ChatAgent（这将触发MCP初始化）
try:
    from chat_agent import ChatAgent
    
    print("=" * 50)
    print("测试 MCP 与 ChatAgent 集成")
    print("=" * 50)
    
    # 创建ChatAgent实例
    print("\n正在初始化ChatAgent...")
    agent = ChatAgent()
    
    # 检查MCP是否已启用
    mcp_info = agent.mcp_manager.get_mcp_info()
    print(f"\nMCP状态: {'已启用' if mcp_info['enabled'] else '未启用'}")
    
    if mcp_info['enabled']:
        print(f"工具数量: {mcp_info['tools_count']}")
        print(f"资源数量: {mcp_info['resources_count']}")
        print(f"提示词数量: {mcp_info['prompts_count']}")
        
        # 测试获取工具列表
        tools = agent.mcp_manager.get_available_tools()
        print(f"\n可用工具:")
        for tool in tools:
            print(f"  - {tool['name']}: {tool['description']}")
        
        # 测试调用工具
        print("\n测试工具调用:")
        result = agent.mcp_manager.call_tool("get_current_time", {})
        if result['success']:
            print(f"  ✓ get_current_time: {result['result']}")
        
        result = agent.mcp_manager.call_tool("calculate", {"expression": "10 + 20"})
        if result['success']:
            print(f"  ✓ calculate(10 + 20): {result['result']}")
        
        # 测试上下文管理
        print("\n测试上下文管理:")
        agent.mcp_manager.add_context({
            "user_input": "测试输入",
            "character": agent.character.name
        })
        contexts = agent.mcp_manager.get_contexts()
        print(f"  ✓ 添加上下文，当前数量: {len(contexts)}")
        
        print("\n✓ MCP与ChatAgent集成测试通过！")
    else:
        print("\n✗ MCP未启用，请检查配置")
        sys.exit(1)
    
except Exception as e:
    print(f"\n✗ 测试失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
finally:
    # 清理测试文件
    if os.path.exists(test_env_path):
        os.remove(test_env_path)
    print("\n测试环境已清理")
