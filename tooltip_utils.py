"""
工具提示(ToolTip)工具类
提供鼠标悬停显示完整文本的功能
"""

import tkinter as tk
from typing import Optional


class ToolTip:
    """
    工具提示类
    在鼠标悬浮时显示完整文本
    """
    def __init__(self, widget, text='', delay=500, wraplength=400):
        """
        初始化工具提示
        
        Args:
            widget: 要绑定的控件
            text: 提示文本
            delay: 延迟显示时间（毫秒）
            wraplength: 文本换行长度
        """
        self.widget = widget
        self.text = text
        self.delay = delay
        self.wraplength = wraplength
        self.tooltip_window: Optional[tk.Toplevel] = None
        self.show_timer: Optional[str] = None
        
        # 绑定事件
        self.widget.bind("<Enter>", self.on_enter)
        self.widget.bind("<Leave>", self.on_leave)
        self.widget.bind("<Motion>", self.on_motion)
        
    def on_enter(self, event=None):
        """鼠标进入控件"""
        self.schedule_show()
        
    def on_leave(self, event=None):
        """鼠标离开控件"""
        self.cancel_show()
        self.hide()
        
    def on_motion(self, event=None):
        """鼠标移动"""
        if self.tooltip_window:
            self.hide()
        self.schedule_show()
        
    def schedule_show(self):
        """调度显示提示"""
        self.cancel_show()
        if self.text:
            self.show_timer = self.widget.after(self.delay, self.show)
            
    def cancel_show(self):
        """取消显示"""
        if self.show_timer:
            self.widget.after_cancel(self.show_timer)
            self.show_timer = None
            
    def show(self):
        """显示工具提示"""
        if not self.text or self.tooltip_window:
            return
            
        # 创建顶层窗口
        self.tooltip_window = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        
        # 计算位置
        x = self.widget.winfo_pointerx() + 10
        y = self.widget.winfo_pointery() + 10
        tw.wm_geometry(f"+{x}+{y}")
        
        # 创建标签
        label = tk.Label(
            tw,
            text=self.text,
            justify=tk.LEFT,
            background="#ffffe0",
            foreground="#000000",
            relief=tk.SOLID,
            borderwidth=1,
            wraplength=self.wraplength,
            font=("微软雅黑", 9),
            padx=5,
            pady=3
        )
        label.pack()
        
    def hide(self):
        """隐藏工具提示"""
        if self.tooltip_window:
            self.tooltip_window.destroy()
            self.tooltip_window = None
            
    def update_text(self, text):
        """更新提示文本"""
        self.text = text


def create_treeview_tooltip(tree, get_tooltip_text_func):
    """
    为Treeview创建鼠标悬停提示
    
    Args:
        tree: Treeview控件
        get_tooltip_text_func: 获取提示文本的函数，接收(item_id, values, tags)参数
        
    Returns:
        绑定的事件ID
    """
    tooltip_window = None
    
    def on_motion(event):
        nonlocal tooltip_window
        
        # 隐藏旧的提示
        if tooltip_window:
            tooltip_window.destroy()
            tooltip_window = None
        
        # 获取鼠标所在的行
        item = tree.identify_row(event.y)
        if not item:
            return
        
        # 获取行信息
        values = tree.item(item, 'values')
        tags = tree.item(item, 'tags')
        
        if not values:
            return
        
        # 获取提示文本
        tooltip_text = get_tooltip_text_func(item, values, tags)
        if not tooltip_text:
            return
        
        # 创建提示窗口
        tooltip_window = tw = tk.Toplevel(tree)
        tw.wm_overrideredirect(True)
        
        # 计算位置
        x = event.x_root + 10
        y = event.y_root + 10
        tw.wm_geometry(f"+{x}+{y}")
        
        # 创建标签
        label = tk.Label(
            tw,
            text=tooltip_text,
            justify=tk.LEFT,
            background="#ffffe0",
            foreground="#000000",
            relief=tk.SOLID,
            borderwidth=1,
            wraplength=400,
            font=("微软雅黑", 9),
            padx=5,
            pady=3
        )
        label.pack()
    
    def on_leave(event):
        nonlocal tooltip_window
        if tooltip_window:
            tooltip_window.destroy()
            tooltip_window = None
    
    # 绑定事件
    tree.bind('<Motion>', on_motion)
    tree.bind('<Leave>', on_leave)
    
    return on_motion, on_leave
