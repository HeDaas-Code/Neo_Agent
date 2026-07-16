# Neo Agent - 智能对话代理系统

[English](#english) | [简体中文](#中文)

---

## 中文

### 简介

Neo Agent 是一个基于 LangChain + LangGraph 的智能对话代理系统，采用多层模型架构，具备角色扮演、长效记忆管理、情感关系分析和智能日程管理功能。

### 架构特性

#### 🏗️ 复合框架架构
- **LangChain**: 核心框架，提供LLM抽象和链式调用
- **多层模型架构**: 根据任务类型智能选择模型
  - 主模型 (DeepSeek-V3.2): 处理主要对话、复杂推理
  - 工具模型 (GLM-4.6V): 处理工具调用、意图识别等轻量级任务
  - 多模态模型 (Qwen3-VL-32B): 处理多模态识别和推理

### 主要特性

- 🧠 **分层记忆系统**: 短期记忆、长期记忆、知识库、基础知识
- 💭 **智能对话**: 角色扮演、连续对话、记忆检索、情感理解
- 📊 **情感分析**: 印象评估、累计评分、关系可视化
- 🖥️ **现代化GUI**: Web GUI（默认）+ Tkinter GUI（开发态/降级方案）
- 🌐 **Web 端独占能力**:
  - **跨设备访问**：任意浏览器打开 http://<host>:8000 即可使用，手机/平板/PC 体验一致
  - **实时 WebSocket 推送**：消息流、事件流、主动消息、调试日志全双工推送
  - **远程访问**：部署到服务器后可通过公网访问，多用户可同时接入
  - **流式回复**：基于 LangChain astream 实时输出 token；不支持时降级到 run_in_executor 模拟流式
- ️ **数据管理**: SQLite存储、数据迁移、备份恢复
- 📝 **提示词工程**: 模块化Markdown提示词、角色扮演、世界观注入

### 技术栈

- **后端**：FastAPI 0.110+ / Uvicorn / Pydantic v2 / WebSockets
- **前端**：React 18 + TypeScript + Vite 5
- **UI 组件库**：Ant Design 5
- **状态管理**：Zustand
- **图表**：ECharts 5
- **HTTP 客户端**：Axios
- **业务核心**：LangChain + LangGraph（与 Tkinter 模式共用，未改动）

### 快速开始

#### Web GUI（推荐 / 默认）

```bash
# 一键启动（自动安装依赖 + 启动后端 + 前端 dev server）
./start.sh

# 或手动启动
pip install -r requirements-web.txt
cd src/web/frontend && npm install && cd -
python run_web.py
```

启动后访问 http://localhost:8000

> 默认模式为 Web；通过 `--tk` 切换到原 Tkinter GUI。

#### Tkinter GUI（开发态/降级方案）

```bash
python main.py --tk
```

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
│   ├── core/              # 核心模块（与 GUI 解耦）
│   ├── gui/               # Tkinter GUI（开发态/降级）
│   ├── web/               # Web GUI（默认）
│   │   ├── backend/       # FastAPI 后端（API / WS / Services / Schemas）
│   │   └── frontend/      # React + Vite + Ant Design 前端
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
├── main.py               # 主入口（默认 Web，可 --tk 切换 Tkinter）
├── run.py                # 简化启动器
├── run_web.py            # Web 模式启动入口
├── start.sh              # Web 模式一键启动脚本
├── requirements.txt      # 核心依赖
├── requirements-web.txt  # Web 端额外依赖
├── example.env          # 环境变量示例
└── LICENSE              # 许可证
```

### 核心模块

- **prompt_manager**: 提示词管理，支持Markdown模板加载和渲染
- **model_config**: 多层模型配置管理
- **langchain_llm**: LangChain LLM封装，支持模型路由
- **llm_helper**: LLM辅助工具，简化工具级任务调用
- **chat_agent**: 对话代理核心
- **database_manager**: 统一数据库管理
- **emotion_analyzer**: 情感关系分析（使用工具模型）
- **knowledge_base**: 知识库管理（使用工具模型）
- **long_term_memory**: 长期记忆系统
- **schedule_manager**: 日程管理

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

## GUI 启动方式（v3.0.0+）

> 以下章节为 v3.0.0 引入的 Web GUI / Tkinter 双模式启动补充说明，保留原"快速开始"中的命令行示例之外，作为对外的明确参考。

### Web GUI（默认模式）

**启动方式**

```bash
# 方式 A：主入口（默认即 Web 模式，可显式加 --web）
python main.py --web

# 方式 B：一键脚本（自动 venv + pip install + 启动前端 dev server）
./start.sh
```

启动成功后会看到：

- FastAPI 监听 `http://0.0.0.0:8000`（可用 `--host` / `--port` 调整）
- Vite dev server（开发态）监听 `http://localhost:5173`
- 终端打印 `API 文档: http://0.0.0.0:8000/docs`

**访问 URL**

| 用途 | URL |
| --- | --- |
| Web 前端主页 | `http://localhost:8000` |
| 备用开发端口（Vite） | `http://localhost:5173` |
| 交互式 API 文档（Swagger UI） | `http://localhost:8000/docs` |
| ReDoc 文档 | `http://localhost:8000/redoc` |
| OpenAPI Schema | `http://localhost:8000/openapi.json` |
| 健康检查 | `http://localhost:8000/api/health` |

**API 文档**

- 默认挂在 FastAPI 自动生成的 `/docs`（Swagger UI）与 `/redoc`
- WebSocket 端点（不在 `/docs` 中列出）需另行参考 [`docs/architecture.md`](docs/architecture.md)：
  - `/ws/chat` 流式聊天
  - `/ws/events` 全局事件流
  - `/ws/debug` 调试日志流
  - `/ws/proactive` 主动消息推送

### Tkinter 模式（开发态/降级）

```bash
# 显式切换到 Tkinter GUI（不依赖 Web 端依赖）
python main.py --tk
```

> Tkinter 模式与 Web GUI 共享同一份 `chat_agent.db`，**数据零迁移**；当 Web 端不可用时随时回滚。详见 [`docs/rollback-procedure.md`](docs/rollback-procedure.md)。

---

## English

### Introduction

Neo Agent is a LangChain + LangGraph-based intelligent conversation agent system with multi-tier model architecture, featuring role-playing, long-term memory management, emotional relationship analysis, and intelligent schedule management capabilities.

### Architecture Features

#### 🏗️ Composite Framework Architecture
- **LangChain**: Core framework providing LLM abstraction and chain invocation
- **Multi-tier Model Architecture**: Intelligent model selection based on task type
  - Main Model (DeepSeek-V3.2): Handles primary conversations and complex reasoning
  - Tool Model (GLM-4.6V): Handles tool invocations, intent recognition, and lightweight tasks
  - Multimodal Model (Qwen3-VL-32B): Handles multimodal recognition and reasoning

### Key Features

- 🧠 **Hierarchical Memory System**: Short-term memory, long-term memory, knowledge base, base knowledge
- 💭 **Intelligent Conversation**: Role-playing, continuous dialogue, memory retrieval, emotional understanding
- 📊 **Emotion Analysis**: Impression assessment, cumulative scoring, relationship visualization
- 🖥️ **Modern GUI**: Web GUI (default) + Tkinter GUI (dev/fallback)
- 🌐 **Web-only capabilities**:
  - **Cross-device access**: any browser at http://&lt;host&gt;:8000 — phone, tablet, PC consistent UX
  - **Real-time WebSocket push**: message stream / event stream / proactive message / debug log full-duplex
  - **Remote access**: deployable on a server, multi-user concurrent
  - **Streaming reply**: LangChain astream tokens; falls back to run_in_executor chunked simulation
- ️ **Data Management**: SQLite storage, data migration, backup and recovery

### Tech Stack

- **Backend**: FastAPI 0.110+ / Uvicorn / Pydantic v2 / WebSockets
- **Frontend**: React 18 + TypeScript + Vite 5
- **UI Kit**: Ant Design 5
- **State**: Zustand
- **Charts**: ECharts 5
- **HTTP client**: Axios
- **Core**: LangChain + LangGraph (shared with Tkinter, unchanged)

### Quick Start

#### Web GUI (recommended / default)

```bash
# One-click launcher (auto-installs deps + starts backend + frontend dev server)
./start.sh

# Or manual
pip install -r requirements-web.txt
cd src/web/frontend && npm install && cd -
python run_web.py
```

Open http://localhost:8000

> Default mode is Web. Pass `--tk` to switch back to Tkinter GUI.

#### Tkinter GUI (dev / fallback)

```bash
python main.py --tk
```

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
├── main.py               # Main entry point (default Web, --tk for Tkinter)
├── run.py                # Simplified launcher
├── run_web.py            # Web-mode launcher
├── start.sh              # Web-mode one-click launcher
├── requirements.txt      # Core dependencies
├── requirements-web.txt  # Web-only dependencies
├── example.env          # Environment variables template
└── LICENSE              # License file
```

### Core Modules

- **chat_agent**: Conversation agent core
- **database_manager**: Unified database management
- **emotion_analyzer**: Emotional relationship analysis
- **knowledge_base**: Knowledge base management
- **long_term_memory**: Long-term memory system
- **schedule_manager**: Schedule management

### GUI Launch Modes (v3.0.0+)

> This section supplements the Quick Start with explicit v3.0.0 launch instructions for both the Web GUI and Tkinter modes.

#### Web GUI (default)

**Launch**

```bash
# Method A: main entry (Web is the default; --web is explicit)
python main.py --web

# Method B: one-click script (auto venv + pip install + frontend dev server)
./start.sh
```

On a successful start you should see:

- FastAPI listening on `http://0.0.0.0:8000` (use `--host` / `--port` to override)
- Vite dev server (dev mode) on `http://localhost:5173`
- The supervisor log line: `API 文档: http://0.0.0.0:8000/docs`

**Access URLs**

| Purpose | URL |
| --- | --- |
| Web frontend | `http://localhost:8000` |
| Vite dev port (alt) | `http://localhost:5173` |
| Interactive API docs (Swagger UI) | `http://localhost:8000/docs` |
| ReDoc | `http://localhost:8000/redoc` |
| OpenAPI schema | `http://localhost:8000/openapi.json` |
| Health check | `http://localhost:8000/api/health` |

**API documentation**

- Auto-generated by FastAPI at `/docs` (Swagger UI) and `/redoc`
- WebSocket endpoints (not listed in `/docs`) are documented in [`docs/architecture.md`](docs/architecture.md):
  - `/ws/chat` — streaming chat
  - `/ws/events` — global event stream
  - `/ws/debug` — debug log stream
  - `/ws/proactive` — proactive message push

#### Tkinter Mode (dev / fallback)

```bash
# Switch to the original Tkinter GUI (no Web-side deps required)
python main.py --tk
```

> Tkinter shares the same `chat_agent.db` with the Web GUI — **zero data migration**; use it as a safe rollback target when the Web stack is unavailable. See [`docs/rollback-procedure.md`](docs/rollback-procedure.md).

### License

This project is licensed under the MIT License. See [LICENSE](LICENSE) file for details.

---

## Web GUI（v3.0.0+）

> 本节为 v3.0.0+ Web GUI 使用速查（追加于原文档末尾，原内容保留不动）。详细架构参见 [`docs/architecture.md`](docs/architecture.md)。

### 启动方式

- 开发模式：`bash start.sh`（自动安装依赖 + 启动前后端）
- 生产模式：`python run_web.py`（需先 `cd src/web/frontend && npm run build`）
- 启动 Tkinter（兼容）：`python main.py --tk`

### 访问 URL

- Web GUI：http://localhost:8000
- API 文档（自动生成）：http://localhost:8000/docs
- 健康检查：http://localhost:8000/api/health

### 功能页面

- `/chat` — 聊天对话 + 情感雷达 + 话题时间线
- `/debug` — 实时调试日志
- `/knowledge` — 知识库管理
- `/schedule` — 日程管理
- `/event` — 事件管理
- `/nps` — NPS 工具管理
- `/database` — 数据库浏览
- `/creative` — 创作项目管理

### 回滚 Tkinter

如需紧急回滚：`python main.py --tk` 即可启动原桌面 GUI，数据完全兼容。
