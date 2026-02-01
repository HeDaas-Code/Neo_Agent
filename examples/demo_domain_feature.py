"""
环境域(Domain)功能示例
演示如何使用域来组织和管理环境集合
"""

from src.core.database_manager import DatabaseManager
from src.tools.agent_vision import AgentVisionTool


def demo_domain_feature():
    """演示域功能的实际使用场景"""
    print("=" * 60)
    print("环境域(Domain)功能演示")
    print("=" * 60)
    
    # 初始化
    db = DatabaseManager("chat_agent.db")
    vision_tool = AgentVisionTool(db)
    
    print("\n场景描述:")
    print("小可是一名高中生，她的日常活动主要在两个域中进行：")
    print("1. 小可家 - 包括房间、客厅、厨房")
    print("2. 学校 - 包括教室、操场、图书馆")
    print()
    
    # 检查是否已有环境
    all_envs = db.get_all_environments()
    if len(all_envs) >= 5:
        print("✓ 检测到已有环境，使用现有环境进行演示")
    else:
        print("创建示例环境...")
        # 这里可以添加环境创建代码
    
    # 检查域
    all_domains = db.get_all_domains()
    print(f"\n当前系统中的域（共{len(all_domains)}个）:")
    for domain in all_domains:
        print(f"  📍 {domain['name']}: {domain['description']}")
        envs = db.get_domain_environments(domain['uuid'])
        env_names = [e['name'] for e in envs]
        print(f"     包含环境: {', '.join(env_names)}")
        if domain['default_environment_uuid']:
            default_env = db.get_environment(domain['default_environment_uuid'])
            if default_env:
                print(f"     默认位置: {default_env['name']}")
    
    if not all_domains:
        print("  (暂无域，请先运行 test_domain_feature.py 创建示例数据)")
        return
    
    print("\n" + "=" * 60)
    print("场景1: 位置查询 - 低精度回答")
    print("=" * 60)
    
    # 获取当前环境
    current_env = db.get_active_environment()
    if current_env:
        print(f"\n当前环境: {current_env['name']}")
        
        # 检查是否属于域
        domains = db.get_environment_domains(current_env['uuid'])
        if domains:
            domain = domains[0]
            print(f"所属域: {domain['name']}")
            
            # 模拟用户询问"你在哪？"
            query = "你在哪？"
            print(f"\n用户问: {query}")
            print("智能体回答思路:")
            print("  1. 检测到位置查询")
            print("  2. 判断精度需求 -> 低精度（用户只是想知道大概位置）")
            print("  3. 返回域级别答案")
            
            # 获取域级别的上下文
            high_precision = vision_tool.detect_precision_requirement(query)
            vision_context = vision_tool.get_vision_context_with_precision(
                query, high_precision=high_precision
            )
            
            if vision_context:
                print(f"\n智能体可能回答: \"我在{domain['name']}\"")
            else:
                print(f"\n智能体可能回答: \"我在{current_env['name']}\"")
    else:
        print("\n⚠ 当前没有激活的环境")
    
    print("\n" + "=" * 60)
    print("场景2: 环境查询 - 高精度回答")
    print("=" * 60)
    
    if current_env:
        # 模拟用户询问详细信息
        query = "周围有什么？"
        print(f"\n用户问: {query}")
        print("智能体回答思路:")
        print("  1. 检测到环境查询")
        print("  2. 判断精度需求 -> 高精度（需要具体描述）")
        print("  3. 返回详细的环境描述和物体列表")
        
        high_precision = vision_tool.detect_precision_requirement(query)
        vision_context = vision_tool.get_vision_context_with_precision(
            query, high_precision=high_precision
        )
        
        if vision_context:
            summary = vision_tool.get_vision_summary(vision_context)
            print(f"\n{summary}")
            print("\n智能体会详细描述当前环境的细节和可见物体")
    
    print("\n" + "=" * 60)
    print("场景3: 域间导航")
    print("=" * 60)
    
    if len(all_domains) >= 2:
        domain1 = all_domains[0]
        domain2 = all_domains[1]
        
        print(f"\n假设智能体想从 {domain1['name']} 去 {domain2['name']}")
        print(f"用户说: \"去{domain2['name']}\"")
        
        # 检测切换意图
        query = f"去{domain2['name']}"
        switch_intent = vision_tool.detect_domain_switch_intent(query)
        
        if switch_intent:
            print(f"\n检测到域切换意图:")
            print(f"  目标域: {switch_intent['to_domain']['name']}")
            print(f"  操作: 切换到域的默认环境")
            
            # 获取默认环境信息
            target_domain = switch_intent['to_domain']
            if target_domain['default_environment_uuid']:
                default_env = db.get_environment(target_domain['default_environment_uuid'])
                if default_env:
                    print(f"  默认位置: {default_env['name']}")
                    print(f"\n智能体会说: \"好的，我现在到{target_domain['name']}的{default_env['name']}了\"")
            else:
                print(f"  (该域未设置默认环境)")
    
    print("\n" + "=" * 60)
    print("场景4: 精度需求的智能判断")
    print("=" * 60)
    
    test_queries = [
        ("你在哪？", "低精度 - 简单位置询问"),
        ("你在什么地方？", "低精度 - 一般位置询问"),
        ("周围有什么？", "高精度 - 需要具体描述"),
        ("房间里有哪些东西？", "高精度 - 需要详细列举"),
        ("能看到什么？", "高精度 - 需要视觉细节"),
    ]
    
    print("\n不同查询的精度判断:")
    for query, expected in test_queries:
        high_precision = vision_tool.detect_precision_requirement(query)
        precision_str = "高精度" if high_precision else "低精度"
        print(f"\n  问: {query}")
        print(f"  判断: {precision_str}")
        print(f"  期望: {expected}")
        print(f"  匹配: {'✓' if precision_str in expected else '✗'}")
    
    print("\n" + "=" * 60)
    print("功能总结")
    print("=" * 60)
    
    print("""
域(Domain)功能的主要优势:

1. 📍 层级化的位置管理
   - 域级别：抽象的位置概念（如"小可家"、"学校"）
   - 环境级别：具体的场所（如"小可的房间"、"教室"）

2. 🎯 智能精度控制
   - 低精度查询：返回域级别的位置信息，简洁明了
   - 高精度查询：返回详细的环境描述和物体列表

3. 🚀 便捷的导航
   - 域间切换：自动导航到默认环境
   - 环境间切换：需要建立连接关系

4. 💡 实际应用场景
   - 聊天机器人：模拟角色在不同场所间的移动
   - 游戏AI：管理游戏世界中的区域和地点
   - 虚拟助手：理解和描述所在位置

使用建议:
- 对于日常位置查询，使用域级别回答更自然
- 对于需要详细信息的场景，切换到环境级别
- 为每个域设置合理的默认环境，提升导航体验
""")
    
    print("=" * 60)


if __name__ == '__main__':
    try:
        demo_domain_feature()
    except Exception as e:
        print(f"\n✗ 演示过程中出现错误: {e}")
        import traceback
        traceback.print_exc()
