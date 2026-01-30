"""
扩展的设定迁移测试脚本 - 包含真实数据测试
"""

import os
import sys
from datetime import datetime
from settings_migration import SettingsMigration
from database_manager import DatabaseManager

def setup_test_database():
    """创建包含测试数据的数据库"""
    print("=" * 50)
    print("创建测试数据库")
    print("=" * 50)
    
    db_manager = DatabaseManager(db_path="test_with_data.db")
    
    # 添加基础知识
    db_manager.add_base_fact(
        entity_name="Python",
        content="Python是一种高级编程语言",
        category="技术",
        description="编程语言知识"
    )
    
    db_manager.add_base_fact(
        entity_name="AI",
        content="人工智能是计算机科学的一个分支",
        category="技术",
        description="人工智能知识"
    )
    
    # 添加实体和定义
    entity_uuid = db_manager.find_or_create_entity("LangChain")
    db_manager.set_entity_definition(
        entity_uuid=entity_uuid,
        content="LangChain是一个用于构建LLM应用的框架"
    )
    
    # 添加短期记忆
    db_manager.add_short_term_message("user", "你好，很高兴认识你")
    db_manager.add_short_term_message("assistant", "你好！我也很高兴认识你！")
    db_manager.add_short_term_message("user", "你能帮我学习Python吗？")
    db_manager.add_short_term_message("assistant", "当然可以！我很乐意帮助你学习Python。")
    
    # 添加长期记忆
    db_manager.add_long_term_summary(
        summary="用户对Python编程感兴趣，希望学习相关知识。我们进行了友好的初次交流。",
        rounds=2,
        message_count=4,
        created_at=datetime.now().isoformat(),
        ended_at=datetime.now().isoformat()
    )
    
    # 添加情感分析
    db_manager.add_emotion_analysis(
        relationship_type="友好",
        emotional_tone="积极向上",
        overall_score=75,
        intimacy=60,
        trust=70,
        pleasure=80,
        resonance=75,
        dependence=50,
        analysis_summary="初次见面，用户表现出学习的积极性"
    )
    
    # 添加环境描述
    env_uuid = db_manager.create_environment(
        name="客厅",
        overall_description="温馨的家庭客厅",
        atmosphere="舒适、放松",
        lighting="柔和的灯光"
    )
    
    # 添加环境物体
    db_manager.add_environment_object(
        environment_uuid=env_uuid,
        name="沙发",
        description="舒适的三人沙发",
        position="客厅中央"
    )
    
    print("✓ 测试数据创建完成")
    print(f"  - 基础知识: 2 条")
    print(f"  - 实体: 1 个")
    print(f"  - 短期记忆: 4 条")
    print(f"  - 长期记忆: 1 条")
    print(f"  - 情感分析: 1 条")
    print(f"  - 环境描述: 1 个")
    print(f"  - 环境物体: 1 个")
    
    return db_manager

def test_full_export_import():
    """测试完整的导出和导入流程"""
    print("\n" + "=" * 50)
    print("测试完整导出导入流程")
    print("=" * 50)
    
    # 1. 创建包含数据的测试数据库
    source_db = setup_test_database()
    
    # 2. 导出所有数据
    print("\n开始导出...")
    migration = SettingsMigration(db_manager=source_db, env_path="example.env")
    
    export_result = migration.export_settings(
        export_path="full_test_export",
        include_env=True,
        selected_categories=None  # 导出所有类别
    )
    
    if not export_result['success']:
        print(f"✗ 导出失败: {export_result['message']}")
        return False
    
    print(f"✓ 导出成功: {export_result['exported_file']}")
    print(f"\n导出统计:")
    for key, count in export_result['stats'].items():
        category_name = migration.DATA_CATEGORIES.get(key, key)
        print(f"  - {category_name}: {count} 条")
    
    # 3. 预览导入文件
    print("\n开始预览导入文件...")
    preview = migration.preview_import("full_test_export.json")
    
    if not preview['success']:
        print(f"✗ 预览失败: {preview['message']}")
        return False
    
    print(f"✓ 预览成功")
    print(f"导出信息:")
    for key, value in preview['export_info'].items():
        print(f"  {key}: {value}")
    
    # 4. 导入到新数据库
    print("\n开始导入到新数据库...")
    target_db = DatabaseManager(db_path="test_imported.db")
    import_migration = SettingsMigration(db_manager=target_db, env_path="test_imported.env")
    
    import_result = import_migration.import_settings(
        import_path="full_test_export.json",
        import_env=True,
        import_database=True,
        overwrite=True,
        selected_categories=None
    )
    
    if not import_result['success']:
        print(f"✗ 导入失败: {import_result['message']}")
        return False
    
    print(f"✓ 导入成功")
    print(f"\n导入统计:")
    for key, count in import_result['stats'].items():
        category_name = migration.DATA_CATEGORIES.get(key, key)
        print(f"  - {category_name}: {count} 条")
    
    # 5. 验证导入的数据
    print("\n验证导入的数据...")
    
    # 验证基础知识
    base_facts = target_db.get_all_base_facts()
    print(f"✓ 基础知识数量: {len(base_facts)}")
    
    # 验证实体
    entities = target_db.get_all_entities()
    print(f"✓ 实体数量: {len(entities)}")
    
    # 验证短期记忆
    short_term = target_db.get_short_term_messages()
    print(f"✓ 短期记忆数量: {len(short_term)}")
    
    # 验证长期记忆
    long_term = target_db.get_long_term_summaries()
    print(f"✓ 长期记忆数量: {len(long_term)}")
    
    # 验证情感分析
    emotion = target_db.get_latest_emotion()
    print(f"✓ 情感分析: {'存在' if emotion else '不存在'}")
    
    # 验证环境
    environments = target_db.get_all_environments()
    print(f"✓ 环境数量: {len(environments)}")
    
    # 验证.env文件
    if os.path.exists("test_imported.env"):
        with open("test_imported.env", 'r', encoding='utf-8') as f:
            lines = [l.strip() for l in f.readlines() if l.strip() and not l.startswith('#')]
        print(f"✓ .env文件已创建，包含 {len(lines)} 行配置")
    
    return True

def test_selective_export():
    """测试选择性导出"""
    print("\n" + "=" * 50)
    print("测试选择性导出")
    print("=" * 50)
    
    db_manager = DatabaseManager(db_path="test_with_data.db")
    migration = SettingsMigration(db_manager=db_manager)
    
    # 只导出部分类别
    selected_categories = ['base_knowledge', 'entities', 'short_term_memory']
    
    result = migration.export_settings(
        export_path="selective_export",
        include_env=False,
        selected_categories=selected_categories
    )
    
    if not result['success']:
        print(f"✗ 选择性导出失败: {result['message']}")
        return False
    
    print(f"✓ 选择性导出成功")
    print(f"\n导出统计:")
    for key, count in result['stats'].items():
        category_name = migration.DATA_CATEGORIES.get(key, key)
        print(f"  - {category_name}: {count} 条")
    
    # 验证只导出了选中的类别
    import json
    with open("selective_export.json", 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    db_categories = data.get('database_data', {}).keys()
    print(f"\n实际导出的类别: {', '.join(db_categories)}")
    
    return True

def cleanup_test_files():
    """清理测试文件"""
    print("\n" + "=" * 50)
    print("清理测试文件")
    print("=" * 50)
    
    files_to_remove = [
        "test_with_data.db",
        "test_imported.db",
        "full_test_export.json",
        "selective_export.json",
        "test_imported.env"
    ]
    
    for filename in files_to_remove:
        if os.path.exists(filename):
            os.remove(filename)
            print(f"✓ 已删除: {filename}")

def main():
    """主测试函数"""
    print("\n🧪 开始扩展设定迁移测试\n")
    
    try:
        # 测试完整导出导入流程
        if not test_full_export_import():
            print("\n✗ 完整导出导入测试失败")
            return
        
        # 测试选择性导出
        if not test_selective_export():
            print("\n✗ 选择性导出测试失败")
            return
        
        print("\n" + "=" * 50)
        print("✓ 所有扩展测试通过！")
        print("=" * 50)
        
    except Exception as e:
        print(f"\n✗ 测试过程中出现错误: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # 清理测试文件
        cleanup_test_files()

if __name__ == '__main__':
    main()
