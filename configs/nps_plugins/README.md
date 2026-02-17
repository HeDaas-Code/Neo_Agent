# NPS插件配置说明

本目录用于存储NPS（Neo Plugin System）插件的独立配置。

## 配置文件

- `plugins_config.json`: 实际使用的配置文件（不会被提交到git）
- `plugins_config.json.example`: 配置文件模板

## 使用方法

1. 复制模板文件创建配置文件：
   ```bash
   cp plugins_config.json.example plugins_config.json
   ```

2. 编辑 `plugins_config.json` 填入你的配置

3. 或者使用GUI界面：
   - 打开Neo Agent GUI
   - 进入"NPS工具管理"标签页
   - 选择一个工具，点击"⚙️ 高级配置"按钮
   - 在弹出的对话框中配置插件参数

## 配置项说明

### websearch（网络搜索）

```json
{
    "api_key": "${SERPAPI_API_KEY}",  // SerpAPI密钥，可使用环境变量
    "engine": "google",                // 搜索引擎：google, bing, yahoo
    "num_results": 5,                  // 返回结果数量（1-20）
    "language": "zh-cn",               // 搜索语言：zh-cn, en, ja, ko等
    "enabled": true                    // 是否启用此插件
}
```

### systime（系统时间）

```json
{
    "timezone": "Asia/Shanghai",       // 时区
    "format": "%Y-%m-%d %H:%M:%S",     // 时间格式
    "enabled": true                    // 是否启用此插件
}
```

## 环境变量

配置值可以使用 `${ENV_VAR}` 格式引用环境变量。

例如：
```json
{
    "api_key": "${SERPAPI_API_KEY}"
}
```

系统会自动从环境变量 `SERPAPI_API_KEY` 读取实际的API密钥。

## 安全提示

⚠️ **重要**: 
- 不要将包含敏感信息（如API keys）的配置文件提交到版本控制系统
- 使用环境变量来管理敏感配置
- `plugins_config.json` 已被添加到 `.gitignore`

## 配置导入/导出

在GUI中，你可以：
- 点击"📤 导出"按钮导出当前配置到文件
- 点击"📥 导入"按钮从文件导入配置
- 点击"🔄 重置"按钮恢复默认配置

## 配置文件位置

- 开发环境：`configs/nps_plugins/plugins_config.json`
- 生产环境：根据部署配置可能有所不同
