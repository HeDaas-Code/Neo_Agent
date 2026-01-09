# 智能体配置迁移指南

[English](../en/CONFIG_MIGRATION.md) | 简体中文

本指南介绍如何使用智能体配置迁移功能，快速导出和导入智能体的完整配置。

## 📋 功能概述

智能体配置迁移功能允许你：

- **导出**当前智能体的完整配置到 JSON 文件
- **导入**配置文件到新的智能体实例
- **迁移**智能体设定到不同的环境或机器
- **备份**重要的智能体配置以防数据丢失

### 包含的配置内容

导出的配置文件包含以下内容：

1. **环境变量** (`.env` 文件中的所有配置)
   - API 密钥和地址
   - 模型配置
   - 角色设定
   - 记忆设置
   - 其他系统参数

2. **环境描述** (智能体视觉系统)
   - 所有环境的详细描述
   - 环境中的物体信息
   - 环境之间的连接关系
   - 当前激活的环境

3. **基础知识库**
   - 所有基础事实
   - 知识分类和描述
   - 优先级和置信度

4. **智能体表达风格**
   - 个性化表达方式
   - 表达含义和分类
   - 激活状态

## 🚀 快速开始

### 导出配置

1. 打开 Neo Agent GUI 应用
2. 在右侧控制面板找到"系统设置"部分
3. 点击"📤 导出智能体配置"按钮
4. 选择保存位置和文件名
5. 点击"保存"完成导出

导出的文件命名建议：`agent_config_YYYYMMDD_HHMMSS.json`

### 导入配置

1. 打开 Neo Agent GUI 应用
2. 在右侧控制面板找到"系统设置"部分
3. 点击"📥 导入智能体配置"按钮
4. 选择要导入的配置文件
5. 选择导入模式：
   - **覆盖模式**：覆盖已存在的配置项
   - **追加模式**：只添加新配置，保留已存在的配置
6. 点击"打开"开始导入
7. 导入完成后，建议点击"♻️ 重新加载代理"以应用新配置

## 📖 详细使用说明

### 导出配置文件格式

导出的 JSON 文件结构如下：

```json
{
  "version": "1.0",
  "export_time": "2026-01-09T18:00:00.000000",
  "env_config": {
    "CHARACTER_NAME": "小可",
    "CHARACTER_AGE": "18",
    "MODEL_NAME": "deepseek-ai/DeepSeek-V3",
    "TEMPERATURE": "0.8"
  },
  "environments": [
    {
      "name": "教室",
      "overall_description": "一个明亮的教室",
      "atmosphere": "安静专注",
      "lighting": "自然光充足",
      "sounds": "偶尔有翻书声",
      "smells": "淡淡的书香",
      "is_active": 1,
      "objects": [
        {
          "name": "黑板",
          "description": "教室前方的黑板",
          "position": "前方墙壁",
          "priority": 90
        }
      ],
      "connections": []
    }
  ],
  "base_knowledge": [
    {
      "entity_name": "HeDaas",
      "content": "HeDaas是一所高校",
      "category": "机构",
      "description": "学校信息",
      "immutable": true,
      "priority": 100,
      "confidence": 1.0
    }
  ],
  "agent_expressions": [
    {
      "expression": "wc",
      "meaning": "表示惊讶",
      "category": "感叹",
      "is_active": true
    }
  ]
}
```

### 导入模式说明

#### 覆盖模式 (overwrite=True)

- 已存在的配置项会被新配置覆盖
- 适用于完全替换现有配置的场景
- 不可变的基础知识不会被覆盖

#### 追加模式 (overwrite=False)

- 已存在的配置项会被保留
- 只添加新的配置项
- 适用于合并多个配置的场景

### 环境变量处理

**重要提示**：由于环境变量文件可能包含敏感信息（如 API 密钥），导入时会采取以下策略：

- **覆盖模式**：环境变量会被写入到 `.env` 文件（覆盖原有内容，但保留注释）
- **追加模式**：环境变量会被保存到 `.env.new` 文件

如果是追加模式，你需要：

1. 检查 `.env.new` 文件内容
2. 手动合并需要的配置到 `.env`
3. 删除或重命名 `.env.new` 文件

## 💡 使用场景

### 场景1：备份当前配置

在进行重大修改前，导出配置作为备份：

```bash
# 导出配置
📤 导出智能体配置 -> agent_config_backup_20260109.json
```

### 场景2：迁移到新机器

将智能体配置迁移到另一台机器：

```bash
# 在旧机器上
📤 导出智能体配置 -> agent_config.json

# 将 agent_config.json 复制到新机器

# 在新机器上
📥 导入智能体配置 -> 选择 agent_config.json
♻️ 重新加载代理
```

### 场景3：创建多个角色

基于现有配置创建不同的角色：

```bash
# 导出基础配置
📤 导出智能体配置 -> base_config.json

# 修改 JSON 文件中的角色设定（env_config 部分）
# 例如修改 CHARACTER_NAME, CHARACTER_PERSONALITY 等

# 导入修改后的配置
📥 导入智能体配置 -> 选择修改后的文件
♻️ 重新加载代理
```

### 场景4：共享配置模板

分享你的智能体配置给其他用户：

1. 导出配置文件
2. **删除敏感信息**（如 API 密钥）
3. 分享 JSON 文件
4. 接收者导入并填入自己的 API 密钥

## ⚠️ 注意事项

### 数据安全

- 导出的配置文件可能包含敏感信息（API 密钥、私密对话等）
- 请妥善保管导出的配置文件
- 分享前务必删除敏感信息

### 版本兼容性

- 当前配置格式版本：1.0
- 导入时会检查版本兼容性
- 如果版本不兼容，导入会失败

### 不可变知识

- 标记为不可变（immutable）的基础知识无法被导入覆盖
- 如需修改，请手动删除后重新添加

### 数据库冲突

- 导入时如果环境名称、实体名称等已存在：
  - 覆盖模式：更新现有数据
  - 追加模式：跳过已存在的项

## 🔧 编程方式使用

除了通过 GUI，你也可以通过代码直接使用配置管理器：

```python
from database_manager import DatabaseManager
from agent_config_manager import AgentConfigManager

# 创建配置管理器
db = DatabaseManager()
config_manager = AgentConfigManager(db_manager=db, env_file=".env")

# 导出配置
config_manager.export_config("my_config.json")

# 导入配置
config_manager.import_config("my_config.json", overwrite=False)
```

### API 参考

#### `export_config(output_file: str) -> bool`

导出当前配置到文件。

**参数：**
- `output_file`: 输出文件路径

**返回值：**
- `True` - 导出成功
- `False` - 导出失败

#### `import_config(input_file: str, overwrite: bool = False) -> bool`

从文件导入配置。

**参数：**
- `input_file`: 输入文件路径
- `overwrite`: 是否覆盖现有配置（默认 False）

**返回值：**
- `True` - 导入成功
- `False` - 导入失败

## 🐛 故障排除

### 问题1：导出失败

**可能原因：**
- 文件权限不足
- 磁盘空间不足
- 数据库连接失败

**解决方案：**
- 检查目标目录的写入权限
- 确保有足够的磁盘空间
- 查看控制台日志获取详细错误信息

### 问题2：导入失败

**可能原因：**
- 配置文件格式错误
- 版本不兼容
- 数据库写入失败

**解决方案：**
- 验证 JSON 文件格式是否正确
- 检查配置文件版本是否支持
- 查看控制台日志获取详细错误信息

### 问题3：环境变量未生效

**可能原因：**
- 追加模式下环境变量保存在 `.env.new`
- 未重新加载代理

**解决方案：**
- 检查是否存在 `.env.new` 文件
- 手动合并环境变量到 `.env`
- 点击"♻️ 重新加载代理"按钮

## 📚 相关文档

- [快速开始指南](QUICKSTART.md) - 了解基本使用
- [开发指南](DEVELOPMENT.md) - 了解项目结构
- [API 文档](API.md) - 查看详细 API

## 🤝 贡献

如果你在使用过程中遇到问题或有改进建议，欢迎：

- 提交 [Issue](https://github.com/HeDaas-Code/Neo_Agent/issues)
- 发起 [Pull Request](https://github.com/HeDaas-Code/Neo_Agent/pulls)
- 参与 [讨论](https://github.com/HeDaas-Code/Neo_Agent/discussions)

---

最后更新：2026-01-09
