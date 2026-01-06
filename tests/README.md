# Neo Agent 单元测试

本目录包含 Neo Agent 项目的单元测试代码。

## 目录结构

```
tests/
├── __init__.py              # 测试包初始化文件
├── README.md                # 本文件
├── test_debug_logger.py     # DebugLogger 模块的单元测试
└── test_event_manager.py    # EventManager 模块的单元测试
```

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

## 注意事项

- 测试文件不应修改生产数据库或配置文件
- 使用临时文件或内存数据库进行测试
- 避免测试依赖外部 API 或网络连接
- 使用 mock 对象模拟外部依赖
