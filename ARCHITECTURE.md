# 架构设计文档

[English](ARCHITECTURE_EN.md) | 简体中文

本文档详细描述 Neo Agent 的系统架构、设计理念和技术实现。

## 📐 设计理念

### 核心目标

Neo Agent 的设计围绕以下核心目标展开：

1. **持久化记忆**：实现真正的长效记忆能力，让 AI 能够记住历史对话
2. **知识积累**：从对话中提取和积累知识，形成可检索的知识库
3. **情感理解**：分析和理解对话中的情感关系，提供更人性化的交互
4. **模块化设计**：各模块独立且可扩展，便于维护和升级
5. **数据安全**：本地存储，用户完全掌控自己的数据

### 设计原则

- **单一职责**：每个模块专注于一个特定功能
- **松耦合**：模块间通过明确的接口交互
- **高内聚**：相关功能集中在同一模块内
- **可扩展性**：易于添加新功能和集成新技术
- **性能优先**：优化数据库查询和内存使用

## 🏛️ 系统架构

### 总体架构图

```
┌─────────────────────────────────────────────────────────────┐
│                        用户界面层 (GUI)                       │
│                      gui_enhanced.py                        │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │聊天界面  │  │情感雷达  │  │时间线图  │  │数据管理  │   │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘   │
└───────────────────────────┬─────────────────────────────────┘
                            │
┌───────────────────────────┴─────────────────────────────────┐
│                        业务逻辑层                            │
│                                                              │
│  ┌────────────────┐  ┌────────────────┐  ┌──────────────┐ │
│  │  ChatAgent     │  │  EmotionAnalyzer│ │  VisionTool  │ │
│  │  (对话代理)    │  │  (情感分析)     │ │  (视觉模拟)  │ │
│  └────────┬───────┘  └────────────────┘  └──────────────┘ │
│           │                                                  │
│  ┌────────┴────────────────────────────┐                   │
│  │   LongTermMemoryManager             │                   │
│  │   (长效记忆管理)                    │                   │
│  │   ┌─────────────┐  ┌──────────────┐│                   │
│  │   │短期记忆管理 │  │知识提取触发  ││                   │
│  │   └─────────────┘  └──────────────┘│                   │
│  └────────┬────────────────────────────┘                   │
│           │                                                  │
│  ┌────────┴────────┐                                        │
│  │  KnowledgeBase  │                                        │
│  │  (知识库管理)   │                                        │
│  └────────┬────────┘                                        │
└───────────┼─────────────────────────────────────────────────┘
            │
┌───────────┴─────────────────────────────────────────────────┐
│                      数据持久层                              │
│                  DatabaseManager                            │
│                                                              │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  │
│  │短期记忆  │  │长期记忆  │  │知识库    │  │基础知识  │  │
│  │  表      │  │  表      │  │  表      │  │  表      │  │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘  │
│                                                              │
│                    SQLite Database                          │
│                   (chat_agent.db)                           │
└─────────────────────────────────────────────────────────────┘
            │
┌───────────┴─────────────────────────────────────────────────┐
│                      外部服务层                              │
│                                                              │
│  ┌──────────────┐              ┌──────────────┐           │
│  │ LLM API      │              │ Debug Logger │           │
│  │ (SiliconFlow)│              │ (日志记录)   │           │
│  └──────────────┘              └──────────────┘           │
└─────────────────────────────────────────────────────────────┘
```

## 🧩 模块架构

### 1. 数据持久层（DatabaseManager）

#### 职责
- 统一管理所有数据的 CRUD 操作
- 提供事务支持和错误恢复
- 数据迁移和版本管理

#### 数据表设计

##### short_term_memory（短期记忆表）
```sql
CREATE TABLE short_term_memory (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    role TEXT NOT NULL,           -- 'user' 或 'assistant'
    content TEXT NOT NULL,        -- 消息内容
    timestamp TEXT NOT NULL       -- ISO 格式时间戳
);
```

##### long_term_memory（长期记忆表）
```sql
CREATE TABLE long_term_memory (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    summary TEXT NOT NULL,        -- 概括内容
    conversation_count INTEGER,   -- 对话轮数
    start_time TEXT,             -- 开始时间
    end_time TEXT,               -- 结束时间
    created_at TEXT              -- 创建时间
);
```

##### entities（实体表）
```sql
CREATE TABLE entities (
    uuid TEXT PRIMARY KEY,        -- 唯一标识
    name TEXT NOT NULL,          -- 实体名称
    normalized_name TEXT NOT NULL, -- 归一化名称（用于搜索）
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX idx_entity_name ON entities(normalized_name);
```

##### entity_definitions（实体定义表）
```sql
CREATE TABLE entity_definitions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_uuid TEXT NOT NULL,   -- 关联实体
    content TEXT NOT NULL,       -- 定义内容
    type TEXT DEFAULT '定义',    -- 定义类型
    source TEXT,                 -- 来源
    confidence REAL DEFAULT 1.0, -- 置信度 (0-1)
    priority INTEGER DEFAULT 50, -- 优先级
    created_at TEXT NOT NULL,
    FOREIGN KEY (entity_uuid) REFERENCES entities(uuid)
);
```

##### base_knowledge（基础知识表）
```sql
CREATE TABLE base_knowledge (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_name TEXT UNIQUE NOT NULL,
    normalized_name TEXT NOT NULL,
    content TEXT NOT NULL,
    category TEXT DEFAULT '通用',
    immutable INTEGER DEFAULT 1,  -- 是否不可变
    priority INTEGER DEFAULT 100, -- 优先级
    confidence REAL DEFAULT 1.0,
    created_at TEXT NOT NULL
);
```

#### 设计亮点

1. **上下文管理器模式**
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

2. **数据迁移支持**
   - 自动检测旧的 JSON 文件
   - 迁移数据到数据库
   - 备份原文件

3. **查询优化**
   - 使用索引加速搜索
   - 批量操作减少 I/O
   - 连接池管理

### 2. 记忆管理层

#### 短期记忆（MemoryManager）

**特点**：
- 保存详细的对话历史
- 限制数量避免内存溢出
- 快速访问最近对话

**实现**：
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
        
        # 限制数量
        if len(self.messages) > self.max_messages:
            self.messages = self.messages[-self.max_messages:]
```

#### 长效记忆（LongTermMemoryManager）

**特点**：
- 分层记忆架构
- 自动概括生成
- 定期知识提取

**记忆转换流程**：
```
短期记忆满 (20轮)
    ↓
调用 LLM 生成概括
    ↓
保存到长期记忆表
    ↓
清理旧的短期记忆
    ↓
触发知识提取 (每5轮)
```

**概括提示词模板**：
```python
prompt = f"""
请对以下对话进行概括总结：

{conversations}

要求：
1. 提取关键信息和重要内容
2. 保留情感倾向和关系变化
3. 总结不超过200字
"""
```

### 3. 知识管理层（KnowledgeBase）

#### 知识提取流程

```
对话内容
    ↓
LLM 识别实体
    ↓
提取定义和关系
    ↓
实体归一化
    │
    ├─ 名称标准化 (小写、去空格)
    ├─ 同义词合并
    └─ 消歧处理
    ↓
存储到数据库
    │
    ├─ entities 表
    ├─ entity_definitions 表
    └─ entity_related_info 表
```

#### 知识检索算法

```python
def search_knowledge(self, query: str, limit: int = 5):
    # 1. 归一化查询
    normalized_query = normalize_text(query)
    
    # 2. 模糊匹配实体
    entities = self.db.search_entities(normalized_query, limit)
    
    # 3. 按优先级和置信度排序
    entities.sort(key=lambda x: (
        -x['priority'],
        -x['confidence']
    ))
    
    # 4. 加载相关信息
    for entity in entities:
        entity['definitions'] = self.db.get_entity_definitions(
            entity['uuid']
        )
    
    return entities
```

#### 归一化算法

```python
def normalize_text(text: str) -> str:
    # 1. 转小写
    text = text.lower()
    
    # 2. 去除多余空格
    text = ' '.join(text.split())
    
    # 3. 去除标点符号（保留中文）
    text = re.sub(r'[^\w\s\u4e00-\u9fff]', '', text)
    
    return text.strip()
```

### 4. 对话代理层（ChatAgent）

#### 提示词构建策略

```python
def build_prompt(self, user_input: str) -> List[Dict]:
    messages = []
    
    # 1. 系统提示（角色设定）
    messages.append({
        'role': 'system',
        'content': self.get_character_prompt()
    })
    
    # 2. 基础知识
    base_knowledge = self.get_base_knowledge()
    if base_knowledge:
        messages.append({
            'role': 'system',
            'content': f"基础知识：\n{base_knowledge}"
        })
    
    # 3. 长期记忆概括
    long_term = self.memory_manager.get_long_term_summaries(3)
    if long_term:
        messages.append({
            'role': 'system',
            'content': f"历史概括：\n{long_term}"
        })
    
    # 4. 相关知识
    knowledge = self.knowledge_base.search_knowledge(user_input)
    if knowledge:
        messages.append({
            'role': 'system',
            'content': f"相关知识：\n{knowledge}"
        })
    
    # 5. 短期记忆（最近对话）
    short_term = self.memory_manager.get_short_term_messages(10)
    messages.extend(short_term)
    
    # 6. 当前用户输入
    messages.append({
        'role': 'user',
        'content': user_input
    })
    
    return messages
```

#### API 调用封装

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
        raise ConnectionError(f"API调用失败: {e}")
```

### 5. 情感分析层（EmotionRelationshipAnalyzer）

#### 五维度模型

```python
DIMENSIONS = {
    'intimacy': {
        'name': '亲密度',
        'description': '关系的亲密程度',
        'indicators': [
            '称呼方式',
            '话题深度',
            '个人信息分享'
        ]
    },
    'trust': {
        'name': '信任度',
        'description': '相互信任程度',
        'indicators': [
            '求助频率',
            '建议接受度',
            '隐私透露'
        ]
    },
    'joy': {
        'name': '愉悦度',
        'description': '交流的愉快程度',
        'indicators': [
            '情绪词使用',
            '表情符号',
            '对话积极性'
        ]
    },
    'empathy': {
        'name': '共鸣度',
        'description': '情感共鸣程度',
        'indicators': [
            '情感理解',
            '观点认同',
            '经历相似性'
        ]
    },
    'dependence': {
        'name': '依赖度',
        'description': '相互依赖程度',
        'indicators': [
            '咨询频率',
            '期待程度',
            '离开焦虑'
        ]
    }
}
```

#### 分析提示词

```python
analysis_prompt = f"""
请分析以下对话中的情感关系，从五个维度评分（0-100）：

对话内容：
{conversations}

评分维度：
1. 亲密度 (intimacy): 关系的亲密程度
2. 信任度 (trust): 相互信任程度
3. 愉悦度 (joy): 交流的愉快程度
4. 共鸣度 (empathy): 情感共鸣程度
5. 依赖度 (dependence): 相互依赖程度

请以 JSON 格式返回：
{{
    "intimacy": 分数,
    "trust": 分数,
    "joy": 分数,
    "empathy": 分数,
    "dependence": 分数,
    "analysis": "分析说明"
}}
"""
```

### 6. 视觉模拟层（AgentVisionTool）

#### 伪视觉实现

由于 LLM 本身没有视觉能力，通过环境描述模拟：

```python
class AgentVisionTool:
    def set_environment(self, description: str):
        """设置当前环境描述"""
        self.db.set_environment_description(description)
    
    def get_visual_context(self) -> str:
        """获取视觉上下文用于提示词"""
        env = self.db.get_current_environment()
        if env:
            return f"当前环境：{env['description']}"
        return ""
```

## 🔄 数据流设计

### 完整对话流程

```
1. 用户输入
   ↓
2. ChatAgent.chat()
   ↓
3. 构建提示词
   ├─ 角色设定
   ├─ 基础知识
   ├─ 长期记忆概括
   ├─ 相关知识检索
   ├─ 短期记忆
   └─ 当前输入
   ↓
4. 调用 LLM API
   ↓
5. 获取响应
   ↓
6. 更新记忆
   ├─ 添加到短期记忆
   ├─ 检查是否需要概括
   └─ 检查是否需要提取知识
   ↓
7. 返回结果给用户
```

### 记忆转换流程

```
短期记忆监控
   ↓
消息数 > 40条？
   ├─ 否 → 继续积累
   └─ 是 ↓
      调用 LLM 生成概括
         ↓
      保存到长期记忆表
         ↓
      删除旧的短期记忆（保留最近20条）
         ↓
      触发知识提取
         ↓
      完成
```

### 知识提取流程

```
对话轮数 % 5 == 0？
   ├─ 否 → 跳过
   └─ 是 ↓
      获取最近N轮对话
         ↓
      调用 LLM 识别实体
         ↓
      解析 JSON 结果
         ↓
      For each 实体:
         ├─ 归一化名称
         ├─ 检查是否已存在
         ├─ 合并或创建实体
         └─ 保存定义和关系
         ↓
      完成
```

## 🎨 UI 架构

### GUI 组件层次

```
ChatGUI (Tk 主窗口)
├── 左侧框架 (Frame)
│   ├── 标题栏 (Label)
│   ├── 聊天显示区 (ScrolledText)
│   ├── 输入框 (Entry)
│   └── 按钮组 (Frame)
│       ├── 发送按钮
│       ├── 清除记忆按钮
│       ├── 分析情感按钮
│       ├── 数据库管理按钮
│       └── Debug日志按钮
│
├── 右侧框架 (Frame)
│   ├── 情感雷达图 (EmotionRadarCanvas)
│   ├── 时间线图 (TimelineCanvas)
│   └── 统计信息 (Frame)
│
└── 弹出窗口
    ├── DatabaseGUI (Toplevel)
    │   └── 数据库管理界面
    └── DebugLogViewer (Toplevel)
        └── 调试日志查看器
```

### 事件驱动模型

```python
class ChatGUI:
    def __init__(self):
        self.setup_ui()
        self.bind_events()
    
    def bind_events(self):
        # 键盘事件
        self.input_entry.bind('<Return>', self.on_send)
        self.input_entry.bind('<Shift-Return>', self.on_newline)
        
        # 按钮事件
        self.send_btn.config(command=self.on_send)
        self.clear_btn.config(command=self.on_clear_memory)
        
        # 窗口事件
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
```

## 🔧 扩展机制

### 插件架构（未来）

```python
class Plugin:
    """插件基类"""
    def __init__(self, agent: ChatAgent):
        self.agent = agent
    
    def on_message(self, role: str, content: str):
        """消息钩子"""
        pass
    
    def on_response(self, response: str):
        """响应钩子"""
        pass

class TranslationPlugin(Plugin):
    """翻译插件示例"""
    def on_response(self, response: str):
        # 自动翻译响应
        translated = self.translate(response)
        return translated
```

### API 提供商扩展

```python
class LLMProvider:
    """LLM 提供商基类"""
    def call_api(self, messages: List[Dict]) -> str:
        raise NotImplementedError

class OpenAIProvider(LLMProvider):
    """OpenAI 实现"""
    def call_api(self, messages: List[Dict]) -> str:
        # OpenAI 特定实现
        pass

class SiliconFlowProvider(LLMProvider):
    """SiliconFlow 实现"""
    def call_api(self, messages: List[Dict]) -> str:
        # SiliconFlow 特定实现
        pass
```

## 🚀 性能优化

### 数据库优化

1. **索引策略**
   ```sql
   CREATE INDEX idx_entity_name ON entities(normalized_name);
   CREATE INDEX idx_message_timestamp ON short_term_memory(timestamp);
   ```

2. **查询优化**
   ```python
   # 使用 LIMIT 限制结果
   SELECT * FROM entities WHERE ... LIMIT 10;
   
   # 避免 SELECT *
   SELECT uuid, name, normalized_name FROM entities;
   ```

3. **批量操作**
   ```python
   cursor.executemany(
       'INSERT INTO messages (role, content) VALUES (?, ?)',
       messages
   )
   ```

### 内存优化

1. **限制短期记忆大小**
   ```python
   MAX_SHORT_TERM_MESSAGES = 40  # 20轮对话
   ```

2. **定期清理**
   ```python
   if len(messages) > MAX_MESSAGES:
       messages = messages[-MAX_MESSAGES:]
   ```

3. **延迟加载**
   ```python
   # 只在需要时加载长期记忆
   def get_long_term_memory(self):
       if not self._long_term_cache:
           self._long_term_cache = self.db.get_long_term_summaries()
       return self._long_term_cache
   ```

## 🔒 安全设计

### 数据隐私

1. **本地存储**：所有数据存储在本地数据库
2. **无云同步**：默认不同步到云端
3. **API密钥保护**：使用环境变量，不提交到代码库

### 输入验证

```python
def validate_input(user_input: str) -> bool:
    # 1. 长度限制
    if len(user_input) > 10000:
        raise ValueError("输入过长")
    
    # 2. 内容检查
    if contains_malicious_content(user_input):
        raise ValueError("包含非法内容")
    
    return True
```

### SQL 注入防护

```python
# 使用参数化查询
cursor.execute(
    'SELECT * FROM entities WHERE name = ?',
    (entity_name,)
)

# 不要使用字符串拼接
# 错误示例：
# cursor.execute(f'SELECT * FROM entities WHERE name = "{name}"')
```

## 📊 监控和日志

### Debug Logger 设计

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

## 🔮 未来扩展

### 计划功能

1. **多模态支持**
   - 图片输入和理解
   - 语音对话
   - 视频分析

2. **分布式部署**
   - 支持多用户
   - 云端同步
   - 协作对话

3. **高级知识管理**
   - 知识图谱可视化
   - 自动推理
   - 知识冲突检测

4. **插件系统**
   - 第三方插件支持
   - 插件市场
   - 热加载

## 📚 参考资料

- [LangChain 架构](https://python.langchain.com/docs/get_started/introduction)
- [SQLite 设计原理](https://www.sqlite.org/arch.html)
- [Tkinter 最佳实践](https://tkdocs.com/tutorial/index.html)
- [软件架构模式](https://www.oreilly.com/library/view/software-architecture-patterns/9781491971437/)

---

本文档持续更新中...

最后更新：2024-01-01
