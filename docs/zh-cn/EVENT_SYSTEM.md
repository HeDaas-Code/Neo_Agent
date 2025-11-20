# 事件驱动系统文档

## 概述

事件驱动模块为智能体提供预先设置的事件功能，事件分为两类：**通知型**和**任务型**。这些事件可以通过GUI界面触发，优先级高于普通对话。

## 模块架构

### 核心模块

1. **event_manager.py** - 事件管理模块
   - 事件的创建、存储、检索和管理
   - 支持通知型和任务型两种事件类型
   - 基于SQLite数据库的持久化存储

2. **interrupt_question_tool.py** - 中断性提问工具
   - 允许智能体在任务执行过程中向用户提问
   - 支持带上下文的问题提示

3. **multi_agent_coordinator.py** - 多智能体协作模块
   - 负责任务型事件的智能体协作处理
   - 任务分解、规划和执行
   - 旁白式进度提示
   - 任务完成验证

4. **chat_agent.py** (扩展)
   - 集成事件处理功能
   - 处理通知型和任务型事件的统一入口

5. **gui_enhanced.py** (扩展)
   - 事件管理可视化界面
   - 事件创建、查看、触发和删除

## 事件类型

### 1. 通知型事件 (Notification Event)

通知型事件用于向智能体传递外部信息，智能体需要立即理解并向用户说明。

**特点：**
- 智能体接收后立即理解事件含义
- 向用户进行自然的说明
- 不需要执行复杂任务
- 处理迅速

**使用场景：**
- 系统更新通知
- 重要消息提醒
- 状态变更通知
- 外部事件告知

**示例：**
```python
from event_manager import EventType, EventPriority

event = agent.event_manager.create_event(
    title="系统更新通知",
    description="新版本已发布，包含性能优化和bug修复。",
    event_type=EventType.NOTIFICATION,
    priority=EventPriority.MEDIUM
)
```

### 2. 任务型事件 (Task Event)

任务型事件需要智能体理解任务要求、进行规划并通过多智能体协作完成任务。

**特点：**
- 需要理解任务要求和完成标准
- 使用多智能体协作完成
- 可以向用户提问获取必要信息
- 输出旁白式进度提示
- 完成后由工具智能体验证

**使用场景：**
- 数据整理分析
- 文档生成
- 信息汇总
- 复杂查询任务

**示例：**
```python
event = agent.event_manager.create_event(
    title="生成周报",
    description="根据本周的对话记录生成周报摘要",
    event_type=EventType.TASK,
    priority=EventPriority.HIGH,
    task_requirements="需要总结本周的主要对话主题和知识点",
    completion_criteria="周报需包含：主题列表、知识点总结、对话统计"
)
```

## 事件处理流程

### 通知型事件处理流程

1. **触发事件** - 用户在GUI中点击"触发事件"按钮
2. **理解阶段** - 智能体分析事件内容和含义
3. **说明阶段** - 智能体以自然语气向用户说明事件
4. **完成** - 事件标记为已完成

```
[用户触发] → [智能体理解] → [生成说明] → [展示给用户] → [完成]
```

### 任务型事件处理流程

1. **触发事件** - 用户在GUI中点击"触发事件"按钮
2. **任务理解** - 理解智能体分析任务需求
3. **制定计划** - 规划智能体分解任务为具体步骤
4. **执行步骤** - 执行智能体逐步完成任务
   - 如需用户输入，使用中断性提问工具
   - 输出旁白式进度提示
5. **验证完成** - 验证智能体检查是否达到完成标准
6. **结果反馈** - 向用户展示任务结果

```
[用户触发] 
    ↓
[任务理解] (理解智能体)
    ↓
[制定计划] (规划智能体) - 分解为3-5个步骤
    ↓
[执行步骤] (执行智能体)
    ├─ 步骤1 → [输出进度] → [完成]
    ├─ 步骤2 → [需要信息] → [中断提问] → [用户回答] → [继续]
    ├─ 步骤3 → [输出进度] → [完成]
    └─ ...
    ↓
[验证结果] (验证智能体)
    ↓
[展示结果] → [完成/失败]
```

## 中断性提问工具

在任务执行过程中，如果智能体需要用户提供信息，可以使用中断性提问工具。

**使用方式：**

```python
# 智能体内部调用（自动处理）
answer = interrupt_question_tool.ask_user(
    question="请问您希望周报包含哪些具体内容？",
    context="正在生成周报，需要确认报告范围"
)
```

**提问时机：**
- 任务信息不明确
- 需要用户确认决策
- 存在多个选择
- 需要用户提供参数

## 旁白式进度提示

在多智能体协作过程中，系统会以第三人称旁白的方式输出进度提示：

```
📢 智能体开始分析任务「生成周报」...
📢 任务已理解：需要从对话历史中提取关键信息生成周报
📢 智能体正在制定执行计划...
📢 执行计划已制定，共3个步骤
📢 正在执行步骤 1/3: 提取对话主题
📢 步骤 1 完成
📢 正在执行步骤 2/3: 统计对话数据
📢 步骤 2 完成
📢 正在执行步骤 3/3: 生成报告文档
📢 步骤 3 完成
📢 所有步骤已完成，正在验证任务结果...
📢 ✅ 任务验证通过！周报已成功生成
```

## GUI 使用指南

### 打开事件管理面板

1. 启动应用：`python gui_enhanced.py`
2. 在右侧选项卡中点击"📅 事件管理"

### 创建新事件

1. 点击"➕ 新建事件"按钮
2. 填写事件信息：
   - 事件标题
   - 事件描述
   - 事件类型（通知型/任务型）
   - 优先级（低/中/高/紧急）
3. 如果是任务型，还需填写：
   - 任务要求
   - 完成标准
4. 点击"创建"按钮

### 触发事件

1. 在事件列表中选择一个事件
2. 点击"🚀 触发事件"按钮
3. 等待智能体处理
4. 查看处理结果（显示在聊天区域）

### 查看事件详情

1. 在事件列表中选择一个事件
2. 点击"📝 查看详情"按钮
3. 查看事件信息和处理日志

### 删除事件

1. 在事件列表中选择一个事件
2. 点击"🗑️ 删除事件"按钮
3. 确认删除操作

## 事件优先级

事件系统支持四个优先级：

- **LOW (1)** - 低优先级，可稍后处理
- **MEDIUM (2)** - 中等优先级，正常处理
- **HIGH (3)** - 高优先级，优先处理
- **URGENT (4)** - 紧急，立即处理

待处理事件列表按照优先级降序、创建时间升序排列。

## 事件状态

事件在生命周期中会经历以下状态：

- **PENDING** - 待处理，刚创建的状态
- **PROCESSING** - 处理中，正在被智能体处理
- **COMPLETED** - 已完成，成功处理完成
- **FAILED** - 失败，处理过程中出错
- **CANCELLED** - 已取消，用户主动取消

## 数据库结构

### events 表

存储事件基本信息：

| 字段 | 类型 | 说明 |
|------|------|------|
| event_id | TEXT | 事件唯一ID（UUID） |
| title | TEXT | 事件标题 |
| description | TEXT | 事件描述 |
| event_type | TEXT | 事件类型（notification/task） |
| priority | INTEGER | 优先级（1-4） |
| status | TEXT | 事件状态 |
| created_at | TEXT | 创建时间（ISO 8601） |
| updated_at | TEXT | 更新时间 |
| completed_at | TEXT | 完成时间 |
| metadata | TEXT | 附加元数据（JSON） |

### event_logs 表

存储事件处理日志：

| 字段 | 类型 | 说明 |
|------|------|------|
| log_id | INTEGER | 日志ID（自增） |
| event_id | TEXT | 关联的事件ID |
| log_type | TEXT | 日志类型 |
| log_content | TEXT | 日志内容 |
| created_at | TEXT | 创建时间 |

## API 参考

### EventManager

```python
from event_manager import EventManager, EventType, EventPriority

# 初始化
manager = EventManager(db_manager=db)

# 创建事件
event = manager.create_event(
    title="标题",
    description="描述",
    event_type=EventType.NOTIFICATION,
    priority=EventPriority.HIGH
)

# 获取事件
event = manager.get_event(event_id)

# 获取待处理事件
pending = manager.get_pending_events(limit=10)

# 更新事件状态
manager.update_event_status(event_id, EventStatus.COMPLETED, "完成消息")

# 添加日志
manager.add_event_log(event_id, "log_type", "日志内容")

# 获取日志
logs = manager.get_event_logs(event_id)

# 删除事件
manager.delete_event(event_id)

# 获取统计
stats = manager.get_statistics()
```

### ChatAgent 事件处理

```python
from chat_agent import ChatAgent

agent = ChatAgent()

# 处理通知型事件
explanation = agent.process_notification_event(notification_event)

# 处理任务型事件
result = agent.process_task_event(task_event)

# 统一事件处理入口
result_message = agent.handle_event(event_id)

# 获取待处理事件
pending_events = agent.get_pending_events()

# 获取事件统计
stats = agent.get_event_statistics()
```

### InterruptQuestionTool

```python
from interrupt_question_tool import InterruptQuestionTool

tool = InterruptQuestionTool()

# 设置回调函数
tool.set_question_callback(lambda q: input(q))

# 向用户提问
answer = tool.ask_user(
    question="您的问题？",
    context="背景说明"
)
```

## 最佳实践

### 1. 创建清晰的事件标题

✅ 好的标题：
- "系统更新通知 v2.0"
- "生成本周对话周报"
- "整理知识库分类"

❌ 不好的标题：
- "通知"
- "任务"
- "测试"

### 2. 提供详细的事件描述

描述应该包含：
- 事件的背景信息
- 事件的具体内容
- 相关的时间、地点、人物等

### 3. 明确任务要求和完成标准

对于任务型事件：
- 任务要求要具体明确
- 完成标准要可验证
- 避免模糊的描述

### 4. 合理设置优先级

- 紧急且重要 → URGENT
- 重要但不紧急 → HIGH
- 一般事务 → MEDIUM
- 可延后的 → LOW

### 5. 及时清理已完成的事件

定期删除已完成的历史事件，保持事件列表清洁。

## 扩展开发

### 添加新的事件类型

1. 在 `EventType` 枚举中添加新类型
2. 创建对应的事件类（继承自 `Event`）
3. 在 `ChatAgent` 中添加处理方法
4. 更新 GUI 以支持新类型

### 自定义智能体角色

在 `multi_agent_coordinator.py` 中可以自定义不同角色的智能体：

```python
agent = SubAgent(
    agent_id='custom_agent',
    role='自定义角色',
    description='角色职责描述',
    api_key=api_key,
    api_url=api_url,
    model_name=model_name
)
```

### 添加新的工具

为智能体添加新工具：

1. 创建工具类
2. 实现 `create_tool_description()` 方法
3. 在执行步骤时传递给智能体

## 故障排查

### 事件创建失败

- 检查数据库连接是否正常
- 确认事件参数是否完整
- 查看日志获取详细错误信息

### 事件处理超时

- 检查API密钥是否有效
- 确认网络连接正常
- 考虑增加超时时间

### 中断提问无响应

- 确认回调函数已正确设置
- 检查GUI主线程是否阻塞
- 验证对话框是否正常显示

## 注意事项

1. **API密钥配置**：确保 `.env` 文件中配置了有效的 `SILICONFLOW_API_KEY`
2. **数据库备份**：重要事件数据应定期备份
3. **并发处理**：同一时间只能处理一个事件
4. **资源消耗**：复杂任务可能消耗较多API调用额度
5. **用户体验**：事件处理期间，用户界面可能短暂无响应

## 更新日志

### v1.0.0 (2025-01-19)

- ✅ 初始版本发布
- ✅ 支持通知型和任务型事件
- ✅ 实现多智能体协作
- ✅ 添加中断性提问工具
- ✅ GUI事件管理界面
- ✅ 旁白式进度提示
- ✅ 任务完成验证机制

## 贡献指南

欢迎提交问题和改进建议！

如需贡献代码：
1. Fork 项目
2. 创建特性分支
3. 提交更改
4. 发起 Pull Request

## 许可证

本项目采用 MIT 许可证。

---

最后更新：2025-01-19
