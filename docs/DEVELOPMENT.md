# 开发指南

**中文** | [English](DEVELOPMENT_EN.md)

本文档面向想要了解项目内部机制、进行二次开发或贡献代码的开发者。

## 目录

- [开发环境搭建](#开发环境搭建)
- [项目架构](#项目架构)
- [核心模块详解](#核心模块详解)
- [开发流程](#开发流程)
- [调试技巧](#调试技巧)
- [最佳实践](#最佳实践)
- [常见开发任务](#常见开发任务)

---

## 开发环境搭建

### 1. 基础环境

```bash
# 克隆仓库
git clone https://github.com/HeDaas-Code/Neo_Agent.git
cd Neo_Agent

# 创建虚拟环境
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装开发依赖
pip install -r requirements.txt

# 配置开发环境变量
cp example.env .env
# 编辑 .env，设置 DEBUG_MODE=True
```

### 2. 开发工具推荐

- **IDE**: PyCharm, VS Code
- **代码格式化**: black, autopep8
- **类型检查**: mypy
- **Linter**: pylint, flake8
- **Git GUI**: GitKraken, SourceTree

### 3. VS Code配置

创建 `.vscode/settings.json`：

```json
{
    "python.linting.enabled": true,
    "python.linting.pylintEnabled": true,
    "python.formatting.provider": "black",
    "python.formatting.blackArgs": ["--line-length", "100"],
    "editor.formatOnSave": true,
    "files.exclude": {
        "**/__pycache__": true,
        "**/*.pyc": true
    }
}
```

---

## 项目架构

### 目录结构

```
Neo_Agent/
├── chat_agent.py              # 核心对话代理
├── long_term_memory.py        # 长期记忆管理
├── knowledge_base.py          # 知识库管理
├── base_knowledge.py          # 基础知识库
├── emotion_analyzer.py        # 情感关系分析
├── database_manager.py        # 数据库管理
├── database_gui.py            # 数据库GUI
├── debug_logger.py            # 调试日志
├── gui_enhanced.py            # 增强版GUI
├── .env                       # 环境配置（不提交）
├── example.env                # 配置模板
├── requirements.txt           # Python依赖
├── README.md                  # 项目主文档
├── CONTRIBUTING.md            # 贡献指南
├── CHANGELOG.md               # 变更日志
├── LICENSE                    # 许可证
└── docs/                      # 详细文档
    ├── API.md                 # API文档
    ├── DEPLOYMENT.md          # 部署指南
    ├── DEVELOPMENT.md         # 本文件
    ├── EXAMPLES.md            # 使用示例
    └── TROUBLESHOOTING.md     # 故障排查
```

### 模块依赖关系

```
gui_enhanced.py
    ↓
chat_agent.py (核心)
    ├─→ database_manager.py (数据持久化)
    ├─→ long_term_memory.py (记忆管理)
    │       └─→ database_manager.py
    ├─→ knowledge_base.py (知识管理)
    │       └─→ database_manager.py
    ├─→ base_knowledge.py (基础知识)
    ├─→ emotion_analyzer.py (情感分析)
    │       └─→ database_manager.py
    └─→ debug_logger.py (日志)
```

---

## 核心模块详解

### 1. chat_agent.py - 对话代理

**核心职责**：
- 对话流程控制
- 记忆管理调度
- 知识检索
- 情感分析触发

**关键类和方法**：

```python
class ChatAgent:
    def __init__(self):
        # 初始化各个管理器
        self.db_manager = DatabaseManager()
        self.memory_manager = MemoryManager()
        self.ltm_manager = LongTermMemoryManager()
        self.kb = KnowledgeBase()
        self.emotion_analyzer = EmotionRelationshipAnalyzer()
    
    def chat(self, user_input: str) -> str:
        """主要对话方法，处理完整的对话流程"""
        # 1. 添加用户消息到记忆
        # 2. 检查触发条件（5轮、10轮、20轮）
        # 3. 实体识别和知识检索
        # 4. 构建提示词
        # 5. 调用LLM
        # 6. 保存响应
        # 7. 返回结果
```

**开发要点**：
- 修改触发频率：调整 `% 5`, `% 10`, `% 20` 的条件
- 添加新功能：在 `chat()` 方法中插入逻辑
- 调试：启用DEBUG_MODE查看完整流程

### 2. database_manager.py - 数据管理

**核心职责**：
- 统一数据存储接口
- JSON序列化/反序列化
- 数据持久化

**关键方法**：

```python
class DatabaseManager:
    def save_data(self, key: str, data: Any):
        """保存数据到数据库"""
    
    def load_data(self, key: str, default: Any = None):
        """从数据库加载数据"""
    
    def delete_data(self, key: str):
        """删除数据"""
```

**开发要点**：
- 所有数据通过此类访问
- 自动处理JSON序列化
- 使用SQLite作为底层存储

### 3. long_term_memory.py - 长期记忆

**核心职责**：
- 短期记忆归档
- 生成主题概括
- 长期记忆检索

**关键方法**：

```python
class LongTermMemoryManager:
    def archive_short_term_memory(self, messages: List[Dict]) -> Dict:
        """将短期记忆归档为长期记忆"""
        # 1. 提取对话内容
        # 2. 调用LLM生成概括
        # 3. 创建UUID
        # 4. 保存到数据库
```

**开发要点**：
- 概括质量取决于LLM模型
- 可以自定义概括提示词
- UUID确保唯一性

### 4. knowledge_base.py - 知识库

**核心职责**：
- 自动知识提取
- 知识结构化存储
- 知识检索和匹配

**关键方法**：

```python
class KnowledgeBase:
    def extract_knowledge(self, messages: List[Dict]) -> List[Dict]:
        """从对话中提取知识"""
        # 1. 构建提取提示词
        # 2. 调用LLM分析
        # 3. 解析JSON结果
        # 4. 生成UUID和元数据
        # 5. 保存到数据库
    
    def search_knowledge(self, query: str) -> List[Dict]:
        """搜索相关知识"""
```

**开发要点**：
- 知识分类可扩展
- 支持自定义提取逻辑
- 可以调整置信度计算

### 5. emotion_analyzer.py - 情感分析

**核心职责**：
- 多维度情感评估
- 关系类型识别
- 语气提示生成

**关键方法**：

```python
class EmotionRelationshipAnalyzer:
    def analyze_emotion_relationship(self, messages: List[Dict]) -> Dict:
        """分析情感关系"""
        # 1. 提取对话内容
        # 2. 构建分析提示词
        # 3. 调用LLM分析
        # 4. 解析5维度评分
        # 5. 计算总分和关系类型
        # 6. 保存到数据库
    
    def generate_tone_prompt(self, emotion_data: Dict) -> str:
        """生成语气提示"""
```

**开发要点**：
- 5个维度可以修改
- 关系类型阈值可调整
- 语气提示可自定义

### 6. gui_enhanced.py - 图形界面

**核心职责**：
- 用户交互界面
- 数据可视化
- 实时更新显示

**关键组件**：

```python
class EnhancedChatGUI:
    def __init__(self):
        # 创建GUI组件
        self.create_widgets()
        self.setup_layout()
    
    def send_message(self):
        """处理发送消息"""
        # 在新线程中调用agent.chat()
        # 避免阻塞GUI
    
    def update_visualization(self):
        """更新可视化组件"""
        # 更新时间线、雷达图等
```

**开发要点**：
- GUI操作在主线程
- LLM调用在后台线程
- Canvas用于绘图

---

## 开发流程

### 1. 功能开发流程

```
1. 创建功能分支
   git checkout -b feature/your-feature

2. 设计功能
   - 明确需求
   - 设计接口
   - 规划数据结构

3. 实现功能
   - 编写核心代码
   - 添加注释
   - 处理异常

4. 测试
   - 单元测试
   - 集成测试
   - 手动测试

5. 文档
   - 更新API文档
   - 添加使用示例
   - 更新README

6. 提交代码
   git add .
   git commit -m "feat: 描述"
   git push origin feature/your-feature

7. 创建Pull Request
```

### 2. Bug修复流程

```
1. 创建修复分支
   git checkout -b fix/bug-description

2. 复现问题
   - 启用DEBUG模式
   - 收集日志
   - 定位原因

3. 修复bug
   - 最小化修改
   - 添加防御性代码
   - 记录修复原因

4. 验证修复
   - 重新测试bug场景
   - 回归测试
   - 检查副作用

5. 提交
   git commit -m "fix: 描述"
```

---

## 调试技巧

### 1. 启用Debug模式

在 `.env` 中设置：
```env
DEBUG_MODE=True
DEBUG_LOG_FILE=debug.log
```

### 2. 查看Debug日志

```python
from debug_logger import get_debug_logger

logger = get_debug_logger()
logger.log("info", "MyModule", "调试信息", {
    "param1": value1,
    "param2": value2
})
```

### 3. 使用Python调试器

```python
# 在代码中添加断点
import pdb; pdb.set_trace()

# 或使用VS Code的图形化调试器
# 在行号左侧点击添加断点
```

### 4. 日志分析

```bash
# 查看最近的错误
grep "error" debug.log | tail -20

# 查看特定模块的日志
grep "ChatAgent" debug.log

# 实时监控日志
tail -f debug.log
```

### 5. 性能分析

```python
import time

start_time = time.time()
# 要测试的代码
end_time = time.time()

logger.log("info", "Performance", f"耗时: {end_time - start_time:.2f}秒")
```

---

## 最佳实践

### 1. 代码风格

```python
# 好的例子
def process_user_message(message: str, user_id: int) -> Dict[str, Any]:
    """
    处理用户消息
    
    Args:
        message: 用户输入的消息内容
        user_id: 用户唯一标识
    
    Returns:
        包含处理结果的字典
    """
    result = {
        "status": "success",
        "response": "处理后的响应"
    }
    return result

# 避免的例子
def process(m,u):  # 参数名不清晰
    r={}  # 变量名过短
    # 缺少注释和类型提示
    return r
```

### 2. 异常处理

```python
# 好的例子
try:
    response = self.llm.invoke(messages)
except ConnectionError as e:
    logger.log("error", "ChatAgent", "API连接失败", {"error": str(e)})
    return "抱歉，网络连接出现问题"
except Exception as e:
    logger.log("error", "ChatAgent", "未知错误", {"error": str(e)})
    raise

# 避免的例子
try:
    response = self.llm.invoke(messages)
except:  # 过于宽泛的异常捕获
    pass  # 忽略错误，不记录日志
```

### 3. 配置管理

```python
# 好的例子
from dotenv import load_dotenv
import os

load_dotenv()
api_key = os.getenv('SILICONFLOW_API_KEY')
if not api_key:
    raise ValueError("API密钥未配置")

# 避免的例子
api_key = "sk-xxxxx"  # 硬编码密钥
```

### 4. 数据验证

```python
# 好的例子
def add_knowledge(self, title: str, content: str):
    if not title or not content:
        raise ValueError("标题和内容不能为空")
    
    if len(title) > 100:
        raise ValueError("标题过长")
    
    # 继续处理...

# 避免的例子
def add_knowledge(self, title, content):
    # 直接使用，不验证
    self.knowledge_list.append({"title": title, "content": content})
```

---

## 常见开发任务

### 1. 添加新的情感维度

修改 `emotion_analyzer.py`：

```python
# 在分析提示词中添加新维度
dimensions = {
    "亲密度": "0-100分",
    "信任度": "0-100分",
    "愉悦度": "0-100分",
    "共鸣度": "0-100分",
    "依赖度": "0-100分",
    "新维度": "0-100分"  # 添加新维度
}

# 更新雷达图绘制代码（gui_enhanced.py）
# 注意：需要调整为六边形
```

### 2. 修改知识提取频率

修改 `chat_agent.py`：

```python
# 找到知识提取触发条件
if current_rounds > 0 and current_rounds % 5 == 0:
    # 改为每3轮
    # if current_rounds > 0 and current_rounds % 3 == 0:
    
    # 或改为每10轮
    # if current_rounds > 0 and current_rounds % 10 == 0:
```

### 3. 添加新的知识类型

修改 `knowledge_base.py`：

```python
# 在提取提示词中添加新类型
knowledge_types = [
    "个人信息",
    "偏好",
    "事实",
    "经历",
    "观点",
    "新类型"  # 添加新类型
]

# 更新GUI显示（gui_enhanced.py）
# 添加新类型的筛选选项
```

### 4. 集成新的LLM模型

修改 `.env`：

```env
# 使用不同的模型
MODEL_NAME=new-model-name
SILICONFLOW_API_URL=https://api.newprovider.com/v1/chat/completions
```

如果API格式不兼容，需要修改 `chat_agent.py` 中的API调用逻辑。

### 5. 导出对话历史

添加导出功能：

```python
def export_conversations(self, filename: str):
    """导出对话历史为JSON"""
    data = {
        "short_term_memory": self.memory_manager.get_messages(),
        "long_term_memory": self.ltm_manager.get_summaries(),
        "knowledge": self.kb.get_all_knowledge(),
        "emotion_history": self.emotion_analyzer.get_emotion_history()
    }
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
```

### 6. 添加命令行参数

使用 `argparse`：

```python
import argparse

parser = argparse.ArgumentParser(description='Neo_Agent 智能对话系统')
parser.add_argument('--gui', action='store_true', help='启动GUI模式')
parser.add_argument('--debug', action='store_true', help='启用调试模式')
parser.add_argument('--config', type=str, help='配置文件路径')

args = parser.parse_args()

if args.debug:
    os.environ['DEBUG_MODE'] = 'True'

if args.gui:
    # 启动GUI
    pass
else:
    # 命令行模式
    pass
```

---

## 测试指南

### 1. 手动测试清单

- [ ] 基础对话功能
- [ ] 记忆保存和加载
- [ ] 知识提取（5轮触发）
- [ ] 长期记忆归档（20轮触发）
- [ ] 情感分析（10轮触发）
- [ ] GUI所有标签页
- [ ] 时间线可视化
- [ ] 情感雷达图
- [ ] Debug日志显示
- [ ] 错误处理

### 2. 性能测试

```python
# 测试大量对话的性能
agent = ChatAgent()

import time
start = time.time()

for i in range(100):
    agent.chat(f"测试消息 {i}")

end = time.time()
print(f"100轮对话耗时: {end - start:.2f}秒")
print(f"平均每轮: {(end - start) / 100:.2f}秒")
```

---

## 贡献代码

提交代码前的检查清单：

- [ ] 代码符合PEP 8规范
- [ ] 添加了必要的注释
- [ ] 更新了相关文档
- [ ] 通过了所有测试
- [ ] 没有遗留的调试代码
- [ ] 提交消息符合规范
- [ ] 没有包含敏感信息（API密钥等）

---

## 资源链接

- [LangChain文档](https://python.langchain.com/)
- [Python官方文档](https://docs.python.org/zh-cn/3/)
- [Tkinter教程](https://docs.python.org/zh-cn/3/library/tkinter.html)
- [PEP 8代码风格指南](https://pep8.org/)

---

如有开发相关问题，欢迎在 [Issues](https://github.com/HeDaas-Code/Neo_Agent/issues) 中讨论！
