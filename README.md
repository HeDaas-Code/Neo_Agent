# Neo Agent - 智能对话代理系统

[English](README_EN.md) | 简体中文

Neo Agent 是一个基于 LangChain 的智能对话代理系统，支持角色扮演、长效记忆管理、情感关系分析和智能日程管理。通过分层记忆架构、知识库管理和事件驱动系统，实现了具有持久化记忆能力和多模态交互能力的智能对话体验。

## ✨ 主要特性

### 🧠 分层记忆系统
- **短期记忆**：保存最近 20 轮对话的详细内容
- **长期记忆**：自动生成历史对话的概括摘要
- **知识库**：从对话中提取并持久化知识性信息
- **基础知识**：预设的不可变核心知识（最高优先级）

### 💭 智能对话能力
- **角色扮演**：支持自定义角色人设、性格、背景
- **连续对话**：上下文感知的多轮对话
- **记忆检索**：智能调用相关历史记忆
- **情感理解**：分析对话中的情感倾向

### 📊 情感关系分析
- **印象评估**：基于角色设定生成对用户的详细印象
- **累计评分**：维护一个累积的情感分数（0-100）
  - 初始评估（5轮对话后）：生成 0-35 分的基础分数
  - 更新评估（每15轮对话）：根据最新印象进行 -3 到 +3 的增量调整
- **可视化展示**：评分圆环直观展现情感关系状态
- **关系分类**：根据印象概括关系类型和情感基调

### 🖥️ 图形用户界面
- **现代化界面**：基于 Tkinter 的友好 GUI
- **实时对话**：流畅的聊天体验
- **数据可视化**：情感雷达图、时间线展示
- **独立功能标签**：
  - 📅 日程管理：独立的日程管理功能
  - 📋 事件管理：事件创建、触发和管理
  - 💾 数据库管理：可视化管理所有存储数据
  - 🔧 Debug日志：实时查看系统日志和 API 调用

### 🗄️ 数据管理
- **SQLite 存储**：统一的数据库管理
- **数据迁移**：自动从 JSON 迁移到数据库
- **备份恢复**：完整的数据导入导出
- **查询优化**：高效的数据检索

### 📅 事件驱动系统
- **通知型事件**：智能体即时理解并说明外部信息
- **任务型事件**：多智能体协作完成复杂任务
  - 理解智能体：分析任务需求
  - 规划智能体：将任务分解为步骤
  - 执行智能体：逐步完成任务
  - 验证智能体：检验任务完成情况
- **中断性提问**：任务执行中向用户提问获取必要信息
- **旁白式提示**：实时展示任务处理进度
- **可视化管理**：GUI界面管理和触发事件

### 📆 智能日程管理
- **三种日程类型**：
  - 周期日程：可重复的固定日程（如每周课程表），优先级为 CRITICAL
  - 预约日程：用户提及或意图识别创建的日程，优先级为 MEDIUM
  - 临时日程：LLM在空闲时段自动生成的补充日程，优先级为 LOW
- **智能冲突检测**：自动检测时间冲突，高优先级日程自动覆盖低优先级
- **相似度检查**：使用LLM检测同一天内相似日程，智能决定保留哪一个
- **协作确认机制**：涉及用户参与的临时日程需要用户确认
- **自然语言识别**：理解"明天下午3点开会"、"周三上午有课"等表达
- **智能生成**：查询日程时自动生成符合角色特点的临时活动
- **上下文集成**：日程信息自动融入对话，自然地讨论日程安排
- **独立GUI管理**：完整的CRUD界面、筛选器、协作确认

### 👁️ 环境域系统
- **环境描述**：模拟智能体的视觉感知能力
- **域(Domain)概念**：将多个环境组织成一个整体
  - 例如："小可家" = 小可的房间 + 客厅 + 厨房
- **精度控制**：
  - 低精度（域级别）："你在哪？" → "我在小可家"
  - 高精度（环境级别）："周围有什么？" → 详细环境描述
- **域间导航**：支持切换域时自动定位到默认环境
- **LLM智能判断**：理解语义，识别隐式需要环境信息的问题

### 🎨 个性化表达系统
- **智能体表达管理**：定义如'wc'、'hhh'等个性化表达及其含义
- **用户习惯学习**：自动识别和总结用户的表达习惯
- **动态提示词注入**：将表达风格融入对话生成

### 🔧 开发工具
- **调试日志**：详细的系统运行日志
- **配置灵活**：通过环境变量轻松配置
- **工具提示**：GUI界面的ToolTip提示功能

## 📋 系统要求

- Python 3.8 或更高版本
- 支持的操作系统：Windows、Linux、macOS

## 🚀 快速开始

### 1. 克隆项目

```bash
git clone https://github.com/HeDaas-Code/Neo_Agent.git
cd Neo_Agent
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 配置环境变量

复制 `example.env` 为 `.env` 并填入你的配置：

```bash
cp example.env .env
```

编辑 `.env` 文件，配置必要参数：

```env
# API配置
SILICONFLOW_API_KEY=your-api-key-here
SILICONFLOW_API_URL=https://api.siliconflow.cn/v1/chat/completions

# 模型配置
MODEL_NAME=deepseek-ai/DeepSeek-V3
TEMPERATURE=0.8
MAX_TOKENS=2000

# 角色设定
CHARACTER_NAME=小可
CHARACTER_GENDER=女
CHARACTER_AGE=18
CHARACTER_ROLE=学生
CHARACTER_PERSONALITY=活泼开朗
```

### 4. 运行应用

```bash
python gui_enhanced.py
```

## 📖 详细文档

> 📚 **[完整文档索引](docs/INDEX.md)** - 查看所有文档的结构化目录

### 核心文档

- [快速开始指南](docs/zh-cn/QUICKSTART.md) - 详细的安装和使用说明
- [开发指南](docs/zh-cn/DEVELOPMENT.md) - 项目结构和开发说明
- [API 文档](docs/zh-cn/API.md) - 详细的 API 接口说明
- [架构设计](docs/zh-cn/ARCHITECTURE.md) - 系统架构和设计原理

### 高级功能

- [事件系统文档](docs/zh-cn/EVENT_SYSTEM.md) - 事件驱动模块使用指南
- [事件系统架构](docs/zh-cn/ARCHITECTURE_EVENT_SYSTEM.md) - 事件驱动系统架构图
- [环境域功能](docs/zh-cn/DOMAIN_FEATURE.md) - 环境域系统使用指南
- [GUI域管理](docs/zh-cn/GUI_DOMAIN_FEATURE.md) - 可视化域管理界面

### 更多文档

所有文档均已整理至 [docs](docs/) 文件夹，包含中英文双语版本。

## 🏗️ 项目结构

```
Neo_Agent/
├── gui_enhanced.py              # 主GUI界面
├── chat_agent.py               # 对话代理核心
├── database_manager.py         # 数据库管理
├── database_gui.py             # 数据库GUI管理
├── long_term_memory.py         # 长效记忆管理
├── knowledge_base.py           # 知识库管理
├── base_knowledge.py           # 基础知识管理（不可变核心知识）
├── emotion_analyzer.py         # 情感分析
├── agent_vision.py             # 视觉工具（环境域系统）
├── event_manager.py            # 事件管理
├── multi_agent_coordinator.py  # 多智能体协作
├── interrupt_question_tool.py  # 中断性提问工具
├── schedule_manager.py         # 日程管理核心
├── schedule_gui.py             # 日程管理独立GUI
├── schedule_intent_tool.py     # 日程意图识别
├── schedule_generator.py       # 临时日程生成
├── schedule_similarity_checker.py  # 日程相似度检查
├── expression_style.py         # 表达风格管理
├── debug_logger.py             # 调试日志
├── tooltip_utils.py            # 工具提示组件
├── tests/                      # 单元测试目录
├── docs/                       # 文档目录（中英文双语）
├── requirements.txt            # 项目依赖
├── example.env                 # 环境变量示例
└── README.md                   # 项目说明
```

## 🎯 使用场景

- **个人助手**：具有记忆能力的私人 AI 助手
- **角色扮演**：创建具有特定人设的对话角色
- **客服机器人**：记住用户历史的智能客服
- **学习伴侣**：能够积累知识的学习助手
- **情感陪伴**：理解和响应情感的陪伴机器人

## ⚙️ 核心配置

### 角色设定
通过 `.env` 文件配置角色的基本信息：
- `CHARACTER_NAME`：角色名称
- `CHARACTER_GENDER`：性别
- `CHARACTER_AGE`：年龄
- `CHARACTER_ROLE`：角色定位
- `CHARACTER_PERSONALITY`：性格特点
- `CHARACTER_HOBBY`：爱好特长
- `CHARACTER_BACKGROUND`：详细背景描述

### 记忆设置
- `MAX_MEMORY_MESSAGES`：最大记忆消息数（默认 50）
- `MAX_SHORT_TERM_ROUNDS`：短期记忆轮数（默认 20）

### 模型设置
- `MODEL_NAME`：使用的 LLM 模型
- `TEMPERATURE`：生成温度（0-1）
- `MAX_TOKENS`：最大生成长度

## 🔍 功能演示

### 对话界面
- 支持实时对话
- 显示历史消息
- 自动保存对话记录
- 角色扮演对话

### 情感分析
- 点击"分析情感关系"按钮
- 查看印象评分和详细印象描述
- 了解当前情感状态和关系类型
- 累计评分系统（0-100分）

### 日程管理
- 独立的「📅 日程管理」标签页
- 添加/编辑/删除日程
- 筛选（按类型/日期/状态）
- 协作确认功能

### 事件管理
- 创建通知型/任务型事件
- 触发事件并查看处理结果
- 多智能体协作完成复杂任务

### 数据库管理
- 查看所有记忆数据
- 管理知识库内容
- 环境域管理
- 导入导出数据

## 🛠️ 开发

### 调试模式
启用调试模式以查看详细日志：

```env
DEBUG_MODE=True
DEBUG_LOG_FILE=debug.log
```

### 扩展开发
1. 查看 [开发指南](docs/zh-cn/DEVELOPMENT.md) 了解项目结构
2. 参考 [API 文档](docs/zh-cn/API.md) 了解接口定义
3. 阅读 [架构设计](docs/zh-cn/ARCHITECTURE.md) 理解系统设计

## 💡 使用示例

### 日程管理示例

智能体的日程管理功能可以自然地融入对话中：

```python
# 用户询问日程
用户: 你今天有什么安排吗？
智能体: [自动生成临时日程] 让我看看...我今天安排了下午2点看会儿书，晚上7点可以放松一下看个电影~

# 用户创建预约
用户: 我们明天下午3点一起去图书馆吧
智能体: [识别意图并创建日程] 好呀！我已经记下来了，明天下午3点一起去图书馆📚

# 周期日程
# 可通过代码创建周期日程，如课程表
agent.schedule_manager.create_schedule(
    title="英语课",
    description="每周一的英语课",
    schedule_type=ScheduleType.RECURRING,
    start_time="2024-01-15T09:00:00",
    end_time="2024-01-15T11:00:00",
    weekday=0,  # 周一
    recurrence_pattern="每周一"
)

# 用户参与的临时日程需要确认
智能体: 我想我们晚上一起看电影吧，你觉得怎么样？
用户: 好啊
智能体: [确认协作日程] 太好了！那我们今晚一起看电影✨
```

### 日程特性

1. **自动冲突检测**：创建日程时自动检查时间冲突
2. **优先级管理**：
   - 周期日程（如课程）：CRITICAL - 不可覆盖
   - 重要预约：HIGH - 可覆盖临时和一般预约
   - 一般预约：MEDIUM - 可覆盖临时日程
   - 临时日程：LOW - 可被任何其他日程覆盖

3. **智能生成**：当用户询问日程时，如果没有临时日程，系统会：
   - 分析空闲时间段
   - 根据角色特点生成1-3个合理的临时活动
   - 考虑时间段特点（早上适合学习，晚上适合放松）

4. **协作确认**：涉及用户的临时日程会：
   - 设置为"待确认"状态
   - 暂时不显示在日程查询中
   - 等待用户确认后才正式生效

## 🤝 贡献

欢迎贡献代码、报告问题或提出建议！

1. Fork 本项目
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

## 📝 许可证

本项目采用 MIT 许可证。详见 [LICENSE](LICENSE) 文件。

## 🙏 致谢

- [LangChain](https://github.com/langchain-ai/langchain) - 强大的 LLM 应用框架
- [SiliconFlow](https://siliconflow.cn/) - 提供 API 服务
- 所有贡献者和支持者

## 📧 联系方式

如有问题或建议，请通过以下方式联系：

- 提交 [Issue](https://github.com/HeDaas-Code/Neo_Agent/issues)
- 发起 [Discussion](https://github.com/HeDaas-Code/Neo_Agent/discussions)

## 🌟 Star History

如果这个项目对你有帮助，请给它一个 ⭐️！

---

由 ❤️ 驱动，为智能对话而生
