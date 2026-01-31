"""
测试设定迁移功能的脚本
"""

import os
import sys
from src.tools.settings_migration import SettingsMigration
from src.core.database_manager import DatabaseManager

def test_export():
    """测试导出功能"""
    print("=" * 50)
    print("测试设定导出功能")
    print("=" * 50)
    
    # 创建数据库管理器（会创建测试数据库）
    db_manager = DatabaseManager(db_path="test_agent.db")
    
    # 创建迁移管理器
    migration = SettingsMigration(db_manager=db_manager, env_path="example.env")
    
    # 测试导出（选择部分类别）
    selected_categories = [
        'base_knowledge',
        'entities',
        'short_term_memory',
        'long_term_memory'
    ]
    
    result = migration.export_settings(
        export_path="test_export",
        include_env=True,
        selected_categories=selected_categories
    )
    
    print(f"\n导出结果: {'成功' if result['success'] else '失败'}")
    print(f"消息: {result['message']}")
    if result['success']:
        print(f"导出文件: {result['exported_file']}")
        print(f"\n导出统计:")
        for key, count in result['stats'].items():
            print(f"  - {key}: {count}")
    
    return result['success']

def test_preview():
    """测试预览功能"""
    print("\n" + "=" * 50)
    print("测试导入预览功能")
    print("=" * 50)
    
    db_manager = DatabaseManager(db_path="test_agent.db")
    migration = SettingsMigration(db_manager=db_manager)
    
    # 预览刚导出的文件
    if not os.path.exists("test_export.json"):
        print("✗ 导出文件不存在，跳过预览测试")
        return False
    
    preview = migration.preview_import("test_export.json")
    
    print(f"\n预览结果: {'成功' if preview['success'] else '失败'}")
    if preview['success']:
        print(f"\n导出信息:")
        for key, value in preview['export_info'].items():
            print(f"  {key}: {value}")
        
        print(f"\n环境变量数量: {preview['env_settings_count']}")
        
        print(f"\n数据类别:")
        for category_key, info in preview['categories'].items():
            print(f"  - {info['name']}: {info['count']} 条")
    else:
        print(f"消息: {preview['message']}")
    
    return preview['success']

def test_import():
    """测试导入功能"""
    print("\n" + "=" * 50)
    print("测试设定导入功能")
    print("=" * 50)
    
    # 使用新的数据库文件进行导入测试
    db_manager = DatabaseManager(db_path="test_import_agent.db")
    migration = SettingsMigration(db_manager=db_manager, env_path="test_import.env")
    
    if not os.path.exists("test_export.json"):
        print("✗ 导出文件不存在，跳过导入测试")
        return False
    
    result = migration.import_settings(
        import_path="test_export.json",
        import_env=True,
        import_database=True,
        overwrite=True,
        selected_categories=None  # 导入所有类别
    )
    
    print(f"\n导入结果: {'成功' if result['success'] else '失败'}")
    print(f"消息: {result['message']}")
    if result['success']:
        if 'backup_env' in result:
            print(f"备份文件: {result['backup_env']}")
        
        print(f"\n导入统计:")
        for key, count in result['stats'].items():
            print(f"  - {key}: {count}")
    
    return result['success']

def cleanup():
    """清理测试文件"""
    print("\n" + "=" * 50)
    print("清理测试文件")
    print("=" * 50)
    
    files_to_remove = [
        "test_agent.db",
        "test_import_agent.db",
        "test_export.json",
        "test_import.env"
    ]
    
    for filename in files_to_remove:
        if os.path.exists(filename):
            os.remove(filename)
            print(f"✓ 已删除: {filename}")
        else:
            print(f"○ 文件不存在: {filename}")

def main():
    """主测试函数"""
    print("开始测试设定迁移功能\n")
    
    try:
        # 测试导出
        if not test_export():
            print("\n✗ 导出测试失败")
            return
        
        # 测试预览
        if not test_preview():
            print("\n✗ 预览测试失败")
            return
        
        # 测试导入
        if not test_import():
            print("\n✗ 导入测试失败")
            return
        
        print("\n" + "=" * 50)
        print("✓ 所有测试通过！")
        print("=" * 50)
        
    except Exception as e:
        print(f"\n✗ 测试过程中出现错误: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # 清理测试文件
        cleanup()

if __name__ == '__main__':
    main()
