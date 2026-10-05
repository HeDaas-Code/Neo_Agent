# Neo Agent 下一步开发计划

## 🎯 当前状态总结

### ✅ 已完成的核心架构
1. **服务-客户端分离** - 守护进程独立运行，TUI可随时连接/断开
2. **PyVDisk持久化** - 统一的数据存储接口，支持重启恢复
3. **现代化TUI** - 琥珀主题，流畅的导航和交互
4. **运行时服务** - 角色、场景、日程、关系、情绪管理
5. **RPC API** - 18个完整的JSON-RPC方法

### 🏗️ 当前架构优势
- **服务独立运行** - TUI关闭后服务继续工作
- **异步非阻塞** - 所有操作都是异步的，不会卡死
- **可扩展性强** - 易于添加新功能和新视图
- **测试覆盖** - 导航、RPC、视图数据加载都有测试

---

## 📋 P0: LangChain Agent 集成（最高优先级）

### 目标
让 Agent 可以进行真实的对话，并具备工具调用能力。

### 实施步骤

#### 第一阶段：基础 Agent 框架（1天）

**1. 创建 Agent 运行时**
```python
# neo_agent/runtime/agent.py

class AgentRuntime:
    """Agent 运行时管理器"""
    
    def __init__(self, llm, tools, memory):
        self.llm = llm
        self.tools = tools
        self.memory = memory
        self.agent_executor = None
    
    async def initialize(self):
        """初始化 Agent"""
        # 创建 LangChain Agent
        # 配置工具和记忆
        pass
    
    async def process_message(self, message: str, context: dict) -> dict:
        """处理消息"""
        # 调用 Agent
        # 返回回复和元数据
        pass
```

**2. 配置 LLM 连接**
```python
# neo_agent/config.py

import os
from langchain_openai import ChatOpenAI

def get_llm():
    """获取配置的LLM"""
    api_key = os.getenv("OPENAI_API_KEY") or os.getenv("SILICONFLOW_API_KEY")
    base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
    
    return ChatOpenAI(
        api_key=api_key,
        base_url=base_url,
        model="gpt-4o-mini",
        temperature=0.7
    )
```

**3. 更新 RPC 处理器**
```python
# neo_agent/service/rpc_handlers.py

async def session_send_message(self, params: Dict[str, Any]) -> Dict[str, Any]:
    """发送消息（真实实现）"""
    text = params.get("text", "")
    
    # 获取上下文
    context = {
        "character": self.services["role"].get_character(),
        "scene": self.services["scene"].get_current_scene(),
        "emotion": self.services["emotion"].get_current_emotion(),
        "relationships": self.services["relationship"].list_all()
    }
    
    # 调用 Agent
    result = await self.agent_runtime.process_message(text, context)
    
    # 保存对话历史
    # 更新情绪状态
    
    return result
```

#### 第二阶段：基础工具集（1-2天）

**创建工具目录结构**
```
neo_agent/runtime/tools/
├── __init__.py
├── base.py           # 工具基类
├── memory.py         # 记忆工具
├── schedule.py       # 日程工具
├── relationship.py   # 关系工具
├── scene.py          # 场景工具
└── knowledge.py      # 知识工具
```

**示例工具实现**
```python
# neo_agent/runtime/tools/memory.py

from langchain.tools import Tool
from typing import Dict, Any

def create_memory_tools(memory_service):
    """创建记忆相关工具"""
    
    def search_memory(query: str) -> str:
        """搜索记忆"""
        results = memory_service.search(query, limit=5)
        return "\n".join([r["content"] for r in results])
    
    def add_memory(content: str, importance: str = "normal") -> str:
        """添加新记忆"""
        memory_service.add(content, importance=importance)
        return "记忆已保存"
    
    return [
        Tool(
            name="search_memory",
            func=search_memory,
            description="搜索过去的记忆和对话历史"
        ),
        Tool(
            name="add_memory",
            func=add_memory,
            description="保存重要的信息到记忆中"
        )
    ]
```

#### 第三阶段：认知门控原型（1天）

**分离决策和语言生成**
```python
# neo_agent/runtime/cognition.py

class CognitionGate:
    """认知门控 - 负责决策和工具调用"""
    
    def __init__(self, llm, tools):
        self.llm = llm
        self.tools = tools
    
    async def decide(self, message: str, context: dict) -> dict:
        """决策阶段 - 可以使用工具"""
        # 分析消息
        # 决定是否需要工具
        # 执行工具调用
        # 返回决策结果
        pass

# neo_agent/runtime/expression.py

class ExpressionGenerator:
    """语言生成器 - 负责生成回复"""
    
    def __init__(self, llm):
        self.llm = llm  # 无工具权限
    
    async def generate(self, context: dict, facts: dict) -> str:
        """生成回复 - 只能访问规范化的事实"""
        # 根据角色设定
        # 结合当前场景
        # 生成自然的回复
        pass
```

#### 测试验收

**功能测试**
```python
# tests/test_agent_integration.py

async def test_basic_conversation():
    """测试基础对话"""
    agent = AgentRuntime(...)
    response = await agent.process_message("你好")
    assert "reply" in response
    assert response["reply"]  # 非空回复

async def test_tool_usage():
    """测试工具调用"""
    agent = AgentRuntime(...)
    response = await agent.process_message("帮我记住今天很开心")
    # 验证记忆工具被调用
    
async def test_context_awareness():
    """测试上下文感知"""
    agent = AgentRuntime(...)
    context = {"scene": {"location": "图书馆"}}
    response = await agent.process_message("这里怎么样？", context)
    # 验证回复提到图书馆
```

**集成测试**
```bash
# 启动服务
./start_service.sh

# 启动TUI，发送消息
python -m neo_agent.ui.v2

# 验证：
# 1. 消息发送成功
# 2. Agent 有回复
# 3. 情绪状态更新
# 4. 对话历史保存
```

---

## 📋 P1: 日程驱动场景系统

### 目标
Agent 每天自动生成行程，根据行程自动切换场景。

### 实施步骤

#### 第一阶段：每日行程生成（1天）

**创建日程生成服务**
```python
# neo_agent/runtime/itinerary.py

class DailyItineraryService:
    """每日行程生成服务"""
    
    def __init__(self, llm, character_service, scene_service):
        self.llm = llm
        self.character = character_service
        self.scene = scene_service
    
    async def generate_today_itinerary(self) -> list:
        """生成今日行程"""
        # 基于角色设定
        # 考虑世界观
        # 生成合理的行程
        pass
    
    def should_generate_today(self) -> bool:
        """判断是否需要生成今日行程"""
        # 检查是否已生成
        # 检查日期是否变化
        pass
```

**添加定时任务**
```python
# neo_agent/service/scheduler.py

import asyncio
from datetime import datetime, time

class BackgroundScheduler:
    """后台调度器"""
    
    def __init__(self, itinerary_service):
        self.itinerary = itinerary_service
        self.running = False
    
    async def start(self):
        """启动调度器"""
        self.running = True
        asyncio.create_task(self._daily_task())
    
    async def _daily_task(self):
        """每日任务"""
        while self.running:
            now = datetime.now()
            target = datetime.combine(now.date(), time(0, 5))
            
            if now > target:
                target = target.replace(day=target.day + 1)
            
            await asyncio.sleep((target - now).total_seconds())
            
            # 生成今日行程
            await self.itinerary.generate_today_itinerary()
```

#### 第二阶段：场景生成与切换（1-2天）

**场景自动生成**
```python
# neo_agent/runtime/scene.py (扩展)

async def generate_scene(self, purpose: str, context: dict) -> dict:
    """根据目的生成新场景"""
    # 使用 LLM 生成场景
    # 包括地点、区域、物体
    # 保存到场景池
    pass

async def activate_scene(self, scene_id: str, area: str = None):
    """激活场景"""
    # 切换当前场景
    # 广播场景切换事件
    pass
```

**场景调度器**
```python
# neo_agent/service/scene_scheduler.py

class SceneScheduler:
    """场景调度器"""
    
    async def check_and_switch(self):
        """检查并切换场景"""
        now = datetime.now()
        current_itinerary = self.get_current_itinerary(now)
        
        if current_itinerary and current_itinerary.scene:
            await self.scene_service.activate_scene(
                current_itinerary.scene
            )
```

#### 第三阶段：共同活动决策（1天）

**冲突判断与处理**
```python
# neo_agent/runtime/schedule.py (扩展)

async def handle_schedule_conflict(
    self, 
    agent_schedule: dict, 
    shared_schedule: dict
) -> dict:
    """处理日程冲突"""
    # 使用 LLM 判断
    # Agent 自主决定调整或取消
    # 保存决策记录
    pass
```

---

## 📋 P2: 认知门控与拟人化

### 目标
完整实现三阶段流程：认知 → 执行 → 表达，防止 OOC。

### 关键点
1. **认知门控** - 可以调用工具，但不生成最终回复
2. **执行引擎** - 执行工具调用，记录审计
3. **语言生成** - 无工具权限，只能生成自然语言

### 数据流
```
用户消息
  ↓
认知门控 (with tools)
  ↓
决策结果 (CognitionDecision)
  ↓
执行引擎
  ↓
操作结果 (ActionResult)
  ↓
语言生成 (no tools)
  ↓
最终回复 (ReplyCandidate)
```

---

## 🧪 测试策略

### 单元测试
- 每个服务独立测试
- Mock LLM 响应
- 验证数据持久化

### 集成测试
- RPC API 端到端测试
- TUI 交互测试 (Textual Pilot)
- 场景切换流程测试

### 压力测试
- 并发 RPC 请求
- 长时间运行稳定性
- 内存泄漏检查

---

## 🔑 环境配置

### 必需的环境变量
```bash
# LLM 配置
export OPENAI_API_KEY="sk-..."
# 或
export SILICONFLOW_API_KEY="sk-..."

# 可选：自定义 API 端点
export OPENAI_BASE_URL="https://api.siliconflow.cn/v1"

# 可选：数据目录
export NEO_AGENT_DATA_DIR="~/.neo_agent"
```

### 推荐的开发环境
```bash
# 创建 .env 文件
cat > .env << 'EOL'
OPENAI_API_KEY=your-key-here
OPENAI_BASE_URL=https://api.siliconflow.cn/v1
NEO_AGENT_DATA_DIR=~/.neo_agent
DEBUG=true
EOL

# 加载环境变量
source .env
```

---

## 📊 开发里程碑

### Week 1: Agent 基础能力
- [ ] LangChain Agent 集成
- [ ] 基础工具集（记忆、日程、关系）
- [ ] 对话功能测试通过

### Week 2: 场景系统
- [ ] 每日行程生成
- [ ] 场景自动生成
- [ ] 场景切换调度

### Week 3: 认知优化
- [ ] 完整的三阶段流程
- [ ] 群聊感知原型
- [ ] 审计日志完善

### Week 4: 测试与优化
- [ ] 完整的测试覆盖
- [ ] 性能优化
- [ ] 文档完善

---

## 🎯 成功标准

### Agent 对话
- ✅ 可以进行自然的多轮对话
- ✅ 回复符合角色设定
- ✅ 能够记住对话历史
- ✅ 可以调用工具完成任务

### 场景系统
- ✅ 每天自动生成合理的行程
- ✅ 根据行程自动切换场景
- ✅ 场景描述自然丰富
- ✅ 支持场景复用和固化

### 拟人化
- ✅ 回复不包含工具调用痕迹
- ✅ 语言风格一致且自然
- ✅ 情绪变化合理
- ✅ 关系更新有据可依

---

**下一步行动**: 开始 P0 - LangChain Agent 集成

准备就绪后运行:
```bash
cd /home/hedass/桌面/Lien_os
source venv/bin/activate
# 设置环境变量
export OPENAI_API_KEY="your-key-here"
# 开始开发
```
