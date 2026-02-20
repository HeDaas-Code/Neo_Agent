"""
技能系统测试
验证SkillRegistry、DeepSubAgentWrapper技能集成和OmniAgent全能代理功能
"""

import os
import sys
import json
import sqlite3
import tempfile
import unittest
from unittest.mock import MagicMock, patch

# 添加项目路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


class TestSkillRegistry(unittest.TestCase):
    """测试SkillRegistry技能注册表"""

    def setUp(self):
        """每个测试使用独立的临时数据库"""
        self.db_fd, self.db_path = tempfile.mkstemp(suffix='.db')

    def tearDown(self):
        """清理临时数据库"""
        os.close(self.db_fd)
        os.unlink(self.db_path)

    def _make_registry(self):
        from src.core.skill_registry import SkillRegistry
        return SkillRegistry(db_path=self.db_path)

    def test_initialization_with_builtin_skills(self):
        """初始化时应加载所有内置技能"""
        registry = self._make_registry()
        skills = registry.list_skills(category='builtin')
        self.assertGreater(len(skills), 0, "应有内置技能")
        # 验证关键内置技能存在
        names = [s['name'] for s in skills]
        self.assertIn('task_decomposition', names)
        self.assertIn('result_synthesis', names)
        self.assertIn('information_retrieval', names)

    def test_get_existing_skill(self):
        """应能获取已存在的内置技能"""
        registry = self._make_registry()
        skill = registry.get_skill('task_decomposition')
        self.assertIsNotNone(skill)
        self.assertEqual(skill['name'], 'task_decomposition')
        self.assertEqual(skill['category'], 'builtin')
        # 验证内容包含步骤（中文）
        self.assertIn('步骤', skill['content'])

    def test_get_nonexistent_skill(self):
        """获取不存在的技能应返回None"""
        registry = self._make_registry()
        skill = registry.get_skill('nonexistent_skill_xyz')
        self.assertIsNone(skill)

    def test_add_user_skill(self):
        """应能添加用户自定义技能"""
        registry = self._make_registry()
        result = registry.add_skill(
            name='my_custom_skill',
            content='# 自定义技能\n\n## 步骤\n1. 步骤一\n2. 步骤二',
            category='user',
            description='自定义技能描述'
        )
        self.assertTrue(result)
        skill = registry.get_skill('my_custom_skill')
        self.assertIsNotNone(skill)
        self.assertEqual(skill['category'], 'user')

    def test_cannot_overwrite_builtin_skill(self):
        """不应允许覆盖内置技能"""
        registry = self._make_registry()
        result = registry.add_skill(
            name='task_decomposition',
            content='恶意覆盖内容',
            category='user'
        )
        self.assertFalse(result, "不应允许覆盖内置技能")
        # 内容应保持原始
        skill = registry.get_skill('task_decomposition')
        self.assertNotEqual(skill['content'], '恶意覆盖内容')

    def test_invalid_skill_name_rejected(self):
        """无效的技能名称应被拒绝"""
        registry = self._make_registry()
        # 包含大写字母
        self.assertFalse(registry.add_skill('InvalidName', 'content'))
        # 包含空格
        self.assertFalse(registry.add_skill('has space', 'content'))
        # 数字开头
        self.assertFalse(registry.add_skill('1starts_with_number', 'content'))

    def test_valid_skill_name_accepted(self):
        """有效的技能名称应被接受"""
        registry = self._make_registry()
        self.assertTrue(registry.add_skill('valid_skill', 'content', category='user'))
        self.assertTrue(registry.add_skill('valid123_skill', 'content', category='user'))

    def test_learn_skill(self):
        """自主学习应保存为learned类别"""
        registry = self._make_registry()
        result = registry.learn_skill(
            name='learned_skill_test',
            content='# 学习到的技能\n\n从任务中学到的方法',
            description='测试学习技能',
            source_task='测试任务'
        )
        self.assertTrue(result)
        skill = registry.get_skill('learned_skill_test')
        self.assertIsNotNone(skill)
        self.assertEqual(skill['category'], 'learned')
        self.assertIn('学习来源', skill['content'])

    def test_update_learned_skill(self):
        """应能更新已学习的技能（非内置）"""
        registry = self._make_registry()
        registry.learn_skill('updatable_skill', '初始内容')
        result = registry.add_skill('updatable_skill', '更新内容', category='learned')
        self.assertTrue(result)
        skill = registry.get_skill('updatable_skill')
        self.assertEqual(skill['content'], '更新内容')

    def test_get_skills_for_agent_all(self):
        """应能获取所有技能的文件字典"""
        registry = self._make_registry()
        files = registry.get_skills_for_agent()
        self.assertIsInstance(files, dict)
        self.assertGreater(len(files), 0)
        # 验证路径格式
        for path in files.keys():
            self.assertTrue(path.startswith('/skills/'), f"路径应以/skills/开头: {path}")
            self.assertTrue(path.endswith('.md'), f"路径应以.md结尾: {path}")

    def test_get_skills_for_agent_filtered(self):
        """应能按技能名称过滤文件字典"""
        registry = self._make_registry()
        files = registry.get_skills_for_agent(skill_names=['task_decomposition'])
        self.assertEqual(len(files), 1)
        # 验证内容包含task_decomposition
        content = list(files.values())[0]
        self.assertIn('分解', content)

    def test_record_usage_updates_count(self):
        """记录使用情况应更新计数"""
        registry = self._make_registry()
        registry.record_usage('task_decomposition', task_type='research', outcome='success')
        skill = registry.get_skill('task_decomposition')
        self.assertEqual(skill['usage_count'], 1)

    def test_get_skill_summary(self):
        """应能生成技能摘要"""
        registry = self._make_registry()
        summary = registry.get_skill_summary()
        self.assertIsInstance(summary, str)
        self.assertIn('技能', summary)

    def test_list_skills_by_category(self):
        """应能按类别列出技能"""
        registry = self._make_registry()
        registry.learn_skill('learned_one', '内容1', description='学习1')
        registry.learn_skill('learned_two', '内容2', description='学习2')

        learned = registry.list_skills(category='learned')
        names = [s['name'] for s in learned]
        self.assertIn('learned_one', names)
        self.assertIn('learned_two', names)

        builtin = registry.list_skills(category='builtin')
        for s in builtin:
            self.assertEqual(s['category'], 'builtin')


class TestGlobalSkillRegistry(unittest.TestCase):
    """测试全局单例"""

    def test_get_skill_registry_returns_same_instance(self):
        """全局注册表应为单例"""
        from src.core.skill_registry import get_skill_registry, _registry
        # 重置单例以测试
        import src.core.skill_registry as skill_mod
        original = skill_mod._registry
        skill_mod._registry = None
        try:
            r1 = get_skill_registry()
            r2 = get_skill_registry()
            self.assertIs(r1, r2, "应返回相同实例")
        finally:
            skill_mod._registry = original


class TestDeepSubAgentWrapperSkills(unittest.TestCase):
    """测试DeepSubAgentWrapper的技能集成"""

    def setUp(self):
        os.environ['SILICON_FLOW_API_KEY'] = 'test-key'
        os.environ['SILICON_FLOW_API_BASE'] = 'https://api.siliconflow.cn/v1'
        os.environ['TOOL_MODEL_NAME'] = 'Qwen/Qwen2.5-7B-Instruct'

    @patch('src.core.deepagents_wrapper.create_deep_agent')
    def test_initialization_with_skills(self, mock_create_agent):
        """包含技能路径时应正确初始化"""
        mock_create_agent.return_value = MagicMock()

        from src.core.deepagents_wrapper import DeepSubAgentWrapper
        wrapper = DeepSubAgentWrapper(
            agent_id='test_skilled',
            role='研究员',
            description='负责研究',
            skill_names=['information_retrieval']
        )

        self.assertEqual(wrapper.skill_names, ['information_retrieval'])
        # 验证create_deep_agent被调用时传递了skills参数
        call_kwargs = mock_create_agent.call_args[1]
        self.assertIn('skills', call_kwargs)
        self.assertIsInstance(call_kwargs['skills'], list)

    @patch('src.core.deepagents_wrapper.create_deep_agent')
    def test_execute_task_injects_skill_files(self, mock_create_agent):
        """执行任务时应注入技能文件"""
        mock_agent = MagicMock()
        mock_message = MagicMock()
        mock_message.content = "任务完成"
        mock_agent.invoke.return_value = {"messages": [mock_message]}
        mock_create_agent.return_value = mock_agent

        from src.core.deepagents_wrapper import DeepSubAgentWrapper
        wrapper = DeepSubAgentWrapper(
            agent_id='test_inject',
            role='研究员',
            description='负责研究'
        )

        result = wrapper.execute_task("完成测试任务", context={})
        self.assertEqual(result, "任务完成")

        # 验证invoke被调用时传递了files（技能文件）
        call_args = mock_agent.invoke.call_args
        input_data = call_args[0][0]
        self.assertIn('files', input_data, "应注入技能文件到files参数")
        files = input_data['files']
        self.assertIsInstance(files, dict)
        # 验证技能文件路径格式
        for path in files.keys():
            self.assertTrue(path.startswith('/skills/'))

    @patch('src.core.deepagents_wrapper.create_deep_agent')
    def test_learn_skill_invalidates_cache(self, mock_create_agent):
        """学习新技能后应使技能文件缓存失效"""
        mock_create_agent.return_value = MagicMock()

        from src.core.deepagents_wrapper import DeepSubAgentWrapper
        wrapper = DeepSubAgentWrapper(
            agent_id='test_learn',
            role='执行者',
            description='负责执行'
        )

        # 先触发缓存加载
        wrapper._get_skill_files()
        self.assertIsNotNone(wrapper._skill_files)

        # 学习新技能
        result = wrapper.learn_skill(
            skill_name='test_new_skill',
            skill_content='# 新技能\n\n新学到的方法',
            description='测试新技能'
        )
        self.assertTrue(result)
        # 缓存应已失效
        self.assertIsNone(wrapper._skill_files)


class TestOmniAgent(unittest.TestCase):
    """测试OmniAgent全能代理"""

    def setUp(self):
        os.environ['SILICON_FLOW_API_KEY'] = 'test-key'
        os.environ['SILICONFLOW_API_KEY'] = 'test-key'
        os.environ['SILICONFLOW_API_URL'] = 'https://api.siliconflow.cn/v1/chat/completions'

    @patch('src.core.omni_agent.create_deep_agent')
    def test_initialization(self, mock_create_agent):
        """全能代理应正确初始化"""
        mock_create_agent.return_value = MagicMock()

        from src.core.omni_agent import OmniAgent
        agent = OmniAgent(agent_id='test_omni')

        self.assertEqual(agent.agent_id, 'test_omni')
        self.assertIsNotNone(agent.skill_registry)
        self.assertIsNotNone(agent._agent)

        # 验证create_deep_agent被调用时传递了正确参数
        call_kwargs = mock_create_agent.call_args[1]
        self.assertIn('skills', call_kwargs)
        self.assertIn('subagents', call_kwargs)
        self.assertIsInstance(call_kwargs['subagents'], list)
        self.assertGreater(len(call_kwargs['subagents']), 0)

    @patch('src.core.omni_agent.create_deep_agent')
    def test_execute_task_success(self, mock_create_agent):
        """全能代理成功执行任务"""
        from src.core.omni_agent import LEARNING_MIN_OUTPUT_LEN
        mock_agent = MagicMock()
        mock_message = MagicMock()
        # 内容足够长（超过LEARNING_MIN_OUTPUT_LEN），可触发学习流程
        mock_message.content = "任务已完成。" * (LEARNING_MIN_OUTPUT_LEN // 5 + 1)
        mock_agent.invoke.return_value = {"messages": [mock_message]}
        mock_create_agent.return_value = mock_agent

        from src.core.omni_agent import OmniAgent
        agent = OmniAgent(agent_id='test_omni_exec', enable_auto_learning=False)

        result = agent.execute_task(
            task_description="测试任务",
            context={"key": "value"}
        )

        self.assertTrue(result['success'])
        self.assertIn('result', result)
        self.assertIn('thread_id', result)

    @patch('src.core.omni_agent.create_deep_agent')
    def test_execute_task_failure(self, mock_create_agent):
        """全能代理执行失败时应返回错误信息"""
        mock_agent = MagicMock()
        mock_agent.invoke.side_effect = Exception("模拟执行失败")
        mock_create_agent.return_value = mock_agent

        from src.core.omni_agent import OmniAgent
        agent = OmniAgent(agent_id='test_omni_fail', enable_auto_learning=False)

        result = agent.execute_task("失败的任务", context={})

        self.assertFalse(result['success'])
        self.assertIn('error', result)
        self.assertIn('执行失败', result['result'])

    @patch('src.core.omni_agent.create_deep_agent')
    def test_list_skills(self, mock_create_agent):
        """全能代理应能列出所有技能"""
        mock_create_agent.return_value = MagicMock()

        from src.core.omni_agent import OmniAgent
        agent = OmniAgent(agent_id='test_omni_skills')

        skills = agent.list_skills()
        self.assertIsInstance(skills, list)
        self.assertGreater(len(skills), 0)

    @patch('src.core.omni_agent.create_deep_agent')
    def test_add_skill(self, mock_create_agent):
        """全能代理应能手动添加技能"""
        mock_create_agent.return_value = MagicMock()

        from src.core.omni_agent import OmniAgent
        agent = OmniAgent(agent_id='test_omni_add')

        result = agent.add_skill(
            name='omni_test_skill',
            content='# 测试技能\n\n## 步骤\n1. 步骤一',
            description='测试用技能'
        )
        self.assertTrue(result)

        skill = agent.skill_registry.get_skill('omni_test_skill')
        self.assertIsNotNone(skill)


class TestGetSkillsForRole(unittest.TestCase):
    """测试角色技能映射函数"""

    def test_known_role_returns_skills(self):
        """已知角色应返回技能列表"""
        from src.core.omni_agent import _get_skills_for_role
        skills = _get_skills_for_role('研究员')
        self.assertIsInstance(skills, list)
        self.assertGreater(len(skills), 0)

    def test_fuzzy_match_role(self):
        """模糊匹配角色名"""
        from src.core.omni_agent import _get_skills_for_role
        skills = _get_skills_for_role('高级研究员')
        self.assertIsInstance(skills, list)
        # 应能模糊匹配到研究员

    def test_unknown_role_returns_list(self):
        """未知角色应返回（可能为空的）列表"""
        from src.core.omni_agent import _get_skills_for_role
        skills = _get_skills_for_role('完全未知角色xyz')
        self.assertIsInstance(skills, list)


class TestCreateSubAgentWithSkills(unittest.TestCase):
    """测试create_sub_agent工厂函数的技能参数"""

    def setUp(self):
        os.environ['SILICON_FLOW_API_KEY'] = 'test-key'
        os.environ['USE_DEEP_AGENTS'] = 'false'

    def test_create_traditional_subagent_ignores_skills(self):
        """传统SubAgent应忽略技能参数（不报错）"""
        from src.core.multi_agent_coordinator import create_sub_agent, SubAgent
        agent = create_sub_agent(
            agent_id='test',
            role='测试',
            description='测试描述',
            use_deep_agents=False,
            skill_names=['task_decomposition']
        )
        self.assertIsInstance(agent, SubAgent)

    @patch('src.core.multi_agent_coordinator.DeepSubAgentWrapper')
    def test_create_deep_subagent_with_skills(self, mock_wrapper):
        """DeepSubAgentWrapper应接收技能名称"""
        mock_instance = MagicMock()
        mock_wrapper.return_value = mock_instance

        from src.core.multi_agent_coordinator import create_sub_agent
        agent = create_sub_agent(
            agent_id='test',
            role='研究员',
            description='负责研究',
            use_deep_agents=True,
            skill_names=['information_retrieval', 'knowledge_extraction']
        )

        mock_wrapper.assert_called_once_with(
            agent_id='test',
            role='研究员',
            description='负责研究',
            skill_names=['information_retrieval', 'knowledge_extraction']
        )
        self.assertEqual(agent, mock_instance)


if __name__ == '__main__':
    unittest.main()
