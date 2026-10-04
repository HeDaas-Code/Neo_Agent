# Neo Agent API（新运行时）

本文档描述 Neo Agent 2.x 的当前公开边界。主运行时由 Textual 控制台、LangChain Agent/Tool 协议和 PyVDisk DataDisk 构成。持久数据只能通过 `DiskStore`/PyVDisk 公共 API 访问；本 API 不提供旧 Tk、SQLite 或旧 `.NPS` 入口，也不读取旧版数据文件。

> 旧 Tk/SQLite/NPS 运行路径已移除；本仓库不提供旧数据格式兼容或导入。已迁移能力和后续产品深化范围见 [`docs/PRODUCT_ROADMAP.md`](docs/PRODUCT_ROADMAP.md)。

## 启动控制台

```bash
python -m neo_agent
# 或
python main.py
```

```python
import os

from neo_agent.storage import DiskStore
from neo_agent.ui.tui import NeoConsole

store = DiskStore.open(os.path.expanduser("~/.neo-agent/runtime.vdisk"))
try:
    NeoConsole(store).run()
finally:
    store.close()
```

`DiskStore.open()` 会创建或重新打开 PyVDisk 镜像。生产启动由 `main.py` 读取 `NEO_VDISK_PATH`；如果镜像无法打开，应向操作者报告错误，不要回退到 SQLite 或主机目录文件。

## 持久化边界：`DiskStore`

```python
from neo_agent.storage import DiskStore

store = DiskStore.open("/data/neo-agent.vdisk")
try:
    store.save_character("mika", {
        "name": "米卡", "personality": "活泼、友善", "status": "active",
    })
    character = store.character("mika")
    active_characters = store.characters()

    store.append_event("operator.note", {"text": "角色档案已核对"})
    recent_events = store.query_events(event_type="operator.note", limit=20)
finally:
    store.close()
```

主要操作族：

- 角色：`save_character`、`character`、`characters`、`archive_character`。
- 领域文档：`list_documents`、`get_document`、`save_document`、`delete_document`。命名空间由领域服务限定，例如 `knowledge`、`relationships`、`environments`、`domains`、`channels`、`entities`。
- 事件和审计：`append_event`、`events`、`query_events`、`runtime_logs`、`clear_runtime_log_view`。清除运行记录视图只推进可见水位，不删除不可变审计日志。
- 会话/记忆：`add_short_term_message`、`short_term_messages`、`clear_short_term`、`conversation_transcripts`、`delete_conversation`、`add_long_term_summary`、`long_term_summaries`、`save_memory`。
- 日程：`create_schedule`、`get_schedule`、`update_schedule`、`delete_schedule`、`schedules`、`schedules_in_range`、`schedule_conflicts`、`schedule_statistics`。
- 生命周期：使用 `close()` 关闭 PyVDisk 资源。

这些方法均经由 PyVDisk AgentSandbox、DataDisk FS/Vector/Log/Checkpoint/Queue API 工作。业务模块不得直接解析镜像、创建主机端运行时文件或自行引入另一套数据库。

### 事件与任务 VFS 工作区

事件和工作流文档会自动带有固定的 `workspace` VFS 路径：事件位于 `/workspaces/events/{event_id}`，任务/工作流位于 `/workspaces/tasks/{task_id}`。路径由 `DiskStore` 生成，写入文档时会覆盖调用方提交的 `workspace` 字段，不能将其改指到主机路径或其他命名空间。

```python
event_files = store.event_workspace("event-42")
event_files.write_json("agenda/brief.json", {"title": "周末活动"})
print(event_files.list_files())  # 相对工作区根的文件路径

# MultiAgentCoordinator 创建任务后，workflow["workspace"] 指向其 VFS 工作区。
task_files = store.task_workspace("task-42")
task_files.write_text("outputs/summary.md", "完成记录")
```

`VFSWorkspace` 提供 `ensure_directory`、`read_text` / `write_text`、`read_json` / `write_json`、`list_files`、`exists` 与 `delete`。这些操作只经过 PyVDisk `AgentSandbox`，文件留在镜像内的 VFS；工作区 API 不接受绝对路径、`.` / `..`、反斜线或空路径组件，且不能删除/读写工作区根本身。事件与任务管理代码不得使用 `open()`、`pathlib`、shell 或其他主机文件接口操作工作区。镜像文件所在的主机目录仅用于 PyVDisk 打开镜像，不等同于工作区。

## Agent 对话：`AgentRuntime`

```python
from neo_agent.runtime import AgentRuntime
from neo_agent.storage import DiskStore

store = DiskStore.open("/data/neo-agent.vdisk")
try:
    agent = AgentRuntime(store)  # 默认从环境变量配置 LangChain ChatOpenAI
    answer = agent.chat(
        "今天群里聊了什么？",
        conversation_id="group_42",
        system_prompt="你是群友小米，表达自然、友好。",
    )
    print(answer)
finally:
    store.close()
```

`AgentRuntime` 在 LangChain 消息/工具协议上运行有界工具调用循环；可注入实现 `bind_tools()`/`invoke()` 的模型用于测试。`chat()` 将对话记录写回 PyVDisk，并可使用近期上下文、语义记忆和表达风格。模型凭据通过环境变量配置，不应写入角色、频道或配置导出文档。

## 领域服务

服务位于 `neo_agent.runtime`，以 `DiskStore` 为唯一持久化依赖：

```python
from neo_agent.runtime import (
    ChannelService, DomainRegistry, EmotionService, EnvironmentService,
    ExpressionService, KnowledgeService, MemoryService, RelationshipService,
)

knowledge = KnowledgeService(store)
knowledge.save("python-basics", {"title": "Python", "content": "一种编程语言"})
results = knowledge.search("编程")

memory = MemoryService(store)
row = memory.remember("小米喜欢桌游", character_id="mika", metadata={"source": "reviewed"})
recall = memory.recall("桌游", character_id="mika")
memory.forget(row["id"])

relationship = RelationshipService(store)
relationship.record_interaction("mika:user-7", note="一起讨论桌游", delta=1.5)
```

`EnvironmentService` 提供环境、环境物体、连接关系、可移动性和视觉使用审计；`DomainRegistry` 管理域成员与当前域；`EmotionService` 保存关系情绪分析结果；`ExpressionService` 管理表达风格和用户习惯；`ChannelService` 管理新格式频道配置。服务层的实际方法签名以对应模块为准，TUI 是当前完整的人工操作入口。

## 日程、行程与场景

日程是角色生活状态和对话上下文，不是提醒工具。系统不投递、不暂存提醒，也没有日程 outbox/通知队列。日程分为 Agent 个人、用户个人（只读信息）和双方共同活动；用户记录不可被 Agent 修改，且只有 Agent 与共同活动可以驱动场景。

```python
from datetime import datetime
from neo_agent.runtime import (
    DailyItineraryService, SceneService, SceneScheduler, ScheduleDecisionService,
)

scenes = SceneService(store)
scenes.ensure_initial_environment()  # 幂等创建“日常起点”地点、区域和物件
itinerary = DailyItineraryService(store, scene_service=scenes)
plan = itinerary.ensure_for_day(now=datetime.now().astimezone())
# TUI 启动时与运行中由 scheduler 补齐计划、协调冲突并切换当前场景
scheduler = SceneScheduler(store, scenes=scenes)
actions = scheduler.run_once()  # 从唯一活动角色读取角色设定
print(scenes.current_context())
```

每日计划按机器本地时区及本地日期幂等保存；持续运行时于当地 00:05 生成新一天计划，TUI 启动恢复会立即补齐缺失计划。迟启动时仅物化尚未结束的活动，失败状态包含错误、重试时间和尝试次数。地点、区域、物件、行程与审计均通过 `DiskStore` / PyVDisk VFS 文档 API 持久化。未访问场景为待用场景；首次进入后地点布局固定，之后可持续记录物件状态变化。已访问地点构成可复用的场景池。

`ScheduleDecisionService` 为共同活动冲突生成结构化自主决定，只可调整/取消 Agent 自己或共同活动，不修改用户个人日程；决定摘要及审计可在 TUI 查看。`SceneScheduler` 在启动恢复并按到期时间切换到绑定场景；没有结束时间的地点活动持续至下一条场景日程，最迟当地日终回到初始环境。用户日程和无场景绑定的既有记录不驱动场景。

`SchedulePlanningService` 可用于把自然语言解析为日程建议，但建议本身不创建提醒。自然语言缺少足够日期、时间、标题或参与方信息时应先澄清。

人工新增/编辑入口仅在 Debug 开启时显示；Agent 自动创作仍按已启用工具能力执行，不受 Debug 开关限制。

## 插件与新版 NPS

基础插件契约位于 `neo_agent.plugins`：`AgentPlugin`、`PluginManifest`、`PluginContext`、`PluginRegistry`。工具必须声明能力，执行结果通过 PyVDisk sandbox 授权和审计。

NPS v1 使用新版 JSON bundle；VScript 为主控，可声明 `python.call` 后通过受限子进程桥接 Python 扩展。`.NPS` 旧格式不支持。

```python
import json
from neo_agent.nps import NPSManager

manager = NPSManager(store)
bundle = {
    "format": "neo.nps/v1",
    "manifest": {
        "id": "example.echo", "name": "Echo", "version": "1.0.0",
        "description": "Return the supplied message",
        "entrypoint": "main",
        "parameters": {
            "type": "object",
            "properties": {"message": {"type": "string"}},
            "required": ["message"],
        },
    },
    "vscript": 'language "1.0"; fn main(args) { return args; }',
}
manager.validate_bundle(bundle)
manager.save(bundle, enabled=True)
result = manager.invoke("example.echo", {"message": "hello"})
serialized = manager.export_json("example.echo")
manager.import_json(serialized, enabled=False)
```

`test_bundle(bundle, args)` 执行临时测试，不安装、不覆盖已安装版本；`langchain_tools()` 将启用的 NPS 暴露为 LangChain 工具。声明能力不足、参数不符合 schema、沙箱超时或扩展执行失败时应视为明确错误，且执行尝试会记录审计事件。

## 配置包校验、预览与导入导出

```python
from neo_agent.runtime import ConfigurationService

config = ConfigurationService(store)
bundle = config.export()                    # neo-agent/config/v2；递归过滤密钥字段
knowledge_only = config.export(categories=["knowledge"])
preview = config.preview(bundle)            # 校验并返回类别/记录数量，不写入数据盘
counts = config.import_config(bundle, categories=["characters", "knowledge"])
```

配置包不是 PyVDisk 镜像快照，也不包含事件日志或会话 transcript；它可包含记忆片段、摘要、关系等领域数据。导入前可在 TUI 查看计数。整个 bundle 会先验证格式、记录结构、ID、重复项和密钥字段，再开始写入；底层 PyVDisk 不提供跨多个领域文档的事务，因此发生存储故障时不承诺多记录写入原子回滚。
`categories` 支持 `characters` 及 `ConfigurationService.COLLECTIONS` 中的稳定类别名；遗漏时默认为全部，空列表或未知类别会被拒绝。即使只选择部分类别，导入也会先校验整个 bundle，再仅写入被选类别。TUI 的类别选择同时用于导入和导出。

## Textual 控制台

`NeoConsole(store)` 是统一管理入口，覆盖总览、虚拟群友、对话、事件、日程、知识、关系、环境/域、插件/NPS、运行记录、存储/记忆、频道、配置、实体、表达风格、人机协作和任务编排。`r` 刷新，`q` 退出；导航侧栏显示页面快捷键。敏感操作需要显式确认，错误在控制台状态区域反馈。

## 异常与安全约束

- 输入错误：`ValueError`；缺失记录：通常为 `KeyError` 或 `None`，以具体方法契约为准。
- 不吞掉 PyVDisk、模型或插件执行故障；由调用层转换为可操作的错误消息，同时保留审计证据。
- 不在配置导出中包含密钥；通过环境变量或未来接入的受管凭据服务提供密钥。
- 不直接调用任意主机 shell/文件读写来绕过 PyVDisk capability、NPS 隔离或工具审计。
- 不依赖任何旧 `src.*` 导入路径、Tk API、SQLite 管理 API 或旧插件包格式。

## 配套说明

- [产品迁移状态与深化路线图](docs/PRODUCT_ROADMAP.md)
- [项目运行与开发说明](README.md)
