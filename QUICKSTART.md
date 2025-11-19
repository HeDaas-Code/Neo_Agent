# 快速开始指南

[English](QUICKSTART_EN.md) | 简体中文

本指南将帮助你快速上手 Neo Agent 智能对话代理系统。

## 📋 前置条件

在开始之前，请确保你的系统满足以下要求：

- **Python**：3.8 或更高版本
- **pip**：Python 包管理器
- **操作系统**：Windows、Linux 或 macOS
- **网络连接**：需要访问 API 服务

### 检查 Python 版本

```bash
python --version
# 或
python3 --version
```

如果版本低于 3.8，请先升级 Python。

## 🔧 安装步骤

### 1. 获取项目代码

#### 方式一：使用 Git 克隆

```bash
git clone https://github.com/HeDaas-Code/Neo_Agent.git
cd Neo_Agent
```

#### 方式二：下载压缩包

1. 访问 [项目主页](https://github.com/HeDaas-Code/Neo_Agent)
2. 点击 "Code" -> "Download ZIP"
3. 解压到你喜欢的目录
4. 进入项目目录

### 2. 创建虚拟环境（推荐）

使用虚拟环境可以避免依赖冲突：

```bash
# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
# Windows:
venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate
```

### 3. 安装依赖包

```bash
pip install -r requirements.txt
```

依赖包列表：
- `langchain>=0.1.0` - LLM 应用框架
- `langchain-community>=0.0.10` - LangChain 社区组件
- `langchain-core>=0.1.0` - LangChain 核心库
- `python-dotenv>=1.0.0` - 环境变量管理
- `requests>=2.31.0` - HTTP 请求库

### 4. 配置环境变量

#### 复制配置模板

```bash
cp example.env .env
```

#### 编辑 .env 文件

使用文本编辑器打开 `.env` 文件，填入必要的配置：

```env
# ========== API 配置 ==========
# 必填：你的 API 密钥
SILICONFLOW_API_KEY=your-api-key-here

# API 服务地址（通常不需要修改）
SILICONFLOW_API_URL=https://api.siliconflow.cn/v1/chat/completions

# ========== 模型配置 ==========
# LLM 模型名称
MODEL_NAME=deepseek-ai/DeepSeek-V3

# 生成温度 (0-1)，越高越有创造性
TEMPERATURE=0.8

# 最大生成 token 数
MAX_TOKENS=2000

# ========== 角色设定 ==========
# 角色名称
CHARACTER_NAME=小可

# 性别
CHARACTER_GENDER=女

# 年龄
CHARACTER_AGE=18

# 角色定位
CHARACTER_ROLE=学生

# 身高体重
CHARACTER_HEIGHT=150cm
CHARACTER_WEIGHT=45kg

# 性格特点
CHARACTER_PERSONALITY=活泼开朗

# 爱好特长
CHARACTER_HOBBY=文科，尤其对历史充满热情

# 详细背景描述
CHARACTER_BACKGROUND=我是一名高中生，叫小可。我身高150cm，体重45kg。我性格活泼开朗，特别喜欢文科，尤其对历史充满热情。我喜欢阅读历史书籍，常常能从历史故事中获得启发。我说话比较俏皮可爱，喜欢和朋友们分享有趣的历史知识。

# ========== 记忆设置 ==========
# 记忆文件路径（使用数据库后这些配置保留用于兼容）
MEMORY_FILE=memory_data.json
LONG_MEMORY_FILE=longmemory_data.json

# 最大记忆消息数
MAX_MEMORY_MESSAGES=50

# 短期记忆最大轮数
MAX_SHORT_TERM_ROUNDS=20

# ========== 调试设置 ==========
# 是否启用调试模式
DEBUG_MODE=True

# 调试日志文件
DEBUG_LOG_FILE=debug.log
```

### 5. 获取 API 密钥

#### SiliconFlow API

1. 访问 [SiliconFlow 官网](https://siliconflow.cn/)
2. 注册账号并登录
3. 进入控制台，创建 API 密钥
4. 复制密钥并填入 `.env` 文件的 `SILICONFLOW_API_KEY`

#### 其他 API 提供商

如果使用其他 API 提供商（如 OpenAI、Azure OpenAI 等），需要：
1. 修改 `SILICONFLOW_API_URL` 为对应的 API 地址
2. 调整 `MODEL_NAME` 为对应的模型名称
3. 可能需要修改代码中的 API 调用格式

## 🚀 运行应用

### 启动图形界面

```bash
python gui_enhanced.py
```

第一次运行时，系统会：
1. 初始化 SQLite 数据库
2. 创建必要的数据表
3. 检查并迁移旧的 JSON 数据（如果存在）

### 使用界面

#### 主界面功能

1. **聊天区域**：显示对话历史
2. **输入框**：输入你的消息
3. **发送按钮**：发送消息（或按 Enter）
4. **清除记忆**：清空所有对话历史
5. **分析情感**：生成情感关系雷达图
6. **数据库管理**：打开数据库管理界面
7. **Debug日志**：查看系统运行日志

#### 开始对话

1. 在输入框中输入消息
2. 按 Enter 键或点击"发送"按钮
3. 等待 AI 回复
4. 继续对话...

#### 查看情感分析

1. 进行几轮对话后
2. 点击"分析情感关系"按钮
3. 在右侧查看五维度雷达图
4. 了解当前的情感关系状态

#### 管理数据库

1. 点击"数据库管理"按钮
2. 在新窗口中查看和管理：
   - 短期记忆
   - 长期记忆
   - 知识库
   - 基础知识
   - 环境描述
3. 可以添加、编辑、删除数据
4. 支持导入导出备份

## 🎯 使用技巧

### 自定义角色

在 `.env` 文件中修改角色设定：

```env
CHARACTER_NAME=小明
CHARACTER_GENDER=男
CHARACTER_AGE=25
CHARACTER_ROLE=程序员
CHARACTER_PERSONALITY=沉稳理性，善于分析问题
CHARACTER_HOBBY=编程、读书、思考
CHARACTER_BACKGROUND=我是一名软件工程师，热爱技术，善于解决复杂问题...
```

修改后重启应用即可生效。

### 调整记忆容量

根据需求调整记忆系统的容量：

```env
# 短期记忆保留 30 轮对话
MAX_SHORT_TERM_ROUNDS=30

# 最大记忆消息数 100 条
MAX_MEMORY_MESSAGES=100
```

### 切换模型

尝试不同的 LLM 模型：

```env
# 使用 Qwen 模型
MODEL_NAME=Qwen/Qwen2.5-7B-Instruct

# 使用 DeepSeek 模型
MODEL_NAME=deepseek-ai/DeepSeek-V3
```

### 调整生成参数

控制 AI 的回复风格：

```env
# 更有创造性（0.8-1.0）
TEMPERATURE=0.9

# 更稳定保守（0.3-0.5）
TEMPERATURE=0.4

# 更长的回复
MAX_TOKENS=3000

# 更简洁的回复
MAX_TOKENS=1000
```

## 🐛 故障排除

### 问题：无法启动应用

**可能原因**：
- Python 版本太低
- 依赖包未安装完整

**解决方案**：
```bash
# 检查 Python 版本
python --version

# 重新安装依赖
pip install -r requirements.txt --upgrade
```

### 问题：API 调用失败

**可能原因**：
- API 密钥无效
- 网络连接问题
- API 服务异常

**解决方案**：
1. 检查 `.env` 中的 `SILICONFLOW_API_KEY` 是否正确
2. 测试网络连接
3. 查看 Debug 日志了解详细错误

### 问题：数据库错误

**可能原因**：
- 数据库文件损坏
- 权限问题

**解决方案**：
```bash
# 删除数据库重新初始化
rm chat_agent.db
python gui_enhanced.py
```

### 问题：界面显示异常

**可能原因**：
- Tkinter 未正确安装
- 系统缺少相关库

**解决方案**：
```bash
# Ubuntu/Debian
sudo apt-get install python3-tk

# macOS
brew install python-tk

# Windows 通常自带 Tkinter
```

## 📚 下一步

- 阅读 [开发指南](DEVELOPMENT.md) 了解项目结构
- 查看 [API 文档](API.md) 学习接口调用
- 探索 [架构设计](ARCHITECTURE.md) 理解系统原理

## 💡 常见问题

### Q: 可以离线使用吗？

A: 不可以。系统需要调用在线 LLM API 服务。

### Q: 支持哪些 LLM 模型？

A: 理论上支持所有兼容 OpenAI API 格式的模型服务。

### Q: 数据存储在哪里？

A: 所有数据存储在本地 SQLite 数据库 `chat_agent.db` 中。

### Q: 可以同时运行多个实例吗？

A: 可以，但需要使用不同的数据库文件路径。

### Q: 如何备份数据？

A: 直接复制 `chat_agent.db` 文件，或使用数据库管理界面的导出功能。

## 🆘 获取帮助

如果遇到问题：

1. 查看本指南的故障排除部分
2. 检查 [Issues](https://github.com/HeDaas-Code/Neo_Agent/issues)
3. 提交新的 Issue 描述问题
4. 加入社区讨论

---

祝你使用愉快！🎉
