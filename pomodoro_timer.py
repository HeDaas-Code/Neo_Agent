"""
番茄时钟模块
提供番茄工作法计时功能，支持工作和休息周期管理
"""

import time
import threading
from datetime import datetime, timedelta
from typing import Callable, Optional, Dict, Any
from enum import Enum
from debug_logger import get_debug_logger

# 获取debug日志记录器
debug_logger = get_debug_logger()


class PomodoroState(Enum):
    """番茄时钟状态枚举"""
    IDLE = "idle"  # 空闲
    WORKING = "working"  # 工作中
    RESTING = "resting"  # 休息中
    PAUSED = "paused"  # 暂停


class PomodoroTimer:
    """
    番茄时钟管理器
    实现标准番茄工作法：25分钟工作 + 5分钟休息
    """

    def __init__(
        self,
        work_duration: int = 25,  # 工作时长（分钟）
        short_break: int = 5,  # 短休息时长（分钟）
        long_break: int = 15,  # 长休息时长（分钟）
        pomodoros_until_long_break: int = 4  # 几个番茄后长休息
    ):
        """
        初始化番茄时钟

        Args:
            work_duration: 工作时长（分钟）
            short_break: 短休息时长（分钟）
            long_break: 长休息时长（分钟）
            pomodoros_until_long_break: 几个番茄后进行长休息
        """
        self.work_duration = work_duration * 60  # 转换为秒
        self.short_break = short_break * 60
        self.long_break = long_break * 60
        self.pomodoros_until_long_break = pomodoros_until_long_break

        self.state = PomodoroState.IDLE
        self.previous_state = PomodoroState.IDLE  # 保存暂停前的状态
        self.current_pomodoro = 0  # 当前完成的番茄数
        self.remaining_time = 0  # 剩余时间（秒）
        self.total_time = 0  # 总时间（秒）
        self.start_time = None
        self.pause_time = None

        self.timer_thread: Optional[threading.Thread] = None
        self.stop_flag = threading.Event()

        # 回调函数
        self.on_work_start: Optional[Callable] = None
        self.on_work_complete: Optional[Callable] = None
        self.on_break_start: Optional[Callable] = None
        self.on_break_complete: Optional[Callable] = None
        self.on_tick: Optional[Callable[[int], None]] = None  # 每秒回调，参数为剩余秒数

        debug_logger.log_info('PomodoroTimer', '初始化番茄时钟', {
            'work_duration': work_duration,
            'short_break': short_break,
            'long_break': long_break
        })

    def start_work(self):
        """开始工作时段"""
        if self.state != PomodoroState.IDLE:
            debug_logger.log_warning('PomodoroTimer', '无法启动工作时段', {
                'current_state': self.state.value
            })
            return False

        self.state = PomodoroState.WORKING
        self.remaining_time = self.work_duration
        self.total_time = self.work_duration
        self.start_time = datetime.now()

        debug_logger.log_info('PomodoroTimer', '开始工作时段', {
            'duration': self.work_duration,
            'pomodoro_number': self.current_pomodoro + 1
        })

        if self.on_work_start:
            self.on_work_start()

        self._start_timer()
        return True

    def start_break(self):
        """开始休息时段"""
        if self.state != PomodoroState.IDLE:
            debug_logger.log_warning('PomodoroTimer', '无法启动休息时段', {
                'current_state': self.state.value
            })
            return False

        # 判断是长休息还是短休息
        is_long_break = (self.current_pomodoro % self.pomodoros_until_long_break == 0 
                        and self.current_pomodoro > 0)
        break_duration = self.long_break if is_long_break else self.short_break

        self.state = PomodoroState.RESTING
        self.remaining_time = break_duration
        self.total_time = break_duration
        self.start_time = datetime.now()

        debug_logger.log_info('PomodoroTimer', '开始休息时段', {
            'duration': break_duration,
            'is_long_break': is_long_break,
            'completed_pomodoros': self.current_pomodoro
        })

        if self.on_break_start:
            self.on_break_start()

        self._start_timer()
        return True

    def pause(self):
        """暂停计时"""
        if self.state not in [PomodoroState.WORKING, PomodoroState.RESTING]:
            return False

        # 保存当前状态
        self.previous_state = self.state
        self.pause_time = datetime.now()
        self.stop_flag.set()

        # 等待线程结束
        if self.timer_thread and self.timer_thread.is_alive():
            self.timer_thread.join(timeout=2)

        self.state = PomodoroState.PAUSED

        debug_logger.log_info('PomodoroTimer', '暂停计时', {
            'remaining_time': self.remaining_time
        })
        return True

    def resume(self):
        """恢复计时"""
        if self.state != PomodoroState.PAUSED:
            return False

        # 恢复之前的状态
        self.state = self.previous_state
        self.start_time = datetime.now()
        self.pause_time = None

        debug_logger.log_info('PomodoroTimer', '恢复计时', {
            'state': self.state.value,
            'remaining_time': self.remaining_time
        })

        self._start_timer()
        return True

    def stop(self):
        """停止当前计时"""
        self.stop_flag.set()

        # 等待线程结束
        if self.timer_thread and self.timer_thread.is_alive():
            self.timer_thread.join(timeout=2)

        debug_logger.log_info('PomodoroTimer', '停止计时', {
            'previous_state': self.state.value,
            'remaining_time': self.remaining_time
        })

        self.state = PomodoroState.IDLE
        self.remaining_time = 0
        self.start_time = None
        return True

    def _start_timer(self):
        """内部方法：启动计时线程"""
        self.stop_flag.clear()
        self.timer_thread = threading.Thread(target=self._timer_loop, daemon=True)
        self.timer_thread.start()

    def _timer_loop(self):
        """内部方法：计时循环"""
        while not self.stop_flag.is_set() and self.remaining_time > 0:
            time.sleep(1)
            self.remaining_time -= 1

            # 调用tick回调
            if self.on_tick:
                try:
                    self.on_tick(self.remaining_time)
                except Exception as e:
                    debug_logger.log_error('PomodoroTimer', '调用tick回调失败', e)

        # 计时完成
        if self.remaining_time <= 0 and not self.stop_flag.is_set():
            self._on_timer_complete()

    def _on_timer_complete(self):
        """内部方法：计时完成处理"""
        if self.state == PomodoroState.WORKING:
            self.current_pomodoro += 1
            debug_logger.log_info('PomodoroTimer', '工作时段完成', {
                'completed_pomodoros': self.current_pomodoro
            })

            if self.on_work_complete:
                self.on_work_complete()

        elif self.state == PomodoroState.RESTING:
            debug_logger.log_info('PomodoroTimer', '休息时段完成')

            if self.on_break_complete:
                self.on_break_complete()

        self.state = PomodoroState.IDLE
        self.remaining_time = 0

    def get_status(self) -> Dict[str, Any]:
        """
        获取当前状态

        Returns:
            包含当前状态信息的字典
        """
        return {
            'state': self.state.value,
            'current_pomodoro': self.current_pomodoro,
            'remaining_time': self.remaining_time,
            'total_time': self.total_time,
            'progress': 1 - (self.remaining_time / self.total_time) if self.total_time > 0 else 0,
            'is_long_break_next': (self.current_pomodoro % self.pomodoros_until_long_break == 0 
                                   and self.current_pomodoro > 0)
        }

    def format_time(self, seconds: int) -> str:
        """
        格式化时间显示

        Args:
            seconds: 秒数

        Returns:
            格式化的时间字符串 (MM:SS)
        """
        minutes = seconds // 60
        secs = seconds % 60
        return f"{minutes:02d}:{secs:02d}"

    def get_formatted_remaining_time(self) -> str:
        """获取格式化的剩余时间"""
        return self.format_time(self.remaining_time)

    def reset_pomodoros(self):
        """重置番茄计数"""
        self.current_pomodoro = 0
        debug_logger.log_info('PomodoroTimer', '重置番茄计数')
