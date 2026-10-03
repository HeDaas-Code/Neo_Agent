# Neo Agent 开发约定

## 当前主线

Neo Agent 已迁移为原子化、插件化的虚拟群友 Agentic。受支持运行时由 Python 3.10+、Textual TUI、LangChain 和 PyVDisk DataDisk 组成。`neo_agent/` 是唯一应用运行路径。

## 架构边界

- `neo_agent/ui/`：全局 Textual 运营控制台；交互通过领域服务，不把业务逻辑塞进 widget 回调。
- `neo_agent/runtime/`、`neo_agent/services/`：Agent 编排、领域服务、日程/人机协作流程。
- `neo_agent/plugins/`、`neo_agent/nps/`：声明式 capability、LangChain 工具及新版 `neo.nps/v1`。VScript 主控，可选 Python 扩展必须经过隔离桥和审计。
- `neo_agent/storage/`：唯一应用持久化边界，使用 PyVDisk 公开的 AgentSandbox、DataDisk FS/Vector/Log/Checkpoint/Queue API。
- 不得在 Neo Agent 运行时直接使用 SQLite、裸主机文件持久化、PyVDisk 镜像内部结构或不受限 shell 来绕过存储/工具权限。
- 不迁移、不读取旧 SQLite/JSON/NPS 数据，不提供旧格式兼容层。密钥通过环境变量等受控机制提供，不写入数据导出。

## 代码与测试

- Python 3.10+，遵循 PEP 8，公共 API 增加类型提示和清晰 docstring。
- 注释与用户可见错误可使用中文，标识符使用清晰英文。
- 每项领域行为都应有服务级测试；Textual 交互使用 Pilot；持久化测试必须覆盖关闭并重开镜像。
- 插件测试应覆盖能力拒绝、异常/超时和审计；队列测试覆盖到期、重试/失败与可观测状态。
- `pytest.ini` 收集 `tests/v2/` 中的新架构测试；旧功能迁移已完成，旧测试与旧实现不再保留。新增功能必须为新架构补充服务级、存储重开和必要的 Textual Pilot 测试。
- 修改后运行：

```bash
.venv/bin/python -m pytest -q
.venv/bin/python -m compileall -q neo_agent tests/v2
 git diff --check
```

## 产品目标和迁移门禁

优先纵向交付可操作闭环。旧用户功能迁移映射见路线图；后续深化目标包括离线群聊模拟、可解释发言仲裁、关系/记忆审核工作台及真实平台人工确认闭环。具体状态见 `docs/PRODUCT_ROADMAP.md`。
