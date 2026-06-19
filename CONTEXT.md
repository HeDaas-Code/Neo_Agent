---
title: Neo_Agent 领域术语表
type: context
status: active
last_updated: 2026-06-19
---

# CONTEXT.md — Neo_Agent 领域术语表

## 项目核心概念

### Neo Agent

基于 LangChain + LangGraph 的智能对话代理系统。**多层模型架构**（主模型 + 工具模型 + 多模态模型），具备：

- 角色扮演（character prompts）
- 长效记忆管理（短期/长期/知识库/基础）
- 情感关系分析（印象评估 + 累计评分）
- 智能日程管理

### 多层模型架构

| 层 | 模型 | 用途 |
|---|---|---|
| 主模型 | DeepSeek-V3.2 | 主要对话、复杂推理 |
| 工具模型 | GLM-4.6V | 工具调用、意图识别 |
| 多模态模型 | Qwen3-VL-32B | 多模态识别 |

### 记忆分层

- **短期记忆**——当前会话上下文
- **长期记忆**——跨会话用户偏好
- **知识库**——用户导入的结构化知识
- **基础知识**——模型预训练 + 系统 prompt

### 提示词分层

`prompts/` 目录分 4 类：

| 子目录 | 用途 |
|---|---|
| `character/` | 角色定义 |
| `system/` | 系统级 prompt（agent 行为约束） |
| `task/` | 任务模板 |
| `worldview/` | 世界观注入 |

### GUI

Tkinter 实现（`src/gui/gui_enhanced.py`）。**注意**：需要系统安装 Tkinter。

### NPS

`src/nps/` 子模块——可能是 Net Promoter Score 或自定义命名空间（待确认）。

## 项目特定命名

| 术语 | 含义 |
|---|---|
| **GUI Enhanced** | 主界面类名（`EnhancedChatDebugGUI`） |
| **NPS** | Net Promoter Score 或本项目自定义子系统（看 `docs/NPS_*.md` 确认） |
| **chinese-standardization** | 历史 PR 标签——把英文术语规范化到中文 |
| **NPS_CONFIG_MANAGEMENT** | NPS 配置管理文档 |
| **NPS_WEB_SEARCH** | NPS Web 搜索与集成文档 |

## 不混淆概念

- **Neo_Agent ≠ NeoForge**——后者是 Minecraft mod loader
- **NPS ≠ NPS（Net Promoter Score 通用含义）**——本项目自定义
- **GLM-4.6V ≠ GLM-4**——前者是多模态，后者纯文本
- **DeepSeek-V3.2 ≠ DeepSeek-V3**——版本号精确

## 待补

- [ ] NPS 子模块确切含义
- [ ] src/tools/ 工具清单
- [ ] src/core/ 子模块清单
- [ ] CHANGELOG 历次关键变更（v1.x → v2.x → v3.x）