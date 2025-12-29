# Neo Agent - Intelligent Dialogue Agent System

English | [简体中文](README.md)

Neo Agent is an intelligent dialogue agent system based on LangChain, featuring role-playing, long-term memory management, and emotional relationship analysis. Through hierarchical memory architecture and knowledge base management, it delivers an intelligent conversation experience with persistent memory capabilities.

## ✨ Key Features

### 🧠 Hierarchical Memory System
- **Short-term Memory**: Stores detailed content of the last 20 conversation rounds
- **Long-term Memory**: Automatically generates summaries of historical conversations
- **Knowledge Base**: Extracts and persists knowledge from conversations
- **Base Knowledge**: Preset immutable core knowledge

### 💭 Intelligent Conversation
- **Role-playing**: Support for custom character settings and personalities
- **Continuous Dialogue**: Context-aware multi-turn conversations
- **Memory Retrieval**: Intelligent recall of relevant historical memories
- **Emotional Understanding**: Analyzes emotional tendencies in conversations

### 📊 Emotional Relationship Analysis
- **Impression Evaluation**: Generate detailed impressions of users based on character settings
- **Intelligent Scoring**: Provide 0-100 point scores based on positive/negative impression tendencies
- **Visual Display**: Score ring for intuitive emotional relationship status visualization
- **Dynamic Updates**: Real-time emotional impression updates based on the last 15 conversation rounds

### 🖥️ Graphical User Interface
- **Modern Interface**: User-friendly GUI based on Tkinter
- **Real-time Chat**: Smooth chat experience
- **Data Visualization**: Emotion radar chart, timeline display
- **Database Management**: Visual management of all stored data
- **Debug Tools**: Real-time system logs and API call monitoring

### 🗄️ Data Management
- **SQLite Storage**: Unified database management
- **Data Migration**: Automatic migration from JSON to database
- **Backup & Restore**: Complete data import/export
- **Query Optimization**: Efficient data retrieval

### 🔧 Extended Features
- **Pseudo-vision**: Simulates visual perception through environment descriptions
- **Debug Logging**: Detailed system operation logs
- **Flexible Configuration**: Easy setup through environment variables

## 📋 System Requirements

- Python 3.8 or higher
- Supported OS: Windows, Linux, macOS

## 🚀 Quick Start

### 1. Clone the Repository

```bash
git clone https://github.com/HeDaas-Code/Neo_Agent.git
cd Neo_Agent
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure Environment Variables

Copy `example.env` to `.env` and fill in your configuration:

```bash
cp example.env .env
```

Edit the `.env` file with necessary parameters:

```env
# API Configuration
SILICONFLOW_API_KEY=your-api-key-here
SILICONFLOW_API_URL=https://api.siliconflow.cn/v1/chat/completions

# Model Configuration
MODEL_NAME=deepseek-ai/DeepSeek-V3
TEMPERATURE=0.8
MAX_TOKENS=2000

# Character Settings
CHARACTER_NAME=Xiao Ke
CHARACTER_GENDER=Female
CHARACTER_AGE=18
CHARACTER_ROLE=Student
CHARACTER_PERSONALITY=Lively and cheerful
```

### 4. Run the Application

```bash
python gui_enhanced.py
```

## 📖 Documentation

> 📚 **[Complete Documentation Index](docs/INDEX.md)** - View structured directory of all documentation

### Core Documentation

- [Quick Start Guide](docs/en/QUICKSTART.md) - Detailed installation and usage instructions
- [Development Guide](docs/en/DEVELOPMENT.md) - Project structure and development guide
- [API Documentation](docs/en/API.md) - Detailed API interface documentation
- [Architecture Design](docs/en/ARCHITECTURE.md) - System architecture and design principles

### More Documentation

All documentation has been organized in the [docs](docs/) folder with bilingual support (Chinese and English).

## 🏗️ Project Structure

```
Neo_Agent/
├── gui_enhanced.py           # Main GUI interface
├── chat_agent.py            # Dialogue agent core
├── database_manager.py      # Database management
├── long_term_memory.py      # Long-term memory management
├── knowledge_base.py        # Knowledge base management
├── emotion_analyzer.py      # Emotional analysis
├── agent_vision.py          # Vision tools
├── debug_logger.py          # Debug logging
├── database_gui.py          # Database GUI management
├── base_knowledge.py        # Base knowledge management
├── requirements.txt         # Project dependencies
├── example.env             # Environment variable example
└── README.md               # Project documentation
```

## 🎯 Use Cases

- **Personal Assistant**: AI assistant with memory capabilities
- **Role-playing**: Create conversational characters with specific personas
- **Customer Service**: Intelligent customer service that remembers user history
- **Learning Companion**: Learning assistant that accumulates knowledge
- **Emotional Support**: Companion bot that understands and responds to emotions

## ⚙️ Core Configuration

### Character Settings
Configure character basics through the `.env` file:
- `CHARACTER_NAME`: Character name
- `CHARACTER_GENDER`: Gender
- `CHARACTER_AGE`: Age
- `CHARACTER_ROLE`: Role positioning
- `CHARACTER_PERSONALITY`: Personality traits
- `CHARACTER_HOBBY`: Hobbies and specialties
- `CHARACTER_BACKGROUND`: Detailed background description

### Memory Settings
- `MAX_MEMORY_MESSAGES`: Maximum memory messages (default 50)
- `MAX_SHORT_TERM_ROUNDS`: Short-term memory rounds (default 20)

### Model Settings
- `MODEL_NAME`: LLM model to use
- `TEMPERATURE`: Generation temperature (0-1)
- `MAX_TOKENS`: Maximum generation length

## 🔍 Feature Showcase

### Chat Interface
- Real-time conversation support
- Historical message display
- Automatic conversation logging

### Emotional Analysis
- Click "Analyze Emotional Relationship" button
- View impression score and detailed impression description
- Understand current emotional state and relationship type

### Database Management
- View all memory data
- Manage knowledge base content
- Import/export data

## 🛠️ Development

### Debug Mode
Enable debug mode to view detailed logs:

```env
DEBUG_MODE=True
DEBUG_LOG_FILE=debug.log
```

### Extension Development
1. Check [Development Guide](DEVELOPMENT_EN.md) for project structure
2. Refer to [API Documentation](API_EN.md) for interface definitions
3. Read [Architecture Design](ARCHITECTURE_EN.md) for system design

## 🤝 Contributing

Contributions, issues, and feature requests are welcome!

1. Fork this repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [LangChain](https://github.com/langchain-ai/langchain) - Powerful LLM application framework
- [SiliconFlow](https://siliconflow.cn/) - API service provider
- All contributors and supporters

## 📧 Contact

For questions or suggestions, please contact us through:

- Submit an [Issue](https://github.com/HeDaas-Code/Neo_Agent/issues)
- Start a [Discussion](https://github.com/HeDaas-Code/Neo_Agent/discussions)

## 🌟 Star History

If this project helps you, please give it a ⭐️!

---

Powered by ❤️, Built for Intelligent Conversation
