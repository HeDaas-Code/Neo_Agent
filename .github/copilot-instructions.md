# Neo Agent - Copilot Instructions

## Project Overview

Neo Agent is an intelligent dialogue agent system based on LangChain, supporting role-playing, long-term memory management, and emotional relationship analysis. The system implements intelligent dialogue experiences with persistent memory capabilities through hierarchical memory architecture and knowledge base management.

**Primary Language**: Python 3.8+  
**Main Framework**: LangChain  
**GUI**: Tkinter  
**Database**: SQLite  
**API**: SiliconFlow (compatible with OpenAI format)

## Core Architecture

### Memory Hierarchy
1. **Short-term Memory**: Recent 20 rounds of detailed conversation (managed by `MemoryManager`)
2. **Long-term Memory**: Summarized historical conversations (managed by `LongTermMemoryManager`)
3. **Knowledge Base**: Extracted and persistent knowledge from conversations (managed by `KnowledgeBase`)
4. **Base Knowledge**: Preset immutable core knowledge (managed by `BaseKnowledgeManager`)

### Key Components
- `chat_agent.py` - Core dialogue agent with memory management
- `database_manager.py` - Unified SQLite database operations
- `long_term_memory.py` - Long-term memory generation and management
- `knowledge_base.py` - Knowledge extraction and retrieval
- `emotion_analyzer.py` - Emotional relationship analysis
- `event_manager.py` - Event-driven system for notifications and tasks
- `multi_agent_coordinator.py` - Multi-agent collaboration system
- `agent_vision.py` - Vision tool for environment perception simulation
- `gui_enhanced.py` - Main GUI interface (~3000 lines)

## Development Setup

### Prerequisites
```bash
python --version  # Should be 3.8 or higher
pip install -r requirements.txt
```

### Configuration
1. Copy `example.env` to `.env`
2. Configure required environment variables:
   - `SILICONFLOW_API_KEY` - Your API key
   - `MODEL_NAME` - LLM model (default: deepseek-ai/DeepSeek-V3)
   - Character settings (NAME, GENDER, AGE, PERSONALITY, etc.)
   - Memory settings (MAX_MEMORY_MESSAGES, MAX_SHORT_TERM_ROUNDS)

### Running the Application
```bash
python gui_enhanced.py  # Main GUI application
python test_event_system.py  # Test event system
```

## Code Style and Conventions

### Python Style
- **Docstrings**: Use triple-quoted strings with Chinese descriptions for classes and functions
- **Type Hints**: Use type hints from `typing` module (List, Dict, Any, Optional)
- **Imports**: Group imports as: standard library, third-party, local modules
- **Naming**: 
  - Classes: PascalCase (e.g., `ChatAgent`, `DatabaseManager`)
  - Functions/Methods: snake_case (e.g., `load_memory`, `get_recent_messages`)
  - Constants: UPPER_SNAKE_CASE (e.g., `MAX_MEMORY_MESSAGES`)

### Documentation
- Primary documentation is in Chinese (zh-cn)
- English translations available in docs/en/
- Use descriptive comments for complex logic
- Include examples in docstrings where appropriate

### Environment Variables
- All configurable parameters should use environment variables with defaults
- Use `python-dotenv` for loading `.env` files
- Document all environment variables in `example.env`

## Database Management

### Schema
The SQLite database (`chat_agent.db`) contains:
- `short_term_memory` - Recent conversation history
- `long_term_memory` - Summarized historical conversations
- `knowledge_base` - Extracted knowledge with status tracking
- `base_knowledge` - Immutable core knowledge
- `environment_descriptions` - Environment context for vision tool
- `events` - Event-driven system events
- `event_logs` - Event processing logs

### Best Practices
- Always use `DatabaseManager` for database operations
- Use transactions for batch operations
- Handle database locks gracefully with retry logic
- Close database connections properly

## LLM Integration

### API Calls
- Use `requests` library for HTTP calls to SiliconFlow API
- API format is compatible with OpenAI's chat completion format
- Implement retry logic with exponential backoff
- Log all API calls using `debug_logger` when DEBUG_MODE is enabled

### Prompt Construction
- Build prompts with character personality and background
- Include relevant memory context (short-term, long-term, knowledge)
- Use system messages for role definition
- Keep prompts under token limits (default: MAX_TOKENS=2000)

## Event-Driven System

### Event Types
1. **Notification Events**: Agent immediately understands and explains external information
2. **Task Events**: Multi-agent collaboration for complex tasks with progress updates

### Event Management
- Create events via `EventManager.create_event()`
- Events stored in database with status tracking
- Support for priority levels (LOW, NORMAL, HIGH, URGENT)
- Event logs track processing history

## Testing

### Test Files
- `test_event_system.py` - Demonstrates event system functionality
- Manual testing through GUI is the primary validation method

### Testing Approach
- Test core functionality through the GUI
- Verify memory persistence across sessions
- Check database integrity after operations
- Validate API integration with debug logs

## Important Notes

### Memory Management
- Short-term memory is limited to `MAX_SHORT_TERM_ROUNDS` (default: 20)
- Long-term memory is generated when short-term exceeds capacity
- Knowledge extraction happens during long-term memory generation
- Base knowledge is read-only and loaded at initialization

### Debug Mode
- Enable `DEBUG_MODE=True` in `.env` for detailed logging
- Logs include prompts, API calls, and responses
- Check `debug.log` or GUI debug viewer for troubleshooting

### GUI Components
- Built with Tkinter for cross-platform compatibility
- Includes emotion radar chart, timeline visualization
- Database management GUI for data inspection
- Real-time debug log viewer

### Vision Tool
- Uses LLM to intelligently determine when environment info is needed
- Falls back to keyword matching if LLM is unavailable
- Simulates visual perception through environment descriptions
- Configurable timeout and token limits

## Common Tasks

### Adding New Features
1. Check if feature fits into existing component structure
2. Update database schema if needed (via `DatabaseManager`)
3. Add configuration to `example.env` if configurable
4. Update relevant documentation in `docs/zh-cn/`
5. Test through GUI before committing

### Modifying Memory System
- Changes should maintain backward compatibility with existing data
- Update migration logic in `DatabaseManager` if schema changes
- Test memory persistence across application restarts

### Extending Event System
- New event types should inherit from `NotificationEvent` or `TaskEvent`
- Register event handlers in `EventManager`
- Update event processing logic in `ChatAgent`

## Resources

- [Architecture Documentation](docs/zh-cn/ARCHITECTURE.md)
- [API Documentation](docs/zh-cn/API.md)
- [Event System Guide](docs/zh-cn/EVENT_SYSTEM.md)
- [Quick Start Guide](docs/zh-cn/QUICKSTART.md)
- [Development Guide](docs/zh-cn/DEVELOPMENT.md)

## Contact

- Issues: https://github.com/HeDaas-Code/Neo_Agent/issues
- Discussions: https://github.com/HeDaas-Code/Neo_Agent/discussions
