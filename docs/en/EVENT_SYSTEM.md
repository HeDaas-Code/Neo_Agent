# Event-Driven System Documentation

## Overview

The event-driven module provides pre-configured event functionality for agents, with events classified into two types: **Notification** and **Task**. These events can be triggered through the GUI interface and have higher priority than regular conversations.

## Module Architecture

### Core Modules

1. **event_manager.py** - Event Management Module
   - Creation, storage, retrieval, and management of events
   - Supports both notification and task event types
   - Persistent storage based on SQLite database

2. **interrupt_question_tool.py** - Interrupt Question Tool
   - Allows agents to ask users questions during task execution
   - Supports contextual question prompts

3. **multi_agent_coordinator.py** - Multi-Agent Collaboration Module
   - Handles multi-agent collaboration for task events
   - Task decomposition, planning, and execution
   - Narrative-style progress updates
   - Task completion verification

4. **chat_agent.py** (Extended)
   - Integrated event processing functionality
   - Unified entry point for handling notification and task events

5. **gui_enhanced.py** (Extended)
   - Event management visualization interface
   - Event creation, viewing, triggering, and deletion

## Event Types

### 1. Notification Event

Notification events are used to convey external information to the agent, which needs to immediately understand and explain to the user.

**Characteristics:**
- Agent immediately understands the event meaning upon receipt
- Provides natural explanation to the user
- No need to execute complex tasks
- Quick processing

**Use Cases:**
- System update notifications
- Important message reminders
- Status change notifications
- External event notifications

**Example:**
```python
from event_manager import EventType, EventPriority

event = agent.event_manager.create_event(
    title="System Update Notification",
    description="New version released, including performance optimizations and bug fixes.",
    event_type=EventType.NOTIFICATION,
    priority=EventPriority.MEDIUM
)
```

### 2. Task Event

Task events require the agent to understand task requirements, plan, and complete tasks through multi-agent collaboration.

**Characteristics:**
- Requires understanding of task requirements and completion criteria
- Uses multi-agent collaboration for completion
- Can ask users for necessary information
- Outputs narrative-style progress updates
- Completion verified by tool agent

**Use Cases:**
- Data organization and analysis
- Document generation
- Information summarization
- Complex query tasks

**Example:**
```python
event = agent.event_manager.create_event(
    title="Generate Weekly Report",
    description="Generate a weekly report summary based on this week's conversation records",
    event_type=EventType.TASK,
    priority=EventPriority.HIGH,
    task_requirements="Need to summarize main conversation topics and knowledge points from this week",
    completion_criteria="Report must include: topic list, knowledge point summary, conversation statistics"
)
```

## Event Processing Flow

### Notification Event Processing Flow

1. **Trigger Event** - User clicks "Trigger Event" button in GUI
2. **Understanding Phase** - Agent analyzes event content and meaning
3. **Explanation Phase** - Agent explains event to user in natural tone
4. **Complete** - Event marked as completed

```
[User Trigger] → [Agent Understanding] → [Generate Explanation] → [Display to User] → [Complete]
```

### Task Event Processing Flow

1. **Trigger Event** - User clicks "Trigger Event" button in GUI
2. **Task Understanding** - Understanding agent analyzes task requirements
3. **Make Plan** - Planning agent decomposes task into specific steps
4. **Execute Steps** - Execution agent completes task step by step
   - Use interrupt question tool if user input needed
   - Output narrative-style progress updates
5. **Verify Completion** - Verification agent checks if completion criteria met
6. **Result Feedback** - Display task results to user

```
[User Trigger] 
    ↓
[Task Understanding] (Understanding Agent)
    ↓
[Make Plan] (Planning Agent) - Decompose into 3-5 steps
    ↓
[Execute Steps] (Execution Agent)
    ├─ Step 1 → [Output Progress] → [Complete]
    ├─ Step 2 → [Need Info] → [Interrupt Question] → [User Answer] → [Continue]
    ├─ Step 3 → [Output Progress] → [Complete]
    └─ ...
    ↓
[Verify Results] (Verification Agent)
    ↓
[Display Results] → [Complete/Failed]
```

## Interrupt Question Tool

During task execution, if the agent needs information from the user, it can use the interrupt question tool.

**Usage:**

```python
# Agent internal call (automatically handled)
answer = interrupt_question_tool.ask_user(
    question="What specific content would you like the weekly report to include?",
    context="Generating weekly report, need to confirm report scope"
)
```

**When to Ask Questions:**
- Task information unclear
- Need user confirmation for decisions
- Multiple choices exist
- User parameters needed

## Narrative-Style Progress Updates

During multi-agent collaboration, the system outputs progress updates in third-person narrative style:

```
📢 Agent begins analyzing task「Generate Weekly Report」...
📢 Task understood: Need to extract key information from conversation history to generate report
📢 Agent is making execution plan...
📢 Execution plan completed, 3 steps total
📢 Executing step 1/3: Extract conversation topics
📢 Step 1 complete
📢 Executing step 2/3: Count conversation data
📢 Step 2 complete
📢 Executing step 3/3: Generate report document
📢 Step 3 complete
📢 All steps completed, verifying task results...
📢 ✅ Task verification passed! Weekly report successfully generated
```

## GUI Usage Guide

### Open Event Management Panel

1. Start application: `python gui_enhanced.py`
2. Click "📅 Event Management" in the right sidebar

### Create New Event

1. Click "➕ New Event" button
2. Fill in event information:
   - Event title
   - Event description
   - Event type (Notification/Task)
   - Priority (Low/Medium/High/Urgent)
3. For task events, also fill in:
   - Task requirements
   - Completion criteria
4. Click "Create" button

### Trigger Event

1. Select an event from the event list
2. Click "🚀 Trigger Event" button
3. Wait for agent processing
4. View processing results (displayed in chat area)

### View Event Details

1. Select an event from the event list
2. Click "📝 View Details" button
3. View event information and processing logs

### Delete Event

1. Select an event from the event list
2. Click "🗑️ Delete Event" button
3. Confirm deletion

## Event Priority

The event system supports four priority levels:

- **LOW (1)** - Low priority, can be processed later
- **MEDIUM (2)** - Medium priority, normal processing
- **HIGH (3)** - High priority, prioritized processing
- **URGENT (4)** - Urgent, immediate processing

Pending event list is sorted by priority (descending) and creation time (ascending).

## Event Status

Events go through the following states in their lifecycle:

- **PENDING** - Pending, newly created state
- **PROCESSING** - Processing, being handled by agent
- **COMPLETED** - Completed, successfully processed
- **FAILED** - Failed, error occurred during processing
- **CANCELLED** - Cancelled, user actively cancelled

## Database Structure

### events Table

Stores event basic information:

| Field | Type | Description |
|-------|------|-------------|
| event_id | TEXT | Event unique ID (UUID) |
| title | TEXT | Event title |
| description | TEXT | Event description |
| event_type | TEXT | Event type (notification/task) |
| priority | INTEGER | Priority (1-4) |
| status | TEXT | Event status |
| created_at | TEXT | Creation time (ISO 8601) |
| updated_at | TEXT | Update time |
| completed_at | TEXT | Completion time |
| metadata | TEXT | Additional metadata (JSON) |

### event_logs Table

Stores event processing logs:

| Field | Type | Description |
|-------|------|-------------|
| log_id | INTEGER | Log ID (auto-increment) |
| event_id | TEXT | Associated event ID |
| log_type | TEXT | Log type |
| log_content | TEXT | Log content |
| created_at | TEXT | Creation time |

## API Reference

### EventManager

```python
from event_manager import EventManager, EventType, EventPriority

# Initialize
manager = EventManager(db_manager=db)

# Create event
event = manager.create_event(
    title="Title",
    description="Description",
    event_type=EventType.NOTIFICATION,
    priority=EventPriority.HIGH
)

# Get event
event = manager.get_event(event_id)

# Get pending events
pending = manager.get_pending_events(limit=10)

# Update event status
manager.update_event_status(event_id, EventStatus.COMPLETED, "Completion message")

# Add log
manager.add_event_log(event_id, "log_type", "Log content")

# Get logs
logs = manager.get_event_logs(event_id)

# Delete event
manager.delete_event(event_id)

# Get statistics
stats = manager.get_statistics()
```

### ChatAgent Event Processing

```python
from chat_agent import ChatAgent

agent = ChatAgent()

# Process notification event
explanation = agent.process_notification_event(notification_event)

# Process task event
result = agent.process_task_event(task_event)

# Unified event processing entry
result_message = agent.handle_event(event_id)

# Get pending events
pending_events = agent.get_pending_events()

# Get event statistics
stats = agent.get_event_statistics()
```

### InterruptQuestionTool

```python
from interrupt_question_tool import InterruptQuestionTool

tool = InterruptQuestionTool()

# Set callback function
tool.set_question_callback(lambda q: input(q))

# Ask user
answer = tool.ask_user(
    question="Your question?",
    context="Background explanation"
)
```

## Best Practices

### 1. Create Clear Event Titles

✅ Good titles:
- "System Update Notification v2.0"
- "Generate This Week's Conversation Report"
- "Organize Knowledge Base Categories"

❌ Bad titles:
- "Notification"
- "Task"
- "Test"

### 2. Provide Detailed Event Descriptions

Descriptions should include:
- Event background information
- Specific event content
- Related time, location, people, etc.

### 3. Clearly Define Task Requirements and Completion Criteria

For task events:
- Task requirements should be specific and clear
- Completion criteria should be verifiable
- Avoid vague descriptions

### 4. Set Priority Reasonably

- Urgent and important → URGENT
- Important but not urgent → HIGH
- General affairs → MEDIUM
- Can be postponed → LOW

### 5. Clean Up Completed Events Promptly

Regularly delete completed historical events to keep the event list clean.

## Extension Development

### Add New Event Types

1. Add new type in `EventType` enum
2. Create corresponding event class (inherit from `Event`)
3. Add handling method in `ChatAgent`
4. Update GUI to support new type

### Customize Agent Roles

In `multi_agent_coordinator.py`, you can customize agents with different roles:

```python
agent = SubAgent(
    agent_id='custom_agent',
    role='Custom Role',
    description='Role responsibility description',
    api_key=api_key,
    api_url=api_url,
    model_name=model_name
)
```

### Add New Tools

Add new tools for agents:

1. Create tool class
2. Implement `create_tool_description()` method
3. Pass to agent when executing steps

## Troubleshooting

### Event Creation Failed

- Check if database connection is normal
- Confirm event parameters are complete
- Check logs for detailed error information

### Event Processing Timeout

- Check if API key is valid
- Confirm network connection is normal
- Consider increasing timeout duration

### Interrupt Question No Response

- Confirm callback function is set correctly
- Check if GUI main thread is blocked
- Verify dialog displays normally

## Notes

1. **API Key Configuration**: Ensure valid `SILICONFLOW_API_KEY` is configured in `.env` file
2. **Database Backup**: Important event data should be backed up regularly
3. **Concurrent Processing**: Only one event can be processed at a time
4. **Resource Consumption**: Complex tasks may consume significant API call quota
5. **User Experience**: User interface may be briefly unresponsive during event processing

## Changelog

### v1.0.0 (2025-01-19)

- ✅ Initial version release
- ✅ Support for notification and task events
- ✅ Multi-agent collaboration implementation
- ✅ Interrupt question tool added
- ✅ GUI event management interface
- ✅ Narrative-style progress updates
- ✅ Task completion verification mechanism

## Contributing

Issues and improvement suggestions welcome!

To contribute code:
1. Fork the project
2. Create feature branch
3. Commit changes
4. Create Pull Request

## License

This project is licensed under the MIT License.

---

Last Updated: 2025-01-19
