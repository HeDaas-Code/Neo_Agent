# Neo Agent 模块清单

## 📦 当前系统模块总览

### 🎨 用户界面层（UI Layer）

#### TUI v2 核心
```
neo_agent/ui/v2/
├── app.py                    ✅ 主应用（600+ 行）
│   ├── NeoAgentApp           - Textual 应用类
│   ├── StatusBar             - 顶部状态栏
│   ├── NavigationPanel       - 左侧导航栏
│   ├── MainContent           - 主内容区
│   └── Footer                - 底部状态栏
│
├── theme.py                  ✅ 琥珀主题系统
│   ├── AMBER_THEME_CSS       - 5级深度配色
│   └── 组件样式              - 按钮、输入框、表格等
│
├── commands.py               ✅ 命令系统
│   ├── CommandPalette        - 命令面板
│   ├── ConfigPanel           - 配置界面
│   ├── ExportPanel           - 导出界面
│   └── ImportPanel           - 导入界面
│
├── client.py                 ✅ RPC 客户端
│   └── AgentClient           - JSON-RPC 2.0 客户端
│
├── websocket_client.py       ✅ WebSocket 客户端
│   └── WebSocketClient       - 事件监听器
│
└── event_handlers.py         ✅ 事件处理器
    └── EventHandlers         - 8种事件自动刷新视图
```

#### 视图组件（Views）
```
已实现的 6 个视图（内嵌于 app.py）:

1. ChatView               ✅ 对话视图
   - 消息历史展示
   - 多行输入框
   - 实时回复

2. ItineraryView          ✅ 今日行程
   - 时间线展示
   - 行程类型标识
   - 场景绑定

3. ScenePoolView          ✅ 场景池
   - 场景列表
   - 详情展示
   - 当前高亮

4. MemoryView             ✅ 记忆与知识
   - 搜索功能
   - 结果列表

5. RelationshipView       ✅ 关系网络
   - 关系列表
   - 分数显示

6. AuditView              ✅ 审计日志
   - 时间倒序
   - 风险标识
```

---

### 🔧 服务层（Service Layer）

#### 守护进程
```
neo_agent/service/
├── daemon.py                 ✅ 守护进程服务
│   ├── start_daemon()        - 启动服务
│   ├── stop_daemon()         - 停止服务
│   └── get_status()          - 查询状态
│
├── rpc_handlers.py           ✅ RPC API 处理器（12 个方法）
│   ├── session.*             - 会话管理（3 个）
│   ├── character.*           - 角色管理（2 个）
│   ├── schedule.*            - 日程管理（1 个）
│   ├── scene.*               - 场景管理（2 个）
│   ├── memory.*              - 记忆管理（1 个）
│   ├── relationship.*        - 关系管理（2 个）
│   ├── emotion.*             - 情绪管理（1 个）
│   └── system.*              - 系统控制（4 个）
│
└── events.py                 ✅ WebSocket 事件（8 种）
    ├── scene_changed
    ├── emotion_updated
    ├── message_received
    ├── schedule_triggered
    ├── relationship_changed
    ├── daily_itinerary_generated
    ├── system_status_changed
    └── audit_logged
```

---

### 🧠 运行时层（Runtime Layer）

#### Agent 核心
```
neo_agent/runtime/
├── agent.py                  ✅ Agent 主控
│   ├── ThreeStageAgent       - 三阶段 Agent
│   ├── cognition_stage()     - 认知决策
│   ├── execution_stage()     - 操作执行
│   └── expression_stage()    - 语言表达
│
├── cognition.py              ⚠️  认知门控（60% 完成）
│   ├── CognitionDecision     - 决策结构
│   ├── ActionResult          - 执行结果
│   ├── ReplyCandidate        - 回复候选
│   └── CognitionService      - 认知服务
│
├── emotion.py                ✅ 情绪系统
│   ├── EmotionState          - 情绪状态
│   └── EmotionService        - 情绪服务
│
├── expression.py             ✅ 表达系统
│   └── ExpressionService     - 语言生成服务
│
├── itinerary.py              ⚠️  日程系统（50% 完成）
│   ├── DailyItineraryService - 每日行程生成
│   └── ScheduleService       - 日程管理
│
└── scene.py                  ⚠️  场景系统（50% 完成）
    ├── SceneService          - 场景管理
    └── SceneScheduler        - 场景调度
```

#### 记忆与知识
```
neo_agent/memory/
├── memory_service.py         ✅ 记忆服务
│   ├── ShortTermMemory       - 短期记忆
│   ├── LongTermMemory        - 长期记忆
│   └── VectorStore           - 向量存储
│
└── knowledge_service.py      ⚠️  知识服务（基础实现）
    └── KnowledgeBase         - 知识库
```

#### 关系与社交
```
neo_agent/social/
├── relationship.py           ✅ 关系系统
│   ├── RelationshipGraph     - 关系图谱
│   └── RelationshipService   - 关系服务
│
└── conversation.py           ✅ 会话管理
    └── ConversationService   - 会话服务
```

---

### 💾 持久化层（Persistence Layer）

#### PyVDisk 集成
```
neo_agent/storage/
├── disk_store.py             ✅ 存储抽象层
│   ├── DiskStore             - PyVDisk 封装
│   ├── save_character()      - 角色存储
│   ├── load_character()      - 角色加载
│   ├── save_memory()         - 记忆存储
│   └── save_relationship()   - 关系存储
│
└── models.py                 ✅ 数据模型
    ├── Character             - 角色模型
    ├── Message               - 消息模型
    ├── Memory                - 记忆模型
    ├── Relationship          - 关系模型
    ├── Scene                 - 场景模型
    └── Schedule              - 日程模型
```

---

### 🔌 插件系统（Plugin System）

#### NPS 插件（待实现）
```
neo_agent/plugins/
├── nps_manager.py            ⏳ NPS 管理器
│   ├── load_plugin()         - 加载插件
│   ├── validate_plugin()     - 校验插件
│   └── execute_plugin()      - 执行插件
│
├── vscript_runtime.py        ⏳ VScript 运行时
│   └── VScriptInterpreter    - VScript 解释器
│
└── python_bridge.py          ⏳ Python 桥接
    └── PythonExecutor        - 隔离 Python 执行
```

---

### 🛠️ 工具与辅助（Utilities）

#### 工具集
```
neo_agent/tools/
├── langchain_tools.py        ✅ LangChain 工具集成
│   ├── FileTool              - 文件操作
│   ├── WebSearchTool         - 网络搜索
│   └── CustomTool            - 自定义工具
│
└── capability_checker.py     ⏳ 能力校验器
    └── CapabilityChecker     - 权限检查
```

#### 配置与日志
```
neo_agent/config/
├── config.py                 ✅ 配置管理
│   └── Config                - 全局配置
│
└── logging.py                ✅ 日志系统
    └── setup_logging()       - 日志初始化
```

---

### 🧪 测试（Tests）

#### 集成测试
```
tests/
├── test_simple_integration.py    ✅ 核心功能测试
├── test_click_navigation.py      ✅ 导航测试
├── test_command_panel.py         ✅ 命令面板测试
├── test_view_switching.py        ✅ 视图切换测试
└── demo_all_views.py             ✅ 功能演示
```

---

### 📄 入口与脚本（Entry Points）

```
根目录/
├── main.py                   ✅ 主入口
│   ├── start                 - 启动服务
│   ├── stop                  - 停止服务
│   ├── restart               - 重启服务
│   ├── status                - 查询状态
│   └── tui                   - 启动 TUI
│
└── requirements.txt          ✅ 依赖清单
    ├── textual >= 0.80.0
    ├── langchain
    ├── aiohttp
    ├── python-daemon
    └── pyvdisk
```

---

## 📊 模块统计

### 按层级分类

| 层级 | 模块数 | 完成度 |
|------|--------|--------|
| UI 层 | 6 | 100% ✅ |
| 服务层 | 3 | 100% ✅ |
| 运行时层 | 8 | 70% ⚠️ |
| 持久化层 | 2 | 80% ⚠️ |
| 插件系统 | 3 | 0% ⏳ |
| 工具辅助 | 3 | 60% ⚠️ |
| 测试 | 5 | 70% ⚠️ |

**总计**: 30 个模块，总体完成度 78%

### 按状态分类

| 状态 | 模块数 | 占比 |
|------|--------|------|
| ✅ 已完成 | 20 | 67% |
| ⚠️ 部分完成 | 7 | 23% |
| ⏳ 待实现 | 3 | 10% |

---

## 🔄 模块依赖关系

```
┌─────────────────────────────────────────────────────────────┐
│                         用户界面层                            │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │ TUI v2   │  │  主题    │  │  命令    │  │  事件    │   │
│  └────┬─────┘  └──────────┘  └──────────┘  └────┬─────┘   │
│       │                                          │         │
└───────┼──────────────────────────────────────────┼─────────┘
        │                                          │
        ▼                                          ▼
┌─────────────────────────────────────────────────────────────┐
│                         服务层                                │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐                   │
│  │ RPC API  │◄─┤  守护进程 │─►│ WebSocket│                   │
│  └────┬─────┘  └──────────┘  └──────────┘                   │
│       │                                                      │
└───────┼──────────────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────────────────────┐
│                       运行时层                                │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │  Agent   │◄─┤  认知    │─►│  执行    │─►│  表达    │   │
│  └────┬─────┘  └──────────┘  └──────────┘  └──────────┘   │
│       │                                                      │
│       ├──────►┌──────────┐  ┌──────────┐  ┌──────────┐    │
│       │       │  记忆    │  │  知识    │  │  关系    │    │
│       │       └──────────┘  └──────────┘  └──────────┘    │
│       │                                                      │
│       └──────►┌──────────┐  ┌──────────┐                   │
│               │  日程    │  │  场景    │                   │
│               └──────────┘  └──────────┘                   │
└───────┬──────────────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────────────────────┐
│                       持久化层                                │
│  ┌──────────┐  ┌──────────┐                                 │
│  │ DiskStore│◄─┤ PyVDisk  │                                 │
│  └──────────┘  └──────────┘                                 │
└─────────────────────────────────────────────────────────────┘
```

---

## 🎯 下一步开发优先级

### P0（必须完成）
1. **认知门控三阶段隔离** → `neo_agent/runtime/cognition.py`
2. **日程自动生成** → `neo_agent/runtime/itinerary.py`
3. **场景自动生成** → `neo_agent/runtime/scene.py`

### P1（尽快完成）
4. **Agent 自动创作** → 各运行时模块
5. **能力校验器** → `neo_agent/tools/capability_checker.py`
6. **知识库完善** → `neo_agent/memory/knowledge_service.py`

### P2（计划中）
7. **NPS 插件系统** → `neo_agent/plugins/`
8. **旧代码清理** → 删除 `neo_agent/ui/tui.py`
9. **文档完善** → `TECHNICAL.md`, `API.md`, `PLUGIN.md`

---

## 📝 模块命名规范

### 文件命名
- 小写 + 下划线：`memory_service.py`
- 模块名即功能名：`cognition.py` → 认知模块

### 类命名
- 大驼峰：`CognitionService`
- 描述职责：`DailyItineraryService`

### 函数命名
- 小写 + 下划线：`get_current_scene()`
- 动词开头：`save_character()`, `load_memory()`

---

**最后更新**: 2026-10-05  
**模块总数**: 30  
**完成度**: 78%
