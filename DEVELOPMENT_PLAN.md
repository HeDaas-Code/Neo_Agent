# Neo Agent 核心开发计划 - 让 Agent 真正"活"起来

## 阶段目标
将 Neo Agent 从"功能完备的框架"转变为"能自主思考和行动的虚拟群友"

## 第一阶段：核心对话与推理能力（P0）

### 任务 1：配置真实 LLM
**目标**：接入生产级 LLM，替换测试 mock

**实施**：
1. 创建配置系统 `neo_agent/config.py`
   - 支持环境变量和配置文件
   - LLM 提供商选择（OpenAI/Anthropic/本地模型）
   - API Key 管理（加密存储）
   - 模型参数配置（温度、最大 token 等）

2. 实现 LLM 适配器 `neo_agent/llm/adapters.py`
   - OpenAI 适配器（GPT-4/GPT-3.5）
   - Anthropic 适配器（Claude）
   - 本地模型适配器（Ollama）
   - 统一接口抽象

3. 创建配置 TUI 界面
   - 命令 `:config llm` 打开配置面板
   - API Key 输入和验证
   - 模型选择下拉菜单
   - 测试连接按钮

**验收标准**：
- ✓ 能通过 TUI 配置 LLM
- ✓ API Key 安全存储
- ✓ 成功调用真实 LLM 并返回响应
- ✓ 配置持久化到 PyVDisk

**预计时间**：1-2 天

---

### 任务 2：实现完整的对话推理流程
**目标**：连接认知门控、工具调用和语言生成

**实施**：
1. 完善认知门控 `neo_agent/cognition/gate.py`
   ```python
   class CognitionGate:
       async def decide(
           self, 
           message: str,
           context: ConversationContext
       ) -> CognitionDecision:
           """
           决策流程：
           1. 理解用户意图
           2. 判断需要的操作（查询记忆、更新关系、切换场景等）
           3. 制定回复策略（信息性/情感性/行动性）
           4. 返回结构化决策
           """
   ```

2. 实现工具执行器 `neo_agent/cognition/executor.py`
   ```python
   class ActionExecutor:
       async def execute(
           self,
           decision: CognitionDecision
       ) -> List[ActionResult]:
           """
           执行决策中的操作：
           1. 校验工具权限
           2. 调用 LangChain 工具
           3. 记录审计日志
           4. 返回规范化结果
           """
   ```

3. 实现语言生成器 `neo_agent/cognition/generator.py`
   ```python
   class ReplyGenerator:
       async def generate(
           self,
           context: ConversationContext,
           action_results: List[ActionResult],
           character_state: CharacterState
       ) -> str:
           """
           生成回复：
           1. 只接收规范化的事实和状态
           2. 无工具权限（隔离执行细节）
           3. 基于角色人设生成自然回复
           4. 避免 OOC（out of character）
           """
   ```

4. 整合到对话服务 `neo_agent/runtime/conversation.py`
   ```python
   class ConversationService:
       async def process_message(self, user_message: str) -> AgentReply:
           # 1. 认知门控决策
           decision = await self.gate.decide(user_message, context)
           
           # 2. 执行操作
           results = await self.executor.execute(decision)
           
           # 3. 生成回复
           reply = await self.generator.generate(context, results, state)
           
           # 4. 更新状态（情绪、记忆）
           await self.update_state(decision, results)
           
           return reply
   ```

5. 连接到 ChatView
   - 输入框发送消息到 RPC
   - 显示"思考中..."加载状态
   - 流式显示回复（如果 LLM 支持）
   - 更新情绪和场景显示

**验收标准**：
- ✓ 在 TUI 对话视图中发送消息
- ✓ Agent 能理解意图并调用合适的工具
- ✓ 回复自然且符合角色人设
- ✓ 操作过程不泄露到回复中（措辞隔离）
- ✓ 审计日志记录所有操作

**预计时间**：3-4 天

---

### 任务 3：Agent 自动创作能力
**目标**：根据对话自动注册事件、知识、关系等实体

**实施**：
1. 定义创作意图识别 `neo_agent/cognition/creation.py`
   ```python
   class CreationDetector:
       async def detect(self, conversation: List[Message]) -> List[CreationIntent]:
           """
           识别需要创作的内容：
           - 用户提到新的人/地点 → 创建关系/场景
           - 讨论重要信息 → 注册知识
           - 约定未来活动 → 创建日程
           - 发生重要事件 → 记录事件
           """
   ```

2. 实现创作执行器 `neo_agent/cognition/creator.py`
   ```python
   class AutoCreator:
       async def create_from_intent(self, intent: CreationIntent):
           """
           根据意图自动创作：
           - 提取必要信息
           - 缺少信息时向用户澄清
           - 校验数据合法性
           - 写入 PyVDisk
           - 记录审计
           """
   ```

3. 集成到对话流程
   - 每轮对话后检测创作意图
   - 异步执行创作（不阻塞回复）
   - 创作完成后静默更新或自然提及

**验收标准**：
- ✓ 对话中提到新朋友，自动创建关系实体
- ✓ 讨论重要话题，自动注册知识点
- ✓ 约定见面时间，自动创建共同日程
- ✓ 缺少信息时能澄清而非盲目创建
- ✓ Debug 关闭时不显示创作入口，但自动创作正常

**预计时间**：2-3 天

---

## 第二阶段：场景自动生成与切换（P0）

### 任务 4：基于行程自动生成场景
**目标**：当 Agent 行程需要去新地点时，自动生成场景

**实施**：
1. 场景生成器 `neo_agent/runtime/scene_generator.py`
   ```python
   class SceneGenerator:
       async def generate(
           self,
           activity: str,          # 活动目的（上学、购物、约会）
           character_profile: dict, # 角色设定
           worldview: dict,         # 世界观
           relevant_memories: list  # 相关记忆
       ) -> Scene:
           """
           生成场景：
           1. 从已访问场景池中匹配
           2. 无匹配时，用 LLM 生成新场景
           3. 生成地点名称、描述、区域、物体
           4. 结构化校验
           5. 返回场景数据
           """
   ```

2. 集成到每日行程生成
   - 生成行程时检查场景绑定
   - 新地点触发场景生成
   - 失败时重试或使用默认场景

3. 场景固化机制
   - 首次访问时保存场景设定
   - 后续访问复用，但允许物体状态变化
   - 场景池视图显示访问历史

**验收标准**：
- ✓ 每日行程生成时自动创建所需场景
- ✓ 场景描述自然且符合世界观
- ✓ 已访问场景不重复生成
- ✓ 到达时间自动切换场景
- ✓ 当前场景描述出现在对话上下文中

**预计时间**：2-3 天

---

## 第三阶段：拟人化增强（P1）

### 任务 5：情绪连续性与衰减
**目标**：情绪跨轮次传递，而非每轮独立

**实施**：
1. 情绪状态机 `neo_agent/runtime/emotion.py`
   ```python
   class EmotionTracker:
       def __init__(self):
           self.current_state = "平静"
           self.intensity = 0.0
           self.decay_rate = 0.1  # 每轮衰减 10%
       
       async def update(self, event: str, delta: float):
           """更新情绪，考虑当前状态"""
       
       async def decay(self):
           """自然衰减"""
       
       async def get_display(self) -> str:
           """返回用户可见的情绪描述"""
   ```

2. 集成到对话流程
   - 每轮对话前加载当前情绪
   - 对话后根据内容更新情绪
   - 定时衰减（每 5 分钟）

**验收标准**：
- ✓ 生气后的情绪会持续几轮
- ✓ 没有新刺激时情绪逐渐平复
- ✓ 状态栏实时显示情绪变化

**预计时间**：1 天

---

### 任务 6：关系演变系统
**目标**：关系分数基于多轮证据累积变化

**实施**：
1. 关系证据收集器 `neo_agent/runtime/relationship.py`
   ```python
   class RelationshipTracker:
       async def collect_evidence(
           self,
           conversation: Message,
           confidence: float
       ) -> Optional[RelationshipChange]:
           """
           收集关系变化证据：
           - 需要至少 3 个不同轮次
           - 每次置信度 >= 0.8
           - 变化幅度限制在 -3 到 +3
           """
   ```

2. 自然说明机制
   - 关系显著变化时，在合适时机自然提及
   - 不发送单独的通知
   - 关系视图显示变化历史

**验收标准**：
- ✓ 单次对话不会导致关系剧变
- ✓ 持续友好交流后关系分数上升
- ✓ 关系变化有可追溯的历史记录

**预计时间**：1-2 天

---

### 任务 7：群聊感知（离线回放）
**目标**：为未来真实群聊做准备，实现发言/沉默决策

**实施**：
1. 消息相关性评分 `neo_agent/cognition/relevance.py`
   ```python
   class RelevanceScorer:
       async def score(
           self,
           message: IncomingMessage,
           character_context: dict
       ) -> float:
           """
           评分因素：
           - 是否 @ 提到角色
           - 话题相关性
           - 群聊活跃度
           - 最近发言时间（冷却）
           """
   ```

2. 发言决策器 `neo_agent/cognition/chat_decision.py`
   ```python
   class ChatDecisionMaker:
       async def decide(
           self,
           message: IncomingMessage,
           relevance: float
       ) -> ChatDecision:
           """
           决策：
           - 立即回复（高相关性 + 低冷却）
           - 延迟回复（中等相关性）
           - 沉默（低相关性或冷却中）
           """
   ```

3. 离线回放测试界面
   - TUI 中添加"群聊回放"视图
   - 导入聊天记录 JSON
   - 逐条播放并显示 Agent 的决策
   - 不实际发送消息

**验收标准**：
- ✓ 高相关性消息触发回复
- ✓ 连续发言有冷却时间
- ✓ 低相关性对话保持沉默
- ✓ 离线回放正确展示决策过程

**预计时间**：2-3 天

---

## 第四阶段：开发者体验优化（P2）

### 任务 8：命令模式实现
**目标**：通过 `:` 命令访问设置和高级功能

**实施**：
1. 命令面板 UI `neo_agent/ui/v2/command_panel.py`
2. 命令注册表和路由
3. 实现核心命令：
   - `:config` - 全局配置
   - `:config llm` - LLM 设置
   - `:debug on/off` - 切换调试模式
   - `:export character` - 导出角色
   - `:import <path>` - 导入数据
   - `:help` - 命令帮助

**预计时间**：1-2 天

---

### 任务 9：Debug 模式人工创作入口
**目标**：Debug 开启时显示手动创作界面

**实施**：
1. 全局 Debug 开关（持久化）
2. Debug 模式下各视图显示创建按钮
3. 人工创作表单（角色编辑、场景创建、日程添加等）

**预计时间**：1-2 天

---

## 实施顺序建议

### 第 1 周：核心对话能力
- Day 1-2: 任务 1（配置真实 LLM）
- Day 3-6: 任务 2（对话推理流程）
- Day 7: 任务 3（自动创作）启动

### 第 2 周：自动创作与场景生成
- Day 8-9: 任务 3（自动创作）完成
- Day 10-12: 任务 4（场景自动生成）

### 第 3 周：拟人化增强
- Day 13: 任务 5（情绪连续性）
- Day 14-15: 任务 6（关系演变）
- Day 16-18: 任务 7（群聊感知）

### 第 4 周：体验优化
- Day 19-20: 任务 8（命令模式）
- Day 21-22: 任务 9（Debug 模式）
- Day 23-24: 整体测试和文档更新
- Day 25: 发布里程碑版本

## 技术栈补充

需要添加的依赖：
```bash
# LLM 客户端
pip install openai anthropic

# 加密存储
pip install cryptography

# 配置管理
pip install pydantic-settings

# 流式输出
pip install aiostream
```

## 验收里程碑

### Alpha 版本（第 1-2 周后）
- ✓ 能进行自然对话
- ✓ 自动创建实体
- ✓ 场景自动生成和切换

### Beta 版本（第 3 周后）
- ✓ 情绪和关系有连续性
- ✓ 群聊决策逻辑完整

### RC 版本（第 4 周后）
- ✓ 命令模式可用
- ✓ Debug 模式完整
- ✓ 文档齐全
- ✓ 可对外演示

## 风险与缓解

**风险 1**: LLM API 成本过高
- **缓解**: 先用 GPT-3.5 开发，只在关键场景用 GPT-4；支持本地模型（Ollama）

**风险 2**: 自动创作质量不稳定
- **缓解**: 严格结构化校验 + 人工审核机制（Debug 模式）

**风险 3**: 场景生成太慢影响体验
- **缓解**: 异步生成 + 缓存常用场景 + 优雅降级（使用默认场景）

**风险 4**: 情绪/关系算法不够自然
- **缓解**: 可调参数 + 日志追踪 + 社区反馈迭代

---

**制定日期**: 2026-10-05  
**目标**: 30 天内完成核心 Agent 能力，使其成为真正的"虚拟群友"  
**对标项目**: MaiBot (https://github.com/Mai-with-u/MaiBot)
