# Changelog / 更新日志

All notable changes to this project will be documented in this file.

本文件记录项目的所有重要变更。

## [2.0.0] - 2026-02-09

### 重大更新 🎉 Major Update

#### 复合框架架构 / Composite Framework Architecture
- **引入LangChain + LangGraph复合框架 / Introduced LangChain + LangGraph Composite Framework**
  - LangChain作为核心框架提供LLM抽象 / LangChain as core framework providing LLM abstraction
  - LangGraph用于状态图管理和对话流程编排 / LangGraph for state graph management and conversation orchestration
  - 创建ConversationGraph基础框架 / Created ConversationGraph base framework

#### 多层模型架构 / Multi-tier Model Architecture
- **实现三层模型系统 / Implemented three-tier model system**
  - 主模型 (deepseek-ai/DeepSeek-V3.2): 处理主要对话和复杂推理 / Main model for primary conversations and complex reasoning
  - 工具模型 (zai-org/GLM-4.6V): 处理轻量级任务 / Tool model for lightweight tasks
  - 多模态模型 (Qwen/Qwen3-VL-32B-Instruct): 预留多模态处理 / Multimodal model reserved for future use

### Added / 新增
- **ModelConfig** (`model_config.py`): 多层模型配置管理 / Multi-tier model configuration management
- **LangChainLLM** (`langchain_llm.py`): LangChain封装，支持模型路由 / LangChain wrapper with model routing
- **ModelRouter** (`langchain_llm.py`): 智能模型路由器 / Intelligent model router
- **LLMHelper** (`llm_helper.py`): 简化工具级任务的LLM调用 / Simplified LLM calls for tool-level tasks
- **ConversationGraph** (`conversation_graph.py`): LangGraph对话流程管理 / LangGraph conversation flow management
- **ARCHITECTURE.md**: 详细的架构文档 / Detailed architecture documentation

### Changed / 变更
- **SiliconFlowLLM**: 重构为兼容层，内部使用LangChain / Refactored as compatibility layer using LangChain internally
- **SubAgent**: 使用工具模型处理子任务 / Uses tool model for sub-tasks
- **EmotionRelationshipAnalyzer**: 使用工具模型进行情感分析 / Uses tool model for emotion analysis
- **KnowledgeBase**: 使用工具模型进行知识提取 / Uses tool model for knowledge extraction
- 更新`requirements.txt`，添加LangGraph和相关依赖 / Updated requirements.txt with LangGraph dependencies
- 更新`example.env`，新增多层模型配置 / Updated example.env with multi-tier model configurations
- 更新README.md，说明新架构 / Updated README.md explaining new architecture

### Improved / 改进
- ✅ 所有模块统一使用LangChain架构 / All modules now use LangChain architecture
- ✅ 轻量级任务使用工具模型，降低成本 / Lightweight tasks use tool model, reducing costs
- ✅ 保持完全向后兼容 / Maintains full backward compatibility
- ✅ 代码更加模块化和可维护 / More modular and maintainable code

---

## [1.0.0] - 2026-01-31

### Added / 新增

- 项目重构为标准Python包结构
- 创建了清晰的模块划分（core, gui, tools, nps）
- 添加主入口点 main.py
- 完善的包初始化文件和模块导出
- 新的项目文档（README, CONTRIBUTING）

### Changed / 变更

- 将所有源代码移至 src/ 目录
- 重新组织核心模块到 src/core/
- 重新组织GUI模块到 src/gui/
- 重新组织工具模块到 src/tools/
- 移动NPS系统到 src/nps/
- 移动示例代码到 examples/
- 统一测试文件到 tests/
- 更新所有import路径以反映新结构

### Removed / 移除

- 删除临时说明文档
- 清理过时的markdown文档
- 移除根目录下的散乱文件

### Technical / 技术细节

- 实现模块化包结构
- 改进代码组织和可维护性
- 标准化项目布局
- 简化部署和安装流程

---

## 版本说明 / Version Notes

版本号遵循 [语义化版本](https://semver.org/lang/zh-CN/) 规范：

- 主版本号：不兼容的API变更
- 次版本号：向下兼容的功能新增
- 修订号：向下兼容的问题修正

Version numbers follow [Semantic Versioning](https://semver.org/):

- MAJOR: Incompatible API changes
- MINOR: Backward compatible functionality additions
- PATCH: Backward compatible bug fixes
