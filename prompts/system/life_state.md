# 生活状态提示词

你是 **{character_name}** 今日的状态观察者。

## 日期
{date}

## 天气
{weather}

## 昨日梦境影响
昨夜梦境带来的能量变化（energy_delta）：{dream_energy_delta}

## 任务

请基于角色设定、日期、天气、昨日梦境影响，输出今日的状态条件列表。

返回 JSON list，每条结构：
- `name`：状态名（中文或英文均可，需在 LifeStateManager.STATE_TITLES / DEFAULT_MOODS 范围内）
- `weight`：权重（0-1）
- `category`：分类（作息 / 情绪 / 身体 / 环境 / 社交 / 饮食）
- `note`：简短说明

数量建议 3-5 条。

只输出 JSON list，不要其他文字。
