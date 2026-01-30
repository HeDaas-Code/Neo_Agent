# MCP支持文档

## 概述

Neo Agent现在支持Model Context Protocol (MCP)，这是一个用于智能体上下文管理和工具集成的标准化协议。MCP支持使得智能体能够：

- 注册和调用外部工具
- 管理资源访问
- 使用提示词模板
- 维护对话上下文

## 快速开始

### 启用MCP

在`.env`文件中设置：

```env
ENABLE_MCP=True
```

### 基本使用

MCP已自动集成到ChatAgent中，启用后会自动初始化：

```python
from chat_agent import ChatAgent

# MCP会在ChatAgent初始化时自动启用（如果在.env中配置）
agent = ChatAgent()

# 查看MCP状态
mcp_info = agent.mcp_manager.get_mcp_info()
print(mcp_info)
```

## MCP功能

### 1. 工具管理

MCP支持注册和调用自定义工具。

#### 默认工具

系统已预置两个工具：

- **get_current_time**: 获取当前时间
- **calculate**: 执行数学计算

#### 注册自定义工具

```python
def my_custom_tool(args):
    """自定义工具函数"""
    message = args.get("message", "")
    return f"处理消息: {message}"

agent.mcp_manager.register_tool(
    name="my_tool",
    description="我的自定义工具",
    handler=my_custom_tool,
    parameters={
        "type": "object",
        "properties": {
            "message": {
                "type": "string",
                "description": "要处理的消息"
            }
        },
        "required": ["message"]
    }
)
```

#### 调用工具

```python
result = agent.mcp_manager.call_tool("my_tool", {"message": "Hello"})
if result['success']:
    print(result['result'])
else:
    print(f"错误: {result['error']}")
```

#### 列出可用工具

```python
tools = agent.mcp_manager.get_available_tools()
for tool in tools:
    print(f"{tool['name']}: {tool['description']}")
```

### 2. 资源管理

MCP支持注册和访问各类资源。

#### 默认资源

- **system://info**: Neo Agent系统信息
- **character://profile**: 智能体角色档案

#### 注册资源

```python
agent.mcp_manager.register_resource(
    uri="custom://mydata",
    name="我的数据",
    description="自定义数据资源",
    mime_type="application/json"
)
```

#### 访问资源

```python
result = agent.mcp_manager.get_resource("custom://mydata")
if result['success']:
    print(result['resource'])
```

#### 列出资源

```python
resources = agent.mcp_manager.get_available_resources()
for resource in resources:
    print(f"{resource['uri']}: {resource['name']}")
```

### 3. 提示词模板

MCP支持可复用的提示词模板。

#### 默认提示词模板

- **emotion_analysis**: 情感分析提示词
- **task_planning**: 任务规划提示词

#### 注册提示词模板

```python
agent.mcp_manager.register_prompt(
    name="greeting",
    description="问候语模板",
    template="你好，{name}！欢迎来到{place}。",
    arguments=[
        {"name": "name", "description": "用户名", "required": True},
        {"name": "place", "description": "地点", "required": True}
    ]
)
```

#### 使用提示词模板

```python
result = agent.mcp_manager.get_prompt(
    "greeting",
    {"name": "张三", "place": "Neo Agent"}
)
if result['success']:
    print(result['prompt'])  # 输出: 你好，张三！欢迎来到Neo Agent。
```

#### 列出提示词模板

```python
prompts = agent.mcp_manager.get_available_prompts()
for prompt in prompts:
    print(f"{prompt['name']}: {prompt['description']}")
```

### 4. 上下文管理

MCP自动维护对话上下文。

#### 添加上下文

```python
agent.mcp_manager.add_context({
    "user_input": "用户的输入",
    "timestamp": "2026-01-30 12:00:00",
    "metadata": {"key": "value"}
})
```

#### 获取上下文

```python
# 获取所有上下文
contexts = agent.mcp_manager.get_contexts()

# 获取最近N个上下文
recent_contexts = agent.mcp_manager.get_contexts(limit=5)
```

#### 清除上下文

```python
agent.mcp_manager.clear_contexts()
```

## 在对话中的应用

MCP上下文会自动集成到对话流程中：

```python
# MCP工具信息会自动添加到系统提示词中
response = agent.chat("现在几点了？")
# 智能体可以识别需要调用 get_current_time 工具

response = agent.chat("帮我算一下 15 * 8")
# 智能体可以识别需要调用 calculate 工具
```

## MCP架构

### 组件结构

```
MCPContextManager (上下文管理器)
    ├── MCPClient (MCP客户端)
    │   ├── 工具注册表
    │   ├── 资源注册表
    │   ├── 提示词注册表
    │   └── 上下文存储
    └── 默认配置
        ├── 默认工具
        ├── 默认资源
        └── 默认提示词
```

### 数据流

```
用户输入 → ChatAgent
    ↓
检查MCP状态
    ↓
添加对话上下文到MCP
    ↓
构建消息列表（包含MCP工具信息）
    ↓
LLM生成回复
    ↓
返回给用户
```

## 配置选项

在`.env`文件中可以配置：

```env
# 启用MCP功能
ENABLE_MCP=False

# Debug模式（可以查看MCP调试日志）
DEBUG_MODE=True
DEBUG_LOG_FILE=debug.log
```

## 测试

运行MCP测试：

```bash
python tests/test_mcp.py
```

测试涵盖：
- MCP客户端基础功能
- 工具注册和调用
- 资源管理
- 提示词模板
- 上下文管理
- 集成场景

## API参考

### MCPContextManager

#### 方法

- `register_tool(name, description, handler, parameters)` - 注册工具
- `register_resource(uri, name, description, mime_type)` - 注册资源
- `register_prompt(name, description, template, arguments)` - 注册提示词
- `call_tool(tool_name, arguments)` - 调用工具
- `get_resource(uri)` - 获取资源
- `get_prompt(name, arguments)` - 获取提示词
- `add_context(context)` - 添加上下文
- `get_contexts(limit)` - 获取上下文
- `clear_contexts()` - 清除上下文
- `get_available_tools()` - 列出工具
- `get_available_resources()` - 列出资源
- `get_available_prompts()` - 列出提示词
- `get_mcp_info()` - 获取MCP信息

### 返回格式

所有MCP操作返回统一格式：

```python
# 成功
{
    "success": True,
    "result": <结果数据>
}

# 失败
{
    "success": False,
    "error": <错误信息>
}
```

## 最佳实践

### 1. 工具命名

使用清晰的动词+名词格式：
- ✅ `get_current_time`
- ✅ `calculate_distance`
- ❌ `time`
- ❌ `calc`

### 2. 参数定义

使用JSON Schema格式定义参数：

```python
parameters={
    "type": "object",
    "properties": {
        "param1": {
            "type": "string",
            "description": "参数说明"
        }
    },
    "required": ["param1"]
}
```

### 3. 错误处理

工具函数应该抛出有意义的异常：

```python
def my_tool(args):
    if not args.get("required_param"):
        raise ValueError("缺少必需参数: required_param")
    # 处理逻辑
    return result
```

### 4. 资源URI

使用统一的URI格式：
- `system://` - 系统资源
- `character://` - 角色资源
- `custom://` - 自定义资源
- `file://` - 文件资源

### 5. 提示词模板

使用Python字符串格式化语法：

```python
template="这是{param1}的{param2}"
```

## 故障排除

### MCP未启用

**问题**: 调用MCP方法返回"MCP未启用"

**解决**: 在`.env`文件中设置`ENABLE_MCP=True`

### 工具未找到

**问题**: `call_tool`返回"工具未找到"

**解决**: 
1. 使用`get_available_tools()`检查已注册的工具
2. 确认工具名称拼写正确

### 提示词渲染失败

**问题**: `get_prompt`返回"提示词渲染失败"

**解决**:
1. 检查模板中的占位符与传入的参数名称是否匹配
2. 确保必需的参数都已提供

## 未来规划

- [ ] MCP服务器通信支持
- [ ] 工具权限管理
- [ ] 异步工具调用
- [ ] GUI管理界面
- [ ] 工具使用统计
- [ ] 资源缓存机制
- [ ] 提示词版本管理

## 贡献

欢迎贡献新的工具、资源和提示词模板！请遵循现有的代码风格和文档格式。

## 许可证

MCP支持遵循Neo Agent的MIT许可证。
