# Quick Start Guide

English | [简体中文](QUICKSTART.md)

This guide will help you get started with the Neo Agent intelligent dialogue system quickly.

## 📋 Prerequisites

Before you begin, ensure your system meets the following requirements:

- **Python**: 3.8 or higher
- **pip**: Python package manager
- **Operating System**: Windows, Linux, or macOS
- **Internet Connection**: Required for API access

### Check Python Version

```bash
python --version
# or
python3 --version
```

If the version is below 3.8, please upgrade Python first.

## 🔧 Installation Steps

### 1. Get the Code

#### Option 1: Clone with Git

```bash
git clone https://github.com/HeDaas-Code/Neo_Agent.git
cd Neo_Agent
```

#### Option 2: Download ZIP

1. Visit the [project homepage](https://github.com/HeDaas-Code/Neo_Agent)
2. Click "Code" -> "Download ZIP"
3. Extract to your preferred directory
4. Navigate to the project directory

### 2. Create Virtual Environment (Recommended)

Using a virtual environment helps avoid dependency conflicts:

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

Dependencies list:
- `langchain>=0.1.0` - LLM application framework
- `langchain-community>=0.0.10` - LangChain community components
- `langchain-core>=0.1.0` - LangChain core library
- `python-dotenv>=1.0.0` - Environment variable management
- `requests>=2.31.0` - HTTP request library

### 4. Configure Environment Variables

#### Copy Configuration Template

```bash
cp example.env .env
```

#### Edit .env File

Open the `.env` file with a text editor and fill in the necessary configuration:

```env
# ========== API Configuration ==========
# Required: Your API key
SILICONFLOW_API_KEY=your-api-key-here

# API service URL (usually no need to modify)
SILICONFLOW_API_URL=https://api.siliconflow.cn/v1/chat/completions

# ========== Model Configuration ==========
# LLM model name
MODEL_NAME=deepseek-ai/DeepSeek-V3

# Generation temperature (0-1), higher is more creative
TEMPERATURE=0.8

# Maximum generation tokens
MAX_TOKENS=2000

# ========== Character Settings ==========
# Character name
CHARACTER_NAME=Xiao Ke

# Gender
CHARACTER_GENDER=Female

# Age
CHARACTER_AGE=18

# Role
CHARACTER_ROLE=Student

# Physical attributes
CHARACTER_HEIGHT=150cm
CHARACTER_WEIGHT=45kg

# Personality
CHARACTER_PERSONALITY=Lively and cheerful

# Hobbies
CHARACTER_HOBBY=Liberal arts, especially passionate about history

# Detailed background
CHARACTER_BACKGROUND=I am a high school student named Xiao Ke. I am 150cm tall and weigh 45kg. I have a lively and cheerful personality and love liberal arts, especially history. I enjoy reading history books and often get inspired by historical stories. I speak in a playful and cute manner and like to share interesting historical knowledge with friends.

# ========== Memory Settings ==========
# Memory file paths (kept for compatibility with old JSON system)
MEMORY_FILE=memory_data.json
LONG_MEMORY_FILE=longmemory_data.json

# Maximum memory messages
MAX_MEMORY_MESSAGES=50

# Maximum short-term memory rounds
MAX_SHORT_TERM_ROUNDS=20

# ========== Debug Settings ==========
# Enable debug mode
DEBUG_MODE=True

# Debug log file
DEBUG_LOG_FILE=debug.log
```

### 5. Get API Key

#### SiliconFlow API

1. Visit [SiliconFlow](https://siliconflow.cn/)
2. Register and log in
3. Go to console and create an API key
4. Copy the key and paste it into `SILICONFLOW_API_KEY` in `.env`

#### Other API Providers

If using other API providers (like OpenAI, Azure OpenAI, etc.):
1. Modify `SILICONFLOW_API_URL` to the corresponding API address
2. Adjust `MODEL_NAME` to the corresponding model name
3. May need to modify API call format in the code

## 🚀 Running the Application

### Start the GUI

```bash
python gui_enhanced.py
```

On first run, the system will:
1. Initialize SQLite database
2. Create necessary tables
3. Check and migrate old JSON data (if exists)

### Using the Interface

#### Main Interface Features

1. **Chat Area**: Displays conversation history
2. **Input Box**: Enter your messages
3. **Send Button**: Send message (or press Enter)
4. **Clear Memory**: Clear all conversation history
5. **Analyze Emotion**: Generate emotional relationship radar chart
6. **Database Management**: Open database management interface
7. **Debug Log**: View system operation logs

#### Start Chatting

1. Type a message in the input box
2. Press Enter or click the "Send" button
3. Wait for AI response
4. Continue the conversation...

#### View Emotional Analysis

1. After a few conversation rounds
2. Click the "Analyze Emotional Relationship" button
3. View the five-dimensional radar chart on the right
4. Understand the current emotional relationship state

#### Manage Database

1. Click the "Database Management" button
2. In the new window, view and manage:
   - Short-term memory
   - Long-term memory
   - Knowledge base
   - Base knowledge
   - Environment descriptions
3. Add, edit, delete data
4. Support import/export backup

## 🎯 Usage Tips

### Customize Character

Modify character settings in the `.env` file:

```env
CHARACTER_NAME=John
CHARACTER_GENDER=Male
CHARACTER_AGE=25
CHARACTER_ROLE=Programmer
CHARACTER_PERSONALITY=Calm and rational, good at analyzing problems
CHARACTER_HOBBY=Programming, reading, thinking
CHARACTER_BACKGROUND=I am a software engineer who loves technology and excels at solving complex problems...
```

Restart the application after modification.

### Adjust Memory Capacity

Adjust memory system capacity based on needs:

```env
# Keep 30 rounds of short-term memory
MAX_SHORT_TERM_ROUNDS=30

# Maximum 100 memory messages
MAX_MEMORY_MESSAGES=100
```

### Switch Models

Try different LLM models:

```env
# Use Qwen model
MODEL_NAME=Qwen/Qwen2.5-7B-Instruct

# Use DeepSeek model
MODEL_NAME=deepseek-ai/DeepSeek-V3
```

### Adjust Generation Parameters

Control AI response style:

```env
# More creative (0.8-1.0)
TEMPERATURE=0.9

# More stable and conservative (0.3-0.5)
TEMPERATURE=0.4

# Longer responses
MAX_TOKENS=3000

# More concise responses
MAX_TOKENS=1000
```

## 🐛 Troubleshooting

### Issue: Cannot Start Application

**Possible Causes**:
- Python version too old
- Dependencies not fully installed

**Solutions**:
```bash
# Check Python version
python --version

# Reinstall dependencies
pip install -r requirements.txt --upgrade
```

### Issue: API Call Failure

**Possible Causes**:
- Invalid API key
- Network connection issues
- API service problems

**Solutions**:
1. Check if `SILICONFLOW_API_KEY` in `.env` is correct
2. Test network connection
3. Check Debug log for detailed errors

### Issue: Database Error

**Possible Causes**:
- Database file corrupted
- Permission issues

**Solutions**:
```bash
# Delete database and reinitialize
rm chat_agent.db
python gui_enhanced.py
```

### Issue: Interface Display Problems

**Possible Causes**:
- Tkinter not properly installed
- System missing required libraries

**Solutions**:
```bash
# Ubuntu/Debian
sudo apt-get install python3-tk

# macOS
brew install python-tk

# Windows usually comes with Tkinter
```

## 📚 Next Steps

- Read [Development Guide](DEVELOPMENT_EN.md) to understand project structure
- Check [API Documentation](API_EN.md) to learn interface calls
- Explore [Architecture Design](ARCHITECTURE_EN.md) to understand system principles

## 💡 FAQ

### Q: Can it be used offline?

A: No. The system requires online LLM API service calls.

### Q: Which LLM models are supported?

A: Theoretically supports all model services compatible with OpenAI API format.

### Q: Where is data stored?

A: All data is stored in local SQLite database `chat_agent.db`.

### Q: Can multiple instances run simultaneously?

A: Yes, but different database file paths are needed.

### Q: How to backup data?

A: Directly copy the `chat_agent.db` file, or use the export function in database management interface.

## 🆘 Getting Help

If you encounter problems:

1. Check the troubleshooting section in this guide
2. Browse [Issues](https://github.com/HeDaas-Code/Neo_Agent/issues)
3. Submit a new Issue describing the problem
4. Join community discussions

---

Enjoy using Neo Agent! 🎉
