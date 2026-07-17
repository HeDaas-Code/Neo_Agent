# Changelog / 更新日志

All notable changes to this project will be documented in this file.

本文件记录项目的所有重要变更。格式遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/) 规范。

## v4.0.0 (2026-07-17)

### 🧠 重构
- **基于人脑认知理论的神经系统架构**：新增 `src/nervous_system/` 统一数据路由与外部访问网关
- **大脑皮层（Cortex）**：`src/cortex/` 承载 LLM 推理、生成、理解能力统一入口（`llm_core`、`echo_cortex`、供应商注册表）
- **边缘系统（Limbic）**：`src/limbic/` 承载记忆、情感、会话（`hippocampus`、`amygdala`）
- **前额叶（Prefrontal）**：`src/prefrontal/` 承载日程、事件、主动决策（`schedule`、`event`、`proactive`）
- **小脑（Cerebellum）**：`src/cerebellum/` 承载工具调用、视觉、反射（`nps`、`vision`、`intent`、`interrupt`、`style`）
- **下丘脑（Hypothalamus）**：`src/hypothalamus/` 承载生命状态、用户习惯（`state`、`habits`）
- **统一网关**：HTTP Gateway、WebSocket Gateway、LLM Gateway 均通过 `CentralRouter + Packet` 进行可追踪路由

### 🔧 修改
- `src/core/*` 原模块保留为 v3.1.0 兼容层，通过导入转发访问新架构实现，**完全向后兼容**
- Web 后端（`src/web/backend/main.py`）集成 `NeoApp`，新增 `/api/v4/gateway/{target}/{channel}` 通用网关路由
- `DatabaseManager` 对 `:memory:` 数据库复用单一连接，解决测试中空库问题

### ✅ 测试
- 全量测试通过：`227 passed, 27 skipped, 0 failed, 0 error`
- 新增/修复 `tests/unit/*` 各层模块测试、`tests/integration/test_web_neo_bridge.py`、特性开关隔离测试

### ⚠️ BREAKING
- 无破坏性变更；所有新特性默认关闭，可通过 `.env` 的 `ENABLE_*` 开关按需启用

## v3.1.0 (2026-XX-XX)

### ✨ 新增
- **会话持久化**：聊天会话与消息存储到数据库（`chat_sessions` / `chat_messages`），支持多会话切换、刷新页面自动恢复、删除级联
- **前端 SessionSidebar**：左侧抽屉列出会话，支持新建/重命名/删除/切换
- **多供应商 LLM 抽象**：内置 6 个 OpenAI 兼容 preset（openai / deepseek / siliconflow / moonshot / zhipu / custom），通过 `LLM_PROVIDER` / `LLM_API_KEY` / `LLM_BASE_URL` / `LLM_MODEL_NAME` 配置
- **LLM 配置 API**：`GET /api/llm/config` + `POST /api/llm/test`
- **Settings 页面**：显示当前 LLM 配置 + 一键测试连接

### 🔧 修改
- 11 个文件中 19 处 `SILICONFLOW_API_KEY` / `SILICONFLOW_API_URL` 调用统一改为 `llm_providers.resolve_*()` 接口
- 旧 `SILICONFLOW_API_KEY` / `SILICONFLOW_API_URL` / `MODEL_NAME` 仍可作为 fallback，**完全向后兼容**
- `model_config.py` 改用供应商注册表
- `useChatStream` 增 `sessionId` / `switchSession` / `ack` 帧处理
- `ChatService` 增持久化钩子（流结束后双写 user+assistant）

### 🗃️ 数据库
- 新增表 `chat_sessions` / `chat_messages`（外键 ON DELETE CASCADE）

### ⚠️ BREAKING
- 数据库 schema 变更：首次启动自动建表（v3.0.0 启动仅 1 天，存量可丢弃）

## [3.0.0] - 2026-07-14

### Added / 新增
- **Web GUI**（FastAPI + React + Ant Design）：替代本地 Tkinter 桌面 GUI（默认启动模式）
- **WebSocket 流式聊天**（`/ws/chat`）：基于 LangChain astream 的 token 级流式输出，降级到 `run_in_executor` 模拟流式
- **WebSocket 主动消息推送**（`/ws/proactive`）：服务端主动向客户端推送
- **WebSocket 事件流**（`/ws/events`）：来自 `EventManager` 的全局事件广播
- **Debug 日志流**（`/ws/debug`）：来自 `DebugLogger` 的实时日志
- **管理页面**：Knowledge / Schedule / Event / NPS / Database / Creative 六个管理类页签
- **Pydantic schema 强约束 + SQLite WAL 模式**：
  - `src/web/backend/schemas/*` 全部基于 Pydantic v2
  - `src/core/database_manager.py` 启用 `PRAGMA journal_mode=WAL`
- 新增文件：
  - `src/web/` — 后端（FastAPI）+ 前端（Vite + React）源码
  - `requirements-web.txt` — Web 端依赖
  - `run_web.py` — Web 模式启动入口
  - `start.sh` — 一键启动脚本

### Changed / 变更
- `EventManager` 新增 `subscribe` / `publish` API（`src/core/event_manager.py`）
  - `subscribe(event_type, callback)` 注册进程内监听者
  - `publish(event_type_or_obj, payload)` 异步广播，listener 异常隔离
- `BackgroundScheduler` 每个 tick 推送状态（`src/core/background_scheduler.py`）
  - 每个 tick 完成后 `EventManager.publish("scheduler_tick", status_payload)` 推送给订阅者
- `ProactiveEngine` 主动消息通过 `EventManager` 推送（`src/core/proactive_engine.py`）
  - 触发主动消息时改为 `em.publish("proactive_message", payload)`
- `ChatAgent` 新增 `chat_stream()` 异步流式方法（原 `chat()` 同步方法保留，向后兼容）
- `main.py` 新增 `--web`（默认）/ `--tk` 参数

### Deprecated / 弃用
- 无

### Removed / 移除
- 无

### Fixed / 修正
- 无

### Security / 安全
- **23 表白名单防御 SQL 注入**（`src/core/database_manager.py`）
  - 多个 `update_*` 方法使用白名单验证允许更新的列名（line 1964, 2100, 2301 等），过滤只允许白名单中的列名
  - 业务层禁止拼接 SQL 列名 / 表名

### Preserved / 保留
- 全部 `src/core/*` 业务层逻辑**未修改**，仅扩展方法（`chat_stream` / WAL / `subscribe`+`publish`）
- 数据存储（`chat_agent.db`）**未迁移**，Tkinter 端与 Web 端共享
- 原 Tkinter GUI 通过 `python main.py --tk` 仍可使用

### Documentation / 文档
- 新增 [`docs/architecture.md`](docs/architecture.md):整体架构图、ASCII 数据流、模块依赖、并行调度
- 新增 [`docs/rollback-procedure.md`](docs/rollback-procedure.md):5 分钟回滚到 Tkinter 步骤 + 5 条 FAQ
- 更新 [`README.md`](README.md):增加 Web GUI 启动方式、访问 URL、`/docs`、Tkinter 回滚说明
- 新增 [`.trae/specs/migrate-tkinter-to-web/verification-report.md`](../.trae/specs/migrate-tkinter-to-web/verification-report.md):5 阶段总体验收报告(326 行,含 P0/P1/P2 清单)

### 验收状态 / Verification Status (2026-07-14)
- **验收方法**:5 个并行子代理 + 静态代码分析 + 测试桩验证
- **整体判定**:**NO-GO(条件式)** — 后端可发,前端 6 页面 mock→真接口未完成
- **数据汇总**:✅ 69 / ⚠️ 21 / ❌ 5(73%)
- **跨阶段核心约束全部达成**:数据零迁移、业务层零改动、Feature flag 兼容、依赖最小化、回滚 ≤ 5 分钟、CHANGELOG 齐全

#### 本次完成(具体改动)

**阶段 A — 基础设施(18/20 ✅)**
- 新建 `src/web/backend/main.py`:FastAPI 应用,CORS / 路由挂载 / `/api/health` / `/docs`
- 新建 `src/web/backend/ws/manager.py`:连接注册/注销/广播,清理机制在 `finally` 块
- 新建 `src/web/backend/ws/{chat,events,proactive,debug}.py`:4 个 WebSocket 端点
- 新建 `src/web/backend/services/{chat,database,event}_service.py`:三层包装,ChatAgent 懒加载,`ALLOWED_TABLES` 23 表白名单
- 新建 `src/web/backend/schemas/*.py`:Pydantic v2 DTO(ChatRequest/ChatResponse/EventDTO/EmotionResponse/TimelineResponse/KnowledgeEntity/ScheduleDTO 等)
- 新建 `src/web/frontend/`:Vite + React 18 + TypeScript + Ant Design 5 + Tailwind 3 + zustand + ECharts 项目骨架
- 新建 `src/web/frontend/src/components/Layout.tsx`:Sider + Header + Content 8 菜单
- 新建 `requirements-web.txt`:5 行独立依赖(fastapi/uvicorn/websockets/python-multipart/pydantic)
- 新建 `run_web.py`:并发启动 FastAPI + 前端 dev server(受 `ENABLE_FRONTEND_DEV=1` 控制)
- 改造 `main.py`:新增 `--web`(默认)/ `--tk` 互斥参数,`_run_web` / `_run_tkinter` 双分支
- 新建 `start.sh`:Python 3.10+ 检查 + venv 创建 + 依赖安装 + 一键启动

**阶段 B — 核心页面(13/17 ✅)**
- 新建 `src/core/chat_agent.py:1049-1177` `chat_stream()`:AsyncIterator,先 LangChain astream,降级到 `run_in_executor(chat)` + 40ms token 切片,原 `chat()` 同步方法保留
- 新建 `src/web/frontend/src/hooks/useWebSocket.ts`:指数退避 `1→2→4→8→16→30s`,`computeBackoff = min(reconnectInterval * 2**attempt, maxReconnectInterval)`
- 新建 `src/web/frontend/src/hooks/useChatStream.ts`:`chunk` 流式追加 + `emotion_update` 写入 `window.__lastEmotion`
- 新建 `src/web/frontend/src/hooks/useProactiveStream.ts`:订阅 `/ws/proactive` 维护消息队列
- 新建 `src/web/frontend/src/components/ChatBubble.tsx`:user/assistant/system 三种样式
- 新建 `src/web/frontend/src/components/MessageList.tsx` / `ChatInput.tsx`:Enter 发、Shift+Enter 换行
- 新建 `src/web/frontend/src/components/EmotionPanel.tsx`:ECharts 雷达图,Plutchik 8 维
- 新建 `src/web/frontend/src/components/TimelineCanvas.tsx`:ECharts 散点图,日期 × 分类
- 新建 `src/web/frontend/src/pages/Chat/index.tsx`:70/30 双栏,ProactiveMessageList + MessageList + ChatInput + EmotionPanel + TimelineCanvas
- 新建 `src/web/frontend/src/pages/Debug/index.tsx` + `components/Debug/{LogFilterBar,LogExporter}.tsx`:实时日志 + 模块/级别/时间筛选 + TXT/JSON 导出
- 新建 `src/web/backend/api/emotion.py` `GET /api/emotion/latest`:返回 `cumulative` + `plutchik`
- 新建 `src/web/backend/api/memory.py` `GET /api/memory/timeline?days=7` + `GET /api/memory/loop/{uuid}/context`
- 新建 `src/web/frontend/src/utils/proactiveSound.ts`:Web Audio API 合成 440Hz 提示音,localStorage 持久化开关
- 新建 `tests/test_chat_stream.py`:覆盖 normal / exception / cancel 三种场景

**阶段 C — 管理页面(后端 4/6,前端 5/6 部分通过)**
- 新建 `src/web/backend/api/knowledge.py`:`GET /api/knowledge/search?q=` + `POST /api/knowledge` + `DELETE /api/knowledge/{uuid}`
- 新建 `src/web/backend/api/schedule.py`:`GET /api/schedule?date=` + `POST/PUT/DELETE /api/schedule/{id}` + `POST /api/schedule/{id}/confirm`(YAML 校验 400)
- 新建 `src/web/backend/api/database.py`:`GET /api/database/tables` + `GET /api/database/{table}?limit=1-1000` + `DELETE /api/database/{table}/{uuid}`,删除走 `X-Confirm: true` header
- 新建 `src/web/backend/api/creative.py`:`GET /api/creative/projects` + `GET /api/creative/projects/{uuid}` + `POST /api/creative/projects/{uuid}/advance`
- 新建 `src/web/frontend/src/pages/{Knowledge,Schedule,Event,Database,Creative,NPS}/index.tsx`:6 管理页面 UI 框架
- 新建 `src/web/frontend/src/components/{KnowledgeGraph,ScheduleForm,EventTable,DataTable,StoryBibleViewer,NPSConfigDrawer}.tsx`:16 组件 UI 完整
- `src/web/backend/services/database_service.py`:23 表白名单 + WAL 模式双层防御(`PRAGMA journal_mode=WAL`)

**阶段 D — 调度整合(14/15 ✅)**
- 改造 `src/core/event_manager.py`:新增 `subscribe` / `publish` / `get_event_manager` API
- 改造 `src/core/background_scheduler.py:194`:每个 tick `em.publish('scheduler_tick', status_payload)`,payload 含 `life_state_snapshot` / `dream_record` / `open_loop_count` / `creative_project_count`
- 改造 `src/core/proactive_engine.py:329`:`bot_proactive_drive_send()` 改走 `em.publish('proactive_message', payload)`
- 改造 `src/web/backend/main.py:79-93`:FastAPI 启动时创建单例 EventService,`threading.Lock` 双重检查
- 新建 `src/web/backend/services/event_service.py`:`register_websocket_listener` / `unregister_websocket_listener`,订阅 `scheduler_tick` / `proactive_message` / `chat_event` / `debug_log` / `message` / 通配 `*`
- 改造 `src/tools/debug_logger.py:92-113`:新增 `subscribe` / `unsubscribe` 钩子,`set_main_loop` 支持跨线程调度
- 新建 `src/web/backend/ws/debug_broadcaster.py`:DebugLogger subscriber + EventService 'debug_log' listener 双挂,`main.py:200-219` 启动 attach,`:232-238` shutdown detach
- 改造 `src/web/backend/ws/proactive.py:55`:读取 `PROACTIVE_MESSAGE_INTERVAL` 环境变量,`_should_throttle()` 进程内节流

**阶段 E — 文档与回滚(11/19 ✅)**
- 新建 `tests/e2e/test_chat_flow.py`(5 方法)+ `test_knowledge_crud.py`(6)+ `test_proactive_push.py`(5)+ `test_websocket_reconnect.py`(9)= **25 个 E2E 测试**,全部 `@unittest.skipUnless(_DEPS_OK, _SKIP_REASON)` + `self.skipTest` 优雅降级
- 新建 `tests/perf/test_load_bench.py`:首屏字节 < 500KB / 首 token < 2s / WS ping-pong < 5s / 1000 条遍历 / 10 并发 WS
- 新建 `tests/rollback/test_rollback_procedure.py`:`TestRunTkinterMode` + `TestEnableWebGuiFlag` + `TestDbConsistency`
- 更新 `README.md:158-209` GUI 启动方式 + `:394-422` Web GUI 速查
- 新建 `docs/architecture.md`:ASCII 总体图 / WebSocket 数据流 / 模块依赖 / 并行调度 / mermaid 总览
- 新建 `docs/rollback-procedure.md`:4 步 5 分钟回滚 + 验证清单 + 5 条 FAQ + 切回 Web
- 本 `CHANGELOG.md` v3.0.0 条目(本节)
- `src/web/backend/main.py:21-29` `app = FastAPI(title="Neo Agent Web", version="3.0.0")` → `/docs` 自动 OpenAPI

#### P0 必修(阻塞正式发布)

- **前端 6 页面 mock→真接口**:`pages/{Knowledge,Schedule,Event,Database,Creative,NPS}/index.tsx` `useEffect` 改调 API,删 `TODO(后端联调)` 注释;Event 页删 `setInterval(5000ms)` 改订阅 `/ws/events`
- **新建 REST 路由**:
  - `src/web/backend/api/nps.py` — `GET /api/nps` + `POST /api/nps/register` + `POST /api/nps/invoke`
  - `src/web/backend/api/event.py` — `GET /api/events` + `POST /api/events/{event_id}/read` + `POST /api/events/{event_id}/archive`
- **`main.py` 显式 `ENABLE_WEB_GUI` 校验**:在 `_run_web` 开头检查 `os.environ.get("ENABLE_WEB_GUI", "true").lower() == "false"` 拒绝启动

#### P1 强烈建议(发布前修)

- [pages/Chat/index.tsx](../Neo_Agent/src/web/frontend/src/pages/Chat/index.tsx) 侧栏真挂载 EmotionPanel + TimelineCanvas(目前占位)
- [TimelineCanvas.tsx](../Neo_Agent/src/web/frontend/src/components/TimelineCanvas.tsx) 节点 click 接 `/api/memory/loop/{uuid}/context`
- [pages/Event/index.tsx](../Neo_Agent/src/web/frontend/src/pages/Event/index.tsx) 订阅 `scheduler_tick` 渲染"当日状态/梦境/日记/想法池"卡
- [MessageList.tsx](../Neo_Agent/src/web/frontend/src/components/MessageList.tsx) 接 `react-window` 真虚拟滚动
- `ws/__init__.py` 聚合或删除 `/ws/event` 单数端点
- `ScheduleDTO` / `EventDTO` 字段名对齐实际表(`schedule_id` / `collaboration_status` / `event_id`)
- `api/creative.py` 续写路径统一(`/api/creative/advance/{uuid}` vs `/api/creative/projects/{uuid}/advance`)
- ChatInput 加 Ctrl/Cmd+Enter 快捷键
- Layout 加 `< 768px` 移动端降级提示

#### P2 后续优化(发布后 1-2 周)

- Lighthouse 真机录制首屏 `< 3s`、FPS `≥ 50`
- 浏览器矩阵:Chrome / Edge / Firefox / Safari 最新 2 版本
- TypeScript 类型自动生成(`openapi-typescript`)
- `Settings` 页面 Web 端实现(对照 Tkinter `src/gui/settings_migration_gui.py` 530 行)
- 团队 React + AntD 培训纪要(≥1 次)
- UAT ≥ 3 个真实用户场景报告

## [2.3.0] - 2026-05-15

> **重大重构:Neo_Agent 拟人化能力与架构分层全面落地**
>
> 目标:参考 [astrbot_plugin_private_companion](https://github.com/) 拟人化设计 + 本地 [ARCHITECTURE_REFACTOR_PLAN.md](../ARCHITECTURE_REFACTOR_PLAN.md) + [INVESTIGATION_HUMANIZATION_CREATIVE.md](../INVESTIGATION_HUMANIZATION_CREATIVE.md),对 Neo_Agent 进行"分层架构 + 拟人化能力 + 数据扩展 + 工程规约"四位一体的全量重构。本次重构**不引入 Web GUI**(留待 v3.0.0),**不破坏任何既有方法**(纯扩展),**不强制启用新功能**(Feature flag 默认关闭)。

### 架构分层(Achitecture Layering)

#### Added / 新增 — 纵向四层架构
- `src/core/` — 核心业务层(LLM/记忆/知识/情感/创作/调度)
- `src/tools/` — 工具层(debug logger / 杂项 utilities)
- `src/gui/` — Tkinter 桌面 GUI 层
- `src/nps/` — Neo Plugin System 插件层
- 所有新模块以**独立文件**形式加入 `src/core/`,不复用 Mixin(规避 70K+ 单类膨胀),统一复用 `LLMHelper` / `PromptManager` / `DatabaseManager`

### 拟人化能力(Humanization Capabilities)

#### Added / 新增 — 六大核心抽象
- **生活状态机** [`src/core/life_state.py`](src/core/life_state.py)
  - 状态枚举:WAKE / WORK / REST / SLEEP / DREAM / SOCIAL / REFLECT
  - 状态转移规则 + 日快照表 `life_state_daily_snapshot`
  - 通过 `ENABLE_LIFE_STATE` Feature flag 控制
- **Plutchik 8 维情绪模型** [`src/core/emotion_analyzer.py`](src/core/emotion_analyzer.py)
  - 8 种基本情绪:joy / trust / fear / surprise / sadness / disgust / anger / anticipation
  - 与现有"印象累加评分"并行注入 prompt
  - 通过 `ENABLE_EMOTION_WHEEL` Feature flag 控制
- **长期创作系统** [`src/core/creative_writer.py`](src/core/creative_writer.py)
  - 立项 → 续写 → 完结 全生命周期
  - 质量审核:similarity ≤ 0.72、retry ≤ 2、min_score ≥ 7
  - 数据表:`creative_projects` / `creative_story_bibles` / `creative_memory_pool`(统一命名)
  - 触发:聊天不活跃 30 分钟后自动开始一轮续写
- **主动决策引擎** [`src/core/proactive_engine.py`](src/core/proactive_engine.py)
  - 想法池(idea pool)+ 触发条件评估 + 主动消息投递
  - 通过 `ENABLE_PROACTIVE_ENGINE` Feature flag 控制
- **未完话题跟踪** [`src/core/long_term_memory.py`](src/core/long_term_memory.py)
  - `OpenLoopTracker` 自动识别用户未说完的话题并打 tag
  - 数据表 `open_loops` 持久化(raised_at / closed_at / topic / entities)
- **梦境记录 + 自我时间线 + 用户习惯**
  - [`src/core/dream_diary.py`](src/core/dream_diary.py) — 梦境生成与日记
  - [`src/core/self_timeline.py`](src/core/self_timeline.py) — 自我时间线聚合
  - [`src/core/user_habits.py`](src/core/user_habits.py) — 用户习惯画像

### 提示词工程(Prompt Engineering)

#### Added / 新增 — 模块化提示词
- [`src/core/prompt_manager.py`](src/core/prompt_manager.py) — `PromptManager` 统一管理四类模板:
  - `character` — 角色人设
  - `system` — 系统级约束
  - `task` — 任务级指令
  - `worldview` — 世界观注入
- 支持 markdown 模板 + Jinja2 占位符 + 热重载
- **改造** `chat_agent.py` / `emotion_analyzer.py` / `multi_agent_coordinator.py` 改走 `PromptManager` 注入
- 角色扮演与世界观参数化(`worldview` 字段)

### 数据持久化(Database Expansion)

#### Added / 新增 — 8 张拟人化数据表
- `life_state_daily_snapshot` — 生活状态日快照(状态/时长/触发原因)
- `dream_records` — 梦境记录(主题/情绪/象征物)
- `diary_entries` — 日记条目(每日反思)
- `open_loops` — 未完话题(uuid/raised_at/closed_at/topic/entities)
- `creative_projects` — 创作项目(uuid/title/status/quality_score)
- `creative_story_bibles` — 创作圣经(角色/世界观/章节大纲)
- `creative_memory_pool` — 创作记忆池(续写上下文)
- `proactive_ideas` — 主动想法池

#### Security / 安全
- **`src/core/database_manager.py` 新增 23 表白名单 + 多个 `update_*` 方法列名白名单**
  - 业务层禁止拼接 SQL 列名 / 表名,所有动态列名经白名单校验
  - 防御 SQL 注入
  - 启用 `PRAGMA journal_mode=WAL` 支持并发读写
- **新增** [`src/core/schedule_similarity_checker.py`](src/core/schedule_similarity_checker.py) — 日程查重,避免重复创建相同日程

### 事件驱动(Event-Driven)

#### Changed / 变更
- **改造** [`src/core/event_manager.py`](src/core/event_manager.py) — 引入通知型 vs 任务型事件分类
  - 通知型:notify_user / notify_admin
  - 任务型:task_dispatch / task_complete
  - listener 异常隔离,单 listener 失败不影响其他

### 调度与线程隔离(Scheduler Isolation)

#### Added / 新增
- [`src/core/background_scheduler.py`](src/core/background_scheduler.py) — 后台调度器
  - 独立 asyncio 子线程运行,**与 Tkinter 主循环物理隔离**
  - 通过线程安全队列与 GUI 通信
  - 调度项:生活状态转移 / 梦境生成 / 创作续写 / 主动消息投递 / 话题时间衰减
  - **每个 tick 完成后通过 EventManager 发布 `scheduler_tick` 状态(payload 含 life_state_snapshot / dream_record / open_loop_count / creative_project_count)**(为 v3.0.0 Web 推送预埋接口)

### 工程规约(Hard Constraints)

#### Added / 新增 — 写入 `project_memory.md` 的硬约束
- 所有新模块必须作为独立文件添加到 `src/core/`,**不通过 Mixin 扩展既有类**
- 复用 `LLMHelper` / `PromptManager` / `DatabaseManager` 三大基础设施
- GUI 触发架构和后台调度器必须使用 asyncio 子线程**物理隔离**
- Feature flags(`ENABLE_LIFE_STATE` / `ENABLE_EMOTION_WHEEL` / `ENABLE_PROACTIVE_ENGINE` 等)**默认禁用**新功能,显式开启后才生效
- 创意项目必须包含质量审核(similarity ≤ 0.72, retry ≤ 2, min_score ≥ 7)
- 新增数据表统一命名为 `creative_projects` / `creative_story_bibles` / `creative_memory_pool`
- 长期创作项目在聊天不活跃 **30 分钟**后触发
- 情感分析统一使用 **Plutchik 8 维情绪模型**

### 文档更新(Documentation)

#### Added / 新增
- 新增 [`docs/architecture.md`](docs/architecture.md) — 整体架构图、ASCII 数据流、模块依赖、并行调度、mermaid 总览
- 新增 [`.trae/AGENTS.md`](../.trae/AGENTS.md) / [`.trae/CONTEXT.md`](../.trae/CONTEXT.md) — 智能体协作规约
- 更新 [`README.md`](README.md) — 增加拟人化能力说明 + Feature flag 配置
- 新增 [`docs/agents/`](../docs/agents/) — Hermes Agent skills 脚手架
- 调研报告 [ARCHITECTURE_REFACTOR_PLAN.md](../ARCHITECTURE_REFACTOR_PLAN.md) / [INVESTIGATION_HUMANIZATION_CREATIVE.md](../INVESTIGATION_HUMANIZATION_CREATIVE.md)

### Lessons Learned / 经验沉淀
- **Mixin 模式导致单类膨胀(70K+ 行)**:后续新能力必须以独立文件 + 组合方式扩展,不再使用 Mixin
- **Plutchik 8 维比"印象评分"更适合雷达可视化**:为 v3.0.0 Web 端 EmotionPanel 雷达图铺路
- **WAL 模式必开**:GUI 进程与后台调度进程并发读写 SQLite,WAL 是必选项
- **Feature flag 默认关闭**:生产事故多为"新功能默认开启"导致

## [2.2.0] - 2026-02-22

### 功能移除 / Features Removed
- **ConversationGraph** (`src/core/conversation_graph.py`): 删除全仓零引用的 LangGraph 对话流程管理模块（真僵尸）
- **EnhancedKnowledgeBase** (`src/core/enhanced_knowledge_base.py`): 删除仅测试在用的增强知识库封装（与 `KnowledgeBase` 职责重叠约 80%）
- **DeepAgentsKnowledgeManager** (`src/core/deepagents_wrapper.py`): 删除与 `EnhancedKnowledgeBase` 配套的虚拟文件系统知识管理器（仅被已删除模块引用，属死代码；`DeepSubAgentWrapper` 保留）

### 修正 / Corrected
- 澄清以下模块仍保留并被生产代码使用（CHANGELOG 早前版本曾错误地将其列为"已移除"，现已修正）：
  - **多智能体协作 / 动态多智能体图** (`src/core/multi_agent_coordinator.py` / `dynamic_multi_agent_graph.py`): 仍由 `chat_agent.py:22` / `:239` 等处生产在用
  - **事件系统 / 事件管理** (`src/core/event_manager.py`): 仍由 `chat_agent.py:20` + `gui_enhanced.py` 20+ 处密集调用
  - **LangGraph 集成**: `dynamic_multi_agent_graph.py` 仍使用 LangGraph `StateGraph` / `MemorySaver`，仅 `conversation_graph.py` 为真僵尸并已删除

### 文档更新 / Documentation Updates
- **修正 README.md**，移除已不存在功能的描述
- **优化文档结构**，提高可读性和维护性
- **更正 `src/core/__init__.py` 文档字符串**：`ScheduleGenerator` → `TemporaryScheduleGenerator`（实际类名），并澄清 Usage 块中 import 行为为示例

### 改进 / Improved
- ✅ 项目结构更加简洁
- ✅ 代码库更加易于维护
- ✅ 文档与实际功能保持一致

## [2.1.0] - 2026-02-22

### 项目结构优化 / Project Structure Optimization
- **清理临时文件 / Removed temporary files**
  - 删除版本号文件（=0.2.0, =0.3.0, =3.9.0）
  - 删除比较文件（VISUAL_COMPARISON.txt）
- **文档归档 / Documentation Archiving**
  - 将所有非核心md文件移动到docs目录
  - 保留README.md、CHANGELOG.md和LICENSE在根目录
  - 归档的文档包括：API.md、ARCHITECTURE.md、CONTRIBUTING.md等

### 文档更新 / Documentation Updates
- **重写README.md**，更新架构描述和特性列表
- **优化文档结构**，提高可读性和维护性
- **统一文档风格**，确保一致性

### 改进 / Improved
- ✅ 项目结构更加清晰整洁
- ✅ 文档管理更加规范
- ✅ 代码库更加易于维护

## [2.0.0] - 2026-02-09

### 重大更新 🎉 Major Update

#### 复合框架架构 / Composite Framework Architecture
- **引入LangChain + LangGraph复合框架 / Introduced LangChain + LangGraph Composite Framework**
  - LangChain作为核心框架提供LLM抽象 / LangChain as core framework providing LLM abstraction
  - LangGraph用于状态图管理和对话流程编排 / LangGraph for state graph management and conversation orchestration
  - 创建ConversationGraph基础框架 / Created ConversationGraph base framework

#### 多层模型架构 / Multi-tier Model Architecture
- **实现三层模型系统 / Implemented three-tier model system**
  - 主模型 (deepseek-ai/DeepSeek-V3.2): 处理主要对话和复杂推理 / Main model for primary conversations and complex reasoning
  - 工具模型 (zai-org/GLM-4.6V): 处理轻量级任务 / Tool model for lightweight tasks
  - 多模态模型 (Qwen/Qwen3-VL-32B-Instruct): 预留多模态处理 / Multimodal model reserved for future use

### Added / 新增
- **ModelConfig** (`model_config.py`): 多层模型配置管理 / Multi-tier model configuration management
- **LangChainLLM** (`langchain_llm.py`): LangChain封装，支持模型路由 / LangChain wrapper with model routing
- **ModelRouter** (`langchain_llm.py`): 智能模型路由器 / Intelligent model router
- **LLMHelper** (`llm_helper.py`): 简化工具级任务的LLM调用 / Simplified LLM calls for tool-level tasks
- **ConversationGraph** (`conversation_graph.py`): LangGraph对话流程管理 / LangGraph conversation flow management
- **ARCHITECTURE.md**: 详细的架构文档 / Detailed architecture documentation

### Changed / 变更
- **SiliconFlowLLM**: 重构为兼容层，内部使用LangChain / Refactored as compatibility layer using LangChain internally
- **SubAgent**: 使用工具模型处理子任务 / Uses tool model for sub-tasks
- **EmotionRelationshipAnalyzer**: 使用工具模型进行情感分析 / Uses tool model for emotion analysis
- **KnowledgeBase**: 使用工具模型进行知识提取 / Uses tool model for knowledge extraction
- 更新`requirements.txt`，添加LangGraph和相关依赖 / Updated requirements.txt with LangGraph dependencies
- 更新`example.env`，新增多层模型配置 / Updated example.env with multi-tier model configurations
- 更新README.md，说明新架构 / Updated README.md explaining new architecture

### Improved / 改进
- ✅ 所有模块统一使用LangChain架构 / All modules now use LangChain architecture
- ✅ 轻量级任务使用工具模型，降低成本 / Lightweight tasks use tool model, reducing costs
- ✅ 保持完全向后兼容 / Maintains full backward compatibility
- ✅ 代码更加模块化和可维护 / More modular and maintainable code

---

## [1.0.0] - 2026-01-31

### Added / 新增

- 项目重构为标准Python包结构
- 创建了清晰的模块划分（core, gui, tools, nps）
- 添加主入口点 main.py
- 完善的包初始化文件和模块导出
- 新的项目文档（README, CONTRIBUTING）

### Changed / 变更

- 将所有源代码移至 src/ 目录
- 重新组织核心模块到 src/core/
- 重新组织GUI模块到 src/gui/
- 重新组织工具模块到 src/tools/
- 移动NPS系统到 src/nps/
- 移动示例代码到 examples/
- 统一测试文件到 tests/
- 更新所有import路径以反映新结构

### Removed / 移除

- 删除临时说明文档
- 清理过时的markdown文档
- 移除根目录下的散乱文件

### Technical / 技术细节

- 实现模块化包结构
- 改进代码组织和可维护性
- 标准化项目布局
- 简化部署和安装流程

---

## 版本说明 / Version Notes

版本号遵循 [语义化版本](https://semver.org/lang/zh-CN/) 规范：

- 主版本号：不兼容的API变更
- 次版本号：向下兼容的功能新增
- 修订号：向下兼容的问题修正

Version numbers follow [Semantic Versioning](https://semver.org/):

- MAJOR: Incompatible API changes
- MINOR: Backward compatible functionality additions
- PATCH: Backward compatible bug fixes
