# NPS插件配置管理系统

本文档详细介绍NPS（Neo Plugin System）插件配置管理系统的完整功能和使用方法。

## 概述

NPS插件配置管理系统提供了一个可视化的GUI界面，允许用户轻松管理每个NPS插件的独立配置，包括API密钥、搜索引擎、时区等参数。

## 功能特性

### 1. 可视化配置界面

- **专业的表单设计**: 根据不同插件类型显示适配的配置界面
- **多种输入控件**: 文本框、密码框、下拉框、数字选择器、JSON编辑器
- **实时预览**: 配置修改实时显示
- **操作反馈**: 保存、导入、导出等操作都有明确的成功/失败提示

### 2. 安全特性

- **密码保护**: API Key等敏感字段显示为`***`，可切换显示/隐藏
- **环境变量引用**: 支持`${ENV_VAR}`格式，避免在配置文件中硬编码敏感信息
- **Git排除**: 实际配置文件（`plugins_config.json`）已添加到`.gitignore`
- **配置验证**: JSON格式检查，字段类型验证

### 3. 配置管理功能

- **保存配置**: 将配置保存到JSON文件
- **重置配置**: 一键恢复默认值
- **导出配置**: 导出当前配置到文件（用于备份或分享）
- **导入配置**: 从文件导入配置
- **启用/禁用**: 快速切换插件状态

## 核心组件

### 1. NPSConfigManager (`src/nps/nps_config_manager.py`)

配置管理器类，负责配置的读取、写入、验证和管理。

**主要方法**:
- `get_plugin_config(tool_id)`: 获取插件配置
- `set_plugin_config(tool_id, config)`: 设置插件配置
- `update_plugin_config(tool_id, updates)`: 更新部分配置
- `get_config_value(tool_id, key, default)`: 获取单个配置值（支持环境变量）
- `export_config(tool_id, output_file)`: 导出配置
- `import_config(tool_id, input_file)`: 导入配置

### 2. NPSPluginConfigDialog (`src/gui/nps_config_dialog.py`)

可视化配置对话框，提供用户友好的配置界面。

**支持的插件类型**:
- **websearch**: 网络搜索配置（API Key、引擎、结果数、语言）
- **systime**: 系统时间配置（时区、时间格式）
- **通用**: JSON编辑器（用于未知插件）

**界面组件**:
- 工具信息显示（名称、ID、版本）
- 配置字段（根据插件类型自动生成）
- 启用/禁用开关
- 操作按钮（保存、取消、重置、导入、导出）

### 3. NPS GUI集成 (`src/gui/nps_gui.py`)

在现有的NPS管理GUI中集成配置功能。

**新增功能**:
- 工具栏添加"⚙️ 高级配置"按钮
- 右键菜单添加"⚙️ 高级配置"选项
- 配置管理器初始化
- 配置更新后自动刷新工具列表

## 使用方法

### 方式1：通过GUI配置（推荐）

1. 打开Neo Agent主界面
2. 切换到"NPS工具管理"标签页
3. 在工具列表中选择要配置的插件
4. 点击工具栏的"⚙️ 高级配置"按钮，或右键点击工具选择"⚙️ 高级配置"
5. 在弹出的配置对话框中编辑配置
6. 点击"💾 保存"按钮保存配置

### 方式2：直接编辑配置文件

1. 复制配置模板：
   ```bash
   cp configs/nps_plugins/plugins_config.json.example \
      configs/nps_plugins/plugins_config.json
   ```

2. 编辑配置文件：
   ```bash
   vim configs/nps_plugins/plugins_config.json
   ```

3. 重启应用或刷新NPS工具管理界面

## 配置文件格式

配置文件采用JSON格式，每个插件作为一个顶级键：

```json
{
    "websearch": {
        "api_key": "${SERPAPI_API_KEY}",
        "engine": "google",
        "num_results": 5,
        "language": "zh-cn",
        "enabled": true
    },
    "systime": {
        "timezone": "Asia/Shanghai",
        "format": "%Y-%m-%d %H:%M:%S",
        "enabled": true
    }
}
```

## 插件配置说明

### websearch（网络搜索）

| 配置项 | 类型 | 说明 | 默认值 | 可选值 |
|--------|------|------|--------|--------|
| api_key | string | SerpAPI密钥 | `${SERPAPI_API_KEY}` | API密钥或环境变量 |
| engine | string | 搜索引擎 | google | google, bing, yahoo |
| num_results | int | 返回结果数 | 5 | 1-20 |
| language | string | 搜索语言 | zh-cn | zh-cn, en, ja, ko等 |
| enabled | boolean | 是否启用 | true | true, false |

**示例配置**:
```json
{
    "websearch": {
        "api_key": "${SERPAPI_API_KEY}",
        "engine": "google",
        "num_results": 5,
        "language": "zh-cn",
        "enabled": true
    }
}
```

### systime（系统时间）

| 配置项 | 类型 | 说明 | 默认值 | 可选值 |
|--------|------|------|--------|--------|
| timezone | string | 时区 | Asia/Shanghai | 任何有效的时区 |
| format | string | 时间格式 | %Y-%m-%d %H:%M:%S | Python strftime格式 |
| enabled | boolean | 是否启用 | true | true, false |

**示例配置**:
```json
{
    "systime": {
        "timezone": "Asia/Shanghai",
        "format": "%Y-%m-%d %H:%M:%S",
        "enabled": true
    }
}
```

**时间格式说明**:
- `%Y`: 四位年份（2024）
- `%m`: 两位月份（01-12）
- `%d`: 两位日期（01-31）
- `%H`: 24小时制小时（00-23）
- `%M`: 分钟（00-59）
- `%S`: 秒（00-59）
- `%A`: 星期全称（Monday）
- `%a`: 星期简称（Mon）

## 环境变量使用

### 为什么使用环境变量？

1. **安全性**: API密钥等敏感信息不会被提交到版本控制系统
2. **灵活性**: 不同环境（开发/测试/生产）可以使用不同的配置
3. **便捷性**: 集中管理所有环境相关的配置

### 使用方法

1. 在`.env`文件中设置环境变量：
   ```bash
   SERPAPI_API_KEY=your-api-key-here
   ```

2. 在配置文件中引用：
   ```json
   {
       "api_key": "${SERPAPI_API_KEY}"
   }
   ```

3. 系统会自动从环境变量中读取实际值

### 支持的格式

- `${VAR_NAME}`: 从环境变量读取
- `actual_value`: 直接使用配置值

**注意**: 如果环境变量不存在，系统会使用配置中的默认值（如果有）。

## 配置文件位置

- **开发环境**: `configs/nps_plugins/plugins_config.json`
- **配置模板**: `configs/nps_plugins/plugins_config.json.example`
- **文档**: `configs/nps_plugins/README.md`

## 文件权限和安全

### .gitignore配置

实际配置文件已添加到`.gitignore`：
```
# NPS插件配置（可能包含API keys）
configs/nps_plugins/plugins_config.json
# 但允许示例文件和文档
!configs/nps_plugins/*.example
!configs/nps_plugins/README.md
```

### 文件权限建议

生产环境中，建议设置适当的文件权限：
```bash
chmod 600 configs/nps_plugins/plugins_config.json
```

## 配置验证

系统会自动验证配置：

1. **JSON格式验证**: 确保配置文件是有效的JSON
2. **必需字段检查**: 某些插件可能有必需的配置项
3. **类型验证**: 确保配置值的类型正确
4. **范围验证**: 数值类型的配置会检查是否在有效范围内

如果验证失败，系统会显示具体的错误信息。

## 配置导入/导出

### 导出配置

1. 在NPS管理界面选择工具
2. 点击"⚙️ 高级配置"
3. 在配置对话框中点击"📤 导出"
4. 选择保存位置和文件名
5. 配置将保存为JSON文件

### 导入配置

1. 在NPS管理界面选择工具
2. 点击"⚙️ 高级配置"
3. 在配置对话框中点击"📥 导入"
4. 选择要导入的JSON文件
5. 配置将被加载并显示在界面上
6. 点击"💾 保存"应用配置

## 扩展开发

### 添加新插件的配置界面

1. 在`nps_config_dialog.py`中创建配置字段方法：

```python
def create_newplugin_fields(self):
    """创建新插件的配置字段"""
    row = 0
    
    # 配置项1
    ttk.Label(self.config_frame, text="配置项1:",
             font=("微软雅黑", 10, "bold")).grid(
        row=row, column=0, sticky=tk.W, padx=5, pady=5)
    
    var1 = tk.StringVar(value=self.current_config.get('key1', 'default1'))
    entry1 = ttk.Entry(self.config_frame, textvariable=var1, width=40)
    entry1.grid(row=row, column=1, sticky=tk.EW, padx=5, pady=5)
    self.config_widgets['key1'] = var1
    row += 1
    
    # 配置项2
    # ...
    
    # 配置列权重
    self.config_frame.columnconfigure(1, weight=1)
```

2. 在`create_config_fields()`中添加判断：

```python
def create_config_fields(self):
    if self.tool.tool_id == 'websearch':
        self.create_websearch_fields()
    elif self.tool.tool_id == 'systime':
        self.create_systime_fields()
    elif self.tool.tool_id == 'newplugin':  # 新增
        self.create_newplugin_fields()
    else:
        self.create_generic_fields()
    
    self.create_enabled_field()
```

3. 更新配置模板添加默认配置：

```json
{
    "newplugin": {
        "key1": "value1",
        "key2": "value2",
        "enabled": true
    }
}
```

### 可用的输入控件

**文本框**:
```python
var = tk.StringVar(value='default')
entry = ttk.Entry(frame, textvariable=var, width=40)
```

**密码框**:
```python
var = tk.StringVar()
entry = ttk.Entry(frame, textvariable=var, show="*", width=40)
```

**下拉框**:
```python
var = tk.StringVar(value='option1')
combo = ttk.Combobox(frame, textvariable=var,
                     values=['option1', 'option2', 'option3'],
                     width=37, state='readonly')
```

**数字选择器**:
```python
var = tk.IntVar(value=5)
spin = ttk.Spinbox(frame, from_=1, to=20,
                   textvariable=var, width=37)
```

**复选框**:
```python
var = tk.BooleanVar(value=True)
check = ttk.Checkbutton(frame, text="启用",
                       variable=var)
```

**文本编辑器**:
```python
text = scrolledtext.ScrolledText(frame, height=10, width=50)
```

## 故障排除

### 配置不生效

1. 检查配置文件格式是否正确（JSON有效性）
2. 检查环境变量是否正确设置
3. 尝试重启应用
4. 检查debug.log中的错误信息

### 环境变量无法读取

1. 确认`.env`文件存在并包含相应的变量
2. 确认变量名拼写正确（区分大小写）
3. 重启应用以重新加载环境变量

### API Key显示为环境变量引用

这是正常的！配置中保存的是`${SERPAPI_API_KEY}`，实际使用时系统会自动从环境变量中读取真实值。

### 配置丢失

1. 检查`configs/nps_plugins/plugins_config.json`文件是否存在
2. 如果丢失，可以从`.example`文件恢复
3. 使用"📥 导入"功能恢复之前导出的备份

## 最佳实践

### 1. 使用环境变量管理敏感信息

✅ **推荐**:
```json
{
    "api_key": "${SERPAPI_API_KEY}"
}
```

❌ **不推荐**:
```json
{
    "api_key": "sk-xxx123xxx456xxx"
}
```

### 2. 定期备份配置

使用"📤 导出"功能定期导出配置文件进行备份。

### 3. 版本控制

- 提交`.example`文件到版本控制
- 不要提交实际的配置文件
- 在README中说明如何从example创建配置

### 4. 配置文档化

在项目README中说明：
- 需要哪些环境变量
- 如何获取API密钥
- 配置示例和说明

### 5. 权限管理

生产环境中限制配置文件的访问权限：
```bash
chmod 600 configs/nps_plugins/plugins_config.json
chown app_user:app_group configs/nps_plugins/plugins_config.json
```

## 技术细节

### 配置加载顺序

1. 尝试从`plugins_config.json`加载
2. 如果文件不存在，使用空配置
3. 获取配置值时，检查是否为环境变量引用
4. 如果是环境变量（`${VAR}`格式），从环境中读取
5. 如果环境变量不存在，使用默认值

### 配置保存机制

1. 收集界面上所有配置项的值
2. 构建配置字典
3. 验证配置格式和类型
4. 写入JSON文件（使用`indent=4`格式化）
5. 更新工具的enabled状态
6. 刷新工具列表

### 错误处理

所有操作都包含完整的异常处理：
- JSON解析错误
- 文件读写错误
- 配置验证错误
- 环境变量读取错误

错误会：
1. 记录到debug.log
2. 显示用户友好的错误对话框
3. 不影响其他功能的正常运行

## 相关文档

- `configs/nps_plugins/README.md` - 配置目录的详细说明
- `docs/NPS_WEB_SEARCH_AND_INTEGRATION.md` - NPS网络搜索和智能体集成
- `src/nps/README.md` - NPS系统总体说明（如果存在）

## 更新历史

- **2024-XX-XX**: 初始版本，支持websearch和systime配置
- **后续**: 将根据新增插件持续更新

## 反馈和贡献

如果您有任何问题、建议或希望添加新的配置选项，请：
1. 提交Issue
2. 提交Pull Request
3. 联系维护者

---

**维护者**: Neo Agent开发团队
**最后更新**: 2024
