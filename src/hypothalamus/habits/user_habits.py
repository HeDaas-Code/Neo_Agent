"""
用户行为习惯跟踪模块
- 提取用户作息 / 饮食 / 工作 / 娱乐 4 类行为习惯
- 准入规则：同一习惯候选需在 ≥2 个不同自然日被提取才进入 qualified_habits
- 为 ProactiveEngine.proactive_impulse_pool 提供 habit_care 想法来源

参考架构：spec §Exploratory → UserHabitTracker
"""

import os
import json
import uuid
from datetime import datetime
from typing import Dict, List, Any, Optional

from src.core.database_manager import DatabaseManager
from src.core.llm_helper import LLMHelper
from src.tools.debug_logger import get_debug_logger

ENABLE_USER_HABITS = os.getenv('ENABLE_USER_HABITS', 'false').lower() == 'true'

debug_logger = get_debug_logger()


class UserHabitTracker:
    """
    用户行为习惯跟踪器。
    - update_from_message: 从用户消息中提取习惯候选
    - qualified_habits: 返回已通过 ≥2 自然日准入规则的习惯
    - habit_proactive_event: 触发习惯相关主动事件
    - format_for_schedule: 渲染为可注入 schedule 的格式
    """

    CATEGORIES = ['作息', '饮食', '工作', '娱乐']
    MIN_DAYS_FOR_QUALIFY = 2

    def __init__(self, db_manager: DatabaseManager = None):
        self.db = db_manager or DatabaseManager()
        self.enabled = ENABLE_USER_HABITS

    def update_from_message(self, user: str, text: str) -> List[Dict[str, Any]]:
        """
        从用户消息中提取习惯候选。
        返回 [{category, content, observed_date}, ...]（仅当天新观察到的）。
        """
        if not self.enabled or not text:
            return []
        # 极简规则：基于关键词分类
        text_lower = text.lower()
        observed_date = datetime.now().date().isoformat()
        candidates = []
        # 作息
        if any(kw in text for kw in ['起床', '睡觉', '晚安', '早起', '熬夜', '失眠']):
            candidates.append({'category': '作息', 'content': text[:80]})
        # 饮食
        if any(kw in text for kw in ['吃饭', '早餐', '午餐', '晚餐', '宵夜', '喝', '咖啡', '奶茶', '饿了', '饱']):
            candidates.append({'category': '饮食', 'content': text[:80]})
        # 工作
        if any(kw in text for kw in ['加班', '开会', '项目', '任务', '工作', '上班', '下班', '出差']):
            candidates.append({'category': '工作', 'content': text[:80]})
        # 娱乐
        if any(kw in text for kw in ['看', '玩', '听', '游戏', '电影', '剧', '音乐', '运动', '跑步', '逛街']):
            candidates.append({'category': '娱乐', 'content': text[:80]})
        # 存储
        for c in candidates:
            self.db.set_metadata(
                f'habit_{user}_{c["category"]}_{observed_date}_{uuid.uuid4().hex[:8]}',
                json.dumps({
                    'category': c['category'],
                    'content': c['content'],
                    'observed_date': observed_date,
                }, ensure_ascii=False)
            )
        return [{**c, 'observed_date': observed_date} for c in candidates]

    def qualified_habits(self, user: str) -> List[Dict[str, Any]]:
        """
        返回已通过 ≥ MIN_DAYS_FOR_QUALIFY 个不同自然日准入规则的习惯。
        """
        if not self.enabled:
            return []
        all_meta = self.db.list_metadata_keys(prefix=f'habit_{user}_')
        by_key: Dict[str, Dict[str, set]] = {}
        for key in all_meta:
            value = self.db.get_metadata(key, None)
            if not value:
                continue
            try:
                data = json.loads(value)
            except (TypeError, ValueError):
                continue
            cat = data.get('category', '其他')
            content = data.get('content', '')[:80]
            date = data.get('observed_date', '')
            key2 = f'{cat}::{content}'
            if key2 not in by_key:
                by_key[key2] = {'category': cat, 'content': content, 'dates': set()}
            by_key[key2]['dates'].add(date)
        qualified = []
        for k, v in by_key.items():
            if len(v['dates']) >= self.MIN_DAYS_FOR_QUALIFY:
                qualified.append({
                    'category': v['category'],
                    'content': v['content'],
                    'observed_dates': sorted(v['dates']),
                })
        return qualified

    def habit_proactive_event(self, user: str,
                              now: Optional[datetime] = None) -> Optional[Dict[str, Any]]:
        """
        根据当前时间 + 已确认习惯触发一条主动事件。
        返回 {category, content, trigger_at} 或 None。
        """
        if not self.enabled:
            return None
        now = now or datetime.now()
        h = now.hour
        # 简单的时段映射
        target_category = None
        if 6 <= h <= 9:
            target_category = '饮食'  # 早餐
        elif 11 <= h <= 13:
            target_category = '饮食'  # 午餐
        elif 17 <= h <= 19:
            target_category = '饮食'  # 晚餐
        elif 22 <= h <= 24 or 0 <= h <= 2:
            target_category = '作息'  # 提醒睡觉
        elif 14 <= h <= 18:
            target_category = '娱乐'  # 下午休闲
        else:
            target_category = '工作'
        habits = self.qualified_habits(user)
        matched = [h2 for h2 in habits if h2.get('category') == target_category]
        if not matched:
            return None
        # 取最新观察
        picked = sorted(matched, key=lambda h2: h2['observed_dates'][-1], reverse=True)[0]
        return {
            'category': picked['category'],
            'content': picked['content'],
            'trigger_at': now.isoformat(),
        }

    def format_for_schedule(self, limit: int = 8) -> str:
        """渲染为 prompt 文本，注入 schedule 上下文。"""
        if not self.enabled:
            return ""
        # 不再传 user（无 GUI 用户上下文）— 改为从 metadata 全局读
        all_meta = self.db.list_metadata_keys(prefix='habit_')
        seen = set()
        lines = []
        for key in all_meta:
            value = self.db.get_metadata(key, None)
            if not value:
                continue
            try:
                data = json.loads(value)
            except (TypeError, ValueError):
                continue
            k = f'{data.get("category")}::{data.get("content")}'
            if k in seen:
                continue
            seen.add(k)
            lines.append(f"• [{data.get('category')}] {data.get('content')[:40]}")
            if len(lines) >= limit:
                break
        if not lines:
            return ""
        return "【用户行为习惯】\n" + "\n".join(lines)
