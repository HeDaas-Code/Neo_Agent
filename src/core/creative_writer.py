"""
长期创作项目管理模块
实现多会话长期创作系统：
- 立项：消费 P1 阶段日记 / 梦境碎片，生成项目前提
- 续写：按 95-320 分钟随机间隔生成 60-1200 字正文
- Story Bible：项目级线索状态机（active_themes / unresolved_threads / resolved_threads / important_facts）
- Memory Pool：按 type + importance 组织，max 50 条
- 质量审核：相似度阈值 0.72 / 重试 2 次 / min_score 7

参考架构：spec §3 ADDED Requirements → CreativeProjectManager
"""

import os
import json
import random
import re
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional

from src.core.database_manager import DatabaseManager
from src.core.llm_helper import LLMHelper
from src.core.prompt_manager import get_prompt_manager
from src.tools.debug_logger import get_debug_logger

ENABLE_CREATIVE_WRITER = os.getenv('ENABLE_CREATIVE_WRITER', 'false').lower() == 'true'

debug_logger = get_debug_logger()


# 默认项目模板（沿用 AstrBot DEFAULT_CREATIVE_PROJECT_TEMPLATE 字段命名）
DEFAULT_CREATIVE_PROJECT_TEMPLATE: Dict[str, Any] = {
    'id': '',
    'title': '',
    'work_type': '短篇',
    'premise': '',
    'tone': '',
    'point_of_view': '第一人称',
    'target_chars': 5000,
    'current_chars': 0,
    'status': 'drafting',
    'inspiration_source': '',
    'draft_chunks': [],
    'story_bible': {},
    'creative_memory_pool': [],
    'outline': [],
    'characters': [],
    'next_advance_at': None,
}

CREATIVE_STORY_BIBLE_TEMPLATE: Dict[str, Any] = {
    'mainline_direction': '',
    'active_themes': [],
    'unresolved_threads': [],
    'resolved_threads': [],
    'important_facts': [],
    'next_direction': '',
    'recent_keywords': [],
}


class CreativeProjectManager:
    """
    长期创作项目管理器。
    - maybe_start_creative_project: 条件触发立项
    - maybe_advance_creative_projects: 续写到期项目
    - generate_creative_project: 立项（生成前提 / 大纲 / 角色）
    - generate_creative_chunk: 续写 60-1200 字正文
    - 质量审核：相似度阈值 0.72 / 重试 2 次 / min_score 7
    """

    WORK_TYPES = ['短篇', '中篇', '长篇', '散文', '诗歌']
    DEFAULT_CHUNK_MIN = 60
    DEFAULT_CHUNK_MAX = 1200
    DEFAULT_INTERVAL_MIN = 95
    DEFAULT_INTERVAL_MAX = 320
    MIN_PROJECT_INTERVAL_HOURS = 10
    MAX_ACTIVE_PROJECTS = 2
    SIMILARITY_THRESHOLD = 0.72
    MAX_RETRY = 2
    MIN_SCORE = 7
    MAX_POOL_SIZE = 50
    QUALITY_SCORE_MAX = 10

    def __init__(self, db_manager: DatabaseManager = None,
                 prompt_manager=None,
                 character_info: Optional[Dict[str, Any]] = None,
                 life_state=None,
                 dream_diary=None):
        self.db = db_manager or DatabaseManager()
        self.prompt_manager = prompt_manager or get_prompt_manager()
        self.character_info = character_info or {}
        self.life_state = life_state
        self.dream_diary = dream_diary
        self.enabled = ENABLE_CREATIVE_WRITER

    # ===== 立项 =====

    def maybe_start_creative_project(self, idle_checked: bool = False,
                                     now: Optional[datetime] = None) -> bool:
        """
        若满足条件（距上次立项 > 10h 且活跃项目数 < max 且已检测空闲），
        启动一个新项目并持久化。
        """
        if not self.enabled:
            return False
        if not idle_checked:
            return False

        now = now or datetime.now()
        active = self.db.list_creative_projects(status='drafting', limit=self.MAX_ACTIVE_PROJECTS + 1)
        if len(active) >= self.MAX_ACTIVE_PROJECTS:
            return False

        # 距上次立项 > 10h
        recent = self.db.list_creative_projects(limit=1)
        if recent:
            try:
                last_dt = datetime.fromisoformat(recent[0]['created_at'])
                if (now - last_dt) < timedelta(hours=self.MIN_PROJECT_INTERVAL_HOURS):
                    return False
            except (ValueError, TypeError):
                pass

        # 消费灵感来源
        source = self.creative_inspiration_source() or {}
        project = self.generate_creative_project(source)
        if not project:
            return False
        project['status'] = 'drafting'
        project['next_advance_at'] = (
            now + timedelta(minutes=random.randint(
                self.DEFAULT_INTERVAL_MIN, self.DEFAULT_INTERVAL_MAX))
        ).isoformat()
        project_uuid = self.db.create_creative_project(project)
        if project_uuid:
            self.get_or_create_story_bible({'uuid': project_uuid})
            self.get_or_create_memory_pool({'uuid': project_uuid})
            debug_logger.log_info('CreativeWriter', '立项成功', {
                'uuid': project_uuid, 'title': project.get('title'),
            })
            return True
        return False

    def generate_creative_project(self, source: Dict[str, Any]) -> Dict[str, Any]:
        """
        通过 LLMHelper.call_main_model 生成项目前提 / 风格 / 大纲 / 角色。
        """
        if not self.enabled:
            return {}

        prompt = self._build_project_prompt(source)
        try:
            raw = LLMHelper.call_main_model(
                system_prompt='你是创作构思助手，输出严格 JSON。',
                user_message=prompt,
            )
            data = self._parse_json_response(raw)
        except Exception as e:
            debug_logger.log_error('CreativeWriter', f'立项 LLM 调用失败: {e}', e)
            return {}

        if not data:
            return {}

        project = dict(DEFAULT_CREATIVE_PROJECT_TEMPLATE)
        project.update({
            'id': str(uuid.uuid4()),
            'title': (data.get('title') or '未命名项目')[:80],
            'work_type': data.get('work_type', '短篇'),
            'premise': (data.get('premise') or '').strip(),
            'tone': (data.get('tone') or '').strip(),
            'point_of_view': data.get('point_of_view', '第一人称'),
            'target_chars': int(data.get('target_chars', 5000)),
            'current_chars': 0,
            'outline': data.get('outline', [])[:20],
            'characters': data.get('characters', [])[:10],
            'inspiration_source': source.get('source', ''),
            'draft_chunks': [],
        })
        return project

    def _build_project_prompt(self, source: Dict[str, Any]) -> str:
        char_name = self.character_info.get('name', 'AI')
        char_setting = self.character_info.get('settings', '无')
        inspiration_text = source.get('content', '（无）')
        inspiration_kind = source.get('source', 'default')
        return f"""你是一位文学构思助手，请基于灵感来源为角色"{char_name}"构思一个创作项目。

【角色设定】
{char_setting}

【灵感来源类型】{inspiration_kind}
【灵感内容】
{inspiration_text}

请输出严格 JSON（仅 JSON，不要其他内容）：
{{
  "title": "项目标题（≤ 20 字）",
  "work_type": "短篇/中篇/长篇/散文/诗歌",
  "premise": "一句话故事前提（≤ 60 字）",
  "tone": "整体语气（温暖/冷峻/...）",
  "point_of_view": "第一人称/第三人称",
  "target_chars": 5000,
  "outline": ["章节1 摘要", "章节2 摘要", ...],
  "characters": [
    {{"name": "角色名", "role": "主角/配角", "trait": "性格/特点"}}
  ]
}}
"""

    def creative_inspiration_source(self) -> Optional[Dict[str, Any]]:
        """
        灵感来源消费 P1 阶段日记 / 梦境碎片。
        返回 {source, content} 或 None（若无可用灵感）。
        """
        if self.dream_diary and getattr(self.dream_diary, 'enabled', False):
            try:
                ctx = self.dream_diary.recent_diary_context(count=1)
                if ctx:
                    return {'source': 'dream_diary', 'content': ctx[:600]}
            except Exception as e:
                debug_logger.log_error('CreativeWriter', f'消费梦境灵感失败: {e}', e)

        if self.life_state and getattr(self.life_state, 'enabled', False):
            try:
                snap = self.life_state.get_current_state_snapshot() or {}
                mood = snap.get('mood', '')
                state = snap.get('state_title', '')
                if mood or state:
                    return {'source': 'life_state',
                            'content': f"今日状态：{state}，心情：{mood}"}
            except Exception as e:
                debug_logger.log_error('CreativeWriter', f'消费生活状态灵感失败: {e}', e)
        return None

    # ===== 续写 =====

    def maybe_advance_creative_projects(self, now: Optional[datetime] = None) -> int:
        """
        推进所有到期的活跃项目。每个项目生成 60-1200 字正文，更新 Story Bible / Memory Pool。
        返回成功推进的项目数。
        """
        if not self.enabled:
            return 0
        now = now or datetime.now()
        active = self.db.list_creative_projects(status='drafting', limit=20)
        advanced = 0
        for proj in active:
            next_at = proj.get('next_advance_at')
            if not next_at:
                continue
            try:
                next_dt = datetime.fromisoformat(next_at)
            except (ValueError, TypeError):
                continue
            if next_dt > now:
                continue
            if self._advance_one(proj, now):
                advanced += 1
        return advanced

    def _advance_one(self, project: Dict[str, Any], now: datetime) -> bool:
        project_uuid = project.get('uuid')
        if not project_uuid:
            return False
        budget = random.randint(self.DEFAULT_CHUNK_MIN, self.DEFAULT_CHUNK_MAX)
        chunk = self.generate_creative_chunk(project, budget)
        if not chunk:
            return False
        # 质量审核：相似度 + 评分
        if not self._quality_check(chunk, project):
            retry = 0
            while retry < self.MAX_RETRY and not self._quality_check(chunk, project):
                chunk = self.generate_creative_chunk(project, budget)
                retry += 1
            if not self._quality_check(chunk, project):
                debug_logger.log_info('CreativeWriter', '续写未达质量阈值，跳过本次', {
                    'uuid': project_uuid,
                })
                return False

        new_chunks = (project.get('draft_chunks') or []) + [{
            'content': chunk,
            'created_at': now.isoformat(),
            'char_count': len(chunk),
        }]
        new_chars = int(project.get('current_chars', 0)) + len(chunk)
        target = int(project.get('target_chars', 5000))
        next_status = 'finished' if new_chars >= target else 'drafting'
        next_at = (now + timedelta(minutes=random.randint(
            self.DEFAULT_INTERVAL_MIN, self.DEFAULT_INTERVAL_MAX))).isoformat()

        self.db.update_creative_project(project_uuid, {
            'current_chars': new_chars,
            'draft_chunks': new_chunks,
            'status': next_status,
            'next_advance_at': next_at,
            'last_advanced_at': now.isoformat(),
        })
        # 追加到 Memory Pool
        self.db.add_creative_memory(
            project_uuid=project_uuid,
            memory_type='chunk',
            content=chunk[:500],
            importance=0.7,
        )
        # 修剪池
        self.db.prune_creative_memory_pool(project_uuid, keep_max=self.MAX_POOL_SIZE)
        # Story Bible 更新
        self._update_story_bible_keywords(project_uuid, chunk)
        return True

    def generate_creative_chunk(self, project: Dict[str, Any],
                                budget: int) -> str:
        """
        通过 LLMHelper.call_main_model（temperature 0.8）生成正文。
        """
        if not self.enabled:
            return ""
        project_uuid = project.get('uuid', '')
        bible = self.db.get_story_bible(project_uuid) or CREATIVE_STORY_BIBLE_TEMPLATE.copy()
        pool = self.db.get_creative_memory_pool(project_uuid, limit=self.MAX_POOL_SIZE)
        prompt = self._build_chunk_prompt(project, bible, pool, budget)
        try:
            chunk = LLMHelper.call_main_model(
                system_prompt='你是文学创作助手，输出符合角色与故事上下文的连续正文。',
                user_message=prompt,
            )
        except Exception as e:
            debug_logger.log_error('CreativeWriter', f'续写 LLM 调用失败: {e}', e)
            return ""
        chunk = (chunk or '').strip()
        return chunk[:budget] if len(chunk) > budget else chunk

    def _build_chunk_prompt(self, project: Dict[str, Any],
                            bible: Dict[str, Any], pool: List[Dict[str, Any]],
                            budget: int) -> str:
        outlines = project.get('outline') or []
        characters = project.get('characters') or []
        recent_chunks = (project.get('draft_chunks') or [])[-3:]
        recent_text = "\n\n".join(c.get('content', '') for c in recent_chunks)
        return f"""你正在续写项目《{project.get('title', '未命名')}》。

【作品元信息】
- 体裁：{project.get('work_type', '短篇')}
- 视角：{project.get('point_of_view', '第一人称')}
- 语气：{project.get('tone', '')}
- 当前已写：{project.get('current_chars', 0)}/{project.get('target_chars', 5000)} 字

【故事前提】
{project.get('premise', '')}

【大纲】
{chr(10).join(f"- {x}" for x in outlines)}

【角色】
{chr(10).join(f"- {c.get('name', '')}：{c.get('role', '')} / {c.get('trait', '')}" for c in characters)}

【Story Bible 提示】
- 主线方向：{bible.get('mainline_direction', '')}
- 活跃主题：{', '.join(bible.get('active_themes', []))}
- 未解线索：{', '.join(bible.get('unresolved_threads', []))}
- 下一方向：{bible.get('next_direction', '')}

【记忆池摘录】
{chr(10).join(f"- [{m.get('memory_type', '')}] {m.get('content', '')[:120]}" for m in pool[:8])}

【最近正文（末段）】
{recent_text[:1500]}

【任务】请续写下一段正文，长度约 {budget} 字（60-1200），保持角色一致、推进 Story Bible 中的下一方向。直接输出正文，不要加解释或标题。
"""

    def _quality_check(self, chunk: str, project: Dict[str, Any]) -> bool:
        if not chunk:
            return False
        if len(chunk) < 30:
            return False
        # 相似度：与最近 chunks 重复率
        recent = (project.get('draft_chunks') or [])[-3:]
        for old in recent:
            sim = self._jaccard_similarity(chunk, old.get('content', ''))
            if sim > self.SIMILARITY_THRESHOLD:
                return False
        # 评分：长度 + 标点密度 + 中文字数占比（启发式）
        score = self._heuristic_score(chunk)
        return score >= self.MIN_SCORE

    @staticmethod
    def _jaccard_similarity(a: str, b: str) -> float:
        if not a or not b:
            return 0.0
        set_a = set(re.findall(r'[\u4e00-\u9fffA-Za-z0-9]+', a))
        set_b = set(re.findall(r'[\u4e00-\u9fffA-Za-z0-9]+', b))
        if not set_a or not set_b:
            return 0.0
        return len(set_a & set_b) / len(set_a | set_b)

    def _heuristic_score(self, chunk: str) -> int:
        score = 0
        if len(chunk) >= 100:
            score += 3
        if len(chunk) >= 300:
            score += 2
        # 句号 / 问号 / 感叹号 / 逗号
        punct = sum(chunk.count(c) for c in '。，！？；：')
        if punct >= 3:
            score += 2
        # 中文字符占比
        cn_chars = len(re.findall(r'[\u4e00-\u9fff]', chunk))
        if cn_chars / max(1, len(chunk)) > 0.5:
            score += 3
        return score

    def _update_story_bible_keywords(self, project_uuid: str, chunk: str) -> None:
        bible = self.db.get_story_bible(project_uuid) or {}
        if not bible:
            bible = dict(CREATIVE_STORY_BIBLE_TEMPLATE)
        # 简单关键词提取
        kws = re.findall(r'[\u4e00-\u9fff]{2,4}', chunk)
        freq: Dict[str, int] = {}
        for k in kws:
            freq[k] = freq.get(k, 0) + 1
        top = sorted(freq.items(), key=lambda kv: kv[1], reverse=True)[:10]
        bible['recent_keywords'] = [k for k, _ in top]
        # next_direction：从前文 outline 中取下一项
        proj = self.db.get_creative_project(project_uuid) or {}
        outlines = proj.get('outline') or []
        current_chars = int(proj.get('current_chars', 0))
        target = max(1, int(proj.get('target_chars', 5000)))
        idx = min(len(outlines) - 1, int(current_chars / target * len(outlines)))
        bible['next_direction'] = outlines[idx] if outlines else ''
        self.db.upsert_story_bible(project_uuid, bible)

    # ===== Story Bible / Memory Pool =====

    def get_or_create_story_bible(self, project: Dict[str, Any]) -> Dict[str, Any]:
        project_uuid = project.get('uuid')
        if not project_uuid:
            return {}
        bible = self.db.get_story_bible(project_uuid)
        if bible:
            return bible
        bible = dict(CREATIVE_STORY_BIBLE_TEMPLATE)
        self.db.upsert_story_bible(project_uuid, bible)
        return bible

    def get_or_create_memory_pool(self, project: Dict[str, Any]) -> List[Dict[str, Any]]:
        project_uuid = project.get('uuid')
        if not project_uuid:
            return []
        pool = self.db.get_creative_memory_pool(project_uuid, limit=self.MAX_POOL_SIZE)
        return pool

    # ===== 工具 =====

    def _parse_json_response(self, raw: str) -> Dict[str, Any]:
        if not raw:
            return {}
        text = raw.strip()
        if text.startswith('```'):
            lines = text.split('\n')
            text = '\n'.join(lines[1:-1]) if len(lines) > 2 else text
            if text.startswith('json'):
                text = text[4:].strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            match = re.search(r'\{[\s\S]*\}', text)
            if match:
                try:
                    return json.loads(match.group(0))
                except json.JSONDecodeError:
                    pass
        return {}

    def get_finished_projects(self, limit: int = 10) -> List[Dict[str, Any]]:
        """供 P4 ProactiveEngine 作为 creative_share 想法来源。"""
        return self.db.list_creative_projects(status='finished', limit=limit)
