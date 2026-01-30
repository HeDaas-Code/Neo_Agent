"""
MCP功能演示示例
展示如何使用MCP功能
"""

import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 临时启用MCP用于演示
os.environ['ENABLE_MCP'] = 'True'

from mcp_context_manager import MCPContextManager

def main():
    print("=" * 60)
    print("MCP功能演示")
    print("=" * 60)
    
    # 创建MCP管理器
    print("\n1. 初始化MCP管理器...")
    mcp = MCPContextManager(enable_mcp=True)
    
    # 显示MCP信息
    info = mcp.get_mcp_info()
    print(f"   MCP状态: {'已启用' if info['enabled'] else '未启用'}")
    print(f"   默认工具数: {info['tools_count']}")
    print(f"   默认资源数: {info['resources_count']}")
    print(f"   默认提示词数: {info['prompts_count']}")
    
    # 演示工具调用
    print("\n2. 演示工具调用")
    print("   - 获取当前时间:")
    result = mcp.call_tool("get_current_time", {})
    if result['success']:
        print(f"     ✓ 当前时间: {result['result']}")
    
    print("   - 执行数学计算:")
    calculations = [
        ("2 + 3", "2+3"),
        ("10 * 5", "10*5"),
        ("100 / 4", "100/4"),
        ("(5 + 3) * 2", "(5+3)*2")
    ]
    for desc, expr in calculations:
        result = mcp.call_tool("calculate", {"expression": expr})
        if result['success']:
            print(f"     ✓ {desc} = {result['result']}")
        else:
            print(f"     ✗ {desc}: {result['error']}")
    
    # 演示资源访问
    print("\n3. 演示资源访问")
    resources = mcp.get_available_resources()
    print(f"   可用资源 ({len(resources)} 个):")
    for resource in resources:
        print(f"     - {resource['uri']}: {resource['name']}")
    
    # 演示提示词模板
    print("\n4. 演示提示词模板")
    result = mcp.get_prompt("emotion_analysis", {
        "conversation": "用户: 今天心情很好！\n助手: 那真是太好了！"
    })
    if result['success']:
        print("   情感分析提示词已生成:")
        print(f"   {result['prompt'][:100]}...")
    
    # 演示自定义工具
    print("\n5. 演示自定义工具注册")
    
    def weather_tool(args):
        """模拟天气查询工具"""
        city = args.get("city", "北京")
        return f"{city}的天气：晴朗，温度25℃"
    
    mcp.register_tool(
        name="get_weather",
        description="查询天气信息",
        handler=weather_tool,
        parameters={
            "type": "object",
            "properties": {
                "city": {
                    "type": "string",
                    "description": "城市名称"
                }
            }
        }
    )
    
    result = mcp.call_tool("get_weather", {"city": "上海"})
    if result['success']:
        print(f"   ✓ 自定义工具调用成功: {result['result']}")
    
    # 演示上下文管理
    print("\n6. 演示上下文管理")
    mcp.add_context({"user_input": "你好", "round": 1})
    mcp.add_context({"user_input": "今天天气怎么样", "round": 2})
    mcp.add_context({"user_input": "帮我算一下", "round": 3})
    
    contexts = mcp.get_contexts()
    print(f"   当前上下文数量: {len(contexts)}")
    print(f"   最近的上下文:")
    for ctx in contexts[-3:]:
        content = ctx['content']
        print(f"     - 第{content.get('round')}轮: {content.get('user_input')}")
    
    # 最终信息
    print("\n7. 最终MCP状态")
    final_info = mcp.get_mcp_info()
    print(f"   工具数量: {final_info['tools_count']} (包含1个自定义工具)")
    print(f"   上下文数量: {final_info['contexts_count']}")
    
    print("\n" + "=" * 60)
    print("MCP演示完成！")
    print("=" * 60)
    print("\n提示：")
    print("- 在.env文件中设置 ENABLE_MCP=True 可以启用MCP功能")
    print("- 详细文档请查看: docs/MCP_SUPPORT.md")
    print("=" * 60)

if __name__ == "__main__":
    main()
