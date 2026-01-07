# Environment Domain Feature Documentation

## Overview

Environment Domain is a virtual collection concept for organizing multiple related environments into a cohesive whole. Domains provide hierarchical location management, allowing agents to understand and describe their location at different precision levels.

### Core Concepts

- **Domain**: A collection of multiple environments representing an abstract location concept
  - Example: "Xiao Ke's Home" = Xiao Ke's Room + Living Room + Kitchen
  - Example: "School" = Classroom + Playground + Library

- **Default Environment**: Each domain can have a default environment for inter-domain navigation
  - Example: When moving from "Xiao Ke's Home" to "School", the agent arrives at the default environment of "School" (e.g., Playground)

- **Precision Levels**:
  - **Low Precision (Domain Level)**: For simple location queries, returns domain name
    - User: "Where are you?"
    - Agent: "I'm at home"
  - **High Precision (Environment Level)**: For detailed environment queries, returns specific environment description
    - User: "What's around you?"
    - Agent: "I'm in Xiao Ke's room. There's a desk, bookshelf, bed..."

## Database Schema

### Environment Domains Table (environment_domains)

Stores basic domain information.

| Field | Type | Description |
|-------|------|-------------|
| uuid | TEXT | Unique identifier for the domain |
| name | TEXT | Domain name (e.g., "Xiao Ke's Home") |
| description | TEXT | Domain description |
| default_environment_uuid | TEXT | UUID of default environment (for inter-domain navigation) |
| created_at | TEXT | Creation timestamp |
| updated_at | TEXT | Last update timestamp |

### Domain-Environment Relations Table (domain_environments)

Stores many-to-many relationships between domains and environments.

| Field | Type | Description |
|-------|------|-------------|
| uuid | TEXT | Unique identifier for the relation |
| domain_uuid | TEXT | Domain UUID (foreign key) |
| environment_uuid | TEXT | Environment UUID (foreign key) |
| created_at | TEXT | Creation timestamp |

## Core API

### DatabaseManager Domain Methods

#### Create Domain
```python
domain_uuid = db.create_domain(
    name="Xiao Ke's Home",
    description="Xiao Ke's warm family home including room, living room, and kitchen",
    default_environment_uuid=living_room_uuid
)
```

#### Query Domains
```python
# Get single domain
domain = db.get_domain(domain_uuid)

# Get domain by name
domain = db.get_domain_by_name("Xiao Ke's Home")

# Get all domains
all_domains = db.get_all_domains()
```

#### Update Domain
```python
db.update_domain(
    domain_uuid,
    name="New Name",
    description="New Description",
    default_environment_uuid=new_default_uuid
)
```

#### Delete Domain
```python
db.delete_domain(domain_uuid)
```

#### Manage Domain-Environment Relations
```python
# Add environment to domain
db.add_environment_to_domain(domain_uuid, environment_uuid)

# Remove environment from domain
db.remove_environment_from_domain(domain_uuid, environment_uuid)

# Get all environments in a domain
environments = db.get_domain_environments(domain_uuid)

# Get all domains an environment belongs to
domains = db.get_environment_domains(environment_uuid)

# Check if environment is in domain
is_in = db.is_environment_in_domain(environment_uuid, domain_uuid)
```

### AgentVisionTool Domain Methods

#### Get Current Domain
```python
current_domain = vision_tool.get_current_domain()
if current_domain:
    print(f"Current domain: {current_domain['name']}")
```

#### Get Domain Description
```python
# Get domain overview description
description = vision_tool.get_domain_description(domain_uuid)

# Get detailed description (including default environment info)
description = vision_tool.get_domain_description(
    domain_uuid, 
    use_default_env=True
)
```

#### Get Vision Context with Precision
```python
# Auto-detect precision requirement
high_precision = vision_tool.detect_precision_requirement(user_query)

# Get context based on precision
vision_context = vision_tool.get_vision_context_with_precision(
    user_query,
    high_precision=high_precision
)

# Format as prompt
prompt = vision_tool.format_vision_prompt(vision_context)
```

#### Domain-Level Navigation
```python
# Switch to specified domain (automatically switches to default environment)
success = vision_tool.switch_to_domain(domain_uuid)

# Detect domain switch intent
switch_intent = vision_tool.detect_domain_switch_intent("go to school")
if switch_intent:
    target_domain = switch_intent['to_domain']
    vision_tool.switch_to_domain(target_domain['uuid'])
```

## Use Cases

### Case 1: Simple Location Query

**User**: "Where are you?"

**Processing Flow**:
1. Detects location query (should_use_vision returns True)
2. Determines low precision requirement (detect_precision_requirement returns False)
3. Gets domain-level context (get_vision_context_with_precision)
4. Returns domain name

**Agent Response**: "I'm at home"

### Case 2: Detailed Environment Query

**User**: "What's around you?"

**Processing Flow**:
1. Detects environment query (should_use_vision returns True)
2. Determines high precision requirement (detect_precision_requirement returns True)
3. Gets detailed environment-level context (get_vision_context)
4. Returns detailed environment description and object list

**Agent Response**: "I'm in Xiao Ke's room. There's a desk, bookshelf, bed, lamp..."

### Case 3: Inter-Domain Navigation

**User**: "Go to school"

**Processing Flow**:
1. Detects domain switch intent (detect_domain_switch_intent)
2. Finds target domain "School"
3. Switches to default environment of School domain (e.g., Playground)
4. Updates current active environment

**Agent Response**: "Okay, I'm now at the school playground"

## Design Considerations

### Why Do We Need Domains?

1. **Natural Interaction**: In daily conversations, people use abstract location concepts
   - "I'm at home" rather than "I'm in the bedroom"
   - "I'm at school" rather than "I'm in the classroom"

2. **Flexible Precision Control**: Provide appropriately detailed responses based on query specificity
   - Simple query → Domain-level response
   - Detailed query → Environment-level response

3. **Convenient Navigation**: Inter-domain switches automatically navigate to default location
   - User says "go to school", agent automatically arrives at default location (e.g., playground)
   - No need for user to specify exact environment

### Precision Detection Logic

The system uses keyword matching to determine query precision requirements:

**High Precision Keywords**:
- specific, detailed, what things, what are, which are
- see, around, nearby, room, house
- objects, items

**Low Precision Queries**:
- Location queries without high precision keywords
- Examples: "Where are you?", "What place are you at?"

## Best Practices

### 1. Organize Domains Logically

Group semantically related environments into the same domain:
```python
# Home domain
home_domain = db.create_domain("Xiao Ke's Home", "...")
db.add_environment_to_domain(home_domain, room_uuid)
db.add_environment_to_domain(home_domain, living_room_uuid)
db.add_environment_to_domain(home_domain, kitchen_uuid)

# School domain
school_domain = db.create_domain("School", "...")
db.add_environment_to_domain(school_domain, classroom_uuid)
db.add_environment_to_domain(school_domain, playground_uuid)
```

### 2. Set Appropriate Default Environments

Choose the most representative or frequently visited environment as the default:
```python
# Set living room as home's default (where family gathers most)
db.update_domain(home_domain, default_environment_uuid=living_room_uuid)

# Set playground as school's default (first place upon arrival)
db.update_domain(school_domain, default_environment_uuid=playground_uuid)
```

### 3. Establish Inter-Domain Connections

Create connections between entry/exit environments of domains:
```python
# From living room at home to playground at school
db.create_environment_connection(
    from_env_uuid=living_room_uuid,
    to_env_uuid=playground_uuid,
    direction='bidirectional',
    description='From home to school'
)
```

## Example Code

For complete usage examples, see:
- `test_domain_feature.py` - Feature test script
- `demo_domain_feature.py` - Demo script

## Extension Suggestions

### Possible Future Enhancements

1. **Domain Hierarchy**: Support nested domains (e.g., "China" -> "Beijing" -> "Chaoyang District")
2. **Dynamic Precision Adjustment**: Auto-adjust precision based on conversation history
3. **Domain Property Inheritance**: Sub-environments inherit certain properties from domain
4. **Path Planning**: Plan optimal paths across multiple domains

## Notes

1. An environment can belong to multiple domains
2. A domain's default environment must be one of its contained environments
3. Deleting a domain doesn't delete its environments, only the associations
4. Precision detection is keyword-based and may not be perfect; consider using LLM in the future
