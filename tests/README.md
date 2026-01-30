# Neo Agent 单元测试

本目录包含 Neo Agent 项目的单元测试代码。

## 目录结构

```
tests/
├── __init__.py                  # 测试包初始化文件
├── README.md                    # 本文件
├── test_debug_logger.py         # DebugLogger 模块的单元测试
├── test_event_manager.py        # EventManager 模块的单元测试
├── test_schedule_manager.py     # ScheduleManager 模块的单元测试
└── test_schedule_similarity.py  # 日程相似度检查的单元测试
```

## 测试覆盖的模块

### 已有测试
- **DebugLogger** - 调试日志记录器
- **EventManager** - 事件管理器
- **ScheduleManager** - 日程管理器
- **ScheduleSimilarityChecker** - 日程相似度检查器

### 需要添加测试的模块
- **ExpressionStyleManager** - 表达风格管理器
- **BaseKnowledge** - 基础知识管理器
- **DatabaseManager** - 数据库管理器（核心功能）
- **ChatAgent** - 对话代理（集成测试）
- **KnowledgeBase** - 知识库管理
- **EmotionAnalyzer** - 情感分析
- **MultiAgentCoordinator** - 多智能体协调器
- **AgentVisionTool** - 视觉工具（环境域系统）

## 运行测试

### 使用 unittest 运行所有测试

```bash
# 从项目根目录运行所有测试
python -m unittest discover tests

# 运行特定测试文件
python -m unittest tests.test_debug_logger

# 运行特定测试类
python -m unittest tests.test_debug_logger.TestDebugLogger

# 运行特定测试方法
python -m unittest tests.test_debug_logger.TestDebugLogger.test_init
```

### 使用 pytest 运行测试（如果已安装）

```bash
# 安装 pytest
pip install pytest

# 运行所有测试
pytest tests/

# 运行特定测试文件
pytest tests/test_debug_logger.py

# 显示详细输出
pytest -v tests/

# 显示print输出
pytest -s tests/
```

## 编写新测试

在 `tests/` 目录下创建新的测试文件，文件名必须以 `test_` 开头。

### 示例测试模板

```python
"""
模块名称的单元测试
"""

import unittest
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from your_module import YourClass


class TestYourClass(unittest.TestCase):
    """YourClass 的单元测试"""

    def setUp(self):
        """每个测试方法执行前的设置"""
        self.instance = YourClass()

    def tearDown(self):
        """每个测试方法执行后的清理"""
        pass

    def test_something(self):
        """测试某个功能"""
        result = self.instance.some_method()
        self.assertEqual(result, expected_value)


if __name__ == '__main__':
    unittest.main()
```

## 测试最佳实践

1. **测试命名**：测试方法名应清晰描述测试内容，如 `test_init_with_debug_mode`
2. **独立性**：每个测试应该独立运行，不依赖其他测试
3. **清理**：在 `tearDown` 中清理测试创建的文件或数据
4. **断言**：使用合适的断言方法，如 `assertEqual`、`assertTrue`、`assertRaises` 等
5. **覆盖率**：尽量覆盖各种情况，包括正常情况和异常情况
6. **Mock外部依赖**：使用mock对象模拟API调用、数据库操作等外部依赖
7. **测试数据隔离**：使用临时数据库或内存数据库，避免影响生产数据
8. **测试文档**：为复杂测试添加注释说明测试目的和预期结果

## 编写新模块测试指南

### ExpressionStyleManager 测试要点

```python
def test_add_agent_expression(self):
    """测试添加智能体表达"""
    manager = ExpressionStyleManager()
    expr_uuid = manager.add_agent_expression(
        expression="wc",
        meaning="表示对突发事情的感叹",
        category="感叹词"
    )
    self.assertIsNotNone(expr_uuid)
    
    # 验证表达已添加
    expressions = manager.get_agent_expressions()
    self.assertTrue(any(e['expression'] == 'wc' for e in expressions))

def test_learn_from_conversation(self):
    """测试从对话中学习用户习惯"""
    manager = ExpressionStyleManager()
    messages = [
        {'role': 'user', 'content': '哈哈哈，太好笑了'},
        {'role': 'assistant', 'content': '是的呢'},
        # 添加更多测试消息...
    ]
    result = manager.learn_from_conversation(messages)
    self.assertIn('learned', result)
```

### BaseKnowledge 测试要点

```python
def test_add_base_fact(self):
    """测试添加基础事实"""
    bk = BaseKnowledge()
    success = bk.add_base_fact(
        entity_name="TestEntity",
        fact_content="Test content",
        category="Test"
    )
    self.assertTrue(success)
    
    # 验证事实已添加
    fact = bk.get_base_fact("TestEntity")
    self.assertEqual(fact['content'], "Test content")

def test_immutable_fact(self):
    """测试不可变事实不能被覆盖"""
    bk = BaseKnowledge()
    bk.add_base_fact(
        entity_name="ImmutableEntity",
        fact_content="Original content",
        immutable=True
    )
    
    # 尝试覆盖应该失败
    success = bk.add_base_fact(
        entity_name="ImmutableEntity",
        fact_content="New content",
        immutable=True
    )
    self.assertFalse(success)
    
    # 验证内容未改变
    fact = bk.get_base_fact("ImmutableEntity")
    self.assertEqual(fact['content'], "Original content")
```

### 数据库相关测试

```python
def setUp(self):
    """为每个测试创建临时数据库"""
    self.test_db = "test_temp.db"
    self.db_manager = DatabaseManager(db_path=self.test_db)

def tearDown(self):
    """清理测试数据库"""
    import os
    if os.path.exists(self.test_db):
        os.remove(self.test_db)
```

## 注意事项

- 测试文件不应修改生产数据库或配置文件
- 使用临时文件或内存数据库进行测试
- 避免测试依赖外部 API 或网络连接
- 使用 mock 对象模拟外部依赖
