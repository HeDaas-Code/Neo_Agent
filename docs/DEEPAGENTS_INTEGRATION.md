# DeepAgents集成文档

## 概述

本次重构使用[deepagents](https://github.com/langchain-ai/deepagents)库增强Neo Agent的以下功能：

1. **子智能体生成与管理** - 替代传统SubAgent
2. **动态多智能体编排** - 增强DynamicMultiAgentGraph
3. **知识库管理** - 重构KnowledgeBase

## 核心改进

### 1. DeepSubAgentWrapper - 增强的子智能体

**解决的问题：**

- ❌ 每次执行都需要传递完整上下文
- ❌ 没有持久化状态管理
- ❌ 无法处理大型工具结果
- ❌ 缺乏任务规划能力

**解决方案：**

- ✅ 使用MemorySaver实现跨会话状态持久化
- ✅ 使用thread_id管理会话状态
- ✅ 使用FilesystemMiddleware处理大型结果
- ✅ 内置write_todos工具支持任务规划

**使用示例：**

```python
from src.core.deepagents_wrapper import DeepSubAgentWrapper

# 创建增强的子智能体
agent = DeepSubAgentWrapper(
    agent_id='researcher',
    role='研究员',
    description='负责信息研究和分析',
    enable_filesystem=True,  # 启用文件系统
    enable_memory=True       # 启用长期记忆
)

# 执行任务（自动持久化状态）
result = agent.execute_task(
    task_description="研究Python的历史",
    context={'topic': 'Python'},
    thread_id='session_123'  # 跨会话状态管理
)

# 获取持久化状态
state = agent.get_state('session_123')
```

### 2. 动态多智能体协作图增强

**新增功能：**

- ✅ 长期记忆支持（MemorySaver）
- ✅ 跨会话状态管理
- ✅ 持久化checkpointer
- ✅ 向后兼容传统模式

**配置：**

```python
# .env文件
ENABLE_PERSISTENT_STATE=true  # 启用持久化状态管理
```

**代码示例：**

```python
from src.core.dynamic_multi_agent_graph import DynamicMultiAgentGraph

# 创建增强的协作图
graph = DynamicMultiAgentGraph(
    question_tool=question_tool,
    progress_callback=callback,
    enable_persistent_state=True  # 启用持久化
)

# 处理任务（状态会自动持久化）
result = graph.process_task_event(task_event, context)
```

### 3. EnhancedKnowledgeBase - 增强的知识库

**新增功能：**

- ✅ DeepAgents长期记忆系统
- ✅ 虚拟文件系统支持
- ✅ 智能知识提取
- ✅ 结构化知识管理
- ✅ 完全向后兼容

**配置：**

```python
# .env文件
USE_DEEPAGENTS_KNOWLEDGE=true  # 启用DeepAgents知识管理
```

**使用示例：**

```python
from src.core.enhanced_knowledge_base import EnhancedKnowledgeBase

# 创建增强的知识库
kb = EnhancedKnowledgeBase(
    db_manager=db_manager,
    use_deepagents=True  # 启用DeepAgents增强
)

# 智能提取知识
conversation = [
    {"role": "user", "content": "Python是一种编程语言"},
    {"role": "assistant", "content": "是的"}
]
result = kb.extract_knowledge_from_conversation(conversation)

# 智能检索知识
knowledge = kb.get_relevant_knowledge_for_query(
    "Python是什么？",
    use_deepagents=True
)
```

## 兼容性设计

### 工厂函数模式

为了保持向后兼容，所有新功能都通过工厂函数和环境变量控制：

```python
from src.core.multi_agent_coordinator import create_sub_agent

# 根据配置自动选择实现
agent = create_sub_agent(
    agent_id='test',
    role='测试专家',
    description='负责测试'
)
# 返回: DeepSubAgentWrapper或SubAgent（取决于USE_DEEP_AGENTS配置）
```

### 环境变量配置

所有新功能默认启用，但可以通过环境变量关闭：

```bash
# .env文件
USE_DEEP_AGENTS=true              # 使用DeepAgents子智能体（默认true）
ENABLE_PERSISTENT_STATE=true      # 启用持久化状态（默认true）
USE_DEEPAGENTS_KNOWLEDGE=true     # 使用DeepAgents知识管理（默认true）
```

## 架构变化

### 新增模块

1. **src/core/deepagents_wrapper.py**
   - `DeepSubAgentWrapper` - 增强的子智能体
   - `DeepAgentsKnowledgeManager` - DeepAgents知识管理器

2. **src/core/enhanced_knowledge_base.py**
   - `EnhancedKnowledgeBase` - 增强的知识库

### 修改的模块

1. **src/core/multi_agent_coordinator.py**
   - 添加`create_sub_agent()`工厂函数
   - 所有SubAgent创建使用工厂函数

2. **src/core/dynamic_multi_agent_graph.py**
   - 添加MemorySaver支持
   - 添加跨会话状态管理
   - 添加checkpointer配置

## DeepAgents特性

### 内置工具

DeepAgents子智能体自动获得以下工具：

1. **write_todos** - 管理待办事项列表
2. **ls** - 列出目录
3. **read_file** - 读取文件
4. **write_file** - 写入文件
5. **edit_file** - 编辑文件
6. **glob** - 文件模式匹配
7. **grep** - 搜索文件内容
8. **execute** - 执行命令（沙箱环境）

### 状态持久化

使用LangGraph的MemorySaver实现：

- 每个thread_id对应一个独立的会话
- 状态在调用之间自动保存和恢复
- 支持长时间运行的任务

### 长期记忆

通过AGENTS.md文件实现：

- 将重要信息存储为markdown文档
- 自动加载到系统提示词
- 支持多个记忆源

## 测试

### 运行测试

```bash
# 运行DeepAgents集成测试
python -m unittest tests.test_deepagents_integration -v

# 运行增强知识库测试
python -m unittest tests.test_enhanced_knowledge_base -v
```

### 测试覆盖

- ✅ DeepSubAgentWrapper初始化
- ✅ 任务执行
- ✅ 跨会话状态管理
- ✅ 持久化状态获取
- ✅ DeepAgentsKnowledgeManager初始化
- ✅ 知识提取和存储
- ✅ 知识检索
- ✅ EnhancedKnowledgeBase基本功能
- ✅ 向后兼容性

## 性能考虑

### 何时使用DeepAgents

**适合：**
- 需要持久化状态的长时间任务
- 需要处理大型数据的场景
- 需要复杂任务规划的情况
- 需要跨会话保持上下文

**不适合：**
- 简单的一次性任务
- 对性能要求极高的场景
- 不需要状态持久化的场景

### 性能优化建议

1. 对于简单任务，使用传统SubAgent（设置USE_DEEP_AGENTS=false）
2. 合理设置thread_id，避免状态冲突
3. 定期清理不需要的持久化状态
4. 大型知识使用文件系统存储（自动）

## 迁移指南

### 从传统SubAgent迁移

**Before:**
```python
from src.core.multi_agent_coordinator import SubAgent

agent = SubAgent(
    agent_id='test',
    role='测试',
    description='测试描述'
)
```

**After:**
```python
from src.core.multi_agent_coordinator import create_sub_agent

# 自动选择最佳实现
agent = create_sub_agent(
    agent_id='test',
    role='测试',
    description='测试描述'
)

# 或显式使用DeepAgents
from src.core.deepagents_wrapper import DeepSubAgentWrapper

agent = DeepSubAgentWrapper(
    agent_id='test',
    role='测试',
    description='测试描述'
)
```

### 从传统KnowledgeBase迁移

**Before:**
```python
from src.core.knowledge_base import KnowledgeBase

kb = KnowledgeBase(db_manager=db)
```

**After:**
```python
from src.core.enhanced_knowledge_base import EnhancedKnowledgeBase

# 默认使用DeepAgents增强
kb = EnhancedKnowledgeBase(
    db_manager=db,
    use_deepagents=True
)

# 或保持传统模式
kb = EnhancedKnowledgeBase(
    db_manager=db,
    use_deepagents=False
)
```

## 故障排除

### 常见问题

1. **DeepAgents初始化失败**
   - 检查deepagents是否正确安装：`pip install deepagents`
   - 检查API密钥配置
   - 查看debug日志了解详细错误

2. **状态持久化不工作**
   - 确保ENABLE_PERSISTENT_STATE=true
   - 检查thread_id是否正确传递
   - 验证checkpointer是否正确初始化

3. **知识提取失败**
   - 确保USE_DEEPAGENTS_KNOWLEDGE=true
   - 检查LLM模型配置
   - 验证数据库连接

### 降级策略

所有新功能都有自动降级机制：

- DeepSubAgentWrapper失败 → 降级到SubAgent
- DeepAgents知识管理失败 → 降级到传统方法
- 持久化状态失败 → 降级到无状态模式

## 未来计划

- [ ] 添加更多DeepAgents中间件
- [ ] 实现分布式状态存储
- [ ] 优化大规模知识检索
- [ ] 添加知识图谱可视化
- [ ] 支持更多文件系统后端

## 参考资料

- [DeepAgents GitHub](https://github.com/langchain-ai/deepagents)
- [DeepAgents文档](https://docs.langchain.com/oss/python/deepagents/overview)
- [LangGraph文档](https://langchain-ai.github.io/langgraph/)
- [Neo Agent架构文档](./ARCHITECTURE.md)
