# Neo Agent - Copilot 指令

## 项目概述

Neo Agent 是一个基于 LangChain 的智能对话代理系统，支持角色扮演、长期记忆管理和情感关系分析。该系统通过分层记忆架构和知识库管理实现具有持久记忆能力的智能对话体验。

**主要语言**: Python 3.8+  
**主要框架**: LangChain  
**GUI**: Tkinter  
**数据库**: SQLite  
**API**: SiliconFlow（兼容 OpenAI 格式）

## 核心架构

### 记忆层次
1. **短期记忆**: 最近 20 轮的详细对话（由 `MemoryManager` 管理）
2. **长期记忆**: 总结的历史对话（由 `LongTermMemoryManager` 管理）
3. **知识库**: 从对话中提取的持久化知识（由 `KnowledgeBase` 管理）
4. **基础知识**: 预设的不可变核心知识（由 `BaseKnowledgeManager` 管理）

### 关键组件
- `chat_agent.py` - 带记忆管理的核心对话代理
- `database_manager.py` - 统一的 SQLite 数据库操作
- `long_term_memory.py` - 长期记忆生成和管理
- `knowledge_base.py` - 知识提取和检索
- `emotion_analyzer.py` - 情感关系分析
- `event_manager.py` - 用于通知和任务的事件驱动系统
- `multi_agent_coordinator.py` - 多代理协作系统
- `agent_vision.py` - 用于环境感知模拟的视觉工具
- `gui_enhanced.py` - 主要 GUI 界面（约 3000 行）

## 开发环境设置

### 前置条件
```bash
python --version  # 应为 3.8 或更高版本
pip install -r requirements.txt
```

### 配置
1. 将 `example.env` 复制为 `.env`
2. 配置必需的环境变量：
   - `SILICONFLOW_API_KEY` - 你的 API 密钥
   - `MODEL_NAME` - LLM 模型（默认: deepseek-ai/DeepSeek-V3）
   - 角色设置（NAME、GENDER、AGE、PERSONALITY 等）
   - 记忆设置（MAX_MEMORY_MESSAGES、MAX_SHORT_TERM_ROUNDS）

### 运行应用程序
```bash
python gui_enhanced.py  # 主 GUI 应用程序
python test_event_system.py  # 测试事件系统
```

## 代码风格和约定

### Python 风格
- **文档字符串**: 为类和函数使用三引号字符串和中文描述
- **类型提示**: 使用 `typing` 模块的类型提示（List、Dict、Any、Optional）
- **导入**: 按以下顺序分组导入：标准库、第三方库、本地模块
- **命名**: 
  - 类: PascalCase（例如 `ChatAgent`、`DatabaseManager`）
  - 函数/方法: snake_case（例如 `load_memory`、`get_recent_messages`）
  - 常量: UPPER_SNAKE_CASE（例如 `MAX_MEMORY_MESSAGES`）

### 文档
- 主要文档使用中文（zh-cn）
- 英文翻译可在 docs/en/ 中找到
- 对复杂逻辑使用描述性注释
- 在适当的地方在文档字符串中包含示例

### 环境变量
- 所有可配置参数都应使用带默认值的环境变量
- 使用 `python-dotenv` 加载 `.env` 文件
- 在 `example.env` 中记录所有环境变量

## 数据库管理

### 模式
SQLite 数据库（`chat_agent.db`）包含：
- `short_term_memory` - 最近的对话历史
- `long_term_memory` - 总结的历史对话
- `knowledge_base` - 提取的知识及状态跟踪
- `base_knowledge` - 不可变的核心知识
- `environment_descriptions` - 视觉工具的环境上下文
- `events` - 事件驱动系统事件
- `event_logs` - 事件处理日志

### 最佳实践
- 始终使用 `DatabaseManager` 进行数据库操作
- 对批量操作使用事务
- 使用重试逻辑优雅地处理数据库锁
- 正确关闭数据库连接

## LLM 集成

### API 调用
- 使用 `requests` 库进行对 SiliconFlow API 的 HTTP 调用
- API 格式与 OpenAI 的聊天完成格式兼容
- 实现带指数退避的重试逻辑
- 当 DEBUG_MODE 启用时使用 `debug_logger` 记录所有 API 调用

### 提示词构建
- 使用角色个性和背景构建提示词
- 包含相关的记忆上下文（短期、长期、知识）
- 使用系统消息进行角色定义
- 保持提示词在令牌限制之下（默认: MAX_TOKENS=2000）

## 事件驱动系统

### 事件类型
1. **通知事件**: 代理立即理解并解释外部信息
2. **任务事件**: 带进度更新的复杂任务的多代理协作

### 事件管理
- 通过 `EventManager.create_event()` 创建事件
- 事件存储在数据库中并进行状态跟踪
- 支持优先级级别（LOW、NORMAL、HIGH、URGENT）
- 事件日志跟踪处理历史

## 测试

### 测试文件
- `test_event_system.py` - 演示事件系统功能
- 通过 GUI 进行手动测试是主要的验证方法

### 测试方法
- 通过 GUI 测试核心功能
- 验证跨会话的记忆持久性
- 在操作后检查数据库完整性
- 使用调试日志验证 API 集成

## 重要说明

### 记忆管理
- 短期记忆限制为 `MAX_SHORT_TERM_ROUNDS`（默认: 20）
- 当短期记忆超出容量时生成长期记忆
- 知识提取在长期记忆生成期间发生
- 基础知识是只读的，在初始化时加载

### 调试模式
- 在 `.env` 中启用 `DEBUG_MODE=True` 以进行详细日志记录
- 日志包括提示词、API 调用和响应
- 检查 `debug.log` 或 GUI 调试查看器以进行故障排查

### GUI 组件
- 使用 Tkinter 构建以实现跨平台兼容性
- 包含情感雷达图、时间线可视化
- 用于数据检查的数据库管理 GUI
- 实时调试日志查看器

### 视觉工具
- 使用 LLM 智能确定何时需要环境信息
- 如果 LLM 不可用，则回退到关键字匹配
- 通过环境描述模拟视觉感知
- 可配置的超时和令牌限制

## 常见任务

### 添加新功能
1. 检查功能是否适合现有组件结构
2. 如有需要更新数据库模式（通过 `DatabaseManager`）
3. 如果可配置，将配置添加到 `example.env`
4. 更新 `docs/zh-cn/` 中的相关文档
5. 在提交前通过 GUI 进行测试

### 修改记忆系统
- 更改应保持与现有数据的向后兼容性
- 如果模式更改，更新 `DatabaseManager` 中的迁移逻辑
- 测试跨应用程序重启的记忆持久性

### 扩展事件系统
- 新的事件类型应继承自 `NotificationEvent` 或 `TaskEvent`
- 在 `EventManager` 中注册事件处理程序
- 更新 `ChatAgent` 中的事件处理逻辑

## 资源

- [架构文档](docs/zh-cn/ARCHITECTURE.md)
- [API 文档](docs/zh-cn/API.md)
- [事件系统指南](docs/zh-cn/EVENT_SYSTEM.md)
- [快速入门指南](docs/zh-cn/QUICKSTART.md)
- [开发指南](docs/zh-cn/DEVELOPMENT.md)

## 联系方式

- Issues: https://github.com/HeDaas-Code/Neo_Agent/issues
- Discussions: https://github.com/HeDaas-Code/Neo_Agent/discussions
