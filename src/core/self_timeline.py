"""
自我时间线聚合模块
聚合多来源输出 Bot 自我时间线（按相关性评分排序）。
来源：日程 / 对话 / 创作（P3）/ 记忆 / 梦境日记（P1）

参考架构：spec §Exploratory → SelfTimelineAggregator
"""

import os
import re
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional

from src.core.database_manager import DatabaseManager
from src.tools.debug_logger import get_debug_logger

ENABLE_SELF_TIMELINE = os.getenv('ENABLE_SELF_TIMELINE', 'false').lower() == 'true'

debug_logger = get_debug_logger()


class SelfTimelineAggregator:
    """
    自我时间线聚合器。
    - aggregate_timeline(user, query, now): 输出按相关性评分排序的 list[dict]
    - ChatAgent.chat() 检测到时间线询问关键词时调用
    """

    QUERY_KEYWORDS = [
        r'你今天', r'你昨天', r'你最近', r'你早上', r'你下午',
        r'你晚上', r'你这周', r'你这几天', r'你上午',
    ]

    def __init__(self, db_manager: DatabaseManager = None,
                 schedule_manager=None,
                 long_term_memory=None,
                 creative_writer=None,
                 knowledge_base=None,
                 dream_diary=None):
        self.db = db_manager or DatabaseManager()
        self.schedule_manager = schedule_manager
        self.long_term_memory = long_term_memory
        self.creative_writer = creative_writer
        self.knowledge_base = knowledge_base
        self.dream_diary = dream_diary
        self.enabled = ENABLE_SELF_TIMELINE

    def is_timeline_query(self, text: str) -> bool:
        if not text:
            return False
        return any(re.search(p, text) for p in self.QUERY_KEYWORDS)

    def aggregate_timeline(self, user: str, query: str,
                           now: Optional[datetime] = None,
                           window_days: int = 7) -> List[Dict[str, Any]]:
        """
        聚合多来源时间线事件。
        每条 {source, content, time, score, metadata}
        """
        if not self.enabled:
            return []
        now = now or datetime.now()
        events: List[Dict[str, Any]] = []
        # 1) 日程
        events.extend(self._from_schedule(user, now, window_days))
        # 2) 对话
        events.extend(self._from_conversation(user, now, window_days))
        # 3) 创作
        events.extend(self._from_creative(user, now, window_days))
        # 4) 记忆
        events.extend(self._from_knowledge(user, now, window_days))
        # 5) 梦境日记
        events.extend(self._from_dream_diary(user, now, window_days))
        # 相关性评分
        for e in events:
            e['score'] = self._score_event(e, query, now)
        events.sort(key=lambda e: e['score'], reverse=True)
        return events

    def format_for_prompt(self, events: List[Dict[str, Any]],
                          limit: int = 5) -> str:
        if not events:
            return ""
        lines = ["【我最近在做的事】"]
        for e in events[:limit]:
            t = e.get('time', '')
            src = e.get('source', '?')
            content = e.get('content', '')[:80]
            lines.append(f"• [{src}] {t}：{content}")
        return "\n".join(lines)

    # ===== 来源 =====

    def _from_schedule(self, user: str, now: datetime,
                       window_days: int) -> List[Dict[str, Any]]:
        if not self.schedule_manager:
            return []
        try:
            start = (now - timedelta(days=window_days)).isoformat()
            end = now.isoformat()
            schedules = self.schedule_manager.get_schedules_by_time_range(
                start, end, queryable_only=True
            )
        except Exception as e:
            debug_logger.log_error('SelfTimeline', f'日程聚合失败: {e}', e)
            return []
        return [{
            'source': 'schedule',
            'content': f"{s.title}：{s.description or ''}",
            'time': s.start_time if hasattr(s, 'start_time') else '',
            'metadata': {'schedule_id': getattr(s, 'schedule_id', '')},
        } for s in schedules]

    def _from_conversation(self, user: str, now: datetime,
                           window_days: int) -> List[Dict[str, Any]]:
        try:
            messages = self.db.get_short_term_messages()
        except Exception:
            return []
        events = []
        for m in messages:
            try:
                t = m.get('timestamp', '')
                if not t:
                    continue
                msg_dt = datetime.fromisoformat(t)
                if (now - msg_dt) > timedelta(days=window_days):
                    continue
                content = (m.get('content', '') or '')[:120]
                if m.get('role') == 'user':
                    content = f"用户说：{content}"
                else:
                    content = f"我回复：{content}"
                events.append({
                    'source': 'conversation',
                    'content': content,
                    'time': t,
                    'metadata': {'role': m.get('role')},
                })
            except (ValueError, TypeError):
                continue
        return events

    def _from_creative(self, user: str, now: datetime,
                       window_days: int) -> List[Dict[str, Any]]:
        try:
            projects = self.db.list_creative_projects(limit=20)
        except Exception:
            return []
        events = []
        for p in projects:
            try:
                t = p.get('created_at', '')
                if not t:
                    continue
                dt = datetime.fromisoformat(t)
                if (now - dt) > timedelta(days=window_days):
                    continue
                events.append({
                    'source': 'creative',
                    'content': f"创作项目《{p.get('title', '?')}》（{p.get('status', '?')}）",
                    'time': t,
                    'metadata': {'project_uuid': p.get('uuid')},
                })
            except (ValueError, TypeError):
                continue
        return events

    def _from_knowledge(self, user: str, now: datetime,
                        window_days: int) -> List[Dict[str, Any]]:
        try:
            # 简化：列出最近 10 条实体
            cursor = self.db.get_connection().__enter__()
            rows = cursor.execute(
                'SELECT * FROM entities ORDER BY created_at DESC LIMIT 10'
            ).fetchall()
        except Exception:
            return []
        events = []
        for r in rows:
            try:
                t = r['created_at']
                dt = datetime.fromisoformat(t)
                if (now - dt) > timedelta(days=window_days):
                    continue
                events.append({
                    'source': 'knowledge',
                    'content': f"认识了「{r['name']}」",
                    'time': t,
                    'metadata': {'entity_uuid': r['uuid']},
                })
            except (KeyError, ValueError, TypeError):
                continue
        return events

    def _from_dream_diary(self, user: str, now: datetime,
                          window_days: int) -> List[Dict[str, Any]]:
        events = []
        try:
            dreams = self.db.get_dream_records(limit=20) if hasattr(self.db, 'get_dream_records') else []
        except Exception:
            dreams = []
        for d in dreams:
            try:
                t = d.get('date') or d.get('created_at', '')
                if not t:
                    continue
                dt = datetime.fromisoformat(t)
                if (now - dt) > timedelta(days=window_days):
                    continue
                events.append({
                    'source': 'dream_diary',
                    'content': f"梦境：{d.get('content', '')[:60]}",
                    'time': t,
                    'metadata': {'type': d.get('dream_type', '')},
                })
            except (ValueError, TypeError):
                continue
        return events

    # ===== 相关性评分 =====

    def _score_event(self, event: Dict[str, Any], query: str, now: datetime) -> float:
        score = 0.0
        # 时间衰减：越近越高
        try:
            t = datetime.fromisoformat(event.get('time', ''))
            delta_h = max(0.0, (now - t).total_seconds() / 3600.0)
            score += max(0.0, 1.0 - delta_h / (24 * 7))
        except (ValueError, TypeError):
            pass
        # 关键词匹配
        q_tokens = set(re.findall(r'[\u4e00-\u9fffA-Za-z0-9]+', query or ''))
        e_tokens = set(re.findall(r'[\u4e00-\u9fffA-Za-z0-9]+', event.get('content', '')))
        if q_tokens and e_tokens:
            overlap = len(q_tokens & e_tokens)
            score += min(1.0, overlap * 0.2)
        # 来源权重
        weight = {
            'conversation': 0.3,
            'schedule': 0.4,
            'creative': 0.2,
            'dream_diary': 0.1,
            'knowledge': 0.1,
        }.get(event.get('source', ''), 0.1)
        score += weight
        return round(score, 3)
