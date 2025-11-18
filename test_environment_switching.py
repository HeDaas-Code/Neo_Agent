"""
测试环境切换功能
"""

from database_manager import DatabaseManager
from agent_vision import AgentVisionTool

def test_environment_switching():
    """
    测试完整的环境切换功能
    """
    print("=" * 80)
    print("环境切换功能测试")
    print("=" * 80)
    
    # 创建测试数据库
    db = DatabaseManager('test_env_switching_complete.db')
    vision = AgentVisionTool(db)
    
    print("\n【步骤1】创建环境")
    print("-" * 80)
    
    # 创建房间
    room_uuid = db.create_environment(
        name="卧室",
        overall_description="温馨的卧室，有一张床和一个书桌"
    )
    print(f"✓ 创建环境「卧室」: {room_uuid[:8]}...")
    
    # 创建客厅
    living_uuid = db.create_environment(
        name="客厅",
        overall_description="宽敞的客厅，有沙发和电视"
    )
    print(f"✓ 创建环境「客厅」: {living_uuid[:8]}...")
    
    # 创建厨房
    kitchen_uuid = db.create_environment(
        name="厨房",
        overall_description="干净的厨房，有灶台和冰箱"
    )
    print(f"✓ 创建环境「厨房」: {kitchen_uuid[:8]}...")
    
    # 创建书房（孤立的）
    study_uuid = db.create_environment(
        name="书房",
        overall_description="安静的书房，有很多书架"
    )
    print(f"✓ 创建环境「书房」(孤立): {study_uuid[:8]}...")
    
    # 设置卧室为当前环境
    db.set_active_environment(room_uuid)
    print(f"✓ 设置「卧室」为当前激活环境")
    
    print("\n【步骤2】创建环境连接")
    print("-" * 80)
    
    # 卧室 <-> 客厅
    conn1_uuid = db.create_environment_connection(
        from_env_uuid=room_uuid,
        to_env_uuid=living_uuid,
        connection_type="door",
        direction="bidirectional",
        description="通过门可以进入客厅"
    )
    print(f"✓ 创建连接: 卧室 ⟷ 客厅 (door)")
    
    # 客厅 -> 厨房
    conn2_uuid = db.create_environment_connection(
        from_env_uuid=living_uuid,
        to_env_uuid=kitchen_uuid,
        connection_type="corridor",
        direction="bidirectional",
        description="走廊连接客厅和厨房"
    )
    print(f"✓ 创建连接: 客厅 ⟷ 厨房 (corridor)")
    
    print("\n【步骤3】测试连通性检查")
    print("-" * 80)
    
    test_cases = [
        (room_uuid, living_uuid, "卧室", "客厅", True),
        (room_uuid, kitchen_uuid, "卧室", "厨房", False),  # 不直接连通
        (living_uuid, kitchen_uuid, "客厅", "厨房", True),
        (room_uuid, study_uuid, "卧室", "书房", False),  # 孤立环境
    ]
    
    for from_uuid, to_uuid, from_name, to_name, expected in test_cases:
        can_move = db.can_move_to_environment(from_uuid, to_uuid)
        status = "✓" if can_move == expected else "✗"
        result = "可以" if can_move else "不可以"
        print(f"{status} {from_name} -> {to_name}: {result} (预期: {'可以' if expected else '不可以'})")
    
    print("\n【步骤4】测试获取连通环境")
    print("-" * 80)
    
    # 从卧室可以到达的环境
    connected_from_room = db.get_connected_environments(room_uuid)
    print(f"从卧室可以到达的环境: {[env['name'] for env in connected_from_room]}")
    
    # 从客厅可以到达的环境
    connected_from_living = db.get_connected_environments(living_uuid)
    print(f"从客厅可以到达的环境: {[env['name'] for env in connected_from_living]}")
    
    # 从书房可以到达的环境（孤立的）
    connected_from_study = db.get_connected_environments(study_uuid)
    print(f"从书房可以到达的环境: {[env['name'] for env in connected_from_study]}")
    
    print("\n【步骤5】测试环境切换意图检测")
    print("-" * 80)
    
    test_queries = [
        "我去客厅吧",
        "我想去厨房",
        "我想去书房",
        "今天天气真好",
        "帮我讲个故事",
    ]
    
    for query in test_queries:
        intent = vision.detect_environment_switch_intent(query)
        if intent:
            print(f"✓ 查询: 「{query}」")
            print(f"  检测到切换意图: {intent['from_env']['name']} -> {intent['to_env']['name']}")
            print(f"  是否可以切换: {intent['can_switch']}")
        else:
            print(f"○ 查询: 「{query}」 - 未检测到切换意图")
    
    print("\n【步骤6】测试环境切换执行")
    print("-" * 80)
    
    # 当前在卧室
    current = db.get_active_environment()
    print(f"当前环境: {current['name']}")
    
    # 尝试切换到客厅（允许）
    print(f"\n尝试切换到客厅...")
    success = vision.switch_environment(living_uuid)
    if success:
        current = db.get_active_environment()
        print(f"✓ 切换成功，当前环境: {current['name']}")
    else:
        print(f"✗ 切换失败")
    
    # 尝试切换到书房（不允许，因为没有连接）
    print(f"\n尝试切换到书房（孤立环境）...")
    success = vision.switch_environment(study_uuid)
    if success:
        current = db.get_active_environment()
        print(f"✗ 不应该切换成功！当前环境: {current['name']}")
    else:
        current = db.get_active_environment()
        print(f"✓ 正确拒绝切换，保持在: {current['name']}")
    
    # 从客厅切换到厨房（允许）
    print(f"\n从客厅尝试切换到厨房...")
    success = vision.switch_environment(kitchen_uuid)
    if success:
        current = db.get_active_environment()
        print(f"✓ 切换成功，当前环境: {current['name']}")
    else:
        print(f"✗ 切换失败")
    
    print("\n【步骤7】获取环境关系统计")
    print("-" * 80)
    
    all_connections = db.get_all_environment_connections()
    print(f"总连接数: {len(all_connections)}")
    for conn in all_connections:
        from_env = db.get_environment(conn['from_environment_uuid'])
        to_env = db.get_environment(conn['to_environment_uuid'])
        direction_symbol = "→" if conn['direction'] == 'one_way' else "⟷"
        print(f"  {from_env['name']} {direction_symbol} {to_env['name']} ({conn['connection_type']})")
    
    print("\n" + "=" * 80)
    print("✓ 所有测试完成！")
    print("=" * 80)

if __name__ == '__main__':
    test_environment_switching()
