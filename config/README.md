# LLM驱动AVG游戏配置文件说明

本项目采用模块化配置文件结构，将原有的单一`config.json`文件拆分为多个专门的配置文件，实现关注点分离和更好的可维护性。

## 配置文件概览

```
config/
├── index.json          # 主配置索引文件
├── model.json          # 模型配置
├── character.json      # 角色配置
├── knowledge.json      # 知识库配置
├── game.json          # 游戏逻辑配置
├── memory.json        # 内存数据库配置
└── README.md          # 本说明文件
```

## 配置文件详细说明

### 1. index.json - 主配置索引

**作用**: 定义所有配置文件的路径和依赖关系，作为配置系统的入口点。

```json
{
  "version": "1.0.0",
  "description": "LLM驱动AVG游戏配置文件索引",
  "config_files": {
    "model": {
      "path": "./config/model.json",
      "description": "模型配置：API密钥、模型名称、嵌入模型等",
      "required": true
    }
    // ... 其他配置文件
  },
  "environment_variables": {
    "DEEPSEEK_API_KEY": {
      "description": "DeepSeek API密钥，可覆盖model.json中的配置",
      "required": false
    }
  }
}
```

### 2. model.json - 模型配置

**作用**: 存储LLM模型和嵌入模型的相关配置。

```json
{
  "deepseek_api_key": "your-api-key-here",
  "api_base": "https://api.siliconflow.cn/v1",
  "model_name": "deepseek-ai/DeepSeek-R1-0528-Qwen3-8B",
  "embedding_model_name": "BAAI/bge-m3"
}
```

**配置项说明**:
- `deepseek_api_key`: DeepSeek API密钥，用于调用LLM服务
- `api_base`: API基础URL
- `model_name`: 使用的LLM模型名称
- `embedding_model_name`: 嵌入模型名称，用于向量化文本

### 3. character.json - 角色配置

**作用**: 定义游戏中的角色信息、性格特征和背景设定。

```json
{
  "name": "艾莉亚",
  "role": "星际飞船AI助手",
  "personality": {
    "traits": ["理性", "谨慎", "忠诚", "好奇"]
  },
  "background": "高级AI系统，负责飞船运行和船员安全",
  "current_status": "正常运行",
  "knowledge_level": 3
}
```

**配置项说明**:
- `name`: 角色名称
- `role`: 角色职业/身份
- `personality`: 性格特征，影响对话风格
- `background`: 角色背景故事
- `current_status`: 当前状态
- `knowledge_level`: 知识访问等级

### 4. knowledge.json - 知识库配置

**作用**: 定义游戏中的知识节点、访问权限和内容结构。

```json
{
  "knowledge_base": {
    "basic_ship_layout": {
      "content": "飞船基本布局信息",
      "access_level": 1,
      "category": "ship_info"
    }
    // ... 其他知识节点
  }
}
```

**配置项说明**:
- `knowledge_base`: 知识节点集合
- `content`: 知识内容描述
- `access_level`: 访问所需权限等级
- `category`: 知识分类

### 5. game.json - 游戏逻辑配置

**作用**: 定义游戏事件、位置、数据片段等游戏逻辑元素。

```json
{
  "events": {
    "system_alert": {
      "trigger_condition": "stress > 80",
      "description": "系统警报触发",
      "effects": ["increase_stress"]
    }
  },
  "locations": {
    "bridge": {
      "name": "舰桥",
      "access_level": 1,
      "description": "飞船指挥中心"
    }
  },
  "data_fragments": {
    "fragment_001": {
      "name": "导航日志",
      "unlock_condition": "permission_level >= 2"
    }
  }
}
```

**配置项说明**:
- `events`: 游戏事件定义
- `locations`: 游戏场景位置
- `data_fragments`: 数据片段，用于解锁新内容

### 6. memory.json - 内存数据库配置

**作用**: 配置向量数据库的存储路径和集合设置。

```json
{
  "memory_db_path": "./memory_db",
  "collection_name": "game_memories"
}
```

**配置项说明**:
- `memory_db_path`: ChromaDB数据库存储路径
- `collection_name`: 向量集合名称

## 环境变量配置

为了安全性，敏感信息可以通过环境变量设置：

```bash
# Windows
set DEEPSEEK_API_KEY=your-actual-api-key

# Linux/Mac
export DEEPSEEK_API_KEY=your-actual-api-key
```

环境变量会自动覆盖配置文件中的对应值。

## 安全注意事项

1. **API密钥安全**: 
   - 不要将真实的API密钥提交到版本控制系统
   - 使用环境变量或创建本地配置文件
   - 将包含敏感信息的文件添加到`.gitignore`

2. **配置文件权限**:
   - 确保配置文件具有适当的读取权限
   - 避免在生产环境中使用默认配置

## 配置验证

系统启动时会自动验证配置的完整性：

- 检查必需的配置文件是否存在
- 验证必需字段是否已设置
- 确保配置格式正确

如果验证失败，系统会输出详细的错误信息。

## 开发与生产环境

### 开发环境
- 可以使用默认配置进行快速开发
- API密钥可以设置为测试密钥
- 数据库路径可以指向本地目录

### 生产环境
- 必须设置真实的API密钥
- 配置适当的数据库存储路径
- 启用日志记录和监控

## 故障排除

### 常见问题

1. **配置文件未找到**
   - 检查文件路径是否正确
   - 确保所有必需的配置文件都存在

2. **API密钥无效**
   - 验证API密钥是否正确
   - 检查环境变量是否正确设置

3. **权限错误**
   - 确保应用程序有读取配置文件的权限
   - 检查文件系统权限设置

4. **JSON格式错误**
   - 使用JSON验证工具检查文件格式
   - 注意JSON语法要求（如尾随逗号问题）

### 调试模式

可以通过设置日志级别来获取更详细的配置加载信息：

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## 配置热重载

系统支持配置热重载，可以在运行时更新配置：

```python
from config_manager import config_manager

# 重新加载配置
config_manager.reload()
```

## 扩展配置

如需添加新的配置文件：

1. 在`config/`目录下创建新的JSON文件
2. 在`index.json`中添加对应的配置项
3. 更新`ConfigManager`类以支持新配置
4. 在相关模块中使用新配置

---

**注意**: 本配置系统向后兼容原有的`config.json`文件，如果检测到旧配置文件，系统会自动使用旧的加载方式。