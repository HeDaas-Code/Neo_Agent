# Changelog / 更新日志

All notable changes to this project will be documented in this file.

本文件记录项目的所有重要变更。

## [3.0.0] - 2026-02-21

### 重大更新 🎉 Major Update

#### 技能系统与全能代理 / Skill System & OmniAgent

参考openclaw的全能代理设计，为多智能体系统引入技能管理和自主学习能力：

**SkillRegistry（技能注册表）**
- SQLite持久化的技能注册表，管理三类技能（builtin/learned/user）
- 5个内置技能：`task_decomposition`、`result_synthesis`、`information_retrieval`、`error_recovery`、`knowledge_extraction`
- 技能以虚拟文件系统路径注入 DeepAgents（`/skills/builtin/`、`/skills/learned/`、`/skills/user/`）
- 支持技能使用统计和成功率追踪

**OmniAgent（全能代理）**
- 拥有所有已注册技能，通过 deepagents `SubAgent` 规格列表动态派生专业子智能体
- 任务成功后调用工具模型自动提炼可复用方法，保存为 `learned` 类别技能
- 支持跨会话状态持久化（MemorySaver）

**DynamicMultiAgentGraph 升级**
- 技能感知调度：`_execute_agent` 根据角色自动推荐并注入对应技能集
- 任务后自主学习：`_post_task_learning()` 在成功任务后提炼技能

**DeepSubAgentWrapper 升级**
- 新增 `skill_names`/`skill_paths` 参数，技能文件延迟加载注入
- 新增 `learn_skill()` 方法，调用后自动使技能缓存失效

### Added / 新增

- **SkillRegistry** (`src/core/skill_registry.py`): 全局技能注册表（SQLite），含内置技能初始化
- **OmniAgent** (`src/core/omni_agent.py`): 全能代理，自主学习入口
- **tests/test_skill_system.py**: 28个技能系统测试用例
- **docs/SKILL_SYSTEM.md**: 技能系统与全能代理完整文档（中英双语）

### Changed / 变更

- **deepagents_wrapper.py**: 新增技能注入支持，`DeepSubAgentWrapper` 增加 `skill_names`/`skill_paths`/`learn_skill()` / 技能文件缓存
- **dynamic_multi_agent_graph.py**: 技能感知调度 + 任务后自主学习 (`_post_task_learning`)
- **multi_agent_coordinator.py**: `create_sub_agent()` 新增 `skill_names` 参数
- **example.env**: 新增 `USE_OMNI_AGENT`、`ENABLE_AUTO_LEARNING`、`LEARNING_MIN_OUTPUT_LEN`、`SKILL_DB_PATH`
- **ARCHITECTURE.md**: 新增技能系统架构章节
- **docs/DEEPAGENTS_INTEGRATION.md**: 更新技能集成说明

### Configuration / 配置

```bash
USE_OMNI_AGENT=true               # 启用全能代理（默认true）
ENABLE_AUTO_LEARNING=true          # 启用自主学习（默认true）
LEARNING_MIN_OUTPUT_LEN=200        # 触发学习的最小输出长度
SKILL_DB_PATH=skill_registry.db   # 技能数据库路径
```

---

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
