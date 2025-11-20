# 开发指南

[English](../en/DEVELOPMENT.md) | 简体中文

本文档为开发者提供 Neo Agent 项目的详细开发指南，包括项目结构、开发流程和最佳实践。

## 📁 项目结构

```
Neo_Agent/
├── gui_enhanced.py           # 主GUI界面（3050行）
│   ├── EmotionRadarCanvas    # 情感雷达图组件
│   ├── TimelineCanvas        # 时间线可视化组件
│   ├── DebugLogViewer        # 调试日志查看器
│   └── ChatGUI               # 主聊天界面
│
├── chat_agent.py            # 对话代理核心（809行）
│   ├── MemoryManager         # 记忆管理器（短期）
│   └── ChatAgent             # 主对话代理类
│
├── database_manager.py      # 数据库管理（1706行）
│   └── DatabaseManager       # 统一数据库管理器
│       ├── 短期记忆管理
│       ├── 长期记忆管理
│       ├── 知识库管理
│       ├── 基础知识管理
│       └── 环境描述管理
│
├── long_term_memory.py      # 长效记忆管理（425行）
│   └── LongTermMemoryManager # 长期记忆管理器
│       ├── 短期→长期迁移
│       ├── 记忆概括生成
│       └── 知识提取触发
│
├── knowledge_base.py        # 知识库管理（842行）
│   └── KnowledgeBase         # 知识库管理类
│       ├── 实体识别与提取
│       ├── 知识归一化
│       └── 知识检索
│
├── emotion_analyzer.py      # 情感分析（706行）
│   └── EmotionRelationshipAnalyzer
│       ├── 情感关系分析
│       └── 五维度评估
│
├── agent_vision.py          # 视觉工具（496行）
│   └── AgentVisionTool       # 伪视觉工具
│       ├── 环境描述管理
│       └── 视觉感知模拟
│
├── debug_logger.py          # 调试日志（408行）
│   └── DebugLogger           # 调试日志记录器
│       ├── 提示词记录
│       ├── API调用记录
│       └── 响应记录
│
├── database_gui.py          # 数据库GUI（786行）
│   └── DatabaseGUI           # 数据库管理界面
│       ├── 数据查看
│       ├── 数据编辑
│       └── 导入导出
│
├── base_knowledge.py        # 基础知识管理（263行）
│   └── BaseKnowledgeManager  # 基础知识管理器
│       ├── 加载基础知识
│       └── 更新基础知识
│
├── event_manager.py         # 事件管理（约500行）
│   └── EventManager          # 事件管理器
│       ├── 事件创建与存储
│       ├── 事件状态管理
│       └── 事件日志记录
│
├── multi_agent_coordinator.py  # 多智能体协作（约600行）
│   └── MultiAgentCoordinator   # 多智能体协调器
│       ├── 任务理解
│       ├── 任务规划
│       ├── 任务执行
│       └── 结果验证
│
└── interrupt_question_tool.py  # 中断提问工具（约150行）
    └── InterruptQuestionTool   # 中断性提问工具
        ├── 用户提问
        └── 回调处理
```

## 🏗️ 核心架构

### 1. 数据流架构

```
用户输入
    ↓
ChatAgent（主控制器）
    ↓
记忆检索 ← DatabaseManager → 数据持久化
    ↓
提示词构建
    ↓
LLM API 调用
    ↓
响应处理
    ↓
记忆更新 → LongTermMemoryManager → 知识提取
    ↓
用户显示
```

### 2. 记忆系统架构

```
┌─────────────────────────────────────────┐
│         用户对话输入                     │
└───────────────┬─────────────────────────┘
                ↓
┌───────────────────────────────────────────┐
│         MemoryManager                     │
│    （添加到短期记忆）                     │
└───────────────┬───────────────────────────┘
                ↓
┌───────────────────────────────────────────┐
│    LongTermMemoryManager                  │
│  • 管理短期记忆（最近20轮）               │
│  • 超出后生成概括→长期记忆                │
│  • 每5轮触发知识提取                      │
└───────────────┬───────────────────────────┘
                ↓
        ┌───────┴────────┐
        ↓                ↓
┌───────────────┐  ┌──────────────┐
│  长期记忆概括  │  │  知识库      │
│  (summary)    │  │ (entities)   │
└───────────────┘  └──────────────┘
```

### 3. 知识管理架构

```
对话内容
    ↓
KnowledgeBase.extract_knowledge_from_conversation()
    ↓
LLM 提取实体和关系
    ↓
实体归一化（统一不同表述）
    ↓
存储到数据库
    ├── entities（实体主体）
    ├── entity_definitions（实体定义）
    └── entity_related_info（相关信息）
```

## 🔧 开发环境搭建

### 1. 开发依赖

除了运行依赖外，开发还需要：

```bash
# 代码格式化
pip install black

# 代码检查
pip install pylint flake8

# 类型检查
pip install mypy

# 测试框架
pip install pytest pytest-cov
```

### 2. 推荐的 IDE 配置

#### VS Code

创建 `.vscode/settings.json`：

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

1. 设置 Python 解释器为虚拟环境
2. 启用代码检查和格式化
3. 配置 Black 作为代码格式化工具

## 💻 核心模块详解

### DatabaseManager（数据库管理器）

**职责**：统一管理所有数据的增删改查

**主要方法**：

```python
# 短期记忆
add_short_term_message(role, content)
get_short_term_messages(limit)
clear_short_term_memory()

# 长期记忆
add_long_term_summary(summary, conversation_count, start_time, end_time)
get_long_term_summaries(limit)

# 知识库
add_entity(name)
add_entity_definition(entity_uuid, content, type, source)
search_entities(query_text, limit)

# 基础知识
add_base_knowledge(entity_name, content, category)
get_base_knowledge(entity_name)
```

**设计模式**：
- 上下文管理器（Context Manager）用于数据库连接
- 工厂模式用于创建数据库实例

### LongTermMemoryManager（长效记忆管理器）

**职责**：管理短期和长期记忆的转换

**核心逻辑**：

```python
def add_message(self, role, content):
    # 1. 添加到短期记忆
    self.db.add_short_term_message(role, content)
    
    # 2. 检查是否需要概括
    if message_count > max_short_term_messages:
        # 生成概括并移到长期记忆
        self._summarize_and_archive()
    
    # 3. 检查是否需要提取知识
    if conversation_count % extraction_interval == 0:
        # 触发知识提取
        self.knowledge_base.extract_knowledge()
```

### KnowledgeBase（知识库）

**职责**：从对话中提取和管理知识

**知识提取流程**：

```python
def extract_knowledge_from_conversation(self, messages):
    # 1. 构建提取提示词
    prompt = self._build_extraction_prompt(messages)
    
    # 2. 调用 LLM 提取实体
    entities = self._call_llm_for_extraction(prompt)
    
    # 3. 归一化实体名称
    normalized_entities = self._normalize_entities(entities)
    
    # 4. 存储到数据库
    for entity in normalized_entities:
        self._save_entity(entity)
```

### EmotionRelationshipAnalyzer（情感分析器）

**职责**：分析对话中的情感关系

**分析维度**：
- 亲密度（Intimacy）：关系的亲密程度
- 信任度（Trust）：相互信任程度
- 愉悦度（Joy）：交流的愉快程度
- 共鸣度（Empathy）：情感共鸣程度
- 依赖度（Dependence）：相互依赖程度

### EventManager（事件管理器）

**职责**：管理事件的完整生命周期

**主要方法**：

```python
# 事件管理
create_event(title, description, event_type, priority)
get_event(event_id)
get_pending_events(limit)
update_event_status(event_id, status)
delete_event(event_id)

# 日志管理
add_event_log(event_id, log_type, log_content)
get_event_logs(event_id)

# 统计信息
get_statistics()
```

**设计模式**：
- 工厂模式用于创建不同类型的事件
- 状态模式管理事件生命周期

### MultiAgentCoordinator（多智能体协调器）

**职责**：协调多个智能体完成复杂任务

**核心逻辑**：

```python
def process_task_event(self, task_event):
    # 1. 理解任务
    understanding = self._understand_task(task_event)
    self.emit_progress("任务已理解")
    
    # 2. 制定计划
    plan = self._create_plan(understanding)
    self.emit_progress(f"执行计划已制定，共{len(plan.steps)}步")
    
    # 3. 执行步骤
    results = []
    for i, step in enumerate(plan.steps):
        self.emit_progress(f"正在执行步骤 {i+1}/{len(plan.steps)}")
        result = self._execute_step(step)
        results.append(result)
    
    # 4. 验证结果
    verification = self._verify_results(results, task_event)
    self.emit_progress("✅ 任务验证通过" if verification.passed else "❌ 任务验证失败")
    
    return verification
```

**子智能体类型**：
- 理解智能体：分析任务需求和完成标准
- 规划智能体：将任务分解为可执行步骤
- 执行智能体：逐步完成任务
- 验证智能体：验证任务完成情况

### InterruptQuestionTool（中断性提问工具）

**职责**：在任务执行中向用户提问

**使用示例**：

```python
# 设置回调
tool = InterruptQuestionTool()
tool.set_question_callback(lambda q: input(q))

# 向用户提问
answer = tool.ask_user(
    question="请问您希望周报包含哪些具体内容？",
    context="正在生成周报"
)
```

## 🎨 GUI 开发

### 组件结构

```python
ChatGUI (主窗口)
    ├── 左侧面板
    │   ├── 聊天历史显示区
    │   ├── 输入框
    │   └── 控制按钮
    │
    ├── 右侧面板
    │   ├── EmotionRadarCanvas（情感雷达图）
    │   ├── TimelineCanvas（时间线）
    │   └── 统计信息
    │
    └── 子窗口
        ├── DatabaseGUI（数据库管理）
        └── DebugLogViewer（调试日志）
```

### 自定义 Canvas 组件

创建自定义可视化组件示例：

```python
class CustomCanvas(Canvas):
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self.bind('<Configure>', self.on_resize)
    
    def on_resize(self, event):
        # 响应窗口大小变化
        self.redraw()
    
    def redraw(self):
        # 重绘逻辑
        self.delete('all')
        # ... 绘制内容
```

## 🔌 API 集成

### 添加新的 LLM 提供商

1. 在 `.env` 中添加配置：

```env
NEW_PROVIDER_API_KEY=xxx
NEW_PROVIDER_API_URL=xxx
```

2. 修改 `chat_agent.py` 中的 API 调用：

```python
def call_llm(self, messages):
    provider = os.getenv('LLM_PROVIDER', 'siliconflow')
    
    if provider == 'new_provider':
        return self._call_new_provider(messages)
    else:
        return self._call_default_provider(messages)
```

## 🧪 测试

### 单元测试示例

```python
import pytest
from database_manager import DatabaseManager

def test_add_short_term_message():
    db = DatabaseManager(':memory:')  # 使用内存数据库
    db.add_short_term_message('user', 'Hello')
    
    messages = db.get_short_term_messages()
    assert len(messages) == 1
    assert messages[0]['role'] == 'user'
    assert messages[0]['content'] == 'Hello'
```

### 运行测试

```bash
# 运行所有测试
pytest

# 运行特定测试文件
pytest tests/test_database.py

# 生成覆盖率报告
pytest --cov=. --cov-report=html
```

## 📝 代码规范

### 命名约定

- **类名**：PascalCase（如 `DatabaseManager`）
- **函数名**：snake_case（如 `add_message`）
- **常量**：UPPER_CASE（如 `MAX_TOKENS`）
- **私有方法**：_leading_underscore（如 `_internal_method`）

### 文档字符串

```python
def add_message(self, role: str, content: str) -> None:
    """
    添加消息到记忆中
    
    Args:
        role: 角色类型 ('user' 或 'assistant')
        content: 消息内容
        
    Returns:
        None
        
    Raises:
        ValueError: 如果 role 不是有效值
        
    Example:
        >>> manager.add_message('user', 'Hello')
    """
    pass
```

### 类型提示

```python
from typing import List, Dict, Any, Optional

def get_messages(self, limit: int = 10) -> List[Dict[str, Any]]:
    """获取消息列表"""
    pass

def find_entity(self, name: str) -> Optional[Dict[str, Any]]:
    """查找实体，如果不存在返回 None"""
    pass
```

## 🐛 调试技巧

### 启用详细日志

```python
import logging

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
```

### 使用 Debug Logger

```python
from debug_logger import get_debug_logger

debug_logger = get_debug_logger()
debug_logger.log_info('ModuleName', '操作描述', {'key': 'value'})
```

### 数据库查询调试

```python
db = DatabaseManager(debug=True)  # 启用调试模式
# 将打印所有 SQL 查询
```

## 🔄 开发工作流

### 1. 创建功能分支

```bash
git checkout -b feature/new-feature
```

### 2. 开发和测试

```bash
# 编写代码
# 运行测试
pytest

# 代码格式化
black .

# 代码检查
pylint *.py
```

### 3. 提交代码

```bash
git add .
git commit -m "feat: add new feature"
git push origin feature/new-feature
```

### 4. 创建 Pull Request

在 GitHub 上创建 PR，等待审核。

## 📊 性能优化

### 数据库优化

```python
# 使用索引
cursor.execute('''
    CREATE INDEX IF NOT EXISTS idx_entity_name 
    ON entities(normalized_name)
''')

# 批量插入
cursor.executemany('''
    INSERT INTO messages (role, content) VALUES (?, ?)
''', messages)
```

### 内存优化

```python
# 限制记忆数量
MAX_SHORT_TERM_ROUNDS = 20  # 不要设置太大

# 定期清理
if len(messages) > MAX_MESSAGES:
    messages = messages[-MAX_MESSAGES:]
```

## 🚀 部署

### 打包为可执行文件

使用 PyInstaller：

```bash
pip install pyinstaller

pyinstaller --onefile --windowed gui_enhanced.py
```

### Docker 部署

创建 `Dockerfile`：

```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

CMD ["python", "gui_enhanced.py"]
```

## 🔐 安全注意事项

1. **不要提交 API 密钥**：
   - 使用 `.env` 文件
   - 添加到 `.gitignore`

2. **输入验证**：
   - 验证所有用户输入
   - 防止 SQL 注入

3. **数据加密**：
   - 敏感数据加密存储
   - 使用 HTTPS 通信

## 📚 推荐资源

- [LangChain 文档](https://python.langchain.com/)
- [SQLite 教程](https://www.sqlitetutorial.net/)
- [Tkinter 文档](https://docs.python.org/3/library/tkinter.html)
- [Python 最佳实践](https://docs.python-guide.org/)

## 🤝 贡献指南

1. Fork 项目
2. 创建功能分支
3. 编写代码和测试
4. 提交 Pull Request
5. 等待审核

更多详情请查看 [CONTRIBUTING.md](CONTRIBUTING.md)（待创建）

## 💬 获取帮助

- 提交 [Issue](https://github.com/HeDaas-Code/Neo_Agent/issues)
- 参与 [Discussions](https://github.com/HeDaas-Code/Neo_Agent/discussions)
- 查看现有文档

---

祝开发愉快！🎉
