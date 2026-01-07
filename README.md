# Neo Agent - 智能对话代理系统

[English](README_EN.md) | 简体中文

Neo Agent 是一个基于 LangChain 的智能对话代理系统，支持角色扮演、长效记忆管理和情感关系分析。通过分层记忆架构和知识库管理，实现了具有持久化记忆能力的智能对话体验。

## ✨ 主要特性

### 🧠 分层记忆系统
- **短期记忆**：保存最近 20 轮对话的详细内容
- **长期记忆**：自动生成历史对话的概括摘要
- **知识库**：从对话中提取并持久化知识性信息
- **基础知识**：预设的不可变核心知识

### 💭 智能对话能力
- **角色扮演**：支持自定义角色人设和性格
- **连续对话**：上下文感知的多轮对话
- **记忆检索**：智能调用相关历史记忆
- **情感理解**：分析对话中的情感倾向

### 📊 情感关系分析
- **印象评估**：基于角色设定生成对用户的详细印象
- **智能评分**：根据印象的正负面倾向给出0-100分的评分
- **可视化展示**：评分圆环直观展现情感关系状态
- **动态更新**：基于最近15轮对话实时更新情感印象

### 🖥️ 图形用户界面
- **现代化界面**：基于 Tkinter 的友好 GUI
- **实时对话**：流畅的聊天体验
- **数据可视化**：情感雷达图、时间线展示
- **数据库管理**：可视化管理所有存储数据
- **调试工具**：实时查看系统日志和 API 调用

### 🗄️ 数据管理
- **SQLite 存储**：统一的数据库管理
- **数据迁移**：自动从 JSON 迁移到数据库
- **备份恢复**：完整的数据导入导出
- **查询优化**：高效的数据检索

### 📅 事件驱动系统
- **通知型事件**：智能体即时理解并说明外部信息
- **任务型事件**：多智能体协作完成复杂任务
- **中断性提问**：任务执行中向用户提问
- **旁白式提示**：实时展示任务处理进度
- **可视化管理**：GUI界面管理和触发事件

### 🔧 扩展功能
- **智能视觉能力**：使用LLM智能判断是否需要环境信息，通过环境描述模拟视觉感知
  - LLM智能判断：理解语义，识别如"你在哪？"等隐式需要环境信息的问题
  - 关键词匹配备用：当LLM不可用时自动降级到关键词匹配
- **个性化表达风格**：管理智能体的独特表达方式和学习用户习惯
  - 智能体表达管理：定义如'wc'、'hhh'等个性化表达及其含义
  - 用户习惯学习：自动识别和总结用户的表达习惯
  - 动态提示词注入：将表达风格融入对话生成
- **调试日志**：详细的系统运行日志
- **配置灵活**：通过环境变量轻松配置

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

### 事件驱动系统

- [事件系统文档](docs/zh-cn/EVENT_SYSTEM.md) - 事件驱动模块使用指南
- [事件系统架构](docs/zh-cn/ARCHITECTURE_EVENT_SYSTEM.md) - 事件驱动系统架构图

### 更多文档

所有文档均已整理至 [docs](docs/) 文件夹，包含中英文双语版本。

## 🏗️ 项目结构

```
Neo_Agent/
├── gui_enhanced.py              # 主GUI界面
├── chat_agent.py               # 对话代理核心
├── database_manager.py         # 数据库管理
├── long_term_memory.py         # 长效记忆管理
├── knowledge_base.py           # 知识库管理
├── emotion_analyzer.py         # 情感分析
├── agent_vision.py             # 视觉工具
├── event_manager.py            # 事件管理
├── multi_agent_coordinator.py  # 多智能体协作
├── interrupt_question_tool.py  # 中断性提问工具
├── expression_style.py         # 表达风格管理
├── debug_logger.py             # 调试日志
├── database_gui.py             # 数据库GUI管理
├── base_knowledge.py           # 基础知识管理
├── requirements.txt         # 项目依赖
├── example.env             # 环境变量示例
└── README.md               # 项目说明
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

### 情感分析
- 点击"分析情感关系"按钮
- 查看印象评分和详细印象描述
- 了解当前情感状态和关系类型

### 数据库管理
- 查看所有记忆数据
- 管理知识库内容
- 导入导出数据

## 🛠️ 开发

### 调试模式
启用调试模式以查看详细日志：

```env
DEBUG_MODE=True
DEBUG_LOG_FILE=debug.log
```

### 扩展开发
1. 查看 [开发指南](DEVELOPMENT.md) 了解项目结构
2. 参考 [API 文档](API.md) 了解接口定义
3. 阅读 [架构设计](ARCHITECTURE.md) 理解系统设计

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
