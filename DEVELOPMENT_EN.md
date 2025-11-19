# Development Guide

English | [简体中文](DEVELOPMENT.md)

This document provides a comprehensive development guide for Neo Agent, including project structure, development workflow, and best practices.

## 📁 Project Structure

```
Neo_Agent/
├── gui_enhanced.py           # Main GUI interface (3050 lines)
│   ├── EmotionRadarCanvas    # Emotion radar chart component
│   ├── TimelineCanvas        # Timeline visualization component
│   ├── DebugLogViewer        # Debug log viewer
│   └── ChatGUI               # Main chat interface
│
├── chat_agent.py            # Dialogue agent core (809 lines)
│   ├── MemoryManager         # Memory manager (short-term)
│   └── ChatAgent             # Main dialogue agent class
│
├── database_manager.py      # Database management (1706 lines)
│   └── DatabaseManager       # Unified database manager
│       ├── Short-term memory management
│       ├── Long-term memory management
│       ├── Knowledge base management
│       ├── Base knowledge management
│       └── Environment description management
│
├── long_term_memory.py      # Long-term memory management (425 lines)
│   └── LongTermMemoryManager # Long-term memory manager
│       ├── Short→Long migration
│       ├── Memory summarization
│       └── Knowledge extraction trigger
│
├── knowledge_base.py        # Knowledge base management (842 lines)
│   └── KnowledgeBase         # Knowledge base class
│       ├── Entity recognition & extraction
│       ├── Knowledge normalization
│       └── Knowledge retrieval
│
├── emotion_analyzer.py      # Emotion analysis (706 lines)
│   └── EmotionRelationshipAnalyzer
│       ├── Emotional relationship analysis
│       └── Five-dimensional assessment
│
├── agent_vision.py          # Vision tools (496 lines)
│   └── AgentVisionTool       # Pseudo-vision tool
│       ├── Environment description management
│       └── Visual perception simulation
│
├── debug_logger.py          # Debug logging (408 lines)
│   └── DebugLogger           # Debug logger
│       ├── Prompt logging
│       ├── API call logging
│       └── Response logging
│
├── database_gui.py          # Database GUI (786 lines)
│   └── DatabaseGUI           # Database management interface
│       ├── Data viewing
│       ├── Data editing
│       └── Import/export
│
└── base_knowledge.py        # Base knowledge management (263 lines)
    └── BaseKnowledgeManager  # Base knowledge manager
        ├── Load base knowledge
        └── Update base knowledge
```

## 🏗️ Core Architecture

### 1. Data Flow Architecture

```
User Input
    ↓
ChatAgent (Main Controller)
    ↓
Memory Retrieval ← DatabaseManager → Data Persistence
    ↓
Prompt Building
    ↓
LLM API Call
    ↓
Response Processing
    ↓
Memory Update → LongTermMemoryManager → Knowledge Extraction
    ↓
Display to User
```

### 2. Memory System Architecture

```
┌─────────────────────────────────────────┐
│         User Conversation Input          │
└───────────────┬─────────────────────────┘
                ↓
┌───────────────────────────────────────────┐
│         MemoryManager                     │
│    (Add to short-term memory)            │
└───────────────┬───────────────────────────┘
                ↓
┌───────────────────────────────────────────┐
│    LongTermMemoryManager                  │
│  • Manage short-term memory (last 20)    │
│  • Generate summary→long-term when full  │
│  • Trigger knowledge extraction every 5  │
└───────────────┬───────────────────────────┘
                ↓
        ┌───────┴────────┐
        ↓                ↓
┌───────────────┐  ┌──────────────┐
│  Long-term    │  │  Knowledge   │
│  Summary      │  │  Base        │
└───────────────┘  └──────────────┘
```

### 3. Knowledge Management Architecture

```
Conversation Content
    ↓
KnowledgeBase.extract_knowledge_from_conversation()
    ↓
LLM extracts entities and relations
    ↓
Entity normalization (unify different expressions)
    ↓
Store to database
    ├── entities (entity main body)
    ├── entity_definitions (entity definitions)
    └── entity_related_info (related information)
```

## 🔧 Development Environment Setup

### 1. Development Dependencies

In addition to runtime dependencies, development requires:

```bash
# Code formatting
pip install black

# Code linting
pip install pylint flake8

# Type checking
pip install mypy

# Testing framework
pip install pytest pytest-cov
```

### 2. Recommended IDE Configuration

#### VS Code

Create `.vscode/settings.json`:

```json
{
    "python.linting.enabled": true,
    "python.linting.pylintEnabled": true,
    "python.formatting.provider": "black",
    "python.formatting.blackArgs": ["--line-length", "100"],
    "editor.formatOnSave": true,
    "python.analysis.typeCheckingMode": "basic"
}
```

#### PyCharm

1. Set Python interpreter to virtual environment
2. Enable code inspection and formatting
3. Configure Black as code formatter

## 💻 Core Module Details

### DatabaseManager (Database Manager)

**Responsibility**: Unified management of all data CRUD operations

**Main Methods**:

```python
# Short-term memory
add_short_term_message(role, content)
get_short_term_messages(limit)
clear_short_term_memory()

# Long-term memory
add_long_term_summary(summary, conversation_count, start_time, end_time)
get_long_term_summaries(limit)

# Knowledge base
add_entity(name)
add_entity_definition(entity_uuid, content, type, source)
search_entities(query_text, limit)

# Base knowledge
add_base_knowledge(entity_name, content, category)
get_base_knowledge(entity_name)
```

**Design Patterns**:
- Context Manager for database connections
- Factory pattern for database instance creation

### LongTermMemoryManager (Long-term Memory Manager)

**Responsibility**: Manage conversion between short-term and long-term memory

**Core Logic**:

```python
def add_message(self, role, content):
    # 1. Add to short-term memory
    self.db.add_short_term_message(role, content)
    
    # 2. Check if summarization needed
    if message_count > max_short_term_messages:
        # Generate summary and move to long-term
        self._summarize_and_archive()
    
    # 3. Check if knowledge extraction needed
    if conversation_count % extraction_interval == 0:
        # Trigger knowledge extraction
        self.knowledge_base.extract_knowledge()
```

### KnowledgeBase (Knowledge Base)

**Responsibility**: Extract and manage knowledge from conversations

**Knowledge Extraction Flow**:

```python
def extract_knowledge_from_conversation(self, messages):
    # 1. Build extraction prompt
    prompt = self._build_extraction_prompt(messages)
    
    # 2. Call LLM for extraction
    entities = self._call_llm_for_extraction(prompt)
    
    # 3. Normalize entity names
    normalized_entities = self._normalize_entities(entities)
    
    # 4. Store to database
    for entity in normalized_entities:
        self._save_entity(entity)
```

### EmotionRelationshipAnalyzer (Emotion Analyzer)

**Responsibility**: Analyze emotional relationships in conversations

**Analysis Dimensions**:
- Intimacy: Degree of relationship closeness
- Trust: Level of mutual trust
- Joy: Happiness in communication
- Empathy: Emotional resonance level
- Dependence: Mutual dependency level

## 🎨 GUI Development

### Component Structure

```python
ChatGUI (Main Window)
    ├── Left Panel
    │   ├── Chat history display
    │   ├── Input box
    │   └── Control buttons
    │
    ├── Right Panel
    │   ├── EmotionRadarCanvas (Emotion radar)
    │   ├── TimelineCanvas (Timeline)
    │   └── Statistics
    │
    └── Sub-windows
        ├── DatabaseGUI (Database management)
        └── DebugLogViewer (Debug log)
```

### Custom Canvas Components

Example of creating custom visualization components:

```python
class CustomCanvas(Canvas):
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self.bind('<Configure>', self.on_resize)
    
    def on_resize(self, event):
        # Respond to window size changes
        self.redraw()
    
    def redraw(self):
        # Redraw logic
        self.delete('all')
        # ... draw content
```

## 🔌 API Integration

### Adding New LLM Provider

1. Add configuration in `.env`:

```env
NEW_PROVIDER_API_KEY=xxx
NEW_PROVIDER_API_URL=xxx
```

2. Modify API calls in `chat_agent.py`:

```python
def call_llm(self, messages):
    provider = os.getenv('LLM_PROVIDER', 'siliconflow')
    
    if provider == 'new_provider':
        return self._call_new_provider(messages)
    else:
        return self._call_default_provider(messages)
```

## 🧪 Testing

### Unit Test Example

```python
import pytest
from database_manager import DatabaseManager

def test_add_short_term_message():
    db = DatabaseManager(':memory:')  # Use in-memory database
    db.add_short_term_message('user', 'Hello')
    
    messages = db.get_short_term_messages()
    assert len(messages) == 1
    assert messages[0]['role'] == 'user'
    assert messages[0]['content'] == 'Hello'
```

### Running Tests

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_database.py

# Generate coverage report
pytest --cov=. --cov-report=html
```

## 📝 Code Standards

### Naming Conventions

- **Classes**: PascalCase (e.g., `DatabaseManager`)
- **Functions**: snake_case (e.g., `add_message`)
- **Constants**: UPPER_CASE (e.g., `MAX_TOKENS`)
- **Private methods**: _leading_underscore (e.g., `_internal_method`)

### Docstrings

```python
def add_message(self, role: str, content: str) -> None:
    """
    Add message to memory
    
    Args:
        role: Role type ('user' or 'assistant')
        content: Message content
        
    Returns:
        None
        
    Raises:
        ValueError: If role is not valid
        
    Example:
        >>> manager.add_message('user', 'Hello')
    """
    pass
```

### Type Hints

```python
from typing import List, Dict, Any, Optional

def get_messages(self, limit: int = 10) -> List[Dict[str, Any]]:
    """Get message list"""
    pass

def find_entity(self, name: str) -> Optional[Dict[str, Any]]:
    """Find entity, return None if not exists"""
    pass
```

## 🐛 Debugging Tips

### Enable Verbose Logging

```python
import logging

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
```

### Use Debug Logger

```python
from debug_logger import get_debug_logger

debug_logger = get_debug_logger()
debug_logger.log_info('ModuleName', 'Operation description', {'key': 'value'})
```

### Database Query Debugging

```python
db = DatabaseManager(debug=True)  # Enable debug mode
# Will print all SQL queries
```

## 🔄 Development Workflow

### 1. Create Feature Branch

```bash
git checkout -b feature/new-feature
```

### 2. Develop and Test

```bash
# Write code
# Run tests
pytest

# Format code
black .

# Lint code
pylint *.py
```

### 3. Commit Code

```bash
git add .
git commit -m "feat: add new feature"
git push origin feature/new-feature
```

### 4. Create Pull Request

Create PR on GitHub and wait for review.

## 📊 Performance Optimization

### Database Optimization

```python
# Use indexes
cursor.execute('''
    CREATE INDEX IF NOT EXISTS idx_entity_name 
    ON entities(normalized_name)
''')

# Batch insert
cursor.executemany('''
    INSERT INTO messages (role, content) VALUES (?, ?)
''', messages)
```

### Memory Optimization

```python
# Limit memory size
MAX_SHORT_TERM_ROUNDS = 20  # Don't set too large

# Periodic cleanup
if len(messages) > MAX_MESSAGES:
    messages = messages[-MAX_MESSAGES:]
```

## 🚀 Deployment

### Package as Executable

Using PyInstaller:

```bash
pip install pyinstaller

pyinstaller --onefile --windowed gui_enhanced.py
```

### Docker Deployment

Create `Dockerfile`:

```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

CMD ["python", "gui_enhanced.py"]
```

## 🔐 Security Considerations

1. **Don't commit API keys**:
   - Use `.env` file
   - Add to `.gitignore`

2. **Input validation**:
   - Validate all user input
   - Prevent SQL injection

3. **Data encryption**:
   - Encrypt sensitive data
   - Use HTTPS communication

## 📚 Recommended Resources

- [LangChain Documentation](https://python.langchain.com/)
- [SQLite Tutorial](https://www.sqlitetutorial.net/)
- [Tkinter Documentation](https://docs.python.org/3/library/tkinter.html)
- [Python Best Practices](https://docs.python-guide.org/)

## 🤝 Contributing Guidelines

1. Fork the project
2. Create feature branch
3. Write code and tests
4. Submit Pull Request
5. Wait for review

For more details, see [CONTRIBUTING.md](CONTRIBUTING.md) (to be created)

## 💬 Getting Help

- Submit [Issue](https://github.com/HeDaas-Code/Neo_Agent/issues)
- Join [Discussions](https://github.com/HeDaas-Code/Neo_Agent/discussions)
- Check existing documentation

---

Happy coding! 🎉
