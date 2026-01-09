"""
日程管理GUI窗口
提供可视化的日程查看、添加、编辑和删除功能
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
from datetime import datetime, date, timedelta
from typing import Optional, List
from schedule_manager import (
    ScheduleManager, Schedule, ScheduleType, SchedulePriority,
    RecurrencePattern
)


class ScheduleManagerWindow:
    """
    日程管理窗口
    """

    def __init__(self, parent, schedule_manager: ScheduleManager):
        """
        初始化日程管理窗口

        Args:
            parent: 父窗口
            schedule_manager: 日程管理器实例
        """
        self.parent = parent
        self.schedule_manager = schedule_manager
        
        # 创建窗口
        self.window = tk.Toplevel(parent)
        self.window.title("日程管理")
        self.window.geometry("1000x700")
        
        # 当前选中的日程
        self.selected_schedule = None
        
        # 设置窗口样式
        self._setup_styles()
        
        # 创建界面
        self._create_widgets()
        
        # 加载今天的日程
        self.current_date = date.today()
        self.refresh_schedules()

    def _setup_styles(self):
        """设置界面样式"""
        style = ttk.Style()
        style.configure('Title.TLabel', font=('微软雅黑', 14, 'bold'))
        style.configure('Subtitle.TLabel', font=('微软雅黑', 10))
        style.configure('Schedule.Treeview', rowheight=30)

    def _create_widgets(self):
        """创建界面组件"""
        # 主容器
        main_frame = ttk.Frame(self.window, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 顶部工具栏
        toolbar = ttk.Frame(main_frame)
        toolbar.pack(fill=tk.X, pady=(0, 10))

        # 日期选择区域
        date_frame = ttk.Frame(toolbar)
        date_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)

        ttk.Label(date_frame, text="查看日期:", font=('微软雅黑', 10)).pack(side=tk.LEFT, padx=5)
        
        # 日期导航按钮
        ttk.Button(date_frame, text="◀ 前一天", command=self.prev_day).pack(side=tk.LEFT, padx=2)
        ttk.Button(date_frame, text="今天", command=self.go_to_today).pack(side=tk.LEFT, padx=2)
        ttk.Button(date_frame, text="后一天 ▶", command=self.next_day).pack(side=tk.LEFT, padx=2)
        
        # 当前日期显示
        self.date_label = ttk.Label(date_frame, text="", font=('微软雅黑', 11, 'bold'))
        self.date_label.pack(side=tk.LEFT, padx=10)

        # 操作按钮区域
        button_frame = ttk.Frame(toolbar)
        button_frame.pack(side=tk.RIGHT)

        ttk.Button(button_frame, text="➕ 添加日程", command=self.add_schedule).pack(side=tk.LEFT, padx=2)
        ttk.Button(button_frame, text="✏️ 编辑", command=self.edit_schedule).pack(side=tk.LEFT, padx=2)
        ttk.Button(button_frame, text="🗑️ 删除", command=self.delete_schedule).pack(side=tk.LEFT, padx=2)
        ttk.Button(button_frame, text="🔄 刷新", command=self.refresh_schedules).pack(side=tk.LEFT, padx=2)

        # 日程列表区域
        list_frame = ttk.LabelFrame(main_frame, text="日程列表", padding="10")
        list_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        # 创建表格
        columns = ('time', 'title', 'type', 'priority', 'location', 'recurrence')
        self.schedule_tree = ttk.Treeview(list_frame, columns=columns, show='headings', style='Schedule.Treeview')
        
        # 设置列标题
        self.schedule_tree.heading('time', text='时间')
        self.schedule_tree.heading('title', text='标题')
        self.schedule_tree.heading('type', text='类型')
        self.schedule_tree.heading('priority', text='优先级')
        self.schedule_tree.heading('location', text='地点')
        self.schedule_tree.heading('recurrence', text='重复')

        # 设置列宽
        self.schedule_tree.column('time', width=120)
        self.schedule_tree.column('title', width=250)
        self.schedule_tree.column('type', width=100)
        self.schedule_tree.column('priority', width=80)
        self.schedule_tree.column('location', width=150)
        self.schedule_tree.column('recurrence', width=100)

        # 滚动条
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.schedule_tree.yview)
        self.schedule_tree.configure(yscrollcommand=scrollbar.set)

        self.schedule_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # 绑定双击事件
        self.schedule_tree.bind('<Double-1>', lambda e: self.edit_schedule())
        self.schedule_tree.bind('<<TreeviewSelect>>', self.on_schedule_select)

        # 日程详情区域
        detail_frame = ttk.LabelFrame(main_frame, text="日程详情", padding="10")
        detail_frame.pack(fill=tk.X)

        self.detail_text = scrolledtext.ScrolledText(detail_frame, height=6, wrap=tk.WORD, font=('微软雅黑', 9))
        self.detail_text.pack(fill=tk.BOTH, expand=True)
        self.detail_text.config(state=tk.DISABLED)

        # 统计信息区域
        stats_frame = ttk.Frame(main_frame)
        stats_frame.pack(fill=tk.X, pady=(10, 0))
        
        self.stats_label = ttk.Label(stats_frame, text="", font=('微软雅黑', 9))
        self.stats_label.pack(side=tk.LEFT)

    def _update_date_label(self):
        """更新日期标签"""
        weekday_names = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']
        weekday = weekday_names[self.current_date.weekday()]
        date_str = self.current_date.strftime('%Y年%m月%d日')
        self.date_label.config(text=f"{date_str} {weekday}")

    def refresh_schedules(self):
        """刷新日程列表"""
        # 清空现有项目
        for item in self.schedule_tree.get_children():
            self.schedule_tree.delete(item)

        # 更新日期标签
        self._update_date_label()

        # 获取当前日期的日程
        date_str = self.current_date.strftime('%Y-%m-%d')
        schedules = self.schedule_manager.get_schedules_by_date(date_str)

        # 类型映射
        type_map = {
            ScheduleType.RECURRING: '周期日程',
            ScheduleType.APPOINTMENT: '预约日程',
            ScheduleType.IMPROMPTU: '临时日程'
        }

        priority_map = {
            SchedulePriority.LOW: '低',
            SchedulePriority.MEDIUM: '中',
            SchedulePriority.HIGH: '高',
            SchedulePriority.URGENT: '紧急'
        }

        recurrence_map = {
            RecurrencePattern.NONE: '不重复',
            RecurrencePattern.DAILY: '每天',
            RecurrencePattern.WEEKLY: '每周',
            RecurrencePattern.WEEKDAYS: '工作日',
            RecurrencePattern.WEEKENDS: '周末',
            RecurrencePattern.MONTHLY: '每月',
            RecurrencePattern.CUSTOM: '自定义'
        }

        # 添加日程到表格
        for schedule in schedules:
            time_str = f"{schedule.start_time} - {schedule.end_time}"
            type_str = type_map.get(schedule.schedule_type, '未知')
            priority_str = priority_map.get(schedule.priority, '未知')
            location_str = schedule.location or '-'
            recurrence_str = recurrence_map.get(schedule.recurrence_pattern, '未知')

            # 根据优先级设置标签
            tags = []
            if schedule.priority == SchedulePriority.URGENT:
                tags.append('urgent')
            elif schedule.priority == SchedulePriority.HIGH:
                tags.append('high')

            self.schedule_tree.insert('', tk.END, 
                                     values=(time_str, schedule.title, type_str, 
                                           priority_str, location_str, recurrence_str),
                                     tags=tags)

        # 设置标签颜色
        self.schedule_tree.tag_configure('urgent', background='#ffebee')
        self.schedule_tree.tag_configure('high', background='#fff3e0')

        # 更新统计信息
        self._update_statistics()

        # 清空详情
        self.show_schedule_detail(None)

    def _update_statistics(self):
        """更新统计信息"""
        stats = self.schedule_manager.get_statistics()
        text = (f"总计: {stats['total_schedules']} 个日程 | "
                f"周期: {stats['recurring']} | "
                f"预约: {stats['appointments']} | "
                f"临时: {stats['impromptu']}")
        self.stats_label.config(text=text)

    def on_schedule_select(self, event):
        """日程选择事件"""
        selection = self.schedule_tree.selection()
        if not selection:
            self.selected_schedule = None
            self.show_schedule_detail(None)
            return

        # 获取选中的行索引
        item = selection[0]
        item_index = self.schedule_tree.index(item)
        
        # 获取当前日期的日程列表
        date_str = self.current_date.strftime('%Y-%m-%d')
        schedules = self.schedule_manager.get_schedules_by_date(date_str)
        
        # 根据索引获取对应的日程
        if 0 <= item_index < len(schedules):
            self.selected_schedule = schedules[item_index]
            self.show_schedule_detail(self.selected_schedule)
        else:
            self.selected_schedule = None
            self.show_schedule_detail(None)

    def show_schedule_detail(self, schedule: Optional[Schedule]):
        """显示日程详情"""
        self.detail_text.config(state=tk.NORMAL)
        self.detail_text.delete(1.0, tk.END)

        if schedule is None:
            self.detail_text.insert(tk.END, "请选择一个日程查看详情")
        else:
            detail = f"标题: {schedule.title}\n"
            detail += f"时间: {schedule.start_time} - {schedule.end_time}\n"
            detail += f"日期: {schedule.date}\n"
            
            if schedule.description:
                detail += f"描述: {schedule.description}\n"
            
            if schedule.location:
                detail += f"地点: {schedule.location}\n"
            
            # 类型和优先级
            type_map = {
                ScheduleType.RECURRING: '周期日程',
                ScheduleType.APPOINTMENT: '预约日程',
                ScheduleType.IMPROMPTU: '临时日程'
            }
            priority_map = {
                SchedulePriority.LOW: '低',
                SchedulePriority.MEDIUM: '中',
                SchedulePriority.HIGH: '高',
                SchedulePriority.URGENT: '紧急'
            }
            
            detail += f"类型: {type_map.get(schedule.schedule_type, '未知')}\n"
            detail += f"优先级: {priority_map.get(schedule.priority, '未知')}\n"
            
            # 重复信息
            if schedule.is_recurring():
                recurrence_map = {
                    RecurrencePattern.DAILY: '每天',
                    RecurrencePattern.WEEKLY: '每周',
                    RecurrencePattern.WEEKDAYS: '工作日（周一到周五）',
                    RecurrencePattern.WEEKENDS: '周末',
                    RecurrencePattern.MONTHLY: '每月',
                    RecurrencePattern.CUSTOM: '自定义'
                }
                detail += f"重复: {recurrence_map.get(schedule.recurrence_pattern, '未知')}\n"
                
                if schedule.recurrence_end_date:
                    detail += f"重复截止: {schedule.recurrence_end_date}\n"

            self.detail_text.insert(tk.END, detail)

        self.detail_text.config(state=tk.DISABLED)

    def prev_day(self):
        """前一天"""
        self.current_date -= timedelta(days=1)
        self.refresh_schedules()

    def next_day(self):
        """后一天"""
        self.current_date += timedelta(days=1)
        self.refresh_schedules()

    def go_to_today(self):
        """回到今天"""
        self.current_date = date.today()
        self.refresh_schedules()

    def add_schedule(self):
        """添加新日程"""
        dialog = ScheduleEditDialog(self.window, self.schedule_manager, 
                                    default_date=self.current_date.strftime('%Y-%m-%d'))
        self.window.wait_window(dialog.dialog)
        
        if dialog.result:
            self.refresh_schedules()

    def edit_schedule(self):
        """编辑选中的日程"""
        if not self.selected_schedule:
            messagebox.showwarning("提示", "请先选择一个日程")
            return

        dialog = ScheduleEditDialog(self.window, self.schedule_manager, 
                                    schedule=self.selected_schedule)
        self.window.wait_window(dialog.dialog)
        
        if dialog.result:
            self.refresh_schedules()

    def delete_schedule(self):
        """删除选中的日程"""
        if not self.selected_schedule:
            messagebox.showwarning("提示", "请先选择一个日程")
            return

        if messagebox.askyesno("确认删除", 
                              f"确定要删除日程「{self.selected_schedule.title}」吗？"):
            if self.schedule_manager.delete_schedule(self.selected_schedule.schedule_id):
                messagebox.showinfo("成功", "日程已删除")
                self.refresh_schedules()
            else:
                messagebox.showerror("错误", "删除日程失败")


class ScheduleEditDialog:
    """
    日程编辑对话框
    """

    def __init__(self, parent, schedule_manager: ScheduleManager, 
                 schedule: Optional[Schedule] = None, default_date: str = None):
        """
        初始化编辑对话框

        Args:
            parent: 父窗口
            schedule_manager: 日程管理器
            schedule: 要编辑的日程（None表示新建）
            default_date: 默认日期
        """
        self.schedule_manager = schedule_manager
        self.schedule = schedule
        self.result = False

        # 创建对话框
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("编辑日程" if schedule else "添加日程")
        self.dialog.geometry("500x600")
        self.dialog.transient(parent)
        self.dialog.grab_set()

        # 创建表单
        self._create_form(default_date)

    def _create_form(self, default_date: str):
        """创建表单"""
        main_frame = ttk.Frame(self.dialog, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)

        row = 0

        # 标题
        ttk.Label(main_frame, text="标题:").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.title_var = tk.StringVar(value=self.schedule.title if self.schedule else "")
        ttk.Entry(main_frame, textvariable=self.title_var, width=40).grid(row=row, column=1, pady=5, sticky=tk.EW)
        row += 1

        # 描述
        ttk.Label(main_frame, text="描述:").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.description_text = tk.Text(main_frame, height=3, width=40)
        if self.schedule and self.schedule.description:
            self.description_text.insert(1.0, self.schedule.description)
        self.description_text.grid(row=row, column=1, pady=5, sticky=tk.EW)
        row += 1

        # 日期
        ttk.Label(main_frame, text="日期:").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.date_var = tk.StringVar(value=self.schedule.date if self.schedule else (default_date or date.today().strftime('%Y-%m-%d')))
        ttk.Entry(main_frame, textvariable=self.date_var, width=40).grid(row=row, column=1, pady=5, sticky=tk.EW)
        ttk.Label(main_frame, text="(格式: YYYY-MM-DD)", font=('微软雅黑', 8)).grid(row=row, column=2, sticky=tk.W, padx=5)
        row += 1

        # 时间
        time_frame = ttk.Frame(main_frame)
        time_frame.grid(row=row, column=1, pady=5, sticky=tk.EW)
        
        ttk.Label(main_frame, text="时间:").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.start_time_var = tk.StringVar(value=self.schedule.start_time if self.schedule else "09:00")
        ttk.Entry(time_frame, textvariable=self.start_time_var, width=8).pack(side=tk.LEFT)
        ttk.Label(time_frame, text=" - ").pack(side=tk.LEFT, padx=5)
        self.end_time_var = tk.StringVar(value=self.schedule.end_time if self.schedule else "10:00")
        ttk.Entry(time_frame, textvariable=self.end_time_var, width=8).pack(side=tk.LEFT)
        ttk.Label(time_frame, text="(格式: HH:MM)", font=('微软雅黑', 8)).pack(side=tk.LEFT, padx=5)
        row += 1

        # 地点
        ttk.Label(main_frame, text="地点:").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.location_var = tk.StringVar(value=self.schedule.location if self.schedule else "")
        ttk.Entry(main_frame, textvariable=self.location_var, width=40).grid(row=row, column=1, pady=5, sticky=tk.EW)
        row += 1

        # 类型
        ttk.Label(main_frame, text="类型:").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.type_var = tk.StringVar(value=self.schedule.schedule_type.value if self.schedule else ScheduleType.APPOINTMENT.value)
        type_combo = ttk.Combobox(main_frame, textvariable=self.type_var, state='readonly', width=37)
        type_combo['values'] = ('recurring', 'appointment', 'impromptu')
        type_combo.grid(row=row, column=1, pady=5, sticky=tk.EW)
        row += 1

        # 优先级
        ttk.Label(main_frame, text="优先级:").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.priority_var = tk.IntVar(value=self.schedule.priority.value if self.schedule else SchedulePriority.MEDIUM.value)
        priority_combo = ttk.Combobox(main_frame, textvariable=self.priority_var, state='readonly', width=37)
        priority_combo['values'] = (1, 2, 3, 4)
        priority_combo.grid(row=row, column=1, pady=5, sticky=tk.EW)
        ttk.Label(main_frame, text="(1=低, 2=中, 3=高, 4=紧急)", font=('微软雅黑', 8)).grid(row=row, column=2, sticky=tk.W, padx=5)
        row += 1

        # 重复模式
        ttk.Label(main_frame, text="重复:").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.recurrence_var = tk.StringVar(value=self.schedule.recurrence_pattern.value if self.schedule else RecurrencePattern.NONE.value)
        recurrence_combo = ttk.Combobox(main_frame, textvariable=self.recurrence_var, state='readonly', width=37)
        recurrence_combo['values'] = ('none', 'daily', 'weekly', 'weekdays', 'weekends', 'monthly')
        recurrence_combo.grid(row=row, column=1, pady=5, sticky=tk.EW)
        row += 1

        # 重复截止日期
        ttk.Label(main_frame, text="重复截止:").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.recurrence_end_var = tk.StringVar(value=self.schedule.recurrence_end_date if self.schedule and self.schedule.recurrence_end_date else "")
        ttk.Entry(main_frame, textvariable=self.recurrence_end_var, width=40).grid(row=row, column=1, pady=5, sticky=tk.EW)
        ttk.Label(main_frame, text="(可选)", font=('微软雅黑', 8)).grid(row=row, column=2, sticky=tk.W, padx=5)
        row += 1

        # 按钮
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=row, column=0, columnspan=3, pady=20)
        
        ttk.Button(button_frame, text="保存", command=self.save).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="取消", command=self.cancel).pack(side=tk.LEFT, padx=5)

        main_frame.columnconfigure(1, weight=1)

    def save(self):
        """保存日程"""
        # 验证输入
        title = self.title_var.get().strip()
        if not title:
            messagebox.showerror("错误", "请输入标题")
            return

        date_str = self.date_var.get().strip()
        if not date_str:
            messagebox.showerror("错误", "请输入日期")
            return

        start_time = self.start_time_var.get().strip()
        end_time = self.end_time_var.get().strip()
        if not start_time or not end_time:
            messagebox.showerror("错误", "请输入时间")
            return

        # 获取其他字段
        description = self.description_text.get(1.0, tk.END).strip()
        location = self.location_var.get().strip()
        schedule_type = ScheduleType(self.type_var.get())
        priority = SchedulePriority(self.priority_var.get())
        recurrence_pattern = RecurrencePattern(self.recurrence_var.get())
        recurrence_end_date = self.recurrence_end_var.get().strip() or None

        try:
            if self.schedule:
                # 更新现有日程
                success, message = self.schedule_manager.update_schedule(
                    self.schedule.schedule_id,
                    title=title,
                    description=description,
                    date=date_str,
                    start_time=start_time,
                    end_time=end_time,
                    location=location,
                    schedule_type=schedule_type,
                    priority=priority,
                    recurrence_pattern=recurrence_pattern,
                    recurrence_end_date=recurrence_end_date
                )
                
                if success:
                    messagebox.showinfo("成功", "日程已更新")
                    self.result = True
                    self.dialog.destroy()
                else:
                    messagebox.showerror("错误", f"更新失败: {message}")
            else:
                # 添加新日程
                success, schedule, message = self.schedule_manager.add_schedule(
                    title=title,
                    description=description,
                    schedule_type=schedule_type,
                    priority=priority,
                    start_time=start_time,
                    end_time=end_time,
                    date=date_str,
                    recurrence_pattern=recurrence_pattern,
                    recurrence_end_date=recurrence_end_date,
                    location=location,
                    auto_resolve_conflicts=True
                )
                
                if success:
                    messagebox.showinfo("成功", message)
                    self.result = True
                    self.dialog.destroy()
                else:
                    messagebox.showerror("错误", f"添加失败: {message}")
        except Exception as e:
            messagebox.showerror("错误", f"操作失败: {str(e)}")

    def cancel(self):
        """取消"""
        self.dialog.destroy()
