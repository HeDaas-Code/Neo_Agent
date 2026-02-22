# Neo Agent 架构文档

## 概述

Neo Agent 是一个基于 LangChain 的智能对话代理系统，采用多层模型架构，具备角色扮演、长效记忆管理、情感关系分析和智能日程管理功能。

## 架构组成

### 1. LangChain核心

LangChain作为核心框架，提供：
- LLM抽象和统一接口
- 消息格式转换
- 链式调用支持
- 模板和输出解析

### 2. 多层模型架构

根据任务类型智能选择合适的模型：

#### 主模型 (deepseek-ai/DeepSeek-V3.2)
- **用途**：处理主要对话和复杂推理
- **特点**：强大的理解和生成能力
- **使用场景**：用户对话、复杂问答、创意生成

#### 工具模型 (zai-org/GLM-4.6V)
- **用途**：处理工具级任务
- **特点**：快速响应、成本效益高
- **使用场景**：
  - 情感分析
  - 知识提取
  - 实体识别
  - 意图识别

#### 多模态模型 (Qwen/Qwen3-VL-32B-Instruct)
- **用途**：处理多模态识别和推理
- **特点**：支持视觉理解
- **使用场景**：环境感知、图像理解（预留）

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
2. **emotion_analyzer.py**: 使用LLMHelper调用工具模型
3. **knowledge_base.py**: 使用LLMHelper进行知识提取
4. **其他工具模块**: 保持原有接口，内部使用新架构

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

## 参考资料

- [LangChain文档](https://docs.langchain.com/)
- [SiliconFlow API](https://siliconflow.cn/)
