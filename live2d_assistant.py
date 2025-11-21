"""
Live2D桌宠助手模块
集成番茄时钟、日程、笔记、计划管理，以及智能对话功能
提供一个可爱的桌面宠物界面
"""

import os
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, Menu
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import threading

from chat_agent import ChatAgent
from pomodoro_timer import PomodoroTimer, PomodoroState
from schedule_manager import ScheduleManager, Schedule, SchedulePriority, ScheduleStatus
from note_manager import NoteManager, Note
from plan_manager import PlanManager, Plan, Task, PlanStatus, TaskStatus
from event_manager import EventManager, EventType, EventPriority, NotificationEvent
from debug_logger import get_debug_logger

# 获取debug日志记录器
debug_logger = get_debug_logger()


class Live2DAssistant(tk.Tk):
    """
    Live2D桌宠助手主窗口
    扮演女高中生小可的角色，提供智能助手功能
    """

    def __init__(self):
        """初始化Live2D助手"""
        super().__init__()

        debug_logger.log_info('Live2DAssistant', '初始化Live2D助手')

        # 窗口基本设置
        self.title("小可的桌面助手 🌸")
        self.geometry("400x650")
        
        # 设置窗口始终置顶
        self.attributes('-topmost', True)
        
        # 可选：设置窗口透明度
        # self.attributes('-alpha', 0.95)

        # 初始化各个管理器
        self.chat_agent = ChatAgent()
        self.pomodoro = PomodoroTimer()
        self.schedule_manager = ScheduleManager()
        self.note_manager = NoteManager()
        self.plan_manager = PlanManager()
        self.event_manager = EventManager()

        # 设置番茄时钟回调
        self._setup_pomodoro_callbacks()

        # 创建UI
        self._create_ui()

        # 启动定时检查
        self._start_reminder_check()

        # 欢迎消息
        self._show_welcome_message()

        debug_logger.log_info('Live2DAssistant', 'Live2D助手初始化完成')

    def _create_ui(self):
        """创建用户界面"""
        # 创建主容器
        main_frame = ttk.Frame(self, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 创建顶部角色信息
        self._create_character_panel(main_frame)

        # 创建标签页
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True, pady=5)

        # 各个功能标签页
        self._create_chat_tab()
        self._create_pomodoro_tab()
        self._create_schedule_tab()
        self._create_note_tab()
        self._create_plan_tab()
        self._create_stats_tab()

        # 创建底部状态栏
        self._create_status_bar(main_frame)

        # 创建右键菜单
        self._create_context_menu()

    def _create_character_panel(self, parent):
        """创建角色信息面板"""
        char_frame = ttk.LabelFrame(parent, text="👧 小可", padding="5")
        char_frame.pack(fill=tk.X, pady=5)

        # 角色状态
        self.character_status_label = ttk.Label(
            char_frame,
            text="😊 我是小可！今天也要加油呀～",
            font=('微软雅黑', 10)
        )
        self.character_status_label.pack()

    def _create_chat_tab(self):
        """创建聊天标签页"""
        chat_frame = ttk.Frame(self.notebook)
        self.notebook.add(chat_frame, text="💬 聊天")

        # 聊天显示区域
        self.chat_display = scrolledtext.ScrolledText(
            chat_frame,
            wrap=tk.WORD,
            height=15,
            font=('微软雅黑', 9)
        )
        self.chat_display.pack(fill=tk.BOTH, expand=True, pady=5)
        self.chat_display.config(state=tk.DISABLED)

        # 输入区域
        input_frame = ttk.Frame(chat_frame)
        input_frame.pack(fill=tk.X, pady=5)

        self.chat_input = ttk.Entry(input_frame, font=('微软雅黑', 9))
        self.chat_input.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        self.chat_input.bind('<Return>', lambda e: self._send_message())

        send_btn = ttk.Button(input_frame, text="发送", command=self._send_message, width=10)
        send_btn.pack(side=tk.RIGHT)

    def _create_pomodoro_tab(self):
        """创建番茄时钟标签页"""
        pomo_frame = ttk.Frame(self.notebook)
        self.notebook.add(pomo_frame, text="🍅 番茄时钟")

        # 时钟显示
        self.pomodoro_time_label = ttk.Label(
            pomo_frame,
            text="25:00",
            font=('Arial', 36, 'bold')
        )
        self.pomodoro_time_label.pack(pady=20)

        # 状态显示
        self.pomodoro_status_label = ttk.Label(
            pomo_frame,
            text="准备开始工作",
            font=('微软雅黑', 10)
        )
        self.pomodoro_status_label.pack()

        # 进度条
        self.pomodoro_progress = ttk.Progressbar(
            pomo_frame,
            length=300,
            mode='determinate'
        )
        self.pomodoro_progress.pack(pady=10)

        # 番茄数显示
        self.pomodoro_count_label = ttk.Label(
            pomo_frame,
            text="今日完成: 0 个番茄 🍅",
            font=('微软雅黑', 9)
        )
        self.pomodoro_count_label.pack(pady=5)

        # 控制按钮
        btn_frame = ttk.Frame(pomo_frame)
        btn_frame.pack(pady=10)

        self.pomo_start_btn = ttk.Button(
            btn_frame,
            text="开始工作",
            command=self._start_pomodoro,
            width=12
        )
        self.pomo_start_btn.pack(side=tk.LEFT, padx=5)

        self.pomo_pause_btn = ttk.Button(
            btn_frame,
            text="暂停",
            command=self._pause_pomodoro,
            width=12,
            state=tk.DISABLED
        )
        self.pomo_pause_btn.pack(side=tk.LEFT, padx=5)

        self.pomo_stop_btn = ttk.Button(
            btn_frame,
            text="停止",
            command=self._stop_pomodoro,
            width=12,
            state=tk.DISABLED
        )
        self.pomo_stop_btn.pack(side=tk.LEFT, padx=5)

    def _create_schedule_tab(self):
        """创建日程标签页"""
        schedule_frame = ttk.Frame(self.notebook)
        self.notebook.add(schedule_frame, text="📅 日程")

        # 工具栏
        toolbar = ttk.Frame(schedule_frame)
        toolbar.pack(fill=tk.X, pady=5)

        ttk.Button(toolbar, text="+ 新建日程", command=self._add_schedule).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="刷新", command=self._refresh_schedules).pack(side=tk.LEFT, padx=2)

        # 日程列表
        self.schedule_listbox = tk.Listbox(schedule_frame, font=('微软雅黑', 9))
        self.schedule_listbox.pack(fill=tk.BOTH, expand=True, pady=5)
        self.schedule_listbox.bind('<Double-Button-1>', self._view_schedule)

        # 加载日程
        self._refresh_schedules()

    def _create_note_tab(self):
        """创建笔记标签页"""
        note_frame = ttk.Frame(self.notebook)
        self.notebook.add(note_frame, text="📝 笔记")

        # 工具栏
        toolbar = ttk.Frame(note_frame)
        toolbar.pack(fill=tk.X, pady=5)

        ttk.Button(toolbar, text="+ 新建笔记", command=self._add_note).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="刷新", command=self._refresh_notes).pack(side=tk.LEFT, padx=2)

        # 笔记列表
        self.note_listbox = tk.Listbox(note_frame, font=('微软雅黑', 9))
        self.note_listbox.pack(fill=tk.BOTH, expand=True, pady=5)
        self.note_listbox.bind('<Double-Button-1>', self._view_note)

        # 加载笔记
        self._refresh_notes()

    def _create_plan_tab(self):
        """创建计划标签页"""
        plan_frame = ttk.Frame(self.notebook)
        self.notebook.add(plan_frame, text="🎯 计划")

        # 工具栏
        toolbar = ttk.Frame(plan_frame)
        toolbar.pack(fill=tk.X, pady=5)

        ttk.Button(toolbar, text="+ 新建计划", command=self._add_plan).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="刷新", command=self._refresh_plans).pack(side=tk.LEFT, padx=2)

        # 计划列表
        self.plan_listbox = tk.Listbox(plan_frame, font=('微软雅黑', 9))
        self.plan_listbox.pack(fill=tk.BOTH, expand=True, pady=5)
        self.plan_listbox.bind('<Double-Button-1>', self._view_plan)

        # 加载计划
        self._refresh_plans()

    def _create_stats_tab(self):
        """创建统计标签页"""
        stats_frame = ttk.Frame(self.notebook)
        self.notebook.add(stats_frame, text="📊 统计")

        # 统计信息显示
        self.stats_text = scrolledtext.ScrolledText(
            stats_frame,
            wrap=tk.WORD,
            font=('微软雅黑', 9)
        )
        self.stats_text.pack(fill=tk.BOTH, expand=True, pady=5)

        # 刷新按钮
        ttk.Button(
            stats_frame,
            text="刷新统计",
            command=self._refresh_stats
        ).pack(pady=5)

        # 初始加载统计
        self._refresh_stats()

    def _create_status_bar(self, parent):
        """创建状态栏"""
        status_frame = ttk.Frame(parent)
        status_frame.pack(fill=tk.X, pady=5)

        self.status_label = ttk.Label(
            status_frame,
            text="就绪",
            font=('微软雅黑', 8),
            relief=tk.SUNKEN
        )
        self.status_label.pack(fill=tk.X)

    def _create_context_menu(self):
        """创建右键菜单"""
        self.context_menu = Menu(self, tearoff=0)
        self.context_menu.add_command(label="显示/隐藏", command=self._toggle_window)
        self.context_menu.add_command(label="置顶", command=self._toggle_topmost)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="退出", command=self.quit)

        self.bind('<Button-3>', self._show_context_menu)

    def _show_context_menu(self, event):
        """显示右键菜单"""
        try:
            self.context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.context_menu.grab_release()

    def _toggle_window(self):
        """显示/隐藏窗口"""
        if self.state() == 'withdrawn':
            self.deiconify()
        else:
            self.withdraw()

    def _toggle_topmost(self):
        """切换置顶状态"""
        current = self.attributes('-topmost')
        self.attributes('-topmost', not current)
        status = "已置顶" if not current else "取消置顶"
        self._update_status(status)

    # ========== 聊天功能 ==========

    def _send_message(self):
        """发送消息"""
        message = self.chat_input.get().strip()
        if not message:
            return

        self.chat_input.delete(0, tk.END)

        # 显示用户消息
        self._append_chat_message("你", message)

        # 在后台线程处理响应
        threading.Thread(
            target=self._process_chat_message,
            args=(message,),
            daemon=True
        ).start()

    def _process_chat_message(self, message: str):
        """处理聊天消息"""
        try:
            response = self.chat_agent.chat(message)
            self.after(0, self._append_chat_message, "小可", response)
        except Exception as e:
            debug_logger.log_error('Live2DAssistant', '处理聊天消息失败', e)
            self.after(0, self._append_chat_message, "系统", f"抱歉，出错了: {str(e)}")

    def _append_chat_message(self, sender: str, message: str):
        """添加聊天消息到显示区域"""
        self.chat_display.config(state=tk.NORMAL)
        timestamp = datetime.now().strftime("%H:%M")
        self.chat_display.insert(tk.END, f"[{timestamp}] {sender}: {message}\n\n")
        self.chat_display.see(tk.END)
        self.chat_display.config(state=tk.DISABLED)

    # ========== 番茄时钟功能 ==========

    def _setup_pomodoro_callbacks(self):
        """设置番茄时钟回调"""
        self.pomodoro.on_tick = self._on_pomodoro_tick
        self.pomodoro.on_work_start = self._on_work_start
        self.pomodoro.on_work_complete = self._on_work_complete
        self.pomodoro.on_break_start = self._on_break_start
        self.pomodoro.on_break_complete = self._on_break_complete

    def _start_pomodoro(self):
        """开始番茄时钟"""
        if self.pomodoro.start_work():
            self.pomo_start_btn.config(state=tk.DISABLED)
            self.pomo_pause_btn.config(state=tk.NORMAL)
            self.pomo_stop_btn.config(state=tk.NORMAL)
            self._update_status("开始工作时段")

    def _pause_pomodoro(self):
        """暂停番茄时钟"""
        if self.pomodoro.state == PomodoroState.PAUSED:
            if self.pomodoro.resume():
                self.pomo_pause_btn.config(text="暂停")
                self._update_status("恢复计时")
        else:
            if self.pomodoro.pause():
                self.pomo_pause_btn.config(text="继续")
                self._update_status("暂停计时")

    def _stop_pomodoro(self):
        """停止番茄时钟"""
        if self.pomodoro.stop():
            self.pomo_start_btn.config(state=tk.NORMAL)
            self.pomo_pause_btn.config(state=tk.DISABLED, text="暂停")
            self.pomo_stop_btn.config(state=tk.DISABLED)
            self.pomodoro_time_label.config(text="25:00")
            self.pomodoro_status_label.config(text="准备开始工作")
            self.pomodoro_progress['value'] = 0
            self._update_status("停止计时")

    def _on_pomodoro_tick(self, remaining_seconds: int):
        """番茄时钟每秒回调"""
        time_str = self.pomodoro.format_time(remaining_seconds)
        status = self.pomodoro.get_status()

        self.after(0, self.pomodoro_time_label.config, {'text': time_str})
        self.after(0, self.pomodoro_progress.__setitem__, 'value', status['progress'] * 100)

    def _on_work_start(self):
        """工作时段开始"""
        self.after(0, self.pomodoro_status_label.config, {'text': '工作中... 保持专注！'})
        self.after(0, self._update_character_status, "💪 我们一起努力工作吧！")

    def _on_work_complete(self):
        """工作时段完成"""
        count = self.pomodoro.current_pomodoro
        self.after(0, self.pomodoro_count_label.config, {'text': f'今日完成: {count} 个番茄 🍅'})
        self.after(0, self._update_character_status, f"🎉 太棒了！完成了第{count}个番茄，休息一下吧～")
        self.after(0, messagebox.showinfo, "番茄时钟", "工作时段完成！该休息啦～")
        
        # 自动开始休息
        self.after(1000, self.pomodoro.start_break)

    def _on_break_start(self):
        """休息时段开始"""
        self.after(0, self.pomodoro_status_label.config, {'text': '休息中... 放松一下'})
        self.after(0, self._update_character_status, "☕ 休息时间到啦！喝杯水，活动一下吧～")

    def _on_break_complete(self):
        """休息时段完成"""
        self.after(0, self._update_character_status, "⏰ 休息结束，准备继续工作吧！")
        self.after(0, messagebox.showinfo, "番茄时钟", "休息结束！准备下一个番茄～")
        self.after(0, self._stop_pomodoro)

    # ========== 日程功能 ==========

    def _add_schedule(self):
        """添加新日程"""
        # 创建简单的对话框
        dialog = tk.Toplevel(self)
        dialog.title("新建日程")
        dialog.geometry("350x250")
        dialog.transient(self)
        dialog.grab_set()

        ttk.Label(dialog, text="标题:").pack(pady=5)
        title_entry = ttk.Entry(dialog, width=40)
        title_entry.pack(pady=5)

        ttk.Label(dialog, text="描述:").pack(pady=5)
        desc_text = tk.Text(dialog, width=40, height=5)
        desc_text.pack(pady=5)

        def save():
            title = title_entry.get().strip()
            if not title:
                messagebox.showwarning("警告", "请输入标题")
                return

            schedule = Schedule(
                title=title,
                description=desc_text.get("1.0", tk.END).strip(),
                start_time=datetime.now() + timedelta(hours=1),
                end_time=datetime.now() + timedelta(hours=2)
            )

            if self.schedule_manager.add_schedule(schedule):
                messagebox.showinfo("成功", "日程已添加")
                self._refresh_schedules()
                dialog.destroy()
            else:
                messagebox.showerror("错误", "添加日程失败")

        ttk.Button(dialog, text="保存", command=save).pack(pady=10)

    def _refresh_schedules(self):
        """刷新日程列表"""
        self.schedule_listbox.delete(0, tk.END)
        schedules = self.schedule_manager.get_upcoming_schedules(24 * 7)  # 未来7天

        for schedule in schedules:
            start_time = schedule.start_time.strftime("%m-%d %H:%M")
            status_icon = "⏳" if schedule.status == ScheduleStatus.PENDING else "✅"
            self.schedule_listbox.insert(
                tk.END,
                f"{status_icon} {start_time} - {schedule.title}"
            )

    def _view_schedule(self, event):
        """查看日程详情"""
        selection = self.schedule_listbox.curselection()
        if selection:
            schedules = self.schedule_manager.get_upcoming_schedules(24 * 7)
            schedule = schedules[selection[0]]
            messagebox.showinfo(
                "日程详情",
                f"标题: {schedule.title}\n"
                f"描述: {schedule.description}\n"
                f"开始: {schedule.start_time.strftime('%Y-%m-%d %H:%M')}\n"
                f"结束: {schedule.end_time.strftime('%Y-%m-%d %H:%M')}"
            )

    # ========== 笔记功能 ==========

    def _add_note(self):
        """添加新笔记"""
        dialog = tk.Toplevel(self)
        dialog.title("新建笔记")
        dialog.geometry("400x350")
        dialog.transient(self)
        dialog.grab_set()

        ttk.Label(dialog, text="标题:").pack(pady=5)
        title_entry = ttk.Entry(dialog, width=45)
        title_entry.pack(pady=5)

        ttk.Label(dialog, text="内容:").pack(pady=5)
        content_text = scrolledtext.ScrolledText(dialog, width=45, height=12)
        content_text.pack(pady=5)

        def save():
            title = title_entry.get().strip()
            if not title:
                messagebox.showwarning("警告", "请输入标题")
                return

            note = Note(
                title=title,
                content=content_text.get("1.0", tk.END).strip()
            )

            if self.note_manager.add_note(note):
                messagebox.showinfo("成功", "笔记已保存")
                self._refresh_notes()
                dialog.destroy()
            else:
                messagebox.showerror("错误", "保存笔记失败")

        ttk.Button(dialog, text="保存", command=save).pack(pady=10)

    def _refresh_notes(self):
        """刷新笔记列表"""
        self.note_listbox.delete(0, tk.END)
        notes = self.note_manager.get_all_notes()

        for note in notes:
            pin_icon = "📌" if note.is_pinned else "📄"
            self.note_listbox.insert(
                tk.END,
                f"{pin_icon} {note.title}"
            )

    def _view_note(self, event):
        """查看笔记详情"""
        selection = self.note_listbox.curselection()
        if selection:
            notes = self.note_manager.get_all_notes()
            note = notes[selection[0]]
            
            # 创建查看窗口
            view_dialog = tk.Toplevel(self)
            view_dialog.title(f"笔记: {note.title}")
            view_dialog.geometry("400x350")

            content_text = scrolledtext.ScrolledText(view_dialog, wrap=tk.WORD)
            content_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
            content_text.insert("1.0", note.content)
            content_text.config(state=tk.DISABLED)

    # ========== 计划功能 ==========

    def _add_plan(self):
        """添加新计划"""
        dialog = tk.Toplevel(self)
        dialog.title("新建计划")
        dialog.geometry("350x200")
        dialog.transient(self)
        dialog.grab_set()

        ttk.Label(dialog, text="计划标题:").pack(pady=5)
        title_entry = ttk.Entry(dialog, width=40)
        title_entry.pack(pady=5)

        ttk.Label(dialog, text="目标描述:").pack(pady=5)
        goal_entry = ttk.Entry(dialog, width=40)
        goal_entry.pack(pady=5)

        def save():
            title = title_entry.get().strip()
            goal = goal_entry.get().strip()

            if not title:
                messagebox.showwarning("警告", "请输入计划标题")
                return

            plan = Plan(
                title=title,
                goal=goal,
                status=PlanStatus.NOT_STARTED
            )

            if self.plan_manager.add_plan(plan):
                messagebox.showinfo("成功", "计划已创建")
                self._refresh_plans()
                dialog.destroy()
            else:
                messagebox.showerror("错误", "创建计划失败")

        ttk.Button(dialog, text="创建", command=save).pack(pady=10)

    def _refresh_plans(self):
        """刷新计划列表"""
        self.plan_listbox.delete(0, tk.END)
        plans = self.plan_manager.get_all_plans()

        for plan in plans:
            status_icons = {
                PlanStatus.NOT_STARTED: "⭕",
                PlanStatus.IN_PROGRESS: "🔄",
                PlanStatus.COMPLETED: "✅",
                PlanStatus.PAUSED: "⏸️",
                PlanStatus.CANCELLED: "❌"
            }
            icon = status_icons.get(plan.status, "📋")
            progress_text = f"{int(plan.progress * 100)}%"
            self.plan_listbox.insert(
                tk.END,
                f"{icon} {plan.title} [{progress_text}]"
            )

    def _view_plan(self, event):
        """查看计划详情"""
        selection = self.plan_listbox.curselection()
        if selection:
            plans = self.plan_manager.get_all_plans()
            plan = plans[selection[0]]

            info = f"标题: {plan.title}\n"
            info += f"目标: {plan.goal}\n"
            info += f"状态: {plan.status.value}\n"
            info += f"进度: {int(plan.progress * 100)}%\n"
            info += f"任务数: {len(plan.tasks)}\n"
            info += f"已完成: {len([t for t in plan.tasks if t.status == TaskStatus.COMPLETED])}"

            messagebox.showinfo("计划详情", info)

    # ========== 统计功能 ==========

    def _refresh_stats(self):
        """刷新统计信息"""
        self.stats_text.config(state=tk.NORMAL)
        self.stats_text.delete("1.0", tk.END)

        # 获取各模块统计
        schedule_stats = self.schedule_manager.get_statistics()
        note_stats = self.note_manager.get_statistics()
        plan_stats = self.plan_manager.get_statistics()
        pomo_stats = self.pomodoro.get_status()

        # 构建统计文本
        stats_text = "=== 📊 小可的统计报告 ===\n\n"

        stats_text += "【番茄时钟】\n"
        stats_text += f"  今日完成: {pomo_stats['current_pomodoro']} 个番茄 🍅\n\n"

        stats_text += "【日程管理】\n"
        stats_text += f"  总计: {schedule_stats['total']} 个日程\n"
        stats_text += f"  待办: {schedule_stats['pending']} 个\n"
        stats_text += f"  已完成: {schedule_stats['completed']} 个\n"
        stats_text += f"  今日日程: {schedule_stats['today']} 个\n\n"

        stats_text += "【笔记管理】\n"
        stats_text += f"  总计: {note_stats['total']} 条笔记\n"
        stats_text += f"  置顶: {note_stats['pinned']} 条\n"
        stats_text += f"  分类数: {note_stats['categories']} 个\n"
        stats_text += f"  标签数: {note_stats['tags']} 个\n\n"

        stats_text += "【计划管理】\n"
        stats_text += f"  总计: {plan_stats['total']} 个计划\n"
        stats_text += f"  进行中: {plan_stats['in_progress']} 个\n"
        stats_text += f"  已完成: {plan_stats['completed']} 个\n"
        stats_text += f"  总任务: {plan_stats['total_tasks']} 个\n"
        stats_text += f"  已完成任务: {plan_stats['completed_tasks']} 个\n\n"

        stats_text += f"=== 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M')} ==="

        self.stats_text.insert("1.0", stats_text)
        self.stats_text.config(state=tk.DISABLED)

    # ========== 提醒系统 ==========

    def _start_reminder_check(self):
        """启动定时提醒检查"""
        self._check_reminders()

    def _check_reminders(self):
        """检查提醒事项"""
        try:
            # 检查即将到期的日程
            due_schedules = self.schedule_manager.check_due_schedules()

            for schedule in due_schedules:
                # 创建提醒通知
                minutes_until = int((schedule.start_time - datetime.now()).total_seconds() / 60)
                message = f"⏰ 提醒：{schedule.title}\n还有{minutes_until}分钟就要开始了哦！"

                self._update_character_status(message)
                messagebox.showinfo("日程提醒", message)

            # 更新过期日程
            self.schedule_manager.update_overdue_schedules()

        except Exception as e:
            debug_logger.log_error('Live2DAssistant', '检查提醒失败', e)

        # 每分钟检查一次
        self.after(60000, self._check_reminders)

    # ========== 辅助方法 ==========

    def _update_status(self, message: str):
        """更新状态栏"""
        self.status_label.config(text=message)
        debug_logger.log_info('Live2DAssistant', f'状态: {message}')

    def _update_character_status(self, message: str):
        """更新角色状态"""
        self.character_status_label.config(text=message)

    def _show_welcome_message(self):
        """显示欢迎消息"""
        welcome = "你好呀！我是小可~ 😊\n今天也要一起努力加油哦！\n有什么需要帮忙的随时告诉我～"
        self._update_character_status(welcome)
        self._append_chat_message("小可", welcome)


def main():
    """主函数"""
    try:
        app = Live2DAssistant()
        app.mainloop()
    except Exception as e:
        debug_logger.log_error('Main', '应用程序错误', e)
        messagebox.showerror("错误", f"应用程序错误: {str(e)}")


if __name__ == "__main__":
    main()
