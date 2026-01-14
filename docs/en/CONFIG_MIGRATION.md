# Agent Configuration Migration Guide

English | [简体中文](../zh-cn/CONFIG_MIGRATION.md)

This guide explains how to use the agent configuration migration feature to quickly export and import complete agent configurations.

## 📋 Overview

The agent configuration migration feature allows you to:

- **Export** current agent's complete configuration to a JSON file
- **Import** configuration files to a new agent instance
- **Migrate** agent settings to different environments or machines
- **Backup** important agent configurations to prevent data loss

### Configuration Contents

The exported configuration file includes:

1. **Environment Variables** (all settings from `.env` file)
   - API keys and URLs
   - Model configuration
   - Character settings
   - Memory settings
   - Other system parameters

2. **Environment Descriptions** (Agent vision system)
   - Detailed descriptions of all environments
   - Objects in environments
   - Connections between environments
   - Currently active environment

3. **Environment Domains** (Environment collections) ✨ NEW
   - Domain names and descriptions
   - Default environment settings
   - All environments in each domain
   - Domain-environment associations

4. **Base Knowledge**
   - All base facts
   - Knowledge categories and descriptions
   - Priority and confidence levels

5. **Agent Expression Styles**
   - Personalized expressions
   - Expression meanings and categories
   - Active status

## 🚀 Quick Start

### Export Configuration

1. Open Neo Agent GUI application
2. Find "System Settings" section in the right control panel
3. Click "📤 Export Agent Config" button
4. Select save location and filename
5. Click "Save" to complete export

Suggested file naming: `agent_config_YYYYMMDD_HHMMSS.json`

### Import Configuration

1. Open Neo Agent GUI application
2. Find "System Settings" section in the right control panel
3. Click "📥 Import Agent Config" button
4. Select the configuration file to import
5. Choose import mode:
   - **Overwrite Mode**: Overwrite existing configurations
   - **Append Mode**: Only add new configurations, keep existing ones
6. Click "Open" to start import
7. After import, it's recommended to click "♻️ Reload Agent" to apply new configuration

## 📖 Detailed Usage

### Export File Format

The exported JSON file structure:

```json
{
  "version": "1.0",
  "export_time": "2026-01-09T18:00:00.000000",
  "env_config": {
    "CHARACTER_NAME": "Neo",
    "CHARACTER_AGE": "18",
    "MODEL_NAME": "deepseek-ai/DeepSeek-V3",
    "TEMPERATURE": "0.8"
  },
  "environments": [
    {
      "name": "Classroom",
      "overall_description": "A bright classroom",
      "atmosphere": "Quiet and focused",
      "lighting": "Natural light",
      "sounds": "Occasional page turning",
      "smells": "Light scent of books",
      "is_active": 1,
      "objects": [
        {
          "name": "Blackboard",
          "description": "Blackboard at the front",
          "position": "Front wall",
          "priority": 90
        }
      ],
      "connections": []
    }
  ],
  "domains": [
    {
      "name": "Xiao Ke's Home",
      "description": "Xiao Ke's warm family environment",
      "default_environment_name": "Living Room",
      "environment_names": ["Living Room", "Bedroom", "Kitchen"]
    }
  ],
  "base_knowledge": [
    {
      "entity_name": "HeDaas",
      "content": "HeDaas is a university",
      "category": "Institution",
      "description": "School information",
      "immutable": true,
      "priority": 100,
      "confidence": 1.0
    }
  ],
  "agent_expressions": [
    {
      "expression": "wc",
      "meaning": "Express surprise",
      "category": "Exclamation",
      "is_active": true
    }
  ]
}
```

### Import Modes

#### Overwrite Mode (overwrite=True)

- Existing configurations will be replaced by new ones
- Suitable for completely replacing current configuration
- Immutable base knowledge won't be overwritten

#### Append Mode (overwrite=False)

- Existing configurations will be preserved
- Only add new configuration items
- Suitable for merging multiple configurations

### Environment Variables Handling

**Important Notice**: Since environment variable files may contain sensitive information (like API keys), the import uses the following strategy:

- **Overwrite Mode**: Environment variables are written to `.env` file (overwriting content but keeping comments)
- **Append Mode**: Environment variables are saved to `.env.new` file

If using append mode, you need to:

1. Check `.env.new` file content
2. Manually merge required configurations to `.env`
3. Delete or rename `.env.new` file

## 💡 Use Cases

### Scenario 1: Backup Current Configuration

Export configuration as backup before major changes:

```bash
# Export configuration
📤 Export Agent Config -> agent_config_backup_20260109.json
```

### Scenario 2: Migrate to New Machine

Migrate agent configuration to another machine:

```bash
# On old machine
📤 Export Agent Config -> agent_config.json

# Copy agent_config.json to new machine

# On new machine
📥 Import Agent Config -> Select agent_config.json
♻️ Reload Agent
```

### Scenario 3: Create Multiple Characters

Create different characters based on existing configuration:

```bash
# Export base configuration
📤 Export Agent Config -> base_config.json

# Edit character settings in JSON file (env_config section)
# For example, modify CHARACTER_NAME, CHARACTER_PERSONALITY, etc.

# Import modified configuration
📥 Import Agent Config -> Select modified file
♻️ Reload Agent
```

### Scenario 4: Share Configuration Template

Share your agent configuration with other users:

1. Export configuration file
2. **Remove sensitive information** (like API keys)
3. Share JSON file
4. Recipient imports and fills in their own API key

## ⚠️ Important Notes

### Data Security

- Exported configuration files may contain sensitive information (API keys, private conversations, etc.)
- Keep exported configuration files secure
- Always remove sensitive information before sharing

### Version Compatibility

- Current configuration format version: 1.0
- Version compatibility is checked during import
- Import will fail if versions are incompatible

### Immutable Knowledge

- Base knowledge marked as immutable cannot be overwritten during import
- To modify, manually delete and re-add

### Database Conflicts

- During import, if environment names, entity names, etc. already exist:
  - Overwrite mode: Update existing data
  - Append mode: Skip existing items

## 🔧 Programmatic Usage

Besides using the GUI, you can also use the configuration manager directly in code:

```python
from database_manager import DatabaseManager
from agent_config_manager import AgentConfigManager

# Create configuration manager
db = DatabaseManager()
config_manager = AgentConfigManager(db_manager=db, env_file=".env")

# Export configuration
config_manager.export_config("my_config.json")

# Import configuration
config_manager.import_config("my_config.json", overwrite=False)
```

### API Reference

#### `export_config(output_file: str) -> bool`

Export current configuration to file.

**Parameters:**
- `output_file`: Output file path

**Returns:**
- `True` - Export successful
- `False` - Export failed

#### `import_config(input_file: str, overwrite: bool = False) -> bool`

Import configuration from file.

**Parameters:**
- `input_file`: Input file path
- `overwrite`: Whether to overwrite existing configurations (default False)

**Returns:**
- `True` - Import successful
- `False` - Import failed

## 🐛 Troubleshooting

### Problem 1: Export Failed

**Possible Causes:**
- Insufficient file permissions
- Insufficient disk space
- Database connection failed

**Solutions:**
- Check write permissions of target directory
- Ensure sufficient disk space
- Check console logs for detailed error information

### Problem 2: Import Failed

**Possible Causes:**
- Configuration file format error
- Version incompatibility
- Database write failed

**Solutions:**
- Verify JSON file format is correct
- Check if configuration file version is supported
- Check console logs for detailed error information

### Problem 3: Environment Variables Not Taking Effect

**Possible Causes:**
- In append mode, environment variables saved to `.env.new`
- Agent not reloaded

**Solutions:**
- Check if `.env.new` file exists
- Manually merge environment variables to `.env`
- Click "♻️ Reload Agent" button

## 📚 Related Documentation

- [Quick Start Guide](QUICKSTART.md) - Learn basic usage
- [Development Guide](DEVELOPMENT.md) - Understand project structure
- [API Documentation](API.md) - View detailed API

## 🤝 Contributing

If you encounter problems or have suggestions for improvement, feel free to:

- Submit [Issue](https://github.com/HeDaas-Code/Neo_Agent/issues)
- Create [Pull Request](https://github.com/HeDaas-Code/Neo_Agent/pulls)
- Join [Discussions](https://github.com/HeDaas-Code/Neo_Agent/discussions)

---

Last Updated: 2026-01-09
