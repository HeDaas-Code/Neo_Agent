# Contributing to Neo Agent

## 中文 / Chinese

### 贡献指南

感谢您对 Neo Agent 项目的关注！我们欢迎各种形式的贡献。

#### 如何贡献

1. **Fork 项目**
2. **创建特性分支** (`git checkout -b feature/AmazingFeature`)
3. **提交更改** (`git commit -m 'Add some AmazingFeature'`)
4. **推送到分支** (`git push origin feature/AmazingFeature`)
5. **开启 Pull Request**

#### 代码规范

- 遵循 PEP 8 Python 代码规范
- 为函数和类添加文档字符串（中文或英文）
- 使用类型提示
- 添加适当的单元测试

#### 项目结构

- `src/core/` - 核心业务逻辑
- `src/gui/` - 图形界面组件
- `src/tools/` - 工具和辅助函数
- `src/nps/` - NPS工具系统
- `tests/` - 单元测试
- `examples/` - 示例代码

#### 开发环境设置

```bash
# 克隆仓库
git clone https://github.com/HeDaas-Code/Neo_Agent.git
cd Neo_Agent

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp .env .env
# 编辑 .env 填入配置

# 运行测试
python -m pytest tests/

# 启动应用
python main.py
```

#### 报告 Bug

如果发现 Bug，请在 GitHub Issues 中报告，包含：

- Bug 描述
- 重现步骤
- 预期行为
- 实际行为
- 环境信息（操作系统、Python版本等）

#### 建议新功能

欢迎提出新功能建议！请在 Issues 中描述：

- 功能描述
- 使用场景
- 预期效果

---

## English

### Contributing Guidelines

Thank you for your interest in the Neo Agent project! We welcome contributions of all kinds.

#### How to Contribute

1. **Fork the project**
2. **Create a feature branch** (`git checkout -b feature/AmazingFeature`)
3. **Commit your changes** (`git commit -m 'Add some AmazingFeature'`)
4. **Push to the branch** (`git push origin feature/AmazingFeature`)
5. **Open a Pull Request**

#### Code Standards

- Follow PEP 8 Python style guide
- Add docstrings for functions and classes (Chinese or English)
- Use type hints
- Add appropriate unit tests

#### Project Structure

- `src/core/` - Core business logic
- `src/gui/` - GUI components
- `src/tools/` - Utilities and helper functions
- `src/nps/` - NPS tool system
- `tests/` - Unit tests
- `examples/` - Example code

#### Development Setup

```bash
# Clone repository
git clone https://github.com/HeDaas-Code/Neo_Agent.git
cd Neo_Agent

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env .env
# Edit .env with your configuration

# Run tests
python -m pytest tests/

# Start application
python main.py
```

#### Reporting Bugs

If you find a bug, please report it in GitHub Issues with:

- Bug description
- Steps to reproduce
- Expected behavior
- Actual behavior
- Environment information (OS, Python version, etc.)

#### Suggesting Features

Feature suggestions are welcome! Please describe in Issues:

- Feature description
- Use cases
- Expected outcome
