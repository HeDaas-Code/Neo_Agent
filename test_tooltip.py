"""
简单测试Tooltip功能
"""

import tkinter as tk
from tkinter import ttk
import sys

# 从gui_enhanced导入ToolTip
sys.path.insert(0, '/home/runner/work/Neo_Agent/Neo_Agent')
from gui_enhanced import ToolTip

def main():
    """测试Tooltip功能"""
    root = tk.Tk()
    root.title("Tooltip测试")
    root.geometry("600x400")
    
    # 创建一些测试控件
    frame = ttk.Frame(root, padding=20)
    frame.pack(fill=tk.BOTH, expand=True)
    
    # 测试标签
    label1 = ttk.Label(frame, text="悬停此处查看长文本", font=("微软雅黑", 12))
    label1.pack(pady=10)
    ToolTip(label1, "这是一个很长的文本，用于测试工具提示功能。当鼠标悬停在控件上时，应该会显示这段完整的文本内容。这个功能对于显示那些在界面上被截断的文本特别有用。", delay=500, wraplength=400)
    
    # 测试按钮
    button1 = ttk.Button(frame, text="带提示的按钮")
    button1.pack(pady=10)
    ToolTip(button1, "这是一个按钮的工具提示\n可以包含多行文本\n也可以显示详细信息", delay=300)
    
    # 测试Entry
    entry_frame = ttk.Frame(frame)
    entry_frame.pack(pady=10, fill=tk.X)
    ttk.Label(entry_frame, text="输入框:").pack(side=tk.LEFT, padx=5)
    entry1 = ttk.Entry(entry_frame)
    entry1.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
    ToolTip(entry1, "在这里输入您的文本\n提示：支持中英文混合输入", delay=500)
    
    # 测试TreeView
    tree_frame = ttk.LabelFrame(frame, text="TreeView测试", padding=10)
    tree_frame.pack(pady=20, fill=tk.BOTH, expand=True)
    
    columns = ('姓名', '年龄', '职业')
    tree = ttk.Treeview(tree_frame, columns=columns, show='headings', height=5)
    
    for col in columns:
        tree.heading(col, text=col)
        tree.column(col, width=150)
    
    # 添加一些数据
    data = [
        ('张三', '28', '软件工程师'),
        ('李四', '32', '产品经理'),
        ('王五', '25', '设计师'),
    ]
    
    for item in data:
        tree.insert('', 'end', values=item)
    
    tree.pack(fill=tk.BOTH, expand=True)
    
    # 为TreeView添加提示（简化版）
    tree_label = ttk.Label(tree_frame, text="将鼠标悬停在TreeView上方标签查看提示")
    tree_label.pack()
    ToolTip(tree_label, "TreeView显示表格数据\n可以排序和筛选\n双击查看详情", delay=500)
    
    # 说明文本
    info_label = ttk.Label(frame, text="将鼠标悬停在各个控件上查看工具提示", foreground="gray")
    info_label.pack(pady=20)
    
    root.mainloop()

if __name__ == '__main__':
    main()
