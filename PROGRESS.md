# Neo Agent 开发进度报告

## 📋 当前完成的功能

### ✅ 1. 服务-客户端架构（100%）
- **守护进程服务** - 独立运行的后台服务
  - Unix socket 通信 (`/home/hedass/.neo_agent/agent.sock`)
  - JSON-RPC 2.0 协议
  - 自动启动脚本 (`start_service.sh`)
  - 完整的日志记录
  
- **客户端连接**
  - 异步 RPC 客户端
  - 自动重连机制
  - 完整的 API 封装

### ✅ 2. 数据持久化（100%）
- **PyVDisk 集成**
  - DiskStore 统一存储接口
  - 角色、场景、日程、关系数据持久化
  - 支持数据重开恢复

- **数据路径**: `/home/hedass/.neo_agent/data.vdisk`

### ✅ 3. 运行时服务层（100%）
- **SingleRoleService** - 单角色管理
  - 预设角色：林依（17岁女高中生）
  - 完整的角色资料和性格设定
  - 系统提示词生成

- **SceneService** - 场景管理
  - 初始环境："家"（客厅、卧室、厨房、阳台）
  - 场景池管理
  - 当前场景追踪

- **ScheduleService** - 日程管理
  - 今日行程查询
  - 三类日程支持（Agent个人、用户个人、共同活动）

- **RelationshipService** - 关系管理
  - 关系状态追踪
  - 关系分数 -100~100
  - 亲密度等级

- **EmotionService** - 情绪管理
  - 临时情绪状态
  - 情绪强度追踪

### ✅ 4. TUI 界面（100%）
- **琥珀温暖主题**
  - 五级深褐表面色 (#050302 → #2B231C)
  - 琥珀金强调色 (#E9A568)
  - 温暖舒适的视觉体验

- **布局系统**
  - 顶栏：角色名、场景、情绪、时间、连接状态
  - 左侧导航栏：6个主要视图 + 设置提示
  - 主内容区：动态切换视图
  - 底栏：服务状态 + 快捷键提示

- **导航系统**
  - ✅ 鼠标点击切换视图
  - ✅ 快捷键切换（c/i/s/m/r/a）
  - ✅ 视图激活状态显示

### ✅ 5. 六大视图框架（100%）

#### 💬 对话视图（ChatView）
- 对话历史显示
- 消息输入框
- 发送按钮
- 实时情绪更新
- **待完善**: 接入 LangChain Agent

#### 📅 今日行程视图（ItineraryView）
- 今日时间线
- 行程类型标注
- 场景绑定显示
- **待完善**: 每日自动生成

#### 🌍 场景池视图（ScenePoolView）
- 已访问场景列表
- 当前场景高亮
- 场景详情查看
- **待完善**: 自动场景生成

#### 🧠 记忆与知识视图（MemoryView）
- 记忆统计
- 搜索功能
- 知识条目显示
- **待完善**: 向量记忆集成

#### 💭 关系网络视图（RelationshipView）
- 关系列表
- 亲密度显示
- 关系分数
- **待完善**: 自动关系更新

#### 🔍 审计日志视图（AuditView）
- 操作日志
- 风险级别过滤
- 时间倒序显示
- **待完善**: 决策审计

### ✅ 6. RPC API（100%）
18个完整的 RPC 方法：
- session.* - 会话管理（send_message, get_context, get_history）
- character.* - 角色管理（get_profile, update_profile）
- schedule.* - 日程管理（get_today_itinerary）
- scene.* - 场景管理（get_current, list_pool）
- memory.* - 记忆管理（search, get_stats）
- knowledge.* - 知识管理（query）
- relationship.* - 关系管理（get_status, list_all）
- emotion.* - 情绪管理（get_current）
- audit.* - 审计管理（get_logs）
- system.* - 系统管理（get_status, set_debug, shutdown）

---

## 🚧 待开发功能

### P0: LangChain Agent 集成（核心功能）
**目标**: 让 Agent 可以真实对话并调用工具

**需要创建的文件**:
- `neo_agent/runtime/agent.py` - Agent 运行时
- `neo_agent/runtime/cognition.py` - 认知门控（决策阶段）
- `neo_agent/runtime/expression.py` - 语言生成（措辞阶段）
- `neo_agent/runtime/tools/` - LangChain 工具定义

**关键设计**:
- 认知门控可用工具，语言生成无工具权限（防止 OOC）
- 三阶段流程：认知门控 → 操作执行 → 角色语言生成
- 需要环境变量：`OPENAI_API_KEY` 或 `SILICONFLOW_API_KEY`

**预估时间**: 2-3天

### P1: 日程驱动场景系统
**目标**: Agent 自主生成每日行程并自动切换场景

**功能点**:
1. **DailyItineraryService** - 每日行程生成
   - 每天 00:05 自动生成当日行程
   - TUI 启动时补齐当天计划
   - 明确起止时间，避免时间重叠

2. **场景生成与切换**
   - 外出触发场景生成（地点、区域、物体）
   - 首次访问后场景固化
   - 到达时段自动切换场景
   - 跨日回到初始环境

3. **共同活动决策**
   - 冲突判断与自主调整
   - 保留结构化决策摘要
   - 不修改用户个人日程

**预估时间**: 2-3天

### P2: 认知门控与拟人化
**目标**: 分离执行引擎和语言生成，防止 OOC

**功能点**:
1. **认知结构**
   - `CognitionDecision` - 决策结果
   - `ActionResult` - 操作结果
   - `ReplyCandidate` - 回复候选

2. **群聊感知**
   - 相关性判断
   - 活跃度评估
   - 冷却机制
   - 沉默/延迟/回复决策

3. **情绪与关系**
   - 临时情绪估计
   - 持久关系更新（需连续3轮 + 置信度≥0.8）
   - 关系分数限幅（±3）

**预估时间**: 2-3天

### P3: Agent 自动创作
**目标**: 让 Agent 自动创建事件、日程、知识等

**功能点**:
- 根据对话按需创建事件、日程、关系、知识、环境域、NPS
- 必要信息不足时先澄清
- NPS 自动生成只允许 VScript，不自动生成 Python 扩展
- 高风险操作加强审计

**预估时间**: 2天

### P4: 混合脚本运行时（NPS v2）
**目标**: VScript 主控 + 可选 Python 扩展

**功能点**:
- 版本化 manifest
- LangChain 工具 schema
- VScript 校验与执行
- Python 扩展隔离运行
- 能力声明与审计

**预估时间**: 3-4天

### P5: WebSocket 状态同步
**目标**: 实时推送状态更新到 TUI

**功能点**:
- 场景切换事件
- 情绪变化事件
- 新消息事件
- 日程触发事件
- 多客户端同步

**预估时间**: 1天

### P6: 命令面板与配置
**目标**: 完善设置和配置管理

**功能点**:
- `:config` - 全局配置（LLM 模型、PyVDisk 路径等）
- `:debug on|off` - 调试模式切换
- `:export character|all` - 数据导出
- `:import <path>` - 数据导入
- 配置持久化

**预估时间**: 1天

---

## 📊 当前模块清单

### 核心模块
```
neo_agent/
├── service/
│   ├── daemon.py          # 守护进程服务 ✅
│   └── rpc_handlers.py    # RPC 处理器 ✅
├── runtime/
│   ├── role.py            # 单角色服务 ✅
│   ├── scene.py           # 场景服务 ✅
│   ├── schedule.py        # 日程服务 ✅
│   ├── relationship.py    # 关系 & 情绪服务 ✅
│   ├── agent.py           # Agent 运行时 🚧
│   ├── cognition.py       # 认知门控 🚧
│   └── expression.py      # 语言生成 🚧
├── storage/
│   └── disk_store.py      # PyVDisk 接口 ✅
└── ui/
    └── v2/
        ├── app.py         # 主应用 ✅
        ├── client.py      # RPC 客户端 ✅
        ├── views.py       # 六大视图 ✅
        ├── modals.py      # 模态窗口 ✅
        ├── theme.py       # 琥珀主题 ✅
        └── commands.py    # 命令面板 ✅
```

### 工具与脚本
```
start_service.sh           # 服务启动脚本 ✅
test_navigation.py         # 导航测试 ✅
test_views.py              # 视图测试 ✅
test_direct_rpc.py         # RPC 测试 ✅
```

---

## 🎯 面向"虚拟群友 Agentic"的产品路线

### 短期目标（1-2周）
1. **完成 LangChain Agent 集成** - 让 Agent 可以真实对话
2. **实现日程驱动场景系统** - 自主生成行程和场景
3. **添加认知门控** - 分离执行和措辞，防止 OOC

### 中期目标（1个月）
1. **Agent 自动创作** - 自动管理事件、日程、知识
2. **混合脚本运行时** - VScript + Python 扩展
3. **WebSocket 实时同步** - 多客户端状态同步
4. **群聊平台连接器** - QQ、Discord 等

### 长期目标（2-3个月）
1. **拟人化增强**
   - 更自然的对话节奏
   - 主动话题引导
   - 情感表达丰富化

2. **社交能力**
   - 多人群聊感知
   - 话题相关性判断
   - 适时发言与沉默

3. **记忆与学习**
   - 长期记忆固化
   - 知识图谱构建
   - 持续学习能力

4. **个性化定制**
   - 用户自定义角色
   - 可调整的性格特质
   - 灵活的行为模式

---

## 🔧 技术栈

### 已使用
- **UI**: Textual >=0.80.0
- **异步**: aiohttp, asyncio
- **持久化**: PyVDisk (自建)
- **AI框架**: LangChain, LangChain-Core, LangChain-OpenAI
- **进程管理**: python-daemon, lockfile

### 计划使用
- **向量数据库**: ChromaDB / FAISS (记忆检索)
- **LLM API**: OpenAI / SiliconFlow / 本地模型
- **群聊平台**: QQ (go-cqhttp), Discord.py

---

## 📝 注意事项

1. **数据迁移**: 不兼容旧 SQLite 数据，不提供迁移工具
2. **配置备份**: 仅支持 PyVDisk 原生快照和新格式导出
3. **插件包**: 使用新版 NPS 格式，不兼容旧 `.NPS` 文件
4. **模型配置**: 需要配置环境变量或在 TUI 中设置
5. **调试模式**: 默认关闭，开启后才能手动编辑数据

---

## 🚀 快速启动

### 启动服务
```bash
cd /home/hedass/桌面/Lien_os
./start_service.sh
```

### 启动 TUI
```bash
cd /home/hedass/桌面/Lien_os
source venv/bin/activate
python -m neo_agent.ui.v2
```

### 停止服务
```bash
pkill -f "neo_agent.service.daemon"
```

### 查看日志
```bash
tail -f /home/hedass/.neo_agent/agent.log
```

---

**最后更新**: 2026-10-05
**当前版本**: v2.0-dev (服务-客户端架构)
