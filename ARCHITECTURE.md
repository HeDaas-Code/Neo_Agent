# Neo Agent 复合框架架构文档

## 概述

Neo Agent已从单一的LangChain框架升级为复合框架架构，引入LangChain、LangGraph、DeepAgents和多层模型系统，实现更智能、更高效的对话代理。

## 架构组成

### 1. LangChain核心

LangChain作为核心框架，提供：
- LLM抽象和统一接口
- 消息格式转换
- 链式调用支持
- 模板和输出解析

### 2. LangGraph状态管理

LangGraph用于管理复杂对话流程：
- 状态图定义和编译
- 节点和边的管理
- 条件分支支持
- 持久化状态管理（MemorySaver）
- 流程可视化（未来计划）

**当前实现**：
- `conversation_graph.py`：定义了基础的对话流程框架
- 节点包括：理解、知识检索、视觉检查、日程检查、NPS工具、生成回复、情感分析
- 支持条件边，根据状态决定是否进行情感分析
- `dynamic_multi_agent_graph.py`：动态多智能体协作图，支持持久化状态

**未来计划**：
- 完全集成到ChatAgent的chat方法
- 添加更多复杂的流程节点
- 实现流程可视化

### 3. DeepAgents增强

DeepAgents库提供高级功能（[详细文档](docs/DEEPAGENTS_INTEGRATION.md)）：
- **子智能体生成**: 自动获得todo list、文件系统等工具
- **状态持久化**: MemorySaver实现跨会话状态管理
- **长期记忆**: AGENTS.md文件系统
- **虚拟文件系统**: 处理大型工具结果
- **任务规划**: 内置write_todos工具

**核心模块**：
- `deepagents_wrapper.py`: DeepSubAgentWrapper, DeepAgentsKnowledgeManager
- `enhanced_knowledge_base.py`: EnhancedKnowledgeBase

**向后兼容**：
- 通过工厂函数和环境变量控制
- 失败时自动降级到传统模式

### 4. 多层模型架构

根据任务类型智能选择合适的模型：

#### 主模型 (deepseek-ai/DeepSeek-V3.2)
- **用途**：处理主要对话和复杂推理
- **特点**：强大的理解和生成能力
- **使用场景**：用户对话、复杂问答、创意生成、任务编排

#### 工具模型 (zai-org/GLM-4.6V)
- **用途**：处理工具级任务
- **特点**：快速响应、成本效益高
- **使用场景**：
  - 情感分析
  - 知识提取
  - 实体识别
  - 子智能体任务
  - 意图识别

#### 多模态模型 (Qwen/Qwen3-VL-32B-Instruct)
- **用途**：处理多模态识别和推理
- **特点**：支持视觉理解
- **使用场景**：环境感知、图像理解（预留）

### 5. 记忆系统（集成MemU）

Neo Agent采用分层记忆架构，并集成了MemU框架用于高效记忆管理：

#### 记忆层次
1. **短期记忆**：保留最近20轮对话的详细内容
2. **长期记忆**：自动归档的对话概括（使用MemU或LLM总结）
3. **知识库**：从对话中提取的结构化知识
4. **基础知识**：不可变的核心知识

#### MemU集成
- **项目**: [MemU](https://github.com/NevaMind-AI/memU) - 24/7主动智能体的记忆框架
- **优势**:
  - 大幅降低长期运行的token成本
  - 持续捕获和理解用户意图
  - 更高效的记忆总结和检索
- **配置**:
  ```bash
  # 启用MemU（默认启用）
  USE_MEMU=true
  # MemU使用的API密钥
  OPENAI_API_KEY=your-openai-key
  # MemU使用的模型（默认gpt-4o-mini）
  MEMU_MODEL_NAME=gpt-4o-mini
  ```
- **回退机制**: 当MemU未配置或失败时，自动回退到传统LLM总结方式
- **实现**: `src/core/memu_memory_adapter.py` 和 `src/core/long_term_memory.py`

#### 记忆管理器
```python
from src.core.long_term_memory import LongTermMemoryManager

# 初始化（自动检测MemU可用性）
ltm = LongTermMemoryManager()

# 添加消息
ltm.add_message('user', '你好')
ltm.add_message('assistant', '你好！')

# 自动功能：
# - 每20轮自动归档为长期记忆
# - 每5轮自动提取知识点
# - 使用MemU进行高效总结（如果可用）
```

## 核心组件

### ModelConfig (model_config.py)

管理多层模型配置：

```python
from src.core.model_config import ModelType, get_model_config

# 获取配置
config = get_model_config()

# 获取特定模型配置
main_config = config.get_model_config(ModelType.MAIN)
tool_config = config.get_model_config(ModelType.TOOL)
vision_config = config.get_model_config(ModelType.VISION)
```

### LangChainLLM (langchain_llm.py)

封装LangChain的ChatOpenAI，支持SiliconFlow API：

```python
from src.core.langchain_llm import LangChainLLM, ModelType

# 创建不同类型的LLM实例
main_llm = LangChainLLM(ModelType.MAIN)
tool_llm = LangChainLLM(ModelType.TOOL)
vision_llm = LangChainLLM(ModelType.VISION)

# 调用LLM
response = tool_llm.chat(messages)
```

### ModelRouter (langchain_llm.py)

智能路由到合适的模型：

```python
from src.core.langchain_llm import ModelRouter

router = ModelRouter()

# 根据任务类型路由
main_llm = router.route('main')
tool_llm = router.route('tool')
vision_llm = router.route('vision')
```

### LLMHelper (llm_helper.py)

简化工具级任务的LLM调用：

```python
from src.core.llm_helper import LLMHelper

# 调用工具模型
response = LLMHelper.call_tool_model(
    system_prompt="你是一个情感分析专家",
    user_message="分析这段对话的情感",
    temperature=0.3,
    max_tokens=1000
)

# 调用主模型
response = LLMHelper.call_main_model(
    system_prompt="你是一个智能助手",
    user_message="帮我写一篇文章"
)
```

### ConversationGraph (conversation_graph.py)

使用LangGraph管理对话流程：

```python
from src.core.conversation_graph import ConversationGraph

# 创建对话流程图（需要chat_agent实例）
graph = ConversationGraph(chat_agent)

# 处理对话
final_state = graph.process(user_input, messages)
```

## 兼容性设计

为保持向后兼容，所有更改都采用了兼容层设计：

### SiliconFlowLLM兼容层

`SiliconFlowLLM`类保持原有接口，但内部使用新的LangChain架构：

```python
# 原有代码仍然工作
from src.core.chat_agent import SiliconFlowLLM

llm = SiliconFlowLLM()
response = llm.chat(messages)

# 新功能：支持任务类型参数
response = llm.chat(messages, task_type='tool')  # 使用工具模型
```

### 模块更新

以下模块已更新为使用新架构：

1. **chat_agent.py**: SiliconFlowLLM作为兼容层
2. **multi_agent_coordinator.py**: SubAgent使用工具模型
3. **emotion_analyzer.py**: 使用LLMHelper调用工具模型
4. **knowledge_base.py**: 使用LLMHelper进行知识提取
5. **其他工具模块**: 保持原有接口，内部使用新架构

## 配置说明

### 环境变量

在`.env`文件中配置：

```bash
# API配置
SILICONFLOW_API_KEY=your-api-key
SILICONFLOW_API_URL=https://api.siliconflow.cn/v1/chat/completions

# 主模型配置
MAIN_MODEL_NAME=deepseek-ai/DeepSeek-V3.2
MAIN_MODEL_TEMPERATURE=0.8
MAIN_MODEL_MAX_TOKENS=2000

# 工具模型配置
TOOL_MODEL_NAME=zai-org/GLM-4.6V
TOOL_MODEL_TEMPERATURE=0.3
TOOL_MODEL_MAX_TOKENS=500

# 多模态模型配置
VISION_MODEL_NAME=Qwen/Qwen3-VL-32B-Instruct
VISION_MODEL_TEMPERATURE=0.5
VISION_MODEL_MAX_TOKENS=1000

# MemU记忆管理配置
USE_MEMU=true
OPENAI_API_KEY=your-openai-key  # MemU使用
MEMU_MODEL_NAME=gpt-4o-mini

# 兼容旧配置
MODEL_NAME=deepseek-ai/DeepSeek-V3
TEMPERATURE=0.8
MAX_TOKENS=2000
```

## 使用指南

### 选择合适的模型

- **主模型**：用户直接交互、需要高质量回复
- **工具模型**：内部处理、轻量级任务、成本敏感场景
- **多模态模型**：涉及图像或视觉理解的任务

### 迁移指南

如果您有自定义代码使用了原有的API调用方式，建议：

1. 使用`LLMHelper`简化调用
2. 根据任务类型选择合适的模型
3. 保持原有接口不变，只更新内部实现

## 性能优化

多层模型架构带来的优势：

1. **成本优化**：轻量级任务使用小模型，降低API成本
2. **响应速度**：小模型响应更快，提升用户体验
3. **质量保证**：主要对话使用大模型，保证质量
4. **灵活扩展**：易于添加新的模型类型

## 未来计划

1. **完全集成LangGraph**：将对话流程完全迁移到LangGraph
2. **深度集成deepagents**：探索更高级的智能体协作模式
3. **流程可视化**：实现对话流程的可视化展示
4. **性能监控**：添加模型使用统计和性能分析
5. **动态路由**：根据任务复杂度动态选择模型
6. **MemU深度集成**：探索MemU的更多高级功能，如主动记忆检索

## 参考资料

- [LangChain文档](https://docs.langchain.com/)
- [LangGraph文档](https://langchain-ai.github.io/langgraph/)
- [DeepAgents文档](https://github.com/aiwaves-cn/agents)
- [MemU项目](https://github.com/NevaMind-AI/memU)
- [SiliconFlow API](https://siliconflow.cn/)
