# API 文档

本文档详细说明 Neo_Agent 项目中各个模块的 API 接口和使用方法。

## 目录

- [ChatAgent - 聊天代理](#chatagent---聊天代理)
- [MemoryManager - 记忆管理](#memorymanager---记忆管理)
- [LongTermMemoryManager - 长期记忆管理](#longtermemorymanager---长期记忆管理)
- [KnowledgeBase - 知识库](#knowledgebase---知识库)
- [BaseKnowledge - 基础知识库](#baseknowledge---基础知识库)
- [EmotionRelationshipAnalyzer - 情感关系分析](#emotionrelationshipanalyzer---情感关系分析)
- [DatabaseManager - 数据库管理](#databasemanager---数据库管理)
- [DebugLogger - 调试日志](#debuglogger---调试日志)

---

## ChatAgent - 聊天代理

核心对话代理类，负责管理整个对话流程。

### 初始化

```python
from chat_agent import ChatAgent

agent = ChatAgent()
```

### 主要方法

#### chat(user_input: str) -> str

发送消息并获取AI回复。

**参数:**
- `user_input` (str): 用户输入的消息

**返回:**
- `str`: AI的回复内容

**示例:**
```python
response = agent.chat("你好")
print(response)
```

#### get_memory() -> List[Dict]

获取当前短期记忆。

**返回:**
- `List[Dict]`: 消息列表，每条消息包含 role、content、timestamp

**示例:**
```python
memory = agent.get_memory()
for msg in memory:
    print(f"{msg['role']}: {msg['content']}")
```

#### get_long_term_summaries() -> List[Dict]

获取所有长期记忆概括。

**返回:**
- `List[Dict]`: 长期记忆列表，每条包含 uuid、summary、rounds 等

**示例:**
```python
summaries = agent.get_long_term_summaries()
for summary in summaries:
    print(f"主题: {summary['summary']}")
```

#### get_knowledge_items() -> List[Dict]

获取所有知识库条目。

**返回:**
- `List[Dict]`: 知识条目列表

**示例:**
```python
knowledge = agent.get_knowledge_items()
for item in knowledge:
    print(f"{item['title']}: {item['content']}")
```

#### analyze_emotion() -> Dict

手动触发情感关系分析。

**返回:**
- `Dict`: 情感分析结果，包含5维度评分、关系类型等

**示例:**
```python
emotion_data = agent.analyze_emotion()
print(f"关系类型: {emotion_data['relationship_type']}")
print(f"总体评分: {emotion_data['overall_score']}/100")
```

#### get_emotion_history() -> List[Dict]

获取情感分析历史记录。

**返回:**
- `List[Dict]`: 历史情感数据列表

**示例:**
```python
history = agent.get_emotion_history()
print(f"共有 {len(history)} 次分析记录")
```

#### clear_memory() -> None

清空短期和长期记忆。

**示例:**
```python
agent.clear_memory()
print("记忆已清空")
```

---

## MemoryManager - 记忆管理

管理短期对话记忆的类。

### 初始化

```python
from chat_agent import MemoryManager

memory_manager = MemoryManager(memory_file="memory_data.json")
```

**参数:**
- `memory_file` (str, 可选): 记忆文件路径

### 主要方法

#### add_message(role: str, content: str) -> None

添加一条消息到记忆中。

**参数:**
- `role` (str): 角色，"user" 或 "assistant"
- `content` (str): 消息内容

**示例:**
```python
memory_manager.add_message("user", "你好")
memory_manager.add_message("assistant", "你好呀！")
```

#### get_messages() -> List[Dict]

获取所有消息。

**返回:**
- `List[Dict]`: 消息列表

#### save_memory() -> None

保存记忆到文件。

**示例:**
```python
memory_manager.save_memory()
```

#### clear_memory() -> None

清空所有记忆。

---

## LongTermMemoryManager - 长期记忆管理

管理长期记忆和主题概括。

### 初始化

```python
from long_term_memory import LongTermMemoryManager

ltm_manager = LongTermMemoryManager(
    db_manager=database_manager,
    llm=llm_instance
)
```

**参数:**
- `db_manager` (DatabaseManager): 数据库管理器实例
- `llm`: LLM实例

### 主要方法

#### archive_short_term_memory(messages: List[Dict]) -> Dict

将短期记忆归档为长期记忆。

**参数:**
- `messages` (List[Dict]): 要归档的消息列表

**返回:**
- `Dict`: 归档后的长期记忆条目

**示例:**
```python
archived = ltm_manager.archive_short_term_memory(recent_messages)
print(f"归档ID: {archived['uuid']}")
```

#### get_summaries() -> List[Dict]

获取所有长期记忆概括。

**返回:**
- `List[Dict]`: 概括列表

---

## KnowledgeBase - 知识库

管理从对话中提取的结构化知识。

### 初始化

```python
from knowledge_base import KnowledgeBase

kb = KnowledgeBase(
    db_manager=database_manager,
    llm=llm_instance
)
```

### 主要方法

#### extract_knowledge(messages: List[Dict]) -> List[Dict]

从对话中提取知识。

**参数:**
- `messages` (List[Dict]): 对话消息列表

**返回:**
- `List[Dict]`: 提取的知识条目列表

**示例:**
```python
knowledge_items = kb.extract_knowledge(recent_messages)
for item in knowledge_items:
    print(f"提取知识: {item['title']}")
```

#### search_knowledge(query: str, knowledge_type: str = None) -> List[Dict]

搜索知识库。

**参数:**
- `query` (str): 搜索关键词
- `knowledge_type` (str, 可选): 知识类型筛选

**返回:**
- `List[Dict]`: 匹配的知识条目

**示例:**
```python
results = kb.search_knowledge("历史", knowledge_type="偏好")
```

#### get_all_knowledge() -> List[Dict]

获取所有知识条目。

**返回:**
- `List[Dict]`: 所有知识条目

---

## BaseKnowledge - 基础知识库

管理优先级最高的核心知识。

### 初始化

```python
from base_knowledge import BaseKnowledge

base_kb = BaseKnowledge()
```

### 主要方法

#### add_base_fact(entity_name: str, fact_content: str, category: str = "定义", description: str = "") -> Dict

添加基础知识。

**参数:**
- `entity_name` (str): 实体名称
- `fact_content` (str): 事实内容
- `category` (str): 分类（默认"定义"）
- `description` (str): 详细描述

**返回:**
- `Dict`: 添加的知识条目

**示例:**
```python
base_kb.add_base_fact(
    entity_name="HeDaas",
    fact_content="HeDaas是一个高校",
    category="机构定义",
    description="这是基础知识，优先级最高"
)
```

#### get_base_fact(entity_name: str) -> Dict

获取指定实体的基础知识（不区分大小写）。

**参数:**
- `entity_name` (str): 实体名称

**返回:**
- `Dict`: 基础知识条目，如果不存在返回 None

**示例:**
```python
fact = base_kb.get_base_fact("hedaas")  # 不区分大小写
if fact:
    print(fact['fact_content'])
```

#### get_all_base_facts() -> List[Dict]

获取所有基础知识。

**返回:**
- `List[Dict]`: 所有基础知识条目

---

## EmotionRelationshipAnalyzer - 情感关系分析

分析用户与AI之间的情感关系。

### 初始化

```python
from emotion_analyzer import EmotionRelationshipAnalyzer

emotion_analyzer = EmotionRelationshipAnalyzer(
    db_manager=database_manager,
    llm=llm_instance
)
```

### 主要方法

#### analyze_emotion_relationship(messages: List[Dict]) -> Dict

分析情感关系。

**参数:**
- `messages` (List[Dict]): 要分析的对话消息列表（通常最近10轮）

**返回:**
- `Dict`: 情感分析结果，包含：
  - 5个维度的评分（亲密度、信任度、愉悦度、共鸣度、依赖度）
  - 总体评分 (overall_score)
  - 关系类型 (relationship_type)
  - 情感基调 (emotional_tone)
  - 主要话题 (key_topics)
  - 详细分析 (analysis)

**示例:**
```python
recent_messages = agent.get_memory()[-20:]  # 最近10轮
emotion_data = emotion_analyzer.analyze_emotion_relationship(recent_messages)

print(f"亲密度: {emotion_data['亲密度']}/100")
print(f"信任度: {emotion_data['信任度']}/100")
print(f"关系类型: {emotion_data['relationship_type']}")
print(f"情感基调: {emotion_data['emotional_tone']}")
```

#### generate_tone_prompt(emotion_data: Dict) -> str

根据情感数据生成语气提示。

**参数:**
- `emotion_data` (Dict): 情感分析结果

**返回:**
- `str`: 语气提示文本

**示例:**
```python
tone_prompt = emotion_analyzer.generate_tone_prompt(emotion_data)
# 将此提示添加到系统消息中
```

#### get_emotion_history() -> List[Dict]

获取历史情感分析记录。

**返回:**
- `List[Dict]`: 历史记录列表

---

## DatabaseManager - 数据库管理

统一管理所有数据存储。

### 初始化

```python
from database_manager import DatabaseManager

db_manager = DatabaseManager(db_file="chat_agent.db")
```

**参数:**
- `db_file` (str): 数据库文件路径

### 主要方法

#### save_data(key: str, data: Any) -> None

保存数据。

**参数:**
- `key` (str): 数据键名
- `data` (Any): 要保存的数据（会自动JSON序列化）

**示例:**
```python
db_manager.save_data("memory_data", {
    "messages": [...],
    "metadata": {...}
})
```

#### load_data(key: str, default: Any = None) -> Any

加载数据。

**参数:**
- `key` (str): 数据键名
- `default` (Any): 如果键不存在返回的默认值

**返回:**
- `Any`: 加载的数据

**示例:**
```python
memory = db_manager.load_data("memory_data", {"messages": []})
```

#### delete_data(key: str) -> None

删除数据。

**参数:**
- `key` (str): 要删除的数据键名

#### get_all_keys() -> List[str]

获取所有数据键。

**返回:**
- `List[str]`: 所有键名列表

---

## DebugLogger - 调试日志

记录和管理调试日志。

### 获取实例

```python
from debug_logger import get_debug_logger

logger = get_debug_logger()
```

### 主要方法

#### log(log_type: str, module_name: str, message: str, details: Dict = None) -> None

记录日志。

**参数:**
- `log_type` (str): 日志类型（module/prompt/request/response/error/info）
- `module_name` (str): 模块名称
- `message` (str): 日志消息
- `details` (Dict, 可选): 详细信息字典

**示例:**
```python
logger.log("info", "ChatAgent", "开始处理用户消息", {
    "user_input": "你好",
    "timestamp": "2025-01-15 10:00:00"
})

logger.log("error", "APIClient", "API调用失败", {
    "status_code": 500,
    "error_message": "服务器错误"
})
```

#### get_logs(log_type: str = None, limit: int = 500) -> List[Dict]

获取日志。

**参数:**
- `log_type` (str, 可选): 筛选日志类型
- `limit` (int): 返回的最大日志数量

**返回:**
- `List[Dict]`: 日志条目列表

**示例:**
```python
# 获取所有错误日志
errors = logger.get_logs(log_type="error")

# 获取最近100条日志
recent_logs = logger.get_logs(limit=100)
```

#### clear_logs() -> None

清空内存中的日志。

---

## 完整使用示例

### 示例1: 基础对话流程

```python
from chat_agent import ChatAgent

# 初始化代理
agent = ChatAgent()

# 进行对话
response1 = agent.chat("你好，我是张三")
print(f"AI: {response1}")

response2 = agent.chat("我喜欢历史")
print(f"AI: {response2}")

# 查看记忆
memory = agent.get_memory()
print(f"当前记忆: {len(memory)} 条消息")
```

### 示例2: 知识管理

```python
from chat_agent import ChatAgent

agent = ChatAgent()

# 进行多轮对话
for i in range(6):
    agent.chat(f"测试消息 {i}")

# 获取提取的知识
knowledge = agent.get_knowledge_items()
for item in knowledge:
    print(f"{item['type']}: {item['title']} - {item['content']}")
```

### 示例3: 情感分析

```python
from chat_agent import ChatAgent

agent = ChatAgent()

# 进行10轮对话
for i in range(10):
    response = agent.chat(f"测试消息 {i}")

# 系统会自动触发情感分析
# 也可以手动触发
emotion_data = agent.analyze_emotion()

print(f"关系类型: {emotion_data['relationship_type']}")
print(f"亲密度: {emotion_data['亲密度']}")
print(f"信任度: {emotion_data['信任度']}")
print(f"愉悦度: {emotion_data['愉悦度']}")
print(f"共鸣度: {emotion_data['共鸣度']}")
print(f"依赖度: {emotion_data['依赖度']}")
```

### 示例4: 基础知识库

```python
from base_knowledge import BaseKnowledge
from chat_agent import ChatAgent

# 添加基础知识
base_kb = BaseKnowledge()
base_kb.add_base_fact(
    entity_name="公司名",
    fact_content="这是一家科技公司",
    category="机构定义"
)

# 使用代理进行对话
agent = ChatAgent()
response = agent.chat("你知道公司名吗？")
# AI会使用基础知识回答
print(response)
```

### 示例5: Debug日志

```python
from debug_logger import get_debug_logger

logger = get_debug_logger()

# 记录自定义日志
logger.log("info", "MyModule", "开始处理", {
    "param1": "value1",
    "param2": "value2"
})

# 获取并查看日志
logs = logger.get_logs(log_type="info")
for log in logs:
    print(f"[{log['timestamp']}] {log['message']}")
```

---

## 数据结构说明

### 消息对象 (Message)

```python
{
    "role": "user",  # 或 "assistant"
    "content": "消息内容",
    "timestamp": "2025-01-15T10:00:00.000000"
}
```

### 知识条目 (Knowledge Item)

```python
{
    "uuid": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "title": "知识标题",
    "content": "知识内容",
    "type": "偏好",  # 个人信息/偏好/事实/经历/观点/其他
    "source": "对话记录",
    "created_at": "2025-01-15T10:00:00.000000",
    "updated_at": "2025-01-15T10:00:00.000000",
    "source_time_range": {
        "start": "2025-01-15T09:50:00.000000",
        "end": "2025-01-15T10:00:00.000000"
    },
    "tags": ["标签1", "标签2"],
    "confidence": 0.85
}
```

### 情感数据 (Emotion Data)

```python
{
    "timestamp": "2025-01-15T10:00:00.000000",
    "message_count": 20,
    "亲密度": 65,
    "信任度": 70,
    "愉悦度": 80,
    "共鸣度": 75,
    "依赖度": 55,
    "overall_score": 69,
    "relationship_type": "朋友",
    "emotional_tone": "积极",
    "key_topics": ["历史", "学习", "生活"],
    "analysis": "详细的分析文字..."
}
```

---

## 错误处理

所有API调用都应该包含适当的错误处理：

```python
try:
    response = agent.chat("你好")
except Exception as e:
    print(f"错误: {e}")
    # 处理错误
```

常见错误类型：
- `FileNotFoundError`: 配置文件或数据文件不存在
- `KeyError`: 访问不存在的数据键
- `ValueError`: 参数值无效
- `ConnectionError`: API连接失败

---

## 环境配置

API的行为受 `.env` 文件中的配置影响，主要配置项：

```env
# API配置
SILICONFLOW_API_KEY=your-api-key
MODEL_NAME=deepseek-ai/DeepSeek-V3
TEMPERATURE=0.8
MAX_TOKENS=2000

# 记忆配置
MAX_SHORT_TERM_ROUNDS=20  # 短期记忆轮数
MAX_MEMORY_MESSAGES=50    # 最大消息数

# Debug模式
DEBUG_MODE=True           # 启用调试日志
```

---

如有疑问或需要更多示例，请参考项目源代码或在 [Issues](https://github.com/HeDaas-Code/Neo_Agent/issues) 中提问。
