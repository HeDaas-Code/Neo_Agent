# Neo Agent 当前开发状态

**更新时间**: 2026-10-05  
**分支**: Dev  
**架构**: 服务-客户端分离 + LangChain + PyVDisk

---

## 已完成功能

### 1. 核心架构重构 ✅
- **服务-客户端分离**: 后台守护进程 + 可随时连接/断开的 TUI 客户端
- **服务管理**: `python3 main.py start|stop|restart|status|tui`
- **IPC 协议**: Unix domain socket + JSON-RPC 2.0
- **持久化**: 完全基于 PyVDisk，抛弃旧 SQLite
- **并发模型**: asyncio 事件循环，TUI 操作不阻塞

### 2. 单角色系统 ✅
- **初始化**: 首次启动创建预设角色"林依"
- **ID 自动生成**: UUID v4
- **载入简化**: 角色创建后自动作为当前角色
- **Debug 模式**: 全局开关，控制人工编辑入口

### 3. Agent 自动创作 ✅
- **事件流**: Agent 自动根据对话创建事件
- **日程**: 每日 00:05 自动生成当日行程
- **关系**: 3 轮证据缓冲 + 置信度 ≥ 0.8 触发关系更新
- **知识库**: 自动提取并存储对话中的知识
- **环境域**: 初始化时创建"在家-客厅"初始环境
- **NPS/任务编排**: 可由 Agent 自动生成（VScript 格式）

### 4. 认知门控与拟人化 ✅
- **三阶段管线**: 认知门控 → 操作执行 → 角色语言生成
- **OOC 防护**: 工具执行与角色措辞分离，措辞阶段无工具权限
- **情绪系统**: 每轮评估临时情绪状态
- **群聊感知**: 相关性、活跃度、置信度、冷却决策（当前仅 TUI 单聊）
- **操作审计**: 高风险操作自动执行但记录增强审计

### 5. 日程驱动场景系统 ✅
- **初始环境**: 角色初始化时自动创建"在家-客厅"
- **每日行程生成**: 机器本地时区每天 00:05 自动生成
- **场景自动生成**: 行程需要新地点时，基于角色设定/世界观/历史对话生成
- **场景固化**: 首次访问后场景设定固定，形成场景池
- **自动切换**: 到达行程时段自动切换到绑定场景
- **三类日程**: Agent 个人、用户个人、双方共同，支持冲突自主决策

### 6. 现代化 TUI ✅
- **琥珀主题**: 温暖琥珀色调，五级深度背景层级
- **服务状态**: 顶栏显示角色名、当前场景、情绪、时间
- **侧边导航**: 鼠标点击 + 键盘快捷键导航
- **六大视图**:
  - **对话视图**: 历史加载、异步发送、实时情绪更新
  - **今日行程视图**: DataTable 展示、点击查看详情、生成计划按钮
  - **场景池视图**: 已访问场景列表、场景详情（地点/区域/物体）
  - **记忆与知识视图**: 关键词搜索、相关度排序、类型图标
  - **关系网络视图**: 当前关系状态、关系变化历史、分数颜色编码
  - **审计日志视图**: 时间倒序、风险过滤（全部/高/中/低）
- **命令模式**: 按 `:` 唤起命令面板（`:config`, `:debug`, `:export`）
- **响应式**: 所有服务调用异步，不阻塞 UI

---

## 当前模块结构

### 运行时服务 (`neo_agent/runtime/`)
```
agent.py              # AgentRuntime 主控
cognition.py          # 认知门控（决策/回复策略）
language_generator.py # 角色语言生成（无工具权限）
auto_creation.py      # 自动创作服务（事件/日程/关系/知识）
relationship.py       # 关系服务（3轮缓冲/置信度门槛）
scene.py              # 场景服务（生成/固化/切换）
schedule.py           # 日程服务（每日生成/三类日程）
memory.py             # 记忆服务（向量搜索）
knowledge.py          # 知识服务（提取/查询）
emotion.py            # 情绪服务（临时状态评估）
```

### 服务层 (`neo_agent/service/`)
```
daemon.py             # 守护进程（Unix socket 服务器）
rpc_handlers.py       # JSON-RPC API 实现
```

### TUI 客户端 (`neo_agent/ui/v2/`)
```
app.py                # 主应用（NeoAgentTUI）
views.py              # 六大视图组件
theme.py              # 琥珀主题 CSS
client.py             # JSON-RPC 客户端
commands.py           # 命令面板
event_handlers.py     # WebSocket 事件处理
```

### 持久化 (`neo_agent/storage/`)
```
disk_store.py         # PyVDisk 封装（所有数据通过此接口）
```

### 命令行 (`neo_agent/cli.py`)
```
start     # 启动服务
stop      # 停止服务
restart   # 重启服务
status    # 查看服务状态
tui       # 启动 TUI 客户端
```

---

## 已移除的旧模块

- ❌ `src/` 旧核心（Tk GUI、旧 NPS 加载器、旧 SQLite 管理器）
- ❌ 旧测试（针对旧架构）
- ❌ 旧 GUI 校验脚本
- ❌ 旧 JSON/SQLite 配置格式（不兼容）

---

## 技术栈

- **Agent 框架**: LangChain
- **持久化**: PyVDisk (DataDisk API)
- **TUI**: Textual >= 0.80.0
- **IPC**: Unix domain socket + JSON-RPC 2.0
- **并发**: asyncio + worker 线程池
- **插件运行时**: VScript 主控 + 可选 Python 扩展（隔离进程）

---

## 配置与数据路径

- **数据目录**: `~/.neo_agent/`
- **PyVDisk 数据**: `~/.neo_agent/data.vdisk` (128MB)
- **服务 Socket**: `~/.neo_agent/agent.sock`
- **服务日志**: `~/.neo_agent/agent.log`
- **PID 文件**: `~/.neo_agent/agent.pid`

---

## 使用流程

### 1. 首次启动
```bash
cd /home/hedass/桌面/Lien_os
source .venv/bin/activate
python3 main.py start    # 启动服务，自动创建预设角色"林依"
python3 main.py tui      # 连接 TUI
```

### 2. 日常使用
```bash
python3 main.py status   # 检查服务状态
python3 main.py tui      # 随时连接/断开 TUI
```

### 3. TUI 操作
- **侧边栏导航**: 鼠标点击或键盘导航切换视图
- **对话**: 输入消息 → Enter 或点击"发送"
- **今日行程**: 查看当日计划，点击行程查看详情
- **场景池**: 查看已访问场景，点击查看场景详情
- **记忆搜索**: 输入关键词搜索历史对话/事件
- **关系网络**: 查看与用户的关系分数及变化历史
- **审计日志**: 查看 Agent 操作记录，按风险级别过滤
- **命令模式**: 按 `:` 唤起命令面板
  - `:debug on` - 开启调试模式（显示人工编辑入口）
  - `:debug off` - 关闭调试模式
  - `:config` - 全局配置（开发中）
  - `:export` - 导出数据（开发中）
- **退出**: 按 `q`（服务继续运行）

### 4. 服务管理
```bash
python3 main.py restart  # 重启服务（更新代码后）
python3 main.py stop     # 停止服务
```

---

## 下一步开发方向

### 短期（功能补全）

1. **关系系统调试** ⚠️
   - 当前问题: RelationshipService 基础设施已建立，但对话中未捕获关系信号
   - 原因分析: `AutoCreationService.extract_relationship_updates()` 依赖 LLM 判断，可能 LLM 总是返回 `has_signal: false`
   - 下一步: 
     - 检查 LLM 返回内容（已添加 debug 日志）
     - 调整提示词使其更敏感
     - 完成 `agent.py` 中的 `RelationshipService` 集成
     - 添加 `relationship.get_history` RPC handler

2. **命令功能完善**
   - `:config` 面板（LLM 模型、PyVDisk 路径、时区配置）
   - `:export` 数据导出（角色、记忆、关系、场景池）
   - `:import` 数据导入（新格式）

3. **Debug 模式人工编辑**
   - 角色卡编辑面板
   - 事件/日程手动创建
   - 关系手动调整
   - 知识库手动添加
   - 场景/物体手动编辑

4. **日程与场景完善**
   - 测试每日 00:05 自动生成
   - 测试场景自动切换
   - 测试共同活动冲突决策
   - 添加场景生成失败重试机制

### 中期（拟人化深化）

1. **群聊平台连接器**
   - QQ/微信/Discord 适配器
   - 离线消息回放与决策
   - 多人对话相关性判断
   - 发言/沉默/延迟策略

2. **记忆系统增强**
   - 短期记忆（对话窗口）
   - 长期记忆（向量检索）
   - 情景记忆（重要事件）
   - 语义记忆（知识图谱）

3. **情绪与关系深化**
   - 多维情绪模型（不只是单一状态）
   - 情绪对回复风格的影响
   - 关系影响对话策略
   - 亲密度门槛解锁话题

4. **世界观与人格一致性**
   - 角色设定约束检查
   - 长期人格追踪
   - 世界观一致性验证
   - OOC 检测与修正

### 长期（产品化）

1. **插件生态**
   - 官方插件库
   - 第三方插件安装/管理
   - 插件权限沙箱
   - 插件市场

2. **多角色支持（可选）**
   - 角色切换（非同时激活）
   - 角色间独立数据
   - 导入导出单个角色

3. **Web 客户端**
   - 复用 JSON-RPC API
   - 浏览器界面
   - 远程访问（SSH 隧道）

4. **性能优化**
   - 向量检索缓存
   - 场景预加载
   - LLM 响应流式传输

---

## 已知问题与限制

1. **关系信号未捕获** ⚠️
   - 基础设施完整，但实际对话中未记录关系变化
   - 需要调试 `AutoCreationService.extract_relationship_updates()` 的 LLM 响应

2. **无真实群平台连接**
   - 群聊感知逻辑已实现，但当前只支持 TUI 单聊
   - 需要开发平台适配器

3. **日程生成未测试**
   - 每日 00:05 自动生成逻辑已实现
   - 需要等待实际运行验证

4. **场景生成幂等性**
   - 同一行程重试时应复用已生成场景
   - 当前可能重复生成

5. **命令功能未完成**
   - `:config` / `:export` / `:import` 只有占位符

---

## 与 MaiBot 的对比

| 功能 | Neo Agent (当前) | MaiBot |
|------|-----------------|--------|
| 拟人化对话 | ✅ 认知门控 + OOC 防护 | ✅ |
| 群聊感知 | ✅ 逻辑已实现，待连接平台 | ✅ |
| 发言时机判断 | ✅ 相关性/活跃度/冷却 | ✅ |
| 记忆系统 | ✅ 向量检索 | ✅ |
| 情绪系统 | ✅ 临时状态 | ✅ 多维模型 |
| 关系系统 | ⚠️ 已实现但未捕获信号 | ✅ |
| 自主行为 | ✅ 日程/场景/自动创作 | ✅ |
| 插件系统 | ✅ VScript + Python | ✅ |
| 平台支持 | ❌ 仅 TUI | ✅ QQ/微信等 |
| 多角色 | ❌ 单角色设计 | ✅ |

**核心差异**:
- Neo Agent 当前是**单角色 + TUI 开发环境**，专注于 Agent 自主行为与拟人化深度
- MaiBot 是**多角色 + 多平台群聊机器人**，专注于实际部署与用户交互

**发展方向**: Neo Agent 短期内补全关系系统与群平台连接后，在拟人化深度上向 MaiBot 看齐，长期可作为更灵活的虚拟群友开发框架。

---

## 贡献指南

### 开发环境
```bash
# 克隆仓库
git clone https://github.com/HeDaas-Code/Neo_Agent.git
cd Neo_Agent
git checkout Dev

# 创建虚拟环境
python3 -m venv .venv
source .venv/bin/activate

# 安装依赖
pip install -r requirements.txt

# 启动开发
python3 main.py start
python3 main.py tui
```

### 代码风格
- 遵循 PEP 8
- 使用类型注解
- 异步函数优先使用 `async/await`
- 中文注释与文档

### 提交规范
- Commit 消息使用中文
- 格式: `[模块] 简短描述`
- 例: `[TUI] 完善记忆搜索视图`

---

**最后更新**: 2026-10-05 11:57  
**维护者**: HeDaas
