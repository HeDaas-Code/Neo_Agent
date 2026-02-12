# NPS网络搜索和智能体集成完整指南

## 概述

本文档说明如何使用新添加的SerpAPI网络搜索插件，以及如何让智能体协作系统调用NPS工具。

## 功能特性

### 1. SerpAPI网络搜索插件
- **工具ID**: `websearch`
- **功能**: 使用SerpAPI进行网络搜索，获取实时信息
- **支持**: Google搜索、答案框、知识图谱

### 2. NPS-智能体桥接
- 智能体可以调用所有NPS工具
- 透明集成，对智能体来说就是普通的LangChain Tool
- 智能体根据任务需求自动决定是否调用

## 配置步骤

### 步骤1: 配置API密钥

编辑`.env`文件，添加SerpAPI密钥：

```bash
# SerpAPI配置（用于网络搜索工具）
SERPAPI_API_KEY=your-serpapi-key-here
```

### 步骤2: NPS系统自动加载

NPS系统会自动扫描并加载`websearch`插件，无需手动配置。

### 步骤3: 智能体集成（可选）

如果需要在智能体协作中使用NPS工具，需要在创建智能体时传入NPS工具列表。

## 使用方式

### 方式1: 通过ChatAgent自动调用

ChatAgent在理解阶段会自动判断是否需要调用NPS工具：

```python
# 用户输入
user_input = "搜索关于明日方舟终末地的相关信息"

# ChatAgent自动判断并调用websearch工具
response = chat_agent.chat(user_input)
```

**自动调用流程**:
1. 用户输入被送入理解阶段
2. NPS Invoker判断输入与`websearch`工具相关（通过关键词或LLM）
3. 自动调用`websearch`工具获取搜索结果
4. 搜索结果作为上下文注入到主模型
5. 主模型参考搜索结果生成回复

### 方式2: 智能体协作中调用

当任务被分配给子智能体时，子智能体可以主动调用NPS工具：

```python
# 在dynamic_multi_agent_graph.py中集成
from src.tools.nps_bridge_tool import NPSBridgeTool
from src.tools.nps_langchain_tools import create_nps_tools

# 创建NPS桥接
nps_bridge = NPSBridgeTool(chat_agent.nps_invoker)

# 创建LangChain工具
nps_tools = create_nps_tools(nps_bridge)

# 创建子智能体时添加NPS工具
agent = DeepSubAgentWrapper(
    agent_id='search_agent',
    role='网络信息检索员',
    description='负责在网络上搜索和收集信息',
    tools=nps_tools  # ← 智能体可以使用的NPS工具
)

# 智能体执行任务
result = agent.execute_task(
    task_description="搜索明日方舟终末地的相关信息",
    context={}
)
```

**智能体调用流程**:
1. 系统创建子智能体并传入NPS工具列表
2. 子智能体分析任务，决定需要调用`nps_web_search`工具
3. 子智能体调用工具：`nps_web_search("明日方舟终末地")`
4. SerpAPI返回搜索结果
5. 子智能体分析整合结果，生成任务输出

### 方式3: 直接调用NPS Invoker

在代码中直接调用：

```python
from src.nps.nps_invoker import NPSInvoker

# 创建invoker
invoker = NPSInvoker()

# 方式A：通过invoke_tool_by_name直接调用
result = invoker.invoke_tool_by_name('websearch', {
    'query': '搜索内容',
    'num_results': 5
})

# 方式B：通过invoke_relevant_tools自动判断并调用
result = invoker.invoke_relevant_tools('搜索关于AI的最新新闻')
```

### 方式4: 使用NPS Bridge Tool

```python
from src.tools.nps_bridge_tool import NPSBridgeTool

# 创建桥接工具
bridge = NPSBridgeTool(nps_invoker)

# 网络搜索
search_result = bridge.search_web('明日方舟终末地', num_results=5)

# 系统时间
time_result = bridge.get_system_time()

# 查看可用工具
tools = bridge.get_available_tools()
print(bridge.format_tool_list_for_agent())
```

## 搜索工具参数

### websearch工具支持的参数

```python
context = {
    'query': '搜索查询',         # 必需：搜索内容
    'num_results': 5,            # 可选：返回结果数（默认5）
    'engine': 'google',          # 可选：搜索引擎（默认google）
    'language': 'zh-cn',         # 可选：语言（默认中文）
    'timeout': 10                # 可选：超时时间（默认10秒）
}
```

### 搜索结果格式

```python
{
    'success': True,
    'query': '搜索内容',
    'num_results': 5,
    'results': [
        {
            'title': '标题',
            'link': 'https://...',
            'snippet': '摘要...',
            'position': 1
        },
        ...
    ],
    'answer_box': {  # 如果有
        'title': '...',
        'answer': '...'
    },
    'knowledge_graph': {  # 如果有
        'title': '...',
        'description': '...'
    },
    'context': '格式化的上下文描述'
}
```

## 集成到现有系统

### ChatAgent集成

在`src/core/chat_agent.py`中：

```python
# 初始化时创建NPS桥接
from src.tools.nps_bridge_tool import NPSBridgeTool

class ChatAgent:
    def __init__(self, ...):
        ...
        # NPS系统
        self.nps_invoker = NPSInvoker(registry)
        self.nps_bridge = NPSBridgeTool(self.nps_invoker)  # ← 新增
```

### DynamicMultiAgentGraph集成

在`src/core/dynamic_multi_agent_graph.py`中：

```python
from src.tools.nps_bridge_tool import NPSBridgeTool
from src.tools.nps_langchain_tools import create_nps_tools

class DynamicMultiAgentGraph:
    def __init__(self, chat_agent, ...):
        ...
        # 创建NPS工具
        self.nps_bridge = NPSBridgeTool(chat_agent.nps_invoker)
        self.nps_tools = create_nps_tools(self.nps_bridge)
    
    def _create_agent(self, agent_config):
        # 创建子智能体时传入NPS工具
        agent = DeepSubAgentWrapper(
            agent_id=agent_config['agent_id'],
            role=agent_config['role'],
            description=agent_config['description'],
            tools=self.nps_tools  # ← 添加NPS工具
        )
        return agent
```

## 智能体工具描述

智能体看到的工具描述：

### nps_web_search
```
使用SerpAPI进行网络搜索，获取实时信息、新闻、知识等。

适用场景：
- 需要查询最新信息、新闻、动态
- 搜索特定内容、知识、资料
- 获取网络上的公开信息
- 需要验证或补充信息

输入格式：搜索查询文本（如"明日方舟终末地"、"最新AI新闻"等）
输出格式：格式化的搜索结果，包含标题、摘要、链接等
```

### nps_system_time
```
获取当前系统时间、日期、星期等信息。

适用场景：
- 回答"现在几点"、"今天星期几"等时间相关问题
- 需要知道当前日期、时间来完成任务
- 判断时间段（早上/中午/晚上等）

输入格式：不需要输入，直接调用即可
输出格式：当前时间的详细信息（年月日、时分秒、星期、时段等）
```

## 完整使用示例

### 示例1: 用户直接提问（自动调用）

```python
# 用户输入
user_input = "搜索最新的AI技术新闻"

# ChatAgent处理
response = chat_agent.chat(user_input)

# 内部流程：
# 1. 理解阶段：NPS Invoker判断需要websearch工具
# 2. 自动调用：websearch("最新的AI技术新闻")
# 3. 获取结果：5条搜索结果
# 4. 上下文注入：将搜索结果作为上下文
# 5. 生成回复：主模型参考搜索结果生成回复

# 用户得到：包含最新AI新闻的详细回复
```

### 示例2: 任务型事件（智能体调用）

```python
# 用户创建任务
event = TaskEvent(
    title="研究明日方舟终末地的设定",
    description="需要搜索并分析明日方舟终末地的相关信息"
)

# 系统处理：
# 1. 编排计划：决定使用sequential策略
# 2. 创建子智能体：
#    - 智能体1: 网络信息检索员（配备nps_web_search工具）
#    - 智能体2: 信息分析师
# 3. 智能体1执行：
#    - 分析任务：需要搜索网络信息
#    - 调用工具：nps_web_search("明日方舟终末地")
#    - 获取结果：搜索到多条相关信息
#    - 输出：整理的搜索结果
# 4. 智能体2执行：
#    - 分析智能体1的输出
#    - 生成报告
# 5. 综合结果：生成最终报告

# 用户得到：详细的分析报告
```

## 错误处理

### SERPAPI_API_KEY未配置

```
搜索失败：SerpAPI密钥未配置，请在.env文件中设置SERPAPI_API_KEY
```

**解决方案**: 在`.env`文件中添加`SERPAPI_API_KEY=your-key`

### API请求超时

```
搜索失败：搜索请求超时
```

**解决方案**: 增加timeout参数或检查网络连接

### 工具未找到

```
工具未找到: websearch
```

**解决方案**: 确保`src/nps/tool/websearch.NPS`文件存在且enabled为true

## 开发者注意事项

### 添加新的NPS工具

1. 创建工具实现：`src/nps/tool/newtool.py`
2. 创建元数据：`src/nps/tool/newtool.NPS`
3. 创建LangChain包装：在`nps_langchain_tools.py`中添加

### 调试

启用DEBUG_MODE查看详细日志：

```bash
DEBUG_MODE=true
DEBUG_LOG_FILE=debug.log
```

日志会显示：
- NPS工具调用
- 智能体决策过程
- 搜索API请求和响应
- 错误和异常

## 总结

现在Neo Agent具备了完整的网络搜索能力：

1. **用户层面**: 直接提问即可，系统自动判断并搜索
2. **智能体层面**: 子智能体可以主动调用搜索工具
3. **开发者层面**: 灵活的API支持多种调用方式

智能体协作系统现在可以获取实时网络信息，大大增强了处理能力！
