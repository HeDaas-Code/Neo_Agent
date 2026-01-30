# MCP Support Documentation

## Overview

Neo Agent now supports the Model Context Protocol (MCP), a standardized protocol for intelligent agent context management and tool integration. MCP support enables the agent to:

- Register and call external tools
- Manage resource access
- Use prompt templates
- Maintain conversation context

## Quick Start

### Enable MCP

Set in `.env` file:

```env
ENABLE_MCP=True
```

### Basic Usage

MCP is automatically integrated into ChatAgent and will auto-initialize when enabled:

```python
from chat_agent import ChatAgent

# MCP will auto-enable if configured in .env
agent = ChatAgent()

# Check MCP status
mcp_info = agent.mcp_manager.get_mcp_info()
print(mcp_info)
```

## MCP Features

### 1. Tool Management

MCP supports registering and calling custom tools.

#### Default Tools

Two built-in tools are available:

- **get_current_time**: Get current time
- **calculate**: Perform mathematical calculations

#### Register Custom Tool

```python
def my_custom_tool(args):
    """Custom tool function"""
    message = args.get("message", "")
    return f"Processing message: {message}"

agent.mcp_manager.register_tool(
    name="my_tool",
    description="My custom tool",
    handler=my_custom_tool,
    parameters={
        "type": "object",
        "properties": {
            "message": {
                "type": "string",
                "description": "Message to process"
            }
        },
        "required": ["message"]
    }
)
```

#### Call Tool

```python
result = agent.mcp_manager.call_tool("my_tool", {"message": "Hello"})
if result['success']:
    print(result['result'])
else:
    print(f"Error: {result['error']}")
```

#### List Available Tools

```python
tools = agent.mcp_manager.get_available_tools()
for tool in tools:
    print(f"{tool['name']}: {tool['description']}")
```

### 2. Resource Management

MCP supports registering and accessing various resources.

#### Default Resources

- **system://info**: Neo Agent system information
- **character://profile**: Agent character profile

#### Register Resource

```python
agent.mcp_manager.register_resource(
    uri="custom://mydata",
    name="My Data",
    description="Custom data resource",
    mime_type="application/json"
)
```

#### Access Resource

```python
result = agent.mcp_manager.get_resource("custom://mydata")
if result['success']:
    print(result['resource'])
```

#### List Resources

```python
resources = agent.mcp_manager.get_available_resources()
for resource in resources:
    print(f"{resource['uri']}: {resource['name']}")
```

### 3. Prompt Templates

MCP supports reusable prompt templates.

#### Default Prompt Templates

- **emotion_analysis**: Emotion analysis prompt
- **task_planning**: Task planning prompt

#### Register Prompt Template

```python
agent.mcp_manager.register_prompt(
    name="greeting",
    description="Greeting template",
    template="Hello, {name}! Welcome to {place}.",
    arguments=[
        {"name": "name", "description": "User name", "required": True},
        {"name": "place", "description": "Location", "required": True}
    ]
)
```

#### Use Prompt Template

```python
result = agent.mcp_manager.get_prompt(
    "greeting",
    {"name": "John", "place": "Neo Agent"}
)
if result['success']:
    print(result['prompt'])  # Output: Hello, John! Welcome to Neo Agent.
```

#### List Prompt Templates

```python
prompts = agent.mcp_manager.get_available_prompts()
for prompt in prompts:
    print(f"{prompt['name']}: {prompt['description']}")
```

### 4. Context Management

MCP automatically maintains conversation context.

#### Add Context

```python
agent.mcp_manager.add_context({
    "user_input": "User's input",
    "timestamp": "2026-01-30 12:00:00",
    "metadata": {"key": "value"}
})
```

#### Get Context

```python
# Get all contexts
contexts = agent.mcp_manager.get_contexts()

# Get recent N contexts
recent_contexts = agent.mcp_manager.get_contexts(limit=5)
```

#### Clear Context

```python
agent.mcp_manager.clear_contexts()
```

## Application in Conversations

MCP context is automatically integrated into the conversation flow:

```python
# MCP tool information is automatically added to system prompts
response = agent.chat("What time is it?")
# Agent can recognize the need to call get_current_time tool

response = agent.chat("Calculate 15 * 8 for me")
# Agent can recognize the need to call calculate tool
```

## MCP Architecture

### Component Structure

```
MCPContextManager (Context Manager)
    ├── MCPClient (MCP Client)
    │   ├── Tool Registry
    │   ├── Resource Registry
    │   ├── Prompt Registry
    │   └── Context Storage
    └── Default Configuration
        ├── Default Tools
        ├── Default Resources
        └── Default Prompts
```

### Data Flow

```
User Input → ChatAgent
    ↓
Check MCP Status
    ↓
Add Conversation Context to MCP
    ↓
Build Message List (including MCP tool info)
    ↓
LLM Generate Response
    ↓
Return to User
```

## Configuration Options

Configure in `.env` file:

```env
# Enable MCP feature
ENABLE_MCP=False

# Debug mode (to view MCP debug logs)
DEBUG_MODE=True
DEBUG_LOG_FILE=debug.log
```

## Testing

Run MCP tests:

```bash
python tests/test_mcp.py
```

Tests cover:
- MCP client basic functionality
- Tool registration and calling
- Resource management
- Prompt templates
- Context management
- Integration scenarios

## API Reference

### MCPContextManager

#### Methods

- `register_tool(name, description, handler, parameters)` - Register tool
- `register_resource(uri, name, description, mime_type)` - Register resource
- `register_prompt(name, description, template, arguments)` - Register prompt
- `call_tool(tool_name, arguments)` - Call tool
- `get_resource(uri)` - Get resource
- `get_prompt(name, arguments)` - Get prompt
- `add_context(context)` - Add context
- `get_contexts(limit)` - Get contexts
- `clear_contexts()` - Clear contexts
- `get_available_tools()` - List tools
- `get_available_resources()` - List resources
- `get_available_prompts()` - List prompts
- `get_mcp_info()` - Get MCP information

### Return Format

All MCP operations return a unified format:

```python
# Success
{
    "success": True,
    "result": <result_data>
}

# Failure
{
    "success": False,
    "error": <error_message>
}
```

## Best Practices

### 1. Tool Naming

Use clear verb+noun format:
- ✅ `get_current_time`
- ✅ `calculate_distance`
- ❌ `time`
- ❌ `calc`

### 2. Parameter Definition

Use JSON Schema format for parameters:

```python
parameters={
    "type": "object",
    "properties": {
        "param1": {
            "type": "string",
            "description": "Parameter description"
        }
    },
    "required": ["param1"]
}
```

### 3. Error Handling

Tool functions should raise meaningful exceptions:

```python
def my_tool(args):
    if not args.get("required_param"):
        raise ValueError("Missing required parameter: required_param")
    # Processing logic
    return result
```

### 4. Resource URI

Use unified URI format:
- `system://` - System resources
- `character://` - Character resources
- `custom://` - Custom resources
- `file://` - File resources

### 5. Prompt Templates

Use Python string formatting syntax:

```python
template="This is {param1}'s {param2}"
```

## Troubleshooting

### MCP Not Enabled

**Issue**: MCP method calls return "MCP not enabled"

**Solution**: Set `ENABLE_MCP=True` in `.env` file

### Tool Not Found

**Issue**: `call_tool` returns "Tool not found"

**Solution**: 
1. Use `get_available_tools()` to check registered tools
2. Verify tool name spelling is correct

### Prompt Rendering Failed

**Issue**: `get_prompt` returns "Prompt rendering failed"

**Solution**:
1. Check if placeholders in template match argument names
2. Ensure all required arguments are provided

## Future Plans

- [ ] MCP server communication support
- [ ] Tool permission management
- [ ] Async tool calling
- [ ] GUI management interface
- [ ] Tool usage statistics
- [ ] Resource caching mechanism
- [ ] Prompt version management

## Contributing

Contributions of new tools, resources, and prompt templates are welcome! Please follow the existing code style and documentation format.

## License

MCP support follows Neo Agent's MIT license.
