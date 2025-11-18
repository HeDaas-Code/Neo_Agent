# Contributing Guide

[中文](CONTRIBUTING.md) | **English**

Thank you for your interest in the Neo_Agent project! We welcome all forms of contribution, including but not limited to:

- 🐛 Bug reports
- 💡 Feature suggestions
- 📝 Documentation improvements
- 🔧 Code fixes
- ⭐ Adding new features

## 📋 Table of Contents

- [Code of Conduct](#code-of-conduct)
- [How to Contribute](#how-to-contribute)
- [Development Process](#development-process)
- [Code Standards](#code-standards)
- [Commit Standards](#commit-standards)
- [Testing Requirements](#testing-requirements)

## Code of Conduct

When participating in this project, please follow these guidelines:

- Respect all contributors
- Use inclusive language
- Accept constructive criticism
- Focus on what's best for the community
- Show empathy towards other community members

## How to Contribute

### Reporting Issues

If you find a bug or have a feature suggestion:

1. First search in [Issues](https://github.com/HeDaas-Code/Neo_Agent/issues) for similar problems
2. If not found, create a new issue and provide the following information:
   - **Bug Report**:
     - Problem description
     - Steps to reproduce
     - Expected behavior
     - Actual behavior
     - Environment (Python version, OS, etc.)
     - Error logs (if available)
   - **Feature Suggestion**:
     - Feature description
     - Use case
     - Expected outcome

### Submitting Code

#### 1. Fork the Project

1. Click the "Fork" button in the upper right corner of the project page
2. Clone your forked repository:
   ```bash
   git clone https://github.com/YOUR_USERNAME/Neo_Agent.git
   cd Neo_Agent
   ```

#### 2. Create a Branch

Create a new branch for your modification:

```bash
# Feature branch
git checkout -b feature/your-feature-name

# Bug fix branch
git checkout -b fix/bug-description
```

#### 3. Make Changes

- Follow [Code Standards](#code-standards)
- Write clear comments
- Keep commits focused and small
- Write or update related tests
- Update documentation

#### 4. Test Changes

Before submitting, ensure:

```bash
# Install dependencies
pip install -r requirements.txt

# Run tests (if available)
python -m pytest

# Test GUI
python gui_enhanced.py

# Test command line
python chat_agent.py
```

#### 5. Commit Changes

Follow [Commit Standards](#commit-standards):

```bash
git add .
git commit -m "feat: add new feature description"
```

#### 6. Push Branch

```bash
git push origin feature/your-feature-name
```

#### 7. Create Pull Request

1. Go to your forked repository on GitHub
2. Click "Pull Request" button
3. Select your branch and fill in PR description:
   - What problem does it solve?
   - What changes were made?
   - Is there anything to pay attention to?
   - Related Issues (if any)

## Development Process

### Environment Setup

1. **Python Environment**
   ```bash
   # Recommended Python 3.8+
   python --version
   
   # Create virtual environment
   python -m venv venv
   
   # Activate virtual environment
   # Windows
   venv\Scripts\activate
   # Linux/Mac
   source venv/bin/activate
   
   # Install dependencies
   pip install -r requirements.txt
   ```

2. **Configure API Key**
   ```bash
   # Copy configuration template
   cp example.env .env
   
   # Edit .env file, fill in your API key
   SILICONFLOW_API_KEY=your_api_key_here
   ```

3. **Run Tests**
   ```bash
   # GUI mode
   python gui_enhanced.py
   
   # Command line mode
   python chat_agent.py
   ```

### Development Workflow

```
1. Create Issue/Select existing Issue
   ↓
2. Fork project and create branch
   ↓
3. Make changes and test locally
   ↓
4. Commit changes (follow commit standards)
   ↓
5. Push branch and create PR
   ↓
6. Code review and discussion
   ↓
7. Merge (after approval)
```

## Code Standards

### Python Code Style

Follow PEP 8 standards:

```python
# Good example
def calculate_emotion_score(intimacy, trust, pleasure):
    """Calculate overall emotional score.
    
    Args:
        intimacy: Intimacy level (0-100)
        trust: Trust level (0-100)
        pleasure: Pleasure level (0-100)
        
    Returns:
        Overall score (0-100)
    """
    return (intimacy + trust + pleasure) / 3


# Bad example
def calc(i,t,p):
    return (i+t+p)/3
```

### Naming Conventions

- **Variables and Functions**: Use snake_case
  ```python
  user_name = "John"
  def get_user_info():
      pass
  ```

- **Classes**: Use PascalCase
  ```python
  class ChatAgent:
      pass
  
  class EmotionAnalyzer:
      pass
  ```

- **Constants**: Use UPPER_CASE
  ```python
  MAX_MEMORY_SIZE = 100
  DEFAULT_TEMPERATURE = 0.8
  ```

### Comments and Documentation

```python
# Module-level docstring
"""
Chat agent module.

This module implements the core chat agent functionality, including
conversation management, memory archiving, and knowledge extraction.
"""

class ChatAgent:
    """Chat agent class.
    
    Attributes:
        memory: Short-term memory manager
        knowledge_base: Knowledge base manager
        emotion_analyzer: Emotional relationship analyzer
    """
    
    def chat(self, user_input: str) -> str:
        """Process user input and generate response.
        
        Args:
            user_input: User's input text
            
        Returns:
            AI's response text
            
        Raises:
            ValueError: When input is empty
        """
        pass
```

### File Organization

```python
# 1. Standard library imports
import os
import sys
from typing import List, Dict

# 2. Third-party library imports
import tkinter as tk
from langchain.llms import OpenAI

# 3. Local module imports
from chat_agent import ChatAgent
from knowledge_base import KnowledgeBase
```

## Commit Standards

### Commit Message Format

```
<type>(<scope>): <subject>

<body>

<footer>
```

### Type

- **feat**: New feature
- **fix**: Bug fix
- **docs**: Documentation changes only
- **style**: Code style changes (whitespace, formatting, etc.)
- **refactor**: Code refactoring (neither new feature nor bug fix)
- **perf**: Performance improvement
- **test**: Add or modify tests
- **chore**: Build process or auxiliary tool changes

### Examples

```bash
# New feature
git commit -m "feat(emotion): add emotional analysis automatic trigger"

# Bug fix
git commit -m "fix(knowledge): fix base knowledge not being retrieved"

# Documentation update
git commit -m "docs(readme): add English documentation"

# Code refactoring
git commit -m "refactor(memory): optimize memory archiving logic"

# Performance improvement
git commit -m "perf(gui): optimize GUI rendering performance"
```

### Detailed Commit Message

```bash
git commit -m "feat(emotion): add emotional radar chart

- Add EmotionRadarCanvas class
- Implement pentagon visualization
- Support real-time data update
- Add tab switching function

Closes #123"
```

## Testing Requirements

### Unit Tests

```python
# test_chat_agent.py
import unittest
from chat_agent import ChatAgent

class TestChatAgent(unittest.TestCase):
    def setUp(self):
        """Initialize test environment."""
        self.agent = ChatAgent()
    
    def test_chat_basic(self):
        """Test basic conversation function."""
        response = self.agent.chat("Hello")
        self.assertIsNotNone(response)
        self.assertIsInstance(response, str)
    
    def test_memory_archiving(self):
        """Test memory archiving."""
        # Simulate 21 rounds of conversation
        for i in range(21):
            self.agent.chat(f"Test message {i}")
        
        # Verify long-term memory generation
        long_memory = self.agent.get_long_memory()
        self.assertGreater(len(long_memory), 0)

if __name__ == '__main__':
    unittest.main()
```

### Integration Tests

```python
# test_integration.py
def test_full_workflow():
    """Test complete workflow."""
    agent = ChatAgent()
    
    # 1. Test basic conversation
    response = agent.chat("Hello")
    assert response
    
    # 2. Test knowledge extraction (5 rounds)
    for i in range(5):
        agent.chat(f"I like history {i}")
    knowledge = agent.get_knowledge()
    assert len(knowledge) > 0
    
    # 3. Test emotional analysis (10 rounds)
    for i in range(5):
        agent.chat(f"Continue conversation {i}")
    emotion = agent.get_emotion_data()
    assert emotion is not None
```

### Manual Tests

Before submitting PR, please test manually:

1. **GUI Test**
   - Start GUI: `python gui_enhanced.py`
   - Test all tabs
   - Test all buttons
   - Test visualization (timeline, radar chart)

2. **Feature Test**
   - Test conversation function
   - Test memory archiving (21 rounds)
   - Test knowledge extraction (5 rounds)
   - Test emotional analysis (10 rounds)

3. **Edge Case Test**
   - Empty input
   - Extremely long input
   - Special characters
   - Network error handling

## Best Practices

### 1. Code Quality

- Keep functions short and focused
- Avoid nested conditions and loops
- Use meaningful variable names
- Write clear comments

### 2. Performance Optimization

- Avoid unnecessary API calls
- Use caching appropriately
- Optimize database queries
- Reduce memory usage

### 3. Security

- Don't hard-code API keys
- Validate user input
- Handle errors appropriately
- Protect sensitive data

### 4. Maintainability

- Follow DRY principle (Don't Repeat Yourself)
- Modular design
- Write tests
- Update documentation

## Communication

### Where to Ask Questions?

- **Issues**: Bug reports, feature suggestions
- **Discussions**: General discussions, Q&A
- **Pull Requests**: Code review, technical discussions

### Response Time

- We will try to respond to Issues and PRs within 48 hours
- More complex issues may take longer to process
- Please be patient and polite

## Acknowledgments

Thank you for your contribution! Every PR, Issue, and Star makes the project better.

### Contributors

See [Contributors List](https://github.com/HeDaas-Code/Neo_Agent/graphs/contributors)

---

## 📞 Contact

If you have any questions, feel free to contact us:

- Create an Issue
- Email: [Your Email]
- GitHub: [@HeDaas-Code](https://github.com/HeDaas-Code)

---

**Once again, thank you for your contribution to Neo_Agent! 🎉**
