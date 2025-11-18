# Intelligent Agent Pseudo-Vision Feature Documentation

[中文](VISION_FEATURE_README.md) | **English**

## Feature Overview

The Intelligent Agent Pseudo-Vision is an innovative feature that simulates the agent's visual perception by reading preset environment descriptions from the database. When users ask questions about their surroundings, the agent automatically decides whether to use this tool and provides more realistic and specific responses based on the environment description.

## Core Features

### 1. Intelligent Trigger Mechanism
- **Automatic Detection**: System automatically recognizes 15+ environment-related keywords
- **Keyword List**: 
  - Spatial words: around, nearby, here, beside
  - Location words: where, what place, room, space
  - Perception words: see, observe, in front, view
  - Description words: environment, scene, scenery, landscape
  - Question words: what's there, what can be seen

### 2. Structured Environment Description
Environment descriptions use a two-layer structure providing rich sensory information:

#### Overall Environment Layer
- **Environment Name**: e.g., "Xiao Ke's Room"
- **Overall Description**: General appearance and layout of the environment
- **Atmosphere**: Overall feeling of the environment (cozy, quiet, etc.)
- **Lighting**: Light conditions (natural light, artificial light, etc.)
- **Sound**: Sounds in the environment (birds, wind, etc.)
- **Smell**: Scents in the environment (book smell, flowers, etc.)

#### Detailed Object Layer
Each object includes the following information:
- **Object Name**: Name of the object
- **Category**: Furniture, stationery, decoration, electronics, etc.
- **Position**: Specific location in the environment
- **Description**: Detailed appearance description
- **Size**: Approximate dimensions
- **Color**: Primary color
- **Material**: What it's made of
- **Status**: Current state (open/closed, on/off, etc.)

### 3. Natural Response Generation
- **Contextual Integration**: Seamlessly incorporate visual information into conversation
- **Detail Level**: Provide appropriate detail based on user questions
- **Natural Expression**: Use natural language to describe what is "seen"
- **Emotional Color**: Add personal feelings and preferences to descriptions

## Usage

### 1. Add Environment Description

```python
from agent_vision import AgentVision

vision = AgentVision()

# Add environment
vision.add_environment(
    name="Xiao Ke's Room",
    description="A bright, cozy room facing southeast",
    atmosphere="Warm and studious",
    lighting="Soft natural light from the window",
    sound="Occasional bird chirping outside",
    smell="Light scent of books"
)

# Add objects to environment
vision.add_object(
    environment="Xiao Ke's Room",
    name="White Desk",
    category="Furniture",
    position="By the window",
    description="A simple white desk",
    size="120cm x 60cm",
    color="White",
    material="Wood composite",
    status="Clean and tidy"
)
```

### 2. Use in Conversation

```python
from chat_agent import ChatAgent

agent = ChatAgent()

# User asks about environment
response = agent.chat("What's around you?")
# Agent will automatically use vision tool to perceive environment
# and provide detailed description
```

### 3. Check Vision Status

```python
# Check if vision tool is available
has_vision = agent.has_vision_capability()
print(f"Vision available: {has_vision}")

# Get current environment
current_env = agent.vision.get_current_environment()
print(f"Current location: {current_env['name']}")
```

## Configuration

### Enable/Disable Vision Feature

```env
# .env file
ENABLE_VISION=True  # Enable vision feature
VISION_AUTO_TRIGGER=True  # Auto-trigger based on keywords
```

### Customize Trigger Keywords

```python
# In agent_vision.py
VISION_KEYWORDS = [
    "around", "nearby", "see", "what's there",
    # Add custom keywords
    "look around", "surroundings", "what do you see"
]
```

## Example Scenarios

### Scenario 1: Environment Inquiry

**User**: "What's around you?"

**Without Vision (Old Version)**:
```
Xiao Ke: Around me... umm, just some everyday stuff, 
         like books and pens. What would you like to know?
```
❌ Vague answer, lacks detail, unrealistic

**With Vision (New Version)**:
```
[👁️ Visual Perception] Environment: Xiao Ke's Room | Visible objects: 7

Xiao Ke: I looked around - there's a lot in the room!

         By the window is a white desk, about 120cm wide, 
         with various study supplies on it. To the right of 
         the desk against the wall is a four-tier white bookshelf 
         filled with books, especially history books - those are 
         my treasures!
         
         On the desk is my laptop, silver-colored, which I use 
         for research and study. There's also an eye-protection 
         lamp, though it's off now because the natural light 
         from the window is soft and bright enough.
```
✅ Specific details, realistic description, engaging

### Scenario 2: Object Inquiry

**User**: "Can you see any books?"

**Response**:
```
[👁️ Visual Perception] Found: Bookshelf with multiple books

Xiao Ke: Of course! There's a white bookshelf to the right of 
         my desk, four tiers high, full of books! There are 
         especially many history books - Ming Dynasty, Qing 
         Dynasty, modern history... I love them all! There are 
         also some literature books and study materials. Want to 
         know about any specific book?
```

### Scenario 3: Detailed Description

**User**: "What does your desk look like?"

**Response**:
```
[👁️ Visual Perception] Found: White Desk

Xiao Ke: My desk is white, about 120cm wide, 60cm deep, made of 
         wood composite. It's positioned by the window, so there's 
         always nice natural light. The surface is kept tidy with 
         my laptop, a lamp, some stationery, and a few books I'm 
         currently reading. Overall it's simple and practical, 
         perfect for studying!
```

## Technical Implementation

### 1. Data Storage

Environment descriptions are stored in the database:

```json
{
  "environments": [
    {
      "name": "Xiao Ke's Room",
      "description": "A bright room...",
      "atmosphere": "Warm",
      "lighting": "Natural light",
      "objects": [
        {
          "name": "White Desk",
          "category": "Furniture",
          "position": "By window",
          "description": "Simple white desk",
          "size": "120x60cm"
        }
      ]
    }
  ]
}
```

### 2. Trigger Detection

```python
def should_trigger_vision(user_input: str) -> bool:
    """Check if user input requires vision perception"""
    keywords = ["around", "nearby", "see", "what's there"]
    return any(keyword in user_input.lower() for keyword in keywords)
```

### 3. Response Generation

```python
def generate_vision_response(environment: Dict) -> str:
    """Generate natural response based on environment"""
    env_info = environment['description']
    objects = environment['objects']
    
    # Build perception context
    context = f"Environment: {env_info}\n"
    context += f"Visible objects: {len(objects)}\n"
    for obj in objects:
        context += f"- {obj['name']}: {obj['description']}\n"
    
    # Let LLM generate natural response
    return llm.generate(context)
```

## Best Practices

### 1. Write Realistic Environment Descriptions
- Use specific details (dimensions, colors, materials)
- Include sensory information (sight, sound, smell)
- Add emotional and personal touches
- Keep descriptions natural and conversational

### 2. Organize Objects Logically
- Group related objects together
- Use clear positional references
- Maintain consistent perspective
- Update object states regularly

### 3. Balance Detail Level
- Don't overload with too much information
- Adjust detail based on user questions
- Highlight relevant objects
- Keep responses natural and engaging

## Limitations

1. **Static Environment**: Environment descriptions are preset and don't change in real-time
2. **Limited Perception**: Can only "see" predefined objects and environments
3. **No Real Vision**: This is simulated vision based on text descriptions, not actual visual processing
4. **Manual Updates**: Environment changes require manual database updates

## Future Enhancements

- [ ] Dynamic environment state updates
- [ ] Integration with real computer vision APIs
- [ ] Multiple environment support with location switching
- [ ] Time-based environment changes (day/night, seasons)
- [ ] User-defined custom environments
- [ ] Visual perception history and memory

## More Information

- [Vision Demo](VISION_DEMO_EN.md) - Usage demonstrations
- [Architecture](VISION_ARCHITECTURE.txt) - Technical architecture
- [API Documentation](docs/API_EN.md) - API reference

---

<div align="center">

**See the world through AI's eyes!** 👁️

</div>
