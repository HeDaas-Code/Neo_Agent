"""
测试智能体视觉功能与聊天代理的集成
"""

import os
from dotenv import load_dotenv

# 设置环境变量
os.environ['DEBUG_MODE'] = 'False'  # 关闭debug日志避免干扰

load_dotenv()

from chat_agent import ChatAgent
from agent_vision import AgentVisionTool

def test_vision_integration():
    """测试视觉功能与聊天代理的集成"""
    
    print("=" * 80)
    print("智能体视觉功能集成测试")
    print("=" * 80)
    
    # 创建聊天代理
    print("\n1. 初始化聊天代理...")
    agent = ChatAgent()
    print("   ✓ 聊天代理初始化完成")
    
    # 创建默认环境
    print("\n2. 创建默认测试环境...")
    env_uuid = agent.vision_tool.create_default_environment()
    print(f"   ✓ 默认环境创建完成: {env_uuid[:8]}...")
    
    # 测试场景1: 询问环境相关问题（应该触发视觉）
    print("\n" + "=" * 80)
    print("测试场景1: 询问环境相关问题")
    print("=" * 80)
    
    test_queries_vision = [
        "周围有什么？",
        "房间里有哪些东西？",
        "我能看到什么？",
    ]
    
    for query in test_queries_vision:
        print(f"\n用户: {query}")
        response = agent.chat(query)
        print(f"小可: {response[:200]}...")
        
        # 检查视觉上下文
        vision_context = agent.get_last_vision_context()
        if vision_context:
            print(f"   ✓ 视觉工具已触发")
            print(f"   环境: {vision_context['environment']['name']}")
            print(f"   物体数量: {vision_context['object_count']}")
        else:
            print(f"   ✗ 视觉工具未触发（异常）")
    
    # 测试场景2: 普通对话（不应该触发视觉）
    print("\n" + "=" * 80)
    print("测试场景2: 普通对话（不应触发视觉）")
    print("=" * 80)
    
    test_queries_normal = [
        "你好",
        "今天天气怎么样？",
        "给我讲个历史故事",
    ]
    
    for query in test_queries_normal:
        print(f"\n用户: {query}")
        response = agent.chat(query)
        print(f"小可: {response[:200]}...")
        
        # 检查视觉上下文
        vision_context = agent.get_last_vision_context()
        if vision_context:
            print(f"   ✗ 视觉工具意外触发")
        else:
            print(f"   ✓ 视觉工具未触发（正常）")
    
    # 检查视觉工具使用记录
    print("\n" + "=" * 80)
    print("检查视觉工具使用记录")
    print("=" * 80)
    
    logs = agent.db.get_vision_tool_logs(limit=10)
    print(f"\n共有 {len(logs)} 条视觉工具使用记录")
    
    for i, log in enumerate(logs, 1):
        print(f"\n记录 {i}:")
        print(f"  时间: {log['created_at']}")
        print(f"  查询: {log['query']}")
        print(f"  触发方式: {log['triggered_by']}")
        if log.get('objects_viewed'):
            print(f"  查看的物体: {log['objects_viewed']}")
    
    # 检查环境数据库
    print("\n" + "=" * 80)
    print("检查环境数据库")
    print("=" * 80)
    
    environments = agent.db.get_all_environments()
    print(f"\n共有 {len(environments)} 个环境配置")
    
    for env in environments:
        print(f"\n环境: {env['name']}")
        print(f"  UUID: {env['uuid'][:8]}...")
        print(f"  描述: {env['overall_description'][:100]}...")
        
        objects = agent.db.get_environment_objects(env['uuid'])
        print(f"  物体数量: {len(objects)}")
        
        for obj in objects[:3]:  # 只显示前3个
            print(f"    - {obj['name']}: {obj['description'][:50]}...")
    
    print("\n" + "=" * 80)
    print("✓ 所有测试完成")
    print("=" * 80)


if __name__ == '__main__':
    test_vision_integration()
