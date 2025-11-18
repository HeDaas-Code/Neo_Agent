# 贡献指南

**中文** | [English](CONTRIBUTING_EN.md)

感谢您对 Neo_Agent 项目的关注！我们欢迎所有形式的贡献，包括但不限于：

- 🐛 报告错误
- 💡 提出新功能建议
- 📝 改进文档
- 🔧 提交代码修复
- ⭐ 添加新功能

## 📋 目录

- [行为准则](#行为准则)
- [如何贡献](#如何贡献)
- [开发流程](#开发流程)
- [代码规范](#代码规范)
- [提交规范](#提交规范)
- [测试要求](#测试要求)

## 行为准则

参与本项目，请遵守以下准则：

- 尊重所有贡献者
- 使用包容性的语言
- 接受建设性的批评
- 专注于对社区最有利的事情
- 对其他社区成员表现出同理心

## 如何贡献

### 报告问题

如果您发现了 bug 或有功能建议：

1. 首先在 [Issues](https://github.com/HeDaas-Code/Neo_Agent/issues) 中搜索是否已有类似问题
2. 如果没有，创建新的 issue，并提供以下信息：
   - **Bug 报告**：
     - 问题描述
     - 重现步骤
     - 预期行为
     - 实际行为
     - 运行环境（Python版本、操作系统等）
     - 错误日志（如有）
   - **功能建议**：
     - 功能描述
     - 使用场景
     - 预期效果

### 提交代码

1. **Fork 项目**
   ```bash
   # 在GitHub上点击Fork按钮
   ```

2. **克隆您的 Fork**
   ```bash
   git clone https://github.com/YOUR_USERNAME/Neo_Agent.git
   cd Neo_Agent
   ```

3. **创建功能分支**
   ```bash
   git checkout -b feature/your-feature-name
   # 或
   git checkout -b fix/your-bug-fix
   ```

4. **进行修改**
   - 遵循代码规范
   - 添加必要的注释
   - 更新相关文档

5. **测试您的修改**
   ```bash
   # 运行测试（如果有）
   python -m pytest
   
   # 手动测试
   python gui_enhanced.py
   ```

6. **提交修改**
   ```bash
   git add .
   git commit -m "feat: 添加新功能"
   # 或
   git commit -m "fix: 修复某个问题"
   ```

7. **推送到您的 Fork**
   ```bash
   git push origin feature/your-feature-name
   ```

8. **创建 Pull Request**
   - 在GitHub上打开您的 Fork
   - 点击 "New Pull Request"
   - 填写 PR 描述，说明您的修改
   - 等待维护者审核

## 开发流程

### 环境设置

1. **安装依赖**
   ```bash
   pip install -r requirements.txt
   ```

2. **配置环境变量**
   ```bash
   cp example.env .env
   # 编辑 .env 文件，填入您的API密钥
   ```

3. **运行项目**
   ```bash
   python gui_enhanced.py
   ```

### 开发建议

- 启用 DEBUG 模式：在 `.env` 中设置 `DEBUG_MODE=True`
- 定期拉取主分支最新代码：`git pull upstream main`
- 保持您的 Fork 与主仓库同步

## 代码规范

### Python 代码风格

遵循 [PEP 8](https://www.python.org/dev/peps/pep-0008/) 规范：

- 使用 4 个空格缩进
- 每行最多 100 个字符（文档字符串除外）
- 类名使用大驼峰命名法：`ChatAgent`
- 函数名使用小写下划线命名法：`load_memory`
- 常量使用大写下划线命名法：`MAX_MEMORY_MESSAGES`

### 注释规范

```python
def function_name(param1: str, param2: int) -> bool:
    """
    函数的简短描述
    
    详细描述函数的功能和使用方法
    
    Args:
        param1: 参数1的描述
        param2: 参数2的描述
    
    Returns:
        返回值的描述
    
    Raises:
        可能抛出的异常
    
    Example:
        >>> function_name("test", 123)
        True
    """
    pass
```

### 模块结构

```python
"""
模块的简短描述

详细描述模块的功能和用途
"""

# 标准库导入
import os
import json

# 第三方库导入
from langchain import LLMChain
from dotenv import load_dotenv

# 本地模块导入
from database_manager import DatabaseManager
from debug_logger import get_debug_logger

# 常量定义
DEFAULT_MEMORY_SIZE = 20

# 类定义
class MyClass:
    pass

# 函数定义
def my_function():
    pass
```

## 提交规范

使用语义化的提交消息：

### 提交类型

- `feat`: 新功能
- `fix`: 错误修复
- `docs`: 文档更新
- `style`: 代码格式调整（不影响功能）
- `refactor`: 代码重构
- `perf`: 性能优化
- `test`: 添加或修改测试
- `chore`: 构建过程或辅助工具的变动

### 提交格式

```
<类型>(<范围>): <简短描述>

<详细描述>（可选）

<关联的 issue>（可选）
```

### 示例

```bash
feat(memory): 添加情感分析自动触发功能

- 每10轮对话自动触发情感分析
- 分析完成后更新GUI显示
- 根据情感状态调整AI语气

Closes #123
```

## 测试要求

### 手动测试

在提交 PR 前，请确保：

1. **基础功能测试**
   - 程序能正常启动
   - GUI界面显示正常
   - 对话功能正常
   - 记忆系统工作正常

2. **新功能测试**
   - 测试所有新增功能
   - 测试边界情况
   - 测试错误处理

3. **兼容性测试**
   - 不影响现有功能
   - 向后兼容旧数据

### 调试技巧

- 启用 DEBUG 模式查看详细日志
- 使用 Debug 日志标签页监控系统运行
- 检查 `debug.log` 文件获取完整日志

## 文档贡献

### 文档类型

- **README.md**: 项目主文档
- **CONTRIBUTING.md**: 本文件
- **docs/**: 详细文档目录
  - API.md: API 文档
  - DEVELOPMENT.md: 开发指南
  - DEPLOYMENT.md: 部署指南
  - EXAMPLES.md: 使用示例
  - TROUBLESHOOTING.md: 故障排查

### 文档编写规范

- 使用清晰的中文表达
- 提供具体的代码示例
- 包含屏幕截图（UI相关）
- 保持格式统一
- 定期更新过时内容

## 常见问题

### Q: 我不会写代码，可以贡献吗？

**A**: 当然可以！您可以：
- 改进文档
- 报告 bug
- 提出功能建议
- 帮助测试新版本
- 翻译文档（如需要）

### Q: Pull Request 多久会被审核？

**A**: 我们会尽快审核，通常在 1-3 个工作日内。复杂的 PR 可能需要更长时间。

### Q: 我的 PR 被拒绝了怎么办？

**A**: 
- 阅读审核意见
- 根据反馈进行修改
- 重新提交
- 如有疑问，可以在 PR 中讨论

### Q: 如何联系维护者？

**A**: 
- 在 Issue 中 @维护者
- 在 PR 中留言
- 查看 README 中的联系方式

## 版本发布

项目采用语义化版本号：`主版本号.次版本号.修订号`

- **主版本号**: 不兼容的API修改
- **次版本号**: 向后兼容的功能新增
- **修订号**: 向后兼容的问题修正

## 许可证

贡献代码即表示您同意将代码以 MIT 许可证授权。

## 感谢

感谢所有为本项目做出贡献的人！

---

如有任何问题，欢迎在 [Issues](https://github.com/HeDaas-Code/Neo_Agent/issues) 中讨论。
