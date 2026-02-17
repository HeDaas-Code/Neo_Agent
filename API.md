# API Documentation / API文档

## 核心API / Core APIs

### ChatAgent

对话代理核心类。

```python
from src.core.chat_agent import ChatAgent

# 创建实例
agent = ChatAgent()

# 发送消息
response = agent.chat(user_message="你好")

# 获取短期记忆
short_memory = agent.get_short_term_memory()

# 获取长期记忆摘要
long_memory = agent.get_long_term_summary()
```

**主要方法**:
- `chat(user_message: str) -> str`: 发送消息并获取回复
- `get_short_term_memory() -> List[Dict]`: 获取短期记忆
- `get_long_term_summary() -> str`: 获取长期记忆摘要
- `reset_memory()`: 重置记忆

---

### DatabaseManager

数据库管理器，提供统一的数据存储接口。

```python
from src.core.database_manager import DatabaseManager

# 创建实例
db = DatabaseManager()

# 保存对话
db.save_conversation(user_msg, agent_msg, timestamp)

# 查询对话历史
history = db.get_conversation_history(limit=20)

# 保存知识
db.save_knowledge(content, category, timestamp)

# 查询知识
knowledge = db.query_knowledge(keyword="Python")
```

**主要方法**:
- `save_conversation(user_msg, agent_msg, timestamp)`: 保存对话
- `get_conversation_history(limit)`: 获取对话历史
- `save_knowledge(content, category, timestamp)`: 保存知识
- `query_knowledge(keyword)`: 查询知识
- `export_data()`: 导出所有数据
- `import_data(data)`: 导入数据

---

### EmotionAnalyzer

情感关系分析器。

```python
from src.core.emotion_analyzer import EmotionAnalyzer

# 创建实例
analyzer = EmotionAnalyzer(character_name="Neo")

# 分析情感
emotion_data = analyzer.analyze_emotion(conversation_history)

# 获取情感评分
score = analyzer.get_emotion_score()

# 格式化显示
summary = analyzer.format_emotion_summary(emotion_data)
```

**主要方法**:
- `analyze_emotion(conversation_history) -> Dict`: 分析情感
- `get_emotion_score() -> int`: 获取评分 (0-100)
- `update_emotion_score(delta)`: 更新评分
- `get_impression() -> str`: 获取印象描述

---

### EventManager

事件管理器，支持事件驱动编程。

```python
from src.core.event_manager import EventManager

# 创建实例
event_mgr = EventManager()

# 创建通知事件
event_mgr.create_event(
    event_type="notification",
    title="提醒",
    content="这是一个通知",
    trigger_time="2026-02-01 10:00:00"
)

# 创建任务事件
event_mgr.create_event(
    event_type="task",
    title="数据分析",
    content="分析用户数据",
    trigger_time="2026-02-01 14:00:00"
)

# 获取待触发事件
pending = event_mgr.get_pending_events()

# 触发事件
event_mgr.trigger_event(event_id)
```

**主要方法**:
- `create_event(event_type, title, content, trigger_time)`: 创建事件
- `get_pending_events() -> List[Dict]`: 获取待触发事件
- `trigger_event(event_id)`: 触发事件
- `cancel_event(event_id)`: 取消事件
- `get_event_history() -> List[Dict]`: 获取历史事件

---

### KnowledgeBase

知识库管理器。

```python
from src.core.knowledge_base import KnowledgeBase

# 创建实例
kb = KnowledgeBase()

# 添加知识
kb.add_knowledge(
    content="Python是一种高级编程语言",
    category="编程",
    source="对话"
)

# 搜索知识
results = kb.search_knowledge(keyword="Python")

# 按分类获取
python_knowledge = kb.get_by_category("编程")

# 获取所有分类
categories = kb.get_all_categories()
```

**主要方法**:
- `add_knowledge(content, category, source)`: 添加知识
- `search_knowledge(keyword) -> List[Dict]`: 搜索知识
- `get_by_category(category) -> List[Dict]`: 按分类获取
- `update_knowledge(knowledge_id, content)`: 更新知识
- `delete_knowledge(knowledge_id)`: 删除知识

---

### LongTermMemory

长期记忆管理器（集成MemU框架）。

```python
from src.core.long_term_memory import LongTermMemoryManager
from src.core.database_manager import DatabaseManager

# 创建实例（可选：提供数据库管理器和API配置）
db_manager = DatabaseManager()  # 可选，不提供则自动创建
ltm = LongTermMemoryManager(
    db_manager=db_manager,
    api_key=None,  # 可选，不提供则从环境变量读取
    api_url=None,  # 可选
    model_name=None  # 可选
)

# 添加消息到短期记忆
ltm.add_message('user', '今天天气真好')
ltm.add_message('assistant', '是的，很适合出去走走')

# 获取记忆统计
stats = ltm.get_statistics()
print(f"短期记忆: {stats['short_term']['rounds']} 轮")
print(f"长期记忆: {stats['long_term']['total_summaries']} 个概括")

# 获取对话历史
recent_messages = ltm.get_recent_messages(count=10)

# 获取长期记忆概括
summaries = ltm.get_all_summaries()
```

**主要特性**:
- 🔄 **自动归档**: 超过20轮对话自动归档为长期记忆
- 🧠 **智能总结**: 使用MemU或传统LLM生成对话概括
- 📚 **知识提取**: 每5轮对话自动提取知识点
- 💾 **数据库存储**: 所有记忆使用SQLite持久化

**主要方法**:
- `add_message(role, content)`: 添加消息到短期记忆
- `get_recent_messages(count) -> List[Dict]`: 获取最近消息
- `get_all_summaries() -> List[Dict]`: 获取所有长期记忆概括
- `get_statistics() -> Dict`: 获取记忆统计信息
- `clear_all_memory()`: 清空所有记忆
- `get_context_for_chat() -> str`: 获取聊天上下文

**MemU集成**:
- 当配置了`USE_MEMU=true`和`OPENAI_API_KEY`时，使用MemU进行记忆总结
- MemU提供更高效的记忆管理，减少长期运行的token成本
- 未配置时自动回退到传统LLM总结方式
- 详见: https://github.com/NevaMind-AI/memU

---

### ScheduleManager

日程管理器。

```python
from src.core.schedule_manager import ScheduleManager

# 创建实例
scheduler = ScheduleManager()

# 创建日程
scheduler.create_schedule(
    title="会议",
    start_time="2026-02-01 10:00:00",
    end_time="2026-02-01 11:00:00",
    description="项目讨论会议"
)

# 获取日程列表
schedules = scheduler.get_schedules(
    start_date="2026-02-01",
    end_date="2026-02-07"
)

# 更新日程
scheduler.update_schedule(
    schedule_id=1,
    title="项目会议",
    start_time="2026-02-01 10:30:00"
)

# 删除日程
scheduler.delete_schedule(schedule_id=1)
```

**主要方法**:
- `create_schedule(title, start_time, end_time, description)`: 创建日程
- `get_schedules(start_date, end_date) -> List[Dict]`: 获取日程
- `update_schedule(schedule_id, **kwargs)`: 更新日程
- `delete_schedule(schedule_id)`: 删除日程
- `check_conflicts(start_time, end_time) -> bool`: 检查冲突

---

## 工具API / Tool APIs

### DebugLogger

调试日志工具。

```python
from src.tools.debug_logger import get_debug_logger

# 获取日志器
logger = get_debug_logger()

# 记录日志
logger.info("信息日志")
logger.warning("警告日志")
logger.error("错误日志")
logger.debug("调试日志")

# API调用日志
logger.log_api_call(
    url="https://api.example.com",
    method="POST",
    response_time=0.5
)
```

---

### AgentVision

智能体视觉工具。

```python
from src.tools.agent_vision import AgentVision

# 创建实例
vision = AgentVision()

# 分析环境
env_description = vision.describe_environment()

# 检测是否需要视觉信息
needs_vision = vision.check_vision_needed(user_query)
```

---

### ToolTip

GUI提示工具。

```python
from src.tools.tooltip_utils import ToolTip

# 创建提示
tooltip = ToolTip(widget, text="这是提示信息")

# 创建树形视图提示
create_treeview_tooltip(treeview, column_texts={
    "col1": "第一列说明",
    "col2": "第二列说明"
})
```

---

## GUI API

### EnhancedChatDebugGUI

主图形界面。

```python
import tkinter as tk
from src.gui.gui_enhanced import EnhancedChatDebugGUI

# 创建主窗口
root = tk.Tk()

# 创建GUI实例
app = EnhancedChatDebugGUI(root)

# 启动主循环
root.mainloop()
```

---

### DatabaseGUI

数据库管理界面。

```python
from src.gui.database_gui import DatabaseGUI

# 在主GUI中集成
db_gui = DatabaseGUI(parent_frame)
```

---

## 数据结构 / Data Structures

### 对话记录 / Conversation Record

```python
{
    "id": 1,
    "user_message": "你好",
    "agent_message": "你好！有什么可以帮助你的吗？",
    "timestamp": "2026-01-31 10:00:00"
}
```

### 知识条目 / Knowledge Entry

```python
{
    "id": 1,
    "content": "Python是一种高级编程语言",
    "category": "编程",
    "source": "对话",
    "timestamp": "2026-01-31 10:00:00"
}
```

### 事件 / Event

```python
{
    "id": 1,
    "type": "notification",  # or "task"
    "title": "提醒",
    "content": "这是一个通知",
    "trigger_time": "2026-02-01 10:00:00",
    "status": "pending",  # pending, triggered, cancelled
    "created_at": "2026-01-31 10:00:00"
}
```

### 日程 / Schedule

```python
{
    "id": 1,
    "title": "会议",
    "start_time": "2026-02-01 10:00:00",
    "end_time": "2026-02-01 11:00:00",
    "description": "项目讨论会议",
    "created_at": "2026-01-31 10:00:00"
}
```

### 情感数据 / Emotion Data

```python
{
    "impression": "友好、专业、乐于助人",
    "score": 75,
    "relationship": "良好关系",
    "updated_at": "2026-01-31 10:00:00"
}
```

---

## 错误处理 / Error Handling

所有API方法在发生错误时会抛出相应的异常：

```python
try:
    agent.chat("Hello")
except ConnectionError:
    # 处理网络连接错误
    pass
except ValueError:
    # 处理参数错误
    pass
except Exception as e:
    # 处理其他错误
    logger.error(f"错误: {e}")
```

---

## 最佳实践 / Best Practices

1. **始终使用try-except处理可能的异常**
2. **定期备份数据库**
3. **不要在代码中硬编码API密钥**
4. **使用日志记录重要操作**
5. **遵循单一职责原则**
6. **编写单元测试**

---

## 示例 / Examples

完整示例请查看 `examples/` 目录。

更多技术细节请参考 [TECHNICAL.md](TECHNICAL.md)。
