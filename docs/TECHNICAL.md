# Technical Documentation / 技术文档

## 项目架构 / Project Architecture

### 目录结构 / Directory Structure

```
Neo_Agent/
├── src/                      # 源代码 / Source code
│   ├── core/                # 核心业务逻辑 / Core business logic
│   │   ├── chat_agent.py           # 对话代理主类
│   │   ├── database_manager.py     # 数据库管理器
│   │   ├── emotion_analyzer.py     # 情感分析器
│   │   ├── knowledge_base.py       # 知识库管理
│   │   ├── long_term_memory.py     # 长期记忆系统
│   │   ├── base_knowledge.py       # 基础知识管理
│   │   ├── schedule_manager.py     # 日程管理器
│   │   ├── schedule_generator.py   # 日程生成器
│   │   └── schedule_similarity_checker.py  # 日程相似度检查
│   │
│   ├── gui/                 # 图形界面 / GUI components
│   │   ├── gui_enhanced.py         # 主界面
│   │   ├── database_gui.py         # 数据库管理界面
│   │   ├── nps_gui.py             # NPS管理界面
│   │   ├── schedule_gui.py        # 日程管理界面
│   │   └── settings_migration_gui.py  # 设置迁移界面
│   │
│   ├── tools/               # 工具模块 / Utility modules
│   │   ├── agent_vision.py         # 智能体视觉工具
│   │   ├── debug_logger.py         # 调试日志工具
│   │   ├── expression_style.py     # 表达风格管理
│   │   ├── interrupt_question_tool.py  # 中断问题工具
│   │   ├── schedule_intent_tool.py # 日程意图工具
│   │   ├── settings_migration.py   # 设置迁移工具
│   │   └── tooltip_utils.py        # 提示工具
│   │
│   └── nps/                 # NPS工具系统 / NPS tool system
│       ├── nps_invoker.py          # NPS调用器
│       ├── nps_registry.py         # NPS注册表
│       └── tool/                   # NPS工具
│           └── systime.py          # 系统时间工具
│
├── tests/                   # 测试文件 / Test files
│   ├── test_chat_agent.py
│   ├── test_database_manager.py
│   └── ...
│
├── examples/                # 示例代码 / Example code
│   ├── demo_domain_feature.py
│   ├── example_schedule.py
│   └── example_schedule_similarity.py
│
├── main.py                  # 主入口 / Main entry point
├── setup.py                 # 安装脚本 / Setup script
├── requirements.txt         # 依赖列表 / Dependencies
├── example.env             # 环境变量模板 / Environment template
├── README.md               # 项目说明 / Project README
├── CONTRIBUTING.md         # 贡献指南 / Contributing guide
├── CHANGELOG.md            # 更新日志 / Changelog
└── LICENSE                 # 许可证 / License
```

### 核心模块说明 / Core Modules

#### 1. chat_agent.py - 对话代理
主要的对话代理类，负责：
- 管理对话流程
- 处理用户输入
- 调用LLM生成回复
- 管理记忆系统集成

**主要类**: `ChatAgent`

#### 2. database_manager.py - 数据库管理
统一的数据库管理接口：
- SQLite数据库操作
- 数据持久化
- 查询优化
- 数据迁移

**主要类**: `DatabaseManager`

#### 3. emotion_analyzer.py - 情感分析
情感关系分析系统：
- 印象评估
- 累计评分
- 关系分类
- 情感可视化

**主要类**: `EmotionAnalyzer`

#### 4. knowledge_base.py - 知识库
知识提取和管理：
- 知识提取
- 知识存储
- 知识检索
- 知识更新

**主要类**: `KnowledgeBase`

#### 5. long_term_memory.py - 长期记忆
长期记忆系统：
- 记忆概括
- 主题提取
- 时间线管理
- 记忆检索

**主要类**: `LongTermMemory`

### 使用方法 / Usage

#### 安装 / Installation

```bash
# 克隆仓库
git clone https://github.com/HeDaas-Code/Neo_Agent.git
cd Neo_Agent

# 安装依赖
pip install -r requirements.txt

# 或使用 setup.py 安装
pip install -e .
```

#### 配置 / Configuration

```bash
# 复制环境变量模板
cp example.env .env

# 编辑 .env 文件，设置必要的配置
# - API密钥
# - 角色设定
# - 系统参数
```

#### 运行 / Running

```bash
# 启动GUI应用
python main.py

# 或使用命令行工具（安装后）
neo-agent
```

#### 导入模块 / Importing Modules

```python
# 导入核心模块
from src.core.chat_agent import ChatAgent
from src.core.database_manager import DatabaseManager
from src.core.emotion_analyzer import EmotionAnalyzer

# 导入GUI组件
from src.gui.gui_enhanced import EnhancedChatDebugGUI

# 导入工具
from src.tools.debug_logger import get_debug_logger
from src.tools.tooltip_utils import ToolTip
```

### 开发指南 / Development Guide

#### 代码规范 / Code Standards

1. **Python风格**: 遵循 PEP 8
2. **文档字符串**: 使用中文或英文编写详细说明
3. **类型提示**: 为函数参数和返回值添加类型注解
4. **导入顺序**: 标准库 → 第三方库 → 本地模块

#### 测试 / Testing

```bash
# 运行所有测试
python -m pytest tests/

# 运行特定测试
python -m pytest tests/test_chat_agent.py

# 生成覆盖率报告
python -m pytest --cov=src tests/
```

#### 添加新功能 / Adding New Features

1. 在相应模块目录中创建新文件
2. 更新对应的 `__init__.py`
3. 添加单元测试
4. 更新文档

### 依赖管理 / Dependencies

主要依赖：
- `langchain` - LLM框架
- `langchain-community` - LangChain社区扩展
- `python-dotenv` - 环境变量管理
- `requests` - HTTP请求
- `tkinter` - GUI框架（Python标准库）

### 数据流 / Data Flow

```
用户输入 → ChatAgent → 
    ├─→ 短期记忆 (最近20轮)
    ├─→ 长期记忆 (历史概括)
    ├─→ 知识库 (提取的知识)
    ├─→ LLM API (生成回复)
    └─→ 情感分析 (更新关系)
           ↓
        生成回复 → GUI显示
```

### 记忆层次 / Memory Hierarchy

```
优先级从高到低:

1. 基础知识 (BaseKnowledge)
   - 预设的核心知识
   - 不可修改
   
2. 知识库 (KnowledgeBase)
   - 从对话中提取
   - 永久存储
   
3. 长期记忆 (LongTermMemory)
   - 历史对话概括
   - 主题和时间线
   
4. 短期记忆 (Short-term)
   - 最近20轮对话
   - 详细内容
```

### 配置参数 / Configuration Parameters

环境变量说明（在 `.env` 中配置）:

```bash
# API配置
API_BASE_URL=https://api.siliconflow.cn/v1/chat/completions
API_KEY=your_api_key_here
MODEL_NAME=Qwen/Qwen2.5-72B-Instruct

# 角色设定
CHARACTER_NAME=Neo
CHARACTER_PERSONALITY=友善、专业、有帮助
CHARACTER_BACKGROUND=智能助手
CHARACTER_HOBBIES=学习新知识、帮助用户

# 系统参数
SHORT_TERM_MEMORY_SIZE=20
LONG_TERM_SUMMARIZE_INTERVAL=20
KNOWLEDGE_EXTRACT_INTERVAL=5
DEBUG_MODE=False
```

### 扩展性 / Extensibility

#### 添加新的LLM提供商

1. 修改 `src/core/chat_agent.py` 中的API调用逻辑
2. 添加新的配置参数
3. 更新环境变量模板

#### 添加新的GUI组件

1. 在 `src/gui/` 创建新模块
2. 继承 `tkinter` 相关类
3. 在主界面中集成

#### 添加新的工具

1. 在 `src/tools/` 创建新模块
2. 实现必要的接口
3. 在需要的地方导入使用

### 性能优化 / Performance Optimization

- 使用数据库索引加速查询
- 异步处理长时间操作
- 缓存常用数据
- 批量处理数据库操作

### 安全考虑 / Security Considerations

- 不在代码中硬编码API密钥
- 使用 `.env` 文件管理敏感信息
- `.gitignore` 中排除敏感文件
- 输入验证和清理

### 故障排除 / Troubleshooting

#### 常见问题

1. **ImportError**: 确保安装了所有依赖 `pip install -r requirements.txt`
2. **API错误**: 检查 `.env` 中的API配置
3. **数据库错误**: 检查文件权限和路径

### 许可证 / License

本项目采用 MIT 许可证。详见 [LICENSE](LICENSE) 文件。

### 联系方式 / Contact

- GitHub: https://github.com/HeDaas-Code/Neo_Agent
- Issues: https://github.com/HeDaas-Code/Neo_Agent/issues
