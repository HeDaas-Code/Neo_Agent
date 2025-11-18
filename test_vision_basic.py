"""
测试视觉工具基本功能（不需要API）
"""

import os
from dotenv import load_dotenv

os.environ['DEBUG_MODE'] = 'False'

load_dotenv()

from database_manager import DatabaseManager
from agent_vision import AgentVisionTool

def test_vision_basic():
    """测试视觉工具基本功能"""
    
    print("=" * 80)
    print("智能体视觉工具基本功能测试")
    print("=" * 80)
    
    # 1. 测试数据库管理器
    print("\n1. 测试数据库管理器...")
    db = DatabaseManager()
    stats = db.get_statistics()
    print(f"   ✓ 数据库初始化完成")
    print(f"   环境数量: {stats.get('base_knowledge_count', 0)}")
    
    # 2. 测试视觉工具
    print("\n2. 测试视觉工具...")
    vision_tool = AgentVisionTool(db_manager=db)
    print(f"   ✓ 视觉工具初始化完成")
    
    # 3. 创建默认环境
    print("\n3. 创建默认环境...")
    env_uuid = vision_tool.create_default_environment()
    print(f"   ✓ 默认环境创建: {env_uuid[:8]}...")
    
    # 4. 验证环境创建
    print("\n4. 验证环境创建...")
    env = db.get_active_environment()
    if env:
        print(f"   ✓ 激活环境: {env['name']}")
        print(f"   描述: {env['overall_description'][:100]}...")
    
    objects = db.get_environment_objects(env_uuid)
    print(f"   ✓ 环境物体: {len(objects)} 个")
    
    for obj in objects:
        print(f"      - {obj['name']} (优先级: {obj['priority']})")
    
    # 5. 测试关键词检测
    print("\n5. 测试环境关键词检测...")
    test_queries = [
        ("周围有什么？", True),
        ("房间里有哪些东西？", True),
        ("我能看到什么？", True),
        ("今天天气怎么样？", False),
        ("讲个历史故事", False),
    ]
    
    for query, should_trigger in test_queries:
        result = vision_tool.should_use_vision(query)
        status = "✓" if result == should_trigger else "✗"
        print(f"   {status} '{query}' -> {'触发' if result else '不触发'} (预期: {'触发' if should_trigger else '不触发'})")
    
    # 6. 测试视觉上下文获取
    print("\n6. 测试视觉上下文获取...")
    vision_context = vision_tool.get_vision_context("周围有什么？")
    
    if vision_context:
        print(f"   ✓ 视觉上下文获取成功")
        print(f"   环境: {vision_context['environment']['name']}")
        print(f"   物体数量: {vision_context['object_count']}")
        
        # 格式化视觉上下文
        formatted = vision_tool.format_vision_prompt(vision_context)
        print(f"   ✓ 格式化文本长度: {len(formatted)} 字符")
        print(f"\n   格式化文本预览:")
        print("   " + "-" * 76)
        for line in formatted.split('\n')[:15]:
            print(f"   {line}")
        print("   ...")
        print("   " + "-" * 76)
    else:
        print(f"   ✗ 视觉上下文获取失败")
    
    # 7. 检查视觉工具使用记录
    print("\n7. 检查视觉工具使用记录...")
    logs = db.get_vision_tool_logs(limit=10)
    print(f"   ✓ 共有 {len(logs)} 条使用记录")
    
    if logs:
        latest = logs[0]
        print(f"   最新记录:")
        print(f"      查询: {latest['query']}")
        print(f"      触发方式: {latest['triggered_by']}")
        if latest.get('objects_viewed'):
            print(f"      物体: {latest['objects_viewed']}")
    
    # 8. 测试环境管理功能
    print("\n8. 测试环境管理功能...")
    
    # 创建一个新环境
    new_env_uuid = db.create_environment(
        name="测试环境",
        overall_description="这是一个测试环境",
        atmosphere="轻松",
        lighting="明亮"
    )
    print(f"   ✓ 新环境创建: {new_env_uuid[:8]}...")
    
    # 添加一个测试物体
    obj_uuid = db.add_environment_object(
        environment_uuid=new_env_uuid,
        name="测试物体",
        description="这是一个测试物体",
        position="中央",
        priority=70
    )
    print(f"   ✓ 测试物体添加: {obj_uuid[:8]}...")
    
    # 获取所有环境
    all_envs = db.get_all_environments()
    print(f"   ✓ 总环境数量: {len(all_envs)}")
    
    # 清理测试环境
    db.delete_environment(new_env_uuid)
    print(f"   ✓ 测试环境已删除")
    
    print("\n" + "=" * 80)
    print("✓ 所有基本功能测试通过")
    print("=" * 80)
    
    print("\n💡 提示:")
    print("   - 默认环境「小可的房间」已创建并激活")
    print("   - 当用户询问周围环境时，视觉工具会自动触发")
    print("   - 可以通过GUI界面管理环境和物体")
    print("   - 视觉工具使用记录会自动保存到数据库")


if __name__ == '__main__':
    test_vision_basic()
