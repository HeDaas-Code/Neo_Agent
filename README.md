# Neo Agent · Agentic 虚拟群友

Neo Agent 已完成从单体 Tkinter/SQLite 程序到原子化、插件化虚拟群友运行时的主架构迁移。当前主线使用 **Textual TUI + LangChain + PyVDisk**，旧 Tk/SQLite/NPS 运行路径与源码已移除；不提供旧数据兼容层。

## 开发分支

当前重构分支：`Dev`。

## 快速开始

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp example.env .env  # 按需填写模型服务配置
python main.py
```

默认数据镜像为 `~/.neo-agent/runtime.vdisk`，可通过 `NEO_VDISK_PATH` 改写。终端内使用方向键选择模块、Enter 进入，数字键快速跳转、`r` 刷新、`q` 退出。

## 新运行时边界

- `neo_agent/ui/`：全局运营控制台与交互导航。
- `neo_agent/storage/`：唯一持久化边界；`DiskStore` 使用 PyVDisk AgentSandbox 的受限接口。
- `neo_agent/tools/`：把 PyVDisk 审计/授权过的 JSON Schema 工具转换成 LangChain `StructuredTool`。
- `neo_agent/runtime/`：LangChain 有界工具调用循环与可持久化对话记录。
- `characters/<id>/profile.json`、`groups/<id>/`、`runtime/`：虚拟角色、群组及运行检查点所在的 DataDisk 命名空间。
- `main.py`、`run.py`：仅启动新 TUI，不再启动 Tk GUI。

PyVDisk 是 Git 依赖，工作树版本来自 `HeDaas-Code/pyvdisk`；其 DataDisk/VFS/Vector/Log/WAL 与 AgentSandbox 构成唯一存储及工具执行基础。镜像容器内部细节由 PyVDisk 管理，Neo Agent 不另行使用 sqlite 或裸文件做运行时持久化。

## 模块地图与后续开发方向

旧 GUI 管理功能已按迁移矩阵纳入 Textual 控制台与领域服务；新运行时覆盖角色、会话、记忆/知识、关系/情绪、环境/域、事件、日程、表达、协作、配置和新版 NPS。持久化统一走 PyVDisk，Agent 编排与工具采用 LangChain。迁移矩阵、现存产品能力边界以及下一阶段深化建议见 [`docs/PRODUCT_ROADMAP.md`](docs/PRODUCT_ROADMAP.md)。
