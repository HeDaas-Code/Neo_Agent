# Environment Switching Feature Documentation

[中文](ENVIRONMENT_SWITCHING.md) | **English**

## Overview

The environment switching feature allows the agent to move between multiple environments, controlling which environments can be switched through connection relationships. This feature enhances the agent's spatial awareness, making conversations more realistic and immersive.

## Main Features

### 1. Environment Connection System

Environments can establish connection relationships, and only connected environments can switch to each other.

#### Connection Types
- `normal` - Normal connection
- `door` - Door
- `portal` - Portal
- `stairs` - Stairs
- `corridor` - Corridor
- `window` - Window
- `other` - Other

#### Connection Direction
- `bidirectional` - Can move in both directions, e.g., A ⟷ B
- `one_way` - Can only move in one direction, e.g., A → B

### 2. Smart Switch Detection

The system automatically detects user's environment switching intent with keywords including:
- go, walk, move, head to, enter
- leave, exit, return, go back
- switch, change to, transfer

Examples:
- "I'll go to the living room" - Will detect the intent to switch to the living room
- "I want to return to my room" - Will detect the intent to switch to the room

### 3. Permission Verification

The system automatically verifies switching permissions:
- ✅ Can only switch to environments connected to the current environment
- ❌ Cannot switch to isolated environments without connections
- ✅ Respects connection directionality (one-way/bidirectional)

### 4. GUI Management Interface

#### Environment Management Panel
- 🔄 Refresh - Refresh environment list
- ➕ New Environment - Create new environment
- ➕ Add Object - Add objects to environment
- 🏠 Create Default Environment - Quickly create sample environment

#### Environment Switching and Connections
- 🔀 Switch Environment - Manually switch to other environments
- 🔗 Manage Connections - Manage environment connection relationships
- 🗺️ Relationship Map - Visualize environment relationships
- 📋 Usage Records - View vision tool usage records

## Usage

### Create Environment

```python
from database_manager import DatabaseManager

db = DatabaseManager()

# Create environment
room_uuid = db.create_environment(
    name="Bedroom",
    overall_description="Cozy bedroom",
    atmosphere="Quiet and comfortable",
    lighting="Soft lighting",
    sounds="Gentle music",
    smells="Light fragrance"
)
```

### Create Connection

```python
# Create bidirectional connection
conn_uuid = db.create_environment_connection(
    from_env_uuid=room_uuid,
    to_env_uuid=living_uuid,
    connection_type="door",
    direction="bidirectional",
    description="Can enter the living room through the door"
)
```

### Check Connectivity

```python
# Check if can move from A to B
can_move = db.can_move_to_environment(room_uuid, living_uuid)
if can_move:
    print("Can move!")
else:
    print("Cannot move!")
```

### Switch Environment

```python
from agent_vision import AgentVisionTool

vision = AgentVisionTool(db)

# Switch to specified environment
success = vision.switch_environment(living_uuid)
if success:
    print("Switch successful!")
```

### Use in Chat

The agent will automatically detect and respond to environment switching suggestions:

```
User: I'll go to the living room
System: 🚪 [Environment Switch] Moved from「Bedroom」to「Living Room」
Agent: Okay, we're in the living room now...
```

## GUI Operation Guide

### Create New Environment

1. Open "👁️ Environment Management" tab
2. Click "➕ New Environment" button
3. Fill in environment information:
   - Environment name
   - Overall description
   - Atmosphere, lighting, sounds, smells (optional)
4. Click "Save"

### Create Environment Connection

1. Click "🔗 Manage Connections" in the environment management panel
2. Click "➕ New Connection"
3. Select source environment and target environment
4. Choose connection type and direction
5. Add connection description (optional)
6. Click "Save"

### Switch Current Environment

1. Click "🔀 Switch Environment" button
2. Select target environment from list
3. Click "Switch"
   - If environments are connected, switches directly
   - If not connected, warns but allows forced switch

### View Environment Relationship Map

1. Click "🗺️ Relationship Map" button
2. View visualized environment relationship map
   - 🔴 Red node - Current active environment
   - 🟢 Green node - Other environments
   - → One-way arrow - One-way connection
   - ⟷ Two-way arrow - Bidirectional connection

## Database Structure

### environment_connections Table

| Field | Type | Description |
|-------|------|-------------|
| uuid | TEXT | Connection unique identifier |
| from_environment_uuid | TEXT | Source environment UUID |
| to_environment_uuid | TEXT | Target environment UUID |
| connection_type | TEXT | Connection type |
| direction | TEXT | Connection direction |
| description | TEXT | Connection description |
| created_at | TEXT | Creation time |
| updated_at | TEXT | Update time |

## API Reference

### DatabaseManager

#### create_environment_connection()
Create environment connection

```python
conn_uuid = db.create_environment_connection(
    from_env_uuid: str,
    to_env_uuid: str,
    connection_type: str = "normal",
    direction: str = "bidirectional",
    description: str = ""
) -> str
```

#### can_move_to_environment()
Check if can move to target environment

```python
can_move = db.can_move_to_environment(
    from_env_uuid: str,
    to_env_uuid: str
) -> bool
```

#### get_connected_environments()
Get all environments connected to specified environment

```python
connected_envs = db.get_connected_environments(
    env_uuid: str
) -> List[Dict[str, Any]]
```

#### get_environment_connections()
Get all connections of an environment

```python
connections = db.get_environment_connections(
    env_uuid: str,
    direction: str = "both"  # "from", "to", "both"
) -> List[Dict[str, Any]]
```

### AgentVisionTool

#### detect_environment_switch_intent()
Detect if user has intent to switch environment

```python
intent = vision.detect_environment_switch_intent(
    user_query: str
) -> Optional[Dict[str, Any]]
```

Return format:
```python
{
    'intent': 'switch_environment',
    'from_env': {...},  # Current environment info
    'to_env': {...},    # Target environment info
    'can_switch': True  # Whether can switch
}
```

#### switch_environment()
Switch to specified environment

```python
success = vision.switch_environment(
    to_env_uuid: str
) -> bool
```

#### get_available_environments_for_switch()
Get list of environments that can be switched to

```python
available_envs = vision.get_available_environments_for_switch()
-> List[Dict[str, Any]]
```

## Testing

Run test script:

```bash
python test_environment_switching.py
```

Tests cover:
- ✅ Environment creation
- ✅ Connection creation
- ✅ Connectivity check
- ✅ Environment switching
- ✅ Permission verification
- ✅ Intent detection

## Best Practices

### 1. Environment Planning

Plan environment layout before creating environment connections:
- Draw environment relationship map
- Determine which environments should be connected
- Decide connection types and directions

### 2. Connection Management

- Use meaningful connection types (door, stairs, etc.)
- Add description information explaining connection characteristics
- Avoid creating overly complex connections with too many cycles

### 3. User Experience

- Keep number of environments reasonable (recommended within 10)
- Keep environment names short and clear
- Connection relationships should be intuitive

### 4. Debugging

Enable DEBUG mode to view detailed switching process:

```python
# Set in .env
DEBUG_MODE=True
```

## Troubleshooting

### Issue 1: Switching doesn't work

**Possible causes:**
- Environments are not connected
- Wrong connection direction (one-way connection)
- Target environment name not in query

**Solutions:**
1. Check environment connections: Click "🔗 Manage Connections"
2. View relationship map: Click "🗺️ Relationship Map"
3. Ensure query includes target environment name

### Issue 2: Cannot create connection

**Possible causes:**
- Connection already exists
- Invalid environment UUID

**Solutions:**
1. Check if same connection already exists
2. Verify environment UUID is correct

### Issue 3: Environment display incomplete

**Possible causes:**
- Database synchronization issue

**Solutions:**
1. Click "🔄 Refresh" button
2. Reload agent

## Future Enhancements

Planned features:
- [ ] Environment switching animations
- [ ] Path planning (automatically find shortest path)
- [ ] Environment visit history
- [ ] Conditional connections (e.g., requiring keys)
- [ ] Time-limited connections (open at specific times)
- [ ] Environment state system (locked/unlocked)

## Version History

### v1.0 (2025-01-18)
- ✅ Initial implementation of environment connection system
- ✅ Implemented smart switch detection
- ✅ Added permission verification
- ✅ Created GUI management interface
- ✅ Added environment relationship visualization
- ✅ Complete test suite

## License

MIT License - Same as main project license

## Support

For questions or suggestions, please submit an Issue on the project GitHub repository.
