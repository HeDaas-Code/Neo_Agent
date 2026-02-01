# Neo Agent - 智能对话代理系统

[English](#english) | [简体中文](#中文)

---

## 中文

### 简介

Neo Agent 是一个基于 LangChain 的智能对话代理系统，具备角色扮演、长效记忆管理、情感关系分析和智能日程管理功能。

### 主要特性

- 🧠 **分层记忆系统**: 短期记忆、长期记忆、知识库、基础知识
- 💭 **智能对话**: 角色扮演、连续对话、记忆检索、情感理解
- 📊 **情感分析**: 印象评估、累计评分、关系可视化
- 🖥️ **现代化GUI**: 基于Tkinter的友好界面
- 📅 **事件驱动**: 通知事件、任务事件、日程管理
- 🗄️ **数据管理**: SQLite存储、数据迁移、备份恢复

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
├── tests/                 # 测试文件
├── examples/              # 示例代码
├── main.py               # 主入口（推荐）
├── run.py                # 简化启动器
├── requirements.txt      # 依赖列表
├── example.env          # 环境变量示例
└── LICENSE              # 许可证
```

### 核心模块

- **chat_agent**: 对话代理核心
- **database_manager**: 统一数据库管理
- **emotion_analyzer**: 情感关系分析
- **event_manager**: 事件驱动系统
- **knowledge_base**: 知识库管理
- **long_term_memory**: 长期记忆系统
- **schedule_manager**: 日程管理

### 许可证

本项目采用 MIT 许可证。详见 [LICENSE](LICENSE) 文件。

---

## English

### Introduction

Neo Agent is a LangChain-based intelligent conversation agent system with role-playing, long-term memory management, emotional relationship analysis, and intelligent schedule management capabilities.

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
