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

## 最新更新 / Latest Updates

### v2.0 - GUI优化与自部署API支持

**新功能**:
1. ✨ 全新的MemU状态可视化界面
2. 🚀 支持自部署的MemU API服务器
3. 🔄 智能双模式运行（API服务/LLM客户端）
4. 🗑️ 移除废弃的长期记忆管理界面

**升级说明**:
- 旧的"长期记忆"选项卡已被"MemU状态"选项卡替代
- 数据库管理界面中的长期记忆管理已废弃
- 所有长期记忆功能现由MemU系统统一管理

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

# 方式1: 使用直接LLM客户端（默认）
adapter = MemUAdapter(
    api_key="your-openai-key",
    model_name="gpt-4o-mini"
)

# 方式2: 使用自部署的MemU API服务器
adapter = MemUAdapter(
    api_key="your-api-key",
    model_name="gpt-4o-mini",
    base_url="http://localhost:8123"  # 您的MemU服务器
)

# 生成对话概括
summary = adapter.generate_summary(messages)

# 获取系统状态
status = adapter.get_status_info()
print(f"运行模式: {status['mode']}")
print(f"API地址: {status['api_url']}")
```

**适配器特性**:
- 自动检测运行模式（API服务/LLM客户端）
- 自动检测API密钥可用性
- 提供与原有接口兼容的方法
- 支持状态查询和监控

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

#### 基础配置（LLM客户端模式）

```bash
# 启用MemU（默认true）
USE_MEMU=true

# MemU使用的API密钥
OPENAI_API_KEY=your-openai-key

# MemU使用的模型名称（可选，默认gpt-4o-mini）
MEMU_MODEL_NAME=gpt-4o-mini
```

#### 高级配置（自部署API服务模式）

```bash
# 启用MemU
USE_MEMU=true

# MemU API服务器地址（设置此项将使用API服务模式）
MEMU_API_URL=http://localhost:8123

# MemU API密钥
OPENAI_API_KEY=your-memu-api-key

# MemU用户ID（用于API服务）
MEMU_USER_ID=neo_agent_user

# MemU智能体ID（用于API服务）
MEMU_AGENT_ID=neo_agent

# 模型名称（可选）
MEMU_MODEL_NAME=gpt-4o-mini
```

### 配置优先级 / Configuration Priority

1. 显式传入的参数
2. 环境变量`MEMU_API_URL`（决定运行模式）
3. 环境变量`OPENAI_API_KEY`
4. 环境变量`SILICONFLOW_API_KEY`（作为备选）

### 运行模式说明 / Mode Explanation

| 模式 | 触发条件 | 说明 |
|------|---------|------|
| **API服务模式** | 配置了`MEMU_API_URL` | 连接自部署的MemU服务器，获得完整的MemU功能 |
| **LLM客户端模式** | 未配置`MEMU_API_URL` | 直接使用LLM进行总结，适合快速开始 |

---

## GUI使用指南 / GUI Usage Guide

### MemU状态界面 / MemU Status Interface

在Neo Agent GUI中，找到"🧠 MemU状态"选项卡：

**显示内容**:
1. **系统状态**
   - ✓ 启用状态
   - ✓ API配置状态
   - ✓ 运行模式
   - ✓ 模型信息

2. **API服务配置**（API模式时）
   - API服务器地址
   - 用户ID
   - 智能体ID
   - 配置提示

3. **记忆统计**
   - 短期记忆轮数
   - 长期概括数量
   - 知识条目数量

**操作按钮**:
- 🔄 刷新MemU状态：手动更新显示

### 界面变化 / Interface Changes

**已移除**:
- ❌ 旧的"长期记忆"选项卡（在调试区域）
- ❌ 数据库管理中的"长期记忆"管理

**新增**:
- ✅ "🧠 MemU状态"选项卡（调试区域）
- ✅ 实时状态监控
- ✅ 配置验证和提示

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
检测运行模式 (Detect Mode)
    ↓
    ├─→ API服务模式?
    │   ├─→ 是 → 通过MemU API生成总结
    │   └─→ 否 → 使用LLM客户端生成总结
    └─→ 失败? → 回退到传统LLM总结
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

## 自部署MemU服务器 / Self-Hosted MemU Server

### 为什么使用自部署? / Why Self-Host?

1. **更强大的功能**: 完整的MemU记忆管理能力
2. **数据隐私**: 数据存储在您自己的服务器
3. **灵活定制**: 可以根据需求定制MemU服务
4. **成本控制**: 避免依赖外部API服务

### 部署指南 / Deployment Guide

参考MemU官方文档：https://github.com/NevaMind-AI/memU

基本步骤：
```bash
# 1. 克隆MemU仓库
git clone https://github.com/NevaMind-AI/memU.git
cd memU

# 2. 安装依赖
pip install -r requirements.txt

# 3. 启动服务器
python -m memu.server --host 0.0.0.0 --port 8123

# 4. 配置Neo Agent
# 在.env中设置:
# MEMU_API_URL=http://localhost:8123
```

---

## 优势 / Advantages

### 使用MemU的优势 / MemU Advantages

1. **成本降低**: 大幅减少长期运行的token成本
2. **高效记忆**: 更智能的记忆组织和检索
3. **主动理解**: 持续捕获和理解用户意图
4. **无缝集成**: 零破坏性变更，现有代码无需修改

### 自部署API的优势 / Self-Hosted API Advantages

1. **完整功能**: 访问MemU的全部高级特性
2. **数据主权**: 完全控制记忆数据
3. **无外部依赖**: 不依赖第三方服务
4. **可定制性**: 根据需求调整配置

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

1. **测试LLM客户端模式**:
   ```bash
   USE_MEMU=true OPENAI_API_KEY=sk-xxx python gui_enhanced.py
   ```
   - 检查"MemU状态"显示"LLM客户端模式"

2. **测试API服务模式**:
   ```bash
   USE_MEMU=true MEMU_API_URL=http://localhost:8123 OPENAI_API_KEY=xxx python gui_enhanced.py
   ```
   - 检查"MemU状态"显示"API服务模式"
   - 验证显示正确的API地址

3. **测试未配置场景**:
   ```bash
   # 应自动回退到传统方式
   python gui_enhanced.py
   ```
   - 系统应正常运行，显示MemU未启用

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

### 问题2: API服务连接失败

**现象**: 看到"✗ MemU API客户端创建失败"或连接错误

**检查清单**:
1. MemU服务器是否正在运行？
   ```bash
   curl http://localhost:8123/health
   ```
2. 防火墙是否允许连接？
3. API地址是否正确？
4. API密钥是否有效？

**解决方案**:
- 检查服务器日志
- 验证网络连接
- 尝试直接访问API端点
- 如果失败，系统会自动回退到LLM客户端模式

### 问题3: GUI显示异常

**现象**: MemU状态显示不正确或出错

**解决方案**:
1. 点击"🔄 刷新MemU状态"按钮
2. 检查后台日志（如果启用DEBUG_MODE）
3. 重启应用程序

### 问题4: 记忆功能异常

**解决步骤**:
1. 检查数据库文件`chat_data.db`是否存在
2. 查看debug日志（如果启用了DEBUG_MODE）
3. 验证MemU状态是否正常
4. 尝试清空记忆后重新开始：在GUI中选择"清空所有记忆"

---

## 性能优化 / Performance Optimization

### API服务模式优化建议

1. **网络延迟**: 将MemU服务器部署在靠近Neo Agent的位置
2. **并发处理**: 配置MemU服务器的并发参数
3. **缓存策略**: 利用MemU的内置缓存机制
4. **资源分配**: 为MemU服务器分配足够的CPU和内存

### LLM客户端模式优化建议

1. **模型选择**: 根据需求选择合适的模型（速度vs质量）
2. **请求参数**: 调整temperature和max_tokens
3. **批处理**: 尽可能批量处理多个请求

---

## 未来计划 / Future Plans

1. **深度集成**: 探索MemU的更多高级功能
2. **主动检索**: 利用MemU的主动记忆检索能力
3. **性能优化**: 进一步优化记忆管理性能
4. **多用户支持**: 支持多用户的记忆隔离
5. **可视化增强**: 添加更多记忆可视化和分析功能
6. **自动部署**: 提供一键部署MemU服务器的脚本

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

*Last Updated: 2026-02-18*
*Version: 2.0 - GUI Optimization & Self-Hosted API Support*

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
