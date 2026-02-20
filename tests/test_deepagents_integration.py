"""
测试DeepAgents集成
验证子智能体生成、长期记忆和知识管理功能
"""

import os
import sys
import unittest
from unittest.mock import MagicMock, patch

# 添加项目路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.core.deepagents_wrapper import DeepSubAgentWrapper, DeepAgentsKnowledgeManager


class TestDeepSubAgentWrapper(unittest.TestCase):
    """测试DeepSubAgentWrapper类"""
    
    def setUp(self):
        """测试前准备"""
        # 设置环境变量
        os.environ['SILICON_FLOW_API_KEY'] = 'test-key'
        os.environ['SILICON_FLOW_API_BASE'] = 'https://api.siliconflow.cn/v1'
        os.environ['TOOL_MODEL_NAME'] = 'Qwen/Qwen2.5-7B-Instruct'
    
    @patch('src.core.deepagents_wrapper.create_deep_agent')
    def test_initialization(self, mock_create_agent):
        """测试初始化"""
        # Mock create_deep_agent返回
        mock_agent = MagicMock()
        mock_create_agent.return_value = mock_agent
        
        # 创建包装器
        wrapper = DeepSubAgentWrapper(
            agent_id='test_agent',
            role='测试专家',
            description='负责测试'
        )
        
        # 验证
        self.assertEqual(wrapper.agent_id, 'test_agent')
        self.assertEqual(wrapper.role, '测试专家')
        self.assertIsNotNone(wrapper.checkpointer)  # 应该有checkpointer
        mock_create_agent.assert_called_once()
    
    @patch('src.core.deepagents_wrapper.create_deep_agent')
    def test_execute_task_basic(self, mock_create_agent):
        """测试基本任务执行"""
        # Mock agent
        mock_agent = MagicMock()
        mock_message = MagicMock()
        mock_message.content = "任务完成"
        mock_agent.invoke.return_value = {
            "messages": [mock_message]
        }
        mock_create_agent.return_value = mock_agent
        
        # 创建包装器并执行任务
        wrapper = DeepSubAgentWrapper(
            agent_id='test_agent',
            role='测试专家',
            description='负责测试'
        )
        
        result = wrapper.execute_task(
            task_description="完成测试任务",
            context={'key': 'value'}
        )
        
        # 验证
        self.assertEqual(result, "任务完成")
        mock_agent.invoke.assert_called_once()
    
    @patch('src.core.deepagents_wrapper.create_deep_agent')
    def test_execute_task_with_thread_id(self, mock_create_agent):
        """测试使用thread_id的任务执行（跨会话状态管理）"""
        # Mock agent
        mock_agent = MagicMock()
        mock_message = MagicMock()
        mock_message.content = "任务完成"
        mock_agent.invoke.return_value = {
            "messages": [mock_message]
        }
        mock_create_agent.return_value = mock_agent
        
        # 创建包装器
        wrapper = DeepSubAgentWrapper(
            agent_id='test_agent',
            role='测试专家',
            description='负责测试'
        )
        
        # 执行任务（指定thread_id）
        result = wrapper.execute_task(
            task_description="完成测试任务",
            context={'key': 'value'},
            thread_id='session_123'
        )
        
        # 验证invoke被调用时传递了正确的config
        call_args = mock_agent.invoke.call_args
        config = call_args[1]['config']
        self.assertEqual(config['configurable']['thread_id'], 'session_123')
    
    @patch('src.core.deepagents_wrapper.create_deep_agent')
    def test_get_state(self, mock_create_agent):
        """测试获取持久化状态"""
        # Mock agent
        mock_agent = MagicMock()
        mock_create_agent.return_value = mock_agent
        
        # 创建包装器
        wrapper = DeepSubAgentWrapper(
            agent_id='test_agent',
            role='测试专家',
            description='负责测试'
        )
        
        # 获取状态
        state = wrapper.get_state('thread_123')
        
        # 验证返回字典（即使是空的也应该是字典）
        self.assertIsInstance(state, dict)


class TestDeepAgentsKnowledgeManager(unittest.TestCase):
    """测试DeepAgentsKnowledgeManager类"""
    
    def setUp(self):
        """测试前准备"""
        os.environ['SILICON_FLOW_API_KEY'] = 'test-key'
        os.environ['SILICON_FLOW_API_BASE'] = 'https://api.siliconflow.cn/v1'
        os.environ['TOOL_MODEL_NAME'] = 'Qwen/Qwen2.5-7B-Instruct'
    
    def test_initialization(self):
        """测试初始化"""
        manager = DeepAgentsKnowledgeManager(
            knowledge_dir="/knowledge",
            memory_file="/memory/AGENTS.md"
        )
        
        # 验证
        self.assertEqual(manager.knowledge_dir, "/knowledge")
        self.assertEqual(manager.memory_file, "/memory/AGENTS.md")
        self.assertIsNotNone(manager.checkpointer)
    
    @patch('src.core.deepagents_wrapper.create_deep_agent')
    @patch('src.core.deepagents_wrapper.LangChainLLM')
    def test_extract_and_store_knowledge(self, mock_llm_class, mock_create_agent):
        """测试知识提取和存储"""
        # Mock LLM
        mock_llm = MagicMock()
        mock_llm_class.return_value.llm = mock_llm
        
        # Mock agent
        mock_agent = MagicMock()
        mock_message = MagicMock()
        mock_message.content = "已提取并存储3条知识"
        mock_agent.invoke.return_value = {
            "messages": [mock_message]
        }
        mock_create_agent.return_value = mock_agent
        
        # 创建管理器
        manager = DeepAgentsKnowledgeManager()
        
        # 测试知识提取
        conversation = [
            {"role": "user", "content": "小明今年18岁"},
            {"role": "assistant", "content": "知道了"}
        ]
        
        result = manager.extract_and_store_knowledge(conversation)
        
        # 验证
        self.assertTrue(result.get('success'))
        self.assertIn('summary', result)
    
    @patch('src.core.deepagents_wrapper.create_deep_agent')
    @patch('src.core.deepagents_wrapper.LangChainLLM')
    def test_retrieve_knowledge(self, mock_llm_class, mock_create_agent):
        """测试知识检索"""
        # Mock LLM
        mock_llm = MagicMock()
        mock_llm_class.return_value.llm = mock_llm
        
        # Mock agent
        mock_agent = MagicMock()
        mock_message = MagicMock()
        mock_message.content = "小明是一个18岁的学生"
        mock_agent.invoke.return_value = {
            "messages": [mock_message]
        }
        mock_create_agent.return_value = mock_agent
        
        # 创建管理器
        manager = DeepAgentsKnowledgeManager()
        
        # 测试知识检索
        result = manager.retrieve_knowledge("小明是谁")
        
        # 验证
        self.assertTrue(result.get('success'))
        self.assertIn('knowledge', result)


class TestFactoryFunction(unittest.TestCase):
    """测试工厂函数"""
    
    def setUp(self):
        """测试前准备"""
        os.environ['SILICON_FLOW_API_KEY'] = 'test-key'
        os.environ['USE_DEEP_AGENTS'] = 'false'  # 默认关闭，避免实际调用
    
    def test_create_traditional_subagent(self):
        """测试创建传统SubAgent"""
        from src.core.multi_agent_coordinator import create_sub_agent, SubAgent
        
        # 创建传统子智能体
        agent = create_sub_agent(
            agent_id='test',
            role='测试',
            description='测试描述',
            use_deep_agents=False
        )
        
        # 验证类型
        self.assertIsInstance(agent, SubAgent)
    
    @patch('src.core.multi_agent_coordinator.DeepSubAgentWrapper')
    def test_create_deep_subagent(self, mock_wrapper):
        """测试创建DeepSubAgentWrapper"""
        from src.core.multi_agent_coordinator import create_sub_agent
        
        # Mock wrapper
        mock_instance = MagicMock()
        mock_wrapper.return_value = mock_instance
        
        # 创建DeepAgents子智能体
        agent = create_sub_agent(
            agent_id='test',
            role='测试',
            description='测试描述',
            use_deep_agents=True
        )
        
        # 验证（包含新增的 skill_names 参数，默认为None）
        mock_wrapper.assert_called_once_with(
            agent_id='test',
            role='测试',
            description='测试描述',
            skill_names=None
        )
        self.assertEqual(agent, mock_instance)


if __name__ == '__main__':
    unittest.main()
