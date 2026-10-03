# Neo Agent 2.x 技术架构

> 本文描述当前唯一受支持的运行时。旧 Tk/SQLite/NPS 源码、旧测试和旧 GUI 校验脚本已移除；本项目不提供旧 API 或数据格式兼容。后续产品路线见 [`docs/PRODUCT_ROADMAP.md`](docs/PRODUCT_ROADMAP.md)。

## 产品边界

Neo Agent 的目标是可配置、可组合、能在群聊中自然互动的虚拟群友 Agentic。运行时采用 LangChain 的模型与工具协议，管理界面采用 Textual TUI，唯一运行时持久化边界为 PyVDisk 的 DataDisk 公共 API。Neo Agent 不直接打开 PyVDisk 镜像结构、不自建 SQLite/主机目录持久化，也不为旧数据格式提供兼容。

## 当前模块

| 模块 | 职责 |
|---|---|
| `neo_agent/ui/tui.py` | 全局运营控制台：角色、对话、事件、日程、知识、关系、环境/域、插件、审计、记忆、频道、配置、实体、表达风格和协作流程。 |
| `neo_agent/storage/disk_store.py`、`vfs_workspace.py` | PyVDisk `AgentSandbox` 适配、领域文档、向量记忆、LogDisk 事件、检查点/持久队列、日程和事件/任务专属 VFS 工作区。 |
| `neo_agent/runtime/agent.py` | 有界 LangChain 工具调用、上下文组合及会话/记忆写入。 |
| `neo_agent/runtime/domain_services.py` | 知识、记忆、关系、环境/域、频道等领域服务。 |
| `neo_agent/runtime/emotion.py`、`expression.py` | 关系情绪分析和表达风格/用户习惯学习。 |
| `neo_agent/runtime/scheduler.py`、`neo_agent/services/scheduling.py` | 到期队列 worker、日程规划建议和人机协作提醒服务。 |
| `neo_agent/plugins/` | 原子插件契约、注册表、PyVDisk 工具和日程事件插件。 |
| `neo_agent/nps/runtime.py` | `neo.nps/v1` manifest、VScript 主控与受限 Python 扩展桥。 |
| `main.py`、`neo_agent/__main__.py` | TUI 入口；启动与关闭 DataDisk 资源。 |
| `tests/v2/` | 新运行时服务、持久化重开、TUI Pilot、队列、权限/审计及插件测试。 |

## 运行数据流

```text
Textual 操作员 / 群消息入口（平台 adapter 尚待建设）
    → AgentRuntime
    → LangChain Model + 已授权的工具
    → PluginRegistry / PyVDisk AgentSandbox
    → PyVDisk DataDisk FS / Vector / Log / Checkpoint / DurableQueue
```

- 对话、角色及领域实体以 PyVDisk 管理的文档形式保存。
- 语义记忆使用 PyVDisk 向量 API；事件及可审计运行轨迹写入 LogDisk。
- 可管理事件记录和工作流任务的附属文件分别限定在 `/workspaces/events/{id}` 与 `/workspaces/tasks/{id}`；只能通过 `VFSWorkspace` 相对路径 API 访问，拒绝绝对路径和目录穿越，不存在主机文件系统回退。
- 日程通知经持久队列调度；队列状态、尝试、失败和完成应可审计。
- 外部消息发送尚未闭环；当前“已投递到待发送/outbox”状态不等价于外部平台送达。
- 密钥通过环境变量注入，不能写入频道公开配置或配置导出。
- 事件/任务工作区严格位于 PyVDisk 镜像内的 DataDisk VFS；禁止使用宿主机目录、临时文件、SQLite 或绝对路径承载/操作其工作产物。只有镜像本身可由启动配置指定主机路径。

## 插件与隔离

新版 NPS bundle 格式为 `neo.nps/v1`。Manifest 描述工具参数 schema 与 capability；VScript 作为主控语言。可选 Python 扩展只有在显式声明 `python.call` 后才运行，并通过独立受限进程/隔离机制调用。导入、启停、一次性测试、删除、导出和执行应保留审计记录。旧 `.NPS` 格式不兼容。插件不得通过普通 Python 代码绕开 AgentSandbox 的 capability 边界。

## 本地开发

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
cp example.env .env  # 按需设置模型凭据与模型名
python -m neo_agent   # 或 python main.py
```

默认镜像路径是 `~/.neo-agent/runtime.vdisk`，可用 `NEO_VDISK_PATH` 覆盖。测试与静态检查：

```bash
.venv/bin/python -m pytest -q
.venv/bin/python -m compileall -q neo_agent tests/v2
git diff --check
```

当前 pytest 配置仅发现新架构测试 `tests/v2/`。旧功能迁移矩阵已核对，旧运行路径与旧测试已清理；产品深化项目（群平台接入、主动发言仲裁、自动记忆学习等）属于后续能力，不是旧模块兼容目标。

## 功能深化方向

迁移闭环后，产品开发建议按离线群聊模拟器 → 关系/记忆审核工作台 → 单平台人工确认的真实群聊闭环推进；再深化主动发言仲裁、多群关系、圈内语言审核学习和多模态表达。详见产品路线图。
