# Knowledge Status Management System

## Overview

The Knowledge Status Management System is a significant improvement to the agent's knowledge base functionality. It implements a smarter knowledge collection and confirmation mechanism, distinguishing between "suspected" and "confirmed" knowledge by tracking how many times information has been mentioned.

## Core Features

### 1. Extract Knowledge Only from User Messages

The system now **extracts information only from user statements**, not from assistant responses. This ensures that the knowledge base contains information from the user's actual expressions rather than AI inferences or responses.

### 2. Knowledge Status Management

Each piece of related information has a status tag:

| Status | Description | Trigger Condition |
|--------|-------------|-------------------|
| Suspected | First mention, needs confirmation | Information extracted for the first time |
| Confirmed | Multiple mentions, high confidence | Same information mentioned ≥3 times |

### 3. Mention Count Tracking

The system tracks how many times each piece of information has been mentioned:
- **mention_count**: Total number of times the information was mentioned
- **last_mentioned_at**: Timestamp of the last mention

### 4. Automatic Status Upgrade

When the same information is mentioned multiple times:
1. 1st mention: Create new knowledge item, status="Suspected", mention_count=1
2. 2nd mention: Increase mention_count to 2, status remains "Suspected"
3. 3rd mention: Increase mention_count to 3, **status automatically upgrades to "Confirmed"**

**Configuration:**
- Upgrade threshold configured via `DatabaseManager.KNOWLEDGE_CONFIRMATION_THRESHOLD`
- Default value is 3, adjustable as needed

## Database Structure

### New Fields in entity_related_info Table

```sql
CREATE TABLE entity_related_info (
    uuid TEXT PRIMARY KEY,
    entity_uuid TEXT NOT NULL,
    content TEXT NOT NULL,
    type TEXT DEFAULT '其他',
    source TEXT,
    confidence REAL DEFAULT 0.7,
    status TEXT DEFAULT '疑似',           -- New: Status field
    mention_count INTEGER DEFAULT 1,      -- New: Mention count
    last_mentioned_at TEXT,               -- New: Last mentioned time
    created_at TEXT NOT NULL,
    FOREIGN KEY (entity_uuid) REFERENCES entities(uuid) ON DELETE CASCADE
)
```

## Usage Example

### Scenario

**Round 1:**
```
User: I like playing basketball
System: [Extract knowledge] "I" -> "likes basketball" [Suspected×1]
```

**Round 2:**
```
User: I often play basketball
System: [Update knowledge] "I" -> "likes basketball" [Suspected×2]
```

**Round 3:**
```
User: Basketball is my hobby
System: [Upgrade status] "I" -> "likes basketball" [✓Confirmed]
```

## Database Migration

### Automatic Migration

The system automatically detects and migrates old databases during initialization:

1. Check if `entity_related_info` table has new fields
2. If fields are missing, automatically execute `ALTER TABLE` to add them
3. Set default values for existing old data:
   - `status = '疑似'` (Suspected)
   - `mention_count = 1`
   - `last_mentioned_at = NULL`

### Backward Compatibility

- ✅ Fully compatible with old database versions
- ✅ Does not affect existing data
- ✅ Automatically sets reasonable default values
- ✅ No manual operation required

## Configuration Options

### Adjust Confirmation Threshold

To adjust the status upgrade threshold, modify in `database_manager.py`:

```python
class DatabaseManager:
    # Knowledge status upgrade threshold
    KNOWLEDGE_CONFIRMATION_THRESHOLD = 3  # Default is 3, can be changed to 2, 4, etc.
```

### Recommended Values

| Threshold | Use Case |
|-----------|----------|
| 2 | Quick confirmation, suitable for testing or small-scale use |
| 3 | **Default**, balances accuracy and responsiveness |
| 4-5 | Strict mode, requires more evidence for confirmation |

## Best Practices

### 1. Knowledge Acquisition Strategy

- **Encourage clear user expressions**: Guide users to state information clearly
- **Regularly review suspected knowledge**: Ask users to confirm suspected information in conversations
- **Prioritize confirmed knowledge**: Prefer confirmed knowledge when generating responses

### 2. Data Quality Management

- Regularly check highly-mentioned but still "suspected" knowledge
- Manually mark important information as "confirmed" if needed
- Clean up suspected knowledge that hasn't been mentioned for a long time

## FAQ

### Q: How to manually mark knowledge as confirmed?

A: Update directly in the database:
```python
db.execute("UPDATE entity_related_info SET status='确认' WHERE uuid=?", (info_uuid,))
```

### Q: Will old data be lost?

A: No. All old data will be preserved and automatically set to "Suspected" status with mention_count=1.

## Changelog

### v2.0 (2024)
- ✨ Added knowledge status management system
- ✨ Extract knowledge only from user messages
- ✨ Automatic status upgrade mechanism
- ✨ Mention count tracking
- 🔧 Automatic database migration
- 🎨 GUI interface updates

## References

- [Architecture Documentation](./ARCHITECTURE.md)
- [API Documentation](./API.md)
- [Development Guide](./DEVELOPMENT.md)
