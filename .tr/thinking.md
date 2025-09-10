# 思考记录

## 项目概述
这是一个基于AI的文字冒险游戏项目，采用五阶段架构设计。

## Start Game 更新记录 (2025-01-10)

### 更新目标
运用最新的 `test_script_framework.py` 和 `test_five_stage_architecture.py` 成果，更新 `game_controller.py` 以更好地集成五阶段架构和剧本框架。

### 主要更新内容

#### 1. 导入扩展
- 添加了五阶段架构相关类的导入：`CognitionResult`, `MemoryResult`, `UnderstandingResult`, `DecisionResult`, `ExecutionResult`
- 添加了 `StoryNode` 导入，支持剧本框架集成

#### 2. UI 增强
- **状态显示改进**：在 `print_status` 方法中添加了角色能量和心情显示
- **详细状态功能**：新增 `print_detailed_status` 方法，提供：
  - 角色详细信息（健康、能量、心情、位置等）
  - 游戏状态信息（时间、权限、数据碎片等）
  - 剧情系统状态（当前节点、可用分支等）
  - 记忆系统状态（交互历史、知识图谱等）

#### 3. 命令系统扩展
- **新增命令**：
  - `detail/dt` - 查看详细状态
  - `verbose/v` - 切换详细模式（显示五阶段处理过程）
  - `story/s` - 查看当前剧情状态
  - `branches/br` - 查看可用剧情分支
  - `progress/pr` - 查看剧情进度
  - `select [分支ID]` - 选择剧情分支
  - `talk/ask/tell` - 更明确的对话命令

#### 4. 初始化增强
- **五阶段架构验证**：在游戏初始化时测试所有五个阶段
- **剧本框架验证**：检查剧本框架加载状态
- **角色和游戏状态设置**：根据配置文件设置初始状态
- **错误处理改进**：添加详细的错误信息和堆栈跟踪

#### 5. 剧情系统集成
- **剧情状态管理**：
  - `_show_story_status()` - 显示当前剧情节点信息
  - `_show_story_branches()` - 显示可用的剧情分支
  - `_show_story_progress()` - 显示剧情完成进度
  - `_select_story_branch()` - 选择并切换剧情分支

- **自动剧情推进**：
  - `_check_story_progression()` - 基于关键词检测剧情推进机会
  - 支持自动推进（单一分支时）和手动选择（多分支时）

#### 6. 对话处理优化
- **详细模式支持**：可选择显示五阶段处理的详细过程
- **剧情推进检测**：在对话后自动检查是否触发剧情推进
- **错误处理改进**：更好的异常捕获和用户反馈

### 技术架构改进

#### 五阶段架构集成
1. **认知阶段**：分析用户输入，评估置信度
2. **记忆阶段**：检索相关知识和历史交互
3. **理解阶段**：分析上下文和意图
4. **决策阶段**：制定响应策略
5. **执行阶段**：生成最终响应

#### 剧本框架集成
- 支持节点式剧情结构
- 动态分支选择
- 进度跟踪
- 约束条件检查

### 测试验证结果
✅ LLM核心系统初始化成功
✅ 角色设置完成
✅ 初始位置设置
✅ 五阶段架构验证完成
- 认知阶段正常，置信度: 0.9
- 记忆阶段正常，知识节点: 2
- 理解阶段正常
- 决策阶段正常，策略: story_progression
✅ 剧本框架加载完成，节点数: 4

## Bug修复记录 (2025-01-10)

### 问题描述
游戏运行时出现 `AttributeError: 'ScriptFrameworkConstrainer' object has no attribute 'current_node'` 错误

### 根本原因
`game_controller.py` 中的剧情相关方法错误地访问了 `ScriptFrameworkConstrainer` 类不存在的 `current_node` 属性

### 修复内容
1. **_show_story_status方法**: 将 `self.core.script_constrainer.current_node` 改为使用 `get_current_story_node()` 方法
2. **_show_story_branches方法**: 同样修复节点获取方式，并调整分支显示逻辑
3. **_select_story_branch方法**: 修复节点获取和分支切换逻辑，使用 `advance_to_branch()` 方法
4. **_check_story_progression方法**: 修复自动推进逻辑，确保正确获取当前节点信息

### 验证结果
- ✅ 游戏启动正常
- ✅ AI对话系统工作正常
- ✅ 五阶段架构运行稳定
- ✅ 剧情推进检查不再报错
- ✅ 用户交互响应正常

## 当前进展
- ✅ 五阶段架构集成完成
- ✅ 剧本框架集成完成
- ✅ UI增强完成
- ✅ 命令系统扩展完成
- ✅ 测试验证通过
- ✅ 文档更新完成
- ✅ 剧情推进错误修复完成

## 认知阶段置信度优化 (2025-01-10)

### 优化内容
将认知阶段的 `confidence_score` 从写死的 0.9 改为基于 embedding 模型的动态计算

### 实现方案
1. **新增 `_calculate_cognition_confidence` 方法**：
   - 评估游戏场景状态与用户输入的相关性（权重30%）
   - 评估角色信息与用户输入的相关性（权重25%）
   - 评估交互历史与用户输入的相关性（权重20%）
   - 评估场景与角色状态的一致性（权重25%）

2. **技术实现**：
   - 使用 embedding API 获取文本向量
   - 通过余弦相似度计算各部分相关性
   - 根据数据完整性调整最终置信度
   - 确保置信度在 0.1-1.0 范围内

3. **验证结果**：
   - ✅ 动态置信度计算正常工作（从固定0.9变为动态0.427）
   - ✅ 游戏启动和运行正常
   - ✅ 五阶段架构验证通过
   - ✅ 详细的置信度计算日志输出

### 技术细节
- 构建场景、角色、历史三个维度的评估文本
- 使用numpy计算向量相似度
- 加权平均得出综合置信度
- 根据数据完整性进行调整

## 下一步计划
1. 继续优化AI响应质量
2. 扩展更多游戏功能
3. 完善错误处理机制
4. 添加更多剧情分支
5. 优化其他阶段的置信度计算

## LLM核心流程五阶段架构重构设计

### 项目背景
重构 `llm_core.py` 的角色扮演LLM核心流程，从当前的线性处理模式改为五阶段架构，提高代码的可维护性、可扩展性和调试能力。

## 当前架构分析

### 现有process_dialogue方法流程
1. 更新游戏状态 (`_update_game_state`)
2. 获取可用知识 (`knowledge_graph.get_available_knowledge`)
3. 构建系统提示词 (`character_controller.build_system_prompt`)
4. 调用LLM API (`model_manager.call_deepseek_api`)
5. 应用角色约束 (`character_controller.apply_character_constraints`)
6. 存储记忆 (`memory_system.store_memory`)

### 问题分析
- 流程线性化，难以调试和优化单个环节
- 缺乏明确的数据流定义
- 各阶段职责不够清晰
- 难以进行单元测试
- 扩展新功能时需要修改核心流程

## 五阶段架构设计

### 1. 认知阶段 (Cognition Stage)
**职责**: 分析当前游戏环境和角色状态
**输入**: user_input, current_game_state, character_state
**输出**: CognitionResult
- scene_status: 当前场景状态分析
- character_profile: 整合的角色信息
- interaction_history: 玩家交互历史摘要

### 2. 记忆阶段 (Memory Stage)
**职责**: 处理长期记忆和知识检索
**输入**: CognitionResult, user_input
**输出**: MemoryResult
- long_term_memory: 检索到的相关长期记忆
- dialogue_cache: 更新的短期对话缓存
- knowledge_graph_nodes: 关联的知识图谱节点

### 3. 理解阶段 (Understanding Stage)
**职责**: 深度理解用户意图和上下文
**输入**: MemoryResult, user_input, previous_dialogue
**输出**: UnderstandingResult
- last_dialogue_intent: 解析的对话意图
- suggestion_feedback: 建议执行效果评估
- sentiment_shift: 识别的情感倾向变化

### 4. 决策阶段 (Decision Stage)
**职责**: 生成响应策略和行为选择
**输入**: UnderstandingResult, game_constraints
**输出**: DecisionResult
- response_options: 多模态响应选项列表
- action_utility_score: 各选项的效用评分
- dialogue_strategy: 选择的最优对话策略

### 5. 执行阶段 (Execution Stage)
**职责**: 输出最终响应和更新状态
**输入**: DecisionResult, all_previous_results
**输出**: ExecutionResult
- nlp_output: 自然语言响应
- game_action: 触发的游戏行为指令
- character_state_update: 角色状态更新数据

## 数据结构设计

```python
@dataclass
class CognitionResult:
    scene_status: Dict[str, Any]
    character_profile: Dict[str, Any]
    interaction_history: List[Dict[str, Any]]
    timestamp: float
    confidence_score: float

@dataclass
class MemoryResult:
    long_term_memory: List[Dict[str, Any]]
    dialogue_cache: List[Dict[str, Any]]
    knowledge_graph_nodes: List[str]
    memory_relevance_scores: Dict[str, float]

@dataclass
class UnderstandingResult:
    last_dialogue_intent: Dict[str, Any]
    suggestion_feedback: Dict[str, Any]
    sentiment_shift: Dict[str, float]
    context_understanding: str

@dataclass
class DecisionResult:
    response_options: List[Dict[str, Any]]
    action_utility_score: Dict[str, float]
    dialogue_strategy: str
    selected_option_id: str

@dataclass
class ExecutionResult:
    nlp_output: str
    game_action: Dict[str, Any]
    character_state_update: Dict[str, Any]
    execution_metadata: Dict[str, Any]
```

## 实施计划

### 阶段1: 数据结构定义
- 添加五个阶段的结果数据类
- 定义阶段间的数据传递接口
- 添加必要的类型注解

### 阶段2: 阶段方法实现
- 实现 `_cognition_stage()` 方法
- 实现 `_memory_stage()` 方法
- 实现 `_understanding_stage()` 方法
- 实现 `_decision_stage()` 方法
- 实现 `_execution_stage()` 方法

### 阶段3: 主流程重构
- 重构 `process_dialogue()` 方法
- 实现五阶段流水线调用
- 添加阶段间的错误处理
- 保持向后兼容性

### 阶段4: 日志和调试
- 为每个阶段添加详细日志
- 实现阶段执行时间统计
- 添加调试模式支持

### 阶段5: 测试和验证
- 创建单元测试
- 实现集成测试
- 性能对比测试
- 用户体验验证

## 技术考虑

### 异步处理
- 保持所有阶段的async/await模式
- 合理使用并发处理提高性能
- 避免阻塞操作

### 错误处理
- 每个阶段独立的异常处理
- 失败时的降级策略
- 错误信息的详细记录

### 性能优化
- 避免重复计算
- 合理的缓存策略
- 内存使用优化

### 可扩展性
- 插件化的阶段扩展机制
- 配置驱动的行为调整
- 模块化的功能组织

## 预期收益

1. **可维护性提升**: 清晰的阶段划分便于代码维护
2. **调试能力增强**: 每个阶段可独立调试和优化
3. **扩展性改善**: 新功能可以插入到特定阶段
4. **测试覆盖**: 每个阶段可以独立测试
5. **性能监控**: 可以监控每个阶段的执行时间
6. **代码复用**: 阶段方法可以在其他场景复用

## 风险评估

1. **复杂度增加**: 架构变复杂可能增加学习成本
2. **性能开销**: 多阶段处理可能增加执行时间
3. **兼容性问题**: 重构可能影响现有功能
4. **调试难度**: 分阶段处理可能增加调试复杂度

## 缓解策略

1. 详细的文档和注释
2. 完善的测试用例
3. 渐进式重构，保持向后兼容
4. 性能基准测试和优化
5. 充分的代码审查和测试

---

设计时间: 2025-09-10
设计者: AI Assistant
版本: v1.0

# 游戏动作识别问题分析

## 问题描述
用户报告：Terminal#6-129 系统没法理解"周围"的这种说法

## 问题分析

### 1. 初步调查
- 从调试日志看到，系统在处理"系统自检"时识别到0个游戏动作
- 这是正常的，因为"系统自检"不包含预定义的游戏动作关键词

### 2. 测试验证
创建了test_parse_actions.py进行独立测试：
- "看看周围" -> 正确识别为look动作
- "看" -> 正确识别为look动作  
- "查看" -> 正确识别为look动作
- "观察周围" -> 正确识别为look动作

### 3. 问题定位
_parse_game_actions方法工作正常，问题可能在于：
1. 用户实际输入的不是"看看周围"而是其他内容
2. 游戏运行时的某个环节处理有问题
3. 用户期望的行为与实际实现不匹配

## 解决方案

### 方案1：增强"周围"相关的关键词识别
在look_keywords中添加更多与"周围"相关的词汇：
- '周围', '四周', '环境', '附近'

### 方案2：改进动作识别逻辑
当用户输入包含"周围"但没有明确动作词时，默认为look动作

### 方案3：提供更好的用户反馈
当系统无法识别动作时，给出建议的命令格式

## 实施计划
1. 先实施方案1，增强关键词识别
2. 测试验证改进效果
3. 如需要再实施方案2和3