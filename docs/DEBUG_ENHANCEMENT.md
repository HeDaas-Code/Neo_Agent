# Debug功能增强说明

## 概述

Neo Agent的Debug功能已经增强，现在可以在捕获错误时自动显示错误发生的文件名、行号、函数名和相关代码，大大提高了调试效率。

## 新增功能

### 1. 错误位置追踪

当错误发生时，系统会自动捕获并显示：

- **文件名**: 错误发生的文件路径
- **行号**: 具体的代码行
- **函数名**: 错误发生在哪个函数中
- **代码内容**: 导致错误的实际代码

### 2. 堆栈跟踪

对于多层函数调用导致的错误，系统会显示完整的调用链：

```
完整堆栈跟踪:
  1. main.py:50 in main()
     process_data()
  2. processor.py:120 in process_data()
     validate_input(data)
  3. validator.py:35 in validate_input()
     if data['key'] is None:  # KeyError发生在这里
```

## 使用示例

### 在代码中使用

```python
from src.tools.debug_logger import get_debug_logger

logger = get_debug_logger()

try:
    # 你的代码
    result = risky_operation()
except Exception as e:
    # 自动记录错误位置和堆栈
    logger.log_error('MyModule', '操作失败', e)
```

### 在GUI中显示

GUI中的错误对话框现在会自动显示增强的错误信息：

```
初始化聊天代理时出错：

TypeError: __init__() got an unexpected keyword argument 'api_key'
位置: /path/to/knowledge_base.py:45
函数: __init__()
代码: super().__init__(api_key=api_key)

完整堆栈跟踪:
  1. chat_agent.py:380 in __init__()
     self.knowledge_base = KnowledgeBase(...)
  2. knowledge_base.py:45 in __init__()
     super().__init__(api_key=api_key)
```

## 错误格式说明

### 简洁模式

```
错误类型: 错误消息
位置: 文件名:行号
函数: 函数名()
代码: 相关代码行
```

### 详细模式

包含简洁模式的所有信息，外加：

```
完整堆栈跟踪:
  序号. 文件:行号 in 函数()
     代码行
  ...
```

## 日志文件

所有错误信息都会记录到 `debug.log` 文件中，包含：

1. 时间戳
2. 错误类型和消息
3. 文件位置信息
4. 完整的Python traceback

示例日志：

```
[2026-02-12T03:34:52.242] [ERROR] ChatAgent
  错误: 初始化失败
  异常: unexpected keyword argument 'api_key'
  位置: knowledge_base.py:45 in __init__()
  代码: super().__init__(api_key=api_key)
  完整堆栈:
Traceback (most recent call last):
  File "chat_agent.py", line 380, in __init__
    self.knowledge_base = KnowledgeBase(...)
  File "knowledge_base.py", line 45, in __init__
    super().__init__(api_key=api_key)
TypeError: __init__() got an unexpected keyword argument 'api_key'
```

## 配置

### 启用Debug模式

在 `.env` 文件中设置：

```bash
DEBUG_MODE=true
DEBUG_LOG_FILE=debug.log
```

### 不启用Debug模式

```bash
DEBUG_MODE=false
```

注意：即使不启用Debug模式，GUI中的错误对话框仍会显示增强的错误信息。

## 技术实现

### DebugLogger增强

```python
def log_error(self, module_name: str, error_message: str, exception: Exception = None):
    """记录错误信息（包含文件和行号）"""
    if exception:
        tb = sys.exc_info()[2]
        if tb:
            frames = traceback.extract_tb(tb)
            last_frame = frames[-1]
            file_info = {
                'filename': last_frame.filename,
                'line': last_frame.lineno,
                'function': last_frame.name,
                'code': last_frame.line
            }
```

### 静态格式化方法

```python
@staticmethod
def format_exception_with_location(exception: Exception, include_traceback: bool = True) -> str:
    """格式化异常信息，包含文件位置信息"""
    # 提取并格式化堆栈信息
    # 返回易读的错误报告
```

## 最佳实践

### 1. 在所有异常处理中使用

```python
try:
    # 代码
except Exception as e:
    logger.log_error('ModuleName', '描述性错误消息', e)
```

### 2. 在GUI中显示用户友好的错误

```python
except Exception as e:
    error_msg = DebugLogger.format_exception_with_location(e, include_traceback=True)
    messagebox.showerror("错误", f"操作失败:\n\n{error_msg}")
```

### 3. 定期检查日志文件

查看 `debug.log` 获取详细的错误历史和完整堆栈信息。

## 常见问题

### Q: 错误信息太长，如何简化？

A: 使用 `include_traceback=False` 参数：

```python
error_msg = DebugLogger.format_exception_with_location(e, include_traceback=False)
```

### Q: 如何获取特定模块的错误？

A: 使用 `get_logs` 方法过滤：

```python
logger = get_debug_logger()
errors = logger.get_logs(log_type='error', module_name='ChatAgent')
```

### Q: 错误位置显示的路径太长？

A: 日志系统显示完整路径以确保准确性。在GUI对话框中，可以手动提取文件名：

```python
import os
filename = os.path.basename(file_info['filename'])
```

## 相关文件

- `src/tools/debug_logger.py` - Debug日志器实现
- `src/gui/gui_enhanced.py` - GUI错误处理
- `debug.log` - 日志文件
- `.env` - 配置文件

## 更新历史

- **2026-02-12**: 初始版本，添加文件位置和堆栈跟踪功能
