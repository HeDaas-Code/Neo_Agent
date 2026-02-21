# 技能系统与全能代理文档

[English](#english) | [简体中文](#中文)

---

## 中文

### 概述

本次更新为 Neo Agent 引入了**技能系统（SkillRegistry）**和**全能代理（OmniAgent）**，参考 openclaw 的工作方式，让多智能体协作升级为具有技能管理和自主学习功能的全能代理架构。

---

### 技能注册表（SkillRegistry）

#### 设计目标

- 将可复用的能力抽象为「技能」文件（Markdown 格式）
- 技能存储在 SQLite 数据库，以虚拟文件系统路径的形式注入 DeepAgents
- 智能体可通过 `read_file /skills/builtin/task_decomposition.md` 读取技能指导
- 支持三种来源：内置技能、自主学习技能、用户自定义技能

#### 技能分类

| 分类 | 路径 | 说明 |
|------|------|------|
| `builtin` | `/skills/builtin/` | 系统内置，开箱即用，不可覆盖 |
| `learned` | `/skills/learned/` | 智能体自主学习保存的技能 |
| `user` | `/skills/user/` | 用户手动注册的技能 |

#### 内置技能

| 技能名称 | 说明 |
|---------|------|
| `information_retrieval` | 信息检索：关键词提取、多源整合 |
| `task_decomposition` | 任务分解：复杂任务拆分为子任务 |
| `result_synthesis` | 结果综合：多智能体结果整合 |
| `error_recovery` | 错误恢复：分析错误并选择替代方案 |
| `knowledge_extraction` | 知识提取：从对话中提炼可复用知识 |

#### 使用示例

```python
from src.core.skill_registry import get_skill_registry

registry = get_skill_registry()

# 列出所有技能
skills = registry.list_skills()

# 获取指定技能
skill = registry.get_skill('task_decomposition')
print(skill['content'])

# 添加用户自定义技能
registry.add_skill(
    name='data_analysis',
    content='# 数据分析技能\n\n## 步骤\n1. 清洗数据\n2. ...',
    category='user',
    description='用于数据清洗和分析'
)

# 记录技能使用（更新成功率）
registry.record_usage('task_decomposition', task_type='research', outcome='success')

# 获取技能文件字典（注入 DeepAgents）
files = registry.get_skills_for_agent(skill_names=['task_decomposition', 'result_synthesis'])
# → {'/skills/builtin/task_decomposition.md': '...', '/skills/builtin/result_synthesis.md': '...'}
```

#### 自主学习

智能体可通过 `learn_skill()` 将任务经验保存为新技能：

```python
registry.learn_skill(
    name='competitive_analysis',
    content='# 竞品分析技能\n\n## 步骤\n1. 收集竞品信息\n2. ...',
    description='竞品市场分析方法',
    source_task='分析竞品市场'
)
```

学习来源和时间戳会自动追加到技能内容末尾。

#### 配置

```bash
# .env 文件
SKILL_DB_PATH=skill_registry.db   # SQLite 数据库路径（默认 skill_registry.db）
```

---

### 全能代理（OmniAgent）

#### 设计目标

参考 openclaw 的全能代理设计：
- 拥有所有已注册技能（技能文件注入虚拟文件系统）
- 通过 deepagents 的 `SubAgent` 规格列表派生专业子智能体
- 任务成功后调用 LLM 提炼经验，自动保存为 `learned` 类别技能

#### 子智能体角色映射

| 角色 | 绑定技能 |
|-----|---------|
| 研究员 | `information_retrieval`, `knowledge_extraction` |
| 分析师 | `information_retrieval`, `result_synthesis` |
| 规划师 | `task_decomposition` |
| 执行者 | `error_recovery` |
| 综合师 | `result_synthesis`, `knowledge_extraction` |
| 任务分析专家 | `task_decomposition`, `information_retrieval` |
| 任务规划专家 | `task_decomposition` |
| 任务执行专家 | `error_recovery` |
| 任务验证专家 | `result_synthesis` |

#### 使用示例

```python
from src.core.omni_agent import OmniAgent

# 创建全能代理
agent = OmniAgent(
    agent_id='omni',
    enable_auto_learning=True   # 启用任务后自主学习
)

# 执行任务
result = agent.execute_task(
    task_description='分析竞品市场',
    context={'industry': '互联网', 'region': '中国'}
)

print(result['result'])           # 任务结果
print(result['learned_skills'])   # 自动学习到的新技能列表
print(result['thread_id'])        # 跨会话线程ID

# 手动添加技能
agent.add_skill(
    name='my_skill',
    content='# 我的技能\n\n## 步骤\n...',
    description='自定义技能'
)

# 查看所有技能
skills = agent.list_skills()
```

#### 工厂函数

```python
from src.core.omni_agent import create_omni_agent

agent = create_omni_agent(
    agent_id='main_omni',
    progress_callback=lambda msg: print(msg)
)
```

#### 自主学习流程

```
执行任务
    ↓
任务成功 + 输出长度 ≥ LEARNING_MIN_OUTPUT_LEN
    ↓
工具模型分析结果，提取可复用方法
    ↓
以 JSON 格式输出技能定义
    ↓
保存到 SkillRegistry（learned 类别）
    ↓
下次执行时，新技能自动注入所有智能体
```

#### 配置

```bash
# .env 文件
USE_OMNI_AGENT=true                # 启用全能代理模式（默认 true）
ENABLE_AUTO_LEARNING=true          # 启用任务后自主学习（默认 true）
LEARNING_MIN_OUTPUT_LEN=200        # 触发学习的最小输出长度（默认 200 字符）
SKILL_DB_PATH=skill_registry.db    # 技能数据库路径
```

---

### DynamicMultiAgentGraph 技能感知升级

`DynamicMultiAgentGraph` 现在支持技能感知的子智能体调度：

1. **技能感知调度**：`_execute_agent` 根据角色名称通过 `_get_skills_for_role()` 自动推荐技能，在创建子智能体时注入对应的技能文件
2. **任务后学习**：非简单任务成功完成后，调用 `_post_task_learning()` 提炼经验技能
3. **结果包含学习信息**：成功的任务结果中包含 `learned_skills` 字段

```python
result = graph.process_task_event(task_event, character_context)

if result['success']:
    print(result.get('learned_skills', []))  # 本次学到的技能
```

---

### DeepSubAgentWrapper 技能集成

`DeepSubAgentWrapper` 新增以下参数：

```python
agent = DeepSubAgentWrapper(
    agent_id='researcher',
    role='研究员',
    description='负责信息研究和分析',
    skill_names=['information_retrieval'],  # 指定加载的技能
    skill_paths=['/skills/builtin/']        # 技能路径（deepagents skills 参数）
)
```

- `skill_names`：`None` 表示加载所有已注册技能
- 技能文件通过延迟加载合并到每次 `invoke(files={...})` 调用中
- 调用 `agent.learn_skill(name, content)` 后会自动使技能文件缓存失效

---

### 架构图

```
用户请求
    │
    ▼
MultiAgentCoordinator / DynamicMultiAgentGraph
    │
    ├── SkillRegistry（技能注册表）
    │       ├── builtin/（内置技能）
    │       ├── learned/（自主学习技能）
    │       └── user/（用户自定义技能）
    │
    ├── OmniAgent（全能代理）
    │       ├── 所有技能注入
    │       ├── 子智能体：研究员、分析师、规划师...
    │       └── 自主学习 → learned/
    │
    └── DeepSubAgentWrapper（技能感知子智能体）
            ├── 技能文件注入（files={...}）
            └── learn_skill() → SkillRegistry
```

---

### 测试

```bash
# 运行技能系统测试
python -m pytest tests/test_skill_system.py -v

# 运行 DeepAgents 集成测试
python -m pytest tests/test_deepagents_integration.py -v
```

---

## English

### Overview

This update introduces the **SkillRegistry** and **OmniAgent** to Neo Agent, inspired by openclaw's approach. Multi-agent collaboration is upgraded to a skills-based omnipotent agent architecture with autonomous learning capability.

---

### SkillRegistry

#### Design Goals

- Abstracts reusable capabilities as "skill" files (Markdown format)
- Skills are stored in SQLite and injected into DeepAgents as virtual filesystem paths
- Agents can read skill guidance via `read_file /skills/builtin/task_decomposition.md`
- Three skill sources: builtin, learned (autonomous), user-defined

#### Skill Categories

| Category | Path | Description |
|---------|------|-------------|
| `builtin` | `/skills/builtin/` | Shipped with the system, immutable |
| `learned` | `/skills/learned/` | Autonomously learned from task outcomes |
| `user` | `/skills/user/` | Manually registered by users |

#### Built-in Skills

| Skill Name | Description |
|-----------|-------------|
| `information_retrieval` | Keyword extraction and multi-source integration |
| `task_decomposition` | Breaking complex tasks into sub-tasks |
| `result_synthesis` | Integrating results from multiple agents |
| `error_recovery` | Analyzing errors and selecting alternatives |
| `knowledge_extraction` | Extracting reusable knowledge from conversations |

#### Usage

```python
from src.core.skill_registry import get_skill_registry

registry = get_skill_registry()

# List all skills
skills = registry.list_skills()

# Get a specific skill
skill = registry.get_skill('task_decomposition')

# Add a user-defined skill
registry.add_skill(
    name='data_analysis',
    content='# Data Analysis\n\n## Steps\n1. Clean data\n2. ...',
    category='user',
    description='Data cleaning and analysis'
)

# Autonomous learning
registry.learn_skill(
    name='competitive_analysis',
    content='# Competitive Analysis\n...',
    description='Market analysis method',
    source_task='Analyze competitor market'
)
```

#### Configuration

```bash
SKILL_DB_PATH=skill_registry.db   # SQLite path (default: skill_registry.db)
```

---

### OmniAgent

#### Design Goals

- Possesses all registered skills (skill files injected into virtual filesystem)
- Spawns specialized sub-agents via deepagents' `SubAgent` spec list
- After task success, LLM extracts reusable procedures and saves them as `learned` skills

#### Usage

```python
from src.core.omni_agent import OmniAgent

agent = OmniAgent(agent_id='omni', enable_auto_learning=True)

result = agent.execute_task(
    task_description='Analyze competitor market',
    context={'industry': 'tech', 'region': 'global'}
)

print(result['result'])           # Task result
print(result['learned_skills'])   # Auto-learned skills
```

#### Configuration

```bash
USE_OMNI_AGENT=true
ENABLE_AUTO_LEARNING=true
LEARNING_MIN_OUTPUT_LEN=200
SKILL_DB_PATH=skill_registry.db
```

---

### Testing

```bash
# Run skill system tests
python -m pytest tests/test_skill_system.py -v

# Run DeepAgents integration tests
python -m pytest tests/test_deepagents_integration.py -v
```
