"""
DebugLogger 模块的单元测试
"""

import unittest
import sys
import os
import tempfile

# 添加项目根目录到路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from debug_logger import DebugLogger


class TestDebugLogger(unittest.TestCase):
    """DebugLogger 类的单元测试"""

    def setUp(self):
        """每个测试方法执行前的设置"""
        # 使用临时文件进行测试
        self.temp_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.log')
        self.temp_file_path = self.temp_file.name
        self.temp_file.close()

    def tearDown(self):
        """每个测试方法执行后的清理"""
        # 删除临时日志文件
        if os.path.exists(self.temp_file_path):
            os.remove(self.temp_file_path)

    def test_init_default(self):
        """测试默认初始化"""
        logger = DebugLogger()
        self.assertFalse(logger.debug_mode)
        self.assertEqual(logger.log_file, 'debug.log')
        self.assertEqual(len(logger.logs), 0)
        self.assertIsInstance(logger.log_stats, dict)

    def test_init_with_debug_mode(self):
        """测试启用debug模式的初始化"""
        logger = DebugLogger(debug_mode=True, log_file=self.temp_file_path)
        self.assertTrue(logger.debug_mode)
        self.assertEqual(logger.log_file, self.temp_file_path)

    def test_log_stats_initialized(self):
        """测试日志统计初始化"""
        logger = DebugLogger()
        expected_keys = ['module', 'prompt', 'request', 'response', 'error', 'info']
        for key in expected_keys:
            self.assertIn(key, logger.log_stats)
            self.assertEqual(logger.log_stats[key], 0)

    def test_logs_list_initialized(self):
        """测试日志列表初始化"""
        logger = DebugLogger()
        self.assertIsInstance(logger.logs, list)
        self.assertEqual(len(logger.logs), 0)

    def test_listeners_initialized(self):
        """测试监听器列表初始化"""
        logger = DebugLogger()
        self.assertIsInstance(logger.listeners, list)
        self.assertEqual(len(logger.listeners), 0)

    def test_custom_log_file(self):
        """测试自定义日志文件路径"""
        custom_path = self.temp_file_path
        logger = DebugLogger(log_file=custom_path)
        self.assertEqual(logger.log_file, custom_path)


class TestDebugLoggerLogging(unittest.TestCase):
    """测试 DebugLogger 的日志记录功能"""

    def setUp(self):
        """设置测试环境"""
        self.temp_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.log')
        self.temp_file_path = self.temp_file.name
        self.temp_file.close()
        self.logger = DebugLogger(debug_mode=True, log_file=self.temp_file_path)

    def tearDown(self):
        """清理测试环境"""
        if os.path.exists(self.temp_file_path):
            os.remove(self.temp_file_path)

    def test_logger_with_debug_mode(self):
        """测试启用debug模式的logger"""
        self.assertTrue(self.logger.debug_mode)
        self.assertEqual(self.logger.log_file, self.temp_file_path)


if __name__ == '__main__':
    unittest.main()
