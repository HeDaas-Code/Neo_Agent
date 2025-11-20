# API 文档

[English](../en/API.md) | 简体中文

本文档详细描述 Neo Agent 各个模块的 API 接口和使用方法。

## 📚 目录

- [DatabaseManager](#databasemanager) - 数据库管理
- [ChatAgent](#chatagent) - 对话代理
- [LongTermMemoryManager](#longtermmemorymanager) - 长效记忆管理
- [KnowledgeBase](#knowledgebase) - 知识库管理
- [EmotionRelationshipAnalyzer](#emotionrelationshipanalyzer) - 情感分析
- [AgentVisionTool](#agentvisiontool) - 视觉工具
- [EventManager](#eventmanager) - 事件管理
- [MultiAgentCoordinator](#multiagentcoordinator) - 多智能体协调器
- [InterruptQuestionTool](#interruptquestiontool) - 中断性提问工具
- [DebugLogger](#debuglogger) - 调试日志

---

## DatabaseManager

数据库管理器，负责所有数据的持久化存储。

### 初始化

```python
from database_manager import DatabaseManager

db = DatabaseManager(
    db_path="chat_agent.db",  # 数据库文件路径
    debug=False                # 是否启用调试模式
)
```

### 短期记忆 API

#### add_short_term_message

添加消息到短期记忆。

```python
db.add_short_term_message(
    role: str,      # 'user' 或 'assistant'
    content: str    # 消息内容
) -> None
```

**示例**：
```python
db.add_short_term_message('user', '你好')
db.add_short_term_message('assistant', '你好！很高兴见到你')
```

#### get_short_term_messages

获取短期记忆消息列表。

```python
db.get_short_term_messages(
    limit: Optional[int] = None  # 返回消息数量限制
) -> List[Dict[str, Any]]
```

**返回格式**：
```python
[
    {
        'id': 1,
        'role': 'user',
        'content': '你好',
        'timestamp': '2024-01-01T12:00:00'
    },
    ...
]
```

#### clear_short_term_memory

清空所有短期记忆。

```python
db.clear_short_term_memory() -> None
```

### 长期记忆 API

#### add_long_term_summary

添加长期记忆概括。

```python
db.add_long_term_summary(
    summary: str,               # 概括内容
    conversation_count: int,    # 对话轮数
    start_time: str,           # 开始时间
    end_time: str              # 结束时间
) -> None
```

**示例**：
```python
db.add_long_term_summary(
    summary="用户询问了关于Python编程的问题，我们讨论了函数和类的区别",
    conversation_count=10,
    start_time="2024-01-01T10:00:00",
    end_time="2024-01-01T11:00:00"
)
```

#### get_long_term_summaries

获取长期记忆概括列表。

```python
db.get_long_term_summaries(
    limit: Optional[int] = None
) -> List[Dict[str, Any]]
```

### 知识库 API

#### add_entity

添加实体到知识库。

```python
db.add_entity(
    name: str  # 实体名称
) -> str      # 返回实体 UUID
```

#### add_entity_definition

为实体添加定义。

```python
db.add_entity_definition(
    entity_uuid: str,       # 实体 UUID
    content: str,          # 定义内容
    type: str = '定义',    # 定义类型
    source: str = None,    # 来源
    confidence: float = 1.0,  # 置信度 (0-1)
    priority: int = 50     # 优先级
) -> None
```

#### search_entities

搜索实体。

```python
db.search_entities(
    query_text: str,           # 搜索关键词
    limit: int = 10,          # 返回结果数量
    min_confidence: float = 0.0  # 最小置信度
) -> List[Dict[str, Any]]
```

**返回格式**：
```python
[
    {
        'uuid': 'xxx-xxx-xxx',
        'name': 'Python',
        'normalized_name': 'python',
        'definitions': [
            {
                'content': 'Python是一种高级编程语言',
                'type': '定义',
                'confidence': 1.0
            }
        ],
        'related_info': [...]
    }
]
```

### 基础知识 API

#### add_base_knowledge

添加基础知识。

```python
db.add_base_knowledge(
    entity_name: str,           # 实体名称
    content: str,              # 知识内容
    category: str = '通用',    # 分类
    description: str = None,   # 描述
    priority: int = 100,       # 优先级（越高越优先）
    confidence: float = 1.0    # 置信度
) -> None
```

#### get_base_knowledge

获取基础知识。

```python
db.get_base_knowledge(
    entity_name: str = None  # 实体名称，None返回全部
) -> List[Dict[str, Any]]
```

---

## ChatAgent

对话代理核心类，处理与 LLM 的交互。

### 初始化

```python
from chat_agent import ChatAgent

agent = ChatAgent(
    api_key: str = None,           # API密钥，默认从环境变量读取
    api_url: str = None,           # API地址
    model_name: str = None,        # 模型名称
    temperature: float = 0.8,      # 生成温度
    max_tokens: int = 2000,        # 最大token数
    db_manager: DatabaseManager = None  # 数据库管理器实例
)
```

### chat

发送消息并获取回复。

```python
response = agent.chat(
    user_input: str,              # 用户输入
    use_memory: bool = True,      # 是否使用记忆
    stream: bool = False          # 是否流式输出
) -> str  # 返回助手回复
```

**示例**：
```python
response = agent.chat("你好，请介绍一下你自己")
print(response)
```

### get_character_prompt

获取角色系统提示词。

```python
prompt = agent.get_character_prompt() -> str
```

### clear_memory

清空对话记忆。

```python
agent.clear_memory() -> None
```

---

## LongTermMemoryManager

长效记忆管理器，管理短期和长期记忆的转换。

### 初始化

```python
from long_term_memory import LongTermMemoryManager

memory_manager = LongTermMemoryManager(
    db_manager: DatabaseManager = None,  # 数据库管理器
    api_key: str = None,
    api_url: str = None,
    model_name: str = None
)
```

### add_message

添加消息（自动处理记忆转换）。

```python
memory_manager.add_message(
    role: str,      # 'user' 或 'assistant'
    content: str    # 消息内容
) -> None
```

### get_relevant_memory

获取相关记忆用于对话。

```python
memory = memory_manager.get_relevant_memory(
    query: str = None,  # 查询关键词（可选）
    limit: int = 10     # 返回数量限制
) -> Dict[str, Any]
```

**返回格式**：
```python
{
    'short_term': [  # 短期记忆
        {'role': 'user', 'content': '...'},
        {'role': 'assistant', 'content': '...'}
    ],
    'long_term': [   # 长期概括
        {'summary': '...', 'conversation_count': 10}
    ],
    'knowledge': [   # 相关知识
        {'entity': 'Python', 'definition': '...'}
    ]
}
```

---

## KnowledgeBase

知识库管理类，从对话中提取和管理知识。

### 初始化

```python
from knowledge_base import KnowledgeBase

kb = KnowledgeBase(
    db_manager: DatabaseManager,
    api_key: str = None,
    api_url: str = None,
    model_name: str = None
)
```

### extract_knowledge_from_conversation

从对话中提取知识。

```python
result = kb.extract_knowledge_from_conversation(
    messages: List[Dict[str, str]],  # 对话消息列表
    force: bool = False               # 是否强制提取
) -> Dict[str, Any]
```

**消息格式**：
```python
messages = [
    {'role': 'user', 'content': '什么是Python？'},
    {'role': 'assistant', 'content': 'Python是一种编程语言...'}
]
```

**返回格式**：
```python
{
    'success': True,
    'entities_extracted': 3,
    'entities': [
        {
            'name': 'Python',
            'type': '编程语言',
            'definition': '...'
        }
    ]
}
```

### search_knowledge

搜索知识。

```python
results = kb.search_knowledge(
    query: str,      # 搜索关键词
    limit: int = 5   # 返回结果数量
) -> List[Dict[str, Any]]
```

---

## EmotionRelationshipAnalyzer

情感关系分析器，分析对话中的情感倾向。

### 初始化

```python
from emotion_analyzer import EmotionRelationshipAnalyzer

analyzer = EmotionRelationshipAnalyzer(
    api_key: str = None,
    api_url: str = None,
    model_name: str = None
)
```

### analyze_emotion

分析情感关系。

```python
result = analyzer.analyze_emotion(
    messages: List[Dict[str, str]],  # 对话消息
    recent_rounds: int = 10           # 分析最近N轮对话
) -> Dict[str, Any]
```

**返回格式**：
```python
{
    'intimacy': 75,      # 亲密度 (0-100)
    'trust': 80,         # 信任度 (0-100)
    'joy': 85,          # 愉悦度 (0-100)
    'empathy': 70,      # 共鸣度 (0-100)
    'dependence': 60,   # 依赖度 (0-100)
    'overall': 74,      # 总体评分
    'analysis': '...'   # 分析说明
}
```

### format_emotion_summary

格式化情感分析结果。

```python
summary = format_emotion_summary(
    emotion_data: Dict[str, Any]  # 情感数据
) -> str
```

---

## AgentVisionTool

智能体视觉工具，模拟视觉感知能力。

### 初始化

```python
from agent_vision import AgentVisionTool

vision = AgentVisionTool(
    db_manager: DatabaseManager
)
```

### set_environment

设置环境描述。

```python
vision.set_environment(
    description: str,   # 环境描述
    category: str = '通用'  # 环境分类
) -> None
```

**示例**：
```python
vision.set_environment(
    description="房间里有一张桌子，桌上放着一本书",
    category="室内"
)
```

### get_current_environment

获取当前环境描述。

```python
env = vision.get_current_environment() -> Dict[str, Any]
```

**返回格式**：
```python
{
    'description': '房间里有一张桌子...',
    'category': '室内',
    'timestamp': '2024-01-01T12:00:00'
}
```

### clear_environment

清空环境描述。

```python
vision.clear_environment() -> None
```

---

## EventManager

事件管理器，负责事件的创建、存储、检索和管理。

### 初始化

```python
from event_manager import EventManager, EventType, EventPriority, EventStatus

manager = EventManager(
    db_manager: DatabaseManager  # 数据库管理器实例
)
```

### create_event

创建新事件。

```python
event = manager.create_event(
    title: str,              # 事件标题
    description: str,        # 事件描述
    event_type: EventType,   # 事件类型（NOTIFICATION或TASK）
    priority: EventPriority, # 优先级（LOW/MEDIUM/HIGH/URGENT）
    task_requirements: str = None,      # 任务要求（任务型事件必填）
    completion_criteria: str = None     # 完成标准（任务型事件必填）
) -> Event
```

**示例**：

```python
# 创建通知型事件
notification = manager.create_event(
    title="系统更新通知",
    description="新版本已发布，包含性能优化和bug修复",
    event_type=EventType.NOTIFICATION,
    priority=EventPriority.MEDIUM
)

# 创建任务型事件
task = manager.create_event(
    title="生成周报",
    description="根据本周的对话记录生成周报摘要",
    event_type=EventType.TASK,
    priority=EventPriority.HIGH,
    task_requirements="需要总结本周的主要对话主题和知识点",
    completion_criteria="周报需包含：主题列表、知识点总结、对话统计"
)
```

### get_event

获取指定事件。

```python
event = manager.get_event(
    event_id: str  # 事件ID
) -> Optional[Event]
```

### get_pending_events

获取待处理事件列表。

```python
events = manager.get_pending_events(
    limit: int = 10  # 返回数量限制
) -> List[Event]
```

### update_event_status

更新事件状态。

```python
manager.update_event_status(
    event_id: str,              # 事件ID
    status: EventStatus,        # 新状态
    completion_message: str = None  # 完成消息（可选）
) -> None
```

**状态类型**：
- `EventStatus.PENDING` - 待处理
- `EventStatus.PROCESSING` - 处理中
- `EventStatus.COMPLETED` - 已完成
- `EventStatus.FAILED` - 失败
- `EventStatus.CANCELLED` - 已取消

### add_event_log

添加事件日志。

```python
manager.add_event_log(
    event_id: str,      # 事件ID
    log_type: str,      # 日志类型
    log_content: str    # 日志内容
) -> None
```

### get_event_logs

获取事件日志。

```python
logs = manager.get_event_logs(
    event_id: str  # 事件ID
) -> List[Dict[str, Any]]
```

### delete_event

删除事件。

```python
manager.delete_event(
    event_id: str  # 事件ID
) -> None
```

### get_statistics

获取事件统计信息。

```python
stats = manager.get_statistics() -> Dict[str, int]
```

**返回格式**：
```python
{
    'total': 100,       # 总事件数
    'pending': 10,      # 待处理
    'processing': 2,    # 处理中
    'completed': 85,    # 已完成
    'failed': 3         # 失败
}
```

---

## MultiAgentCoordinator

多智能体协调器，负责任务型事件的多智能体协作处理。

### 初始化

```python
from multi_agent_coordinator import MultiAgentCoordinator

coordinator = MultiAgentCoordinator(
    api_key: str = None,
    api_url: str = None,
    model_name: str = None,
    question_tool: InterruptQuestionTool = None,
    progress_callback: Callable = None  # 进度回调函数
)
```

### process_task_event

处理任务型事件。

```python
result = coordinator.process_task_event(
    task_event: TaskEvent,              # 任务事件
    character_context: str = None,      # 角色上下文
    memory_context: str = None          # 记忆上下文
) -> Dict[str, Any]
```

**返回格式**：
```python
{
    'success': True,
    'understanding': '任务理解内容',
    'plan': {
        'steps': ['步骤1', '步骤2', '步骤3']
    },
    'execution_results': [
        {'step': 1, 'result': '步骤1结果'},
        {'step': 2, 'result': '步骤2结果'},
        {'step': 3, 'result': '步骤3结果'}
    ],
    'verification': {
        'passed': True,
        'message': '任务验证通过'
    }
}
```

### set_progress_callback

设置进度回调函数。

```python
coordinator.set_progress_callback(
    callback: Callable[[str], None]  # 回调函数
) -> None
```

**示例**：
```python
def on_progress(message):
    print(f"进度更新: {message}")

coordinator.set_progress_callback(on_progress)
```

---

## InterruptQuestionTool

中断性提问工具，允许智能体在任务执行中向用户提问。

### 初始化

```python
from interrupt_question_tool import InterruptQuestionTool

tool = InterruptQuestionTool()
```

### set_question_callback

设置提问回调函数。

```python
tool.set_question_callback(
    callback: Callable[[str], str]  # 回调函数，接收问题返回答案
) -> None
```

**示例**：
```python
def ask_user(question):
    return input(f"{question}\n> ")

tool.set_question_callback(ask_user)
```

### ask_user

向用户提问。

```python
answer = tool.ask_user(
    question: str,      # 问题内容
    context: str = None # 问题上下文（可选）
) -> str
```

**示例**：
```python
answer = tool.ask_user(
    question="请问您希望周报包含哪些具体内容？",
    context="正在生成周报，需要确认报告范围"
)
```

---

## DebugLogger

调试日志记录器，记录系统运行详情。

### 获取实例

```python
from debug_logger import get_debug_logger

logger = get_debug_logger()
```

### log_info

记录信息日志。

```python
logger.log_info(
    module: str,       # 模块名称
    action: str,       # 操作描述
    data: Dict = None  # 额外数据
) -> None
```

**示例**：
```python
logger.log_info(
    'ChatAgent',
    '发送用户消息',
    {'message_length': 50}
)
```

### log_prompt

记录提示词。

```python
logger.log_prompt(
    prompt: str,       # 提示词内容
    context: Dict = None  # 上下文信息
) -> None
```

### log_api_call

记录 API 调用。

```python
logger.log_api_call(
    endpoint: str,     # API端点
    request: Dict,     # 请求数据
    response: Dict,    # 响应数据
    duration: float    # 耗时（秒）
) -> None
```

### get_logs

获取日志记录。

```python
logs = logger.get_logs(
    limit: int = 100,           # 返回数量
    level: str = None,          # 日志级别过滤
    module: str = None          # 模块过滤
) -> List[Dict[str, Any]]
```

---

## 🔧 工具函数

### normalize_text

文本归一化（用于实体名称标准化）。

```python
from knowledge_base import normalize_text

normalized = normalize_text(text: str) -> str
```

**示例**：
```python
normalize_text("  Python  ")  # 返回: "python"
normalize_text("Python编程")  # 返回: "python编程"
```

### format_timestamp

格式化时间戳。

```python
from datetime import datetime

timestamp = datetime.now().isoformat()
# 返回: "2024-01-01T12:00:00.000000"
```

---

## 📊 数据模型

### Message（消息）

```python
{
    'id': int,              # 消息ID
    'role': str,            # 'user' 或 'assistant'
    'content': str,         # 消息内容
    'timestamp': str        # ISO格式时间戳
}
```

### Entity（实体）

```python
{
    'uuid': str,            # 唯一标识
    'name': str,            # 实体名称
    'normalized_name': str, # 归一化名称
    'created_at': str,      # 创建时间
    'updated_at': str       # 更新时间
}
```

### Summary（概括）

```python
{
    'id': int,              # 概括ID
    'summary': str,         # 概括内容
    'conversation_count': int,  # 对话轮数
    'start_time': str,      # 开始时间
    'end_time': str,        # 结束时间
    'created_at': str       # 创建时间
}
```

---

## 🎯 使用示例

### 完整对话流程

```python
from chat_agent import ChatAgent
from database_manager import DatabaseManager

# 1. 初始化
db = DatabaseManager()
agent = ChatAgent(db_manager=db)

# 2. 开始对话
response = agent.chat("你好")
print(response)

# 3. 继续对话
response = agent.chat("你知道Python吗？")
print(response)

# 4. 查看记忆
messages = db.get_short_term_messages()
for msg in messages:
    print(f"{msg['role']}: {msg['content']}")
```

### 知识提取

```python
from knowledge_base import KnowledgeBase

kb = KnowledgeBase(db_manager=db)

# 从对话中提取知识
messages = db.get_short_term_messages()
result = kb.extract_knowledge_from_conversation(messages)

print(f"提取了 {result['entities_extracted']} 个实体")

# 搜索知识
results = kb.search_knowledge("Python")
for entity in results:
    print(f"{entity['name']}: {entity['definitions'][0]['content']}")
```

### 情感分析

```python
from emotion_analyzer import EmotionRelationshipAnalyzer

analyzer = EmotionRelationshipAnalyzer()

# 分析情感
messages = db.get_short_term_messages()
emotion = analyzer.analyze_emotion(messages)

print(f"亲密度: {emotion['intimacy']}")
print(f"信任度: {emotion['trust']}")
print(f"总体评分: {emotion['overall']}")
```

---

## 🚨 错误处理

所有 API 调用都应该包含错误处理：

```python
try:
    response = agent.chat("你好")
except Exception as e:
    print(f"错误: {e}")
    # 处理错误
```

常见错误：
- `ValueError`: 参数无效
- `ConnectionError`: API连接失败
- `TimeoutError`: 请求超时
- `sqlite3.Error`: 数据库错误

---

## 📝 注意事项

1. **线程安全**：DatabaseManager 使用上下文管理器，每次操作都会打开新连接
2. **内存管理**：短期记忆会自动限制数量，避免内存溢出
3. **API限流**：注意 API 调用频率限制
4. **数据备份**：定期备份 `chat_agent.db` 文件

---

## 🔗 相关文档

- [快速开始](QUICKSTART.md)
- [开发指南](DEVELOPMENT.md)
- [架构设计](ARCHITECTURE.md)

---

最后更新：2024-01-01
