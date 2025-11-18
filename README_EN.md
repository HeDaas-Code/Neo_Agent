# Intelligent Dialogue Agent System v5.0

[中文](README.md) | **English**

An intelligent dialogue agent system based on LangChain and Python, supporting role-playing, three-layer memory management (short-term + long-term + knowledge base), base knowledge, emotional relationship analysis, and debug log tracking.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)

## 📚 Documentation Navigation

- **[Quick Start](#installation-steps)** - Get started in 5 minutes
- **[Contributing Guide](CONTRIBUTING_EN.md)** - How to participate in project development
- **[Changelog](CHANGELOG_EN.md)** - Version history and change log
- **[API Documentation](docs/API_EN.md)** - Complete API reference manual
- **[Deployment Guide](docs/DEPLOYMENT_EN.md)** - Local, production, and cloud deployment
- **[Development Guide](docs/DEVELOPMENT_EN.md)** - In-depth developer guide
- **[Usage Examples](docs/EXAMPLES_EN.md)** - Rich code examples
- **[Troubleshooting](docs/TROUBLESHOOTING_EN.md)** - Common problem solutions

## Features

### 🎭 Role-Playing
- Read character settings from .env file
- Support custom character personality, background, hobbies, etc.
- Default character: Student Xiao Ke (lively and cheerful, loves history)

### 🧠 Three-Layer Memory System
- **Short-term Memory**: Saves the last 20 rounds of detailed conversation (memory_data)
- **Long-term Memory**: Conversations beyond 20 rounds are automatically archived as summarized memories (longmemory_data)
- **Knowledge Base**: Automatically extract knowledge points every 5 rounds (knowledge_base)
- **Intelligent Summarization**: Use LLM to automatically generate topic summaries and knowledge extraction
- **UUID Identification**: Each long-term memory and knowledge has a unique identifier

### 📚 Knowledge Base System (v3.0)
- **Automatic Extraction**: Automatically analyze and extract user information every 5 rounds
- **Structured Storage**: Each knowledge item contains title, content, type, source, tags, etc.
- **Knowledge Classification**: Automatically categorized as personal information, preferences, facts, experiences, opinions, etc.
- **Search Function**: Support keyword search and type filtering
- **UUID Tracking**: Each knowledge item has a unique UUID for easy management
- **Time Tracking**: Record the time range of knowledge sources

### 🔒 Base Knowledge System (v4.0)
- **Highest Priority**: 100% priority, absolutely accurate core knowledge
- **Immutable**: Once added, will not be overwritten or modified
- **Mandatory Compliance**: Must follow base knowledge even if it contradicts AI common sense
- **Case Insensitive**: Support matching queries in various case formats
- **Independent Storage**: Separate base_knowledge file management
- **GUI Management**: View and add base knowledge through the interface
- **Default Knowledge**: Pre-configured "HeDaas is a university"

### 🔧 Debug System (v4.0)
- **Complete Log Tracking**: Record module operations, prompts, API requests/responses
- **Real-time Monitoring**: Display log stream in real-time in GUI
- **Type Filtering**: Support filtering by type (module/prompt/request/response/error/info)
- **Color Highlighting**: Different log types use different colors
- **Performance Analysis**: Record API response time and processing duration
- **Problem Troubleshooting**: Quickly locate problems and view complete execution flow
- **Optional Toggle**: Enable/disable via DEBUG_MODE configuration
- **Emotion Analysis Logging**: Record automatic triggers, analysis processes, tone adjustments, etc.

### 💖 Emotional Relationship Analysis System (v5.0)
- **Automatic Analysis**: Automatically perform emotional relationship analysis every 10 rounds
- **Multi-dimensional Assessment**: Evaluate emotional relationships from 5 dimensions (intimacy, trust, pleasure, resonance, dependence)
- **Relationship Type**: Automatically identify relationship types (acquaintance, friend, close friend, etc.)
- **Emotional Tone**: Analyze overall emotional tone (positive, neutral, negative)
- **Radar Chart Visualization**: Intuitively display scores of 5 emotional dimensions
- **Adaptive Tone**: AI automatically adjusts conversation tone and attitude based on emotional state
- **Persistent Storage**: Emotional data saved to emotion_data, supporting historical tracking
- **Tab Switching**: Timeline and radar chart share visualization area, switch via tabs
- **Manual Analysis**: Support manual trigger for emotional analysis at any time
- **System Notification**: Display result summary in chat window after analysis completion

### 📊 Visualization Interface
- **Topic Timeline**: Graphically display the trajectory of chat topic changes
- **Emotional Relationship Radar Chart**: Pentagon radar chart showing 5 emotional dimensions (NEW!)
- **Tab Switching**: Timeline and radar chart share the same area, click to switch (NEW!)
- **Knowledge Base Panel**: Display all knowledge points in a structured way
- **Click Interaction**: Click timeline nodes to view detailed summary information
- **Real-time Update**: Automatically update interface when memory is archived, knowledge is extracted, and emotional analysis is performed
- **Multiple Tabs**: System information, short-term memory, long-term memory, understanding stage, knowledge base, environment management, debug log, control panel

### 👁️ Agent Pseudo-Vision System (v6.0 NEW!)
- **Environment Perception**: Simulate agent's visual capabilities through database presets
- **Smart Trigger**: Automatically recognize 15+ environment-related keywords (around, see, observe, etc.)
- **Structured Description**: Two-layer environment description (overall environment + detailed objects)
- **Multi-sensory Information**: Includes visual, auditory, olfactory and other multi-dimensional perception
- **Object Management**: Support adding, editing, deleting objects in environment
- **Priority System**: Adjust display order based on object importance
- **Visibility Control**: Flexible control of object visibility to agent
- **Usage Records**: Automatically record vision tool usage history
- **Detailed Documentation**: See [Pseudo-Vision Feature Documentation](VISION_FEATURE_README_EN.md)

### 🌐 Environment Switching System (v6.0 NEW!)
- **Smart Environment Management**: Support creating and managing multiple environments
- **Environment Connection System**: Record connection relationships between environments through UUID
- **Smart Switch Detection**: Automatically detect user's environment switching intent
- **Permission Verification**: Only allow switching to connected environments
- **Visualization Management**: Graphically display environment relationships
- **GUI Enhancement**: Optimized environment management interface with hierarchical object addition
- **Connection Types**: Support multiple connection types such as doors, stairs, corridors, etc.
- **Direction Control**: Support one-way and bidirectional connections
- **Detailed Documentation**: See [Environment Switching Feature Documentation](ENVIRONMENT_SWITCHING_EN.md)

## Project Structure

```
Neo_Agent/
├── .env                       # Configuration file (API key, character settings, debug mode, etc.)
├── example.env                # Configuration file template
├── requirements.txt           # Python dependencies
├── LICENSE                    # MIT license
├── README.md                  # Main project documentation (Chinese)
├── README_EN.md               # Main project documentation (English)
├── CONTRIBUTING.md            # Contributing guide (Chinese)
├── CONTRIBUTING_EN.md         # Contributing guide (English)
├── CHANGELOG.md               # Changelog (Chinese)
├── CHANGELOG_EN.md            # Changelog (English)
├── ENVIRONMENT_SWITCHING.md   # Environment switching documentation (Chinese)
├── ENVIRONMENT_SWITCHING_EN.md # Environment switching documentation (English)
├── VISION_FEATURE_README.md   # Pseudo-vision feature documentation (Chinese)
├── VISION_FEATURE_README_EN.md # Pseudo-vision feature documentation (English)
├── VISION_DEMO.md             # Vision feature demo (Chinese)
├── VISION_DEMO_EN.md          # Vision feature demo (English)
├── VISION_ARCHITECTURE.txt    # Vision system architecture description
│
├── chat_agent.py              # Chat agent core module
├── long_term_memory.py        # Long-term memory management module
├── knowledge_base.py          # Knowledge base management module
├── base_knowledge.py          # Base knowledge base module
├── emotion_analyzer.py        # Emotional relationship analysis module
├── agent_vision.py            # Agent pseudo-vision module (NEW!)
├── database_gui.py            # Database GUI interface module
├── database_manager.py        # Database management module
├── debug_logger.py            # Debug log manager
├── gui_enhanced.py            # Enhanced GUI interface (recommended)
├── test_environment_switching.py # Environment switching feature test
│
├── chat_agent.db              # Database file (auto-generated)
├── debug.log                  # Debug log file (auto-generated)
│
└── docs/                      # Detailed documentation directory
    ├── README.md              # Documentation center (Chinese)
    ├── README_EN.md           # Documentation center (English)
    ├── API.md                 # API reference documentation (Chinese)
    ├── API_EN.md              # API reference documentation (English)
    ├── DEPLOYMENT.md          # Deployment guide (Chinese)
    ├── DEPLOYMENT_EN.md       # Deployment guide (English)
    ├── DEVELOPMENT.md         # Developer guide (Chinese)
    ├── DEVELOPMENT_EN.md      # Developer guide (English)
    ├── EXAMPLES.md            # Usage examples (Chinese)
    ├── EXAMPLES_EN.md         # Usage examples (English)
    ├── TROUBLESHOOTING.md     # Troubleshooting guide (Chinese)
    └── TROUBLESHOOTING_EN.md  # Troubleshooting guide (English)
```

## Installation Steps

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure API Key

Edit the `.env` file and set your SiliconFlow API key:

```env
SILICONFLOW_API_KEY=your_api_key_here
```

### 3. Customize Character (Optional)

Modify character settings in the `.env` file:

```env
# API Configuration
SILICONFLOW_API_KEY=your_api_key_here
SILICONFLOW_API_URL=https://api.siliconflow.cn/v1/chat/completions
MODEL_NAME=Qwen/Qwen2.5-7B-Instruct
TEMPERATURE=0.8
MAX_TOKENS=2000

# Character Settings
CHARACTER_NAME=Xiao Ke
CHARACTER_GENDER=Female
CHARACTER_ROLE=Student
CHARACTER_AGE=18
CHARACTER_PERSONALITY=Lively and cheerful
CHARACTER_HOBBY=Liberal arts, especially passionate about history
CHARACTER_BACKGROUND=I'm a high school student named Xiao Ke...

# Memory Settings
MEMORY_FILE=memory_data.json
LONG_MEMORY_FILE=longmemory_data.json
MAX_MEMORY_MESSAGES=50
MAX_SHORT_TERM_ROUNDS=20

# Debug Mode (NEW!)
DEBUG_MODE=True
DEBUG_LOG_FILE=debug.log
```

## Usage

### Start Enhanced GUI (Recommended)

```bash
python gui_enhanced.py
```

### Command Line Mode

```bash
python chat_agent.py
```

## Memory System Explained

### Short-term Memory (memory_data)

```json
{
  "messages": [
    {
      "role": "user",
      "content": "Hello",
      "timestamp": "2025-11-14T20:44:10.942693"
    },
    {
      "role": "assistant",
      "content": "Hello! I'm Xiao Ke...",
      "timestamp": "2025-11-14T20:44:11.855484"
    }
  ],
  "metadata": {
    "created_at": "2025-11-14T20:43:56.635027",
    "total_conversations": 3
  }
}
```

**Features**:
- Save the last 20 rounds of conversation (40 messages)
- Contains complete conversation content and timestamps
- Automatically triggers archiving after 20 rounds

### Long-term Memory (longmemory_data)

```json
{
  "summaries": [
    {
      "uuid": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
      "created_at": "2025-11-14T10:00:00.000000",
      "ended_at": "2025-11-14T10:30:00.000000",
      "rounds": 20,
      "message_count": 40,
      "summary": "Discussed Chinese ancient history, focusing on Tang Dynasty culture and imperial examination system..."
    }
  ],
  "metadata": {
    "created_at": "2025-11-14T10:00:00.000000",
    "total_summaries": 1
  }
}
```

**Features**:
- Generate a summary for every 20 rounds of conversation
- Use UUID for unique identification
- Record time range and conversation rounds
- LLM automatically generates topic summaries

## Emotional Relationship Analysis System Details (v5.0 NEW!)

### What is Emotional Relationship Analysis?

The emotional relationship analysis system intelligently analyzes conversations between users and AI through LLM, evaluates emotional relationship status from multiple dimensions, and automatically adjusts AI's conversation tone and attitude based on analysis results, making communication more natural and considerate.

### Core Features

#### 1. Automatic Emotional Analysis
- **Trigger Mechanism**: Automatically perform analysis every 10 rounds of conversation
- **Analysis Window**: Based on the last 10 rounds of conversation (20 messages)
- **Smart Deduplication**: Avoid repeated analysis of the same round
- **Background Execution**: Does not affect normal conversation flow
- **Real-time Feedback**: Display brief results in chat window after analysis

#### 2. Multi-dimensional Assessment

The system comprehensively evaluates emotional relationships from 5 dimensions, each scored 0-100:

| Dimension | Description | Impact |
|-----------|-------------|--------|
| **Intimacy** | Degree of relationship closeness | Determines the level of intimacy in communication |
| **Trust** | User's trust level in AI | Affects the depth and honesty of advice |
| **Pleasure** | Pleasure in conversation | Determines the liveliness of tone |
| **Resonance** | Emotional and topic resonance | Affects the depth of topic exploration |
| **Dependence** | User's dependence on AI | Determines the strength of support and help |

#### 3. Relationship Type Recognition

Automatically identify relationship types based on overall scores:

| Score | Relationship Type | AI Tone Characteristics |
|-------|-------------------|-------------------------|
| 0-30 | Acquaintance/Stranger | Polite and friendly, maintain appropriate distance |
| 31-50 | Friend | Friendly and natural, moderate sharing |
| 51-70 | Good Friend | Kind and enthusiastic, more interaction |
| 71-85 | Close Friend | Intimate and comfortable, deep communication |
| 86-100 | Soulmate | Complete trust, talk about everything |

## Keyboard Shortcuts

- **Enter**: Send message
- **Ctrl+Enter**: Line break in input box

## Development Information

- **Version**: v5.0
- **Development Time**: November 2025
- **Tech Stack**: Python 3.12+, Tkinter, LangChain, SiliconFlow API
- **License**: MIT

## Common Questions

### Memory System Related

#### Q: Why is long-term memory not generated?
**A**: Long-term memory is automatically generated only when the conversation exceeds 20 rounds. Please ensure you have had at least 21 rounds of conversation. The system will automatically archive the first 20 rounds as a topic summary after the 20th round.

#### Q: How to modify the archiving rounds?
**A**: Modify the `MAX_SHORT_TERM_ROUNDS` parameter in the `.env` file (default 20). For example:
```env
MAX_SHORT_TERM_ROUNDS=30  # Change to archive every 30 rounds
```

### Emotional Analysis Related ⭐NEW

#### Q: When is emotional analysis triggered?
**A**: 
- **Automatic Trigger**: Automatically analyze once every 10 rounds of conversation (rounds 10, 20, 30...)
- **Manual Trigger**: Click the "🔍 Analyze Emotional Relationship" button
- **Minimum Rounds**: At least 1 round of conversation (2 messages) is required for analysis

#### Q: Are emotional analysis results accurate?
**A**: Accuracy depends on:
1. **Conversation Quality**: The richer the conversation content, the more accurate the analysis
2. **Conversation Rounds**: Based on 10 rounds of conversation, the more samples the better
3. **LLM Model**: Stronger models have better understanding capabilities
4. **Expression Clarity**: Clear emotional expression helps analysis

## Version History

### v5.0 (2025-01-15) - Emotional Relationship Analysis Version ⭐NEW
- ✅ Added emotional relationship analysis system
- ✅ Automatic emotional analysis (triggered every 10 rounds)
- ✅ 5-dimensional emotional assessment (intimacy, trust, pleasure, resonance, dependence)
- ✅ Relationship type recognition and emotional tone analysis
- ✅ Emotional radar chart visualization (pentagon)
- ✅ AI tone adaptation (adjust based on emotional state)
- ✅ Emotional data persistence (emotion_data)
- ✅ Timeline and radar chart tab switching
- ✅ GUI automatic refresh emotional display
- ✅ Complete debug log support
- 🎨 Optimized visualization area layout

### v4.0 (2025-11-15) - Debug and Base Knowledge Version
- ✨ Added base knowledge system (100% priority, immutable)
- ✨ Added debug log tracking system
- ✨ GUI added debug log tab (real-time monitoring)
- ✨ Base knowledge management function (view/add)
- 🔧 Fixed base knowledge not being retrieved
- 🔧 Implemented case-insensitive entity matching
- 🎨 Optimized knowledge base display, distinguish base knowledge and regular knowledge
- 🎨 Knowledge context building optimization, clearly marked priority
- 📝 Added complete debug log tracking

### v3.0 (2025-11-14) - Knowledge Base Version
- ✨ Added knowledge base system
- ✨ Automatic knowledge extraction function (every 5 rounds)
- ✨ Knowledge classification and tag system
- ✨ Knowledge base search and filtering function
- ✨ Knowledge base visualization panel
- 🎨 Optimized GUI layout, fixed input box at bottom
- 🎨 Added knowledge extraction notification message

### v2.0 (2025-11-14) - Enhanced Version
- ✨ Added layered memory system (short-term + long-term)
- ✨ Added topic timeline visualization
- ✨ Added automatic summary generation function
- ✨ Added UUID identification system
- 🎨 Optimized GUI interface layout
- 📝 Improved Chinese comments

### v1.0
- Basic conversation function
- Role-playing
- Simple memory system
- Basic GUI interface

---

## 📖 More Documentation

Want to learn more about Neo_Agent? Check out our detailed documentation:

### Getting Started
- 📘 **[Quick Start](#installation-steps)** - 5-minute quick start guide
- 📙 **[Usage Examples](docs/EXAMPLES_EN.md)** - Rich practical application scenarios and code examples
- 📗 **[Troubleshooting](docs/TROUBLESHOOTING_EN.md)** - Having problems? Here are solutions

### Developer Documentation
- 📕 **[API Reference](docs/API_EN.md)** - Complete API interface documentation
- 📔 **[Development Guide](docs/DEVELOPMENT_EN.md)** - In-depth understanding of project architecture and development process
- 📓 **[Contributing Guide](CONTRIBUTING_EN.md)** - How to contribute to the project

### Deployment and Operations
- 📒 **[Deployment Guide](docs/DEPLOYMENT_EN.md)** - Local, production, Docker, cloud deployment
- 📃 **[Changelog](CHANGELOG_EN.md)** - Version history and update records

## 🤝 Contributing

We welcome all forms of contribution! Whether it's:

- 🐛 Reporting bugs
- 💡 Suggesting new features
- 📝 Improving documentation
- 🔧 Submitting code fixes
- ⭐ Starring this project

Please read our [Contributing Guide](CONTRIBUTING_EN.md) for details.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

Thanks to all developers and users who contributed to this project!

---

<div align="center">

**If this project helps you, please give it a ⭐ Star!**

Made with ❤️ by [HeDaas-Code](https://github.com/HeDaas-Code)

</div>
