# 知识提取状态管理系统

## 概述

知识提取状态管理系统是对智能体知识库功能的重要改进，实现了更智能的知识收集和确认机制。系统现在能够区分"疑似"知识和"确认"知识，通过跟踪信息被提及的次数来自动提升知识的可信度。

## 核心特性

### 1. 只从用户消息中提取知识

系统现在**只从用户的陈述中提取信息**，不再从助手的回复中提取。这确保了知识库中的信息来源于用户的真实表达，而不是AI的推测或回应。

**实现细节：**
- `extract_knowledge` 方法现在会过滤消息列表，只保留 `role='user'` 的消息
- 提取提示词强调"只提取用户明确陈述的信息"

### 2. 知识状态管理

每条相关信息都有一个状态标记：

| 状态 | 说明 | 触发条件 |
|-----|------|---------|
| 疑似 | 首次提及，需要进一步确认 | 信息首次被提取 |
| 确认 | 多次提及，高可信度 | 相同信息被提及≥3次 |

### 3. 提及次数跟踪

系统会跟踪每条信息被提及的次数：
- **mention_count**: 记录信息被提到的总次数
- **last_mentioned_at**: 记录最后一次提及的时间戳

### 4. 自动状态升级

当相同信息被多次提及时：
1. 第1次提及：创建新知识项，状态为"疑似"，mention_count=1
2. 第2次提及：增加mention_count到2，状态仍为"疑似"
3. 第3次提及：增加mention_count到3，**状态自动升级为"确认"**

**配置：**
- 升级阈值通过 `DatabaseManager.KNOWLEDGE_CONFIRMATION_THRESHOLD` 配置
- 默认值为3，可根据需要调整

## 数据库结构

### entity_related_info 表新增字段

```sql
CREATE TABLE entity_related_info (
    uuid TEXT PRIMARY KEY,
    entity_uuid TEXT NOT NULL,
    content TEXT NOT NULL,
    type TEXT DEFAULT '其他',
    source TEXT,
    confidence REAL DEFAULT 0.7,
    status TEXT DEFAULT '疑似',           -- 新增：状态字段
    mention_count INTEGER DEFAULT 1,      -- 新增：提及次数
    last_mentioned_at TEXT,               -- 新增：最后提及时间
    created_at TEXT NOT NULL,
    FOREIGN KEY (entity_uuid) REFERENCES entities(uuid) ON DELETE CASCADE
)
```

## 使用示例

### 场景示例

**第1轮对话：**
```
用户: 我喜欢打篮球
系统: [提取知识] "我" -> "喜欢打篮球" [疑似×1]
```

**第2轮对话：**
```
用户: 我经常打篮球
系统: [更新知识] "我" -> "喜欢打篮球" [疑似×2]
```

**第3轮对话：**
```
用户: 打篮球是我的爱好
系统: [升级状态] "我" -> "喜欢打篮球" [✓确认]
```

### 代码示例

```python
from database_manager import DatabaseManager

db = DatabaseManager()

# 添加新知识（默认为疑似状态）
entity_uuid = db.find_or_create_entity("张三")
info_uuid = db.add_entity_related_info(
    entity_uuid=entity_uuid,
    content="喜欢编程",
    type_="个人偏好",
    status="疑似"  # 可省略，默认为"疑似"
)

# 重复添加相同内容（自动增加mention_count）
info_uuid = db.add_entity_related_info(
    entity_uuid=entity_uuid,
    content="喜欢编程",  # 相同内容
    type_="个人偏好",
    status="疑似"
)
# 此时 mention_count=2，状态仍为"疑似"

# 第三次添加（自动升级为确认）
info_uuid = db.add_entity_related_info(
    entity_uuid=entity_uuid,
    content="喜欢编程",  # 相同内容
    type_="个人偏好",
    status="疑似"
)
# 此时 mention_count=3，状态自动升级为"确认"
```

## GUI界面更新

### 知识库显示

在GUI的知识库标签页中，相关信息现在会显示：

```
  • [个人偏好] ✓ 确认 (置信度: 0.80)
     喜欢编程
     时间: 2024-01-01 10:30:00 | UUID: xxx...

  • [兴趣爱好] ? 疑似 (提及×2) (置信度: 0.75)
     喜欢旅游
     时间: 2024-01-01 11:00:00 | UUID: xxx...
```

### 统计信息

知识库统计面板新增状态分布：

```
知识状态: 确认 15 条 | 疑似 8 条
```

## 数据库迁移

### 自动迁移

系统在初始化时会自动检测并迁移旧数据库：

1. 检查 `entity_related_info` 表是否有新字段
2. 如果缺少字段，自动执行 `ALTER TABLE` 添加
3. 为已存在的旧数据设置默认值：
   - `status = '疑似'`
   - `mention_count = 1`
   - `last_mentioned_at = NULL`

### 向后兼容性

- ✅ 完全兼容旧版本数据库
- ✅ 不影响已有数据
- ✅ 自动设置合理的默认值
- ✅ 不需要手动操作

## 配置选项

### 调整确认阈值

如果您想要调整状态升级的阈值，可以在 `database_manager.py` 中修改：

```python
class DatabaseManager:
    # 知识状态升级阈值：当提及次数达到此值时，状态从"疑似"升级为"确认"
    KNOWLEDGE_CONFIRMATION_THRESHOLD = 3  # 默认为3，可改为2、4或其他值
```

### 建议值

| 阈值 | 适用场景 |
|-----|---------|
| 2 | 快速确认，适合测试或小规模使用 |
| 3 | **默认值**，平衡准确性和响应速度 |
| 4-5 | 严格模式，需要更多证据才确认 |

## 最佳实践

### 1. 知识获取策略

- **鼓励用户明确表达**：引导用户清楚地陈述信息
- **定期回顾疑似知识**：可以在对话中询问用户以确认疑似信息
- **优先使用确认知识**：在生成回复时优先参考确认状态的知识

### 2. 数据质量管理

- 定期检查提及次数较高但仍为"疑似"的知识
- 对于重要信息，可以手动将状态标记为"确认"
- 清理长期未被提及的疑似知识

### 3. 性能优化

- 系统已实现重复信息检测，避免重复存储
- 优先级排序：确认知识 > 疑似知识
- 在检索时优先返回确认状态的知识

## 技术实现细节

### 重复检测机制

```python
# 精确匹配：content、type、entity_uuid 三者完全相同
cursor.execute('''
    SELECT uuid, mention_count, status FROM entity_related_info 
    WHERE entity_uuid = ? AND content = ? AND type = ?
''', (entity_uuid, content, type_))
```

### 状态升级逻辑

```python
new_mention_count = existing_mention_count + 1
if new_mention_count >= KNOWLEDGE_CONFIRMATION_THRESHOLD:
    new_status = "确认"
else:
    new_status = existing_status  # 保持原状态
```

### 排序优先级

在知识检索时的排序规则：
1. **基础知识**（优先级100，最高）
2. **定义**（高置信度）
3. **确认状态的相关信息**（可信度高）
4. **疑似状态的相关信息**（按时间倒序）

## 常见问题

### Q: 如何手动将某条知识标记为确认？

A: 可以直接在数据库中更新：
```python
db.execute("UPDATE entity_related_info SET status='确认' WHERE uuid=?", (info_uuid,))
```

### Q: 如果用户表达的内容有细微差异，会被识别为重复吗？

A: 当前实现使用精确字符串匹配。如果内容有差异，会被视为不同的信息。未来可能增加语义相似度检测。

### Q: 疑似状态的知识会被用于回复生成吗？

A: 会，但优先级低于确认状态的知识。系统在检索时会优先返回确认状态的信息。

### Q: 旧数据会丢失吗？

A: 不会。所有旧数据都会保留，并自动设置为"疑似"状态，提及次数为1。

## 更新日志

### v2.0 (2024)
- ✨ 新增知识状态管理系统
- ✨ 只从用户消息中提取知识
- ✨ 自动状态升级机制
- ✨ 提及次数跟踪
- 🔧 数据库自动迁移
- 🎨 GUI界面更新

## 参考

- [架构文档](./ARCHITECTURE.md)
- [API文档](./API.md)
- [开发指南](./DEVELOPMENT.md)
