"""
日程管理GUI模块
独立的日程管理界面
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, simpledialog
from typing import Dict, Any, List
from datetime import datetime, timedelta
from schedule_manager import ScheduleManager, ScheduleType, SchedulePriority
from database_manager import DatabaseManager


class ScheduleManagerGUI:
    """
    日程管理GUI界面
    提供独立的日程管理功能
    """

    def __init__(self, parent_frame, db_manager: DatabaseManager = None):
        """
        初始化日程管理GUI

        Args:
            parent_frame: 父容器
            db_manager: 数据库管理器实例
        """
        self.parent = parent_frame
        self.db = db_manager or DatabaseManager()
        
        # 获取或创建schedule_manager
        if hasattr(self.db, 'schedule_manager'):
            self.schedule_manager = self.db.schedule_manager
        else:
            self.schedule_manager = ScheduleManager(self.db)
        
        # 自动刷新相关
        self.auto_refresh_enabled = True
        self.refresh_interval = 3000  # 3秒刷新一次
        self.refresh_job = None
        
        # 创建界面
        self.create_widgets()
        
        # 首次刷新数据
        self.refresh_schedules()
        
        # 启动自动刷新
        self.start_auto_refresh()
        
        # 绑定窗口关闭事件
        self.parent.bind('<Destroy>', self.on_destroy)

    def on_destroy(self, event=None):
        """窗口销毁时的清理工作"""
        self.stop_auto_refresh()

    def create_widgets(self):
        """创建所有GUI组件"""
        # 顶部工具栏
        toolbar = ttk.Frame(self.parent)
        toolbar.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(toolbar, text="📅 日程管理", font=("微软雅黑", 12, "bold")).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(toolbar, text="➕ 添加日程", command=self.add_schedule, width=12).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="✏ 编辑", command=self.edit_schedule, width=10).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="🗑 删除", command=self.delete_schedule, width=10).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="🔄 刷新", command=self.refresh_schedules, width=10).pack(side=tk.LEFT, padx=2)
        
        # 自动刷新开关
        self.auto_refresh_btn = ttk.Button(toolbar, text="⏸ 暂停刷新", command=self.toggle_auto_refresh, width=12)
        self.auto_refresh_btn.pack(side=tk.LEFT, padx=2)
        
        # 待确认日程提示
        self.pending_label = ttk.Label(toolbar, text="", font=("微软雅黑", 9), foreground="orange")
        self.pending_label.pack(side=tk.RIGHT, padx=10)
        
        # 分割线
        ttk.Separator(self.parent, orient=tk.HORIZONTAL).pack(fill=tk.X, padx=5, pady=2)
        
        # 筛选器区域
        filter_frame = ttk.Frame(self.parent)
        filter_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(filter_frame, text="类型:").pack(side=tk.LEFT, padx=(5, 2))
        self.type_var = tk.StringVar(value="全部")
        type_combo = ttk.Combobox(filter_frame, textvariable=self.type_var, width=12, state="readonly")
        type_combo['values'] = ['全部', '周期日程', '预约日程', '临时日程']
        type_combo.pack(side=tk.LEFT, padx=2)
        type_combo.bind('<<ComboboxSelected>>', lambda e: self.refresh_schedules())
        
        ttk.Label(filter_frame, text="日期:").pack(side=tk.LEFT, padx=(15, 2))
        self.date_var = tk.StringVar(value="今天")
        date_combo = ttk.Combobox(filter_frame, textvariable=self.date_var, width=12, state="readonly")
        date_combo['values'] = ['今天', '明天', '本周', '全部']
        date_combo.pack(side=tk.LEFT, padx=2)
        date_combo.bind('<<ComboboxSelected>>', lambda e: self.refresh_schedules())
        
        ttk.Label(filter_frame, text="状态:").pack(side=tk.LEFT, padx=(15, 2))
        self.status_var = tk.StringVar(value="全部")
        status_combo = ttk.Combobox(filter_frame, textvariable=self.status_var, width=12, state="readonly")
        status_combo['values'] = ['全部', '待确认', '已确认', '不需要']
        status_combo.pack(side=tk.LEFT, padx=2)
        status_combo.bind('<<ComboboxSelected>>', lambda e: self.refresh_schedules())
        
        # 日程列表区域
        list_frame = ttk.Frame(self.parent)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 滚动条
        scrollbar_y = ttk.Scrollbar(list_frame, orient=tk.VERTICAL)
        scrollbar_x = ttk.Scrollbar(list_frame, orient=tk.HORIZONTAL)
        
        # Treeview
        self.tree = ttk.Treeview(
            list_frame,
            columns=("title", "type", "priority", "time", "status", "queryable", "description"),
            show="headings",
            yscrollcommand=scrollbar_y.set,
            xscrollcommand=scrollbar_x.set
        )
        
        # 配置列
        self.tree.heading("title", text="标题")
        self.tree.heading("type", text="类型")
        self.tree.heading("priority", text="优先级")
        self.tree.heading("time", text="时间")
        self.tree.heading("status", text="协作状态")
        self.tree.heading("queryable", text="可查询")
        self.tree.heading("description", text="描述")
        
        self.tree.column("title", width=180, minwidth=150, stretch=False)
        self.tree.column("type", width=80, minwidth=70, stretch=False)
        self.tree.column("priority", width=70, minwidth=60, stretch=False)
        self.tree.column("time", width=280, minwidth=200, stretch=False)
        self.tree.column("status", width=90, minwidth=80, stretch=False)
        self.tree.column("queryable", width=70, minwidth=60, stretch=False)
        self.tree.column("description", width=250, minwidth=150, stretch=True)
        
        scrollbar_y.config(command=self.tree.yview)
        scrollbar_x.config(command=self.tree.xview)
        
        # 布局
        self.tree.grid(row=0, column=0, sticky="nsew")
        scrollbar_y.grid(row=0, column=1, sticky="ns")
        scrollbar_x.grid(row=1, column=0, sticky="ew")
        
        list_frame.grid_rowconfigure(0, weight=1)
        list_frame.grid_columnconfigure(0, weight=1)
        
        # 双击编辑
        self.tree.bind("<Double-1>", lambda e: self.edit_schedule())
        
        # 右键菜单
        self.context_menu = tk.Menu(self.tree, tearoff=0)
        self.context_menu.add_command(label="查看详情", command=self.view_schedule_details)
        self.context_menu.add_command(label="编辑", command=self.edit_schedule)
        self.context_menu.add_command(label="删除", command=self.delete_schedule)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="✓ 确认协作", command=self.confirm_collaboration)
        self.context_menu.add_command(label="✗ 拒绝协作", command=self.reject_collaboration)
        
        self.tree.bind("<Button-3>", self.show_context_menu)
        
        # 底部统计区域
        stats_frame = ttk.Frame(self.parent)
        stats_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.stats_label = ttk.Label(stats_frame, text="", font=("微软雅黑", 9))
        self.stats_label.pack(side=tk.LEFT, padx=5)
        
        self.last_refresh_label = ttk.Label(stats_frame, text="", font=("微软雅黑", 8), foreground="gray")
        self.last_refresh_label.pack(side=tk.RIGHT, padx=5)

    def refresh_schedules(self):
        """刷新日程列表"""
        # 清空现有内容
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        try:
            # 根据日期筛选确定时间范围
            date_filter = self.date_var.get()
            today = datetime.now().date()
            
            if date_filter == "今天":
                start_date = today
                end_date = today
            elif date_filter == "明天":
                start_date = today + timedelta(days=1)
                end_date = today + timedelta(days=1)
            elif date_filter == "本周":
                days_since_monday = today.weekday()
                start_date = today - timedelta(days=days_since_monday)
                end_date = start_date + timedelta(days=6)
            else:  # 全部
                start_date = today - timedelta(days=365)
                end_date = today + timedelta(days=365)
            
            start_time = datetime.combine(start_date, datetime.min.time()).isoformat()
            end_time = datetime.combine(end_date, datetime.max.time()).isoformat()
            
            # 获取日程
            schedules = self.schedule_manager.get_schedules_by_time_range(
                start_time, end_time, queryable_only=False, active_only=True
            )
            
            # 根据类型筛选
            type_filter = self.type_var.get()
            type_map = {
                '周期日程': 'recurring',
                '预约日程': 'appointment',
                '临时日程': 'temporary'
            }
            
            if type_filter != "全部":
                filter_type = type_map.get(type_filter)
                schedules = [s for s in schedules if s.schedule_type.value == filter_type]
            
            # 根据状态筛选
            status_filter = self.status_var.get()
            status_map = {
                '待确认': 'pending',
                '已确认': 'confirmed',
                '不需要': 'not_required'
            }
            
            if status_filter != "全部":
                filter_status = status_map.get(status_filter)
                schedules = [s for s in schedules if s.collaboration_status.value == filter_status]
            
            # 类型映射（显示用）
            type_display_map = {
                'recurring': '周期',
                'appointment': '预约',
                'temporary': '临时'
            }
            
            # 优先级映射
            priority_display_map = {
                1: '低',
                2: '中',
                3: '高',
                4: '关键'
            }
            
            # 协作状态映射
            collab_status_map = {
                'not_required': '不需要',
                'pending': '待确认',
                'confirmed': '已确认',
                'rejected': '已拒绝'
            }
            
            # 填充数据
            pending_count = 0
            for schedule in schedules:
                start_dt = datetime.fromisoformat(schedule.start_time)
                end_dt = datetime.fromisoformat(schedule.end_time)
                time_str = f"{start_dt.strftime('%Y-%m-%d %H:%M')} - {end_dt.strftime('%H:%M')}"
                
                schedule_type = type_display_map.get(schedule.schedule_type.value, schedule.schedule_type.value)
                priority = priority_display_map.get(schedule.priority.value, str(schedule.priority.value))
                status = collab_status_map.get(schedule.collaboration_status.value, schedule.collaboration_status.value)
                queryable = "是" if schedule.is_queryable else "否"
                description = schedule.description[:50] + "..." if len(schedule.description) > 50 else schedule.description
                
                # 统计待确认数量
                if schedule.collaboration_status.value == 'pending':
                    pending_count += 1
                
                # 添加颜色标记
                tags = []
                if schedule.collaboration_status.value == 'pending':
                    tags.append('pending')
                elif schedule.priority.value >= 3:
                    tags.append('high_priority')
                
                self.tree.insert(
                    "",
                    tk.END,
                    values=(schedule.title, schedule_type, priority, time_str, status, queryable, description),
                    tags=(schedule.schedule_id,) + tuple(tags)
                )
            
            # 配置标签颜色
            self.tree.tag_configure('pending', foreground='orange', font=("微软雅黑", 9, "bold"))
            self.tree.tag_configure('high_priority', foreground='red')
            
            # 更新待确认提示
            if pending_count > 0:
                self.pending_label.config(text=f"⚠️ 有 {pending_count} 个待确认的协作日程")
            else:
                self.pending_label.config(text="")
            
            # 更新统计信息
            stats = self.schedule_manager.get_statistics()
            stats_text = (f"总计: {len(schedules)} 个日程 (显示中) | "
                         f"全部: {stats['total_schedules']} | "
                         f"周期: {stats['recurring']} | "
                         f"预约: {stats['appointments']} | "
                         f"临时: {stats['temporary']} | "
                         f"待确认: {stats['pending_collaboration']}")
            self.stats_label.config(text=stats_text)
            
            # 更新刷新时间
            current_time = datetime.now().strftime("%H:%M:%S")
            self.last_refresh_label.config(text=f"最后刷新: {current_time}")
            
        except Exception as e:
            messagebox.showerror("错误", f"刷新日程列表失败:\n{str(e)}")

    def add_schedule(self):
        """添加新日程"""
        dialog = tk.Toplevel(self.parent)
        dialog.title("添加日程")
        dialog.geometry("550x500")
        dialog.transient(self.parent)
        dialog.grab_set()
        
        # 创建表单
        form_frame = ttk.Frame(dialog, padding=20)
        form_frame.pack(fill=tk.BOTH, expand=True)
        
        # 标题
        ttk.Label(form_frame, text="标题:", font=("微软雅黑", 9)).grid(row=0, column=0, sticky=tk.W, pady=5)
        title_entry = ttk.Entry(form_frame, width=45, font=("微软雅黑", 9))
        title_entry.grid(row=0, column=1, pady=5, sticky=tk.EW)
        
        # 描述
        ttk.Label(form_frame, text="描述:", font=("微软雅黑", 9)).grid(row=1, column=0, sticky=tk.W, pady=5)
        description_text = tk.Text(form_frame, width=45, height=4, font=("微软雅黑", 9))
        description_text.grid(row=1, column=1, pady=5, sticky=tk.EW)
        
        # 类型
        ttk.Label(form_frame, text="类型:", font=("微软雅黑", 9)).grid(row=2, column=0, sticky=tk.W, pady=5)
        type_var = tk.StringVar(value="预约日程")
        type_combo = ttk.Combobox(form_frame, textvariable=type_var, width=43, state="readonly", font=("微软雅黑", 9))
        type_combo['values'] = ['周期日程', '预约日程', '临时日程']
        type_combo.grid(row=2, column=1, pady=5, sticky=tk.EW)
        
        # 优先级
        ttk.Label(form_frame, text="优先级:", font=("微软雅黑", 9)).grid(row=3, column=0, sticky=tk.W, pady=5)
        priority_var = tk.StringVar(value="中")
        priority_combo = ttk.Combobox(form_frame, textvariable=priority_var, width=43, state="readonly", font=("微软雅黑", 9))
        priority_combo['values'] = ['低', '中', '高', '关键']
        priority_combo.grid(row=3, column=1, pady=5, sticky=tk.EW)
        
        # 开始时间
        ttk.Label(form_frame, text="开始时间:", font=("微软雅黑", 9)).grid(row=4, column=0, sticky=tk.W, pady=5)
        start_frame = ttk.Frame(form_frame)
        start_frame.grid(row=4, column=1, pady=5, sticky=tk.EW)
        
        now = datetime.now()
        start_date_entry = ttk.Entry(start_frame, width=14, font=("微软雅黑", 9))
        start_date_entry.insert(0, now.strftime("%Y-%m-%d"))
        start_date_entry.pack(side=tk.LEFT, padx=2)
        
        start_time_entry = ttk.Entry(start_frame, width=10, font=("微软雅黑", 9))
        start_time_entry.insert(0, "09:00")
        start_time_entry.pack(side=tk.LEFT, padx=2)
        
        # 结束时间
        ttk.Label(form_frame, text="结束时间:", font=("微软雅黑", 9)).grid(row=5, column=0, sticky=tk.W, pady=5)
        end_frame = ttk.Frame(form_frame)
        end_frame.grid(row=5, column=1, pady=5, sticky=tk.EW)
        
        end_date_entry = ttk.Entry(end_frame, width=14, font=("微软雅黑", 9))
        end_date_entry.insert(0, now.strftime("%Y-%m-%d"))
        end_date_entry.pack(side=tk.LEFT, padx=2)
        
        end_time_entry = ttk.Entry(end_frame, width=10, font=("微软雅黑", 9))
        end_time_entry.insert(0, "11:00")
        end_time_entry.pack(side=tk.LEFT, padx=2)
        
        # 涉及用户参与
        involves_user_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(form_frame, text="涉及用户参与（需要确认）", variable=involves_user_var, 
                       style="TCheckbutton").grid(row=6, column=1, pady=5, sticky=tk.W)
        
        form_frame.grid_columnconfigure(1, weight=1)
        
        # 按钮区域
        button_frame = ttk.Frame(dialog)
        button_frame.pack(fill=tk.X, padx=20, pady=10)
        
        def save_schedule():
            try:
                title = title_entry.get().strip()
                if not title:
                    messagebox.showwarning("警告", "请输入标题")
                    return
                
                description = description_text.get("1.0", tk.END).strip()
                
                # 类型映射
                type_map = {
                    '周期日程': ScheduleType.RECURRING,
                    '预约日程': ScheduleType.APPOINTMENT,
                    '临时日程': ScheduleType.TEMPORARY
                }
                schedule_type = type_map[type_var.get()]
                
                # 优先级映射
                priority_map = {
                    '低': SchedulePriority.LOW,
                    '中': SchedulePriority.MEDIUM,
                    '高': SchedulePriority.HIGH,
                    '关键': SchedulePriority.CRITICAL
                }
                priority = priority_map[priority_var.get()]
                
                # 解析时间
                start_date = start_date_entry.get().strip()
                start_time = start_time_entry.get().strip()
                end_date = end_date_entry.get().strip()
                end_time = end_time_entry.get().strip()
                
                start_datetime = datetime.strptime(f"{start_date} {start_time}", "%Y-%m-%d %H:%M")
                end_datetime = datetime.strptime(f"{end_date} {end_time}", "%Y-%m-%d %H:%M")
                
                # 创建日程
                success, schedule, message = self.schedule_manager.create_schedule(
                    title=title,
                    description=description,
                    schedule_type=schedule_type,
                    start_time=start_datetime.isoformat(),
                    end_time=end_datetime.isoformat(),
                    priority=priority,
                    involves_user=involves_user_var.get() if schedule_type == ScheduleType.TEMPORARY else False,
                    check_conflict=True
                )
                
                if success:
                    messagebox.showinfo("成功", message)
                    dialog.destroy()
                    self.refresh_schedules()
                else:
                    messagebox.showerror("错误", message)
                    
            except ValueError as e:
                messagebox.showerror("错误", f"时间格式不正确:\n{str(e)}")
            except Exception as e:
                messagebox.showerror("错误", f"创建日程失败:\n{str(e)}")
        
        ttk.Button(button_frame, text="💾 保存", command=save_schedule, width=12).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="✗ 取消", command=dialog.destroy, width=12).pack(side=tk.LEFT, padx=5)

    def edit_schedule(self):
        """编辑选中的日程"""
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("警告", "请选择要编辑的日程")
            return
        
        item = selection[0]
        schedule_id = self.tree.item(item)['tags'][0]
        
        try:
            schedule = self.schedule_manager.get_schedule(schedule_id)
            if not schedule:
                messagebox.showerror("错误", "日程不存在")
                return
            
            # 创建编辑对话框（与添加类似，但预填充数据）
            dialog = tk.Toplevel(self.parent)
            dialog.title("编辑日程")
            dialog.geometry("550x450")
            dialog.transient(self.parent)
            dialog.grab_set()
            
            form_frame = ttk.Frame(dialog, padding=20)
            form_frame.pack(fill=tk.BOTH, expand=True)
            
            # 标题
            ttk.Label(form_frame, text="标题:", font=("微软雅黑", 9)).grid(row=0, column=0, sticky=tk.W, pady=5)
            title_entry = ttk.Entry(form_frame, width=45, font=("微软雅黑", 9))
            title_entry.insert(0, schedule.title)
            title_entry.grid(row=0, column=1, pady=5, sticky=tk.EW)
            
            # 描述
            ttk.Label(form_frame, text="描述:", font=("微软雅黑", 9)).grid(row=1, column=0, sticky=tk.W, pady=5)
            description_text = tk.Text(form_frame, width=45, height=4, font=("微软雅黑", 9))
            description_text.insert("1.0", schedule.description)
            description_text.grid(row=1, column=1, pady=5, sticky=tk.EW)
            
            # 优先级
            ttk.Label(form_frame, text="优先级:", font=("微软雅黑", 9)).grid(row=2, column=0, sticky=tk.W, pady=5)
            priority_map = {1: '低', 2: '中', 3: '高', 4: '关键'}
            priority_var = tk.StringVar(value=priority_map[schedule.priority.value])
            priority_combo = ttk.Combobox(form_frame, textvariable=priority_var, width=43, state="readonly", font=("微软雅黑", 9))
            priority_combo['values'] = ['低', '中', '高', '关键']
            priority_combo.grid(row=2, column=1, pady=5, sticky=tk.EW)
            
            # 开始时间
            start_dt = datetime.fromisoformat(schedule.start_time)
            end_dt = datetime.fromisoformat(schedule.end_time)
            
            ttk.Label(form_frame, text="开始时间:", font=("微软雅黑", 9)).grid(row=3, column=0, sticky=tk.W, pady=5)
            start_frame = ttk.Frame(form_frame)
            start_frame.grid(row=3, column=1, pady=5, sticky=tk.EW)
            
            start_date_entry = ttk.Entry(start_frame, width=14, font=("微软雅黑", 9))
            start_date_entry.insert(0, start_dt.strftime("%Y-%m-%d"))
            start_date_entry.pack(side=tk.LEFT, padx=2)
            
            start_time_entry = ttk.Entry(start_frame, width=10, font=("微软雅黑", 9))
            start_time_entry.insert(0, start_dt.strftime("%H:%M"))
            start_time_entry.pack(side=tk.LEFT, padx=2)
            
            # 结束时间
            ttk.Label(form_frame, text="结束时间:", font=("微软雅黑", 9)).grid(row=4, column=0, sticky=tk.W, pady=5)
            end_frame = ttk.Frame(form_frame)
            end_frame.grid(row=4, column=1, pady=5, sticky=tk.EW)
            
            end_date_entry = ttk.Entry(end_frame, width=14, font=("微软雅黑", 9))
            end_date_entry.insert(0, end_dt.strftime("%Y-%m-%d"))
            end_date_entry.pack(side=tk.LEFT, padx=2)
            
            end_time_entry = ttk.Entry(end_frame, width=10, font=("微软雅黑", 9))
            end_time_entry.insert(0, end_dt.strftime("%H:%M"))
            end_time_entry.pack(side=tk.LEFT, padx=2)
            
            form_frame.grid_columnconfigure(1, weight=1)
            
            # 按钮区域
            button_frame = ttk.Frame(dialog)
            button_frame.pack(fill=tk.X, padx=20, pady=10)
            
            def save_changes():
                try:
                    title = title_entry.get().strip()
                    description = description_text.get("1.0", tk.END).strip()
                    
                    # 优先级映射
                    priority_reverse_map = {
                        '低': SchedulePriority.LOW,
                        '中': SchedulePriority.MEDIUM,
                        '高': SchedulePriority.HIGH,
                        '关键': SchedulePriority.CRITICAL
                    }
                    priority = priority_reverse_map[priority_var.get()]
                    
                    # 解析时间
                    start_date = start_date_entry.get().strip()
                    start_time = start_time_entry.get().strip()
                    end_date = end_date_entry.get().strip()
                    end_time = end_time_entry.get().strip()
                    
                    start_datetime = datetime.strptime(f"{start_date} {start_time}", "%Y-%m-%d %H:%M")
                    end_datetime = datetime.strptime(f"{end_date} {end_time}", "%Y-%m-%d %H:%M")
                    
                    # 更新日程
                    success = self.schedule_manager.update_schedule(
                        schedule_id,
                        title=title,
                        description=description,
                        priority=priority.value,
                        start_time=start_datetime.isoformat(),
                        end_time=end_datetime.isoformat()
                    )
                    
                    if success:
                        messagebox.showinfo("成功", "日程更新成功")
                        dialog.destroy()
                        self.refresh_schedules()
                    else:
                        messagebox.showerror("错误", "更新日程失败")
                        
                except ValueError as e:
                    messagebox.showerror("错误", f"时间格式不正确:\n{str(e)}")
                except Exception as e:
                    messagebox.showerror("错误", f"更新日程失败:\n{str(e)}")
            
            ttk.Button(button_frame, text="💾 保存", command=save_changes, width=12).pack(side=tk.LEFT, padx=5)
            ttk.Button(button_frame, text="✗ 取消", command=dialog.destroy, width=12).pack(side=tk.LEFT, padx=5)
            
        except Exception as e:
            messagebox.showerror("错误", f"加载日程失败:\n{str(e)}")

    def delete_schedule(self):
        """删除选中的日程"""
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("警告", "请选择要删除的日程")
            return
        
        item = selection[0]
        values = self.tree.item(item)['values']
        schedule_id = self.tree.item(item)['tags'][0]
        
        if not messagebox.askyesno("确认", f"确定要删除日程「{values[0]}」吗？\n\n这是软删除操作，不会永久删除数据。"):
            return
        
        try:
            success = self.schedule_manager.delete_schedule(schedule_id)
            if success:
                messagebox.showinfo("成功", "日程已删除")
                self.refresh_schedules()
            else:
                messagebox.showerror("错误", "删除日程失败")
                
        except Exception as e:
            messagebox.showerror("错误", f"删除日程失败:\n{str(e)}")

    def view_schedule_details(self):
        """查看日程详情"""
        selection = self.tree.selection()
        if not selection:
            return
        
        item = selection[0]
        schedule_id = self.tree.item(item)['tags'][0]
        
        try:
            schedule = self.schedule_manager.get_schedule(schedule_id)
            if not schedule:
                messagebox.showerror("错误", "日程不存在")
                return
            
            # 创建详情对话框
            dialog = tk.Toplevel(self.parent)
            dialog.title(f"日程详情 - {schedule.title}")
            dialog.geometry("500x400")
            dialog.transient(self.parent)
            
            # 详情文本
            text_frame = ttk.Frame(dialog, padding=10)
            text_frame.pack(fill=tk.BOTH, expand=True)
            
            text = scrolledtext.ScrolledText(text_frame, wrap=tk.WORD, font=("微软雅黑", 10))
            text.pack(fill=tk.BOTH, expand=True)
            
            # 格式化详情信息
            type_map = {'recurring': '周期日程', 'appointment': '预约日程', 'temporary': '临时日程'}
            priority_map = {1: '低', 2: '中', 3: '高', 4: '关键'}
            status_map = {'not_required': '不需要', 'pending': '待确认', 'confirmed': '已确认', 'rejected': '已拒绝'}
            
            details = f"""
📅 日程详情

标题: {schedule.title}
类型: {type_map.get(schedule.schedule_type.value, schedule.schedule_type.value)}
优先级: {priority_map.get(schedule.priority.value, schedule.priority.value)}

⏰ 时间安排
开始时间: {datetime.fromisoformat(schedule.start_time).strftime('%Y-%m-%d %H:%M')}
结束时间: {datetime.fromisoformat(schedule.end_time).strftime('%Y-%m-%d %H:%M')}

📝 描述
{schedule.description if schedule.description else '(无)'}

🤝 协作信息
协作状态: {status_map.get(schedule.collaboration_status.value, schedule.collaboration_status.value)}
可查询: {'是' if schedule.is_queryable else '否'}

🔧 系统信息
日程ID: {schedule.schedule_id}
创建时间: {schedule.created_at[:19] if schedule.created_at else '(未知)'}
状态: {'激活' if schedule.is_active else '已删除'}
"""
            
            text.insert("1.0", details)
            text.config(state=tk.DISABLED)
            
            # 关闭按钮
            ttk.Button(dialog, text="关闭", command=dialog.destroy, width=15).pack(pady=10)
            
        except Exception as e:
            messagebox.showerror("错误", f"加载日程详情失败:\n{str(e)}")

    def show_context_menu(self, event):
        """显示右键菜单"""
        item = self.tree.identify_row(event.y)
        if item:
            self.tree.selection_set(item)
            self.context_menu.post(event.x_root, event.y_root)

    def confirm_collaboration(self):
        """确认协作"""
        selection = self.tree.selection()
        if not selection:
            return
        
        item = selection[0]
        schedule_id = self.tree.item(item)['tags'][0]
        
        try:
            success = self.schedule_manager.confirm_collaboration(schedule_id, True)
            if success:
                messagebox.showinfo("成功", "已确认协作日程")
                self.refresh_schedules()
            else:
                messagebox.showerror("错误", "确认失败")
        except Exception as e:
            messagebox.showerror("错误", f"确认失败:\n{str(e)}")

    def reject_collaboration(self):
        """拒绝协作"""
        selection = self.tree.selection()
        if not selection:
            return
        
        item = selection[0]
        schedule_id = self.tree.item(item)['tags'][0]
        
        try:
            success = self.schedule_manager.confirm_collaboration(schedule_id, False)
            if success:
                messagebox.showinfo("成功", "已拒绝协作日程")
                self.refresh_schedules()
            else:
                messagebox.showerror("错误", "拒绝失败")
        except Exception as e:
            messagebox.showerror("错误", f"拒绝失败:\n{str(e)}")

    def start_auto_refresh(self):
        """启动自动刷新"""
        if self.auto_refresh_enabled:
            self.refresh_schedules()
            self.refresh_job = self.parent.after(self.refresh_interval, self.start_auto_refresh)

    def stop_auto_refresh(self):
        """停止自动刷新"""
        if self.refresh_job:
            self.parent.after_cancel(self.refresh_job)
            self.refresh_job = None

    def toggle_auto_refresh(self):
        """切换自动刷新"""
        self.auto_refresh_enabled = not self.auto_refresh_enabled
        if self.auto_refresh_enabled:
            self.auto_refresh_btn.config(text="⏸ 暂停刷新")
            self.start_auto_refresh()
        else:
            self.auto_refresh_btn.config(text="▶ 启动刷新")
            self.stop_auto_refresh()
