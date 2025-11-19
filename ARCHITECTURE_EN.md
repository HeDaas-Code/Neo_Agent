# Architecture Design Document

English | [简体中文](ARCHITECTURE.md)

This document describes the system architecture, design principles, and technical implementation of Neo Agent in detail.

## 📐 Design Philosophy

### Core Objectives

Neo Agent's design revolves around the following core objectives:

1. **Persistent Memory**: Implement true long-term memory capability for AI to remember historical conversations
2. **Knowledge Accumulation**: Extract and accumulate knowledge from conversations to form a searchable knowledge base
3. **Emotional Understanding**: Analyze and understand emotional relationships in conversations for more humanized interaction
4. **Modular Design**: Independent and extensible modules for easy maintenance and upgrades
5. **Data Security**: Local storage with users having complete control over their data

### Design Principles

- **Single Responsibility**: Each module focuses on a specific function
- **Loose Coupling**: Modules interact through well-defined interfaces
- **High Cohesion**: Related functions are centralized within the same module
- **Extensibility**: Easy to add new features and integrate new technologies
- **Performance First**: Optimize database queries and memory usage

## 🏛️ System Architecture

### Overall Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                      User Interface Layer (GUI)              │
│                      gui_enhanced.py                        │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │Chat UI   │  │Emotion   │  │Timeline  │  │Database  │   │
│  │          │  │Radar     │  │Chart     │  │Manager   │   │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘   │
└───────────────────────────┬─────────────────────────────────┘
                            │
┌───────────────────────────┴─────────────────────────────────┐
│                      Business Logic Layer                    │
│                                                              │
│  ┌────────────────┐  ┌────────────────┐  ┌──────────────┐ │
│  │  ChatAgent     │  │EmotionAnalyzer │  │ VisionTool   │ │
│  │  (Dialogue)    │  │  (Emotion)     │  │ (Vision Sim) │ │
│  └────────┬───────┘  └────────────────┘  └──────────────┘ │
│           │                                                  │
│  ┌────────┴────────────────────────────┐                   │
│  │   LongTermMemoryManager             │                   │
│  │   (Long-term Memory Management)     │                   │
│  │   ┌─────────────┐  ┌──────────────┐│                   │
│  │   │Short Memory │  │Knowledge     ││                   │
│  │   │Management   │  │Extraction    ││                   │
│  │   └─────────────┘  └──────────────┘│                   │
│  └────────┬────────────────────────────┘                   │
│           │                                                  │
│  ┌────────┴────────┐                                        │
│  │  KnowledgeBase  │                                        │
│  │  (Knowledge Mgmt)│                                       │
│  └────────┬────────┘                                        │
└───────────┼─────────────────────────────────────────────────┘
            │
┌───────────┴─────────────────────────────────────────────────┐
│                    Data Persistence Layer                    │
│                  DatabaseManager                            │
│                                                              │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  │
│  │Short-term│  │Long-term │  │Knowledge │  │Base      │  │
│  │Memory    │  │Memory    │  │Base      │  │Knowledge │  │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘  │
│                                                              │
│                    SQLite Database                          │
│                   (chat_agent.db)                           │
└─────────────────────────────────────────────────────────────┘
            │
┌───────────┴─────────────────────────────────────────────────┐
│                    External Services Layer                   │
│                                                              │
│  ┌──────────────┐              ┌──────────────┐           │
│  │ LLM API      │              │ Debug Logger │           │
│  │ (SiliconFlow)│              │ (Logging)    │           │
│  └──────────────┘              └──────────────┘           │
└─────────────────────────────────────────────────────────────┘
```

## 🧩 Module Architecture

### 1. Data Persistence Layer (DatabaseManager)

#### Responsibilities
- Unified management of all data CRUD operations
- Transaction support and error recovery
- Data migration and version management

#### Database Schema Design

##### short_term_memory Table
```sql
CREATE TABLE short_term_memory (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    role TEXT NOT NULL,           -- 'user' or 'assistant'
    content TEXT NOT NULL,        -- Message content
    timestamp TEXT NOT NULL       -- ISO format timestamp
);
```

##### long_term_memory Table
```sql
CREATE TABLE long_term_memory (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    summary TEXT NOT NULL,        -- Summary content
    conversation_count INTEGER,   -- Conversation rounds
    start_time TEXT,             -- Start time
    end_time TEXT,               -- End time
    created_at TEXT              -- Creation time
);
```

##### entities Table
```sql
CREATE TABLE entities (
    uuid TEXT PRIMARY KEY,        -- Unique identifier
    name TEXT NOT NULL,          -- Entity name
    normalized_name TEXT NOT NULL, -- Normalized name (for search)
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX idx_entity_name ON entities(normalized_name);
```

##### entity_definitions Table
```sql
CREATE TABLE entity_definitions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_uuid TEXT NOT NULL,   -- Associated entity
    content TEXT NOT NULL,       -- Definition content
    type TEXT DEFAULT 'definition', -- Definition type
    source TEXT,                 -- Source
    confidence REAL DEFAULT 1.0, -- Confidence (0-1)
    priority INTEGER DEFAULT 50, -- Priority
    created_at TEXT NOT NULL,
    FOREIGN KEY (entity_uuid) REFERENCES entities(uuid)
);
```

##### base_knowledge Table
```sql
CREATE TABLE base_knowledge (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_name TEXT UNIQUE NOT NULL,
    normalized_name TEXT NOT NULL,
    content TEXT NOT NULL,
    category TEXT DEFAULT 'General',
    immutable INTEGER DEFAULT 1,  -- Whether immutable
    priority INTEGER DEFAULT 100, -- Priority
    confidence REAL DEFAULT 1.0,
    created_at TEXT NOT NULL
);
```

#### Design Highlights

1. **Context Manager Pattern**
   ```python
   @contextmanager
   def get_connection(self):
       conn = sqlite3.connect(self.db_path)
       try:
           yield conn
           conn.commit()
       except Exception as e:
           conn.rollback()
           raise e
       finally:
           conn.close()
   ```

2. **Data Migration Support**
   - Auto-detect old JSON files
   - Migrate data to database
   - Backup original files

3. **Query Optimization**
   - Use indexes to accelerate searches
   - Batch operations to reduce I/O
   - Connection pool management

### 2. Memory Management Layer

#### Short-term Memory (MemoryManager)

**Features**:
- Saves detailed conversation history
- Limits quantity to avoid memory overflow
- Fast access to recent conversations

**Implementation**:
```python
class MemoryManager:
    def __init__(self, memory_file: str = None):
        self.max_messages = 50
        self.messages = []
    
    def add_message(self, role: str, content: str):
        self.messages.append({
            'role': role,
            'content': content,
            'timestamp': datetime.now().isoformat()
        })
        
        # Limit quantity
        if len(self.messages) > self.max_messages:
            self.messages = self.messages[-self.max_messages:]
```

#### Long-term Memory (LongTermMemoryManager)

**Features**:
- Hierarchical memory architecture
- Automatic summary generation
- Periodic knowledge extraction

**Memory Conversion Flow**:
```
Short-term memory full (20 rounds)
    ↓
Call LLM to generate summary
    ↓
Save to long-term memory table
    ↓
Clean old short-term memory
    ↓
Trigger knowledge extraction (every 5 rounds)
```

**Summary Prompt Template**:
```python
prompt = f"""
Please summarize the following conversation:

{conversations}

Requirements:
1. Extract key information and important content
2. Preserve emotional tendencies and relationship changes
3. Summary should not exceed 200 words
"""
```

### 3. Knowledge Management Layer (KnowledgeBase)

#### Knowledge Extraction Flow

```
Conversation Content
    ↓
LLM Identifies Entities
    ↓
Extract Definitions and Relations
    ↓
Entity Normalization
    │
    ├─ Name Standardization (lowercase, remove spaces)
    ├─ Synonym Merging
    └─ Disambiguation
    ↓
Store to Database
    │
    ├─ entities table
    ├─ entity_definitions table
    └─ entity_related_info table
```

#### Knowledge Retrieval Algorithm

```python
def search_knowledge(self, query: str, limit: int = 5):
    # 1. Normalize query
    normalized_query = normalize_text(query)
    
    # 2. Fuzzy match entities
    entities = self.db.search_entities(normalized_query, limit)
    
    # 3. Sort by priority and confidence
    entities.sort(key=lambda x: (
        -x['priority'],
        -x['confidence']
    ))
    
    # 4. Load related information
    for entity in entities:
        entity['definitions'] = self.db.get_entity_definitions(
            entity['uuid']
        )
    
    return entities
```

#### Normalization Algorithm

```python
def normalize_text(text: str) -> str:
    # 1. Convert to lowercase
    text = text.lower()
    
    # 2. Remove extra spaces
    text = ' '.join(text.split())
    
    # 3. Remove punctuation (preserve Chinese)
    text = re.sub(r'[^\w\s\u4e00-\u9fff]', '', text)
    
    return text.strip()
```

### 4. Dialogue Agent Layer (ChatAgent)

#### Prompt Building Strategy

```python
def build_prompt(self, user_input: str) -> List[Dict]:
    messages = []
    
    # 1. System prompt (character setting)
    messages.append({
        'role': 'system',
        'content': self.get_character_prompt()
    })
    
    # 2. Base knowledge
    base_knowledge = self.get_base_knowledge()
    if base_knowledge:
        messages.append({
            'role': 'system',
            'content': f"Base Knowledge:\n{base_knowledge}"
        })
    
    # 3. Long-term memory summaries
    long_term = self.memory_manager.get_long_term_summaries(3)
    if long_term:
        messages.append({
            'role': 'system',
            'content': f"Historical Summary:\n{long_term}"
        })
    
    # 4. Relevant knowledge
    knowledge = self.knowledge_base.search_knowledge(user_input)
    if knowledge:
        messages.append({
            'role': 'system',
            'content': f"Relevant Knowledge:\n{knowledge}"
        })
    
    # 5. Short-term memory (recent conversation)
    short_term = self.memory_manager.get_short_term_messages(10)
    messages.extend(short_term)
    
    # 6. Current user input
    messages.append({
        'role': 'user',
        'content': user_input
    })
    
    return messages
```

#### API Call Encapsulation

```python
def call_llm_api(self, messages: List[Dict]) -> str:
    try:
        response = requests.post(
            self.api_url,
            headers={
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json'
            },
            json={
                'model': self.model_name,
                'messages': messages,
                'temperature': self.temperature,
                'max_tokens': self.max_tokens
            },
            timeout=30
        )
        
        response.raise_for_status()
        result = response.json()
        
        return result['choices'][0]['message']['content']
        
    except requests.exceptions.RequestException as e:
        raise ConnectionError(f"API call failed: {e}")
```

### 5. Emotion Analysis Layer (EmotionRelationshipAnalyzer)

#### Five-Dimensional Model

```python
DIMENSIONS = {
    'intimacy': {
        'name': 'Intimacy',
        'description': 'Degree of relationship closeness',
        'indicators': [
            'Form of address',
            'Topic depth',
            'Personal information sharing'
        ]
    },
    'trust': {
        'name': 'Trust',
        'description': 'Level of mutual trust',
        'indicators': [
            'Help-seeking frequency',
            'Advice acceptance',
            'Privacy disclosure'
        ]
    },
    'joy': {
        'name': 'Joy',
        'description': 'Happiness in communication',
        'indicators': [
            'Emotional word usage',
            'Emoji usage',
            'Conversation positivity'
        ]
    },
    'empathy': {
        'name': 'Empathy',
        'description': 'Emotional resonance level',
        'indicators': [
            'Emotional understanding',
            'Opinion agreement',
            'Experience similarity'
        ]
    },
    'dependence': {
        'name': 'Dependence',
        'description': 'Mutual dependency level',
        'indicators': [
            'Consultation frequency',
            'Expectation level',
            'Separation anxiety'
        ]
    }
}
```

#### Analysis Prompt

```python
analysis_prompt = f"""
Please analyze the emotional relationship in the following conversation, 
rating five dimensions (0-100):

Conversation:
{conversations}

Rating Dimensions:
1. Intimacy: Degree of relationship closeness
2. Trust: Level of mutual trust
3. Joy: Happiness in communication
4. Empathy: Emotional resonance level
5. Dependence: Mutual dependency level

Please return in JSON format:
{{
    "intimacy": score,
    "trust": score,
    "joy": score,
    "empathy": score,
    "dependence": score,
    "analysis": "analysis description"
}}
"""
```

### 6. Vision Simulation Layer (AgentVisionTool)

#### Pseudo-Vision Implementation

Since LLMs don't have native vision capability, simulate through environment descriptions:

```python
class AgentVisionTool:
    def set_environment(self, description: str):
        """Set current environment description"""
        self.db.set_environment_description(description)
    
    def get_visual_context(self) -> str:
        """Get visual context for prompt"""
        env = self.db.get_current_environment()
        if env:
            return f"Current Environment: {env['description']}"
        return ""
```

## 🔄 Data Flow Design

### Complete Conversation Flow

```
1. User Input
   ↓
2. ChatAgent.chat()
   ↓
3. Build Prompt
   ├─ Character setting
   ├─ Base knowledge
   ├─ Long-term memory summary
   ├─ Relevant knowledge retrieval
   ├─ Short-term memory
   └─ Current input
   ↓
4. Call LLM API
   ↓
5. Get Response
   ↓
6. Update Memory
   ├─ Add to short-term memory
   ├─ Check if summarization needed
   └─ Check if knowledge extraction needed
   ↓
7. Return result to user
```

### Memory Conversion Flow

```
Short-term Memory Monitoring
   ↓
Message count > 40?
   ├─ No → Continue accumulating
   └─ Yes ↓
      Call LLM to generate summary
         ↓
      Save to long-term memory table
         ↓
      Delete old short-term memory (keep recent 20)
         ↓
      Trigger knowledge extraction
         ↓
      Complete
```

### Knowledge Extraction Flow

```
Conversation rounds % 5 == 0?
   ├─ No → Skip
   └─ Yes ↓
      Get recent N rounds
         ↓
      Call LLM to identify entities
         ↓
      Parse JSON result
         ↓
      For each entity:
         ├─ Normalize name
         ├─ Check if exists
         ├─ Merge or create entity
         └─ Save definitions and relations
         ↓
      Complete
```

## 🎨 UI Architecture

### GUI Component Hierarchy

```
ChatGUI (Tk Main Window)
├── Left Frame
│   ├── Title Bar (Label)
│   ├── Chat Display (ScrolledText)
│   ├── Input Box (Entry)
│   └── Button Group (Frame)
│       ├── Send Button
│       ├── Clear Memory Button
│       ├── Analyze Emotion Button
│       ├── Database Manager Button
│       └── Debug Log Button
│
├── Right Frame
│   ├── Emotion Radar (EmotionRadarCanvas)
│   ├── Timeline Chart (TimelineCanvas)
│   └── Statistics (Frame)
│
└── Popup Windows
    ├── DatabaseGUI (Toplevel)
    │   └── Database management interface
    └── DebugLogViewer (Toplevel)
        └── Debug log viewer
```

### Event-Driven Model

```python
class ChatGUI:
    def __init__(self):
        self.setup_ui()
        self.bind_events()
    
    def bind_events(self):
        # Keyboard events
        self.input_entry.bind('<Return>', self.on_send)
        self.input_entry.bind('<Shift-Return>', self.on_newline)
        
        # Button events
        self.send_btn.config(command=self.on_send)
        self.clear_btn.config(command=self.on_clear_memory)
        
        # Window events
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
```

## 🔧 Extension Mechanism

### Plugin Architecture (Future)

```python
class Plugin:
    """Plugin base class"""
    def __init__(self, agent: ChatAgent):
        self.agent = agent
    
    def on_message(self, role: str, content: str):
        """Message hook"""
        pass
    
    def on_response(self, response: str):
        """Response hook"""
        pass

class TranslationPlugin(Plugin):
    """Translation plugin example"""
    def on_response(self, response: str):
        # Auto-translate response
        translated = self.translate(response)
        return translated
```

### API Provider Extension

```python
class LLMProvider:
    """LLM provider base class"""
    def call_api(self, messages: List[Dict]) -> str:
        raise NotImplementedError

class OpenAIProvider(LLMProvider):
    """OpenAI implementation"""
    def call_api(self, messages: List[Dict]) -> str:
        # OpenAI specific implementation
        pass

class SiliconFlowProvider(LLMProvider):
    """SiliconFlow implementation"""
    def call_api(self, messages: List[Dict]) -> str:
        # SiliconFlow specific implementation
        pass
```

## 🚀 Performance Optimization

### Database Optimization

1. **Index Strategy**
   ```sql
   CREATE INDEX idx_entity_name ON entities(normalized_name);
   CREATE INDEX idx_message_timestamp ON short_term_memory(timestamp);
   ```

2. **Query Optimization**
   ```python
   # Use LIMIT to restrict results
   SELECT * FROM entities WHERE ... LIMIT 10;
   
   # Avoid SELECT *
   SELECT uuid, name, normalized_name FROM entities;
   ```

3. **Batch Operations**
   ```python
   cursor.executemany(
       'INSERT INTO messages (role, content) VALUES (?, ?)',
       messages
   )
   ```

### Memory Optimization

1. **Limit Short-term Memory Size**
   ```python
   MAX_SHORT_TERM_MESSAGES = 40  # 20 conversation rounds
   ```

2. **Periodic Cleanup**
   ```python
   if len(messages) > MAX_MESSAGES:
       messages = messages[-MAX_MESSAGES:]
   ```

3. **Lazy Loading**
   ```python
   # Only load long-term memory when needed
   def get_long_term_memory(self):
       if not self._long_term_cache:
           self._long_term_cache = self.db.get_long_term_summaries()
       return self._long_term_cache
   ```

## 🔒 Security Design

### Data Privacy

1. **Local Storage**: All data stored in local database
2. **No Cloud Sync**: No cloud sync by default
3. **API Key Protection**: Use environment variables, don't commit to codebase

### Input Validation

```python
def validate_input(user_input: str) -> bool:
    # 1. Length limit
    if len(user_input) > 10000:
        raise ValueError("Input too long")
    
    # 2. Content check
    if contains_malicious_content(user_input):
        raise ValueError("Contains illegal content")
    
    return True
```

### SQL Injection Protection

```python
# Use parameterized queries
cursor.execute(
    'SELECT * FROM entities WHERE name = ?',
    (entity_name,)
)

# Don't use string concatenation
# Wrong example:
# cursor.execute(f'SELECT * FROM entities WHERE name = "{name}"')
```

## 📊 Monitoring and Logging

### Debug Logger Design

```python
class DebugLogger:
    def log_api_call(self, endpoint, request, response, duration):
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'type': 'api_call',
            'endpoint': endpoint,
            'request_size': len(json.dumps(request)),
            'response_size': len(json.dumps(response)),
            'duration': duration
        }
        self._write_log(log_entry)
    
    def log_prompt(self, prompt, context):
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'type': 'prompt',
            'content': prompt,
            'context': context
        }
        self._write_log(log_entry)
```

## 🔮 Future Extensions

### Planned Features

1. **Multimodal Support**
   - Image input and understanding
   - Voice conversation
   - Video analysis

2. **Distributed Deployment**
   - Multi-user support
   - Cloud synchronization
   - Collaborative conversation

3. **Advanced Knowledge Management**
   - Knowledge graph visualization
   - Automatic reasoning
   - Knowledge conflict detection

4. **Plugin System**
   - Third-party plugin support
   - Plugin marketplace
   - Hot reload

## 📚 References

- [LangChain Architecture](https://python.langchain.com/docs/get_started/introduction)
- [SQLite Design Principles](https://www.sqlite.org/arch.html)
- [Tkinter Best Practices](https://tkdocs.com/tutorial/index.html)
- [Software Architecture Patterns](https://www.oreilly.com/library/view/software-architecture-patterns/9781491971437/)

---

This document is continuously updated...

Last updated: 2024-01-01
