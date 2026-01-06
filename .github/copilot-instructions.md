# Copilot Instructions for Neo Agent

## Project Overview

Neo Agent is an intelligent conversation agent system based on LangChain, supporting role-playing, long-term memory management, and emotional relationship analysis. The system is designed primarily for Chinese users with bilingual (Chinese/English) documentation.

## Technology Stack

- **Language**: Python 3.8+
- **Main Framework**: LangChain (langchain, langchain-community, langchain-core)
- **Database**: SQLite for persistent storage
- **GUI**: Tkinter for graphical user interface
- **API**: SiliconFlow API for LLM integration
- **Configuration**: python-dotenv for environment management

## Code Organization

### Core Modules

- `chat_agent.py` - Main conversation agent with memory management
- `database_manager.py` - Unified database operations with SQLite
- `long_term_memory.py` - Long-term memory summarization and management
- `knowledge_base.py` - Knowledge extraction and storage from conversations
- `emotion_analyzer.py` - Emotion and relationship analysis
- `event_manager.py` - Event-driven system for notifications and tasks
- `multi_agent_coordinator.py` - Multi-agent collaboration system
- `agent_vision.py` - Vision tool with LLM-based environment perception
- `gui_enhanced.py` - Main GUI application
- `database_gui.py` - Database management GUI
- `base_knowledge.py` - Immutable core knowledge management

### Supporting Modules

- `debug_logger.py` - Debug logging system
- `interrupt_question_tool.py` - User interaction tool during task execution
- `expression_style.py` - Character expression style management
- `test_event_system.py` - Event system testing

## Coding Conventions

### Language and Comments

- **Primary Language**: Chinese for code comments, docstrings, and variable names that represent domain concepts
- **Documentation**: Maintain bilingual (Chinese/English) documentation in `docs/` folder
- **Docstrings**: Use Chinese for detailed docstrings explaining functionality
- Example:
  ```python
  from typing import List, Dict, Any
  
  def analyze_emotion(self, messages: List[Dict[str, Any]]) -> Dict[str, Any]:
      """
      分析情感关系
      
      Args:
          messages: 对话消息列表
          
      Returns:
          包含印象描述和评分的字典
      """
  ```

### Python Style

- Follow PEP 8 style guidelines
- Use type hints for function parameters and return values
- Use docstrings for all classes and public methods
- Prefer descriptive variable names in Chinese for domain-specific concepts
- Use English for technical terms and common programming constructs

### Memory and Data Management

- All persistent data uses SQLite through `DatabaseManager`
- Short-term memory: Recent 20 conversation rounds
- Long-term memory: Summarized historical conversations
- Knowledge base: Extracted factual information from conversations
- Base knowledge: Predefined immutable core knowledge

### Environment Configuration

- All configurable parameters should be in `.env` file
- Use `example.env` as template
- Never commit actual API keys or sensitive data
- Use `os.getenv()` with sensible defaults

### Error Handling

- Use try-except blocks for external API calls
- Log errors using the debug logger
- Provide meaningful error messages in Chinese
- Gracefully handle API failures and timeouts

## Development Guidelines

### Adding New Features

1. Consider memory and database implications
2. Update relevant documentation in both Chinese and English
3. Add debug logging for important operations
4. Maintain backward compatibility with existing data
5. Update `example.env` if new configuration is needed

### Database Changes

- Use `DatabaseManager` for all database operations
- Test data migration from JSON to SQLite if applicable
- Ensure proper error handling and transaction management
- Document schema changes

### GUI Development

- Use Tkinter conventions consistent with existing code
- Maintain the modern, user-friendly interface style
- Support real-time updates and visual feedback
- Include proper error dialogs in Chinese

### Event System

- Use `EventManager` for event-driven functionality
- Support both notification events and task events
- Enable multi-agent coordination for complex tasks
- Implement proper event status tracking

## Testing

### Test Structure

- Tests are located in `tests/` directory
- Use descriptive test names in English
- Test both success and failure scenarios
- Mock external API calls when appropriate

### Running Tests

```bash
python -m pytest tests/
```

### Manual Testing

- Use `gui_enhanced.py` for GUI testing
- Test with various character configurations
- Verify memory persistence across sessions
- Check emotion analysis with different conversation patterns

## Dependencies

- Keep `requirements.txt` minimal and up-to-date
- Use version constraints (>=) for flexibility
- Document any system-level dependencies
- Test with clean virtual environment

## Key Design Patterns

### Memory Hierarchy

- Short-term: Detailed recent conversations
- Long-term: Summarized history
- Knowledge base: Extracted facts
- Base knowledge: Core immutable knowledge

### Character System

- Configurable via environment variables
- Supports custom personality, background, hobbies
- Used for role-playing and emotion analysis

### Event-Driven Architecture

- Notification events: Immediate information sharing
- Task events: Complex multi-agent tasks
- Interrupt questions: User interaction during execution
- Visual progress tracking in GUI

## Common Pitfalls to Avoid

1. **Don't** hardcode file paths - use environment variables
2. **Don't** mix JSON and database storage - use `DatabaseManager` consistently
3. **Don't** skip debug logging for important operations
4. **Don't** forget to update both Chinese and English documentation
5. **Don't** commit sensitive data like API keys
6. **Don't** break backward compatibility without migration path

## Security Considerations

- Never expose API keys in code
- Validate user inputs in GUI and event handlers
- Sanitize data before database insertion
- Use secure API communication (HTTPS)

## Build and Run

### Setup

```bash
pip install -r requirements.txt
cp example.env .env
# Edit .env with your configuration
```

### Run Application

```bash
python gui_enhanced.py
```

### Debug Mode

Enable in `.env`:
```
DEBUG_MODE=True
DEBUG_LOG_FILE=debug.log
```

## Contributing

- Follow existing code style and conventions
- Add tests for new functionality
- Update documentation for significant changes
- Use meaningful commit messages in English
- Keep changes focused and minimal

## API Integration

- Primary API: SiliconFlow for LLM chat completions
- Use `requests` library for API calls
- Implement timeout and retry logic
- Handle rate limiting gracefully
- Log all API interactions when debug mode is enabled

## Vision System

The `agent_vision.py` module provides intelligent environment perception:

- **LLM-based semantic understanding**: Uses LLM to analyze user queries and determine if environment information is needed (e.g., "你在哪？" / "Where are you?")
- **Keyword matching fallback**: When LLM is unavailable, falls back to keyword matching for common phrases
- **Environment description simulation**: Provides textual environment descriptions to simulate visual perception without actual image processing
- **Intelligent context detection**: Automatically identifies both explicit and implicit requests for environmental information
- **Configurable parameters**: Vision LLM temperature, max tokens, and timeout can be configured via environment variables

## Multi-Agent System

- Coordinator manages multiple agents
- Task decomposition and delegation
- Progress tracking and result aggregation
- Support for interrupt questions during execution
