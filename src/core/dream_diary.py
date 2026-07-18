"""
梦境与日记管理模块
- 每日凌晨生成梦境（基于 memory_fragments 池 + 情绪线 + energy_delta）
- 每日凌晨生成叙事体裁日记（区别于 long_term_memory 的 ≤100 字摘要）
- 梦境输出 energy_delta 喂回 LifeStateManager 形成状态闭环
- 日记反作用于次日状态（通过 tags 字段）

参考架构：spec §1 ADDED Requirements → DreamDiaryManager
"""

import os
import json
import random
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional

from src.core.database_manager import DatabaseManager
from src.core.llm_helper import LLMHelper
from src.core.prompt_manager import get_prompt_manager
from src.core.long_term_memory import LongTermMemoryManager
from src.tools.debug_logger import get_debug_logger

ENABLE_DREAM_DIARY = os.getenv('ENABLE_DREAM_DIARY', 'false').lower() == 'true'

debug_logger = get_debug_logger()

DIARY_TAG_TO_STATE = {
    '失眠': '疲惫',
    '生病': '不适',
    '低能量': '疲惫',
    '好梦': '放松',
    '一般': '常态',
    '焦虑': '焦虑',
    '兴奋': '兴奋',
}


class DreamDiaryManager:
    """
    梦境与日记管理器
    梦境按 6 种主题生成；日记按叙事体裁生成（与摘要区别）。
    """

    DREAM_TYPES = ['温柔日常', '奇幻', '追逐', '悬疑', '荒诞', '怀旧']
    MOOD_OPTIONS = ['平静', '愉快', '焦虑', '忧伤', '温暖', '不安']
    DREAM_LABELS = ['清晰', '半梦半醒', '碎片', '重复', '强烈']
    DEFAULT_TAGS = ['一般']

    def __init__(self, db_manager: DatabaseManager = None,
                 life_state: Optional[Any] = None,
                 long_term_memory: Optional[LongTermMemoryManager] = None,
                 prompt_manager=None,
                 character_info: Optional[Dict[str, str]] = None):
        """
        Args:
            db_manager: 共享数据库管理器
            life_state: LifeStateManager 实例（用于回传 energy_delta）
            long_term_memory: LongTermMemoryManager 实例（碎片来源）
            prompt_manager: 提示词管理器
            character_info: 角色设定信息
        """
        self.db = db_manager or DatabaseManager()
        self.life_state = life_state
        self.memory = long_term_memory or LongTermMemoryManager(db_manager=self.db)
        self.prompt_manager = prompt_manager or get_prompt_manager()
        self.character_info = character_info or {}
        self.enabled = ENABLE_DREAM_DIARY

    def generate_dream_pick(self, weather: Optional[Dict[str, Any]] = None,
                            now: Optional[datetime] = None) -> Dict[str, Any]:
        """
        生成单条梦境记录并写入数据库。
        返回的 dict 含 dream_type / content / afterglow / label / mood / energy_delta / duration_hours。
        """
        if not self.enabled:
            return {}

        now = now or datetime.now()
        date_str = now.date().isoformat()
        dream_type = random.choice(self.DREAM_TYPES)
        fragments = self.build_dream_memory_fragments(count=8)
        mood = random.choice(self.MOOD_OPTIONS)
        label = random.choice(self.DREAM_LABELS)
        duration = round(random.uniform(5.0, 9.0), 1)

        content = self._compose_dream_text(dream_type, fragments, mood)
        energy_delta = self._compute_energy_delta(mood, label, dream_type)
        afterglow = self._compose_afterglow(mood, dream_type)

        dream_uuid = self.db.insert_dream_record(
            date=date_str, dream_type=dream_type, content=content,
            afterglow=afterglow, label=label, mood=mood,
            energy_delta=energy_delta, duration_hours=duration,
            weather=weather or {}
        )

        if self.life_state is not None and hasattr(self.life_state, 'consume_dream_energy_delta'):
            self.life_state.consume_dream_energy_delta(energy_delta)

        debug_logger.log_info('DreamDiaryManager', '梦境生成', {
            'date': date_str, 'dream_type': dream_type, 'mood': mood,
            'energy_delta': energy_delta, 'uuid': dream_uuid
        })
        return {
            'uuid': dream_uuid, 'date': date_str, 'dream_type': dream_type,
            'content': content, 'afterglow': afterglow, 'label': label,
            'mood': mood, 'energy_delta': energy_delta,
            'duration_hours': duration, 'weather': weather or {}
        }

    def generate_daily_diary(self, now: Optional[datetime] = None) -> Dict[str, Any]:
        """
        生成单条叙事体裁日记并写入数据库。
        与 long_term_memory 摘要（≤100 字）区别：日记是叙事文，不反向影响状态。
        """
        if not self.enabled:
            return {}

        now = now or datetime.now()
        date_str = now.date().isoformat()
        recent_dreams = self.db.get_recent_dreams(limit=3)
        fragments = self.build_dream_memory_fragments(count=5)
        state_title = (self.life_state.get_current_state_snapshot(now=now).get('state_title', '常态')
                       if self.life_state else '常态')

        body = self._compose_diary_body(recent_dreams, fragments, state_title)
        title = self._compose_diary_title(state_title)
        mood = self._infer_diary_mood(recent_dreams)
        tags = self._compute_diary_tags(recent_dreams, state_title, body)

        entry_uuid = self.db.insert_diary_entry(
            date=date_str, title=title, body=body, mood=mood, tags=tags
        )

        debug_logger.log_info('DreamDiaryManager', '日记生成', {
            'date': date_str, 'word_count': len(body), 'tags': tags,
            'uuid': entry_uuid
        })
        return {
            'uuid': entry_uuid, 'date': date_str, 'title': title,
            'body': body, 'mood': mood, 'tags': tags,
            'word_count': len(body)
        }

    def build_dream_memory_fragments(self, count: int = 8) -> List[str]:
        """
        从数据库读取历史梦境作为碎片池，必要时叠加短期对话中的关键句。
        """
        pool = self.db.get_dream_fragments_pool(limit=50)
        recent_messages = []
        try:
            recent_messages = self.memory.get_recent_messages(count=10) or []
        except Exception:
            recent_messages = []

        for msg in recent_messages[-count:]:
            content = (msg.get('content') or '').strip()
            if 4 <= len(content) <= 60:
                pool.append(content)

        if not pool:
            pool = ['旧梦', '街灯', '窗台', '脚步', '远处的声音']
        random.shuffle(pool)
        return pool[:count]

    def recent_diary_context(self, count: int = 3) -> str:
        """
        拉取最近 N 篇日记，渲染为可注入 prompt 的文本。
        """
        if not self.enabled:
            return ""
        diaries = self.db.get_recent_diaries(limit=count)
        if not diaries:
            return ""
        parts = ["【最近的日记】"]
        for d in diaries:
            body = (d.get('body') or '').strip()
            if len(body) > 200:
                body = body[:200] + '…'
            parts.append(f"• {d.get('date', '?')} {d.get('title', '')}：{body}")
        return '\n'.join(parts)

    def _compose_dream_text(self, dream_type: str, fragments: List[str], mood: str) -> str:
        chosen = fragments[: min(4, len(fragments))]
        intro = {
            '温柔日常': '某个平常的下午',
            '奇幻': '在不可能的边缘',
            '追逐': '有什么在身后',
            '悬疑': '线索突然中断',
            '荒诞': '重力方向反了',
            '怀旧': '旧照片掉在地上',
        }.get(dream_type, '场景模糊地展开')
        frag_phrase = '，'.join(chosen) if chosen else '光影'
        return f"{intro}。{frag_phrase}。"

    def _compute_energy_delta(self, mood: str, label: str, dream_type: str) -> float:
        delta = 0.0
        if mood in ('平静', '温暖'):
            delta += 0.1
        elif mood in ('焦虑', '忧伤', '不安'):
            delta -= 0.15
        if '噩梦' in dream_type or '追逐' in dream_type or '悬疑' in dream_type:
            delta -= 0.1
        if '好梦' in label or '清晰' in label:
            delta += 0.05
        return round(max(-0.3, min(0.3, delta)), 3)

    def _compose_afterglow(self, mood: str, dream_type: str) -> str:
        return f"梦醒时心绪 {mood}，残留 {dream_type} 的余韵。"

    def _compose_diary_body(self, recent_dreams: List[Dict[str, Any]],
                            fragments: List[str], state_title: str) -> str:
        """叙事体裁日记：与摘要区别——更长、更具文学性。"""
        # 注意：叙事体裁日记正文走主模型（LLMHelper.call_main_model）。
        # 若环境无 LLM 凭据（开发/测试），降级到模板拼装。
        prompt_vars = {
            'character_name': self.character_info.get('character_name', 'AI'),
            'state_title': state_title,
            'recent_dream_types': ', '.join(d.get('dream_type', '?') for d in recent_dreams[:3]) or '无',
            'fragments': '，'.join(fragments[:5]),
        }
        try:
            system_prompt = self.prompt_manager.get_system_prompt(
                'daily_diary', prompt_vars
            )
            user_msg = f"请基于今日状态「{state_title}」与近期梦境/碎片，写一篇 200-400 字的叙事日记。"
            body = LLMHelper.call_main_model(
                system_prompt=system_prompt,
                user_message=user_msg
            )
        except Exception as e:
            debug_logger.log_error('DreamDiaryManager', f'主模型生成日记失败，降级: {e}', e)
            body = (
                f"今天的状态是「{state_title}」。"
                f"近几天的梦境像一些散落的胶片——"
                f"「{'，'.join(fragments[:3]) or '光影'}」——"
                f"在脑海里反复出现。"
                "把这一切写下来的瞬间，好像又把它们重新走过一遍。"
            )
        return body.strip()

    def _compose_diary_title(self, state_title: str) -> str:
        return f"{state_title}的一天"

    def _infer_diary_mood(self, recent_dreams: List[Dict[str, Any]]) -> str:
        if not recent_dreams:
            return '平静'
        return recent_dreams[0].get('mood', '平静') or '平静'

    def _compute_diary_tags(self, recent_dreams: List[Dict[str, Any]],
                            state_title: str, body: str) -> List[str]:
        tags = set()
        if '失眠' in body or '睡不着' in body:
            tags.add('失眠')
        if '生病' in body or '不舒服' in body:
            tags.add('生病')
        if '累' in body or '疲惫' in body:
            tags.add('低能量')
        if recent_dreams and recent_dreams[0].get('mood') in ('平静', '温暖'):
            tags.add('好梦')
        if state_title in ('焦虑',):
            tags.add('焦虑')
        if not tags:
            tags.add('一般')
        return sorted(tags)
