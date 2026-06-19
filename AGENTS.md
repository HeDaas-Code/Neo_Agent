---
title: Neo_Agent Agent Skills Configuration
type: agents-config
status: active
last_updated: 2026-06-19
---

# AGENTS.md — Neo_Agent Agent Skills Configuration

> 本文件配置 Neo_Agent 项目使用 Hermes / Matt Pocock engineering skills 所需的项目级上下文。

## Agent skills

### Issue tracker

项目使用 GitHub Issues。详见 [[docs/agents/issue-tracker]]。

### Triage labels

Matt Pocock 默认 5 类状态机标签。详见 [[docs/agents/triage-labels]]。

### Domain docs

单上下文布局——根 `CONTEXT.md` + `docs/adr/`。详见 [[docs/agents/domain]]。

## 沟通约定

- **本项目代码、注释、issue/PR 标题使用中文**
- **变量/函数命名使用英文**（Python 业界惯例）
- **Commit message**：`feat: <中文简述>` / `fix: <中文简述>` / `chore: <中文简述>` / `docs: <中文简述>`
- **分支命名**：`feature/<功能>` / `fix/<问题>` / `chore/<任务>`

## 快速命令

```bash
# 启动 GUI（需要 Tkinter）
python main.py

# 启动方式 2（推荐用 run.py——自动加项目根到 sys.path）
python run.py

# 运行测试
pytest

# 安装依赖
pip install -r requirements.txt
```

## 关联笔记

- [[README]] — 仓库根 README
- [[CHANGELOG]] — 变更日志
- [[docs/ARCHITECTURE]] — 架构总览
- [[docs/TECHNICAL]] — 技术细节
- [[工作Wiki/README]] — 工作 Wiki 入口
- [[工作Wiki/00-index/README]] — 项目速览
- [[CONTEXT]] — 项目领域术语