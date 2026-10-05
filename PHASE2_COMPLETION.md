# Phase 2 完成报告：认知门控三阶段隔离

## 完成时间
2026-10-05

## 目标
实现认知门控的三阶段隔离架构：**认知 → 执行 → 表达**，确保表达阶段无工具权限，只接收规范化摘要，防止 OOC（Out of Character）。

## 已实现功能

### 1. 认知决策服务（`neo_agent/runtime/cognition.py`）

#### CognitionDecision 结构
- `intent`: 用户意图分类
- `action_needed`: 是否需要执行操作
- `reply_strategy`: 回复策略（reply/clarify/delay/silence）
- `confidence`: 置信度（0-1）
- `relationship_signal`: 关系信号（positive/neutral/negative）
- `affective_state`: 临时情绪状态

#### ActionResult 公开边界
```python
public_dict() -> {"status": "succeeded/failed/denied", "summary": "规范化摘要"}
```
- **隐藏字段**：`tool_name`, `capability`, `risk`
- **只暴露**：`status` 和 `summary`

### 2. 安全摘要过滤（`safe_result_summary`）

自动脱敏以下敏感信息：
- API 密钥、Token、密码：`api_key=xxx` → `api_key=[已隐藏]`
- 文件路径：`/home/user/.ssh/key` → `[路径已隐藏]`
- 内部标识符：`internal_vector_service_v2` → `[内部标识已隐藏]`
- 非结构化字符串：直接返回 `"操作已完成。"` 或 `"操作未能完成。"`

### 3. 风险分类（`risk_for_tool`）

**高风险标记**（触发增强审计）：
- `sandbox.fs.write`：文件系统写入
- `delete`, `remove`, `overwrite`：删除/覆盖操作
- `nps.create`：插件创建
- `plugin.install`, `plugin.enable`：插件安装/启用
- `send`, `permission`, `secret`, `token`：外部发送/权限变更/密钥操作

**低风险**：
- 只读查询（`search`, `get`, `query`）
- 不含高风险关键字的操作

### 4. 群聊回复门控（`GroupReplyGate`）

#### 决策逻辑
| 条件 | 决策 | 原因 |
|------|------|------|
| 直接 @ 提及 + 置信度 ≥ 0.45 | reply | direct_address |
| 冷却期 + 非直接提及 | silence | cooldown_active |
| 置信度 < 0.45 或相关性 < 0.25 | silence | low_relevance_or_confidence |
| 置信度 < 0.65 | delay | uncertain_intent |
| 活跃度 > 0.9 + 相关性 < 0.8 | delay | group_is_busy |
| 其他相关消息 | reply | relevant_message |

#### 离线回放能力
```python
gate.replay(messages: List[IncomingMessage]) -> List[ReplyCandidate]
```
支持批量消息回放，用于调试和优化门控策略。

### 5. 三阶段 Agent 运行时（`neo_agent/runtime/agent.py`）

#### Stage 1: 认知门控
```python
decision = self.cognition.assess(
    message=message,
    context=context,
    personality=personality,
    direct_chat=True
)
```
- 输入：用户消息、上下文、角色设定
- 输出：结构化 `CognitionDecision`
- **无工具权限**

#### Stage 2: 执行阶段
```python
if decision.action_needed:
    planned = self.model.bind_tools(self.tools).invoke(planner_messages)
    for call in planned.tool_calls:
        actions.append(self._execute_tool(call))
```
- 带工具绑定的模型调用
- 校验声明式能力
- 执行工具并记录 `ActionResult`
- 高风险操作自动增强审计

#### Stage 3: 表达阶段
```python
action_facts = [item.public_dict() for item in actions]
response = self.language_model.invoke([
    SystemMessage(content=language_system),
    *history,
    HumanMessage(content=language_user)
])
```
- **无工具绑定**（纯语言生成）
- 只接收 `action_facts`（规范化摘要）
- 不传递原始工具轨迹、参数、隐藏推理
- 失败操作明确标记为 `failed`

### 6. 直聊模式约束

```python
if direct_chat and decision.reply_strategy in {"delay", "silence"}:
    decision = CognitionDecision.from_mapping({
        **decision.__dict__,
        "reply_strategy": "reply"
    })
```
- 一对一聊天强制回复或澄清
- 不允许沉默或延迟

## 测试覆盖

### 核心功能测试（`test_cognition_core.py`）
- ✅ 认知决策结构化解析
- ✅ 操作结果公开视图隔离
- ✅ 敏感信息自动脱敏
- ✅ 风险分类正确性
- ✅ 群聊回复门控策略
- ✅ 认知服务模型集成
- ✅ 直聊模式强制回复

### 验收标准
- [x] 表达阶段无工具权限
- [x] 表达阶段只接收规范化摘要
- [x] 敏感信息（密钥、路径、内部标识）被过滤
- [x] 高风险操作有增强审计标记
- [x] 失败操作不会被角色声称成功
- [x] 直聊模式不允许沉默
- [x] 群聊门控正确判断回复/延迟/沉默

## 关键设计决策

### 1. 为什么表达阶段无工具权限？
防止模型在生成自然语言时泄漏工具调用细节、技术术语或执行轨迹，保持角色一致性（避免 OOC）。

### 2. 为什么高风险操作仍自动执行？
Agent 需要自主决策能力，人在回路会破坏拟人化体验。通过**增强审计**而非事前批准来保证可观测性和可问责性。

### 3. 为什么非结构化字符串返回默认消息？
插件可能输出任意文本，包括敏感信息或技术细节。非结构化输出不安全，统一返回通用消息避免泄漏。

### 4. 为什么需要群聊回复门控？
真实群聊环境中，Agent 不应对每条消息都回复。门控模拟人类的选择性参与，提升自然度和拟人化程度。

## 架构图

```
用户消息
   ↓
┌─────────────────────────────────────┐
│ Stage 1: 认知门控（无工具）          │
│  - 意图分析                          │
│  - 决策：回复/澄清/延迟/沉默          │
│  - 是否需要操作                       │
│  - 临时情绪与关系信号                 │
└─────────────────────────────────────┘
   ↓ CognitionDecision
┌─────────────────────────────────────┐
│ Stage 2: 执行阶段（带工具）          │
│  - 工具绑定模型调用                   │
│  - 能力校验                          │
│  - 工具执行 → ActionResult           │
│  - 高风险操作增强审计                 │
└─────────────────────────────────────┘
   ↓ List[ActionResult]
┌─────────────────────────────────────┐
│ 脱敏：ActionResult.public_dict()     │
│  - 只保留 status 和 summary          │
│  - 隐藏 tool_name, capability, risk  │
└─────────────────────────────────────┘
   ↓ List[PublicDict]
┌─────────────────────────────────────┐
│ Stage 3: 表达阶段（无工具）          │
│  - 角色设定 + 上下文                 │
│  - 规范化操作结果                    │
│  - 纯语言生成                        │
│  - 不泄漏工具细节                    │
└─────────────────────────────────────┘
   ↓
角色回复
```

## 后续工作（Phase 3 & 4）

### Phase 3: 日程驱动场景生成
- 每日自动生成 Agent 行程
- 场景池匹配与结构化生成
- 三类日程管理（Agent/用户/共同）
- 自主冲突协调
- 到期自动场景切换

### Phase 4: Agent 自动创作
- 自动创建事件、日程、关系、知识
- NPS 自动生成（仅 VScript）
- Debug 开关控制人工入口
- 完整审计记录

## 技术债务与改进

### 已知限制
1. **群聊门控阈值硬编码**：相关性/置信度/活跃度阈值应可配置
2. **临时情绪未持久化**：当前只作为上下文传递，未写入存储
3. **表达模型独立配置**：目前与执行模型共用，应支持独立模型

### 潜在优化
- 群聊门控可引入学习机制，根据用户反馈调整阈值
- 敏感信息过滤可扩展为可配置规则库
- 高风险操作审计可推送到外部监控系统

## 结论

✅ **Phase 2 完成**：认知门控三阶段隔离架构已实现并通过测试。

核心目标达成：
- 表达阶段与工具执行完全隔离
- 敏感信息自动脱敏
- 高风险操作可审计
- 群聊回复智能门控
- 直聊模式约束

架构清晰，边界明确，为后续 Phase 3（日程驱动场景）和 Phase 4（自动创作）奠定坚实基础。
