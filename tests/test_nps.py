"""
NPS (Neo Plugin System) 模块的单元测试
"""

import unittest
import sys
import os
import json
import tempfile
import shutil

# 添加项目根目录到路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from NPS.nps_registry import NPSRegistry, NPSTool
from NPS.nps_invoker import NPSInvoker


class TestNPSTool(unittest.TestCase):
    """测试 NPSTool 类"""

    def test_tool_creation(self):
        """测试工具创建"""
        def test_func(context):
            return {'result': 'test'}
        
        tool = NPSTool(
            tool_id='test_tool',
            name='测试工具',
            description='这是一个测试工具',
            keywords=['测试', '关键词'],
            execute_func=test_func
        )
        
        self.assertEqual(tool.tool_id, 'test_tool')
        self.assertEqual(tool.name, '测试工具')
        self.assertEqual(tool.description, '这是一个测试工具')
        self.assertEqual(tool.keywords, ['测试', '关键词'])
        self.assertTrue(tool.enabled)

    def test_tool_execution(self):
        """测试工具执行"""
        def test_func(context):
            return {'context': f"收到输入: {context.get('user_input', '')}"}
        
        tool = NPSTool(
            tool_id='test_tool',
            name='测试工具',
            description='测试',
            keywords=[],
            execute_func=test_func
        )
        
        result = tool.execute({'user_input': 'hello'})
        
        self.assertTrue(result['success'])
        self.assertEqual(result['tool_id'], 'test_tool')
        self.assertEqual(result['result']['context'], '收到输入: hello')

    def test_tool_to_dict(self):
        """测试工具转字典"""
        def test_func(context):
            return {}
        
        tool = NPSTool(
            tool_id='test_tool',
            name='测试工具',
            description='测试',
            keywords=['关键词'],
            execute_func=test_func,
            version='2.0.0',
            author='测试作者'
        )
        
        tool_dict = tool.to_dict()
        
        self.assertEqual(tool_dict['tool_id'], 'test_tool')
        self.assertEqual(tool_dict['version'], '2.0.0')
        self.assertEqual(tool_dict['author'], '测试作者')


class TestNPSRegistry(unittest.TestCase):
    """测试 NPSRegistry 类"""

    def setUp(self):
        """设置测试环境"""
        # 创建临时目录作为工具目录
        self.temp_dir = tempfile.mkdtemp()
        self.registry = NPSRegistry(tools_dir=self.temp_dir)

    def tearDown(self):
        """清理测试环境"""
        shutil.rmtree(self.temp_dir)

    def test_registry_initialization(self):
        """测试注册表初始化"""
        self.assertEqual(len(self.registry.get_all_tools()), 0)

    def test_manual_tool_registration(self):
        """测试手动注册工具"""
        def test_func(context):
            return {}
        
        tool = NPSTool(
            tool_id='manual_tool',
            name='手动注册工具',
            description='测试手动注册',
            keywords=['手动'],
            execute_func=test_func
        )
        
        result = self.registry.register_tool(tool)
        
        self.assertTrue(result)
        self.assertEqual(len(self.registry.get_all_tools()), 1)
        self.assertIsNotNone(self.registry.get_tool('manual_tool'))

    def test_tool_unregistration(self):
        """测试注销工具"""
        def test_func(context):
            return {}
        
        tool = NPSTool(
            tool_id='temp_tool',
            name='临时工具',
            description='测试',
            keywords=[],
            execute_func=test_func
        )
        
        self.registry.register_tool(tool)
        self.assertEqual(len(self.registry.get_all_tools()), 1)
        
        result = self.registry.unregister_tool('temp_tool')
        
        self.assertTrue(result)
        self.assertEqual(len(self.registry.get_all_tools()), 0)

    def test_scan_and_register_with_nps_file(self):
        """测试通过 .NPS 文件自动注册"""
        # 创建测试工具模块
        module_content = '''
def test_execute(context):
    return {'context': '测试结果'}
'''
        module_path = os.path.join(self.temp_dir, 'test_module.py')
        with open(module_path, 'w', encoding='utf-8') as f:
            f.write(module_content)
        
        # 创建 .NPS 元数据文件
        nps_content = {
            'tool_id': 'test_module',
            'name': '测试模块',
            'description': '自动注册测试',
            'module': 'test_module',
            'function': 'test_execute',
            'keywords': ['测试']
        }
        nps_path = os.path.join(self.temp_dir, 'test_module.NPS')
        with open(nps_path, 'w', encoding='utf-8') as f:
            json.dump(nps_content, f)
        
        # 扫描并注册
        registered = self.registry.scan_and_register()
        
        self.assertEqual(len(registered), 1)
        self.assertIn('test_module', registered)
        
        tool = self.registry.get_tool('test_module')
        self.assertIsNotNone(tool)
        self.assertEqual(tool.name, '测试模块')

    def test_get_statistics(self):
        """测试获取统计信息"""
        def test_func(context):
            return {}
        
        tool = NPSTool(
            tool_id='stat_tool',
            name='统计测试工具',
            description='测试',
            keywords=[],
            execute_func=test_func,
            enabled=True
        )
        self.registry.register_tool(tool)
        
        stats = self.registry.get_statistics()
        
        self.assertEqual(stats['total_tools'], 1)
        self.assertEqual(stats['enabled_tools'], 1)
        self.assertEqual(stats['disabled_tools'], 0)


class TestNPSInvoker(unittest.TestCase):
    """测试 NPSInvoker 类"""

    def setUp(self):
        """设置测试环境"""
        self.temp_dir = tempfile.mkdtemp()
        self.registry = NPSRegistry(tools_dir=self.temp_dir)
        self.invoker = NPSInvoker(registry=self.registry)

    def tearDown(self):
        """清理测试环境"""
        shutil.rmtree(self.temp_dir)

    def test_invoker_initialization(self):
        """测试调用器初始化"""
        self.assertIsNotNone(self.invoker.registry)

    def test_keyword_matching(self):
        """测试关键词匹配"""
        def time_func(context):
            return {'context': '现在是下午3点'}
        
        tool = NPSTool(
            tool_id='time_tool',
            name='时间工具',
            description='获取时间',
            keywords=['时间', '几点', '现在'],
            execute_func=time_func
        )
        self.registry.register_tool(tool)
        
        # 测试关键词匹配
        match = self.invoker._match_keywords('现在几点了？', tool)
        self.assertTrue(match)
        
        # 测试不匹配
        no_match = self.invoker._match_keywords('你好', tool)
        self.assertFalse(no_match)

    def test_fallback_keyword_match(self):
        """测试关键词匹配降级"""
        def test_func(context):
            return {'context': '测试结果'}
        
        tool = NPSTool(
            tool_id='test_tool',
            name='测试工具',
            description='测试',
            keywords=['测试', '关键词'],
            execute_func=test_func
        )
        self.registry.register_tool(tool)
        
        result = self.invoker._fallback_keyword_match('这是一个测试', [tool])
        
        self.assertEqual(len(result), 1)
        self.assertIn('test_tool', result)

    def test_invoke_relevant_tools_no_tools(self):
        """测试没有工具时的调用"""
        result = self.invoker.invoke_relevant_tools('任意输入')
        
        self.assertEqual(result['tools_invoked'], [])
        self.assertEqual(result['context_info'], '')
        self.assertFalse(result['has_context'])

    def test_invoke_relevant_tools_with_keyword_match(self):
        """测试使用关键词匹配调用工具"""
        def time_func(context):
            return {'context': '现在是下午3点'}
        
        tool = NPSTool(
            tool_id='time_tool',
            name='时间工具',
            description='获取时间',
            keywords=['时间', '几点'],
            execute_func=time_func
        )
        self.registry.register_tool(tool)
        
        # 使用关键词匹配（不使用LLM）
        result = self.invoker.invoke_relevant_tools('现在几点了？', use_llm=False)
        
        self.assertTrue(result['has_context'])
        self.assertIn('时间工具', result['context_info'])

    def test_get_context_for_understanding(self):
        """测试获取理解阶段上下文"""
        def test_func(context):
            return {'context': '测试上下文'}
        
        tool = NPSTool(
            tool_id='test_tool',
            name='测试工具',
            description='测试',
            keywords=['测试'],
            execute_func=test_func
        )
        self.registry.register_tool(tool)
        
        context = self.invoker.get_context_for_understanding('这是测试')
        
        self.assertIsNotNone(context)
        self.assertIn('测试上下文', context)

    def test_format_nps_prompt(self):
        """测试格式化NPS提示词"""
        context_info = "当前时间：15:30"
        prompt = self.invoker.format_nps_prompt(context_info)
        
        self.assertIn('NPS工具信息', prompt)
        self.assertIn('当前时间：15:30', prompt)


class TestSysTimeModule(unittest.TestCase):
    """测试 SysTime 示例模块"""

    def test_systime_execution(self):
        """测试系统时间模块执行"""
        from NPS.tool.systime import get_system_time
        
        result = get_system_time()
        
        self.assertIn('datetime', result)
        self.assertIn('date', result)
        self.assertIn('time', result)
        self.assertIn('weekday', result)
        self.assertIn('period', result)
        self.assertIn('context', result)
        
        # 验证星期格式
        self.assertTrue(result['weekday'].startswith('星期'))
        
        # 验证时段
        valid_periods = ['清晨', '上午', '中午', '下午', '晚上', '深夜']
        self.assertIn(result['period'], valid_periods)


class TestNPSIntegration(unittest.TestCase):
    """NPS系统集成测试"""

    def test_full_workflow(self):
        """测试完整工作流程"""
        # 使用项目实际的NPS工具目录
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
        tools_dir = os.path.join(project_root, 'NPS', 'tool')
        
        # 创建注册表并扫描
        registry = NPSRegistry(tools_dir=tools_dir)
        registered = registry.scan_and_register()
        
        # 验证systime工具被注册
        self.assertIn('systime', registered)
        
        # 创建调用器
        invoker = NPSInvoker(registry=registry)
        
        # 测试时间相关查询
        result = invoker.invoke_relevant_tools('现在几点了？', use_llm=False)
        
        self.assertTrue(result['has_context'])
        self.assertIn('系统时间', result['context_info'])


if __name__ == '__main__':
    unittest.main()
