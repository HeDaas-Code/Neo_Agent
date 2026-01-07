# API Documentation

English | [简体中文](../zh-cn/API.md)

This document provides detailed API interfaces and usage methods for all Neo Agent modules.

## 📚 Table of Contents

- [DatabaseManager](#databasemanager) - Database Management
- [ChatAgent](#chatagent) - Dialogue Agent
- [LongTermMemoryManager](#longtermmemorymanager) - Long-term Memory Management
- [KnowledgeBase](#knowledgebase) - Knowledge Base Management
- [EmotionRelationshipAnalyzer](#emotionrelationshipanalyzer) - Emotion Analysis
- [AgentVisionTool](#agentvisiontool) - Vision Tools
- [ExpressionStyleManager](#expressionstylemanager) - Expression Style Management
- [BaseKnowledge](#baseknowledge) - Base Knowledge Management
- [DebugLogger](#debuglogger) - Debug Logging

---

## DatabaseManager

Database manager responsible for all data persistence.

### Initialization

```python
from database_manager import DatabaseManager

db = DatabaseManager(
    db_path="chat_agent.db",  # Database file path
    debug=False                # Enable debug mode
)
```

### Short-term Memory API

#### add_short_term_message

Add message to short-term memory.

```python
db.add_short_term_message(
    role: str,      # 'user' or 'assistant'
    content: str    # Message content
) -> None
```

**Example**:
```python
db.add_short_term_message('user', 'Hello')
db.add_short_term_message('assistant', 'Hi! Nice to meet you')
```

#### get_short_term_messages

Get short-term memory message list.

```python
db.get_short_term_messages(
    limit: Optional[int] = None  # Limit number of messages returned
) -> List[Dict[str, Any]]
```

**Return format**:
```python
[
    {
        'id': 1,
        'role': 'user',
        'content': 'Hello',
        'timestamp': '2024-01-01T12:00:00'
    },
    ...
]
```

#### clear_short_term_memory

Clear all short-term memory.

```python
db.clear_short_term_memory() -> None
```

### Long-term Memory API

#### add_long_term_summary

Add long-term memory summary.

```python
db.add_long_term_summary(
    summary: str,               # Summary content
    conversation_count: int,    # Conversation rounds
    start_time: str,           # Start time
    end_time: str              # End time
) -> None
```

**Example**:
```python
db.add_long_term_summary(
    summary="User asked about Python programming, we discussed the difference between functions and classes",
    conversation_count=10,
    start_time="2024-01-01T10:00:00",
    end_time="2024-01-01T11:00:00"
)
```

#### get_long_term_summaries

Get long-term memory summary list.

```python
db.get_long_term_summaries(
    limit: Optional[int] = None
) -> List[Dict[str, Any]]
```

### Knowledge Base API

#### add_entity

Add entity to knowledge base.

```python
db.add_entity(
    name: str  # Entity name
) -> str      # Returns entity UUID
```

#### add_entity_definition

Add definition for entity.

```python
db.add_entity_definition(
    entity_uuid: str,       # Entity UUID
    content: str,          # Definition content
    type: str = 'definition',  # Definition type
    source: str = None,    # Source
    confidence: float = 1.0,  # Confidence (0-1)
    priority: int = 50     # Priority
) -> None
```

#### search_entities

Search entities.

```python
db.search_entities(
    query_text: str,           # Search keyword
    limit: int = 10,          # Number of results
    min_confidence: float = 0.0  # Minimum confidence
) -> List[Dict[str, Any]]
```

**Return format**:
```python
[
    {
        'uuid': 'xxx-xxx-xxx',
        'name': 'Python',
        'normalized_name': 'python',
        'definitions': [
            {
                'content': 'Python is a high-level programming language',
                'type': 'definition',
                'confidence': 1.0
            }
        ],
        'related_info': [...]
    }
]
```

### Base Knowledge API

#### add_base_knowledge

Add base knowledge.

```python
db.add_base_knowledge(
    entity_name: str,           # Entity name
    content: str,              # Knowledge content
    category: str = 'General',  # Category
    description: str = None,   # Description
    priority: int = 100,       # Priority (higher = more priority)
    confidence: float = 1.0    # Confidence
) -> None
```

#### get_base_knowledge

Get base knowledge.

```python
db.get_base_knowledge(
    entity_name: str = None  # Entity name, None returns all
) -> List[Dict[str, Any]]
```

---

## ChatAgent

Core dialogue agent class that handles LLM interactions.

### Initialization

```python
from chat_agent import ChatAgent

agent = ChatAgent(
    api_key: str = None,           # API key, defaults to env var
    api_url: str = None,           # API URL
    model_name: str = None,        # Model name
    temperature: float = 0.8,      # Generation temperature
    max_tokens: int = 2000,        # Maximum tokens
    db_manager: DatabaseManager = None  # Database manager instance
)
```

### chat

Send message and get response.

```python
response = agent.chat(
    user_input: str,              # User input
    use_memory: bool = True,      # Whether to use memory
    stream: bool = False          # Whether to stream output
) -> str  # Returns assistant response
```

**Example**:
```python
response = agent.chat("Hello, please introduce yourself")
print(response)
```

### get_character_prompt

Get character system prompt.

```python
prompt = agent.get_character_prompt() -> str
```

### clear_memory

Clear conversation memory.

```python
agent.clear_memory() -> None
```

---

## LongTermMemoryManager

Long-term memory manager that handles conversion between short and long-term memory.

### Initialization

```python
from long_term_memory import LongTermMemoryManager

memory_manager = LongTermMemoryManager(
    db_manager: DatabaseManager = None,  # Database manager
    api_key: str = None,
    api_url: str = None,
    model_name: str = None
)
```

### add_message

Add message (automatically handles memory conversion).

```python
memory_manager.add_message(
    role: str,      # 'user' or 'assistant'
    content: str    # Message content
) -> None
```

### get_relevant_memory

Get relevant memory for conversation.

```python
memory = memory_manager.get_relevant_memory(
    query: str = None,  # Query keyword (optional)
    limit: int = 10     # Limit number of results
) -> Dict[str, Any]
```

**Return format**:
```python
{
    'short_term': [  # Short-term memory
        {'role': 'user', 'content': '...'},
        {'role': 'assistant', 'content': '...'}
    ],
    'long_term': [   # Long-term summaries
        {'summary': '...', 'conversation_count': 10}
    ],
    'knowledge': [   # Relevant knowledge
        {'entity': 'Python', 'definition': '...'}
    ]
}
```

---

## KnowledgeBase

Knowledge base management class that extracts and manages knowledge from conversations.

### Initialization

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

Extract knowledge from conversation.

```python
result = kb.extract_knowledge_from_conversation(
    messages: List[Dict[str, str]],  # Conversation messages
    force: bool = False               # Force extraction
) -> Dict[str, Any]
```

**Message format**:
```python
messages = [
    {'role': 'user', 'content': 'What is Python?'},
    {'role': 'assistant', 'content': 'Python is a programming language...'}
]
```

**Return format**:
```python
{
    'success': True,
    'entities_extracted': 3,
    'entities': [
        {
            'name': 'Python',
            'type': 'Programming Language',
            'definition': '...'
        }
    ]
}
```

### search_knowledge

Search knowledge.

```python
results = kb.search_knowledge(
    query: str,      # Search keyword
    limit: int = 5   # Number of results
) -> List[Dict[str, Any]]
```

---

## EmotionRelationshipAnalyzer

Emotion relationship analyzer that analyzes emotional tendencies in conversations.

### Initialization

```python
from emotion_analyzer import EmotionRelationshipAnalyzer

analyzer = EmotionRelationshipAnalyzer(
    api_key: str = None,
    api_url: str = None,
    model_name: str = None
)
```

### analyze_emotion

Analyze emotional relationship.

```python
result = analyzer.analyze_emotion(
    messages: List[Dict[str, str]],  # Conversation messages
    recent_rounds: int = 10           # Analyze recent N rounds
) -> Dict[str, Any]
```

**Return format**:
```python
{
    'intimacy': 75,      # Intimacy (0-100)
    'trust': 80,         # Trust (0-100)
    'joy': 85,          # Joy (0-100)
    'empathy': 70,      # Empathy (0-100)
    'dependence': 60,   # Dependence (0-100)
    'overall': 74,      # Overall score
    'analysis': '...'   # Analysis description
}
```

### format_emotion_summary

Format emotion analysis result.

```python
summary = format_emotion_summary(
    emotion_data: Dict[str, Any]  # Emotion data
) -> str
```

---

## AgentVisionTool

Agent vision tool that simulates visual perception.

### Initialization

```python
from agent_vision import AgentVisionTool

vision = AgentVisionTool(
    db_manager: DatabaseManager
)
```

### set_environment

Set environment description.

```python
vision.set_environment(
    description: str,   # Environment description
    category: str = 'General'  # Environment category
) -> None
```

**Example**:
```python
vision.set_environment(
    description="There is a table in the room with a book on it",
    category="Indoor"
)
```

### get_current_environment

Get current environment description.

```python
env = vision.get_current_environment() -> Dict[str, Any]
```

**Return format**:
```python
{
    'description': 'There is a table in the room...',
    'category': 'Indoor',
    'timestamp': '2024-01-01T12:00:00'
}
```

### clear_environment

Clear environment description.

```python
vision.clear_environment() -> None
```

---

## DebugLogger

Debug logger that records system operation details.

### Get Instance

```python
from debug_logger import get_debug_logger

logger = get_debug_logger()
```

### log_info

Log information.

```python
logger.log_info(
    module: str,       # Module name
    action: str,       # Action description
    data: Dict = None  # Additional data
) -> None
```

**Example**:
```python
logger.log_info(
    'ChatAgent',
    'Send user message',
    {'message_length': 50}
)
```

### log_prompt

Log prompt.

```python
logger.log_prompt(
    prompt: str,       # Prompt content
    context: Dict = None  # Context information
) -> None
```

### log_api_call

Log API call.

```python
logger.log_api_call(
    endpoint: str,     # API endpoint
    request: Dict,     # Request data
    response: Dict,    # Response data
    duration: float    # Duration (seconds)
) -> None
```

### get_logs

Get log records.

```python
logs = logger.get_logs(
    limit: int = 100,           # Number of records
    level: str = None,          # Log level filter
    module: str = None          # Module filter
) -> List[Dict[str, Any]]
```

---

## ExpressionStyleManager

Expression style manager for managing agent's personalized expressions and learning user expression habits.

### Initialization

```python
from expression_style import ExpressionStyleManager

manager = ExpressionStyleManager(
    db_manager=db,                      # Database manager (optional)
    api_key="your-api-key",            # API key (optional)
    api_url="https://api.url",         # API URL (optional)
    model_name="model-name"            # Model name (optional)
)
```

### add_agent_expression

Add agent personalized expression.

```python
expr_uuid = manager.add_agent_expression(
    expression: str,    # Expression (e.g., 'wc', 'hhh')
    meaning: str,       # Meaning description
    category: str = "通用"  # Category
) -> str
```

**Example**:
```python
expr_uuid = manager.add_agent_expression(
    expression="wc",
    meaning="Expresses surprise at unexpected events",
    category="Exclamation"
)
```

### get_agent_expressions

Get all agent personalized expressions.

```python
expressions = manager.get_agent_expressions(
    active_only: bool = True  # Whether to get only active expressions
) -> List[Dict[str, Any]]
```

### update_agent_expression

Update agent expression.

```python
success = manager.update_agent_expression(
    expr_uuid: str,  # Expression UUID
    **kwargs         # Fields to update (expression, meaning, category, is_active, etc.)
) -> bool
```

### delete_agent_expression

Delete agent expression.

```python
success = manager.delete_agent_expression(
    expr_uuid: str  # Expression UUID
) -> bool
```

### add_user_habit

Add user expression habit.

```python
habit_uuid = manager.add_user_habit(
    expression: str,      # User expression
    meaning: str,         # Meaning
    context: str = "",    # Usage context
    confidence: float = 0.5  # Confidence (0-1)
) -> str
```

### get_user_habits

Get user expression habits.

```python
habits = manager.get_user_habits(
    active_only: bool = True,
    min_confidence: float = 0.0
) -> List[Dict[str, Any]]
```

### learn_from_conversation

Learn user expression habits from conversation.

```python
result = manager.learn_from_conversation(
    messages: List[Dict[str, Any]]  # Conversation message list
) -> Dict[str, Any]
```

**Returns**:
```python
{
    'learned': True/False,
    'habits_found': [...],  # List of discovered habits
    'message': '...'
}
```

### format_expressions_for_prompt

Format expression list for prompt.

```python
prompt_text = manager.format_expressions_for_prompt(
    expressions: List[Dict[str, Any]]
) -> str
```

---

## BaseKnowledge

Base knowledge manager for managing agent's core base knowledge, which has highest priority and cannot be overridden.

### Initialization

```python
from base_knowledge import BaseKnowledge

bk = BaseKnowledge(
    db_manager=db  # Database manager (optional)
)
```

### add_base_fact

Add base fact.

```python
success = bk.add_base_fact(
    entity_name: str,       # Entity name (e.g., "HeDaas")
    fact_content: str,      # Fact content (e.g., "HeDaas is a university")
    category: str = "General", # Category
    description: str = "",  # Description
    immutable: bool = True  # Whether immutable
) -> bool
```

**Example**:
```python
success = bk.add_base_fact(
    entity_name="HeDaas",
    fact_content="HeDaas is a university",
    category="Institution Type",
    description="Basic definition of HeDaas",
    immutable=True
)
```

### get_base_fact

Get base fact for specified entity.

```python
fact = bk.get_base_fact(
    entity_name: str  # Entity name
) -> Dict[str, Any]
```

**Returns**:
```python
{
    'entity_name': 'HeDaas',
    'content': 'HeDaas is a university',
    'category': 'Institution Type',
    'description': '...',
    'immutable': True,
    'created_at': '...',
    'updated_at': '...'
}
```

### get_all_base_facts

Get all base facts.

```python
facts = bk.get_all_base_facts() -> List[Dict[str, Any]]
```

### update_base_fact

Update base fact (only non-immutable items).

```python
success = bk.update_base_fact(
    entity_name: str,
    **kwargs  # Fields to update
) -> bool
```

### delete_base_fact

Delete base fact.

```python
success = bk.delete_base_fact(
    entity_name: str  # Entity name
) -> bool
```

### get_all_for_prompt

Get formatted base knowledge text for prompt.

```python
prompt_text = bk.get_all_for_prompt() -> str
```

**Returns example**:
```
=== Base Knowledge (Absolute Authority) ===

1. HeDaas (Institution Type)
   HeDaas is a university
   Description: Basic definition of HeDaas

========================
```

---

## 🔧 Utility Functions

### normalize_text

Text normalization (for entity name standardization).

```python
from knowledge_base import normalize_text

normalized = normalize_text(text: str) -> str
```

**Example**:
```python
normalize_text("  Python  ")  # Returns: "python"
normalize_text("Python Programming")  # Returns: "python programming"
```

### format_timestamp

Format timestamp.

```python
from datetime import datetime

timestamp = datetime.now().isoformat()
# Returns: "2024-01-01T12:00:00.000000"
```

---

## 📊 Data Models

### Message

```python
{
    'id': int,              # Message ID
    'role': str,            # 'user' or 'assistant'
    'content': str,         # Message content
    'timestamp': str        # ISO format timestamp
}
```

### Entity

```python
{
    'uuid': str,            # Unique identifier
    'name': str,            # Entity name
    'normalized_name': str, # Normalized name
    'created_at': str,      # Creation time
    'updated_at': str       # Update time
}
```

### Summary

```python
{
    'id': int,              # Summary ID
    'summary': str,         # Summary content
    'conversation_count': int,  # Conversation rounds
    'start_time': str,      # Start time
    'end_time': str,        # End time
    'created_at': str       # Creation time
}
```

---

## 🎯 Usage Examples

### Complete Conversation Flow

```python
from chat_agent import ChatAgent
from database_manager import DatabaseManager

# 1. Initialize
db = DatabaseManager()
agent = ChatAgent(db_manager=db)

# 2. Start conversation
response = agent.chat("Hello")
print(response)

# 3. Continue conversation
response = agent.chat("Do you know Python?")
print(response)

# 4. View memory
messages = db.get_short_term_messages()
for msg in messages:
    print(f"{msg['role']}: {msg['content']}")
```

### Knowledge Extraction

```python
from knowledge_base import KnowledgeBase

kb = KnowledgeBase(db_manager=db)

# Extract knowledge from conversation
messages = db.get_short_term_messages()
result = kb.extract_knowledge_from_conversation(messages)

print(f"Extracted {result['entities_extracted']} entities")

# Search knowledge
results = kb.search_knowledge("Python")
for entity in results:
    print(f"{entity['name']}: {entity['definitions'][0]['content']}")
```

### Emotion Analysis

```python
from emotion_analyzer import EmotionRelationshipAnalyzer

analyzer = EmotionRelationshipAnalyzer()

# Analyze emotion
messages = db.get_short_term_messages()
emotion = analyzer.analyze_emotion(messages)

print(f"Intimacy: {emotion['intimacy']}")
print(f"Trust: {emotion['trust']}")
print(f"Overall: {emotion['overall']}")
```

---

## 🚨 Error Handling

All API calls should include error handling:

```python
try:
    response = agent.chat("Hello")
except Exception as e:
    print(f"Error: {e}")
    # Handle error
```

Common errors:
- `ValueError`: Invalid parameters
- `ConnectionError`: API connection failed
- `TimeoutError`: Request timeout
- `sqlite3.Error`: Database error

---

## 📝 Notes

1. **Thread Safety**: DatabaseManager uses context manager, opening new connection for each operation
2. **Memory Management**: Short-term memory automatically limits quantity to avoid overflow
3. **API Rate Limiting**: Be aware of API call frequency limits
4. **Data Backup**: Regularly backup `chat_agent.db` file

---

## 🔗 Related Documentation

- [Quick Start](QUICKSTART_EN.md)
- [Development Guide](DEVELOPMENT_EN.md)
- [Architecture Design](ARCHITECTURE_EN.md)

---

Last updated: 2024-01-01
