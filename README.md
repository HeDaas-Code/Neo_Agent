# Neo Agent - 智能对话代理系统

[English](#english) | [简体中文](#中文)

---

## 中文

### 简介

Neo Agent 是一个基于 LangChain + LangGraph 的智能对话代理系统，采用类神经系统多层模型架构，具备角色扮演、长效记忆管理、情感关系分析、智能日程管理以及可观测的统一日志能力。

自 v4.1 起，项目统一了入口与日志体系：`run.py` 成为唯一主入口，`UnifiedLogger` 贯通前后端日志，前端 console 日志可通过 WebSocket 实时回流到后端集中存储与分析。

---

### 架构总览

```
┌─────────────────────────────────────────────────────────────┐
│                         入口层                                │
│   run.py  (web / stop / status / logs)   ←  统一 CLI 入口    │
│   main.py  ──────────────────────────────→ run.py 兼容层     │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────┴───────────────────────────────┐
│                       Web 服务层                             │
│  FastAPI + Uvicorn                                            │
│  ├── REST API  (/api/*)                                       │
│  ├── WebSocket (/ws/chat, /ws/events, /ws/debug,             │
│  │              /ws/proactive, /ws/frontend-logs)             │
│  └── 静态前端 (React + Vite + Ant Design)                     │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────┴───────────────────────────────┐
│                    神经系统 (Nervous System)                 │
│  CentralRouter ── Packet ── Gateway                          │
│  跨模块工作流：对话 → 情感分析 → 日程创建 → 主动确认         │
└─────────────────────────────────────────────────────────────┘
                              │
┌──────────┬──────────┬───────────────┬──────────┬────────────┐
│ 大脑皮层  │  边缘系统 │    前额叶     │  小脑    │  下丘脑     │
│ cortex/  │ limbic/  │ prefrontal/   │cerebellum│hypothalamus│
│ LLMCore  │ 海马体    │ 日程 / 事件   │ NPS 工具 │ 生命状态   │
│ ModelRouter│ 杏仁核  │ 主动决策      │ 视觉 / 风格│ 用户习惯  │
└──────────┴──────────┴───────────────┴──────────┴────────────┘
                              │
┌─────────────────────────────┴───────────────────────────────┐
│                    统一日志基础设施                          │
│  UnifiedLogger  ←  FileHandler / MemoryBufferHandler         │
│                 ← WebSocketBroadcastHandler                   │
│                 ← ExternalForwarderHandler                    │
│  DebugLogger（旧 API 兼容层） ←  委托 UnifiedLogger           │
└─────────────────────────────────────────────────────────────┘
```

---

### 架构特性

#### 🏗️ 复合框架架构
- **LangChain / LangGraph**: 核心框架，提供 LLM 抽象、链式调用与 Agent 编排
- **多层模型架构**: 根据任务类型智能选择模型
  - 主模型：处理主要对话、复杂推理
  - 工具模型：处理工具调用、意图识别等轻量级任务
  - 多模态模型：处理多模态识别和推理

#### 🧠 类神经系统分层
- **nervous_system**: 中央路由 `CentralRouter` + `Packet` 协议 + `Gateway` 网关，实现跨模块流式调用
- **cortex**: 大脑皮层，LLM 推理核心（`LLMCore`、`ModelRouter`、流式响应）
- **limbic**: 边缘系统，海马体记忆 + 杏仁核情感
- **prefrontal**: 前额叶，日程 / 事件 / 主动决策
- **cerebellum**: 小脑，NPS 工具 / 视觉 / 表达风格
- **hypothalamus**: 下丘脑，生命状态 / 用户习惯

#### 📜 统一日志系统（v4.1）
- **格式统一**: timestamp / level / module / message / source / trace_id / extra
- **前后端贯通**: 前端 `logger.ts` 拦截 `console.*`，通过 `/ws/frontend-logs` 实时上报
- **多 Handler 输出**: 文件、内存缓冲、WebSocket 广播、外部转发可扩展
- **向后兼容**: `DebugLogger` 保留原 API，内部委托 `UnifiedLogger`
- **进程管理**: `run.py stop` 基于 PID 文件 + 进程树清理，支持优雅停止与强制兜底

---

### 主要特性

- 🧠 **分层记忆系统**: 短期记忆、长期记忆、知识库、基础知识
- 💭 **智能对话**: 角色扮演、连续对话、记忆检索、情感理解、流式回复
- 📊 **情感分析**: 印象评估、累计评分、关系可视化
- 📅 **日程管理**: 自然语言创建、冲突检测、提醒推送
- 🛠️ **NPS 工具系统**: 可扩展工具注册、调用与编排
- 🖥️ **现代化 Web GUI**: React + TypeScript + Vite + Ant Design
- 🌐 **Web 端独占能力**:
  - **跨设备访问**：任意浏览器打开 `http://<host>:8000` 即可使用
  - **实时 WebSocket 推送**：消息流、事件流、主动消息、调试日志、前端日志全双工推送
  - **远程访问**：部署到服务器后可通过公网访问，多用户可同时接入
  - **流式回复**：基于 LangChain `astream` 实时输出 token；不支持时自动降级
- 🪵 **可观测日志**：前后端日志统一收集、查询、广播与持久化
- 💾 **数据管理**: SQLite 存储、数据迁移、备份恢复
- 📝 **提示词工程**: 模块化 Markdown 提示词、角色扮演、世界观注入

---

### 技术栈

- **后端**：FastAPI 0.110+ / Uvicorn / Pydantic v2 / WebSockets
- **前端**：React 18 + TypeScript + Vite 5
- **UI 组件库**：Ant Design 5
- **状态管理**：Zustand
- **图表**：ECharts 5
- **HTTP 客户端**：Axios
- **业务核心**：LangChain + LangGraph
- **日志**：自研 `UnifiedLogger` + 多 Handler 架构

---

### 快速开始

#### 环境准备

```bash
# Python >= 3.10
python --version

# 复制环境变量模板
cp example.env .env
# 编辑 .env 填入 API 密钥等配置
```

#### 一键启动（推荐）

```bash
# 自动创建 venv、安装依赖、启动后端 + 前端 dev server
./start.sh
```

启动后访问 http://localhost:8000

#### 手动启动

```bash
pip install -r requirements.txt -r requirements-web.txt
cd src/web/frontend && npm install && cd -

# 统一入口：默认启动 Web / API
python run.py web

# 纯 API 模式（不启动前端 dev server、不挂载静态产物）
python run.py web --no-dev --no-static

# 指定端口
python run.py web --port 8080 --host 127.0.0.1
```

#### 常用 CLI 命令

```bash
python run.py web        # 启动 Web / API（默认）
python run.py stop       # 停止正在运行的 Neo Agent 进程
python run.py status     # 查看运行状态
python run.py logs       # 查看 debug.log 尾部
python run.py logs -f    # 持续跟踪日志输出
```

`main.py` 保留为兼容层，等效于 `python run.py web`。

---

### 访问 URL

| 用途 | URL |
| --- | --- |
| Web 前端主页 | `http://localhost:8000` |
| 前端开发端口（Vite） | `http://localhost:5173` |
| 交互式 API 文档（Swagger UI） | `http://localhost:8000/docs` |
| ReDoc 文档 | `http://localhost:8000/redoc` |
| OpenAPI Schema | `http://localhost:8000/openapi.json` |
| 健康检查 | `http://localhost:8000/api/health` |

---

### 项目结构

```
Neo_Agent/
├── src/                        # 源代码
│   ├── nervous_system/        # 神经系统：CentralRouter + Gateway + Packet
│   ├── cortex/                # 大脑皮层：LLM 推理核心
│   ├── limbic/                # 边缘系统：海马体记忆 + 杏仁核情感
│   ├── prefrontal/            # 前额叶：日程 / 事件 / 主动决策
│   ├── cerebellum/            # 小脑：NPS 工具 / 视觉 / 表达风格
│   ├── hypothalamus/          # 下丘脑：生命状态 / 用户习惯
│   ├── core/                  # 核心模块（v3.x 兼容层 + 公共服务）
│   ├── web/                   # Web GUI
│   │   ├── backend/           # FastAPI 后端（API / WS / Services）
│   │   └── frontend/          # React + Vite + Ant Design 前端
│   ├── tools/                 # 工具模块（UnifiedLogger / DebugLogger 等）
│   └── nps/                   # NPS 工具系统
├── prompts/                   # 提示词模板
├── tests/                     # 测试文件
├── examples/                  # 示例代码
├── docs/                      # 文档
├── main.py                    # 兼容层入口（委托 run.py）
├── run.py                     # 统一 CLI 入口（v4.1 主入口）
├── run_web.py                 # Web 启动实现（被 run.py 复用）
├── start.sh                   # 一键启动脚本
├── requirements.txt           # 核心依赖
├── requirements-web.txt       # Web 端额外依赖
├── example.env                # 环境变量示例
└── LICENSE                    # 许可证
```

---

### 核心模块

- **UnifiedLogger**: 统一日志核心，标准化格式、多 Handler 输出
- **DebugLogger**: 旧日志 API 兼容层，委托 UnifiedLogger
- **CentralRouter**: 神经系统中央路由，跨模块同步 / 流式调用
- **LLMCore / ModelRouter**: LLM 推理与模型路由
- **Chat Agent**: 对话代理核心
- **Memory Store**: 分层记忆系统
- **Emotion Analyzer**: 情感关系分析
- **Schedule Manager**: 日程管理
- **Knowledge Base**: 知识库管理
- **NPS Toolkit**: 工具注册、调用与编排

---

### WebSocket 端点

| 端点 | 说明 |
| --- | --- |
| `/ws/chat` | 流式聊天 |
| `/ws/events` | 全局事件流 |
| `/ws/debug` | 调试日志流 |
| `/ws/proactive` | 主动消息推送 |
| `/ws/frontend-logs` | 前端日志回流（v4.1） |

---

### 提示词系统

Neo Agent 采用模块化的提示词工程系统：

- 📝 **Markdown 模板**: 所有提示词以 Markdown 文件存储
- 🎭 **角色扮演**: 详细的角色设定和行为准则
- 🌍 **世界观注入**: 虚拟世界背景和环境设定
- 🔄 **动态渲染**: 支持变量替换和上下文注入
- 🛡️ **后备机制**: 模板失败时自动降级到硬编码提示词

---

### 许可证

本项目采用 MIT 许可证。详见 [LICENSE](LICENSE) 文件。

---

## English

### Introduction

Neo Agent is a LangChain + LangGraph-based intelligent conversation agent system with a nervous-system-inspired multi-layer architecture. It features role-playing, long-term memory management, emotional relationship analysis, intelligent schedule management, and observable unified logging.

Since v4.1, the project unifies the entry point and logging system: `run.py` is the single main entry, and `UnifiedLogger` carries logs across the frontend and backend, allowing frontend console logs to flow back to the backend in real time via WebSocket.

---

### Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                      Entry Layer                             │
│   run.py  (web / stop / status / logs)   ←  unified CLI     │
│   main.py  ──────────────────────────────→ run.py wrapper   │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────┴───────────────────────────────┐
│                      Web Service Layer                       │
│  FastAPI + Uvicorn                                            │
│  ├── REST API  (/api/*)                                       │
│  ├── WebSocket (/ws/chat, /ws/events, /ws/debug,             │
│  │              /ws/proactive, /ws/frontend-logs)             │
│  └── Static frontend (React + Vite + Ant Design)              │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────┴───────────────────────────────┐
│                   Nervous System                             │
│  CentralRouter ── Packet ── Gateway                          │
│  Cross-module workflow: chat → emotion → schedule → proactive│
└─────────────────────────────────────────────────────────────┘
                              │
┌──────────┬──────────┬───────────────┬──────────┬────────────┐
│ Cortex   │ Limbic   │ Prefrontal    │Cerebellum│Hypothalamus│
│ LLMCore  │ Memory   │ Schedule /    │ NPS tools│ Life state │
│ ModelRouter│ Emotion│ proactive     │ vision   │ user habits│
└──────────┴──────────┴───────────────┴──────────┴────────────┘
                              │
┌─────────────────────────────┴───────────────────────────────┐
│                  Unified Logging Infrastructure              │
│  UnifiedLogger  ←  FileHandler / MemoryBufferHandler         │
│                 ← WebSocketBroadcastHandler                   │
│                 ← ExternalForwarderHandler                    │
│  DebugLogger (legacy API)  ←  delegates to UnifiedLogger     │
└─────────────────────────────────────────────────────────────┘
```

---

### Key Features

- 🧠 **Hierarchical Memory System**: short-term, long-term, knowledge base, base knowledge
- 💭 **Intelligent Conversation**: role-playing, continuous dialogue, memory retrieval, emotional understanding, streaming replies
- 📊 **Emotion Analysis**: impression assessment, cumulative scoring, relationship visualization
- 📅 **Schedule Management**: natural-language creation, conflict detection, reminder push
- 🛠️ **NPS Toolkit**: extensible tool registration, invocation and orchestration
- 🖥️ **Modern Web GUI**: React + TypeScript + Vite + Ant Design
- 🌐 **Web-only capabilities**:
  - **Cross-device access**: any browser at `http://<host>:8000`
  - **Real-time WebSocket push**: message / event / proactive / debug / frontend logs
  - **Remote access**: deployable on a server, multi-user concurrent
  - **Streaming reply**: LangChain `astream` with automatic fallback
- 🪵 **Observable Logging**: unified log collection, query, broadcast and persistence across frontend and backend
- 💾 **Data Management**: SQLite storage, migration, backup and recovery
- 📝 **Prompt Engineering**: modular Markdown prompts, character settings, worldview injection

---

### Tech Stack

- **Backend**: FastAPI 0.110+ / Uvicorn / Pydantic v2 / WebSockets
- **Frontend**: React 18 + TypeScript + Vite 5
- **UI Kit**: Ant Design 5
- **State**: Zustand
- **Charts**: ECharts 5
- **HTTP client**: Axios
- **Core**: LangChain + LangGraph
- **Logging**: custom `UnifiedLogger` + multi-handler architecture

---

### Quick Start

#### Environment

```bash
# Python >= 3.10
python --version

cp example.env .env
# Edit .env with your API keys and configuration
```

#### One-click launch (recommended)

```bash
./start.sh
```

Open http://localhost:8000

#### Manual launch

```bash
pip install -r requirements.txt -r requirements-web.txt
cd src/web/frontend && npm install && cd -

# Unified entry: start Web / API by default
python run.py web

# Pure API mode
python run.py web --no-dev --no-static

# Custom port
python run.py web --port 8080 --host 127.0.0.1
```

#### Common CLI commands

```bash
python run.py web        # Start Web / API (default)
python run.py stop       # Stop running Neo Agent process
python run.py status     # Show running status
python run.py logs       # Tail debug.log
python run.py logs -f    # Follow log output
```

`main.py` remains as a compatibility wrapper equivalent to `python run.py web`.

---

### Access URLs

| Purpose | URL |
| --- | --- |
| Web frontend | `http://localhost:8000` |
| Vite dev port | `http://localhost:5173` |
| Swagger UI | `http://localhost:8000/docs` |
| ReDoc | `http://localhost:8000/redoc` |
| OpenAPI schema | `http://localhost:8000/openapi.json` |
| Health check | `http://localhost:8000/api/health` |

---

### Project Structure

```
Neo_Agent/
├── src/                        # Source code
│   ├── nervous_system/        # Nervous system: CentralRouter + Gateway + Packet
│   ├── cortex/                # Cerebral cortex: LLM reasoning core
│   ├── limbic/                # Limbic system: memory + emotion
│   ├── prefrontal/            # Prefrontal cortex: schedule / event / proactive
│   ├── cerebellum/            # Cerebellum: NPS tools / vision / expression style
│   ├── hypothalamus/          # Hypothalamus: life state / user habits
│   ├── core/                  # Core modules (v3.x compatibility + shared services)
│   ├── web/                   # Web GUI
│   │   ├── backend/           # FastAPI backend (API / WS / services)
│   │   └── frontend/          # React + Vite + Ant Design frontend
│   ├── tools/                 # Utilities (UnifiedLogger / DebugLogger, etc.)
│   └── nps/                   # NPS tool system
├── prompts/                   # Prompt templates
├── tests/                     # Test files
├── examples/                  # Example code
├── docs/                      # Documentation
├── main.py                    # Compatibility wrapper (delegates to run.py)
├── run.py                     # Unified CLI entry (v4.1 main entry)
├── run_web.py                 # Web launcher implementation (reused by run.py)
├── start.sh                   # One-click launcher
├── requirements.txt           # Core dependencies
├── requirements-web.txt       # Web-only dependencies
├── example.env                # Environment variables template
└── LICENSE                    # License file
```

---

### Core Modules

- **UnifiedLogger**: unified logging core with standardized format and multi-handler output
- **DebugLogger**: legacy logging API compatibility wrapper delegating to UnifiedLogger
- **CentralRouter**: nervous system central router for cross-module sync/streaming calls
- **LLMCore / ModelRouter**: LLM reasoning and model routing
- **Chat Agent**: conversation agent core
- **Memory Store**: hierarchical memory system
- **Emotion Analyzer**: emotional relationship analysis
- **Schedule Manager**: schedule management
- **Knowledge Base**: knowledge base management
- **NPS Toolkit**: tool registration, invocation and orchestration

---

### WebSocket Endpoints

| Endpoint | Description |
| --- | --- |
| `/ws/chat` | Streaming chat |
| `/ws/events` | Global event stream |
| `/ws/debug` | Debug log stream |
| `/ws/proactive` | Proactive message push |
| `/ws/frontend-logs` | Frontend log backflow (v4.1) |

---

### Prompt System

Neo Agent uses a modular prompt engineering system:

- 📝 **Markdown templates**: all prompts stored as Markdown files
- 🎭 **Role-playing**: detailed character settings and behavior guidelines
- 🌍 **Worldview injection**: virtual world background and environment settings
- 🔄 **Dynamic rendering**: variable substitution and context injection
- 🛡️ **Fallback mechanism**: automatically falls back to hard-coded prompts

---

### License

This project is licensed under the MIT License. See [LICENSE](LICENSE) file for details.
