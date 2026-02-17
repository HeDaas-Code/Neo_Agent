# MemU集成说明 / MemU Integration Guide

## 简介 / Introduction

### 中文

本文档说明了Neo_Agent项目中MemU框架的集成方式。MemU是一个为24/7主动智能体设计的记忆管理框架，能够大幅降低长期运行的LLM token成本。

**MemU项目**: https://github.com/NevaMind-AI/memU

**License**: Apache License 2.0

### English

This document explains the integration of the MemU framework into the Neo_Agent project. MemU is a memory management framework designed for 24/7 proactive agents, which significantly reduces long-running LLM token costs.

**MemU Project**: https://github.com/NevaMind-AI/memU

**License**: Apache License 2.0

---

## 集成方式 / Integration Approach

### 1. 依赖管理 / Dependency Management

MemU已添加到`requirements.txt`中：

```txt
memu-py>=0.2.2
anthropic>=0.79.0
azure-ai-inference>=1.0.0b9
cachetools>=7.0.0
pydantic-settings>=2.13.0
PyYAML>=6.0
```

### 2. 适配器模式 / Adapter Pattern

创建了`src/core/memu_memory_adapter.py`作为适配器层，封装MemU的功能：

```python
from src.core.memu_memory_adapter import MemUAdapter

# 初始化适配器
adapter = MemUAdapter(
    api_key="your-openai-key",  # 可选，默认从环境变量读取
    model_name="gpt-4o-mini"    # 可选
)

# 生成对话概括
summary = adapter.generate_summary(messages)
```

**适配器特性**:
- 使用MemU的OpenAI LLM客户端进行总结
- 自动检测API密钥可用性
- 提供与原有接口兼容的方法

### 3. 长期记忆集成 / Long-term Memory Integration

`src/core/long_term_memory.py`已更新以使用MemU：

```python
class LongTermMemoryManager:
    def __init__(self, ...):
        # 初始化MemU适配器
        self.use_memu = MEMU_ENABLED and os.getenv('USE_MEMU', 'true').lower() == 'true'
        if self.use_memu:
            self.memu_adapter = MemUAdapter(...)
    
    def _generate_summary(self, messages):
        # 优先使用MemU
        if self.use_memu and self.memu_adapter:
            summary = self.memu_adapter.generate_summary(messages)
            if summary:
                return summary
        
        # 回退到传统LLM总结
        # ...原有代码...
```

**集成特性**:
- 🔄 自动检测MemU可用性
- 🛡️ 失败时自动回退到传统方式
- 📚 知识库功能不受影响

---

## 配置说明 / Configuration

### 环境变量 / Environment Variables

在`.env`文件中配置：

```bash
# 是否启用MemU（默认true）
USE_MEMU=true

# MemU使用的API密钥（必需）
OPENAI_API_KEY=your-openai-key

# MemU使用的模型名称（可选，默认gpt-4o-mini）
MEMU_MODEL_NAME=gpt-4o-mini
```

### 配置优先级 / Configuration Priority

1. 显式传入的参数
2. 环境变量`OPENAI_API_KEY`
3. 环境变量`SILICONFLOW_API_KEY`（作为备选）

---

## 工作流程 / Workflow

### 记忆总结流程 / Memory Summarization Flow

```
用户对话 (User Conversation)
    ↓
添加到短期记忆 (Add to Short-term Memory)
    ↓
达到20轮? (Reached 20 rounds?)
    ↓ 是/Yes
归档到长期记忆 (Archive to Long-term Memory)
    ↓
生成概括 (Generate Summary)
    ↓
优先使用MemU? (Use MemU first?)
    ↓ 是/Yes
    ├─→ MemU可用? (MemU Available?)
    │   ├─→ 是/Yes → 使用MemU总结 (Use MemU)
    │   └─→ 否/No → 回退到传统LLM (Fallback to LLM)
    └─→ 否/No → 使用传统LLM (Use traditional LLM)
```

### 知识提取流程 / Knowledge Extraction Flow

知识提取功能**不使用MemU**，保持原有实现：

```
每5轮对话 (Every 5 rounds)
    ↓
提取知识 (Extract Knowledge)
    ↓
使用原有LLM (Use original LLM)
    ↓
保存到知识库 (Save to Knowledge Base)
```

---

## 优势 / Advantages

### 使用MemU的优势 / MemU Advantages

1. **成本降低**: 大幅减少长期运行的token成本
2. **高效记忆**: 更智能的记忆组织和检索
3. **主动理解**: 持续捕获和理解用户意图
4. **无缝集成**: 零破坏性变更，现有代码无需修改

### 回退机制优势 / Fallback Advantages

1. **高可用性**: API密钥未配置时仍可正常工作
2. **零中断**: MemU失败时自动使用传统方式
3. **兼容性**: 完全兼容现有功能和数据

---

## 测试 / Testing

### 单元测试 / Unit Testing

```bash
# 测试MemU适配器
python src/core/memu_memory_adapter.py

# 测试长期记忆管理器
python -c "from src.core.long_term_memory import LongTermMemoryManager; m = LongTermMemoryManager(); print('OK')"
```

### 功能测试 / Functional Testing

1. **启用MemU**:
   ```bash
   USE_MEMU=true OPENAI_API_KEY=sk-xxx python gui_enhanced.py
   ```

2. **禁用MemU**:
   ```bash
   USE_MEMU=false python gui_enhanced.py
   ```

3. **未配置API密钥**:
   ```bash
   # 应自动回退到传统方式
   python gui_enhanced.py
   ```

---

## 故障排除 / Troubleshooting

### 问题1: MemU未启用

**现象**: 看到"⚠ MemU未安装"或"⚠ MemU API密钥未配置"

**解决方案**:
```bash
# 1. 确保已安装memu-py
pip install memu-py>=0.2.2

# 2. 配置API密钥
export OPENAI_API_KEY=your-key

# 3. 启用MemU
export USE_MEMU=true
```

### 问题2: MemU总结失败

**现象**: 看到"⚠ MemU未返回概括"或"⚠ MemU生成概括失败"

**影响**: 系统自动回退到传统LLM总结，功能不受影响

**检查**:
1. API密钥是否正确
2. 网络连接是否正常
3. 模型名称是否正确

### 问题3: 记忆功能异常

**解决步骤**:
1. 检查数据库文件`chat_data.db`是否存在
2. 查看debug日志（如果启用了DEBUG_MODE）
3. 尝试清空记忆后重新开始：在GUI中选择"清空所有记忆"

---

## 未来计划 / Future Plans

1. **深度集成**: 探索MemU的更多高级功能
2. **主动检索**: 利用MemU的主动记忆检索能力
3. **性能优化**: 进一步优化记忆管理性能
4. **多用户支持**: 支持多用户的记忆隔离

---

## 参考资料 / References

- [MemU GitHub](https://github.com/NevaMind-AI/memU)
- [MemU Documentation](https://github.com/NevaMind-AI/memU#readme)
- [Neo_Agent Architecture](ARCHITECTURE.md)
- [Neo_Agent API Documentation](API.md)

---

## 致谢 / Acknowledgments

感谢MemU团队开发了如此优秀的记忆管理框架！

Thanks to the MemU team for developing such an excellent memory management framework!

---

*Last Updated: 2026-02-17*
