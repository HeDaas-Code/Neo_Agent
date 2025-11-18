# Usage Examples

[中文](EXAMPLES.md) | **English**

This document provides various use cases and code examples for Neo_Agent.

## Table of Contents

- [Basic Usage](#basic-usage)
- [Advanced Features](#advanced-features)
- [Custom Configuration](#custom-configuration)
- [Practical Application Scenarios](#practical-application-scenarios)
- [Code Integration](#code-integration)

---

## Basic Usage

### Example 1: Simple Conversation

The most basic usage:

```python
from chat_agent import ChatAgent

# Create agent instance
agent = ChatAgent()

# Start conversation
print("AI assistant started, type 'quit' to exit\n")

while True:
    user_input = input("You: ")
    
    if user_input.lower() in ['quit', 'exit']:
        print("Goodbye!")
        break
    
    response = agent.chat(user_input)
    print(f"Xiao Ke: {response}\n")
```

### Example 2: View Memory

View conversation memory and statistics:

```python
from chat_agent import ChatAgent

agent = ChatAgent()

# Have a few conversations
agent.chat("Hello")
agent.chat("My name is John")
agent.chat("I like history")

# View short-term memory
memory = agent.get_memory()
print(f"Current memory: {len(memory)} messages")

# Print all messages
for msg in memory:
    role = "You" if msg['role'] == 'user' else "Xiao Ke"
    print(f"{role}: {msg['content']}")
    print(f"Time: {msg['timestamp']}\n")
```

### Example 3: Start GUI

Use the graphical interface:

```bash
# Command line startup
python gui_enhanced.py
```

Or start in code:

```python
from gui_enhanced import EnhancedChatGUI
import tkinter as tk

root = tk.Tk()
app = EnhancedChatGUI(root)
root.mainloop()
```

---

## Advanced Features

### Example 4: Knowledge Extraction

Automatically extract knowledge from conversations:

```python
from chat_agent import ChatAgent

agent = ChatAgent()

# Have 5 rounds of conversation to trigger knowledge extraction
conversations = [
    "I'm a student",
    "I'm 20 years old",
    "I like programming",
    "I'm learning Python",
    "I'm interested in AI"
]

for msg in conversations:
    response = agent.chat(msg)
    print(f"User: {msg}")
    print(f"AI: {response}\n")

# View extracted knowledge
knowledge = agent.knowledge_base.get_all_knowledge()
print(f"\nExtracted {len(knowledge)} knowledge items:")
for item in knowledge:
    print(f"- [{item['type']}] {item['title']}: {item['content']}")
```

### Example 5: Emotional Analysis

Use the emotional relationship analysis system:

```python
from chat_agent import ChatAgent

agent = ChatAgent()

# Have 10 rounds of conversation to trigger automatic emotional analysis
for i in range(10):
    user_msg = f"Let's talk about topic {i+1}"
    response = agent.chat(user_msg)

# Get emotional data
emotion_data = agent.get_emotion_data()
if emotion_data:
    print("\n=== Emotional Analysis Results ===")
    print(f"Relationship Type: {emotion_data['relationship_type']}")
    print(f"Overall Score: {emotion_data['overall_score']}/100")
    print(f"Emotional Tone: {emotion_data['emotional_tone']}")
    print("\nDimensional Scores:")
    print(f"  Intimacy: {emotion_data['intimacy']}")
    print(f"  Trust: {emotion_data['trust']}")
    print(f"  Pleasure: {emotion_data['pleasure']}")
    print(f"  Resonance: {emotion_data['resonance']}")
    print(f"  Dependence: {emotion_data['dependence']}")
```

### Example 6: Base Knowledge Management

Manage base knowledge (highest priority knowledge):

```python
from base_knowledge import BaseKnowledge

base_kb = BaseKnowledge()

# Add base knowledge
base_kb.add_base_fact(
    entity_name="HeDaas",
    fact_content="HeDaas is a university",
    category="Organization",
    description="Core definition"
)

# Search base knowledge
results = base_kb.search("HeDaas")
print(f"Found {len(results)} base knowledge items:")
for item in results:
    print(f"- {item['entity_name']}: {item['fact_content']}")

# Test in conversation
from chat_agent import ChatAgent
agent = ChatAgent()
response = agent.chat("What is HeDaas?")
print(f"\nAI Response: {response}")
# AI will use base knowledge: "HeDaas is a university"
```

---

## Custom Configuration

### Example 7: Custom Character Settings

Configure different character personalities:

```env
# .env file configuration

# Student character
CHARACTER_NAME=Emma
CHARACTER_GENDER=Female
CHARACTER_ROLE=Student
CHARACTER_AGE=18
CHARACTER_PERSONALITY=Lively and cheerful
CHARACTER_HOBBY=Mathematics and science
CHARACTER_BACKGROUND=I'm a high school student, passionate about STEM...

# Or configure as a professional consultant
CHARACTER_NAME=Dr. Smith
CHARACTER_GENDER=Male
CHARACTER_ROLE=Career Consultant
CHARACTER_AGE=35
CHARACTER_PERSONALITY=Professional and patient
CHARACTER_HOBBY=Career development and psychology
CHARACTER_BACKGROUND=I'm a career consultant with 10 years of experience...
```

### Example 8: Adjust Model Parameters

Optimize model response quality:

```env
# .env file

# Use more powerful model
MODEL_NAME=deepseek-ai/DeepSeek-V3

# Adjust creativity (0-2, default 0.8)
TEMPERATURE=0.7  # Lower = more conservative
# TEMPERATURE=1.2  # Higher = more creative

# Adjust response length
MAX_TOKENS=3000  # Longer responses
# MAX_TOKENS=500  # Shorter responses

# Memory settings
MAX_SHORT_TERM_ROUNDS=30  # Archive every 30 rounds
```

### Example 9: Enable Debug Mode

Enable detailed logging for troubleshooting:

```env
# .env file
DEBUG_MODE=True
DEBUG_LOG_FILE=debug.log
```

View logs in code:

```python
from debug_logger import DebugLogger

logger = DebugLogger.get_instance()

# View recent logs
logs = logger.get_logs(log_type='error', limit=10)
for log in logs:
    print(f"[{log['timestamp']}] {log['message']}")
```

---

## Practical Application Scenarios

### Example 10: Customer Service Assistant

Build an intelligent customer service assistant:

```python
from chat_agent import ChatAgent
from base_knowledge import BaseKnowledge

# Initialize
agent = ChatAgent()
base_kb = BaseKnowledge()

# Add company knowledge
base_kb.add_base_fact(
    entity_name="Company",
    fact_content="Our company offers 24/7 customer support",
    category="Service",
    description="Business hours information"
)

base_kb.add_base_fact(
    entity_name="Return Policy",
    fact_content="30-day unconditional return policy",
    category="Policy",
    description="Return policy"
)

# Customer service conversation loop
print("Customer Service Assistant started")
while True:
    question = input("\nCustomer: ")
    if question.lower() in ['quit', 'exit']:
        break
    
    answer = agent.chat(question)
    print(f"Customer Service: {answer}")
```

### Example 11: Learning Companion

Create a personalized learning companion:

```python
from chat_agent import ChatAgent

agent = ChatAgent()

# Learning session
subjects = ["Math", "Physics", "Chemistry"]

for subject in subjects:
    print(f"\n=== {subject} Learning ===")
    
    # User describes learning situation
    user_msg = f"I'm learning {subject}, can you help me?"
    response = agent.chat(user_msg)
    print(f"AI: {response}")
    
    # User asks questions
    question = input("Your question: ")
    answer = agent.chat(question)
    print(f"AI: {answer}")

# Check learned knowledge
knowledge = agent.knowledge_base.search("", type_filter="Learning")
print(f"\nRecorded {len(knowledge)} learning records")
```

### Example 12: Daily Journal Assistant

Automatically record daily events and extract key information:

```python
from chat_agent import ChatAgent
from datetime import datetime

agent = ChatAgent()

print("Daily Journal Assistant")
print("Record your daily events, I'll help you organize and summarize\n")

# Record events
events = []
while True:
    event = input("Today's event (press Enter to finish): ")
    if not event:
        break
    
    response = agent.chat(f"Today {event}")
    events.append(event)
    print(f"Recorded: {response}\n")

# Generate summary
if events:
    summary_prompt = "Please summarize today's main events"
    summary = agent.chat(summary_prompt)
    print(f"\n=== Today's Summary ===")
    print(summary)
    
    # Save to file
    date_str = datetime.now().strftime("%Y-%m-%d")
    with open(f"journal_{date_str}.txt", "w", encoding="utf-8") as f:
        f.write(f"Date: {date_str}\n\n")
        f.write("Events:\n")
        for i, event in enumerate(events, 1):
            f.write(f"{i}. {event}\n")
        f.write(f"\nSummary:\n{summary}\n")
    
    print(f"\nJournal saved to: journal_{date_str}.txt")
```

---

## Code Integration

### Example 13: Web API Integration

Integrate into Flask web application:

```python
from flask import Flask, request, jsonify
from chat_agent import ChatAgent

app = Flask(__name__)

# Create global agent instance
agent = ChatAgent()

@app.route('/chat', methods=['POST'])
def chat():
    """Chat API endpoint"""
    data = request.json
    user_message = data.get('message', '')
    
    if not user_message:
        return jsonify({'error': 'Message is required'}), 400
    
    try:
        # Generate response
        response = agent.chat(user_message)
        
        return jsonify({
            'success': True,
            'response': response,
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/memory', methods=['GET'])
def get_memory():
    """Get conversation memory"""
    memory = agent.get_memory()
    return jsonify({
        'success': True,
        'memory': memory,
        'count': len(memory)
    })

@app.route('/emotion', methods=['GET'])
def get_emotion():
    """Get emotional analysis results"""
    emotion = agent.get_emotion_data()
    return jsonify({
        'success': True,
        'emotion': emotion
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
```

### Example 14: Command Line Tool

Create a powerful command line chat tool:

```python
#!/usr/bin/env python3
"""
Neo Agent CLI Tool
"""
import argparse
import sys
from chat_agent import ChatAgent

def main():
    parser = argparse.ArgumentParser(description='Neo Agent CLI Chat Tool')
    parser.add_argument('-m', '--message', help='Send a single message')
    parser.add_argument('-i', '--interactive', action='store_true', 
                       help='Start interactive mode')
    parser.add_argument('--memory', action='store_true', 
                       help='Display current memory')
    parser.add_argument('--emotion', action='store_true', 
                       help='Display emotional analysis')
    parser.add_argument('--knowledge', action='store_true', 
                       help='Display knowledge base')
    
    args = parser.parse_args()
    agent = ChatAgent()
    
    if args.message:
        # Single message mode
        response = agent.chat(args.message)
        print(response)
    
    elif args.memory:
        # Display memory
        memory = agent.get_memory()
        print(f"Current memory: {len(memory)} messages\n")
        for msg in memory[-10:]:  # Display last 10
            role = "User" if msg['role'] == 'user' else "AI"
            print(f"[{role}] {msg['content']}")
    
    elif args.emotion:
        # Display emotional analysis
        emotion = agent.get_emotion_data()
        if emotion:
            print(f"Relationship Type: {emotion['relationship_type']}")
            print(f"Overall Score: {emotion['overall_score']}/100")
        else:
            print("No emotional data yet")
    
    elif args.knowledge:
        # Display knowledge base
        knowledge = agent.knowledge_base.get_all_knowledge()
        print(f"Total knowledge: {len(knowledge)}\n")
        for item in knowledge[:10]:  # Display first 10
            print(f"[{item['type']}] {item['title']}")
    
    elif args.interactive:
        # Interactive mode
        print("Interactive mode started (type 'quit' to exit)\n")
        while True:
            try:
                user_input = input("You: ")
                if user_input.lower() in ['quit', 'exit']:
                    break
                response = agent.chat(user_input)
                print(f"AI: {response}\n")
            except KeyboardInterrupt:
                print("\nGoodbye!")
                break
    
    else:
        parser.print_help()

if __name__ == '__main__':
    main()
```

Usage:

```bash
# Single message
python neo_cli.py -m "Hello, how are you?"

# Interactive mode
python neo_cli.py -i

# View memory
python neo_cli.py --memory

# View emotional analysis
python neo_cli.py --emotion

# View knowledge base
python neo_cli.py --knowledge
```

---

## More Examples

For more examples, please refer to:

- [API Documentation](API_EN.md) - Detailed API usage
- [Development Guide](DEVELOPMENT_EN.md) - Advanced development techniques
- [Troubleshooting](TROUBLESHOOTING_EN.md) - Problem solving

---

## Feedback

If you have better usage examples or suggestions, welcome to:

- Submit [Issue](https://github.com/HeDaas-Code/Neo_Agent/issues)
- Submit [Pull Request](https://github.com/HeDaas-Code/Neo_Agent/pulls)
- Discuss in [Discussions](https://github.com/HeDaas-Code/Neo_Agent/discussions)

---

<div align="center">

**Happy coding!** 🎉

</div>
