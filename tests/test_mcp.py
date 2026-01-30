"""
MCP模块测试
测试MCP客户端和上下文管理器功能
"""

import os
import sys
from dotenv import load_dotenv

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from mcp_client import MCPClient
from mcp_context_manager import MCPContextManager

def test_mcp_client():
    """测试MCP客户端基础功能"""
    print("=" * 50)
    print("测试 MCP 客户端")
    print("=" * 50)
    
    client = MCPClient()
    
    # 测试工具注册
    def test_tool_handler(args):
        return f"测试工具被调用，参数: {args}"
    
    client.register_tool(
        name="test_tool",
        description="测试工具",
        handler=test_tool_handler,
        parameters={"type": "object", "properties": {}}
    )
    
    # 测试工具调用
    result = client.call_tool("test_tool", {"param1": "value1"})
    print(f"工具调用结果: {result}")
    assert result['success'] == True
    
    # 测试资源注册
    client.register_resource(
        uri="test://resource",
        name="测试资源",
        description="这是一个测试资源",
        mime_type="text/plain"
    )
    
    # 测试资源获取
    resource = client.get_resource("test://resource")
    print(f"资源获取结果: {resource}")
    assert resource['success'] == True
    
    # 测试提示词注册
    client.register_prompt(
        name="test_prompt",
        description="测试提示词",
        template="这是一个测试提示词：{arg1}",
        arguments=[{"name": "arg1", "description": "参数1", "required": True}]
    )
    
    # 测试提示词获取
    prompt = client.get_prompt("test_prompt", {"arg1": "测试值"})
    print(f"提示词渲染结果: {prompt}")
    assert prompt['success'] == True
    assert "测试值" in prompt['prompt']
    
    # 测试上下文添加
    client.add_context({"test": "context"})
    contexts = client.get_contexts()
    print(f"上下文数量: {len(contexts)}")
    assert len(contexts) == 1
    
    # 测试列表功能
    tools = client.list_tools()
    resources = client.list_resources()
    prompts = client.list_prompts()
    print(f"工具数量: {len(tools)}")
    print(f"资源数量: {len(resources)}")
    print(f"提示词数量: {len(prompts)}")
    
    # 测试服务器信息
    server_info = client.get_server_info()
    print(f"服务器信息: {server_info}")
    
    print("\n✓ MCP客户端测试通过\n")


def test_mcp_context_manager_disabled():
    """测试MCP上下文管理器（禁用状态）"""
    print("=" * 50)
    print("测试 MCP 上下文管理器（禁用状态）")
    print("=" * 50)
    
    manager = MCPContextManager(enable_mcp=False)
    
    # 测试禁用状态下的操作
    info = manager.get_mcp_info()
    print(f"MCP状态: {info}")
    assert info['enabled'] == False
    
    # 测试禁用状态下调用工具
    result = manager.call_tool("test", {})
    print(f"工具调用（禁用）: {result}")
    assert result['success'] == False
    
    print("\n✓ MCP上下文管理器（禁用）测试通过\n")


def test_mcp_context_manager_enabled():
    """测试MCP上下文管理器（启用状态）"""
    print("=" * 50)
    print("测试 MCP 上下文管理器（启用状态）")
    print("=" * 50)
    
    manager = MCPContextManager(enable_mcp=True)
    
    # 测试启用状态
    info = manager.get_mcp_info()
    print(f"MCP状态: {info}")
    assert info['enabled'] == True
    assert info['tools_count'] > 0  # 应该有默认工具
    
    # 测试默认工具
    tools = manager.get_available_tools()
    print(f"\n默认工具列表:")
    for tool in tools:
        print(f"  - {tool['name']}: {tool['description']}")
    
    # 测试调用默认工具：get_current_time
    result = manager.call_tool("get_current_time", {})
    print(f"\n调用get_current_time: {result}")
    assert result['success'] == True
    
    # 测试调用默认工具：calculate
    result = manager.call_tool("calculate", {"expression": "2+3"})
    print(f"调用calculate(2+3): {result}")
    assert result['success'] == True
    assert result['result'] == 5.0
    
    # 测试默认资源
    resources = manager.get_available_resources()
    print(f"\n默认资源列表:")
    for resource in resources:
        print(f"  - {resource['uri']}: {resource['name']}")
    
    # 测试默认提示词
    prompts = manager.get_available_prompts()
    print(f"\n默认提示词列表:")
    for prompt in prompts:
        print(f"  - {prompt['name']}: {prompt['description']}")
    
    # 测试获取提示词
    result = manager.get_prompt("emotion_analysis", {"conversation": "测试对话"})
    print(f"\n获取emotion_analysis提示词: {result}")
    assert result['success'] == True
    assert "测试对话" in result['prompt']
    
    # 测试自定义工具注册
    def custom_tool_handler(args):
        return f"自定义工具: {args.get('message', 'no message')}"
    
    manager.register_tool(
        name="custom_tool",
        description="自定义测试工具",
        handler=custom_tool_handler,
        parameters={"type": "object", "properties": {"message": {"type": "string"}}}
    )
    
    result = manager.call_tool("custom_tool", {"message": "Hello MCP"})
    print(f"\n调用自定义工具: {result}")
    assert result['success'] == True
    assert "Hello MCP" in result['result']
    
    # 测试上下文管理
    manager.add_context({"test": "context1"})
    manager.add_context({"test": "context2"})
    contexts = manager.get_contexts()
    print(f"\n上下文数量: {len(contexts)}")
    assert len(contexts) == 2
    
    # 测试限制上下文数量
    limited_contexts = manager.get_contexts(limit=1)
    print(f"限制后上下文数量: {len(limited_contexts)}")
    assert len(limited_contexts) == 1
    
    # 测试清除上下文
    manager.clear_contexts()
    contexts = manager.get_contexts()
    print(f"清除后上下文数量: {len(contexts)}")
    assert len(contexts) == 0
    
    print("\n✓ MCP上下文管理器（启用）测试通过\n")


def test_integration():
    """测试集成场景"""
    print("=" * 50)
    print("测试 MCP 集成场景")
    print("=" * 50)
    
    manager = MCPContextManager(enable_mcp=True)
    
    # 模拟对话场景
    print("\n场景1: 用户询问时间")
    manager.add_context({
        'user_input': '现在几点了？',
        'character': '小可',
        'conversation_round': 1
    })
    
    result = manager.call_tool("get_current_time", {})
    print(f"当前时间: {result['result']}")
    
    # 场景2: 用户请求计算
    print("\n场景2: 用户请求计算")
    manager.add_context({
        'user_input': '帮我算一下 15 * 8',
        'character': '小可',
        'conversation_round': 2
    })
    
    result = manager.call_tool("calculate", {"expression": "15 * 8"})
    print(f"计算结果: {result['result']}")
    
    # 场景3: 获取情感分析提示词
    print("\n场景3: 使用情感分析提示词")
    conversation = "用户: 今天心情不太好\n小可: 怎么了？发生什么事了吗？"
    result = manager.get_prompt("emotion_analysis", {"conversation": conversation})
    if result['success']:
        print(f"生成的提示词:\n{result['prompt']}")
    
    # 查看最终信息
    info = manager.get_mcp_info()
    print(f"\n最终MCP信息:")
    print(f"  启用状态: {info['enabled']}")
    print(f"  工具数量: {info['tools_count']}")
    print(f"  资源数量: {info['resources_count']}")
    print(f"  提示词数量: {info['prompts_count']}")
    print(f"  上下文数量: {info['contexts_count']}")
    
    print("\n✓ MCP集成场景测试通过\n")


if __name__ == "__main__":
    # 加载环境变量
    load_dotenv()
    
    try:
        test_mcp_client()
        test_mcp_context_manager_disabled()
        test_mcp_context_manager_enabled()
        test_integration()
        
        print("=" * 50)
        print("✓ 所有测试通过！")
        print("=" * 50)
    except AssertionError as e:
        print(f"\n✗ 测试失败: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ 测试出错: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
