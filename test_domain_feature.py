"""
测试环境域(Domain)功能
验证域的创建、管理和导航功能
"""

import os
import sys
from database_manager import DatabaseManager
from agent_vision import AgentVisionTool


def test_domain_functionality():
    """测试域功能的完整流程"""
    print("=" * 60)
    print("环境域(Domain)功能测试")
    print("=" * 60)
    
    # 创建测试数据库
    test_db_path = "test_domain.db"
    if os.path.exists(test_db_path):
        os.remove(test_db_path)
        print(f"✓ 已删除旧的测试数据库")
    
    # 初始化数据库管理器和视觉工具
    db = DatabaseManager(test_db_path, debug=False)
    vision_tool = AgentVisionTool(db)
    
    print("\n" + "=" * 60)
    print("步骤1: 创建测试环境")
    print("=" * 60)
    
    # 创建小可家的环境
    room_uuid = db.create_environment(
        name="小可的房间",
        overall_description="温馨舒适的学生卧室，约15平方米",
        atmosphere="温馨、宁静",
        lighting="柔和的自然光",
        sounds="偶尔能听到窗外鸟鸣",
        smells="淡淡的书香"
    )
    print(f"✓ 创建环境: 小可的房间 (UUID: {room_uuid[:8]}...)")
    
    living_room_uuid = db.create_environment(
        name="小可的客厅",
        overall_description="宽敞明亮的客厅，约25平方米",
        atmosphere="温馨、舒适",
        lighting="充足的自然光和吊灯照明",
        sounds="电视的声音和家人的交谈",
        smells="清新的空气"
    )
    print(f"✓ 创建环境: 小可的客厅 (UUID: {living_room_uuid[:8]}...)")
    
    kitchen_uuid = db.create_environment(
        name="小可的厨房",
        overall_description="整洁的现代化厨房，约12平方米",
        atmosphere="干净、整洁",
        lighting="明亮的顶灯",
        sounds="水龙头流水声和锅碗瓢盆的声音",
        smells="饭菜的香味"
    )
    print(f"✓ 创建环境: 小可的厨房 (UUID: {kitchen_uuid[:8]}...)")
    
    # 创建学校的环境
    playground_uuid = db.create_environment(
        name="学校操场",
        overall_description="宽阔的操场，有篮球场和跑道",
        atmosphere="青春活力",
        lighting="阳光充足",
        sounds="学生们的欢笑声和篮球的拍打声",
        smells="青草的味道"
    )
    print(f"✓ 创建环境: 学校操场 (UUID: {playground_uuid[:8]}...)")
    
    classroom_uuid = db.create_environment(
        name="教室",
        overall_description="明亮的教室，整齐排列着课桌椅",
        atmosphere="学习氛围浓厚",
        lighting="明亮的日光灯",
        sounds="老师讲课的声音和学生讨论",
        smells="粉笔和书本的味道"
    )
    print(f"✓ 创建环境: 教室 (UUID: {classroom_uuid[:8]}...)")
    
    print("\n" + "=" * 60)
    print("步骤2: 创建域(Domain)")
    print("=" * 60)
    
    # 创建"小可家"域，默认环境为客厅
    home_domain_uuid = db.create_domain(
        name="小可家",
        description="小可的温馨家庭，包括房间、客厅和厨房",
        default_environment_uuid=living_room_uuid
    )
    print(f"✓ 创建域: 小可家 (UUID: {home_domain_uuid[:8]}...)")
    print(f"  默认环境: 小可的客厅")
    
    # 创建"学校"域，默认环境为操场
    school_domain_uuid = db.create_domain(
        name="学校",
        description="小可就读的高中，充满青春活力的地方",
        default_environment_uuid=playground_uuid
    )
    print(f"✓ 创建域: 学校 (UUID: {school_domain_uuid[:8]}...)")
    print(f"  默认环境: 学校操场")
    
    print("\n" + "=" * 60)
    print("步骤3: 将环境添加到域")
    print("=" * 60)
    
    # 将环境添加到"小可家"域
    db.add_environment_to_domain(home_domain_uuid, room_uuid)
    print(f"✓ 将'小可的房间'添加到'小可家'域")
    
    db.add_environment_to_domain(home_domain_uuid, living_room_uuid)
    print(f"✓ 将'小可的客厅'添加到'小可家'域")
    
    db.add_environment_to_domain(home_domain_uuid, kitchen_uuid)
    print(f"✓ 将'小可的厨房'添加到'小可家'域")
    
    # 将环境添加到"学校"域
    db.add_environment_to_domain(school_domain_uuid, playground_uuid)
    print(f"✓ 将'学校操场'添加到'学校'域")
    
    db.add_environment_to_domain(school_domain_uuid, classroom_uuid)
    print(f"✓ 将'教室'添加到'学校'域")
    
    print("\n" + "=" * 60)
    print("步骤4: 查询域信息")
    print("=" * 60)
    
    # 查询所有域
    all_domains = db.get_all_domains()
    print(f"\n所有域（共{len(all_domains)}个）:")
    for domain in all_domains:
        print(f"  - {domain['name']}: {domain['description']}")
        envs = db.get_domain_environments(domain['uuid'])
        print(f"    包含环境: {', '.join([e['name'] for e in envs])}")
        if domain['default_environment_uuid']:
            default_env = db.get_environment(domain['default_environment_uuid'])
            print(f"    默认环境: {default_env['name']}")
    
    # 查询环境所属的域
    print(f"\n查询'小可的房间'所属的域:")
    room_domains = db.get_environment_domains(room_uuid)
    for domain in room_domains:
        print(f"  - {domain['name']}")
    
    print("\n" + "=" * 60)
    print("步骤5: 测试域级别的导航")
    print("=" * 60)
    
    # 设置当前环境为小可的房间
    db.set_active_environment(room_uuid)
    current_env = db.get_active_environment()
    print(f"\n当前环境: {current_env['name']}")
    
    # 获取当前域
    current_domain = vision_tool.get_current_domain()
    if current_domain:
        print(f"当前所在域: {current_domain['name']}")
    
    # 创建环境连接（小可家和学校之间的连接）
    print(f"\n创建域间连接: 小可家 <-> 学校")
    # 我们需要在"小可家"的某个环境和"学校"的某个环境之间创建连接
    # 例如：从客厅可以去学校操场
    db.create_environment_connection(
        from_env_uuid=living_room_uuid,
        to_env_uuid=playground_uuid,
        connection_type='normal',
        direction='bidirectional',
        description='从家出发去学校'
    )
    print(f"✓ 创建连接: 小可的客厅 <-> 学校操场")
    
    # 测试切换到域
    print(f"\n测试切换到'学校'域:")
    success = vision_tool.switch_to_domain(school_domain_uuid)
    if success:
        current_env = db.get_active_environment()
        print(f"✓ 切换成功，当前环境: {current_env['name']}")
    else:
        print(f"✗ 切换失败")
    
    print("\n" + "=" * 60)
    print("步骤6: 测试视觉上下文（域级别 vs 环境级别）")
    print("=" * 60)
    
    # 切换回小可的房间
    db.set_active_environment(room_uuid)
    
    # 测试低精度查询（域级别）
    print("\n测试低精度查询（域级别）:")
    test_query_low = "你在哪？"
    print(f"查询: {test_query_low}")
    
    high_precision = vision_tool.detect_precision_requirement(test_query_low)
    print(f"精度要求: {'高' if high_precision else '低'}")
    
    vision_context = vision_tool.get_vision_context_with_precision(
        test_query_low, 
        high_precision=high_precision
    )
    if vision_context:
        summary = vision_tool.get_vision_summary(vision_context)
        print(f"{summary}")
        print(f"\n完整上下文:")
        prompt = vision_tool.format_vision_prompt(vision_context)
        print(prompt)
    
    # 测试高精度查询（环境级别）
    print("\n" + "-" * 60)
    print("测试高精度查询（环境级别）:")
    test_query_high = "房间里有什么？"
    print(f"查询: {test_query_high}")
    
    high_precision = vision_tool.detect_precision_requirement(test_query_high)
    print(f"精度要求: {'高' if high_precision else '低'}")
    
    vision_context = vision_tool.get_vision_context_with_precision(
        test_query_high, 
        high_precision=high_precision
    )
    if vision_context:
        summary = vision_tool.get_vision_summary(vision_context)
        print(f"{summary}")
        print(f"\n完整上下文预览:")
        prompt = vision_tool.format_vision_prompt(vision_context)
        print(prompt[:300] + "...")
    
    print("\n" + "=" * 60)
    print("步骤7: 测试域切换意图检测")
    print("=" * 60)
    
    # 测试域切换意图
    test_queries = [
        "我想去学校",
        "回到小可家",
        "去学校操场",
        "今天天气怎么样",  # 不应该触发切换
    ]
    
    for query in test_queries:
        print(f"\n查询: {query}")
        
        # 检测域切换意图
        domain_switch = vision_tool.detect_domain_switch_intent(query)
        if domain_switch:
            print(f"✓ 检测到域切换意图:")
            print(f"  目标域: {domain_switch['to_domain']['name']}")
        else:
            # 检测环境切换意图
            env_switch = vision_tool.detect_environment_switch_intent(query)
            if env_switch:
                print(f"✓ 检测到环境切换意图:")
                print(f"  目标环境: {env_switch['to_env']['name']}")
            else:
                print(f"  未检测到切换意图")
    
    print("\n" + "=" * 60)
    print("步骤8: 统计信息")
    print("=" * 60)
    
    stats = db.get_statistics()
    print(f"\n数据库统计:")
    print(f"  总环境数: {stats.get('total_environments', 0)}")
    print(f"  总域数: {len(all_domains)}")
    print(f"  环境连接数: {stats.get('environment_connections', 0)}")
    
    print("\n" + "=" * 60)
    print("✓ 所有测试完成")
    print("=" * 60)
    
    # 清理测试数据库
    print(f"\n是否删除测试数据库? (y/n)")
    # 自动删除以便于CI测试
    if os.path.exists(test_db_path):
        os.remove(test_db_path)
        print(f"✓ 已删除测试数据库: {test_db_path}")


if __name__ == '__main__':
    try:
        test_domain_functionality()
    except Exception as e:
        print(f"\n✗ 测试过程中出现错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
