# Troubleshooting Guide

[中文](TROUBLESHOOTING.md) | **English**

This document helps you quickly diagnose and solve common problems when using Neo_Agent.

## Table of Contents

- [Installation and Startup Issues](#installation-and-startup-issues)
- [API Related Issues](#api-related-issues)
- [Memory System Issues](#memory-system-issues)
- [Knowledge Base Issues](#knowledge-base-issues)
- [Emotional Analysis Issues](#emotional-analysis-issues)
- [GUI Issues](#gui-issues)
- [Performance Issues](#performance-issues)
- [Data Issues](#data-issues)

---

## Installation and Startup Issues

### Issue 1: Incompatible Python Version

**Symptoms**:
```
SyntaxError: invalid syntax
```

**Cause**: Python version too old (below 3.8)

**Solution**:
```bash
# Check Python version
python --version

# Upgrade Python (Ubuntu/Debian)
sudo apt update
sudo apt install python3.12

# macOS (using Homebrew)
brew install python@3.12

# Windows: Download and install from official website
```

### Issue 2: Dependency Installation Failed

**Symptoms**:
```
ERROR: Could not find a version that satisfies the requirement
```

**Solutions**:

```bash
# Solution 1: Upgrade pip
pip install --upgrade pip

# Solution 2: Use mirror (for China)
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# Solution 3: Install dependencies one by one
pip install langchain
pip install langchain-community
pip install langchain-core
pip install python-dotenv
pip install requests
```

### Issue 3: "No module named 'xxx'" Error on Startup

**Symptoms**:
```
ModuleNotFoundError: No module named 'langchain'
```

**Cause**: Virtual environment not activated or dependencies not installed

**Solution**:
```bash
# Activate virtual environment
# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate

# Then install dependencies
pip install -r requirements.txt
```

### Issue 4: .env File Not Found

**Symptoms**:
```
Error: .env file not found or API key not configured
```

**Solution**:
```bash
# Copy template
cp example.env .env

# Edit .env file
nano .env  # or use any text editor

# Add your API key
SILICONFLOW_API_KEY=your_api_key_here
```

---

## API Related Issues

### Issue 5: API Call Failed

**Symptoms**:
```
Error: API request failed with status code 401
```

**Possible Causes**:
1. Invalid API key
2. Insufficient API quota
3. Network connection issue

**Solutions**:

```python
# 1. Verify API key
# Check if .env file contains correct API key
SILICONFLOW_API_KEY=sk-xxxxxxxxxxxx

# 2. Test network connection
import requests
response = requests.get("https://api.siliconflow.cn")
print(response.status_code)

# 3. Check API quota
# Login to SiliconFlow console to check remaining quota

# 4. Enable DEBUG mode to view detailed error
# In .env:
DEBUG_MODE=True
```

### Issue 6: Slow API Response

**Symptoms**: Each response takes more than 10 seconds

**Solutions**:

```env
# 1. Use smaller model
MODEL_NAME=Qwen/Qwen2.5-7B-Instruct

# 2. Reduce response length
MAX_TOKENS=1000

# 3. Lower temperature (faster but less creative)
TEMPERATURE=0.5

# 4. Check network latency
ping api.siliconflow.cn
```

### Issue 7: API Rate Limit Exceeded

**Symptoms**:
```
Error: Rate limit exceeded
```

**Solutions**:
- Reduce request frequency
- Upgrade API plan
- Add retry logic with exponential backoff:

```python
import time

def chat_with_retry(agent, message, max_retries=3):
    for attempt in range(max_retries):
        try:
            return agent.chat(message)
        except Exception as e:
            if "rate limit" in str(e).lower():
                wait_time = 2 ** attempt  # Exponential backoff
                print(f"Rate limited, waiting {wait_time}s...")
                time.sleep(wait_time)
            else:
                raise
    raise Exception("Max retries exceeded")
```

---

## Memory System Issues

### Issue 8: Long-term Memory Not Generated

**Symptoms**: After more than 20 rounds, no long-term memory created

**Debugging Steps**:

```python
from chat_agent import ChatAgent

agent = ChatAgent()

# Check current rounds
print(f"Current rounds: {agent.current_rounds}")

# Check short-term memory
memory = agent.get_memory()
print(f"Messages in memory: {len(memory)}")

# Manually trigger archiving (for testing)
if len(memory) >= 40:  # 20 rounds = 40 messages
    agent._archive_to_long_memory()
```

**Solution**:
1. Ensure you've had at least 21 rounds of conversation
2. Check if archiving is triggered correctly
3. Enable DEBUG mode to view archiving process

### Issue 9: Memory Data Lost

**Symptoms**: Previous conversations disappeared after restart

**Cause**: Database file corrupted or deleted

**Solution**:

```bash
# 1. Check if database file exists
ls chat_agent.db

# 2. Restore from backup (if available)
cp chat_agent.db.backup chat_agent.db

# 3. If no backup, system will create new database
# Previous data cannot be recovered

# 4. Enable automatic backup
# Add to your code:
import shutil
from datetime import datetime

def backup_database():
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    shutil.copy2("chat_agent.db", f"backup/chat_agent_{timestamp}.db")
```

---

## Knowledge Base Issues

### Issue 10: Knowledge Not Extracted

**Symptoms**: After 5 rounds of conversation, no knowledge extracted

**Debugging**:

```python
from chat_agent import ChatAgent

agent = ChatAgent()

# Check extraction conditions
print(f"Current rounds: {agent.current_rounds}")
print(f"Should extract: {agent.current_rounds % 5 == 0}")

# Manually trigger extraction
agent._extract_knowledge()

# Check extracted knowledge
knowledge = agent.knowledge_base.get_all_knowledge()
print(f"Total knowledge: {len(knowledge)}")
```

**Solutions**:
1. Provide clear personal information in conversations
2. Use explicit statements like "I like...", "I am..."
3. Enable DEBUG mode to view extraction process
4. Check if LLM model supports knowledge extraction

### Issue 11: Base Knowledge Not Working

**Symptoms**: AI doesn't follow base knowledge settings

**Debugging with DEBUG mode**:

```env
# Enable DEBUG in .env
DEBUG_MODE=True
```

Then check logs for:
1. Entity extraction: Is entity correctly identified?
2. Knowledge retrieval: Is base knowledge found?
3. Context building: Is base knowledge included in prompt?

**Solution**:

```python
from base_knowledge import BaseKnowledge
from chat_agent import ChatAgent

# Verify base knowledge exists
base_kb = BaseKnowledge()
results = base_kb.search("HeDaas")
print(f"Found {len(results)} base knowledge items")

# Test in conversation
agent = ChatAgent()
response = agent.chat("What is HeDaas?")
print(response)
# Should use base knowledge: "HeDaas is a university"
```

---

## Emotional Analysis Issues

### Issue 12: Emotional Analysis Not Triggered

**Symptoms**: After 10 rounds, no emotional analysis

**Debugging**:

```python
from chat_agent import ChatAgent

agent = ChatAgent()

# Check trigger condition
print(f"Current rounds: {agent.current_rounds}")
print(f"Should analyze: {agent.current_rounds % 10 == 0}")
print(f"Last analyzed: {agent._last_emotion_analysis_round}")

# Manually trigger
emotion = agent.analyze_emotion()
print(f"Emotion analysis result: {emotion}")
```

**Solutions**:
1. Verify you've had at least 10 rounds
2. Check if analysis was already done for this round
3. Manually trigger using "🔍 Analyze Emotional Relationship" button

### Issue 13: Emotional Radar Chart Not Showing

**Symptoms**: GUI shows empty in emotional relationship tab

**Solutions**:

```python
# 1. Check if emotional data exists
emotion_data = agent.get_emotion_data()
if not emotion_data:
    print("No emotional data, please analyze first")

# 2. Manually refresh GUI
# Click "🔍 Analyze Emotional Relationship" button

# 3. Check if switch to correct tab
# Make sure you're in "💖 Emotional Relationship" tab, not timeline
```

---

## GUI Issues

### Issue 14: GUI Window Too Small

**Symptoms**: Content overlaps or is cut off

**Solution**:

```python
# In gui_enhanced.py, modify minimum window size
root.minsize(1200, 800)  # Increase from default 1000x700

# Or manually resize window
# Drag window edges to desired size
```

### Issue 15: GUI Freezes When Sending Message

**Symptoms**: GUI unresponsive during API call

**Cause**: API call blocks main thread

**This is expected behavior**. The API call must complete before GUI responds.

**Workaround**: Be patient, typically responds within 1-5 seconds.

### Issue 16: Visualization Not Updating

**Symptoms**: Timeline or radar chart doesn't update

**Solutions**:

```python
# 1. Click refresh button
# Click "📈 Update Topic Timeline" or "🔍 Analyze Emotional Relationship"

# 2. Switch tabs
# Switch to other tab and back

# 3. Restart application
# Close and reopen GUI
```

---

## Performance Issues

### Issue 17: High Memory Usage

**Symptoms**: Application uses too much RAM

**Solutions**:

```env
# 1. Reduce memory size
MAX_MEMORY_MESSAGES=30
MAX_SHORT_TERM_ROUNDS=15

# 2. More frequent archiving
MAX_SHORT_TERM_ROUNDS=10

# 3. Close DEBUG mode
DEBUG_MODE=False
```

### Issue 18: Slow Response After Long Use

**Cause**: Too much data accumulated

**Solutions**:

```python
# 1. Clear old data periodically
from database_manager import DatabaseManager

db = DatabaseManager()
# Delete data older than 30 days
db.cleanup_old_data(days=30)

# 2. Restart application
# Memory is cleared on restart

# 3. Optimize database
import sqlite3
conn = sqlite3.connect('chat_agent.db')
conn.execute('VACUUM')
conn.close()
```

---

## Data Issues

### Issue 19: Database Corrupted

**Symptoms**:
```
sqlite3.DatabaseError: database disk image is malformed
```

**Solutions**:

```bash
# 1. Try to recover
sqlite3 chat_agent.db ".dump" | sqlite3 recovered.db
mv recovered.db chat_agent.db

# 2. If recovery fails, restore from backup
cp backup/chat_agent_20250115.db chat_agent.db

# 3. If no backup, create new database
rm chat_agent.db
python gui_enhanced.py
```

### Issue 20: Data Export

**How to export all data**:

```python
from database_manager import DatabaseManager
import json

db = DatabaseManager()

# Export to JSON
data = {
    'memory': db.get('memory_data', []),
    'long_memory': db.get('longmemory_data', []),
    'knowledge': db.get('knowledge_base', []),
    'emotion': db.get('emotion_data', [])
}

with open('export.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print("Data exported to export.json")
```

---

## Debug Tools

### Enable Detailed Logging

```env
# .env file
DEBUG_MODE=True
DEBUG_LOG_FILE=debug.log
```

### View Logs

```python
# In Python
from debug_logger import DebugLogger

logger = DebugLogger.get_instance()

# View all logs
logs = logger.get_logs()
for log in logs[-20:]:  # Last 20 logs
    print(f"[{log['log_type']}] {log['message']}")

# View specific type
errors = logger.get_logs(log_type='error')
for error in errors:
    print(f"Error: {error['message']}")
```

### Check System Info

```python
from chat_agent import ChatAgent

agent = ChatAgent()

# System information
print(f"Model: {agent.model_name}")
print(f"Temperature: {agent.temperature}")
print(f"Max tokens: {agent.max_tokens}")
print(f"Current rounds: {agent.current_rounds}")
print(f"Memory messages: {len(agent.get_memory())}")
```

---

## Still Having Issues?

If problems persist:

1. **Search Existing Issues**: [GitHub Issues](https://github.com/HeDaas-Code/Neo_Agent/issues)
2. **Create New Issue**: Provide:
   - Problem description
   - Steps to reproduce
   - Error messages
   - Environment info (OS, Python version)
   - Debug logs (if available)
3. **Ask in Discussions**: [GitHub Discussions](https://github.com/HeDaas-Code/Neo_Agent/discussions)

---

<div align="center">

**We're here to help!** 💪

</div>
