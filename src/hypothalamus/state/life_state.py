"""
生活状态机管理模块
管理 Bot 当日精力 / 心情 / 健康状态的状态机。
实现要点：
- ensure_daily_state: 每日首次访问时自动生成状态快照（含 conditions 与 transition_options）
- generate_state_conditions: 通过 LLMHelper.call_tool_model 生成结构化状态条件（temperature 0.3）
- get_current_state_snapshot: 拉取当日状态
- apply_transition: 按 transition_options 的权重决定下一状态
- format_state_for_prompt: 渲染为 prompt 文本（通过 PromptManager）
- 反向消费：DreamDiaryManager.generate_dream_pick 的 energy_delta 喂入次日 energy 基线

参考架构：spec §1 ADDED Requirements → LifeStateManager
"""

import os
import json
import random
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional

from src.core.database_manager import DatabaseManager
from src.core.llm_helper import LLMHelper
from src.core.prompt_manager import get_prompt_manager
from src.tools.debug_logger import get_debug_logger

ENABLE_LIFE_STATE = os.getenv('ENABLE_LIFE_STATE', 'false').lower() == 'true'

debug_logger = get_debug_logger()


class LifeStateManager:
    """
    生活状态机管理器
    每日生成一次状态快照，按 transition_options 决定状态转移。
    """

    STATE_TITLES = ['常态', '疲惫', '兴奋', '低落', '焦虑', '放松', '专注', '饥饿']
    DEFAULT_MOODS = ['平静', '愉快', '低落', '焦虑', '兴奋', '疲倦', '温暖']
    DEFAULT_HEALTHS = ['健康', '轻微不适', '生病', '康复中']
    TRANSITION_TRIGGERS = ['sleep_debt', 'body_cycle', 'meal_missed', 'weather_shift',
                           'good_news', 'bad_news', 'idle_long', 'intense_talk']

    def __init__(self, db_manager: DatabaseManager = None,
                 prompt_manager=None,
                 character_info: Optional[Dict[str, str]] = None):
        """
        Args:
            db_manager: 共享数据库管理器
            prompt_manager: 提示词管理器（默认走单例）
            character_info: 角色设定信息（用于状态生成时的角色一致性）
        """
        self.db = db_manager or DatabaseManager()
        self.prompt_manager = prompt_manager or get_prompt_manager()
        self.character_info = character_info or {}
        self.enabled = ENABLE_LIFE_STATE
        self._last_dream_energy_delta = 0.0

    def ensure_daily_state(self, force: bool = False,
                           weather: Optional[Dict[str, Any]] = None,
                           now: Optional[datetime] = None) -> Dict[str, Any]:
        """
        每日首次访问时生成状态快照；若当日已存在则直接返回（除非 force=True）。
        """
        if not self.enabled:
            return self._get_or_create_default(now)

        now = now or datetime.now()
        date_str = now.date().isoformat()

        if not force:
            existing = self.db.get_life_state_daily(date_str)
            if existing:
                return existing

        conditions = self.generate_state_conditions(weather=weather, now=now)
        energy = self._resolve_energy(conditions, now)
        mood = self._resolve_mood(conditions)
        health = self._resolve_health(conditions)
        state_title = self._resolve_state_title(conditions, energy, mood)
        transition_options = self._build_transition_options(conditions)

        success = self.db.upsert_life_state_daily(
            date=date_str, energy=energy, mood=mood,
            state_title=state_title, health=health,
            conditions=conditions, transition_options=transition_options,
            energy_delta=self._last_dream_energy_delta
        )
        self._last_dream_energy_delta = 0.0

        if not success:
            return self._get_or_create_default(now)

        result = self.db.get_life_state_daily(date_str) or {}
        debug_logger.log_info('LifeStateManager', '生成当日状态', {
            'date': date_str, 'energy': energy, 'mood': mood,
            'state_title': state_title, 'conditions_count': len(conditions)
        })
        return result

    def generate_state_conditions(self, weather: Optional[Dict[str, Any]] = None,
                                  now: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """
        调用工具模型生成结构化的"今日状态条件"列表。
        每条 condition 含 name / weight / category / note。
        """
        now = now or datetime.now()
        prompt_vars = {
            'character_name': self.character_info.get('character_name', 'AI'),
            'date': now.date().isoformat(),
            'weather': (weather or {}).get('summary', '晴') if weather else '晴',
            'dream_energy_delta': self._last_dream_energy_delta,
        }

        try:
            system_prompt = self.prompt_manager.get_system_prompt(
                'life_state', prompt_vars
            )
        except Exception:
            system_prompt = self._fallback_conditions_prompt()

        user_msg = f"今日 {prompt_vars['date']}，天气 {prompt_vars['weather']}。请给出 3-5 条状态条件 JSON。"

        try:
            raw = LLMHelper.call_tool_model(
                system_prompt=system_prompt,
                user_message=user_msg,
                temperature=0.3,
                max_tokens=512
            )
            conditions = self._parse_conditions(raw)
        except Exception as e:
            debug_logger.log_error('LifeStateManager', f'生成状态条件失败: {e}', e)
            conditions = self._default_conditions(now)

        if not conditions:
            conditions = self._default_conditions(now)
        return conditions

    def get_current_state_snapshot(self, now: Optional[datetime] = None) -> Dict[str, Any]:
        """
        获取当前状态快照（若当日不存在则确保生成）。
        """
        now = now or datetime.now()
        return self.ensure_daily_state(now=now)

    def apply_transition(self, current: Dict[str, Any],
                         transition_options: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """
        根据 transition_options 权重决定下一状态。
        transition_options 每条：{trigger, target_state, weight}。
        """
        options = transition_options or current.get('transition_options', [])
        if not options:
            return current

        weights = [max(0.0, float(opt.get('weight', 0.5))) for opt in options]
        total = sum(weights)
        if total <= 0:
            return current
        pick = random.random() * total
        cumulative = 0.0
        chosen = options[0]
        for opt, w in zip(options, weights):
            cumulative += w
            if pick <= cumulative:
                chosen = opt
                break

        new_state = dict(current)
        new_state['state_title'] = chosen.get('target_state', current.get('state_title', '常态'))
        new_state['last_transition_trigger'] = chosen.get('trigger', 'unknown')

        date_str = current.get('date') or datetime.now().date().isoformat()
        self.db.upsert_life_state_daily(
            date=date_str,
            energy=float(current.get('energy', 0.7)),
            mood=current.get('mood', '平静'),
            state_title=new_state['state_title'],
            health=current.get('health', '健康'),
            conditions=current.get('conditions', []),
            transition_options=options,
            energy_delta=0.0,
        )
        return new_state

    def format_state_for_prompt(self, now: Optional[datetime] = None) -> str:
        """
        将当前状态渲染为 prompt 文本（与 generate_tone_prompt 平行注入）。
        """
        if not self.enabled:
            return ""
        snapshot = self.get_current_state_snapshot(now=now)
        if not snapshot:
            return ""

        template = self.prompt_manager.load_prompt('system', 'life_state')
        vars_ = {
            'energy': f"{snapshot.get('energy', 0.7):.2f}",
            'mood': snapshot.get('mood', '平静'),
            'state_title': snapshot.get('state_title', '常态'),
            'health': snapshot.get('health', '健康'),
            'date': snapshot.get('date', datetime.now().date().isoformat()),
        }
        return self.prompt_manager.render_prompt(template, vars_)

    def consume_dream_energy_delta(self, energy_delta: float) -> None:
        """
        DreamDiaryManager 调用此方法将梦境的 energy_delta 喂给次日精力基线。
        """
        self._last_dream_energy_delta = float(energy_delta)

    # ==================== P3-E: body_cycle 子模块（女性人格可选） ====================

    def body_cycle(self, character_info: Optional[Dict[str, Any]] = None,
                   now: Optional[datetime] = None) -> Dict[str, Any]:
        """
        仅当角色为女性人格时启用。
        返回 {'enabled': bool, 'phase': str, 'energy_modifier': float}
        """
        info = character_info or self.character_info or {}
        gender = (info.get('gender') or info.get('性别') or '').lower()
        if gender not in ('female', 'f', '女', '女性'):
            return {'enabled': False, 'phase': '', 'energy_modifier': 0.0}
        # 简化：以 28 天周期计算（无个性化锚点）
        now = now or datetime.now()
        anchor = self._body_cycle_anchor(info)
        delta_days = (now - anchor).days % 28
        phase = self.cycle_phase(delta_days)
        modifier = self.cycle_energy_modifier(phase)
        return {
            'enabled': True,
            'phase': phase,
            'energy_modifier': modifier,
            'cycle_day': delta_days,
        }

    @staticmethod
    def _body_cycle_anchor(info: Dict[str, Any]) -> datetime:
        """简化：默认锚点 2026-01-01。生产环境应从 character_info 中读取真实锚点。"""
        anchor_str = info.get('cycle_anchor') or info.get('生理周期锚点')
        if anchor_str:
            try:
                return datetime.fromisoformat(str(anchor_str))
            except (ValueError, TypeError):
                pass
        return datetime(2026, 1, 1)

    @staticmethod
    def cycle_phase(cycle_day: int) -> str:
        """
        根据周期天数（0-27）返回阶段。
        简化分段（4 段）：经期 / 经后 / 排卵期 / 经前
        """
        cycle_day = cycle_day % 28
        if cycle_day < 5:
            return '经期'
        if cycle_day < 13:
            return '经后'
        if cycle_day < 17:
            return '排卵期'
        return '经前'

    @staticmethod
    def cycle_energy_modifier(phase: str) -> float:
        """返回对能量基线的修正系数（-0.2 ~ +0.1）。"""
        return {
            '经期': -0.15,
            '经后': 0.05,
            '排卵期': 0.1,
            '经前': -0.2,
        }.get(phase, 0.0)

    def _resolve_energy(self, conditions: List[Dict[str, Any]], now: datetime) -> float:
        base = 0.7
        for c in conditions:
            name = (c.get('name') or '').lower()
            weight = float(c.get('weight', 0.0))
            if any(k in name for k in ('失眠', '熬夜', 'sleep_debt')):
                base -= 0.2 * weight
            elif any(k in name for k in ('好梦', 'good_dream', '恢复', 'relaxed')):
                base += 0.1 * weight
            elif any(k in name for k in ('焦虑', 'anxiety', '压力')):
                base -= 0.1 * weight
        base += self._last_dream_energy_delta
        return round(max(0.0, min(1.0, base)), 3)

    def _resolve_mood(self, conditions: List[Dict[str, Any]]) -> str:
        for c in conditions:
            name = (c.get('name') or '').lower()
            if '焦虑' in name or '压力' in name:
                return '焦虑'
            if '低落' in name or 'sad' in name:
                return '低落'
            if '兴奋' in name or 'excited' in name:
                return '兴奋'
            if '愉快' in name or 'happy' in name:
                return '愉快'
            if '疲倦' in name or 'tired' in name:
                return '疲倦'
        return '平静'

    def _resolve_health(self, conditions: List[Dict[str, Any]]) -> str:
        for c in conditions:
            name = (c.get('name') or '').lower()
            if '生病' in name or 'ill' in name:
                return '生病'
            if '不适' in name or 'unwell' in name:
                return '轻微不适'
        return '健康'

    def _resolve_state_title(self, conditions: List[Dict[str, Any]],
                             energy: float, mood: str) -> str:
        for c in conditions:
            name = (c.get('name') or '').lower()
            if '饥饿' in name or 'hungry' in name:
                return '饥饿'
            if '专注' in name or 'focus' in name:
                return '专注'
        if energy < 0.4:
            return '疲惫'
        if mood == '焦虑':
            return '焦虑'
        if mood == '低落':
            return '低落'
        if mood == '兴奋':
            return '兴奋'
        return '常态'

    def _build_transition_options(self, conditions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        options = []
        for c in conditions:
            name = (c.get('name') or '').lower()
            if '饥饿' in name or 'hungry' in name:
                options.append({'trigger': 'meal_missed', 'target_state': '饥饿', 'weight': 0.7})
            elif '疲倦' in name or 'tired' in name:
                options.append({'trigger': 'sleep_debt', 'target_state': '疲惫', 'weight': 0.8})
            elif '焦虑' in name or 'anxiety' in name:
                options.append({'trigger': 'bad_news', 'target_state': '焦虑', 'weight': 0.6})
        if not options:
            options.append({'trigger': 'idle_long', 'target_state': '放松', 'weight': 0.5})
        return options

    def _parse_conditions(self, raw: str) -> List[Dict[str, Any]]:
        text = raw.strip()
        if text.startswith('```'):
            text = text.strip('`')
            if text.startswith('json'):
                text = text[4:]
        try:
            data = json.loads(text)
            if isinstance(data, list):
                return [c for c in data if isinstance(c, dict) and 'name' in c]
            if isinstance(data, dict) and 'conditions' in data:
                return [c for c in data['conditions'] if isinstance(c, dict) and 'name' in c]
        except json.JSONDecodeError:
            pass
        return []

    def _default_conditions(self, now: datetime) -> List[Dict[str, Any]]:
        return [
            {'name': '常态作息', 'weight': 0.6, 'category': '作息', 'note': '保持稳定'},
            {'name': '天气适宜', 'weight': 0.4, 'category': '环境', 'note': '外部环境平稳'},
        ]

    def _fallback_conditions_prompt(self) -> str:
        return ("你是状态分析器。返回 JSON list，每条含 name/weight/category/note。"
                "weight 范围 0-1，表示强度。")

    def _get_or_create_default(self, now: Optional[datetime]) -> Dict[str, Any]:
        now = now or datetime.now()
        date_str = now.date().isoformat()
        existing = self.db.get_life_state_daily(date_str)
        if existing:
            return existing
        return {
            'date': date_str,
            'energy': 0.7,
            'mood': '平静',
            'state_title': '常态',
            'health': '健康',
            'conditions': [],
            'transition_options': [],
            'energy_delta': 0.0,
        }
