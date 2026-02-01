# Changelog / 更新日志

All notable changes to this project will be documented in this file.

本文件记录项目的所有重要变更。

## [1.0.0] - 2026-01-31

### Added / 新增

- 项目重构为标准Python包结构
- 创建了清晰的模块划分（core, gui, tools, nps）
- 添加主入口点 main.py
- 完善的包初始化文件和模块导出
- 新的项目文档（README, CONTRIBUTING）

### Changed / 变更

- 将所有源代码移至 src/ 目录
- 重新组织核心模块到 src/core/
- 重新组织GUI模块到 src/gui/
- 重新组织工具模块到 src/tools/
- 移动NPS系统到 src/nps/
- 移动示例代码到 examples/
- 统一测试文件到 tests/
- 更新所有import路径以反映新结构

### Removed / 移除

- 删除临时说明文档
- 清理过时的markdown文档
- 移除根目录下的散乱文件

### Technical / 技术细节

- 实现模块化包结构
- 改进代码组织和可维护性
- 标准化项目布局
- 简化部署和安装流程

---

## 版本说明 / Version Notes

版本号遵循 [语义化版本](https://semver.org/lang/zh-CN/) 规范：

- 主版本号：不兼容的API变更
- 次版本号：向下兼容的功能新增
- 修订号：向下兼容的问题修正

Version numbers follow [Semantic Versioning](https://semver.org/):

- MAJOR: Incompatible API changes
- MINOR: Backward compatible functionality additions
- PATCH: Backward compatible bug fixes
