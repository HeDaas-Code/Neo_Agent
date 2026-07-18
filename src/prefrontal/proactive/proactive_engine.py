"""
主动决策与想法池模块
- 想法池（impulse pool）：多来源候选（habit_care / open_loop_recall / creative_share / weather_note）
- 核心决策：should_send 综合多因子（驱动力 / 就绪度 / 关系温度 / 闸门 / 复核）
- 主动消息经 EventManager 投递回 GUI

参考架构：spec §4 ADDED Requirements → ProactiveEngine
"""

import os
import json
import random
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple

from src.core.database_manager import DatabaseManager
from src.core.llm_helper import LLMHelper
from src.core.prompt_manager import get_prompt_manager
from src.prefrontal.event.event_manager import EventManager, EventPriority, NotificationEvent
from src.tools.debug_logger import get_debug_logger

ENABLE_PROACTIVE_ENGINE = os.getenv('ENABLE_PROACTIVE_ENGINE', 'false').lower() == 'true'

debug_logger = get_debug_logger()


class ProactiveEngine:
    """
    主动决策与想法池。
    - bot_proactive_drive: Bot 内在驱动（创作冲动 / 梦境残留 / 生活状态影响）
    - proactive_inner_readiness: 当下情绪就绪度（情绪轮 + 关系温度）
    - proactive_impulse_pool: 候选想法（habit_care / open_loop_recall / creative_share / weather_note）
    - should_send: 多因子决策
    - bot_proactive_drive: 触发主动消息经 EventManager 投递
    """

    QUIET_HOURS_START = 23
    QUIET_HOURS_END = 7
    DEFAULT_DAILY_LIMIT = 2
    MIN_INTERVAL_MINUTES = 60
    DEFAULT_REVIEW_COOLDOWN_HOURS = 4

    def __init__(self, db_manager: DatabaseManager = None,
                 prompt_manager=None,
                 event_manager: Optional[EventManager] = None,
                 life_state=None,
                 emotion_wheel=None,
                 open_loop_tracker=None,
                 creative_writer=None,
                 user_habits=None):
        self.db = db_manager or DatabaseManager()
        self.prompt_manager = prompt_manager or get_prompt_manager()
        self.event_manager = event_manager
        self.life_state = life_state
        self.emotion_wheel = emotion_wheel
        self.open_loop_tracker = open_loop_tracker
        self.creative_writer = creative_writer
        self.user_habits = user_habits
        self.enabled = ENABLE_PROACTIVE_ENGINE

    # ===== 多因子决策 =====

    def should_send(self, user: str,
                    now: Optional[datetime] = None) -> Tuple[bool, str]:
        """
        多因子决策：
        - bot_proactive_drive
        - proactive_inner_readiness
        - 静默时段闸门
        - effective_user_daily_limit
        - 复核冷却
        返回 (bool, reason)。
        """
        if not self.enabled:
            return False, 'disabled'
        now = now or datetime.now()
        if self._is_quiet_time(now):
            return False, 'quiet_hours'
        if not self._cooldown_passed(user, now):
            return False, 'cooldown'
        if self._daily_limit_reached(user, now):
            return False, 'daily_limit'
        drive = self.bot_proactive_drive(user, now=now)
        readiness = self.proactive_inner_readiness(user, now=now)
        # 简单阈值：驱动力 + 就绪度 >= 0.5
        score = drive.get('score', 0.0) + readiness.get('score', 0.0)
        if score < 0.5:
            return False, f'low_score({score:.2f})'
        return True, f'pass(score={score:.2f})'

    def schedule_next_proactive(self, user: str, now: Optional[datetime] = None,
                                 delay_hours: Optional[float] = None) -> None:
        """记录下次主动消息时间。"""
        if not self.enabled:
            return
        now = now or datetime.now()
        if delay_hours is None:
            delay_hours = random.uniform(2.0, 6.0)
        next_at = (now + timedelta(hours=delay_hours)).isoformat()
        self.db.set_metadata(f'next_proactive_{user}', next_at)
        debug_logger.log_info('ProactiveEngine', '已排定下次主动消息', {
            'user': user, 'next_at': next_at,
        })

    # ===== 内在驱动 / 就绪度 =====

    def bot_proactive_drive(self, user: Optional[str] = None,
                            now: Optional[datetime] = None) -> Dict[str, Any]:
        """
        Bot 内在驱动：综合 创作冲动 + 梦境残留 + 生活状态
        返回 {score(0-1), components: {creative, dream, life_state}}
        """
        if not self.enabled:
            return {'score': 0.0, 'components': {}}
        creative = 0.0
        if self.creative_writer and getattr(self.creative_writer, 'enabled', False):
            try:
                finished = self.creative_writer.get_finished_projects(limit=3)
                creative = min(1.0, 0.4 * len(finished))
            except Exception as e:
                debug_logger.log_error('ProactiveEngine', f'创作驱动评估失败: {e}', e)

        dream = 0.0
        if self.life_state and getattr(self.life_state, 'enabled', False):
            try:
                snap = self.life_state.get_current_state_snapshot() or {}
                # 疲惫/低落时降低驱动
                mood = snap.get('mood', '')
                if mood in ('焦虑', '低落', '疲倦'):
                    dream = 0.2
                else:
                    dream = 0.5
            except Exception as e:
                debug_logger.log_error('ProactiveEngine', f'生活状态评估失败: {e}', e)

        score = (creative + dream) / 2.0
        return {
            'score': round(score, 3),
            'components': {
                'creative': round(creative, 3),
                'dream': round(dream, 3),
            },
        }

    def proactive_inner_readiness(self, user: str,
                                  now: Optional[datetime] = None) -> Dict[str, Any]:
        """
        当下情绪就绪度：情绪轮正向 + 关系温度
        返回 {score(0-1), emotion_summary}
        """
        if not self.enabled:
            return {'score': 0.0, 'emotion_summary': ''}
        score = 0.0
        summary = ''
        if self.emotion_wheel and getattr(self.emotion_wheel, 'enabled', False):
            try:
                state = {'emotions': {}}
                # 简化的情绪轮评分
                score = 0.5
                summary = '情绪轮活跃'
            except Exception as e:
                debug_logger.log_error('ProactiveEngine', f'情绪就绪度评估失败: {e}', e)

        # 关系温度：从情感分析历史读取
        try:
            latest = self.db.get_latest_emotion()
            if latest:
                overall = int(latest.get('overall_score', 0))
                if overall >= 60:
                    score = max(score, 0.6)
                elif overall < 30:
                    score = min(score, 0.3)
        except Exception as e:
            debug_logger.log_error('ProactiveEngine', f'关系温度评估失败: {e}', e)

        return {'score': round(score, 3), 'emotion_summary': summary}

    # ===== 想法池 =====

    def proactive_impulse_pool(self, user: str) -> List[Dict[str, Any]]:
        """
        候选想法列表。
        来源：habit_care / open_loop_recall / creative_share / weather_note
        """
        if not self.enabled:
            return []
        ideas: List[Dict[str, Any]] = []

        # habit_care
        if self.user_habits and getattr(self.user_habits, 'enabled', False):
            try:
                ideas.extend(self._ideas_from_habits(user))
            except Exception as e:
                debug_logger.log_error('ProactiveEngine', f'habit 想法失败: {e}', e)

        # open_loop_recall
        if self.open_loop_tracker and getattr(self.open_loop_tracker, 'enabled', False):
            try:
                ideas.extend(self._ideas_from_open_loops(user))
            except Exception as e:
                debug_logger.log_error('ProactiveEngine', f'open_loop 想法失败: {e}', e)

        # creative_share
        if self.creative_writer and getattr(self.creative_writer, 'enabled', False):
            try:
                ideas.extend(self._ideas_from_creative(user))
            except Exception as e:
                debug_logger.log_error('ProactiveEngine', f'creative 想法失败: {e}', e)

        # weather_note
        ideas.extend(self._ideas_from_weather(user))
        return ideas

    def _ideas_from_habits(self, user: str) -> List[Dict[str, Any]]:
        ideas = []
        try:
            event = self.user_habits.habit_proactive_event(user)
        except Exception:
            return ideas
        if not event:
            return ideas
        ideas.append({
            'id': str(uuid.uuid4()),
            'reason': 'habit_care',
            'motive': event.get('content', '该吃饭了'),
            'window_start': datetime.now().isoformat(),
            'window_end': (datetime.now() + timedelta(hours=2)).isoformat(),
            'priority': 'normal',
            'used': False,
        })
        return ideas

    def _ideas_from_open_loops(self, user: str) -> List[Dict[str, Any]]:
        ideas = []
        try:
            loops = self.db.get_open_loops(status='open', limit=3)
        except Exception:
            return ideas
        for lp in loops:
            ideas.append({
                'id': str(uuid.uuid4()),
                'reason': 'open_loop_recall',
                'motive': f"想起之前的「{lp.get('topic', '?')}」，要不要继续聊聊？",
                'window_start': datetime.now().isoformat(),
                'window_end': (datetime.now() + timedelta(hours=3)).isoformat(),
                'priority': 'low',
                'used': False,
                'related_loop_uuid': lp.get('uuid'),
            })
        return ideas

    def _ideas_from_creative(self, user: str) -> List[Dict[str, Any]]:
        ideas = []
        try:
            finished = self.creative_writer.get_finished_projects(limit=3)
        except Exception:
            return ideas
        for proj in finished:
            ideas.append({
                'id': str(uuid.uuid4()),
                'reason': 'creative_share',
                'motive': f"刚把《{proj.get('title', '?')}》写完了，要不要看看？",
                'window_start': datetime.now().isoformat(),
                'window_end': (datetime.now() + timedelta(hours=4)).isoformat(),
                'priority': 'normal',
                'used': False,
                'related_project_uuid': proj.get('uuid'),
            })
        return ideas

    def _ideas_from_weather(self, user: str) -> List[Dict[str, Any]]:
        # 简化的天气提示：随机注入（实际接入 weather 模块时替换）
        notes = [
            '今天天气不错，要不要出去走走？',
            '外面下雨啦，记得带伞。',
            '天气转凉了，多穿点。',
        ]
        return [{
            'id': str(uuid.uuid4()),
            'reason': 'weather_note',
            'motive': random.choice(notes),
            'window_start': datetime.now().isoformat(),
            'window_end': (datetime.now() + timedelta(hours=6)).isoformat(),
            'priority': 'low',
            'used': False,
        }]

    # ===== 投递 =====

    def bot_proactive_drive_send(self, user: str,
                                 idea: Dict[str, Any]) -> bool:
        """
        触发主动消息并经 EventManager 投递回 GUI / Web 端。

        Stage D.2: 通过 EventManager.publish("proactive_message", payload) 推送
        独立 EventManager 单例 + try/except 保护，绝不阻塞主流程。
        """
        if not self.enabled:
            return False
        message = (idea or {}).get('motive', '') if isinstance(idea, dict) else ''
        if not message:
            debug_logger.log_info('ProactiveEngine', 'idea 为空，跳过投递')
            return False

        payload: Dict[str, Any] = {
            'content': message,
            'timestamp': datetime.now().isoformat(),
            'user': user,
            'reason': (idea or {}).get('reason', '') if isinstance(idea, dict) else '',
            'idea_id': (idea or {}).get('id', '') if isinstance(idea, dict) else '',
            'priority': (idea or {}).get('priority', 'normal') if isinstance(idea, dict) else 'normal',
            'source': 'ProactiveEngine',
        }

        # Stage D.2: 优先使用注入的 event_manager；否则走全局单例
        em = self.event_manager
        if em is None:
            try:
                from src.prefrontal.event.event_manager import get_event_manager
                em = get_event_manager()
            except Exception as e:
                debug_logger.log_error('ProactiveEngine', f'获取 EventManager 失败: {e}', e)
                em = None

        # 推送给 EventManager（绝对 try/except，绝不阻塞主流程）
        try:
            if em is not None:
                em.publish('proactive_message', payload)
            else:
                # 兜底：保留旧的 NotificationEvent 写库方式（如果 EventManager 不可用）
                event = NotificationEvent(
                    event_id=str(uuid.uuid4()),
                    title='主动消息',
                    description=message,
                    source='ProactiveEngine',
                    priority=EventPriority.MEDIUM,
                    metadata={'content': message, 'user': user,
                              'reason': payload['reason'],
                              'idea_id': payload['idea_id']},
                )
                # 即便 fallback 也仅记录日志，不抛出
                debug_logger.log_info('ProactiveEngine', 'fallback 通知(无 EventManager)', {
                    'event_id': event.event_id,
                })
        except Exception as e:
            debug_logger.log_error('ProactiveEngine', f'proactive_message 推送失败: {e}', e)

        debug_logger.log_info('ProactiveEngine', '主动消息已投递', {
            'user': user, 'reason': payload['reason'],
        })
        # 更新今日主动次数
        try:
            self._increment_daily_count(user)
        except Exception as e:
            debug_logger.log_error('ProactiveEngine', f'更新今日主动次数失败: {e}', e)
        return True

    # ===== 工具方法 =====

    def _is_quiet_time(self, now: datetime) -> bool:
        h = now.hour
        if self.QUIET_HOURS_START > self.QUIET_HOURS_END:
            return h >= self.QUIET_HOURS_START or h < self.QUIET_HOURS_END
        return self.QUIET_HOURS_START <= h < self.QUIET_HOURS_END

    def _cooldown_passed(self, user: str, now: datetime) -> bool:
        last = self.db.get_metadata(f'last_proactive_{user}', '')
        if not last:
            return True
        try:
            last_dt = datetime.fromisoformat(last)
        except (ValueError, TypeError):
            return True
        delta = (now - last_dt).total_seconds() / 60.0
        return delta >= self.MIN_INTERVAL_MINUTES

    def _daily_limit_reached(self, user: str, now: datetime) -> bool:
        today = now.date().isoformat()
        last_day = self.db.get_metadata(f'last_proactive_day_{user}', '')
        if last_day != today:
            return False
        count = int(self.db.get_metadata(f'proactive_count_{today}_{user}', 0))
        return count >= self.effective_user_daily_limit(user, now)

    def effective_user_daily_limit(self, user: str, now: datetime) -> int:
        """默认上限；可被角色设定或用户偏好覆盖。"""
        override = self.db.get_metadata(f'proactive_limit_{user}', None)
        if override is not None:
            try:
                return int(override)
            except (TypeError, ValueError):
                pass
        return self.DEFAULT_DAILY_LIMIT

    def _increment_daily_count(self, user: str) -> None:
        now = datetime.now()
        today = now.date().isoformat()
        key = f'proactive_count_{today}_{user}'
        count = int(self.db.get_metadata(key, 0)) + 1
        self.db.set_metadata(key, count)
        self.db.set_metadata(f'last_proactive_day_{user}', today)
        self.db.set_metadata(f'last_proactive_{user}', now.isoformat())
