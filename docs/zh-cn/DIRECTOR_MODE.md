# 导演模式文档

## 概述

导演模式（Director Mode）是 Neo Agent 的一项高级功能，允许用户为智能体预设一系列场景时间线，使智能体能够按照预定的剧情进行角色扮演。这个功能特别适合于需要引导式对话、情景模拟、故事演绎等场景。

## 核心概念

### 时间线 (Timeline)

时间线是场景的集合，代表一个完整的角色扮演剧情。时间线具有以下属性：

- **名称**：时间线的标题
- **描述**：时间线的详细说明
- **场景列表**：按顺序排列的场景
- **状态**：未启动、运行中、暂停

### 场景 (Scenario)

场景是时间线中的单个节点，代表剧情中的一个特定时刻或事件。场景具有以下属性：

| 属性 | 说明 |
|------|------|
| 名称 | 场景的标题 |
| 描述 | 场景的详细描述 |
| 类型 | 场景类型（见下方） |
| 触发类型 | 触发方式 |
| 触发时间 | 时间触发的延迟秒数 |
| 持续时间 | 场景持续的秒数 |
| 自动进入下一场景 | 是否自动推进 |
| 内容 | 场景的具体内容（JSON格式） |

## 场景类型

### 1. 环境变化场景 (environment)

用于描述环境的变化，如时间、地点、氛围的变化。

```json
{
  "time_of_day": "早晨7:00",
  "mood": "宁静、舒适",
  "environment_hints": ["阳光", "闹钟", "窗帘"]
}
```

### 2. 对话提示场景 (dialogue)

用于为对话提供话题提示和风格指导。

```json
{
  "dialogue_hints": ["早安", "睡得好吗", "今天的计划"],
  "expected_response_style": "亲切、活泼"
}
```

### 3. 情感变化场景 (emotion)

用于设定智能体的情感状态。

```json
{
  "emotion": "happy",
  "intensity": 0.8,
  "reason": "期待今天的活动"
}
```

### 4. 事件触发场景 (event)

用于在时间线中触发系统事件。

```json
{
  "event_type": "notification",
  "event_title": "新消息",
  "event_description": "收到了一条新消息"
}
```

### 5. 动作描述场景 (action)

用于描述智能体正在进行的动作。

```json
{
  "action": "整理书包",
  "target": "课本和笔记",
  "manner": "仔细地"
}
```

## 触发类型

### 时间触发 (time)

场景在时间线开始后指定秒数自动触发。

### 顺序触发 (sequence)

场景在前一个场景完成后自动触发。

### 手动触发 (manual)

场景需要用户手动推进。

### 条件触发 (condition)

场景在满足特定条件时触发（预留功能）。

## 使用指南

### 通过 GUI 使用

1. **打开导演模式面板**
   - 启动应用：`python gui_enhanced.py`
   - 点击右侧选项卡中的「🎬 导演模式」

2. **创建时间线**
   - 点击「➕ 新建时间线」
   - 输入时间线名称和描述
   - 点击「创建」

3. **添加场景**
   - 选择一个时间线
   - 点击「➕ 添加场景」
   - 填写场景信息
   - 设置触发类型和时间
   - 输入场景内容（JSON格式）
   - 点击「添加」

4. **启动时间线**
   - 选择要启动的时间线
   - 点击「▶️ 开始」
   - 在聊天窗口与智能体对话

5. **控制时间线**
   - 暂停：点击「⏸️ 暂停」
   - 恢复：点击「▶️ 恢复」
   - 停止：点击「⏹️ 停止」

### 通过代码使用

```python
from chat_agent import ChatAgent

# 初始化代理
agent = ChatAgent()

# 创建时间线
timeline = agent.create_director_timeline(
    name="角色扮演：校园生活",
    description="模拟智能体在校园中的一天"
)

# 添加场景
agent.add_scenario_to_director_timeline(
    timeline_id=timeline.timeline_id,
    name="早晨起床",
    description="阳光透过窗户照进房间",
    scenario_type="environment",
    trigger_type="time",
    trigger_time=0,
    content={
        "time_of_day": "早晨7:00",
        "mood": "宁静"
    },
    duration=10,
    auto_advance=True
)

# 启动时间线
agent.start_director_timeline(timeline.timeline_id)

# 对话（场景上下文会自动注入）
response = agent.chat("早安！")

# 停止时间线
agent.stop_director_timeline()
```

## API 参考

### DirectorMode 类

```python
from director_mode import DirectorMode, Timeline, Scenario, ScenarioType, TriggerType

# 初始化
director = DirectorMode(db_manager=db)

# 创建时间线
timeline = director.create_timeline(
    name="时间线名称",
    description="描述"
)

# 添加场景
scenario = director.add_scenario_to_timeline(
    timeline_id=timeline.timeline_id,
    name="场景名称",
    description="场景描述",
    scenario_type=ScenarioType.DIALOGUE,
    trigger_type=TriggerType.SEQUENCE,
    trigger_time=0,
    content={"hints": ["提示1", "提示2"]},
    duration=0,
    auto_advance=False
)

# 启动时间线
director.start_timeline(timeline.timeline_id)

# 暂停/恢复/停止
director.pause_timeline()
director.resume_timeline()
director.stop_timeline()

# 获取统计信息
stats = director.get_statistics()
```

### ChatAgent 集成方法

```python
# 创建时间线
timeline = agent.create_director_timeline(name, description)

# 获取所有时间线
timelines = agent.get_all_director_timelines()

# 添加场景
scenario = agent.add_scenario_to_director_timeline(...)

# 启动/暂停/恢复/停止
agent.start_director_timeline(timeline_id)
agent.pause_director_timeline()
agent.resume_director_timeline()
agent.stop_director_timeline()

# 检查状态
is_active = agent.is_director_mode_active()
stats = agent.get_director_statistics()

# 获取当前场景上下文
context = agent.get_current_scenario_context()

# 删除时间线
agent.delete_director_timeline(timeline_id)

# 创建示例时间线
sample = agent.create_sample_director_timeline()
```

## 数据库结构

### director_timelines 表

| 字段 | 类型 | 说明 |
|------|------|------|
| timeline_id | TEXT | 时间线UUID（主键） |
| name | TEXT | 时间线名称 |
| description | TEXT | 时间线描述 |
| is_active | INTEGER | 是否激活 |
| is_paused | INTEGER | 是否暂停 |
| start_time | TEXT | 开始时间 |
| current_scenario_index | INTEGER | 当前场景索引 |
| elapsed_time | INTEGER | 已经过时间（秒） |
| metadata | TEXT | 附加元数据（JSON） |
| created_at | TEXT | 创建时间 |
| updated_at | TEXT | 更新时间 |

### director_scenarios 表

| 字段 | 类型 | 说明 |
|------|------|------|
| scenario_id | TEXT | 场景UUID（主键） |
| timeline_id | TEXT | 所属时间线ID |
| name | TEXT | 场景名称 |
| description | TEXT | 场景描述 |
| scenario_type | TEXT | 场景类型 |
| trigger_type | TEXT | 触发类型 |
| trigger_time | INTEGER | 触发时间（秒） |
| trigger_condition | TEXT | 触发条件 |
| content | TEXT | 场景内容（JSON） |
| duration | INTEGER | 持续时间（秒） |
| auto_advance | INTEGER | 是否自动推进 |
| environment_uuid | TEXT | 关联的环境UUID |
| status | TEXT | 场景状态 |
| metadata | TEXT | 附加元数据（JSON） |
| created_at | TEXT | 创建时间 |
| sort_order | INTEGER | 排序顺序 |

### director_scenario_logs 表

| 字段 | 类型 | 说明 |
|------|------|------|
| log_id | INTEGER | 日志ID（自增主键） |
| scenario_id | TEXT | 场景ID |
| timeline_id | TEXT | 时间线ID |
| action | TEXT | 动作类型 |
| details | TEXT | 详细信息 |
| created_at | TEXT | 创建时间 |

## 最佳实践

### 1. 合理规划时间线

- 将复杂剧情分解为多个简单场景
- 为每个场景设置清晰的目标
- 考虑用户可能的反应

### 2. 设置适当的触发类型

- 对于需要用户参与的场景，使用顺序触发并将 `auto_advance` 设为 `false`
- 对于过渡性场景，使用时间触发并设置适当的持续时间

### 3. 提供丰富的场景内容

- 在 `content` 中提供足够的上下文信息
- 为对话场景提供多个话题提示
- 为情感场景提供明确的情绪原因

### 4. 测试时间线

- 在正式使用前先测试整个时间线
- 检查场景之间的过渡是否自然
- 确保所有触发条件都能正常工作

## 与其他功能的集成

### 与环境系统集成

场景可以通过 `environment_uuid` 关联到特定环境，当场景触发时会自动切换环境。

### 与事件系统集成

事件触发类型的场景可以自动创建系统事件，实现与事件驱动系统的联动。

### 与情感分析集成

情感场景会影响智能体的情感状态，这些状态会被纳入对话生成的上下文中。

## 故障排查

### 时间线无法启动

- 确保时间线包含至少一个场景
- 检查场景的触发设置是否正确

### 场景没有触发

- 检查触发类型和触发时间设置
- 确保前一个场景已正确完成（顺序触发）
- 查看调试日志获取更多信息

### 对话没有场景上下文

- 确保导演模式已启动（检查状态栏）
- 确保当前场景已被触发
- 检查场景内容是否正确设置

## 更新日志

### v1.0.0 (2025-01-19)

- ✅ 初始版本发布
- ✅ 支持五种场景类型
- ✅ 支持四种触发类型
- ✅ GUI 时间线管理界面
- ✅ 与 ChatAgent 完整集成
- ✅ 场景上下文自动注入对话

---

最后更新：2025-01-19
