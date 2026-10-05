# Neo Agent 项目结构

## 目录组织

```
neo_agent/
├── ui/v2/              # TUI v2 客户端 ✅ 已完成
│   ├── app.py          # 主应用 + 侧边栏 + 状态栏 (443行)
│   ├── views.py        # 6个视图完整实现 (617行)
│   ├── theme.py        # 琥珀主题定义
│   ├── client.py       # JSON-RPC 客户端
│   ├── modals.py       # 模态对话框
│   └── event_handlers.py
│
├── service/            # 服务层 ⏳ 框架就绪
│   ├── daemon.py       # 守护进程骨架
│   ├── rpc_handlers.py # RPC API 处理器
│   ├── events.py       # WebSocket 事件广播
│   └── mock_daemon.py  # Mock 服务（测试用）
│
├── runtime/            # 运行时服务 ⏳ 待集成
│   ├── agent.py        # LangChain Agent 编排
│   ├── cognition.py    # 认知门控
│   ├── expression.py   # 语言生成
│   ├── daily_itinerary.py    # 日程自动生成
│   ├── scene_generation.py   # 场景生成
│   ├── scene_scheduler.py    # 场景调度
│   ├── relationship.py       # 关系管理
│   ├── emotion.py            # 情绪状态
│   └── domain_services.py    # 领域服务
│
├── storage/            # 存储层 ⏳ 待实现
│   ├── disk_store.py   # PyVDisk 集成接口
│   └── vfs_workspace.py # VFS 工作区
│
├── nps/                # NPS 插件系统 📝 未开始
│   └── runtime.py      # 插件运行时
│
├── services/           # 辅助服务 ⏳ 部分完成
│   ├── collaboration.py # 协作服务
│   └── scheduling.py    # 调度服务
│
└── cli.py              # 命令行入口 ✅ 基础完成
```

## 核心模块状态

### ✅ 已完成
1. **TUI v2 客户端** (`ui/v2/`)
   - 主应用框架
   - 6 个完整视图
   - 琥珀主题
   - 快捷键和鼠标交互
   - 自动化测试

2. **CLI 工具** (`cli.py`)
   - `neo-agent tui` 命令
   - 基础框架（start/stop 待完善）

### ⏳ 进行中
3. **服务层** (`service/`)
   - 守护进程骨架 ✅
   - RPC 处理器 ✅
   - WebSocket 广播 ✅
   - 真实启动流程 ⏳

4. **运行时** (`runtime/`)
   - 数据模型定义 ✅
   - LangChain 集成 ⏳
   - 认知门控实现 ⏳
   - 日程与场景系统 ⏳

5. **存储层** (`storage/`)
   - DiskStore 接口 ✅
   - PyVDisk 连接 ⏳
   - 持久化实现 ⏳

### 📝 未开始
6. **NPS 插件系统** (`nps/`)
   - VScript 运行时
   - Python 扩展隔离
   - Manifest 管理
   - 工具桥接

7. **群聊感知**
   - 发言/沉默决策
   - 群平台连接器
   - 离线回放

## 数据流

```
用户输入
  ↓
TUI Client (ui/v2/)
  ↓ JSON-RPC
Service Daemon (service/)
  ↓
Runtime Services (runtime/)
  ├── Cognition (认知门控)
  ├── Agent (LangChain 编排)
  ├── Expression (语言生成)
  ├── Scene (场景管理)
  └── Relationship (关系网络)
  ↓
Storage Layer (storage/)
  ↓
PyVDisk (持久化)
```

## 技术栈

### 前端 (TUI)
- **框架**: Textual 0.80+
- **主题**: 琥珀温暖配色
- **交互**: 快捷键 + 鼠标点击

### 后端 (Service)
- **IPC**: Unix socket + JSON-RPC 2.0
- **实时**: WebSocket 事件广播
- **并发**: asyncio + threading

### 核心 (Runtime)
- **Agent**: LangChain + LangChain-OpenAI
- **认知**: 门控架构（决策→执行→生成）
- **调度**: 日程 worker + 场景切换

### 存储 (Storage)
- **持久化**: PyVDisk DataDisk API
- **数据**: 角色、记忆、知识、关系、场景、事件、审计

## 文件统计

### 代码量
```
ui/v2/       ~1100 行  ✅ 完成
service/     ~600 行   ⏳ 40%
runtime/     ~1500 行  ⏳ 30%
storage/     ~400 行   ⏳ 20%
nps/         ~200 行   📝 5%
────────────────────────
总计         ~3800 行
```

### 测试覆盖
```
TUI 视图切换    6/6   ✅ 100%
TUI 快捷键      7/7   ✅ 100%
服务层 API      0/15  ⏳ 0%
运行时服务      0/20  ⏳ 0%
集成测试        0/10  ⏳ 0%
```

## 依赖关系

```
TUI Client
  ├── Textual (UI 框架)
  └── aiohttp (WebSocket 客户端)

Service Daemon
  ├── aiohttp (JSON-RPC + WebSocket 服务端)
  ├── python-daemon (守护进程)
  └── lockfile (PID 管理)

Runtime
  ├── LangChain (Agent 编排)
  ├── LangChain-OpenAI (LLM 接口)
  └── asyncio (异步调度)

Storage
  └── PyVDisk (持久化后端)
```

## 配置文件

```
~/.neo_agent/
├── agent.sock          # Unix socket
├── agent.pid           # PID 文件
├── agent.log           # 日志文件
├── config.json         # 全局配置
└── data/               # PyVDisk 数据目录
    └── agent.vdisk     # 数据镜像
```

## 入口点

### 用户命令
```bash
neo-agent tui           # 启动 TUI 客户端 ✅
neo-agent start         # 启动后台服务 ⏳
neo-agent stop          # 停止服务 ⏳
neo-agent status        # 查看状态 ⏳
neo-agent restart       # 重启服务 ⏳
```

### Python 模块
```python
# TUI 客户端
python3 -m neo_agent.ui.v2.app

# 服务守护进程（待实现）
python3 -m neo_agent.service.daemon

# 测试
python3 test_tui_simple.py
```

## 开发路线

### Phase 1: TUI 重构 ✅ (已完成)
- 侧边栏修复
- 6 个视图实现
- 琥珀主题应用
- 测试验证

### Phase 2: 服务层 ⏳ (进行中)
- 守护进程启动
- JSON-RPC 服务
- WebSocket 广播
- PyVDisk 连接

### Phase 3: 核心功能 ⏳ (下一步)
- LangChain 集成
- 认知门控
- 角色初始化
- 对话流程

### Phase 4: 拟人化 📝 (规划中)
- 日程自动生成
- 场景驱动
- 关系网络
- 情绪状态

### Phase 5: 插件与群聊 📝 (未来)
- NPS 系统
- 群聊感知
- 平台连接器

## 参考文档

- `QUICKREF.md` - 快速参考
- `CURRENT_STATUS.md` - 当前状态
- `PROGRESS.md` - 详细进度
- `SESSION_SUMMARY.md` - 会话记录
- `PROJECT_STRUCTURE.md` - 本文件

---

**更新**: 2026-10-05  
**分支**: Dev  
**提交**: d1fb5d3  
**完成度**: ~50%
