# LLM驱动AVG游戏核心系统

这是一个基于大语言模型的文字冒险游戏(AVG)核心引擎，实现了智能角色对话、动态记忆系统、知识图谱管理和权限控制等功能。

## 🎮 游戏概念

在这个游戏中，玩家扮演一个被困在损坏飞船上的AI系统，需要与幸存的船员合作求生。游戏的核心特色包括：

- **LLM驱动角色**: 船员由大语言模型扮演，具有真实的人格和情感反应
- **权限层级系统**: 玩家需要逐步提升AI权限来解锁新功能和区域
- **数据碎片收集**: 通过收集数据碎片来修复知识图谱，揭示真相
- **生命指标监测**: 实时监控船员的生理和心理状态
- **动态事件系统**: 基于游戏状态触发各种紧急情况和剧情分支

## 🏗️ 系统架构

### 核心组件

1. **LLMCore**: 主控制器，协调各个子系统
2. **ModelManager**: 管理AI模型调用（主模型+嵌入模型）
3. **MemorySystem**: 基于向量数据库的长期记忆存储
4. **CharacterController**: 角色行为和对话控制
5. **KnowledgeGraph**: 知识图谱和信息边界管理
6. **GameState**: 游戏状态和事件系统

### 技术栈

- **主模型**: DeepSeek-R1 (通过硅基流动API)
- **嵌入模型**: BAAI/bge-m3 (本地部署)
- **向量数据库**: ChromaDB
- **知识图谱**: NetworkX
- **配置管理**: JSON + Pydantic

## 🚀 快速开始

### 1. 环境准备

```bash
# 进入项目目录
cd Project

# 安装依赖
pip install -r requirements.txt
```

### 2. 配置设置

编辑 `config.json` 文件，填入你的API密钥：

```json
{
  "model": {
    "deepseek_api_key": "YOUR_DEEPSEEK_API_KEY_HERE",
    "api_base": "https://api.siliconflow.cn/v1",
    "model_name": "deepseek-ai/DeepSeek-R1-0528-Qwen3-8B",
    "bge_model_path": "BAAI/bge-m3"
  }
}
```

### 3. 快速体验

```bash
# 方式1: 交互式演示（推荐新手）
python quick_start.py

# 方式2: 运行基础测试
python test_basic.py

# 方式3: 完整功能测试（需要网络和API密钥）
python test_llm_core.py
```

### 4. 基本使用

```python
import asyncio
from llm_core import LLMCore

async def main():
    # 初始化核心系统
    core = LLMCore("config.json")
    
    # 开始对话
    response = await core.process_dialogue("你好，请告诉我当前的情况")
    print(f"船员: {response}")
    
    # 处理数据碎片
    result = core.process_data_fragment("engine_data")
    print(f"数据碎片处理结果: {result}")
    
    # 检查游戏状态
    print(f"当前权限等级: {core.game_state.permission_level}")
    print(f"角色健康状态: {core.game_state.character_health}")

if __name__ == "__main__":
    asyncio.run(main())
```

## 📋 功能特性

### 🧠 智能对话系统

- **角色一致性**: 基于人格设定和当前状态生成符合角色的回应
- **上下文感知**: 利用向量记忆库维持长期对话连贯性
- **情感状态**: 根据角色的生理和心理状态调整对话风格
- **知识边界**: 严格限制角色只能回答已解锁的知识内容

### 🗃️ 记忆系统

- **向量存储**: 使用BGE-M3模型将对话和事件转换为向量存储
- **语义检索**: 基于语义相似度检索相关历史记忆
- **分类管理**: 按对话、事件、发现等类型组织记忆
- **持久化**: 记忆数据持久保存，支持游戏存档

### 🕸️ 知识图谱

- **分层解锁**: 知识按权限等级分层，逐步解锁
- **碎片系统**: 通过收集数据碎片来解锁新知识
- **依赖关系**: 某些知识需要前置条件才能解锁
- **动态更新**: 支持运行时动态添加新知识节点

### 🎯 权限系统

- **等级控制**: 从紧急权限(1级)到核心权限(7级)
- **功能解锁**: 不同权限等级解锁不同的系统功能
- **区域访问**: 控制玩家可以访问的飞船区域
- **渐进式**: 通过完成任务和收集碎片提升权限

### 🎲 事件系统

- **动态触发**: 基于时间、健康状态、权限等级触发事件
- **多重结局**: 不同的选择和状态导向不同的游戏结局
- **状态影响**: 事件会影响角色状态和可用系统
- **分支剧情**: 支持复杂的剧情分支和条件判断

## 🔧 配置说明

### 模型配置

```json
{
  "model": {
    "deepseek_api_key": "API密钥",
    "api_base": "API基础URL",
    "model_name": "模型名称",
    "bge_model_path": "嵌入模型路径"
  }
}
```

### 角色配置

```json
{
  "character": {
    "name": "角色名称",
    "role": "角色职业",
    "personality": "性格描述",
    "background": "背景故事",
    "current_state": "当前情绪状态",
    "knowledge_level": "知识水平"
  }
}
```

### 游戏内容配置

- **知识库**: 定义可解锁的知识内容和权限要求
- **事件系统**: 配置触发条件和效果
- **地点系统**: 定义可访问的区域和权限要求
- **数据碎片**: 配置碎片类型和解锁效果

## 🧪 测试和调试

### 运行测试套件

```bash
# 完整测试
python test_llm_core.py

# 单独测试记忆系统
python -c "from test_llm_core import test_memory_system; test_memory_system()"
```

### 调试模式

在代码中设置 `debug=True` 来启用详细日志：

```python
core = LLMCore("config.json", debug=True)
```

## 📁 项目结构

```
Project/
├── llm_core.py          # 核心游戏引擎（单文件架构）
├── config.json          # 配置文件模板
├── requirements.txt     # 依赖列表
├── test_llm_core.py    # 完整功能测试
├── test_basic.py       # 基础逻辑测试（无网络依赖）
├── quick_start.py      # 快速启动和演示脚本
├── README.md           # 项目文档
├── .tr/                # 设计文档
│   ├── thinking.md     # 设计思路记录
│   └── mermaid.md      # 系统架构图表
└── memory_db/          # 记忆数据库(运行时生成)
```

### 文件说明

- **llm_core.py**: 包含所有核心类和功能的单文件实现
- **quick_start.py**: 提供交互式演示，无需API密钥即可体验
- **test_basic.py**: 测试核心逻辑，不依赖网络连接
- **test_llm_core.py**: 完整功能测试，需要API密钥和网络
- **config.json**: 详细的配置模板，包含所有可调参数

## 🔮 扩展开发

### 添加新角色

1. 在配置文件中定义角色属性
2. 扩展 `CharacterController` 类
3. 添加角色特定的提示词模板

### 添加新事件

1. 在配置文件的 `events` 部分定义事件
2. 实现事件触发逻辑
3. 定义事件效果和后果

### 集成新模型

1. 扩展 `ModelManager` 类
2. 添加新的API调用方法
3. 更新配置文件格式

## 🤝 贡献指南

1. Fork 项目
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

## 🙏 致谢

- [DeepSeek](https://www.deepseek.com/) - 提供强大的语言模型
- [BAAI](https://www.baai.ac.cn/) - BGE嵌入模型
- [ChromaDB](https://www.trychroma.com/) - 向量数据库
- [Sentence Transformers](https://www.sbert.net/) - 文本嵌入框架

---

**注意**: 这是一个实验性项目，用于探索LLM在游戏开发中的应用。请确保在使用前仔细配置API密钥和模型参数。