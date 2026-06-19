---
title: Neo_Agent Triage Labels
type: agents-config
parent: AGENTS.md
---

# Triage Labels

Matt Pocock 默认 5 类：

| 标签 | 含义 |
|---|---|
| `status: ready-for-agent` | 需求清晰、上下文完整 |
| `status: needs-triage` | 信息不全、需澄清 |
| `status: in-progress` | agent 已开 PR |
| `status: blocked` | 依赖外部 |
| `status: needs-human-review` | agent 完成后需 owner 验收 |

## 状态机

```
needs-triage → ready-for-agent → in-progress → needs-human-review → close
                  ↑                                 │
                  └──── blocked ←─────────────────────┘
```