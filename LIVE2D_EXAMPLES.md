# Live2D助手使用示例

## 场景1：学习计划管理

### 步骤1：创建学习计划

```python
from plan_manager import PlanManager, Plan, Task, PlanStatus

# 初始化计划管理器
plan_manager = PlanManager()

# 创建学习Python的计划
python_plan = Plan(
    title="学习Python编程",
    description="系统学习Python语言，从基础到进阶",
    goal="能够独立开发Python应用程序"
)

# 添加任务
tasks = [
    Task(title="学习Python基础语法", description="变量、数据类型、控制流"),
    Task(title="学习函数和模块", description="函数定义、模块导入"),
    Task(title="学习面向对象编程", description="类、继承、多态"),
    Task(title="学习常用库", description="requests、pandas、numpy"),
    Task(title="完成实战项目", description="开发一个完整的应用")
]

for task in tasks:
    python_plan.add_task(task)

# 保存计划
plan_manager.add_plan(python_plan)
print(f"✓ 创建计划: {python_plan.title}")
print(f"  任务数: {len(python_plan.tasks)}")
```

### 步骤2：设置学习日程

```python
from schedule_manager import ScheduleManager, Schedule, SchedulePriority
from datetime import datetime, timedelta

schedule_manager = ScheduleManager()

# 创建每日学习日程
for day in range(7):
    study_time = datetime.now().replace(hour=19, minute=0, second=0) + timedelta(days=day)
    schedule = Schedule(
        title="Python学习时间",
        description=f"学习任务: {tasks[day % len(tasks)].title}",
        start_time=study_time,
        end_time=study_time + timedelta(hours=2),
        priority=SchedulePriority.HIGH
    )
    schedule_manager.add_schedule(schedule)

print("✓ 已创建本周学习日程")
```

### 步骤3：使用番茄时钟学习

```python
from pomodoro_timer import PomodoroTimer
import time

pomodoro = PomodoroTimer(work_duration=25, short_break=5)

# 设置回调
def on_work_complete():
    print("🎉 完成一个番茄！继续加油！")
    # 标记任务进度
    current_task = tasks[0]
    print(f"   当前学习: {current_task.title}")

pomodoro.on_work_complete = on_work_complete

# 开始学习
pomodoro.start_work()
print("⏰ 开始专注学习25分钟...")

# 模拟等待（实际使用中程序会持续运行）
# time.sleep(1500)  # 25分钟
```

### 步骤4：记录学习笔记

```python
from note_manager import NoteManager, Note

note_manager = NoteManager()

# 创建学习笔记
note = Note(
    title="Python基础语法学习笔记",
    content="""
# Python基础语法

## 变量和数据类型
- int: 整数
- float: 浮点数
- str: 字符串
- bool: 布尔值

## 控制流
- if/elif/else
- for循环
- while循环

## 重要知识点
- Python是动态类型语言
- 缩进很重要
- 列表推导式很强大
    """,
    category="学习笔记",
    tags=["Python", "基础", "编程"]
)

note_manager.add_note(note)
print(f"✓ 保存笔记: {note.title}")
```

## 场景2：日常工作管理

### 创建今日待办事项

```python
from datetime import datetime, timedelta

# 早晨计划
morning_meeting = Schedule(
    title="团队晨会",
    description="讨论今日工作安排",
    start_time=datetime.now().replace(hour=9, minute=30),
    end_time=datetime.now().replace(hour=10, minute=0),
    priority=SchedulePriority.URGENT
)

# 中午提醒
lunch_reminder = Schedule(
    title="午餐时间",
    description="记得休息一下",
    start_time=datetime.now().replace(hour=12, minute=0),
    end_time=datetime.now().replace(hour=13, minute=0),
    priority=SchedulePriority.LOW
)

# 下午工作
afternoon_work = Schedule(
    title="完成项目报告",
    description="整理本周工作成果",
    start_time=datetime.now().replace(hour=14, minute=0),
    end_time=datetime.now().replace(hour=17, minute=0),
    priority=SchedulePriority.HIGH
)

# 添加所有日程
for schedule in [morning_meeting, lunch_reminder, afternoon_work]:
    schedule_manager.add_schedule(schedule)

print("✓ 今日日程已安排")
```

### 工作日志记录

```python
work_log = Note(
    title=f"工作日志 - {datetime.now().strftime('%Y-%m-%d')}",
    content="""
## 今日完成事项
1. 完成需求文档评审
2. 修复3个bug
3. 更新项目文档

## 遇到的问题
- 数据库连接超时 -> 已解决，增加了重试机制

## 明日计划
1. 开始新功能开发
2. 优化代码性能
3. 编写单元测试
    """,
    category="工作",
    tags=["日志", "总结"]
)

note_manager.add_note(work_log)
print("✓ 工作日志已保存")
```

## 场景3：健身计划跟踪

```python
# 创建健身计划
fitness_plan = Plan(
    title="三个月健身计划",
    description="提升身体素质，养成运动习惯",
    goal="体重减少5kg，体脂率降低3%",
    target_date=datetime.now() + timedelta(days=90)
)

# 添加阶段性任务
fitness_tasks = [
    Task(title="第一周：建立习惯", description="每天30分钟有氧运动"),
    Task(title="第二周：增加强度", description="加入力量训练"),
    Task(title="第三周：保持节奏", description="固定每周5次训练"),
    Task(title="第一月总结", description="记录身体变化，调整计划")
]

for task in fitness_tasks:
    fitness_plan.add_task(task)

plan_manager.add_plan(fitness_plan)

# 创建每日运动提醒
workout_schedule = Schedule(
    title="今日运动",
    description="30分钟有氧 + 力量训练",
    start_time=datetime.now().replace(hour=18, minute=0),
    end_time=datetime.now().replace(hour=19, minute=0),
    priority=SchedulePriority.MEDIUM
)

schedule_manager.add_schedule(workout_schedule)

print("✓ 健身计划已创建")
```

## 场景4：与小可的日常互动

### 早晨问候

```python
from chat_agent import ChatAgent

chat_agent = ChatAgent()

# 早晨与小可打招呼
morning_greeting = chat_agent.chat("早上好，小可！")
print(f"小可: {morning_greeting}")

# 询问今日日程
today_plan = chat_agent.chat("今天有什么安排吗？")
print(f"小可: {today_plan}")
```

### 学习中寻求帮助

```python
# 学习遇到问题
question = chat_agent.chat("Python的装饰器是什么？能解释一下吗？")
print(f"小可: {question}")

# 请求鼓励
encouragement = chat_agent.chat("学习有点困难，给我加油吧！")
print(f"小可: {encouragement}")
```

### 晚间总结

```python
# 一天结束，与小可分享
summary = chat_agent.chat("今天完成了3个番茄，学习了Python基础语法，感觉很充实！")
print(f"小可: {summary}")

# 准备休息
goodnight = chat_agent.chat("今天辛苦了，晚安小可～")
print(f"小可: {goodnight}")
```

## 场景5：综合使用示例

```python
from live2d_assistant import Live2DAssistant

# 启动Live2D助手（GUI模式）
app = Live2DAssistant()

# 以下操作通过GUI完成：

# 1. 使用番茄时钟专注学习
#    - 切换到"🍅 番茄时钟"标签
#    - 点击"开始工作"
#    - 25分钟后自动提醒休息

# 2. 查看今日日程
#    - 切换到"📅 日程"标签
#    - 浏览即将到来的日程
#    - 双击查看详情

# 3. 快速记录笔记
#    - 切换到"📝 笔记"标签
#    - 点击"+ 新建笔记"
#    - 记录学习心得

# 4. 跟踪学习计划
#    - 切换到"🎯 计划"标签
#    - 查看计划进度
#    - 标记完成的任务

# 5. 与小可聊天
#    - 切换到"💬 聊天"标签
#    - 输入消息与小可交流
#    - 获取鼓励和建议

# 6. 查看统计数据
#    - 切换到"📊 统计"标签
#    - 了解学习和工作情况
#    - 调整后续计划

# 运行应用
app.mainloop()
```

## 最佳实践

### 1. 每日例行流程

**早晨 (8:00)**
- 启动Live2D助手
- 与小可问好
- 查看今日日程
- 规划今日番茄时钟安排

**上午 (9:00-12:00)**
- 使用番茄时钟工作/学习
- 完成2-3个番茄
- 记录重要笔记

**中午 (12:00-13:30)**
- 休息时间
- 查看并整理上午笔记
- 调整下午计划

**下午 (14:00-18:00)**
- 继续使用番茄时钟
- 完成3-4个番茄
- 更新计划进度

**晚上 (19:00-22:00)**
- 个人学习时间
- 记录工作日志
- 规划明日计划
- 与小可道晚安

### 2. 计划分解技巧

**大计划 → 月计划 → 周计划 → 日计划**
- 将大目标分解为可执行的小任务
- 每个任务时长控制在1-3个番茄（25-75分钟）
- 定期回顾和调整计划

### 3. 笔记组织方法

**使用标签和分类**
- 学习笔记：按科目分类
- 工作笔记：按项目分类
- 生活笔记：按类型分类
- 重要笔记置顶
- 定期整理和归档

### 4. 提醒设置建议

- 重要会议：提前30分钟提醒
- 日常任务：提前15分钟提醒
- 休息提醒：每2小时设置一次
- 定期回顾：每周/每月设置总结提醒

## 进阶技巧

### 自定义番茄时钟

```python
# 在live2d_assistant.py中修改PomodoroTimer初始化
self.pomodoro = PomodoroTimer(
    work_duration=50,      # 50分钟工作
    short_break=10,        # 10分钟休息
    long_break=30,         # 30分钟长休息
    pomodoros_until_long_break=3  # 3个番茄后长休息
)
```

### 批量导入日程

```python
import json

# 从JSON文件导入日程
with open('schedules.json', 'r', encoding='utf-8') as f:
    schedules_data = json.load(f)

for data in schedules_data:
    schedule = Schedule.from_dict(data)
    schedule_manager.add_schedule(schedule)
```

### 数据导出和备份

```python
import shutil
from datetime import datetime

# 备份数据库
backup_name = f"chat_agent_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
shutil.copy('chat_agent.db', backup_name)
print(f"✓ 数据库已备份: {backup_name}")

# 导出笔记为Markdown
all_notes = note_manager.get_all_notes()
with open('notes_export.md', 'w', encoding='utf-8') as f:
    for note in all_notes:
        f.write(f"# {note.title}\n\n")
        f.write(f"{note.content}\n\n")
        f.write(f"---\n\n")
```

---

💕 希望这些示例能帮助你更好地使用Live2D助手！
