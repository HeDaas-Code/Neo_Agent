# API Reference

[中文](API.md) | **English**

Complete API reference documentation for Neo_Agent.

## Table of Contents

- [ChatAgent](#chatagent) - Core dialogue agent
- [MemoryManager](#memorymanager) - Memory management
- [KnowledgeBase](#knowledgebase) - Knowledge base
- [BaseKnowledge](#baseknowledge) - Base knowledge
- [EmotionAnalyzer](#emotionanalyzer) - Emotion analysis
- [DatabaseManager](#databasemanager) - Database management
- [DebugLogger](#debuglogger) - Debug logging

---

## ChatAgent

Core dialogue agent class for managing conversations, memory, knowledge, and emotional analysis.

### Initialization

```python
from chat_agent import ChatAgent

agent = ChatAgent(
    api_key=None,           # API key (reads from .env if None)
    model_name=None,        # Model name (reads from .env if None)
    temperature=0.8,        # Creativity level (0-2)
    max_tokens=2000        # Maximum response length
)
```

### Main Methods

#### chat(user_input: str) -> str

Process user input and generate response.

```python
response = agent.chat("Hello, how are you?")
print(response)
```

**Parameters**:
- `user_input` (str): User's message

**Returns**:
- str: AI's response

**Raises**:
- `ValueError`: If input is empty
- `APIError`: If API call fails

#### get_memory() -> List[Dict]

Get short-term memory (recent conversations).

```python
memory = agent.get_memory()
for msg in memory:
    print(f"{msg['role']}: {msg['content']}")
```

**Returns**:
- List[Dict]: List of message dictionaries with role, content, timestamp

#### get_long_memory() -> List[Dict]

Get long-term memory (archived summaries).

```python
long_memory = agent.get_long_memory()
for summary in long_memory:
    print(f"Topic: {summary['summary']}")
    print(f"Time: {summary['created_at']} - {summary['ended_at']}")
```

**Returns**:
- List[Dict]: List of summary dictionaries with UUID, summary, time range

#### analyze_emotion() -> Dict

Manually trigger emotional relationship analysis.

```python
emotion_data = agent.analyze_emotion()
print(f"Relationship: {emotion_data['relationship_type']}")
print(f"Score: {emotion_data['overall_score']}/100")
```

**Returns**:
- Dict: Emotional analysis results including:
  - `intimacy`: Intimacy score (0-100)
  - `trust`: Trust score (0-100)
  - `pleasure`: Pleasure score (0-100)
  - `resonance`: Resonance score (0-100)
  - `dependence`: Dependence score (0-100)
  - `overall_score`: Overall score (0-100)
  - `relationship_type`: Relationship type (string)
  - `emotional_tone`: Emotional tone (positive/neutral/negative)

#### get_emotion_data() -> Dict | None

Get latest emotional analysis data.

```python
emotion = agent.get_emotion_data()
if emotion:
    print(f"Latest analysis: {emotion['timestamp']}")
```

**Returns**:
- Dict or None: Latest emotional data or None if no analysis yet

#### reload_agent()

Reload agent configuration from .env file.

```python
agent.reload_agent()
print("Configuration reloaded")
```

---

## KnowledgeBase

Knowledge base management for structured information storage.

### Initialization

```python
from knowledge_base import KnowledgeBase

kb = KnowledgeBase()
```

### Main Methods

#### get_all_knowledge() -> List[Dict]

Get all knowledge items.

```python
knowledge = kb.get_all_knowledge()
for item in knowledge:
    print(f"[{item['type']}] {item['title']}: {item['content']}")
```

**Returns**:
- List[Dict]: All knowledge items

#### search(keyword: str, type_filter: str = None) -> List[Dict]

Search knowledge by keyword and/or type.

```python
# Search by keyword
results = kb.search("history")

# Search by type
results = kb.search("", type_filter="偏好")

# Combined search
results = kb.search("programming", type_filter="个人信息")
```

**Parameters**:
- `keyword` (str): Search keyword
- `type_filter` (str, optional): Filter by knowledge type

**Returns**:
- List[Dict]: Matching knowledge items

#### add_knowledge(title: str, content: str, type: str, tags: List[str] = None) -> str

Manually add knowledge item.

```python
uuid = kb.add_knowledge(
    title="Likes Programming",
    content="User enjoys Python programming",
    type="偏好",
    tags=["programming", "Python"]
)
print(f"Added knowledge with UUID: {uuid}")
```

**Parameters**:
- `title` (str): Knowledge title
- `content` (str): Knowledge content
- `type` (str): Knowledge type (个人信息/偏好/事实/经历/观点/其他)
- `tags` (List[str], optional): Tags list

**Returns**:
- str: UUID of created knowledge item

---

## BaseKnowledge

Highest priority knowledge management (100% priority, immutable).

### Initialization

```python
from base_knowledge import BaseKnowledge

base_kb = BaseKnowledge()
```

### Main Methods

#### add_base_fact(entity_name: str, fact_content: str, category: str = "General", description: str = "")

Add base knowledge fact.

```python
base_kb.add_base_fact(
    entity_name="HeDaas",
    fact_content="HeDaas is a university",
    category="Organization",
    description="Core definition"
)
```

**Parameters**:
- `entity_name` (str): Entity name (case-insensitive)
- `fact_content` (str): Fact content
- `category` (str): Category
- `description` (str): Additional description

#### search(entity_name: str) -> List[Dict]

Search base knowledge by entity name (case-insensitive).

```python
results = base_kb.search("HeDaas")  # Works with any case
for fact in results:
    print(f"{fact['entity_name']}: {fact['fact_content']}")
```

**Parameters**:
- `entity_name` (str): Entity name to search

**Returns**:
- List[Dict]: Matching base knowledge items

#### get_all_facts() -> List[Dict]

Get all base knowledge facts.

```python
all_facts = base_kb.get_all_facts()
for fact in all_facts:
    print(f"[{fact['category']}] {fact['entity_name']}: {fact['fact_content']}")
```

**Returns**:
- List[Dict]: All base knowledge facts

---

## EmotionAnalyzer

Emotional relationship analysis system.

### Initialization

```python
from emotion_analyzer import EmotionAnalyzer

analyzer = EmotionAnalyzer()
```

### Main Methods

#### analyze(messages: List[Dict]) -> Dict

Analyze emotional relationship from conversation messages.

```python
# Prepare messages (last 10 rounds = 20 messages)
messages = agent.get_memory()[-20:]

emotion_data = analyzer.analyze(messages)
print(f"Intimacy: {emotion_data['intimacy']}")
print(f"Trust: {emotion_data['trust']}")
print(f"Overall: {emotion_data['overall_score']}")
```

**Parameters**:
- `messages` (List[Dict]): Conversation messages to analyze

**Returns**:
- Dict: Emotional analysis results with all dimensions and metadata

#### generate_tone_prompt(emotion_data: Dict) -> str

Generate tone adjustment prompt based on emotional state.

```python
emotion = agent.get_emotion_data()
if emotion:
    prompt = analyzer.generate_tone_prompt(emotion)
    print(f"Tone guidance: {prompt}")
```

**Parameters**:
- `emotion_data` (Dict): Emotional analysis data

**Returns**:
- str: Tone adjustment prompt for LLM

---

## DatabaseManager

SQLite database management.

### Initialization

```python
from database_manager import DatabaseManager

db = DatabaseManager(db_name="chat_agent.db")
```

### Main Methods

#### set(key: str, value: Any)

Store data with key.

```python
db.set("my_data", {"name": "John", "age": 25})
```

#### get(key: str, default: Any = None) -> Any

Retrieve data by key.

```python
data = db.get("my_data", default={})
print(data)
```

#### delete(key: str)

Delete data by key.

```python
db.delete("my_data")
```

#### list_keys() -> List[str]

List all keys.

```python
keys = db.list_keys()
print(f"Available keys: {keys}")
```

---

## DebugLogger

Debug logging system for troubleshooting.

### Initialization

```python
from debug_logger import DebugLogger

# Get singleton instance
logger = DebugLogger.get_instance()
```

### Main Methods

#### log(log_type: str, module: str, message: str, details: Dict = None)

Log a message.

```python
logger.log(
    log_type="info",
    module="ChatAgent",
    message="Processing user input",
    details={"input_length": 25}
)
```

**Log Types**:
- `module`: Module operation tracking
- `prompt`: Prompt content recording
- `request`: API request details
- `response`: API response details
- `error`: Error and exception
- `info`: General information

#### get_logs(log_type: str = None, limit: int = 100) -> List[Dict]

Retrieve logs.

```python
# Get all logs
all_logs = logger.get_logs()

# Get error logs only
errors = logger.get_logs(log_type="error", limit=50)

# Get last 10 logs
recent = logger.get_logs(limit=10)
```

**Parameters**:
- `log_type` (str, optional): Filter by log type
- `limit` (int): Maximum number of logs to return

**Returns**:
- List[Dict]: Log entries

#### clear_logs()

Clear all logs from memory (file logs remain).

```python
logger.clear_logs()
```

---

## Usage Examples

### Complete Workflow Example

```python
from chat_agent import ChatAgent

# Initialize agent
agent = ChatAgent()

# Conversation loop
for i in range(15):
    user_input = input("You: ")
    response = agent.chat(user_input)
    print(f"AI: {response}\n")

# Check memory
print(f"Messages: {len(agent.get_memory())}")

# Check knowledge (after 5 rounds)
if i >= 5:
    knowledge = agent.knowledge_base.get_all_knowledge()
    print(f"Knowledge items: {len(knowledge)}")

# Check emotion (after 10 rounds)
if i >= 10:
    emotion = agent.get_emotion_data()
    if emotion:
        print(f"Relationship: {emotion['relationship_type']}")
```

### Error Handling Example

```python
from chat_agent import ChatAgent

agent = ChatAgent()

try:
    response = agent.chat(user_input)
    print(response)
except ValueError as e:
    print(f"Input error: {e}")
except Exception as e:
    print(f"Unexpected error: {e}")
    # Check debug logs
    from debug_logger import DebugLogger
    logger = DebugLogger.get_instance()
    errors = logger.get_logs(log_type="error", limit=5)
    for error in errors:
        print(f"  {error['message']}")
```

---

## Configuration

All API classes can be configured via `.env` file:

```env
# API Settings
SILICONFLOW_API_KEY=your_key_here
MODEL_NAME=Qwen/Qwen2.5-7B-Instruct
TEMPERATURE=0.8
MAX_TOKENS=2000

# Memory Settings
MAX_MEMORY_MESSAGES=50
MAX_SHORT_TERM_ROUNDS=20

# Debug Settings
DEBUG_MODE=True
DEBUG_LOG_FILE=debug.log
```

---

## More Information

- [Usage Examples](EXAMPLES_EN.md) - Practical examples
- [Development Guide](DEVELOPMENT_EN.md) - Architecture details
- [Troubleshooting](TROUBLESHOOTING_EN.md) - Problem solving

---

<div align="center">

**Happy coding!** 🚀

</div>
