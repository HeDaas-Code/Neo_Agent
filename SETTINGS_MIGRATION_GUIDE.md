# 设定迁移功能使用指南

## 功能简介

设定迁移功能允许您快速导出和导入智能体的完整配置，包括：
- **.env 环境变量配置**：角色设定、API配置、模型参数等
- **数据库数据**：记忆、知识库、情感分析、环境描述等

这使得您可以：
- 🔄 在不同设备间迁移智能体
- 💾 备份智能体的完整状态
- 🚀 快速初始化新的智能体实例
- 🤝 分享预配置的智能体设定

## 使用方法

### 1. 导出设定

#### 步骤一：打开设定迁移界面
1. 启动 Neo Agent 主界面（运行 `python gui_enhanced.py`）
2. 点击顶部选项卡中的 **"📦 设定迁移"**
3. 默认显示 **"导出设定"** 标签页

#### 步骤二：选择导出内容
1. **包含 .env 配置文件**：勾选此项将导出所有环境变量设置
2. **选择数据类别**：
   - 点击 **"全选"** 按钮选择所有数据类别
   - 点击 **"取消全选"** 按钮清除所有选择
   - 或者手动勾选需要的数据类别：
     - ✅ **基础知识** (base_knowledge)：不可变的核心知识
     - ✅ **实体知识库** (entities)：从对话中提取的实体和定义
     - ✅ **短期记忆** (short_term_memory)：最近的对话记录
     - ✅ **长期记忆** (long_term_memory)：历史对话概括
     - ✅ **情感分析历史** (emotion_history)：情感关系分析记录
     - ✅ **环境描述** (environment_descriptions)：智能体视觉环境
     - ✅ **环境物体** (environment_objects)：环境中的物体
     - ✅ **环境连接** (environment_connections)：环境之间的连接
     - ✅ **智能体表达** (agent_expressions)：个性化表达方式
     - ✅ **用户表达习惯** (user_expression_habits)：学习的用户习惯
     - ✅ **视觉工具日志** (vision_tool_logs)：视觉工具使用记录
     - ✅ **元数据** (metadata)：系统元数据

#### 步骤三：执行导出
1. 点击 **"导出设定"** 按钮
2. 在弹出的文件保存对话框中选择保存位置和文件名
   - 默认文件名格式：`neo_agent_settings_YYYYMMDD_HHMMSS.json`
3. 等待导出完成，查看结果区域显示的导出统计信息

#### 导出结果示例
```
✓ 导出成功!

导出文件: /path/to/neo_agent_settings_20260130_123456.json

导出统计:
  - env_settings: 20 条
  - 基础知识: 2 条
  - 实体知识库: 5 条
  - 短期记忆: 40 条
  - 长期记忆: 3 条
  - 情感分析历史: 2 条
  - 环境描述: 1 条
  - 环境物体: 5 条
```

### 2. 导入设定

#### 步骤一：选择导入文件
1. 在设定迁移界面中，切换到 **"导入设定"** 标签页
2. 点击 **"浏览..."** 按钮，选择之前导出的 JSON 文件
3. 文件路径将显示在输入框中

#### 步骤二：预览导入内容（推荐）
1. 点击 **"预览导入内容"** 按钮
2. 在结果区域查看导入文件的详细信息：
   - 导出版本和时间
   - 原智能体名称
   - 环境变量数量
   - 各数据类别的记录数

#### 预览结果示例
```
=== 导入文件预览 ===

导出信息:
  版本: 1.0
  导出时间: 2026-01-30T12:34:56.789012
  智能体名称: 小可

环境变量: 20 项

数据类别:
  - 基础知识: 2 条
  - 实体知识库: 5 条
  - 短期记忆: 40 条
  - 长期记忆: 3 条
  - 情感分析历史: 2 条
```

#### 步骤三：配置导入选项
1. **导入 .env 配置文件**：勾选此项将导入环境变量设置
2. **覆盖现有数据**：
   - ⚠️ **谨慎使用**：勾选此项将删除现有数据后导入
   - 不勾选：将尝试保留现有数据，只添加新数据
3. **选择导入的数据类别**：可以只导入部分数据类别

#### 步骤四：执行导入
1. 点击 **"执行导入"** 按钮
2. 在确认对话框中确认操作
3. 等待导入完成，查看结果统计

#### 导入结果示例
```
✓ 导入成功!

原 .env 已备份到: .env.backup.20260130_123456

导入统计:
  - env_settings: 20 条
  - 基础知识: 2 条
  - 实体知识库: 5 条
  - 短期记忆: 40 条
  - 长期记忆: 3 条
```

### 3. 命令行使用（高级）

也可以通过 Python 代码直接使用设定迁移功能：

```python
from settings_migration import SettingsMigration
from database_manager import DatabaseManager

# 创建迁移管理器
db_manager = DatabaseManager()
migration = SettingsMigration(db_manager=db_manager)

# 导出设定
result = migration.export_settings(
    export_path="my_agent_backup",
    include_env=True,
    selected_categories=['base_knowledge', 'entities', 'short_term_memory']
)

if result['success']:
    print(f"导出成功: {result['exported_file']}")
    print(f"统计: {result['stats']}")

# 预览导入
preview = migration.preview_import("my_agent_backup.json")
if preview['success']:
    print(f"文件信息: {preview['export_info']}")
    print(f"数据类别: {preview['categories']}")

# 导入设定
result = migration.import_settings(
    import_path="my_agent_backup.json",
    import_env=True,
    import_database=True,
    overwrite=False,
    selected_categories=None  # None 表示全部导入
)

if result['success']:
    print(f"导入成功! 统计: {result['stats']}")
```

## 使用场景

### 场景一：在新电脑上部署智能体
1. 在原电脑上导出完整设定（包含 .env 和所有数据）
2. 将导出的 JSON 文件复制到新电脑
3. 在新电脑上安装 Neo Agent
4. 导入设定文件
5. 智能体立即可用，保留所有记忆和知识

### 场景二：备份智能体状态
- 定期导出完整设定作为备份
- 在重要对话或数据更新后及时备份
- 可以随时恢复到之前的状态

### 场景三：分享智能体配置
1. 导出智能体的角色设定和基础知识
2. 选择性导出，不包含个人对话记忆
3. 分享给他人快速创建相似的智能体

### 场景四：测试和开发
- 导出当前状态作为基准
- 在测试环境中导入进行实验
- 如有问题，可以快速恢复到基准状态

## 注意事项

### 数据安全
- ⚠️ 导出的 JSON 文件包含敏感信息（API密钥、对话记录等）
- 请妥善保管导出文件，不要分享给不信任的人
- 分享前建议删除敏感数据（如 API密钥）

### 覆盖选项
- ⚠️ "覆盖现有数据" 选项会删除现有数据，请谨慎使用
- 建议在覆盖前先备份当前数据
- 首次导入到新环境时可以安全使用覆盖选项

### 环境变量导入
- 导入 .env 配置时会自动备份原文件
- 备份文件名格式：`.env.backup.YYYYMMDD_HHMMSS`
- 如果导入的配置有问题，可以从备份恢复

### 版本兼容性
- 导出文件包含版本信息
- 目前版本：1.0
- 未来版本更新可能需要数据迁移

## 常见问题

### Q1: 导入后需要重启应用吗？
**A:** 如果导入了 .env 配置，需要重启应用以使新配置生效。如果只导入了数据库数据，可以直接使用。

### Q2: 可以只导入部分数据吗？
**A:** 可以。在导入时取消勾选不需要的数据类别即可。

### Q3: 导入会覆盖现有数据吗？
**A:** 取决于 "覆盖现有数据" 选项。不勾选时会尝试保留现有数据；勾选时会先删除再导入。

### Q4: 导出文件可以手动编辑吗？
**A:** 可以，导出的 JSON 文件是标准格式，可以用文本编辑器打开编辑。但请确保 JSON 格式正确。

### Q5: 不同版本的 Neo Agent 之间可以迁移吗？
**A:** 主版本相同时可以兼容。跨主版本迁移可能需要手动调整数据格式。

## 技术细节

### 导出文件结构
```json
{
  "export_info": {
    "version": "1.0",
    "exported_at": "2026-01-30T12:34:56.789012",
    "agent_name": "小可"
  },
  "env_settings": {
    "CHARACTER_NAME": "小可",
    "CHARACTER_GENDER": "女",
    "MODEL_NAME": "deepseek-ai/DeepSeek-V3",
    ...
  },
  "database_data": {
    "base_knowledge": [...],
    "entities": [...],
    "short_term_memory": [...],
    ...
  }
}
```

### 支持的数据表
- `base_knowledge`: 基础知识表
- `entities`: 实体表
- `entity_definitions`: 实体定义表
- `entity_related_info`: 实体相关信息表
- `short_term_memory`: 短期记忆表
- `long_term_memory`: 长期记忆表
- `emotion_history`: 情感分析历史表
- `environment_descriptions`: 环境描述表
- `environment_objects`: 环境物体表
- `environment_connections`: 环境连接表
- `environment_domains`: 环境域表
- `domain_environments`: 域环境关联表
- `agent_expressions`: 智能体表达表
- `user_expression_habits`: 用户表达习惯表
- `vision_tool_logs`: 视觉工具日志表
- `metadata`: 元数据表

## 相关文档

- [快速开始指南](docs/zh-cn/QUICKSTART.md)
- [开发指南](docs/zh-cn/DEVELOPMENT.md)
- [数据库管理文档](docs/zh-cn/DATABASE.md)
