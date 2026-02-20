"""
Cognee 智能记忆系统和世界观构建系统测试
"""

import os
import sys
import unittest
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))


class TestCogneeMemoryManager(unittest.TestCase):
    """测试 Cognee 记忆管理器"""
    
    def setUp(self):
        """测试前设置"""
        # 记录原始环境变量值，避免污染其他测试
        self._old_cognee_enabled = os.environ.get('COGNEE_ENABLED')
        # 禁用 Cognee 以避免依赖问题
        os.environ['COGNEE_ENABLED'] = 'false'
    
    def tearDown(self):
        """测试后恢复环境变量"""
        if self._old_cognee_enabled is None:
            # 原来未设置，则删除
            os.environ.pop('COGNEE_ENABLED', None)
        else:
            # 恢复原始值
            os.environ['COGNEE_ENABLED'] = self._old_cognee_enabled
    
    def test_import_cognee_memory(self):
        """测试导入 Cognee 记忆模块"""
        from src.core.cognee_memory import CogneeMemoryManager, CogneeMemorySyncWrapper
        self.assertTrue(callable(CogneeMemoryManager))
        self.assertTrue(callable(CogneeMemorySyncWrapper))
    
    def test_cognee_manager_disabled(self):
        """测试禁用状态下的 Cognee 管理器"""
        from src.core.cognee_memory import CogneeMemoryManager
        
        manager = CogneeMemoryManager(enabled=False)
        
        self.assertFalse(manager.enabled)
        self.assertFalse(manager._initialized)
    
    def test_cognee_manager_statistics(self):
        """测试获取统计信息"""
        from src.core.cognee_memory import CogneeMemoryManager
        
        manager = CogneeMemoryManager(enabled=False)
        stats = manager.get_statistics()
        
        self.assertIn('enabled', stats)
        self.assertIn('initialized', stats)
        self.assertIn('backend', stats)
        self.assertEqual(stats['backend'], 'cognee')
    
    def test_sync_wrapper_creation(self):
        """测试同步包装器创建"""
        from src.core.cognee_memory import CogneeMemorySyncWrapper, CogneeMemoryManager
        
        manager = CogneeMemoryManager(enabled=False)
        wrapper = CogneeMemorySyncWrapper(manager)
        
        self.assertIsNotNone(wrapper.manager)


class TestWorldviewBuilder(unittest.TestCase):
    """测试世界观构建器"""
    
    def setUp(self):
        """测试前设置"""
        self.test_dir = Path(__file__).parent / "test_worldview_temp"
        self.test_dir.mkdir(exist_ok=True)
    
    def tearDown(self):
        """测试后清理"""
        import shutil
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)
    
    def test_import_worldview_builder(self):
        """测试导入世界观构建模块"""
        from src.core.worldview_builder import WorldviewBuilder, WorldviewModule
        self.assertTrue(callable(WorldviewBuilder))
        self.assertTrue(callable(WorldviewModule))
    
    def test_worldview_module_creation(self):
        """测试世界观模块创建"""
        from src.core.worldview_builder import WorldviewModule
        
        module = WorldviewModule(
            name="测试模块",
            category="general",
            content="这是测试内容"
        )
        
        self.assertEqual(module.name, "测试模块")
        self.assertEqual(module.category, "general")
        self.assertEqual(module.content, "这是测试内容")
    
    def test_worldview_module_to_dict(self):
        """测试世界观模块转字典"""
        from src.core.worldview_builder import WorldviewModule
        
        module = WorldviewModule(
            name="测试",
            category="rules",
            content="规则内容"
        )
        
        data = module.to_dict()
        
        self.assertIn('name', data)
        self.assertIn('category', data)
        self.assertIn('content', data)
        self.assertIn('created_at', data)
    
    def test_worldview_module_from_dict(self):
        """测试从字典创建世界观模块"""
        from src.core.worldview_builder import WorldviewModule
        
        data = {
            'name': '测试',
            'category': 'locations',
            'content': '地点内容'
        }
        
        module = WorldviewModule.from_dict(data)
        
        self.assertEqual(module.name, '测试')
        self.assertEqual(module.category, 'locations')
    
    def test_worldview_builder_creation(self):
        """测试世界观构建器创建"""
        from src.core.worldview_builder import WorldviewBuilder
        
        builder = WorldviewBuilder(worldview_dir=str(self.test_dir))
        
        self.assertTrue(self.test_dir.exists())
    
    def test_worldview_builder_categories(self):
        """测试世界观分类"""
        from src.core.worldview_builder import WorldviewBuilder
        
        self.assertIn('general', WorldviewBuilder.CATEGORIES)
        self.assertIn('rules', WorldviewBuilder.CATEGORIES)
        self.assertIn('locations', WorldviewBuilder.CATEGORIES)
        self.assertIn('characters', WorldviewBuilder.CATEGORIES)
    
    def test_create_worldview_template(self):
        """测试创建世界观模板"""
        from src.core.worldview_builder import WorldviewBuilder
        
        builder = WorldviewBuilder(worldview_dir=str(self.test_dir))
        
        content = builder.create_worldview_from_natural_language(
            "一个测试世界",
            name="测试世界",
            use_llm=False
        )
        
        self.assertIn("测试世界", content)
        self.assertIn("#", content)  # Markdown 标题
    
    def test_save_and_load_worldview(self):
        """测试保存和加载世界观"""
        from src.core.worldview_builder import WorldviewBuilder
        
        builder = WorldviewBuilder(worldview_dir=str(self.test_dir))
        
        # 保存
        test_content = "# 测试世界观\n\n这是测试内容"
        success = builder.save_worldview("test_world", test_content)
        self.assertTrue(success)
        
        # 加载
        loaded_content = builder.load_worldview("test_world")
        self.assertEqual(loaded_content, test_content)
    
    def test_list_worldview_files(self):
        """测试列出世界观文件"""
        from src.core.worldview_builder import WorldviewBuilder
        
        builder = WorldviewBuilder(worldview_dir=str(self.test_dir))
        
        # 创建测试文件
        builder.save_worldview("world1", "# World 1")
        builder.save_worldview("world2", "# World 2")
        
        files = builder.list_worldview_files()
        
        self.assertEqual(len(files), 2)
        names = [f['name'] for f in files]
        self.assertIn('world1', names)
        self.assertIn('world2', names)
    
    def test_delete_worldview(self):
        """测试删除世界观"""
        from src.core.worldview_builder import WorldviewBuilder
        
        builder = WorldviewBuilder(worldview_dir=str(self.test_dir))
        
        # 创建并删除
        builder.save_worldview("to_delete", "# Delete me")
        self.assertTrue((self.test_dir / "to_delete.md").exists())
        
        success = builder.delete_worldview("to_delete")
        self.assertTrue(success)
        self.assertFalse((self.test_dir / "to_delete.md").exists())
    
    def test_parse_worldview_to_modules(self):
        """测试解析世界观为模块"""
        from src.core.worldview_builder import WorldviewBuilder
        
        builder = WorldviewBuilder(worldview_dir=str(self.test_dir))
        
        content = """# 测试世界

## 基本信息

这是基本信息内容。

## 规则设定

这是规则内容。

## 重要地点

这是地点内容。
"""
        
        modules = builder.parse_worldview_to_modules(content)
        
        self.assertGreater(len(modules), 0)
        # 检查模块是否被正确解析
        module_names = [m.name for m in modules]
        self.assertIn("基本信息", module_names)
    
    def test_infer_category(self):
        """测试分类推断"""
        from src.core.worldview_builder import WorldviewBuilder
        
        builder = WorldviewBuilder(worldview_dir=str(self.test_dir))
        
        self.assertEqual(builder._infer_category("基本信息"), "general")
        self.assertEqual(builder._infer_category("规则设定"), "rules")
        self.assertEqual(builder._infer_category("重要地点"), "locations")
        self.assertEqual(builder._infer_category("角色人物"), "characters")
    
    def test_get_statistics(self):
        """测试获取统计信息"""
        from src.core.worldview_builder import WorldviewBuilder
        
        builder = WorldviewBuilder(worldview_dir=str(self.test_dir))
        
        # 创建一些测试文件
        builder.save_worldview("stat_test1", "# Test 1")
        builder.save_worldview("stat_test2", "# Test 2")
        
        stats = builder.get_statistics()
        
        self.assertEqual(stats['worldview_count'], 2)
        self.assertIn('total_size_kb', stats)
        self.assertIn('categories', stats)


class TestLongTermMemoryIntegration(unittest.TestCase):
    """测试长期记忆与 Cognee 集成"""
    
    def setUp(self):
        """测试前设置"""
        os.environ['COGNEE_ENABLED'] = 'false'
        self.test_db = Path(__file__).parent / "test_ltm_temp.db"
    
    def tearDown(self):
        """测试后清理"""
        if self.test_db.exists():
            self.test_db.unlink()
    
    def test_long_term_memory_import(self):
        """测试导入长期记忆模块"""
        from src.core.long_term_memory import LongTermMemoryManager
        self.assertTrue(callable(LongTermMemoryManager))
    
    def test_long_term_memory_cognee_disabled(self):
        """测试禁用 Cognee 的长期记忆"""
        from src.core.long_term_memory import LongTermMemoryManager
        from src.core.database_manager import DatabaseManager
        
        # 使用临时文件数据库
        db = DatabaseManager(db_path=str(self.test_db))
        manager = LongTermMemoryManager(db_manager=db, enable_cognee=False)
        
        self.assertIsNone(manager.cognee_manager)
    
    def test_statistics_includes_cognee(self):
        """测试统计信息包含 Cognee"""
        from src.core.long_term_memory import LongTermMemoryManager
        from src.core.database_manager import DatabaseManager
        
        db = DatabaseManager(db_path=str(self.test_db))
        manager = LongTermMemoryManager(db_manager=db, enable_cognee=False)
        
        stats = manager.get_statistics()
        
        self.assertIn('cognee', stats)


class TestCogneeGUI(unittest.TestCase):
    """测试 Cognee GUI 模块"""
    
    def test_import_cognee_gui(self):
        """测试导入 Cognee GUI"""
        from src.gui.cognee_gui import CogneeMemoryGUI, WorldviewBuilderGUI, CogneeWorldviewManagerGUI
        self.assertTrue(callable(CogneeMemoryGUI))
        self.assertTrue(callable(WorldviewBuilderGUI))
        self.assertTrue(callable(CogneeWorldviewManagerGUI))


class TestDatabaseGUIIntegration(unittest.TestCase):
    """测试数据库 GUI 集成"""
    
    def test_database_gui_accepts_cognee_params(self):
        """测试数据库 GUI 接受 Cognee 参数"""
        from src.gui.database_gui import DatabaseManagerGUI
        import inspect
        
        # 检查初始化方法是否接受 cognee_manager 和 worldview_builder 参数
        sig = inspect.signature(DatabaseManagerGUI.__init__)
        params = list(sig.parameters.keys())
        
        self.assertIn('cognee_manager', params)
        self.assertIn('worldview_builder', params)


if __name__ == '__main__':
    unittest.main()
