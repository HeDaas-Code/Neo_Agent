"""
测试增强知识库
验证EnhancedKnowledgeBase与DeepAgents的集成
"""

import os
import sys
import unittest
import tempfile
from unittest.mock import MagicMock, patch

# 添加项目路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.core.enhanced_knowledge_base import EnhancedKnowledgeBase
from src.core.database_manager import DatabaseManager


class TestEnhancedKnowledgeBase(unittest.TestCase):
    """测试EnhancedKnowledgeBase类"""
    
    def setUp(self):
        """测试前准备"""
        # 创建临时数据库
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.db_path = self.temp_db.name
        self.temp_db.close()
        
        # 设置环境变量
        os.environ['USE_DEEPAGENTS_KNOWLEDGE'] = 'false'  # 默认关闭，避免实际调用
        os.environ['SILICON_FLOW_API_KEY'] = 'test-key'
        
        # 创建数据库管理器
        self.db_manager = DatabaseManager(db_path=self.db_path)
    
    def tearDown(self):
        """测试后清理"""
        # 删除临时数据库
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)
    
    def test_initialization_without_deepagents(self):
        """测试不使用DeepAgents初始化"""
        kb = EnhancedKnowledgeBase(
            db_manager=self.db_manager,
            use_deepagents=False
        )
        
        # 验证
        self.assertFalse(kb.use_deepagents)
        self.assertIsNone(kb.deep_knowledge)
        self.assertIsNotNone(kb.db)
        self.assertIsNotNone(kb.base_knowledge)
    
    @patch('src.core.enhanced_knowledge_base.DeepAgentsKnowledgeManager')
    def test_initialization_with_deepagents(self, mock_manager):
        """测试使用DeepAgents初始化"""
        # Mock DeepAgentsKnowledgeManager
        mock_instance = MagicMock()
        mock_manager.return_value = mock_instance
        
        kb = EnhancedKnowledgeBase(
            db_manager=self.db_manager,
            use_deepagents=True
        )
        
        # 验证
        self.assertTrue(kb.use_deepagents)
        self.assertIsNotNone(kb.deep_knowledge)
        mock_manager.assert_called_once()
    
    def test_add_entity_definition_traditional(self):
        """测试传统方式添加实体定义"""
        kb = EnhancedKnowledgeBase(
            db_manager=self.db_manager,
            use_deepagents=False
        )
        
        # 添加定义
        entity_uuid = kb.add_or_update_entity_definition(
            entity_name='小明',
            definition='一个18岁的学生',
            confidence=0.9
        )
        
        # 验证
        self.assertIsNotNone(entity_uuid)
        
        # 检查数据库
        entity = self.db_manager.get_entity_by_name('小明')
        self.assertIsNotNone(entity)
        self.assertEqual(entity['name'], '小明')
        
        definition = self.db_manager.get_entity_definition(entity_uuid)
        self.assertIsNotNone(definition)
        self.assertEqual(definition['content'], '一个18岁的学生')
        self.assertEqual(definition['confidence'], 0.9)
    
    def test_add_entity_definition_large_content(self):
        """测试添加大型定义（应该使用文件系统）"""
        kb = EnhancedKnowledgeBase(
            db_manager=self.db_manager,
            use_deepagents=False  # 即使启用，由于内容>1000字符也会触发特殊处理
        )
        
        # 创建大型定义（>1000字符）
        large_definition = "这是一个非常长的定义。" * 100  # > 1000字符
        
        entity_uuid = kb.add_or_update_entity_definition(
            entity_name='复杂概念',
            definition=large_definition,
            use_deepagents=False  # 不使用deepagents，直接存数据库
        )
        
        # 验证
        self.assertIsNotNone(entity_uuid)
        definition = self.db_manager.get_entity_definition(entity_uuid)
        self.assertIsNotNone(definition)
        # 由于use_deepagents=False，应该直接存储到数据库
        self.assertEqual(definition['content'], large_definition)
    
    def test_add_related_info(self):
        """测试添加相关信息"""
        kb = EnhancedKnowledgeBase(
            db_manager=self.db_manager,
            use_deepagents=False
        )
        
        # 先添加实体
        entity_uuid = kb.add_or_update_entity_definition(
            entity_name='小红',
            definition='一个学生'
        )
        
        # 添加相关信息
        info_uuid = kb.add_related_info_to_entity(
            entity_uuid=entity_uuid,
            info_content='喜欢画画',
            info_type='爱好',
            confidence=0.8
        )
        
        # 验证
        self.assertIsNotNone(info_uuid)
        
        # 检查数据库
        related_infos = self.db_manager.get_entity_related_info(entity_uuid)
        self.assertEqual(len(related_infos), 1)
        self.assertEqual(related_infos[0]['content'], '喜欢画画')
        self.assertEqual(related_infos[0]['type'], '爱好')
    
    def test_get_relevant_knowledge_basic(self):
        """测试基本知识检索"""
        kb = EnhancedKnowledgeBase(
            db_manager=self.db_manager,
            use_deepagents=False
        )
        
        # 添加一些知识
        entity_uuid = kb.add_or_update_entity_definition(
            entity_name='Python',
            definition='一种编程语言'
        )
        kb.add_related_info_to_entity(
            entity_uuid=entity_uuid,
            info_content='由Guido van Rossum创建',
            info_type='历史'
        )
        
        # 检索知识
        result = kb.get_relevant_knowledge_for_query('Python是什么')
        
        # 验证
        self.assertIn('entities_found', result)
        self.assertIn('knowledge_items', result)
        self.assertIn('Python', result['entities_found'])
    
    @patch('src.core.enhanced_knowledge_base.DeepAgentsKnowledgeManager')
    def test_extract_knowledge_with_deepagents(self, mock_manager):
        """测试使用DeepAgents提取知识"""
        # Mock DeepAgentsKnowledgeManager
        mock_instance = MagicMock()
        mock_instance.extract_and_store_knowledge.return_value = {
            'success': True,
            'summary': '提取了3条知识'
        }
        mock_manager.return_value = mock_instance
        
        kb = EnhancedKnowledgeBase(
            db_manager=self.db_manager,
            use_deepagents=True
        )
        
        # 提取知识
        conversation = [
            {"role": "user", "content": "小明今年18岁"},
            {"role": "assistant", "content": "知道了"}
        ]
        
        result = kb.extract_knowledge_from_conversation(conversation)
        
        # 验证
        self.assertTrue(result.get('success'))
        self.assertEqual(result.get('summary'), '提取了3条知识')
        mock_instance.extract_and_store_knowledge.assert_called_once()


class TestEnhancedKnowledgeBaseCompatibility(unittest.TestCase):
    """测试EnhancedKnowledgeBase的向后兼容性"""
    
    def setUp(self):
        """测试前准备"""
        # 创建临时数据库
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.db_path = self.temp_db.name
        self.temp_db.close()
        
        os.environ['USE_DEEPAGENTS_KNOWLEDGE'] = 'false'
        
        # 创建数据库管理器
        self.db_manager = DatabaseManager(db_path=self.db_path)
    
    def tearDown(self):
        """测试后清理"""
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)
    
    def test_extract_entities_from_query(self):
        """测试从查询中提取实体"""
        kb = EnhancedKnowledgeBase(
            db_manager=self.db_manager,
            use_deepagents=False
        )
        
        # 添加一些实体
        kb.add_or_update_entity_definition('Python', '编程语言')
        kb.add_or_update_entity_definition('Java', '编程语言')
        
        # 提取实体
        entities = kb.extract_entities_from_query('Python和Java的区别是什么？')
        
        # 验证
        self.assertIn('Python', entities)
        self.assertIn('Java', entities)


if __name__ == '__main__':
    unittest.main()
