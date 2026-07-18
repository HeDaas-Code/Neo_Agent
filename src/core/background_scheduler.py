"""
后台调度入口模块
- 异步执行 P1/P2/P3/P4 阶段的后台任务
- 通过共享 DatabaseManager 与 EventManager 与 Web/API 层通信
- 线程隔离：asyncio.run 在独立子线程运行，与主线程事件循环物理隔离

参考架构：spec §4 ADDED Requirements → BackgroundScheduler
"""

import os
import asyncio
import threading
from datetime import datetime
from typing import Optional, List, Dict, Any

from src.tools.debug_logger import get_debug_logger

ENABLE_BACKGROUND_SCHEDULER = os.getenv('ENABLE_BACKGROUND_SCHEDULER', 'false').lower() == 'true'

debug_logger = get_debug_logger()


class BackgroundScheduler:
    """
    后台调度器
    - scheduler_loop: 异步主循环
    - 任务调度：梦境生成 / 日记生成 / 创作推进 / 主动决策评估
    - 在独立子线程运行，与主线程事件循环物理隔离
    """

    DEFAULT_TICK_SECONDS = 60
    TASK_REGISTRY_KEY = 'background_scheduler_tasks'

    def __init__(self, tick_seconds: int = DEFAULT_TICK_SECONDS,
                 life_state=None,
                 dream_diary=None,
                 creative_writer=None,
                 proactive_engine=None,
                 open_loop_tracker=None):
        self.tick_seconds = tick_seconds
        self.life_state = life_state
        self.dream_diary = dream_diary
        self.creative_writer = creative_writer
        self.proactive_engine = proactive_engine
        self.open_loop_tracker = open_loop_tracker
        self.enabled = ENABLE_BACKGROUND_SCHEDULER
        self._thread: Optional[threading.Thread] = None
        self._stop_event: Optional[asyncio.Event] = None
        self._last_run_at: Dict[str, str] = {}

    # ===== 启停 =====

    def start(self) -> bool:
        """
        在独立子线程启动 asyncio 事件循环，物理隔离于主线程事件循环。
        """
        if not self.enabled:
            debug_logger.log_info('BackgroundScheduler', '功能未启用，跳过启动')
            return False
        if self._thread and self._thread.is_alive():
            debug_logger.log_info('BackgroundScheduler', '已在运行，跳过启动')
            return True
        self._stop_event = threading.Event()
        self._thread = threading.Thread(
            target=self._run_in_thread,
            name='BackgroundScheduler',
            daemon=True,
        )
        self._thread.start()
        debug_logger.log_info('BackgroundScheduler', '已在子线程启动', {
            'tick_seconds': self.tick_seconds,
        })
        return True

    def stop(self, timeout: float = 5.0) -> bool:
        if self._stop_event:
            self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=timeout)
        debug_logger.log_info('BackgroundScheduler', '已停止')
        return True

    def _run_in_thread(self) -> None:
        try:
            asyncio.run(self.scheduler_loop())
        except Exception as e:
            debug_logger.log_error('BackgroundScheduler', f'主循环异常退出: {e}', e)

    # ===== 主循环 =====

    async def scheduler_loop(self) -> None:
        """
        每 tick_seconds 秒轮询一次，按各任务 last_run_at 决定是否执行。
        """
        debug_logger.log_info('BackgroundScheduler', '主循环开始', {
            'tick_seconds': self.tick_seconds,
        })
        while True:
            try:
                # 检查停止事件
                if self._stop_event and self._stop_event.is_set():
                    debug_logger.log_info('BackgroundScheduler', '收到停止信号，退出主循环')
                    break
                # 按序执行
                self._tick_dream_generation()
                self._tick_diary_generation()
                self._tick_creative_advance()
                self._tick_proactive_evaluation()
            except Exception as e:
                debug_logger.log_error('BackgroundScheduler', f'tick 异常: {e}', e)

            # Stage D.1: 每个 tick 结束后向 EventManager 推送状态，try/except 保护
            try:
                self.tick()
            except Exception as e:
                debug_logger.log_error('BackgroundScheduler', f'tick 状态发布失败: {e}', e)

            # 异步睡眠
            await asyncio.sleep(self.tick_seconds)

    # ===== Stage D.1: 单次 tick 状态发布 =====
    def tick(self) -> None:
        """
        单次 tick：收集当前状态快照并通过 EventManager.publish 推送给订阅者。

        - 不修改任何调度逻辑；仅在调度循环末尾调用。
        - payload 包含 life_state_snapshot / dream_record / open_loop_count /
          creative_project_count / last_run_at / running 等只读字段。
        - 单次 publish 失败不会影响主循环。
        """
        try:
            from src.core.event_manager import get_event_manager
            em = get_event_manager()
        except Exception as e:
            debug_logger.log_error('BackgroundScheduler', f'获取 EventManager 失败: {e}', e)
            return

        # 收集状态（所有外部访问均 try/except，避免影响主流程）
        status_payload: Dict[str, Any] = {
            'enabled': self.enabled,
            'running': bool(self._thread and self._thread.is_alive()),
            'tick_seconds': self.tick_seconds,
            'last_run_at': dict(self._last_run_at),
            'timestamp': datetime.now().isoformat(),
        }

        # life_state_snapshot
        try:
            if self.life_state and getattr(self.life_state, 'enabled', False):
                snap = self.life_state.get_current_state_snapshot() or {}
                status_payload['life_state_snapshot'] = snap
        except Exception as e:
            debug_logger.log_error('BackgroundScheduler', f'life_state snapshot 失败: {e}', e)
            status_payload['life_state_snapshot'] = None

        # dream_record（最新一条梦境）
        try:
            if self.dream_diary and getattr(self.dream_diary, 'enabled', False):
                latest = None
                getter = getattr(self.dream_diary, 'get_latest_dream', None)
                if callable(getter):
                    latest = getter()
                status_payload['dream_record'] = latest
        except Exception as e:
            debug_logger.log_error('BackgroundScheduler', f'dream_record 拉取失败: {e}', e)
            status_payload['dream_record'] = None

        # open_loop_count
        try:
            if self.open_loop_tracker and getattr(self.open_loop_tracker, 'enabled', False):
                status_payload['open_loop_count'] = int(
                    self.open_loop_tracker.count_open_loops()
                )
            else:
                status_payload['open_loop_count'] = 0
        except Exception as e:
            debug_logger.log_error('BackgroundScheduler', f'open_loop_count 失败: {e}', e)
            status_payload['open_loop_count'] = 0

        # creative_project_count
        try:
            if self.creative_writer and getattr(self.creative_writer, 'enabled', False):
                status_payload['creative_project_count'] = int(
                    self.creative_writer.count_projects()
                )
            else:
                status_payload['creative_project_count'] = 0
        except Exception as e:
            debug_logger.log_error('BackgroundScheduler', f'creative_project_count 失败: {e}', e)
            status_payload['creative_project_count'] = 0

        # 推送给 EventManager 订阅者（如 Web 后端 EventService）
        try:
            em.publish('scheduler_tick', status_payload)
        except Exception as e:
            debug_logger.log_error('BackgroundScheduler', f'publish scheduler_tick 失败: {e}', e)

    # ===== 子任务 =====

    def _should_run(self, task: str, interval_minutes: int) -> bool:
        last = self._last_run_at.get(task)
        now = datetime.now()
        if not last:
            return True
        try:
            last_dt = datetime.fromisoformat(last)
        except (ValueError, TypeError):
            return True
        return (now - last_dt).total_seconds() / 60.0 >= interval_minutes

    def _tick_dream_generation(self) -> None:
        # 默认 24h 一次；与日历日的凌晨触发对齐
        if not self.dream_diary or not getattr(self.dream_diary, 'enabled', False):
            return
        if not self._should_run('dream_generation', 60 * 24):
            return
        try:
            self.dream_diary.generate_dream_pick()
            self._last_run_at['dream_generation'] = datetime.now().isoformat()
            debug_logger.log_info('BackgroundScheduler', '梦境生成已调度')
        except Exception as e:
            debug_logger.log_error('BackgroundScheduler', f'梦境生成失败: {e}', e)

    def _tick_diary_generation(self) -> None:
        if not self.dream_diary or not getattr(self.dream_diary, 'enabled', False):
            return
        if not self._should_run('diary_generation', 60 * 24):
            return
        try:
            self.dream_diary.generate_daily_diary()
            self._last_run_at['diary_generation'] = datetime.now().isoformat()
            debug_logger.log_info('BackgroundScheduler', '日记生成已调度')
        except Exception as e:
            debug_logger.log_error('BackgroundScheduler', f'日记生成失败: {e}', e)

    def _tick_creative_advance(self) -> None:
        if not self.creative_writer or not getattr(self.creative_writer, 'enabled', False):
            return
        try:
            self.creative_writer.maybe_advance_creative_projects()
            self._last_run_at['creative_advance'] = datetime.now().isoformat()
        except Exception as e:
            debug_logger.log_error('BackgroundScheduler', f'创作推进失败: {e}', e)

    def _tick_proactive_evaluation(self) -> None:
        if not self.proactive_engine or not getattr(self.proactive_engine, 'enabled', False):
            return
        # 默认每 5 分钟评估一次
        if not self._should_run('proactive_evaluation', 5):
            return
        try:
            user = 'default'
            ok, reason = self.proactive_engine.should_send(user)
            if ok:
                pool = self.proactive_engine.proactive_impulse_pool(user)
                if pool:
                    idea = pool[0]
                    self.proactive_engine.bot_proactive_drive_send(user, idea)
            self._last_run_at['proactive_evaluation'] = datetime.now().isoformat()
        except Exception as e:
            debug_logger.log_error('BackgroundScheduler', f'主动决策评估失败: {e}', e)

    # ===== 状态查询 =====

    def get_status(self) -> Dict[str, Any]:
        return {
            'enabled': self.enabled,
            'running': bool(self._thread and self._thread.is_alive()),
            'tick_seconds': self.tick_seconds,
            'last_run_at': dict(self._last_run_at),
        }


# 便于 main.py 调用的便捷函数
_default_scheduler: Optional[BackgroundScheduler] = None


def start_default_scheduler(**kwargs) -> Optional[BackgroundScheduler]:
    global _default_scheduler
    if _default_scheduler is not None and _default_scheduler._thread and _default_scheduler._thread.is_alive():
        return _default_scheduler
    _default_scheduler = BackgroundScheduler(**kwargs)
    if _default_scheduler.start():
        return _default_scheduler
    return None
