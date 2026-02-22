# Neo Agent - 智能对话代理系统

[English](#english) | [简体中文](#中文)

---

## 中文

### 简介

Neo Agent 是一个基于 LangChain + LangGraph 的智能对话代理系统，采用多层模型架构，具备角色扮演、长效记忆管理、情感关系分析和智能日程管理功能。

### 架构特性

#### 🏗️ 复合框架架构
- **LangChain**: 核心框架，提供LLM抽象和链式调用
- **LangGraph**: 状态图管理，实现复杂对话流程编排和动态多智能体协作
- **DeepAgents**: 子智能体生成、长期记忆和文件系统
- **多层模型架构**: 根据任务类型智能选择模型
  - 主模型 (DeepSeek-V3.2): 处理主要对话、复杂推理和任务编排
  - 工具模型 (GLM-4.6V): 处理工具调用、意图识别等轻量级任务
  - 多模态模型 (Qwen3-VL-32B): 处理多模态识别和推理

### 主要特性

- 🧠 **分层记忆系统**: 短期记忆、长期记忆、知识库、基础知识
- 💭 **智能对话**: 角色扮演、连续对话、记忆检索、情感理解
- 📊 **情感分析**: 印象评估、累计评分、关系可视化
- 🖥️ **现代化GUI**: 基于Tkinter的友好界面
- 📅 **事件驱动**: 通知事件、任务事件、日程管理
- 🗄️ **数据管理**: SQLite存储、数据迁移、备份恢复
- 📝 **提示词工程**: 模块化Markdown提示词、角色扮演、世界观注入
- 🤖 **动态多智能体**: 主模型自主编排、并行协作、智能任务分解
- 🚀 **DeepAgents增强**: 持久化状态、任务规划、大型结果处理、跨会话记忆

### 快速开始

#### 安装依赖

```bash
pip install -r requirements.txt
```

#### 配置环境

```bash
cp example.env .env
# 编辑 .env 文件，填入你的API密钥和配置
```

#### 运行应用

```bash
# 方式1: 使用主入口（推荐）
python main.py

# 方式2: 使用简化启动器（如果遇到导入问题）
python run.py

# 方式3: 如果已安装包
neo-agent
```

**常见问题 / Troubleshooting:**
- 如果遇到导入错误，请确保在项目根目录运行
- 确保已安装所有依赖: `pip install -r requirements.txt`
- Windows用户可能需要使用 `python` 而不是 `python3`

### 项目结构

```
Neo_Agent/
├── src/                    # 源代码
│   ├── core/              # 核心模块
│   ├── gui/               # GUI模块
│   ├── tools/             # 工具模块
│   └── nps/               # NPS工具系统
├── prompts/               # 提示词模板
│   ├── character/         # 角色设定模板
│   ├── system/           # 系统提示词模板
│   ├── task/             # 任务提示词模板
│   └── worldview/        # 世界观设定
├── tests/                 # 测试文件
├── examples/              # 示例代码
├── docs/                  # 文档
├── main.py               # 主入口（推荐）
├── run.py                # 简化启动器
├── requirements.txt      # 依赖列表
├── example.env          # 环境变量示例
└── LICENSE              # 许可证
```

### 核心模块

- **prompt_manager**: 提示词管理，支持Markdown模板加载和渲染
- **dynamic_multi_agent_graph**: 基于LangGraph的动态多智能体协作系统（支持持久化状态）
- **deepagents_wrapper**: DeepAgents集成，提供增强的子智能体和知识管理
- **enhanced_knowledge_base**: 增强的知识库，集成DeepAgents长期记忆和文件系统
- **model_config**: 多层模型配置管理
- **langchain_llm**: LangChain LLM封装，支持模型路由
- **llm_helper**: LLM辅助工具，简化工具级任务调用
- **conversation_graph**: LangGraph对话流程管理（基础框架）
- **chat_agent**: 对话代理核心
- **database_manager**: 统一数据库管理
- **emotion_analyzer**: 情感关系分析（使用工具模型）
- **event_manager**: 事件驱动系统
- **knowledge_base**: 知识库管理（使用工具模型）
- **long_term_memory**: 长期记忆系统
- **schedule_manager**: 日程管理
- **multi_agent_coordinator**: 多智能体协作（支持动态/传统模式，DeepAgents增强）

### 动态多智能体协作

Neo Agent实现了基于LangGraph的动态多智能体协作系统：

- 🤖 **主模型自主编排**: DeepSeek-V3.2分析任务并决定执行策略
- ⚡ **并行执行**: 独立任务同时处理，显著提升效率
- 🔄 **灵活策略**: 支持simple/parallel/sequential三种执行模式
- 📊 **状态管理**: LangGraph提供清晰的状态追踪和流程控制
- 💾 **持久化状态**: DeepAgents MemorySaver实现跨会话状态管理
- 🛡️ **容错设计**: 失败自动降级到传统固定流程

### 提示词系统

Neo Agent采用模块化的提示词工程系统，参考了SillyTavern的设计理念：

- 📝 **Markdown模板**: 所有提示词以Markdown文件存储
- 🎭 **角色扮演**: 详细的角色设定和行为准则
- 🌍 **世界观注入**: 虚拟世界背景和环境设定
- 🔄 **动态渲染**: 支持变量替换和上下文注入
- 🛡️ **后备机制**: 模板失败时自动降级到硬编码提示词

### 许可证

本项目采用 MIT 许可证。详见 [LICENSE](LICENSE) 文件。

---

## English

### Introduction

Neo Agent is a LangChain + LangGraph-based intelligent conversation agent system with multi-tier model architecture, featuring role-playing, long-term memory management, emotional relationship analysis, and intelligent schedule management capabilities.

### Architecture Features

#### 🏗️ Composite Framework Architecture
- **LangChain**: Core framework providing LLM abstraction and chain invocation
- **LangGraph**: State graph management for complex conversation flow orchestration
- **Multi-tier Model Architecture**: Intelligent model selection based on task type
  - Main Model (DeepSeek-V3.2): Handles primary conversations and complex reasoning
  - Tool Model (GLM-4.6V): Handles tool invocations, intent recognition, and lightweight tasks
  - Multimodal Model (Qwen3-VL-32B): Handles multimodal recognition and reasoning

### Key Features

- 🧠 **Hierarchical Memory System**: Short-term memory, long-term memory, knowledge base, base knowledge
- 💭 **Intelligent Conversation**: Role-playing, continuous dialogue, memory retrieval, emotional understanding
- 📊 **Emotion Analysis**: Impression assessment, cumulative scoring, relationship visualization
- 🖥️ **Modern GUI**: User-friendly Tkinter-based interface
- 📅 **Event-Driven**: Notification events, task events, schedule management
- 🗄️ **Data Management**: SQLite storage, data migration, backup and recovery

### Quick Start

#### Install Dependencies

```bash
pip install -r requirements.txt
```

#### Configure Environment

```bash
cp example.env .env
# Edit .env file with your API keys and configuration
```

#### Run Application

```bash
# Method 1: Use main entry point (recommended)
python main.py

# Method 2: Use simplified launcher (if import issues occur)
python run.py

# Method 3: If package is installed
neo-agent
```

**Troubleshooting:**
- If you encounter import errors, ensure you're running from the project root directory
- Make sure all dependencies are installed: `pip install -r requirements.txt`
- Windows users may need to use `python` instead of `python3`

### Project Structure

```
Neo_Agent/
├── src/                    # Source code
│   ├── core/              # Core modules
│   ├── gui/               # GUI modules
│   ├── tools/             # Utility modules
│   └── nps/               # NPS tool system
├── tests/                 # Test files
├── examples/              # Example code
├── main.py               # Main entry point (recommended)
├── run.py                # Simplified launcher
├── requirements.txt      # Dependencies
├── example.env          # Environment variables template
└── LICENSE              # License file
```

### Core Modules

- **chat_agent**: Conversation agent core
- **database_manager**: Unified database management
- **emotion_analyzer**: Emotional relationship analysis
- **event_manager**: Event-driven system
- **knowledge_base**: Knowledge base management
- **long_term_memory**: Long-term memory system
- **schedule_manager**: Schedule management

### License

This project is licensed under the MIT License. See [LICENSE](LICENSE) file for details.
