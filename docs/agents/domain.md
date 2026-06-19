---
title: Neo_Agent Domain Docs
type: agents-config
parent: AGENTS.md
---

# Domain Docs

**单上下文布局**——`CONTEXT.md`（根） + `docs/adr/`（入仓） + `工作Wiki/`（不入仓）。

## 何时开 ADR

- 引入新依赖（如替换 LangChain → Composite Framework 已开）
- 改变公共 API（GUI 类、CLI 命令）
- 重构跨 ≥3 个文件
- 推翻旧决策

## 何时不开

- bug fix
- 文档更新
- 依赖小版本升级

## Neo_Agent 已有 ADR 范本

- `copilot/replace-langchain-with-composite-framework` (PR #58)——框架替换
- `copilot/refactor-deepagents-optimization` (PR #59)——性能优化
- `docs/chinese-standardization`——命名规范化