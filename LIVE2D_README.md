# Live2D桌宠助手 - 小可 🌸

## 项目简介

Live2D桌宠助手是基于Neo_Agent项目开发的智能桌面助手，扮演女高中生"小可"的角色，为用户提供日常学习和生活管理功能。小可不仅可以像桌宠一样陪伴你，还能帮助你管理时间、记录笔记、安排日程和追踪计划。

## 主要特性

### 🍅 番茄时钟
- **标准番茄工作法**：25分钟工作 + 5分钟休息
- **灵活配置**：可自定义工作和休息时长
- **自动提醒**：工作和休息时段自动提醒
- **进度追踪**：显示今日完成的番茄数量
- **暂停恢复**：支持暂停和继续功能

### 📅 日程管理
- **日程创建**：轻松创建日程安排
- **智能提醒**：提前提醒即将到来的日程
- **优先级管理**：支持设置日程优先级
- **状态跟踪**：待办、进行中、已完成等状态
- **时间筛选**：按日期范围查看日程

### 📝 笔记管理
- **快速记录**：随时记录想法和笔记
- **分类整理**：支持分类和标签管理
- **全文搜索**：快速搜索笔记内容
- **置顶功能**：重要笔记可置顶显示
- **编辑查看**：方便的编辑和查看界面

### 🎯 计划管理
- **长期规划**：创建和跟踪长期计划
- **任务分解**：将计划分解为可执行任务
- **进度可视化**：实时显示计划完成进度
- **状态管理**：未开始、进行中、已完成等状态
- **统计分析**：查看计划完成情况统计

### 💬 智能对话
- **角色扮演**：小可会以女高中生的身份与你交流
- **记忆功能**：记住你们的对话历史
- **情感理解**：理解你的情感并给予回应
- **主动提醒**：在合适的时候主动提醒你

### 🖥️ 桌面宠物特性
- **窗口置顶**：可选择窗口始终置顶
- **紧凑界面**：400x650的紧凑设计，不占用太多空间
- **多标签切换**：便捷的标签页设计
- **实时统计**：查看各项功能的使用统计

## 安装与配置

### 1. 环境要求

- Python 3.8 或更高版本
- 支持的操作系统：Windows、Linux、macOS

### 2. 安装依赖

```bash
cd Neo_Agent
pip install -r requirements.txt
```

### 3. 配置环境变量

复制 `example.env` 为 `.env` 并配置：

```bash
cp example.env .env
```

编辑 `.env` 文件：

```env
# API配置（用于智能对话功能）
SILICONFLOW_API_KEY=your-api-key
SILICONFLOW_API_URL=https://api.siliconflow.cn/v1/chat/completions

# LLM模型配置
MODEL_NAME=deepseek-ai/DeepSeek-V3
TEMPERATURE=0.8
MAX_TOKENS=2000

# 角色设定（小可的人设）
CHARACTER_NAME=小可
CHARACTER_GENDER=女
CHARACTER_ROLE=学生
CHARACTER_AGE=18
CHARACTER_HEIGHT=150cm
CHARACTER_WEIGHT=45kg
CHARACTER_PERSONALITY=活泼开朗
CHARACTER_HOBBY=文科，尤其对历史充满热情
CHARACTER_BACKGROUND=我是一名高中生，叫小可。我身高150cm，体重45kg。我性格活泼开朗，特别喜欢文科，尤其对历史充满热情。我喜欢阅读历史书籍，常常能从历史故事中获得启发。我说话比较俏皮可爱，喜欢和朋友们分享有趣的历史知识。

# Debug模式
DEBUG_MODE=True
DEBUG_LOG_FILE=debug.log
```

### 4. 启动应用

```bash
python live2d_assistant.py
```

## 使用指南

### 番茄时钟使用

1. 切换到"🍅 番茄时钟"标签页
2. 点击"开始工作"按钮开始25分钟的工作时段
3. 专注工作，计时器会实时显示剩余时间
4. 工作完成后，系统会自动提醒并开始休息时段
5. 休息结束后可以开始下一个番茄

**小贴士**：
- 可以随时暂停或停止计时
- 每完成4个番茄会有一次长休息（15分钟）
- 番茄数统计帮助你了解每天的工作效率

### 日程管理使用

1. 切换到"📅 日程"标签页
2. 点击"+ 新建日程"创建新日程
3. 填写日程标题和描述
4. 系统会在日程开始前15分钟提醒你
5. 双击日程可查看详情

**小贴士**：
- 小可会主动提醒即将到来的日程
- 可以通过列表快速浏览所有日程
- 过期的日程会自动标记为过期状态

### 笔记管理使用

1. 切换到"📝 笔记"标签页
2. 点击"+ 新建笔记"创建笔记
3. 输入标题和内容后保存
4. 双击笔记可查看完整内容
5. 支持按分类和标签整理笔记

**小贴士**：
- 重要笔记可以置顶显示
- 使用搜索功能快速找到需要的笔记
- 笔记会自动记录创建和更新时间

### 计划管理使用

1. 切换到"🎯 计划"标签页
2. 点击"+ 新建计划"创建长期计划
3. 为计划添加具体任务
4. 完成任务后标记为已完成
5. 系统会自动计算计划完成进度

**小贴士**：
- 将大目标分解为小任务更容易完成
- 定期查看计划进度保持动力
- 可以暂停或取消不适合的计划

### 与小可聊天

1. 切换到"💬 聊天"标签页
2. 在输入框输入消息并发送
3. 小可会以女高中生的身份回复你
4. 小可会记住你们的对话历史

**小贴士**：
- 可以向小可询问任何问题
- 小可会根据你的日程和计划主动提醒
- 和小可多聊天，她会更了解你

### 查看统计

1. 切换到"📊 统计"标签页
2. 查看各项功能的使用情况
3. 了解自己的学习和工作状态
4. 点击"刷新统计"更新数据

## 功能特色

### 智能提醒系统

小可会根据你的日程安排主动提醒你：
- 日程开始前15分钟提醒
- 番茄时钟工作/休息时段提醒
- 过期日程自动标记
- 计划进度更新提示

### 数据持久化

所有数据都保存在SQLite数据库中：
- 日程数据 (schedules表)
- 笔记数据 (notes表)
- 计划数据 (plans表)
- 聊天记录 (通过chat_agent.db)

### 桌面宠物模式

- 窗口可以设置为始终置顶
- 紧凑的界面设计不遮挡工作区域
- 右键菜单快速操作
- 可最小化到系统托盘（Windows）

## 技术架构

### 核心模块

```
live2d_assistant.py         # 主界面和应用入口
├── pomodoro_timer.py       # 番茄时钟模块
├── schedule_manager.py     # 日程管理模块
├── note_manager.py         # 笔记管理模块
├── plan_manager.py         # 计划管理模块
├── chat_agent.py           # 智能对话模块
└── database_manager.py     # 数据库管理模块
```

### 数据库结构

```sql
-- 日程表
CREATE TABLE schedules (
    schedule_id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    description TEXT,
    start_time TEXT NOT NULL,
    end_time TEXT NOT NULL,
    priority INTEGER,
    status TEXT,
    remind_before INTEGER,
    tags TEXT,
    created_at TEXT,
    metadata TEXT
);

-- 笔记表
CREATE TABLE notes (
    note_id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    content TEXT,
    tags TEXT,
    category TEXT,
    is_pinned INTEGER,
    created_at TEXT,
    updated_at TEXT,
    metadata TEXT
);

-- 计划表
CREATE TABLE plans (
    plan_id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    description TEXT,
    goal TEXT,
    start_date TEXT,
    target_date TEXT,
    status TEXT,
    tasks TEXT,
    progress REAL,
    created_at TEXT,
    updated_at TEXT,
    metadata TEXT
);
```

## 常见问题

### Q: 如何让小可一直显示在桌面上？
A: 在主窗口右键，选择"置顶"选项，或在设置中启用"始终置顶"。

### Q: 番茄时钟可以自定义时长吗？
A: 目前使用标准的25分钟工作时长。如需自定义，可以修改 `live2d_assistant.py` 中 `PomodoroTimer` 的初始化参数。

### Q: 数据保存在哪里？
A: 所有数据保存在项目目录下的 `chat_agent.db` SQLite数据库文件中。

### Q: 可以关闭智能对话功能吗？
A: 可以。智能对话需要API密钥，如果不配置API密钥，对话功能将不可用，但其他功能正常。

### Q: 如何备份我的数据？
A: 复制 `chat_agent.db` 文件即可备份所有数据。

### Q: 小可会自动启动吗？
A: 需要手动启动。如需开机自动启动，可以将启动脚本添加到系统启动项。

## 开发与扩展

### 添加新功能

如果你想为小可添加新功能，可以：

1. 在相应的管理器模块中添加功能
2. 在 `live2d_assistant.py` 中添加对应的UI
3. 连接功能逻辑和UI
4. 编写测试确保功能正常

### 自定义小可的人设

编辑 `.env` 文件中的角色设定：

```env
CHARACTER_NAME=你的角色名
CHARACTER_PERSONALITY=你想要的性格
CHARACTER_BACKGROUND=详细的背景描述
```

### 修改界面样式

主界面使用tkinter的ttk主题，可以通过修改样式配置来改变外观。

## 贡献

欢迎提交问题和改进建议！

## 许可证

本项目基于Neo_Agent项目开发，遵循MIT许可证。

## 致谢

- Neo_Agent项目团队
- 所有贡献者和用户

---

💕 愿小可能成为你的好伙伴，陪伴你度过每一天！
