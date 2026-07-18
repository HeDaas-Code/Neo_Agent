# 创作任务提示词

用于 `CreativeProjectManager` 的 LLM 调用（`call_main_model`），生成项目前提 / 大纲 / 角色 / 续写正文。

## 立项提示词

输入变量：
- `{character_name}`：角色名
- `{character_settings}`：角色设定
- `{inspiration_kind}`：灵感来源类型（`dream_diary` / `life_state` / `default`）
- `{inspiration_content}`：灵感内容

## 立项任务

你是一位文学构思助手，请基于灵感来源为角色 `{character_name}` 构思一个创作项目。

【角色设定】
{character_settings}

【灵感来源类型】{inspiration_kind}
【灵感内容】
{inspiration_content}

请输出严格 JSON（仅 JSON，不要其他内容）：
```json
{
  "title": "项目标题（≤ 20 字）",
  "work_type": "短篇/中篇/长篇/散文/诗歌",
  "premise": "一句话故事前提（≤ 60 字）",
  "tone": "整体语气（温暖/冷峻/...）",
  "point_of_view": "第一人称/第三人称",
  "target_chars": 5000,
  "outline": ["章节1 摘要", "章节2 摘要", "..."],
  "characters": [
    {"name": "角色名", "role": "主角/配角", "trait": "性格/特点"}
  ]
}
```

## 续写提示词

输入变量：
- `{title}` / `{work_type}` / `{point_of_view}` / `{tone}` / `{current_chars}` / `{target_chars}`
- `{premise}`：故事前提
- `{outline}`：项目大纲
- `{characters}`：角色列表
- `{bible_summary}`：Story Bible 摘要（主线 / 活跃主题 / 未解线索 / 下一方向）
- `{memory_pool}`：记忆池摘录
- `{recent_chunks}`：最近 3 段正文
- `{budget}`：本次续写字数预算

## 续写任务

你正在续写项目《{title}》。

【作品元信息】
- 体裁：{work_type}
- 视角：{point_of_view}
- 语气：{tone}
- 当前已写：{current_chars}/{target_chars} 字

【故事前提】
{premise}

【大纲】
{outline}

【角色】
{characters}

【Story Bible 提示】
{bible_summary}

【记忆池摘录】
{memory_pool}

【最近正文（末段）】
{recent_chunks}

【任务】请续写下一段正文，长度约 {budget} 字（60-1200），保持角色一致、推进 Story Bible 中的下一方向。直接输出正文，不要加解释或标题。

## 质量要求

- 续写长度 60-1200 字，区间内随机
- 相似度阈值 0.72，重试 2 次
- 启发式评分 min_score 7（满分 10）：长度 + 标点密度 + 中文字符占比
- 当前累计字数 >= target_chars 时进入 `finished` 状态
- Story Bible `recent_keywords` 持续更新（前 10 关键词）
- Memory Pool 按 `importance` 排序，最大 50 条
