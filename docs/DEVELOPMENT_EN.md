# Development Guide

[中文](DEVELOPMENT.md) | **English**

In-depth guide for developers to understand Neo_Agent architecture and development workflow.

## Table of Contents

- [Getting Started](#getting-started)
- [Project Architecture](#project-architecture)
- [Core Modules](#core-modules)
- [Development Workflow](#development-workflow)
- [Debugging Techniques](#debugging-techniques)
- [Best Practices](#best-practices)
- [Common Development Tasks](#common-development-tasks)

---

## Getting Started

### Prerequisites

- Python 3.8 or higher
- Git
- Code editor (VS Code, PyCharm, etc.)
- Basic understanding of:
  - Python programming
  - LangChain framework
  - SQLite database
  - Tkinter GUI

### Development Environment Setup

```bash
# Clone repository
git clone https://github.com/HeDaas-Code/Neo_Agent.git
cd Neo_Agent

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows
venv\Scripts\activate
# Linux/Mac
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Install development tools
pip install pytest black flake8 mypy

# Configure environment
cp example.env .env
# Edit .env with your API key
```

### Project Structure

```
Neo_Agent/
├── chat_agent.py              # Core dialogue agent
├── long_term_memory.py        # Memory management
├── knowledge_base.py          # Knowledge system
├── base_knowledge.py          # Base knowledge (priority 100%)
├── emotion_analyzer.py        # Emotional analysis
├── database_manager.py        # Database operations
├── debug_logger.py            # Debug logging
├── gui_enhanced.py            # Enhanced GUI
├── database_gui.py            # Database GUI
├── requirements.txt           # Python dependencies
├── .env                       # Configuration (not in git)
└── docs/                      # Documentation
```

---

## Project Architecture

### System Architecture Overview

```
┌─────────────────────────────────────────┐
│         Presentation Layer               │
│  ┌────────────────────────────────────┐ │
│  │   GUI Enhanced (Tkinter)           │ │
│  │   - Chat Interface                 │ │
│  │   - Visualization (Timeline/Radar) │ │
│  │   - Debug Monitor                  │ │
│  └────────────────────────────────────┘ │
└──────────────┬──────────────────────────┘
               │
┌──────────────▼──────────────────────────┐
│         Business Logic Layer            │
│  ┌────────────────────────────────────┐ │
│  │   ChatAgent (Core Controller)      │ │
│  │   - Conversation Management        │ │
│  │   - Memory Orchestration           │ │
│  │   - Knowledge Retrieval            │ │
│  │   - Emotion Analysis Trigger       │ │
│  └────────────────────────────────────┘ │
│               │                         │
│     ┌─────────┼─────────┐               │
│     ▼         ▼         ▼               │
│  ┌──────┐ ┌──────┐ ┌──────────┐        │
│  │Memory│ │Know- │ │Emotion   │        │
│  │Mgr   │ │ledge │ │Analyzer  │        │
│  └──────┘ └──────┘ └──────────┘        │
└──────────────┬──────────────────────────┘
               │
┌──────────────▼──────────────────────────┐
│         Data Layer                      │
│  ┌────────────────────────────────────┐ │
│  │   DatabaseManager (SQLite)         │ │
│  │   - Memory Data                    │ │
│  │   - Knowledge Data                 │ │
│  │   - Emotion Data                   │ │
│  └────────────────────────────────────┘ │
└──────────────┬──────────────────────────┘
               │
┌──────────────▼──────────────────────────┐
│         External Services               │
│  ┌────────────────────────────────────┐ │
│  │   LLM API (SiliconFlow)            │ │
│  │   - Conversation Generation        │ │
│  │   - Memory Summarization           │ │
│  │   - Knowledge Extraction           │ │
│  │   - Emotion Analysis               │ │
│  └────────────────────────────────────┘ │
└─────────────────────────────────────────┘
```

### Data Flow

```
User Input
    ↓
┌──────────────────────┐
│   ChatAgent.chat()   │
│  1. Preprocess       │
│  2. Entity Extract   │
│  3. Knowledge Search │
│  4. Emotion Check    │
│  5. Build Prompt     │
│  6. Call LLM         │
│  7. Post-process     │
└──────┬───────────────┘
       ↓
┌──────────────────────┐
│  Trigger Conditions  │
│  - Every 5: Extract  │
│  - Every 10: Emotion │
│  - Every 20: Archive │
└──────┬───────────────┘
       ↓
   AI Response + GUI Update
```

---

## Core Modules

### 1. ChatAgent (chat_agent.py)

**Responsibilities**:
- Manage conversation flow
- Coordinate all subsystems
- Handle LLM interactions
- Trigger periodic tasks

**Key Methods**:
```python
def chat(self, user_input: str) -> str:
    """Main conversation entry point"""
    
def _extract_entities(self, text: str) -> List[str]:
    """Extract entities from text"""
    
def _search_knowledge(self, entities: List[str]) -> Dict:
    """Search knowledge base for entities"""
    
def _check_and_trigger_emotion(self):
    """Check if emotion analysis should trigger"""
```

### 2. KnowledgeBase (knowledge_base.py)

**Responsibilities**:
- Store structured knowledge
- Extract knowledge from conversations
- Provide knowledge search
- Manage knowledge lifecycle

**Data Structure**:
```json
{
  "uuid": "unique-id",
  "title": "Knowledge title",
  "content": "Knowledge content",
  "type": "个人信息|偏好|事实|经历|观点",
  "tags": ["tag1", "tag2"],
  "created_at": "2025-01-15T10:00:00",
  "confidence": 0.9
}
```

### 3. EmotionAnalyzer (emotion_analyzer.py)

**Responsibilities**:
- Analyze emotional relationships
- Generate 5-dimensional scores
- Determine relationship type
- Adjust AI tone based on emotion

**Dimensions**:
- Intimacy (亲密度): 0-100
- Trust (信任度): 0-100
- Pleasure (愉悦度): 0-100
- Resonance (共鸣度): 0-100
- Dependence (依赖度): 0-100

### 4. DatabaseManager (database_manager.py)

**Responsibilities**:
- Abstract database operations
- Provide key-value storage
- Handle data persistence
- Support SQLite operations

**Usage**:
```python
db = DatabaseManager()

# Store data
db.set("key", {"data": "value"})

# Retrieve data
data = db.get("key", default={})

# List keys
keys = db.list_keys()
```

---

## Development Workflow

### 1. Feature Development

```bash
# Create feature branch
git checkout -b feature/new-feature

# Make changes
# ... edit code ...

# Test locally
python gui_enhanced.py

# Run tests
pytest tests/

# Format code
black .

# Commit
git add .
git commit -m "feat: add new feature"

# Push and create PR
git push origin feature/new-feature
```

### 2. Bug Fixing

```bash
# Create bugfix branch
git checkout -b fix/bug-description

# Enable DEBUG mode
# In .env: DEBUG_MODE=True

# Reproduce bug
python gui_enhanced.py

# Check debug logs
tail -f debug.log

# Fix bug
# ... edit code ...

# Test fix
python gui_enhanced.py

# Commit and push
git commit -m "fix: resolve bug description"
git push origin fix/bug-description
```

### 3. Code Review Checklist

- [ ] Code follows PEP 8 style
- [ ] Functions have docstrings
- [ ] No hardcoded values (use .env)
- [ ] Error handling implemented
- [ ] Tests written and passing
- [ ] Documentation updated
- [ ] No debug print statements
- [ ] Performance considered

---

## Debugging Techniques

### 1. Enable Debug Mode

```env
# .env
DEBUG_MODE=True
DEBUG_LOG_FILE=debug.log
```

### 2. Use Debug Logger

```python
from debug_logger import DebugLogger

logger = DebugLogger.get_instance()

# Log module operation
logger.log("module", "ChatAgent", "Processing input")

# Log prompt
logger.log("prompt", "LLM", prompt_text)

# Log errors
logger.log("error", "ChatAgent", str(error), {"traceback": tb})
```

### 3. Inspect Data

```python
from chat_agent import ChatAgent

agent = ChatAgent()

# Check internal state
print(f"Current rounds: {agent.current_rounds}")
print(f"Memory size: {len(agent.get_memory())}")

# Check database
from database_manager import DatabaseManager
db = DatabaseManager()
print(f"All keys: {db.list_keys()}")
```

### 4. Test Individual Modules

```python
# Test knowledge base
from knowledge_base import KnowledgeBase
kb = KnowledgeBase()
result = kb.search("test")
print(result)

# Test emotion analyzer
from emotion_analyzer import EmotionAnalyzer
analyzer = EmotionAnalyzer()
# ... test methods ...
```

---

## Best Practices

### 1. Code Style

```python
# Good: Clear, documented, typed
def extract_knowledge(
    self, 
    messages: List[Dict[str, str]], 
    rounds: int
) -> List[Dict[str, Any]]:
    """Extract knowledge from conversation messages.
    
    Args:
        messages: List of conversation messages
        rounds: Number of conversation rounds
        
    Returns:
        List of extracted knowledge items
    """
    pass

# Bad: Unclear, no docs, no types
def extract(msgs, r):
    pass
```

### 2. Error Handling

```python
# Good: Specific handling with logging
try:
    response = self._call_llm(prompt)
except APIError as e:
    logger.log("error", "ChatAgent", f"API failed: {e}")
    return "Sorry, I'm having trouble responding."
except Exception as e:
    logger.log("error", "ChatAgent", f"Unexpected: {e}")
    raise

# Bad: Generic catch-all
try:
    response = self._call_llm(prompt)
except:
    pass
```

### 3. Configuration Management

```python
# Good: Use environment variables
import os
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("SILICONFLOW_API_KEY")

# Bad: Hardcode values
API_KEY = "sk-xxxxxxxxxxxx"  # Never do this!
```

### 4. Testing

```python
# Write unit tests
def test_chat_basic():
    agent = ChatAgent()
    response = agent.chat("Hello")
    assert response is not None
    assert isinstance(response, str)
    
# Write integration tests
def test_full_workflow():
    agent = ChatAgent()
    # Test 5 rounds -> knowledge extraction
    for i in range(5):
        agent.chat(f"I like topic {i}")
    knowledge = agent.knowledge_base.get_all_knowledge()
    assert len(knowledge) > 0
```

---

## Common Development Tasks

### Task 1: Add New Knowledge Type

```python
# 1. Update knowledge_base.py
KNOWLEDGE_TYPES = [
    "个人信息", "偏好", "事实", "经历", "观点",
    "新类型"  # Add new type
]

# 2. Update extraction prompt
# In _extract_knowledge method, add new type to instructions

# 3. Update GUI
# In gui_enhanced.py, add filter option for new type
```

### Task 2: Modify Trigger Frequency

```python
# In chat_agent.py

# Change knowledge extraction (currently every 5 rounds)
if current_rounds % 3 == 0:  # Now every 3 rounds
    self._extract_knowledge()

# Change emotion analysis (currently every 10 rounds)
if current_rounds % 5 == 0:  # Now every 5 rounds
    self._check_and_trigger_emotion()
```

### Task 3: Add New Emotional Dimension

```python
# 1. Update emotion_analyzer.py
def analyze(self, messages):
    # ... existing code ...
    
    # Add new dimension
    new_dimension = self._analyze_new_dimension(messages)
    
    result = {
        # ... existing dimensions ...
        "new_dimension": new_dimension
    }
    return result

# 2. Update radar chart in GUI
# In gui_enhanced.py, EmotionRadarCanvas
# Modify to hexagon if adding 6th dimension
```

### Task 4: Integrate New LLM Provider

```python
# 1. Create new LLM wrapper
class NewLLMProvider:
    def __init__(self, api_key, model):
        self.api_key = api_key
        self.model = model
    
    def generate(self, prompt):
        # Implement API call
        pass

# 2. Update chat_agent.py
def _initialize_llm(self):
    provider = os.getenv("LLM_PROVIDER", "siliconflow")
    
    if provider == "siliconflow":
        # Existing code
        pass
    elif provider == "new_provider":
        return NewLLMProvider(api_key, model)
```

---

## Performance Optimization Tips

### 1. Database Optimization

```python
# Run VACUUM periodically
import sqlite3
conn = sqlite3.connect('chat_agent.db')
conn.execute('VACUUM')
conn.close()

# Use indexes for frequent queries
# Add in database_manager.py initialization
```

### 2. Memory Management

```python
# Limit memory size
MAX_MEMORY = 50  # Adjust based on needs

# Archive more frequently if memory grows too large
if len(memory) > MAX_MEMORY:
    self._archive_to_long_memory()
```

### 3. API Call Optimization

```python
# Cache responses when appropriate
from functools import lru_cache

@lru_cache(maxsize=100)
def _extract_entities(self, text):
    # Cached entity extraction
    pass

# Batch operations when possible
# Instead of multiple API calls, combine prompts
```

---

## Testing Guide

### Running Tests

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_chat_agent.py

# Run with coverage
pytest --cov=. tests/

# Run with verbose output
pytest -v tests/
```

### Writing Tests

```python
# tests/test_chat_agent.py
import pytest
from chat_agent import ChatAgent

class TestChatAgent:
    def setup_method(self):
        """Setup before each test"""
        self.agent = ChatAgent()
    
    def test_basic_chat(self):
        """Test basic conversation"""
        response = self.agent.chat("Hello")
        assert response
        assert len(response) > 0
    
    def test_memory_persistence(self):
        """Test memory is saved"""
        self.agent.chat("Test message")
        memory = self.agent.get_memory()
        assert len(memory) > 0
    
    def teardown_method(self):
        """Cleanup after each test"""
        # Clean up test data
        pass
```

---

## Contributing

See [Contributing Guide](../CONTRIBUTING_EN.md) for:
- Code standards
- Commit message format
- Pull request process
- Code review checklist

---

## More Resources

- [API Reference](API_EN.md) - Detailed API documentation
- [Usage Examples](EXAMPLES_EN.md) - Practical examples
- [Troubleshooting](TROUBLESHOOTING_EN.md) - Problem solving
- [Deployment Guide](DEPLOYMENT_EN.md) - Deployment instructions

---

<div align="center">

**Happy developing!** 💻

</div>
