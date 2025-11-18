"""
增强版Tkinter GUI界面
包含聊天主题时间线可视化功能和Debug日志界面
"""

import os
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, Canvas
from datetime import datetime
import threading
import math
from typing import Dict, Any, List, Optional
from chat_agent import ChatAgent
from debug_logger import get_debug_logger
from emotion_analyzer import format_emotion_summary


class EmotionRadarCanvas(Canvas):
    """
    情感关系雷达图画布
    用于可视化展示情感关系的5个维度
    """

    def __init__(self, parent, **kwargs):
        """
        初始化雷达图画布

        Args:
            parent: 父容器
        """
        super().__init__(parent, **kwargs)
        self.emotion_data = None
        self.dimensions = ["亲密度", "信任度", "愉悦度", "共鸣度", "依赖度"]
        self.colors = {
            'bg': '#f8f9fa',
            'grid': '#dee2e6',
            'axis': '#adb5bd',
            'text': '#495057',
            'fill': '#4ecdc4',
            'line': '#2c9c94',
            'highlight': '#ff6b6b'
        }

        # 绑定事件
        self.bind('<Configure>', self.on_resize)

    def update_emotion(self, emotion_data: Dict[str, Any]):
        """
        更新情感数据并重绘

        Args:
            emotion_data: 情感分析数据
        """
        debug_logger = get_debug_logger()
        debug_logger.log_info('EmotionRadarCanvas', '更新情感数据', {
            'has_data': bool(emotion_data),
            'dimensions': list(emotion_data.keys()) if emotion_data else []
        })

        self.emotion_data = emotion_data
        self.draw_radar()

        debug_logger.log_info('EmotionRadarCanvas', '雷达图重绘完成')

    def draw_radar(self):
        """
        绘制雷达图
        """
        self.delete('all')  # 清空画布

        width = self.winfo_width()
        height = self.winfo_height()

        if width <= 1 or height <= 1:
            return

        # 计算中心点和半径
        center_x = width // 2
        center_y = height // 2
        max_radius = min(width, height) // 2 - 60  # 留出空间显示标签

        if max_radius < 20:
            return

        # 如果没有数据，显示提示
        if not self.emotion_data:
            self.create_text(
                center_x, center_y,
                text="暂无情感分析数据\n对话后点击「分析情感关系」按钮",
                font=('微软雅黑', 10),
                fill='#999999',
                justify=tk.CENTER
            )
            return

        # 绘制背景网格（5层）
        for i in range(5, 0, -1):
            radius = max_radius * (i / 5)
            self._draw_pentagon(center_x, center_y, radius, fill='', outline=self.colors['grid'], width=1)

            # 绘制刻度值
            if i % 1 == 0:
                value = i * 20
                self.create_text(
                    center_x + 5, center_y - radius,
                    text=str(value),
                    font=('Arial', 8),
                    fill=self.colors['axis']
                )

        # 绘制5条轴线
        for i in range(5):
            angle = math.radians(90 - i * 72)  # 从顶部开始，顺时针
            end_x = center_x + max_radius * math.cos(angle)
            end_y = center_y - max_radius * math.sin(angle)
            self.create_line(
                center_x, center_y, end_x, end_y,
                fill=self.colors['axis'], width=1
            )

            # 绘制维度标签
            label_distance = max_radius + 30
            label_x = center_x + label_distance * math.cos(angle)
            label_y = center_y - label_distance * math.sin(angle)

            dimension = self.dimensions[i]
            score = self.emotion_data.get(dimension, 0)

            self.create_text(
                label_x, label_y,
                text=f"{dimension}\n{score}",
                font=('微软雅黑', 9, 'bold'),
                fill=self.colors['text'],
                justify=tk.CENTER
            )

        # 绘制数据多边形
        points = []
        for i in range(5):
            angle = math.radians(90 - i * 72)
            dimension = self.dimensions[i]
            score = self.emotion_data.get(dimension, 0)
            radius = max_radius * (score / 100)
            x = center_x + radius * math.cos(angle)
            y = center_y - radius * math.sin(angle)
            points.extend([x, y])

        # 填充多边形
        self.create_polygon(
            points,
            fill=self.colors['fill'],
            outline=self.colors['line'],
            width=2,
            stipple='gray50'  # 半透明效果
        )

        # 绘制数据点
        for i in range(0, len(points), 2):
            x, y = points[i], points[i + 1]
            self.create_oval(
                x - 4, y - 4, x + 4, y + 4,
                fill=self.colors['line'],
                outline='white',
                width=2
            )

        # 绘制中心信息
        relationship_type = self.emotion_data.get('relationship_type', '未知')
        overall_score = self.emotion_data.get('overall_score', 0)
        emotional_tone = self.emotion_data.get('emotional_tone', '未知')

        self.create_text(
            center_x, center_y - 10,
            text=relationship_type,
            font=('微软雅黑', 12, 'bold'),
            fill=self.colors['highlight']
        )

        self.create_text(
            center_x, center_y + 10,
            text=f"总评: {overall_score}/100",
            font=('微软雅黑', 9),
            fill=self.colors['text']
        )

        self.create_text(
            center_x, center_y + 28,
            text=f"基调: {emotional_tone}",
            font=('微软雅黑', 8),
            fill=self.colors['text']
        )

    def _draw_pentagon(self, center_x, center_y, radius, **kwargs):
        """
        绘制正五边形

        Args:
            center_x: 中心X坐标
            center_y: 中心Y坐标
            radius: 半径
            **kwargs: 其他绘图参数
        """
        points = []
        for i in range(5):
            angle = math.radians(90 - i * 72)
            x = center_x + radius * math.cos(angle)
            y = center_y - radius * math.sin(angle)
            points.extend([x, y])

        self.create_polygon(points, **kwargs)

    def on_resize(self, event):
        """
        窗口大小改变事件处理

        Args:
            event: 事件对象
        """
        self.draw_radar()


class TopicTimelineCanvas(Canvas):
    """
    主题时间线画布
    用于可视化展示聊天主题的变化
    """

    def __init__(self, parent, **kwargs):
        """
        初始化时间线画布

        Args:
            parent: 父容器
        """
        super().__init__(parent, **kwargs)
        self.topics = []
        self.colors = [
            '#FF6B6B', '#4ECDC4', '#45B7D1', '#FFA07A',
            '#98D8C8', '#F7DC6F', '#BB8FCE', '#85C1E2',
            '#F8B739', '#52B788', '#FF8FA3', '#6A9BD1'
        ]

        # 绑定鼠标事件
        self.bind('<Configure>', self.on_resize)
        self.bind('<Motion>', self.on_mouse_move)

        # 工具提示
        self.tooltip = None

    def update_topics(self, summaries):
        """
        更新主题数据并重绘

        Args:
            summaries: 长期记忆概括列表
        """
        self.topics = summaries
        self.draw_timeline()

    def draw_timeline(self):
        """
        绘制时间线
        """
        self.delete('all')  # 清空画布

        if not self.topics:
            # 如果没有数据，显示提示
            width = self.winfo_width()
            height = self.winfo_height()
            self.create_text(
                width // 2, height // 2,
                text="暂无主题数据\n对话超过20轮后将自动生成主题概括",
                font=('微软雅黑', 10),
                fill='#999999',
                justify=tk.CENTER
            )
            return

        width = self.winfo_width()
        height = self.winfo_height()

        if width <= 1 or height <= 1:
            return

        # 计算布局参数
        padding = 40
        timeline_y = height // 2
        available_width = width - 2 * padding

        # 如果只有一个主题
        if len(self.topics) == 1:
            x = width // 2
            self._draw_topic_node(x, timeline_y, self.topics[0], 0)
            return

        # 多个主题：均匀分布
        step = available_width / (len(self.topics) - 1) if len(self.topics) > 1 else 0

        # 绘制时间线
        self.create_line(
            padding, timeline_y,
            width - padding, timeline_y,
            fill='#CCCCCC', width=2, tags='timeline'
        )

        # 绘制各个主题节点
        for i, topic in enumerate(self.topics):
            x = padding + i * step
            self._draw_topic_node(x, timeline_y, topic, i)

            # 绘制连接线（除了最后一个）
            if i < len(self.topics) - 1:
                next_x = padding + (i + 1) * step
                self.create_line(
                    x, timeline_y,
                    next_x, timeline_y,
                    fill=self.colors[i % len(self.colors)],
                    width=3,
                    arrow=tk.LAST,
                    arrowshape=(10, 12, 5),
                    tags=f'line_{i}'
                )

    def _draw_topic_node(self, x, y, topic, index):
        """
        绘制单个主题节点

        Args:
            x: X坐标
            y: Y坐标
            topic: 主题数据
            index: 索引
        """
        color = self.colors[index % len(self.colors)]
        radius = 12

        # 绘制节点圆圈
        node_id = self.create_oval(
            x - radius, y - radius,
            x + radius, y + radius,
            fill=color,
            outline='white',
            width=3,
            tags=f'node_{index}'
        )

        # 绘制节点编号
        self.create_text(
            x, y,
            text=str(index + 1),
            font=('Arial', 10, 'bold'),
            fill='white',
            tags=f'node_text_{index}'
        )

        # 绘制日期标签
        date_str = topic.get('created_at', '')[:10] if topic.get('created_at') else ''
        self.create_text(
            x, y - 30,
            text=date_str,
            font=('微软雅黑', 8),
            fill='#666666',
            tags=f'date_{index}'
        )

        # 绘制主题摘要（简短版）
        summary = topic.get('summary', '')
        short_summary = summary[:15] + '...' if len(summary) > 15 else summary
        self.create_text(
            x, y + 30,
            text=short_summary,
            font=('微软雅黑', 8),
            fill='#333333',
            width=100,
            tags=f'summary_{index}'
        )

        # 绑定点击事件
        self.tag_bind(f'node_{index}', '<Button-1>',
                     lambda e, t=topic, i=index: self.on_node_click(t, i))

        # 存储完整信息用于工具提示
        self.itemconfig(node_id, tags=(f'node_{index}', f'tooltip_{index}'))

    def on_node_click(self, topic, index):
        """
        节点点击事件处理

        Args:
            topic: 主题数据
            index: 索引
        """
        # 显示详细信息
        info = f"""主题 {index + 1} 详细信息
        
时间范围: {topic.get('created_at', '')[:19]} 至 {topic.get('ended_at', '')[:19]}
对话轮数: {topic.get('rounds', 0)} 轮
消息数量: {topic.get('message_count', 0)} 条
UUID: {topic.get('uuid', '')}

主题概括:
{topic.get('summary', '')}"""

        messagebox.showinfo(f"主题 {index + 1}", info)

    def on_mouse_move(self, event):
        """
        鼠标移动事件处理（用于显示工具提示）

        Args:
            event: 事件对象
        """
        # 查找鼠标下的节点
        items = self.find_overlapping(event.x - 2, event.y - 2, event.x + 2, event.y + 2)

        for item in items:
            tags = self.gettags(item)
            for tag in tags:
                if tag.startswith('node_') and not tag.endswith('text'):
                    # 改变鼠标样式
                    self.config(cursor='hand2')
                    return

        # 恢复默认鼠标样式
        self.config(cursor='')

    def on_resize(self, event):
        """
        窗口大小改变事件处理

        Args:
            event: 事件对象
        """
        self.draw_timeline()


class EnhancedChatDebugGUI:
    """
    增强版聊天调试GUI
    包含主题时��线可视化
    """

    def __init__(self, root):
        """
        初始化GUI界面

        Args:
            root: Tkinter根窗口
        """
        self.root = root
        self.root.title("智能对话代理 - 增强调试界面")
        self.root.geometry("1400x900")
        self.root.minsize(1000, 700)  # 设置最小窗口尺寸，防止布局混乱

        # 初始化聊天代理
        self.agent = None
        self.is_processing = False

        # 创建UI组件
        self.create_widgets()

        # 初始化代理
        self.initialize_agent()

        # 绑定快捷键
        self.root.bind('<Return>', lambda e: self.send_message() if not e.state & 0x1 else None)
        self.root.bind('<Control-Return>', lambda e: self.input_text.insert(tk.INSERT, '\n'))

    def create_widgets(self):
        """
        创建所有UI组件
        """
        # 主容器
        main_container = ttk.Frame(self.root)
        main_container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # 上部：可视化区域（时间线和雷达图的标签页，固定高度）
        visualization_frame = ttk.LabelFrame(main_container, text="📊 数据可视化", padding=5, height=280)
        visualization_frame.pack(fill=tk.X, padx=5, pady=5, side=tk.TOP)
        visualization_frame.pack_propagate(False)  # 固定高度

        # 创建标签页控件
        viz_notebook = ttk.Notebook(visualization_frame)
        viz_notebook.pack(fill=tk.BOTH, expand=True)

        # 标签页1：对话主题时间线
        timeline_tab = ttk.Frame(viz_notebook)
        viz_notebook.add(timeline_tab, text="📈 主题时间线")

        self.timeline_canvas = TopicTimelineCanvas(
            timeline_tab,
            bg='#f8f9fa',
            highlightthickness=0
        )
        self.timeline_canvas.pack(fill=tk.BOTH, expand=True)

        # 标签页2：情感关系雷达图
        emotion_tab = ttk.Frame(viz_notebook)
        viz_notebook.add(emotion_tab, text="💖 情感关系")

        # 创建一个水平容器用于雷达图和详细信息
        emotion_container = ttk.Frame(emotion_tab)
        emotion_container.pack(fill=tk.BOTH, expand=True)

        # 左侧：雷达图
        radar_frame = ttk.Frame(emotion_container)
        radar_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.emotion_canvas = EmotionRadarCanvas(
            radar_frame,
            bg='#f8f9fa',
            highlightthickness=0
        )
        self.emotion_canvas.pack(fill=tk.BOTH, expand=True)

        # 右侧：详细信息和控制按钮
        emotion_info_frame = ttk.Frame(emotion_container, width=250)
        emotion_info_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=(10, 0))
        emotion_info_frame.pack_propagate(False)

        # 分析按钮
        ttk.Button(
            emotion_info_frame,
            text="🔍 分析情感关系",
            command=self.analyze_emotion,
            width=20
        ).pack(pady=5)

        # 情感分析详细信息
        self.emotion_info_text = scrolledtext.ScrolledText(
            emotion_info_frame,
            wrap=tk.WORD,
            font=("微软雅黑", 9),
            bg="#f9f9f9",
            relief=tk.FLAT,
            height=12
        )
        self.emotion_info_text.pack(fill=tk.BOTH, expand=True, pady=5)
        self.emotion_info_text.config(state=tk.DISABLED)

        # 主分割窗格
        main_paned = ttk.PanedWindow(main_container, orient=tk.HORIZONTAL)
        main_paned.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # 左侧面板 - 聊天区域
        left_frame = ttk.Frame(main_paned)
        main_paned.add(left_frame, weight=3)

        # 右侧面板 - 调试信息
        right_frame = ttk.Frame(main_paned)
        main_paned.add(right_frame, weight=1)

        # ========== 左侧聊天区域 ==========
        self.create_chat_area(left_frame)

        # ========== 右侧调试区域 ==========
        self.create_debug_area(right_frame)

    def create_chat_area(self, parent):
        """
        创建聊天区域

        Args:
            parent: 父容器
        """
        # 顶部标题栏（固定高度）
        title_frame = ttk.Frame(parent, height=40)
        title_frame.pack(fill=tk.X, padx=5, pady=5, side=tk.TOP)
        title_frame.pack_propagate(False)  # 防止子组件改变frame大小

        title_label = ttk.Label(
            title_frame,
            text="💬 智能对话系统",
            font=("微软雅黑", 16, "bold")
        )
        title_label.pack(side=tk.LEFT)

        self.status_label = ttk.Label(
            title_frame,
            text="● 就绪",
            foreground="green",
            font=("微软雅黑", 10)
        )
        self.status_label.pack(side=tk.RIGHT, padx=10)

        # 角色信息栏（固定高度）
        self.character_frame = ttk.LabelFrame(parent, text="📋 当前角色", padding=5, height=50)
        self.character_frame.pack(fill=tk.X, padx=5, pady=3, side=tk.TOP)
        self.character_frame.pack_propagate(False)

        self.character_label = ttk.Label(
            self.character_frame,
            text="加载中...",
            font=("微软雅黑", 9)
        )
        self.character_label.pack()

        # 记忆状态栏（固定高度）
        memory_status_frame = ttk.Frame(parent, height=30)
        memory_status_frame.pack(fill=tk.X, padx=5, pady=2, side=tk.TOP)
        memory_status_frame.pack_propagate(False)

        self.memory_status_label = ttk.Label(
            memory_status_frame,
            text="短期记忆: 0轮 | 长期记忆: 0个主题",
            font=("微软雅黑", 9),
            foreground="#0066cc"
        )
        self.memory_status_label.pack(side=tk.LEFT)

        ttk.Button(
            memory_status_frame,
            text="🔄",
            width=3,
            command=self.refresh_all
        ).pack(side=tk.RIGHT, padx=2)

        # 输入区域（固定在底部，固定高度）
        input_frame = ttk.LabelFrame(parent, text="✏️ 输入消息", padding=5, height=140)
        input_frame.pack(fill=tk.X, padx=5, pady=5, side=tk.BOTTOM)
        input_frame.pack_propagate(False)  # 防止被压缩

        # 输入文本框
        self.input_text = tk.Text(
            input_frame,
            height=3,
            wrap=tk.WORD,
            font=("微软雅黑", 10),
            relief=tk.SOLID,
            borderwidth=1
        )
        self.input_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=(5, 2))

        # 按钮区域
        button_frame = ttk.Frame(input_frame)
        button_frame.pack(fill=tk.X, padx=5, pady=(2, 5))

        self.send_button = ttk.Button(
            button_frame,
            text="发送 (Enter)",
            command=self.send_message
        )
        self.send_button.pack(side=tk.LEFT, padx=2)

        ttk.Button(
            button_frame,
            text="清空输入",
            command=self.clear_input
        ).pack(side=tk.LEFT, padx=2)

        ttk.Button(
            button_frame,
            text="清空对话",
            command=self.clear_chat_display
        ).pack(side=tk.LEFT, padx=2)

        # 聊天显示区域（填充剩余空间）
        chat_frame = ttk.Frame(parent)
        chat_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5, side=tk.TOP)

        self.chat_display = scrolledtext.ScrolledText(
            chat_frame,
            wrap=tk.WORD,
            font=("微软雅黑", 11),
            bg="#f5f5f5",
            relief=tk.FLAT,
            padx=10,
            pady=10
        )
        self.chat_display.pack(fill=tk.BOTH, expand=True)
        self.chat_display.config(state=tk.DISABLED)

        # 配置文本标签样式
        self.chat_display.tag_config("user", foreground="#0066cc", font=("微软雅黑", 11, "bold"))
        self.chat_display.tag_config("assistant", foreground="#ff6600", font=("微软雅黑", 11, "bold"))
        self.chat_display.tag_config("system", foreground="#666666", font=("微软雅黑", 9, "italic"))
        self.chat_display.tag_config("timestamp", foreground="#999999", font=("微软雅黑", 8))
        self.chat_display.tag_config("archive", foreground="#9933cc", font=("微软雅黑", 9, "italic"))

    def create_debug_area(self, parent):
        """
        创建调试区域

        Args:
            parent: 父容器
        """
        # 调试选项卡
        notebook = ttk.Notebook(parent)
        notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # 选项卡1: 系统信息
        info_tab = ttk.Frame(notebook)
        notebook.add(info_tab, text="系统信息")

        self.info_display = scrolledtext.ScrolledText(
            info_tab,
            wrap=tk.WORD,
            font=("Consolas", 9),
            bg="#f9f9f9",
            relief=tk.FLAT
        )
        self.info_display.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.info_display.config(state=tk.DISABLED)

        # 选项卡2: 短期记忆
        short_term_tab = ttk.Frame(notebook)
        notebook.add(short_term_tab, text="短期记忆")

        self.short_term_display = scrolledtext.ScrolledText(
            short_term_tab,
            wrap=tk.WORD,
            font=("微软雅黑", 9),
            bg="#f9f9f9",
            relief=tk.FLAT
        )
        self.short_term_display.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.short_term_display.config(state=tk.DISABLED)

        # 选项卡3: 长期记忆
        long_term_tab = ttk.Frame(notebook)
        notebook.add(long_term_tab, text="长期记忆")

        self.long_term_display = scrolledtext.ScrolledText(
            long_term_tab,
            wrap=tk.WORD,
            font=("微软雅黑", 9),
            bg="#f9f9f9",
            relief=tk.FLAT
        )
        self.long_term_display.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.long_term_display.config(state=tk.DISABLED)

        # 选项卡4: 理解阶段
        understanding_tab = ttk.Frame(notebook)
        notebook.add(understanding_tab, text="🧠 理解阶段")

        self.understanding_display = scrolledtext.ScrolledText(
            understanding_tab,
            wrap=tk.WORD,
            font=("微软雅黑", 9),
            bg="#f9f9f9",
            relief=tk.FLAT
        )
        self.understanding_display.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.understanding_display.config(state=tk.DISABLED)

        # 选项卡5: 知识库
        knowledge_tab = ttk.Frame(notebook)
        notebook.add(knowledge_tab, text="📚 知识库")

        # 知识库顶部工具栏
        kb_toolbar = ttk.Frame(knowledge_tab)
        kb_toolbar.pack(fill=tk.X, padx=5, pady=5)

        # 第一行：基础知识信息
        kb_info_frame = ttk.Frame(kb_toolbar)
        kb_info_frame.pack(fill=tk.X, pady=(0, 5))

        self.base_kb_info_label = ttk.Label(
            kb_info_frame,
            text="🔒 基础知识: 加载中...",
            font=("微软雅黑", 9, "bold"),
            foreground="#d35400"
        )
        self.base_kb_info_label.pack(side=tk.LEFT, padx=2)

        ttk.Button(
            kb_info_frame,
            text="查看基础知识",
            width=12,
            command=self.show_base_knowledge
        ).pack(side=tk.LEFT, padx=5)

        ttk.Button(
            kb_info_frame,
            text="添加基础知识",
            width=12,
            command=self.add_base_knowledge
        ).pack(side=tk.LEFT, padx=2)

        # 第二行：搜索和筛选
        kb_search_frame = ttk.Frame(kb_toolbar)
        kb_search_frame.pack(fill=tk.X)

        ttk.Label(kb_search_frame, text="搜索:", font=("微软雅黑", 9)).pack(side=tk.LEFT, padx=2)

        self.kb_search_var = tk.StringVar()
        self.kb_search_entry = ttk.Entry(kb_search_frame, textvariable=self.kb_search_var, width=20)
        self.kb_search_entry.pack(side=tk.LEFT, padx=2)

        ttk.Button(
            kb_search_frame,
            text="🔍",
            width=3,
            command=self.search_knowledge
        ).pack(side=tk.LEFT, padx=2)

        ttk.Button(
            kb_search_frame,
            text="刷新",
            width=6,
            command=self.update_knowledge_display
        ).pack(side=tk.LEFT, padx=2)

        # 知识类型筛选
        ttk.Label(kb_search_frame, text="类型:", font=("微软雅黑", 9)).pack(side=tk.LEFT, padx=(10, 2))
        self.kb_type_var = tk.StringVar(value="全部")
        self.kb_type_combo = ttk.Combobox(
            kb_search_frame,
            textvariable=self.kb_type_var,
            width=12,
            state="readonly"
        )
        self.kb_type_combo['values'] = ['全部', '基础知识', '个人信息', '偏好', '事实', '经历', '观点', '其他']
        self.kb_type_combo.pack(side=tk.LEFT, padx=2)
        self.kb_type_combo.bind('<<ComboboxSelected>>', lambda e: self.filter_knowledge_by_type())

        # 知识显示区域
        self.knowledge_display = scrolledtext.ScrolledText(
            knowledge_tab,
            wrap=tk.WORD,
            font=("微软雅黑", 9),
            bg="#f9f9f9",
            relief=tk.FLAT
        )
        self.knowledge_display.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.knowledge_display.config(state=tk.DISABLED)

        # 选项卡6: 环境管理（智能体视觉）
        environment_tab = ttk.Frame(notebook)
        notebook.add(environment_tab, text="👁️ 环境管理")

        # 环境管理工具栏
        env_toolbar = ttk.Frame(environment_tab)
        env_toolbar.pack(fill=tk.X, padx=5, pady=5)

        ttk.Label(
            env_toolbar,
            text="智能体视觉环境配置",
            font=("微软雅黑", 10, "bold")
        ).pack(side=tk.LEFT, padx=5)

        ttk.Button(
            env_toolbar,
            text="🔄 刷新",
            command=self.refresh_environment_display,
            width=12
        ).pack(side=tk.LEFT, padx=2)

        ttk.Button(
            env_toolbar,
            text="➕ 新建环境",
            command=self.create_new_environment,
            width=12
        ).pack(side=tk.LEFT, padx=2)

        ttk.Button(
            env_toolbar,
            text="➕ 添加物体",
            command=self.add_new_object,
            width=12
        ).pack(side=tk.LEFT, padx=2)

        ttk.Button(
            env_toolbar,
            text="📋 使用记录",
            command=self.show_vision_logs,
            width=12
        ).pack(side=tk.LEFT, padx=2)

        ttk.Button(
            env_toolbar,
            text="🏠 创建默认环境",
            command=self.create_default_environment,
            width=15
        ).pack(side=tk.LEFT, padx=2)

        # 环境显示区域
        self.environment_display = scrolledtext.ScrolledText(
            environment_tab,
            wrap=tk.WORD,
            font=("微软雅黑", 9),
            bg="#f9f9f9",
            relief=tk.FLAT
        )
        self.environment_display.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.environment_display.config(state=tk.DISABLED)

        # 选项卡7: Debug日志（仅在debug模式下显示）
        debug_mode = os.getenv('DEBUG_MODE', 'False').lower() == 'true'
        if debug_mode:
            debug_tab = ttk.Frame(notebook)
            notebook.add(debug_tab, text="🔧 Debug日志")

            # Debug工具栏
            debug_toolbar = ttk.Frame(debug_tab)
            debug_toolbar.pack(fill=tk.X, padx=5, pady=5)

            ttk.Label(
                debug_toolbar,
                text="Debug模式已启用",
                font=("微软雅黑", 9, "bold"),
                foreground="#e74c3c"
            ).pack(side=tk.LEFT, padx=5)

            ttk.Button(
                debug_toolbar,
                text="刷新日志",
                width=10,
                command=self.update_debug_display
            ).pack(side=tk.LEFT, padx=2)

            ttk.Button(
                debug_toolbar,
                text="清空日志",
                width=10,
                command=self.clear_debug_logs
            ).pack(side=tk.LEFT, padx=2)

            # 日志类型筛选
            ttk.Label(debug_toolbar, text="类型:", font=("微软雅黑", 9)).pack(side=tk.LEFT, padx=(10, 2))
            self.debug_type_var = tk.StringVar(value="全部")
            debug_type_combo = ttk.Combobox(
                debug_toolbar,
                textvariable=self.debug_type_var,
                width=12,
                state="readonly"
            )
            debug_type_combo['values'] = ['全部', 'module', 'prompt', 'request', 'response', 'error', 'info']
            debug_type_combo.pack(side=tk.LEFT, padx=2)
            debug_type_combo.bind('<<ComboboxSelected>>', lambda e: self.update_debug_display())

            # 自动刷新开关
            self.debug_auto_refresh = tk.BooleanVar(value=True)
            ttk.Checkbutton(
                debug_toolbar,
                text="自动刷新",
                variable=self.debug_auto_refresh
            ).pack(side=tk.LEFT, padx=10)

            # 统计信息
            self.debug_stats_label = ttk.Label(
                debug_toolbar,
                text="日志: 0 条",
                font=("微软雅黑", 8)
            )
            self.debug_stats_label.pack(side=tk.RIGHT, padx=5)

            # Debug日志显示区域
            self.debug_display = scrolledtext.ScrolledText(
                debug_tab,
                wrap=tk.WORD,
                font=("Consolas", 9),
                bg="#1e1e1e",
                fg="#d4d4d4",
                relief=tk.FLAT,
                insertbackground="white"
            )
            self.debug_display.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
            self.debug_display.config(state=tk.DISABLED)

            # 配置颜色标签
            self.debug_display.tag_config('module', foreground='#4ec9b0')
            self.debug_display.tag_config('prompt', foreground='#ce9178')
            self.debug_display.tag_config('request', foreground='#569cd6')
            self.debug_display.tag_config('response', foreground='#4fc1ff')
            self.debug_display.tag_config('error', foreground='#f48771')
            self.debug_display.tag_config('info', foreground='#b5cea8')
            self.debug_display.tag_config('timestamp', foreground='#858585')

            # 获取debug logger并添加监听器
            self.debug_logger = get_debug_logger()
            self.debug_logger.add_listener(self.on_debug_log_added)

        # 选项卡7: 数据库管理
        db_tab = ttk.Frame(notebook)
        notebook.add(db_tab, text="💾 数据库管理")

        # 导入并创建数据库管理GUI
        try:
            from database_gui import DatabaseManagerGUI
            # 获取数据库管理器实例
            if hasattr(self, 'agent') and self.agent and hasattr(self.agent, 'db'):
                db_manager = self.agent.db
            else:
                from database_manager import DatabaseManager
                db_manager = DatabaseManager()

            self.db_gui = DatabaseManagerGUI(db_tab, db_manager)
        except Exception as e:
            ttk.Label(db_tab, text=f"数据库管理界面加载失败:\n{str(e)}",
                     font=("微软雅黑", 10), foreground="red").pack(pady=50)

        # 选项卡8: 控制面板
        control_tab = ttk.Frame(notebook)
        notebook.add(control_tab, text="⚙️ 控制面板")

        self.create_control_panel(control_tab)

    def create_control_panel(self, parent):
        """
        创建控制面板

        Args:
            parent: 父容器
        """
        control_container = ttk.Frame(parent, padding=10)
        control_container.pack(fill=tk.BOTH, expand=True)

        ttk.Label(control_container, text="记忆管理", font=("微软雅黑", 10, "bold")).pack(anchor=tk.W, pady=5)

        ttk.Button(
            control_container,
            text="🔄 刷新所有信息",
            command=self.refresh_all,
            width=25
        ).pack(fill=tk.X, pady=2)

        ttk.Button(
            control_container,
            text="📈 更新主题时间线",
            command=self.update_timeline,
            width=25
        ).pack(fill=tk.X, pady=2)

        ttk.Button(
            control_container,
            text="🗑️ 清空所有记忆",
            command=self.clear_all_memory,
            width=25
        ).pack(fill=tk.X, pady=2)

        ttk.Separator(control_container, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=10)

        ttk.Label(control_container, text="系统设置", font=("微软雅黑", 10, "bold")).pack(anchor=tk.W, pady=5)

        ttk.Button(
            control_container,
            text="♻️ 重新加载代理",
            command=self.reload_agent,
            width=25
        ).pack(fill=tk.X, pady=2)

        ttk.Button(
            control_container,
            text="ℹ️ 关于",
            command=self.show_about,
            width=25
        ).pack(fill=tk.X, pady=2)

    def initialize_agent(self):
        """
        初始化聊天代理
        """
        try:
            self.update_status("初始化中...", "orange")
            self.agent = ChatAgent()

            # 记录初始知识库数量
            stats = self.agent.get_memory_stats()
            self._last_kb_count = stats['knowledge_base']['total_knowledge']

            # 记录初始情感分析数量
            emotion_history = self.agent.get_emotion_history()
            self._last_emotion_count = len(emotion_history)

            # 如果已有情感数据，加载并显示最新的
            if emotion_history:
                latest_emotion = self.agent.get_latest_emotion()
                if latest_emotion:
                    self.update_emotion_display(latest_emotion)
                    print(f"✓ 加载已有情感数据: {len(emotion_history)} 条记录")
                    print(f"  最新关系类型: {latest_emotion.get('relationship_type', '未知')}")
                    print(f"  情感基调: {latest_emotion.get('emotional_tone', '未知')}")
                    print(f"  总体评分: {latest_emotion.get('overall_score', 0)}/100")

            # 更新所有信息显示
            self.update_character_info()
            self.update_system_info()
            self.refresh_all()

            # 显示欢迎消息
            self.add_system_message("系统初始化完成！开始对话吧～")

            # 如果有情感数据，显示提示
            if emotion_history:
                self.add_system_message(
                    f"💖 已加载情感分析数据 ({len(emotion_history)} 条) | "
                    f"当前关系：{latest_emotion.get('relationship_type', '未知')}"
                )

            self.update_status("就绪", "green")

        except Exception as e:
            self.update_status("初始化失败", "red")
            messagebox.showerror("初始化错误", f"初始化聊天代理时出错：\n{str(e)}")

    def update_character_info(self):
        """
        更新角色信息显示
        """
        if self.agent:
            char_info = self.agent.get_character_info()
            info_text = f"姓名: {char_info['name']} | 性别: {char_info['gender']} | 身份: {char_info['role']} | "
            info_text += f"年龄: {char_info['age']}岁 | 身高: {char_info['height']} | 体重: {char_info['weight']}\n"
            info_text += f"性格: {char_info['personality']}"

            self.character_label.config(text=info_text)

    def update_system_info(self):
        """
        更新系统信息显示
        """
        if not self.agent:
            return

        info = []
        info.append("=" * 40)
        info.append("系统信息")
        info.append("=" * 40)
        info.append("")

        char_info = self.agent.get_character_info()
        info.append("【角色信息】")
        for key, value in char_info.items():
            info.append(f"  {key}: {value}")

        info.append("")
        info.append("【系统配置】")
        # 显示数据库路径而不是JSON文件路径
        info.append(f"  数据库文件: {self.agent.memory_manager.db.db_path}")
        info.append(f"  最大短期轮数: {self.agent.memory_manager.max_short_term_rounds}")
        info.append(f"  知识提取间隔: {self.agent.memory_manager.knowledge_extraction_interval} 轮")
        info.append(f"  API模型: {self.agent.llm.model_name}")
        info.append(f"  温度参数: {self.agent.llm.temperature}")

        self.update_text_widget(self.info_display, "\n".join(info))

    def refresh_all(self):
        """
        刷新所有信息
        """
        if not self.agent:
            return

        self.update_memory_status()
        self.update_short_term_display()
        self.update_long_term_display()
        self.update_understanding_display()  # 新增：更新理解阶段显示
        self.update_knowledge_display()
        self.refresh_environment_display()  # 新增：更新环境显示
        self.update_timeline()

    def analyze_emotion(self):
        """
        分析情感关系
        """
        if not self.agent:
            messagebox.showwarning("警告", "聊天代理未初始化")
            return

        # 检查对话数量
        history = self.agent.get_conversation_history()
        if len(history) < 2:
            messagebox.showinfo("提示", "对话轮数太少，至少需要1轮对话（2条消息）才能进行情感分析")
            return

        debug_logger = get_debug_logger()
        debug_logger.log_module('GUI', '用户触发情感分析', {
            'history_count': len(history)
        })

        # 在线程中执行分析，避免UI卡顿
        def analyze_thread():
            try:
                self.update_status("分析情感关系中...", "orange")
                debug_logger.log_info('GUI', '开始情感分析线程')

                # 调用情感分析
                emotion_data = self.agent.analyze_emotion()

                debug_logger.log_info('GUI', '情感分析线程完成', {
                    'overall_score': emotion_data.get('overall_score', 0),
                    'relationship_type': emotion_data.get('relationship_type', '未知')
                })

                # 更新显示
                self.root.after(0, lambda: self.update_emotion_display(emotion_data))
                self.root.after(0, lambda: self.update_status("情感分析完成", "green"))
                self.root.after(0, lambda: messagebox.showinfo("完成", "情感关系分析已完成！"))

            except Exception as e:
                debug_logger.log_error('GUI', f'情感分析线程出错: {str(e)}', e)
                self.root.after(0, lambda: self.update_status("分析失败", "red"))
                self.root.after(0, lambda: messagebox.showerror("错误", f"情感分析时出错：\n{str(e)}"))

        thread = threading.Thread(target=analyze_thread, daemon=True)
        thread.start()

    def update_emotion_display(self, emotion_data: Dict[str, Any]):
        """
        更新情感关系显示

        Args:
            emotion_data: 情感分析数据
        """
        if not emotion_data:
            return

        debug_logger = get_debug_logger()
        debug_logger.log_info('GUI', '更新情感显示', {
            'has_data': bool(emotion_data)
        })

        # 更新雷达图
        self.emotion_canvas.update_emotion(emotion_data)

        # 更新详细信息文本
        info_text = format_emotion_summary(emotion_data)
        self.update_text_widget(self.emotion_info_text, info_text)

        debug_logger.log_info('GUI', '情感显示更新完成')

    def update_memory_status(self):
        """
        更新记忆状态显示
        """
        if not self.agent:
            return

        stats = self.agent.get_memory_stats()
        base_kb_count = stats['knowledge_base'].get('base_knowledge_facts', 0)
        status_text = f"短期: {stats['short_term']['rounds']}轮 | 长期: {stats['long_term']['total_summaries']}主题 | 知识库: {stats['knowledge_base']['total_knowledge']}条"
        if base_kb_count > 0:
            status_text += f" | 基础: {base_kb_count}条"
        self.memory_status_label.config(text=status_text)

    def update_short_term_display(self):
        """
        更新短期记忆显示
        """
        if not self.agent:
            return

        history = self.agent.get_conversation_history()

        if not history:
            self.update_text_widget(self.short_term_display, "暂无短期记忆")
            return

        text = []
        text.append("=" * 40)
        text.append(f"短期记忆 (共 {len(history)} 条消息)")
        text.append("=" * 40)
        text.append("")

        for i, msg in enumerate(history, 1):
            role = "用户" if msg['role'] == 'user' else self.agent.character.name
            timestamp = msg.get('timestamp', 'Unknown')[:19]
            text.append(f"[{i}] {timestamp}")
            text.append(f"{role}: {msg['content']}")
            text.append("-" * 40)

        self.update_text_widget(self.short_term_display, "\n".join(text))

    def update_long_term_display(self):
        """
        更新长期记忆显示
        """
        if not self.agent:
            return

        summaries = self.agent.get_long_term_summaries()

        if not summaries:
            self.update_text_widget(self.long_term_display, "暂无长期记忆\n对话超过20轮后将自动生成")
            return

        text = []
        text.append("=" * 40)
        text.append(f"长期记忆概括 (共 {len(summaries)} 个主题)")
        text.append("=" * 40)
        text.append("")

        for i, summary in enumerate(summaries, 1):
            text.append(f"【主题 {i}】")
            text.append(f"UUID: {summary.get('uuid', '')}")
            text.append(f"时间: {summary.get('created_at', '')[:19]} ~ {summary.get('ended_at', '')[:19]}")
            text.append(f"对话轮数: {summary.get('rounds', 0)} 轮")
            text.append(f"消息数量: {summary.get('message_count', 0)} 条")
            text.append(f"主题概括: {summary.get('summary', '')}")
            text.append("=" * 40)
            text.append("")

        self.update_text_widget(self.long_term_display, "\n".join(text))

    def update_understanding_display(self, understanding_result: Dict[str, Any] = None):
        """
        更新理解阶段显示

        Args:
            understanding_result: 理解阶段结果字典
        """
        if not self.agent:
            return

        # 如果没有传入结果，尝试获取最后一次的结果
        if understanding_result is None:
            understanding_result = self.agent.get_last_understanding()

        if not understanding_result:
            self.update_text_widget(
                self.understanding_display,
                "理解阶段\n\n等待用户输入...\n\n说明：\n当你发送消息后，系统会：\n1. 提取消息中的相关主体\n2. 从知识库检索相关知识\n3. 按优先级排序（定义>相关信息）\n4. 将知识提供给AI参考"
            )
            return

        text = []
        text.append("=" * 50)
        text.append("🧠 理解阶段分析")
        text.append("=" * 50)
        text.append("")

        text.append(f"【用户输入】\n{understanding_result.get('query', '')}")
        text.append("")
        text.append("-" * 50)

        entities_found = understanding_result.get('entities_found', [])
        if entities_found:
            text.append(f"\n【识别到的主体】（共 {len(entities_found)} 个）")
            for i, entity in enumerate(entities_found, 1):
                text.append(f"  {i}. {entity}")
        else:
            text.append("\n【识别到的主体】")
            text.append("  未识别到相关主体")

        text.append("")
        text.append("-" * 50)

        knowledge_items = understanding_result.get('knowledge_items', [])
        if knowledge_items:
            text.append(f"\n【检索到的知识】（共 {len(knowledge_items)} 条，按优先级排序）")
            text.append("")

            # 按主体分组
            by_entity = {}
            for item in knowledge_items:
                entity_name = item['entity_name']
                if entity_name not in by_entity:
                    by_entity[entity_name] = {'definitions': [], 'info': []}

                if item['type'] == '定义':
                    by_entity[entity_name]['definitions'].append(item)
                else:
                    by_entity[entity_name]['info'].append(item)

            for entity_name, items in by_entity.items():
                text.append(f"► 主体: {entity_name}")
                text.append("")

                # 显示定义
                if items['definitions']:
                    for definition in items['definitions']:
                        confidence = definition['confidence']
                        confidence_icon = "⭐⭐⭐" if confidence >= 0.9 else "⭐⭐"
                        priority_label = "【最高优先级】"
                        text.append(f"  {confidence_icon} {priority_label} 定义")
                        text.append(f"     置信度: {confidence:.2f}")
                        text.append(f"     内容: {definition['content']}")
                        text.append(f"     时间: {definition.get('created_at', '')[:19]}")
                        text.append("")

                # 显示相关信息
                if items['info']:
                    text.append("  其他相关信息:")
                    for info in items['info']:
                        confidence = info['confidence']
                        confidence_icon = "⭐⭐" if confidence >= 0.8 else "⭐"
                        priority_label = "【次优先级】"
                        text.append(f"    {confidence_icon} {priority_label} {info['type']}")
                        text.append(f"       置信度: {confidence:.2f}")
                        text.append(f"       内容: {info['content']}")
                        text.append(f"       时间: {info.get('created_at', '')[:19]}")
                        text.append("")

                text.append("-" * 50)
        else:
            text.append("\n【检索到的知识】")
            text.append("  知识库中暂无相关信息")
            text.append("")

        text.append("")
        text.append("【摘要】")
        text.append(understanding_result.get('summary', ''))
        text.append("")
        text.append("=" * 50)
        text.append("✓ AI将基于以上知识来回答用户问题")

        self.update_text_widget(self.understanding_display, "\n".join(text))

    def update_knowledge_display(self):
        """
        更新知识库显示（支持基础知识和主体-定义-信息结构）
        """
        if not self.agent:
            return

        # 更新基础知识信息标签
        if hasattr(self.agent.memory_manager.knowledge_base, 'base_knowledge'):
            base_kb = self.agent.memory_manager.knowledge_base.base_knowledge
            base_facts = base_kb.get_all_base_facts()
            self.base_kb_info_label.config(
                text=f"🔒 基础知识: {len(base_facts)} 条 (优先级: 100%)"
            )

        knowledge_list = self.agent.get_all_knowledge()

        if not knowledge_list:
            # 即使没有普通知识，也显示基础知识
            if hasattr(self.agent.memory_manager.knowledge_base, 'base_knowledge'):
                base_kb = self.agent.memory_manager.knowledge_base.base_knowledge
                base_facts = base_kb.get_all_base_facts()
                if base_facts:
                    text = []
                    text.append("=" * 60)
                    text.append("【核心基础知识库 - 最高优先级】")
                    text.append("=" * 60)
                    text.append("")

                    for fact in base_facts:
                        text.append(f"🔒 主体: {fact['entity_name']}")
                        text.append(f"   内容: {fact['content']}")
                        text.append(f"   分类: {fact['category']}")
                        text.append(f"   优先级: {fact['priority']} | 置信度: {fact['confidence']*100:.0f}%")
                        if fact.get('description'):
                            text.append(f"   说明: {fact['description']}")
                        text.append(f"   创建时间: {fact['created_at'][:19]}")
                        text.append(f"   🔐 状态: 不可更改")
                        text.append("")
                        text.append("-" * 60)
                        text.append("")

                    text.append("\n普通知识库: 暂无知识\n对话超过5轮后将自动提取知识")
                    self.update_text_widget(self.knowledge_display, "\n".join(text))
                    return

            self.update_text_widget(self.knowledge_display, "暂无知识\n对话超过5轮后将自动提取知识")
            return

        text = []
        text.append("=" * 60)
        text.append(f"知识库总览")

        # 显示统计信息
        if hasattr(self.agent.memory_manager.knowledge_base, 'get_statistics'):
            stats = self.agent.memory_manager.knowledge_base.get_statistics()
            text.append(f"基础知识: {stats.get('base_knowledge_facts', 0)} 条 (优先级100%) | "
                       f"主体数: {stats.get('total_entities', 0)} | "
                       f"定义: {stats.get('total_definitions', 0)} | "
                       f"相关信息: {stats.get('total_related_info', 0)}")

        text.append("=" * 60)
        text.append("")

        # 首先显示基础知识（如果有）
        if hasattr(self.agent.memory_manager.knowledge_base, 'base_knowledge'):
            base_kb = self.agent.memory_manager.knowledge_base.base_knowledge
            base_facts = base_kb.get_all_base_facts()

            if base_facts:
                text.append("╔" + "═" * 58 + "╗")
                text.append("║" + " " * 15 + "【核心基础知识 - 优先级100%】" + " " * 15 + "║")
                text.append("╚" + "═" * 58 + "╝")
                text.append("")

                for fact in base_facts:
                    text.append(f"🔒 主体: {fact['entity_name']}")
                    text.append(f"   ● 内容: {fact['content']}")
                    text.append(f"   ● 分类: {fact['category']} | 置信度: {fact['confidence']*100:.0f}%")
                    if fact.get('description'):
                        text.append(f"   ● 说明: {fact['description']}")
                    text.append(f"   ● 时间: {fact['created_at'][:19]} | 状态: 🔐 不可更改")
                    text.append("")

                text.append("=" * 60)
                text.append("")

        # 显示普通知识库（按主体分组显示）
        text.append("【普通知识库】")
        text.append("")

        knowledge_by_entity = {}
        for k in knowledge_list:
            entity_name = k.get('entity_name', '未知主体')
            if entity_name not in knowledge_by_entity:
                knowledge_by_entity[entity_name] = {'definitions': [], 'related': []}

            if k.get('is_definition', False):
                knowledge_by_entity[entity_name]['definitions'].append(k)
            else:
                knowledge_by_entity[entity_name]['related'].append(k)

        for entity_name, items in knowledge_by_entity.items():
            text.append(f"📌 主体: {entity_name}")
            text.append("")

            # 显示定义（高置信度）
            if items['definitions']:
                for definition in items['definitions']:
                    confidence = definition.get('confidence', 1.0)
                    confidence_icon = "⭐" if confidence >= 0.9 else "✓"

                    # 检查是否来自基础知识
                    is_base = definition.get('is_base_knowledge', False)
                    base_mark = " [基础知识]" if is_base else ""

                    text.append(f"  {confidence_icon} 定义 (置信度: {confidence:.2f}){base_mark}")
                    text.append(f"     内容: {definition.get('content', '')}")
                    text.append(f"     类型: {definition.get('type', '')}")
                    text.append(f"     来源: {definition.get('source', '')}")
                    text.append(f"     时间: {definition.get('created_at', '')[:19]}")
                    if is_base:
                        text.append(f"     🔐 此定义来自基础知识库，不可更改")
                    text.append(f"     UUID: {definition.get('uuid', '')}")
                    text.append("")

            # 显示相关信息
            if items['related']:
                text.append(f"  相关信息 ({len(items['related'])}条):")
                for i, info in enumerate(items['related'], 1):
                    confidence = info.get('confidence', 0.8)
                    confidence_icon = "•" if confidence >= 0.7 else "◦"
                    text.append(f"    {confidence_icon} [{info.get('type', '其他')}] (置信度: {confidence:.2f})")
                    text.append(f"       {info.get('content', '')}")
                    text.append(f"       时间: {info.get('created_at', '')[:19]} | UUID: {info.get('uuid', '')}")
                    if i < len(items['related']):
                        text.append("")

            text.append("-" * 60)
            text.append("")

        self.update_text_widget(self.knowledge_display, "\n".join(text))

    def search_knowledge(self):
        """
        搜索知识库（支持主体名称搜索）
        """
        if not self.agent:
            return

        keyword = self.kb_search_var.get().strip()
        if not keyword:
            self.update_knowledge_display()
            return

        results = self.agent.search_knowledge(keyword=keyword)

        if not results:
            self.update_text_widget(self.knowledge_display, f"未找到包含 '{keyword}' 的知识")
            return

        text = []
        text.append("=" * 50)
        text.append(f"搜索结果: '{keyword}' (共 {len(results)} 条)")
        text.append("=" * 50)
        text.append("")

        # 按主体分组显示搜索结果
        results_by_entity = {}
        for k in results:
            entity_name = k.get('entity_name', '未知主体')
            if entity_name not in results_by_entity:
                results_by_entity[entity_name] = []
            results_by_entity[entity_name].append(k)

        for entity_name, items in results_by_entity.items():
            text.append(f"【主体: {entity_name}】")
            for item in items:
                confidence = item.get('confidence', 0.8)
                is_def = item.get('is_definition', False)
                type_label = "定义" if is_def else item.get('type', '其他')
                confidence_icon = "⭐" if confidence >= 0.9 else "✓" if confidence >= 0.7 else "◦"

                text.append(f"  {confidence_icon} [{type_label}] (置信度: {confidence:.2f})")
                text.append(f"     内容: {item.get('content', '')}")
                text.append(f"     来源: {item.get('source', '')}")
                text.append(f"     时间: {item.get('created_at', '')[:19]}")
                text.append(f"     UUID: {item.get('uuid', '')}")
                text.append("")
            text.append("-" * 50)

        self.update_text_widget(self.knowledge_display, "\n".join(text))

    def filter_knowledge_by_type(self):
        """
        按类型筛选知识（支持新的主体结构）
        """
        if not self.agent:
            return

        selected_type = self.kb_type_var.get()

        if selected_type == "全部":
            self.update_knowledge_display()
            return

        results = self.agent.search_knowledge(knowledge_type=selected_type)

        if not results:
            self.update_text_widget(self.knowledge_display, f"暂无 '{selected_type}' 类型的知识")
            return

        text = []
        text.append("=" * 50)
        text.append(f"类型筛选: {selected_type} (共 {len(results)} 条)")
        text.append("=" * 50)
        text.append("")

        # 按主体分组显示
        results_by_entity = {}
        for k in results:
            entity_name = k.get('entity_name', '未知主体')
            if entity_name not in results_by_entity:
                results_by_entity[entity_name] = []
            results_by_entity[entity_name].append(k)

        for entity_name, items in results_by_entity.items():
            text.append(f"【主体: {entity_name}】")
            for item in items:
                confidence = item.get('confidence', 0.8)
                is_def = item.get('is_definition', False)
                confidence_icon = "⭐" if confidence >= 0.9 else "✓" if confidence >= 0.7 else "◦"

                text.append(f"  {confidence_icon} {'定义' if is_def else '相关信息'} (置信度: {confidence:.2f})")
                text.append(f"     内容: {item.get('content', '')}")
                text.append(f"     来源: {item.get('source', '')}")
                text.append(f"     时间: {item.get('created_at', '')[:19]}")
                text.append(f"     UUID: {item.get('uuid', '')}")
                text.append("")
            text.append("-" * 50)

        self.update_text_widget(self.knowledge_display, "\n".join(text))

    def show_base_knowledge(self):
        """
        显示基础知识库详情
        """
        if not self.agent:
            return

        base_kb = self.agent.memory_manager.knowledge_base.base_knowledge
        base_facts = base_kb.get_all_base_facts()

        if not base_facts:
            messagebox.showinfo("基础知识库", "基础知识库为空")
            return

        # 创建新窗口显示基础知识
        base_window = tk.Toplevel(self.root)
        base_window.title("基础知识库 - 最高优先级")
        base_window.geometry("700x500")

        # 标题
        title_frame = ttk.Frame(base_window, padding=10)
        title_frame.pack(fill=tk.X)

        ttk.Label(
            title_frame,
            text="🔒 基础知识库（优先级: 100% | 不可更改）",
            font=("微软雅黑", 12, "bold"),
            foreground="#d35400"
        ).pack()

        # 统计信息
        stats = base_kb.get_statistics()
        ttk.Label(
            title_frame,
            text=f"总计: {stats['total_facts']} 条基础事实",
            font=("微软雅黑", 9)
        ).pack()

        # 显示区域
        text_widget = scrolledtext.ScrolledText(
            base_window,
            wrap=tk.WORD,
            font=("微软雅黑", 10),
            bg="#fff9e6"
        )
        text_widget.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # 生成显示内容
        text = []
        text.append(base_kb.generate_base_knowledge_prompt())
        text.append("\n")
        text.append("=" * 60)
        text.append("详细信息")
        text.append("=" * 60)
        text.append("")

        for i, fact in enumerate(base_facts, 1):
            text.append(f"{i}. 【{fact['entity_name']}】")
            text.append(f"   内容: {fact['content']}")
            text.append(f"   分类: {fact['category']}")
            text.append(f"   优先级: {fact['priority']} | 置信度: {fact['confidence']*100:.0f}%")
            if fact.get('description'):
                text.append(f"   说明: {fact['description']}")
            text.append(f"   创建时间: {fact['created_at'][:19]}")
            text.append(f"   不可变: {'是' if fact.get('immutable', True) else '否'}")
            text.append("")

        text_widget.insert(tk.END, "\n".join(text))
        text_widget.config(state=tk.DISABLED)

        # 关闭按钮
        ttk.Button(
            base_window,
            text="关闭",
            command=base_window.destroy
        ).pack(pady=10)

    def add_base_knowledge(self):
        """
        添加基础知识对话框
        """
        if not self.agent:
            return

        # 创建对话框
        dialog = tk.Toplevel(self.root)
        dialog.title("添加基础知识")
        dialog.geometry("600x450")
        dialog.transient(self.root)
        dialog.grab_set()

        # 标题
        ttk.Label(
            dialog,
            text="添加核心基础知识",
            font=("微软雅黑", 12, "bold")
        ).pack(pady=10)

        ttk.Label(
            dialog,
            text="基础知识具有最高优先级（100%），不可被覆盖或更改",
            font=("微软雅黑", 9),
            foreground="#d35400"
        ).pack()

        # 输入框架
        input_frame = ttk.Frame(dialog, padding=15)
        input_frame.pack(fill=tk.BOTH, expand=True)

        # 实体名称
        ttk.Label(input_frame, text="实体名称:", font=("微软雅黑", 10)).grid(row=0, column=0, sticky=tk.W, pady=5)
        entity_entry = ttk.Entry(input_frame, width=40, font=("微软雅黑", 10))
        entity_entry.grid(row=0, column=1, pady=5, padx=10)

        # 事实内容
        ttk.Label(input_frame, text="事实内容:", font=("微软雅黑", 10)).grid(row=1, column=0, sticky=tk.NW, pady=5)
        content_text = tk.Text(input_frame, width=40, height=4, font=("微软雅黑", 10))
        content_text.grid(row=1, column=1, pady=5, padx=10)

        # 分类
        ttk.Label(input_frame, text="分类:", font=("微软雅黑", 10)).grid(row=2, column=0, sticky=tk.W, pady=5)
        category_var = tk.StringVar(value="通用")
        category_combo = ttk.Combobox(
            input_frame,
            textvariable=category_var,
            width=38,
            font=("微软雅黑", 10)
        )
        category_combo['values'] = ['机构类型', '人物定义', '地点定义', '事物定义', '关系定义', '通用']
        category_combo.grid(row=2, column=1, pady=5, padx=10)

        # 说明
        ttk.Label(input_frame, text="说明:", font=("微软雅黑", 10)).grid(row=3, column=0, sticky=tk.NW, pady=5)
        desc_text = tk.Text(input_frame, width=40, height=3, font=("微软雅黑", 10))
        desc_text.grid(row=3, column=1, pady=5, padx=10)

        # 提示信息
        tip_frame = ttk.Frame(dialog)
        tip_frame.pack(fill=tk.X, padx=15, pady=5)
        ttk.Label(
            tip_frame,
            text="⚠️ 注意：基础知识一旦添加，将优先于所有其他信息，即使与现实相悖也会被遵循",
            font=("微软雅黑", 8),
            foreground="red",
            wraplength=550
        ).pack()

        # 按钮
        button_frame = ttk.Frame(dialog)
        button_frame.pack(pady=15)

        def save_base_knowledge():
            entity_name = entity_entry.get().strip()
            content = content_text.get("1.0", tk.END).strip()
            category = category_var.get().strip()
            description = desc_text.get("1.0", tk.END).strip()

            if not entity_name or not content:
                messagebox.showwarning("输入错误", "实体名称和事实内容不能为空")
                return

            # 添加基础知识
            base_kb = self.agent.memory_manager.knowledge_base.base_knowledge
            success = base_kb.add_base_fact(
                entity_name=entity_name,
                fact_content=content,
                category=category,
                description=description,
                immutable=True
            )

            if success:
                messagebox.showinfo("成功", f"已添加基础知识：{entity_name}")
                self.update_knowledge_display()
                dialog.destroy()
            else:
                messagebox.showerror("失败", "添加基础知识失败（可能已存在同名实体）")

        ttk.Button(
            button_frame,
            text="保存",
            command=save_base_knowledge,
            width=15
        ).pack(side=tk.LEFT, padx=5)

        ttk.Button(
            button_frame,
            text="取消",
            command=dialog.destroy,
            width=15
        ).pack(side=tk.LEFT, padx=5)

    def update_timeline(self):
        """
        更新主题时间线
        """
        if not self.agent:
            return

        summaries = self.agent.get_long_term_summaries()
        self.timeline_canvas.update_topics(summaries)

    def update_text_widget(self, widget, text):
        """
        更新文本组件内容
        """
        widget.config(state=tk.NORMAL)
        widget.delete(1.0, tk.END)
        widget.insert(tk.END, text)
        widget.config(state=tk.DISABLED)

    def update_status(self, status: str, color: str = "black"):
        """
        更新状态标签
        """
        self.status_label.config(text=f"● {status}", foreground=color)
        self.root.update()

    def on_debug_log_added(self, log_entry: Dict[str, Any]):
        """
        Debug日志监听器回调，当有新日志时自动更新显示

        Args:
            log_entry: 日志条目
        """
        if not hasattr(self, 'debug_display') or not self.debug_auto_refresh.get():
            return

        # 在主线程中更新UI
        self.root.after(0, lambda: self._append_debug_log(log_entry))

    def _append_debug_log(self, log_entry: Dict[str, Any]):
        """
        添加单条debug日志到显示区域

        Args:
            log_entry: 日志条目
        """
        try:
            # 检查是否需要筛选
            selected_type = self.debug_type_var.get()
            if selected_type != "全部" and log_entry['type'] != selected_type:
                return

            self.debug_display.config(state=tk.NORMAL)

            # 时间戳
            timestamp = log_entry['timestamp'][11:19]
            self.debug_display.insert(tk.END, f"[{timestamp}] ", "timestamp")

            # 日志类型
            log_type = log_entry['type'].upper()
            self.debug_display.insert(tk.END, f"[{log_type}] ", log_entry['type'])

            # 模块名
            module = log_entry.get('module', 'Unknown')
            self.debug_display.insert(tk.END, f"{module} ", "info")

            # 根据类型显示不同内容
            if log_entry['type'] == 'module':
                self.debug_display.insert(tk.END, f"| {log_entry.get('action', '')}\n")
                if log_entry.get('details'):
                    self.debug_display.insert(tk.END, f"  详情: {log_entry['details']}\n", "info")

            elif log_entry['type'] == 'prompt':
                prompt_type = log_entry.get('prompt_type', '')
                content = log_entry.get('content', '')
                display_content = content[:150] + "..." if len(content) > 150 else content
                self.debug_display.insert(tk.END, f"| {prompt_type}\n")
                self.debug_display.insert(tk.END, f"  {display_content}\n", "prompt")

            elif log_entry['type'] == 'request':
                api_url = log_entry.get('api_url', '')
                self.debug_display.insert(tk.END, f"| {api_url}\n")

            elif log_entry['type'] == 'response':
                status = log_entry.get('status_code', 0)
                elapsed = log_entry.get('elapsed_time', 0)
                self.debug_display.insert(tk.END, f"| 状态:{status} 耗时:{elapsed:.2f}s\n")

            elif log_entry['type'] == 'error':
                message = log_entry.get('message', '')
                self.debug_display.insert(tk.END, f"| {message}\n", "error")

            elif log_entry['type'] == 'info':
                message = log_entry.get('message', '')
                self.debug_display.insert(tk.END, f"| {message}\n")

            self.debug_display.insert(tk.END, "\n")
            self.debug_display.see(tk.END)
            self.debug_display.config(state=tk.DISABLED)

            # 更新统计
            if hasattr(self, 'debug_logger'):
                stats = self.debug_logger.get_statistics()
                self.debug_stats_label.config(text=f"日志: {stats['total_logs']} 条")

        except Exception as e:
            print(f"✗ 更新debug日志显示失败: {e}")

    def update_debug_display(self):
        """
        更新Debug日志显示
        """
        if not hasattr(self, 'debug_display') or not hasattr(self, 'debug_logger'):
            return

        try:
            # 获取筛选类型
            selected_type = self.debug_type_var.get()
            log_type = None if selected_type == "全部" else selected_type

            # 获取日志
            logs = self.debug_logger.get_logs(log_type=log_type, limit=500)

            # 清空并重新显示
            self.debug_display.config(state=tk.NORMAL)
            self.debug_display.delete(1.0, tk.END)

            if not logs:
                self.debug_display.insert(tk.END, "暂无日志\n", "info")
            else:
                for log_entry in logs:
                    self._append_debug_log(log_entry)

            self.debug_display.config(state=tk.DISABLED)

            # 更新统计
            stats = self.debug_logger.get_statistics()
            self.debug_stats_label.config(
                text=f"日志: {stats['total_logs']} 条 | "
                     f"模块:{stats['by_type']['module']} "
                     f"提示词:{stats['by_type']['prompt']} "
                     f"请求:{stats['by_type']['request']} "
                     f"响应:{stats['by_type']['response']} "
                     f"错误:{stats['by_type']['error']}"
            )

        except Exception as e:
            print(f"✗ 更新debug显示失败: {e}")

    def clear_debug_logs(self):
        """
        清空Debug日志
        """
        if not hasattr(self, 'debug_logger'):
            return

        if messagebox.askyesno("确认", "确定要清空所有Debug日志吗？"):
            self.debug_logger.clear_logs()
            if hasattr(self, 'debug_display'):
                self.debug_display.config(state=tk.NORMAL)
                self.debug_display.delete(1.0, tk.END)
                self.debug_display.insert(tk.END, "日志已清空\n", "info")
                self.debug_display.config(state=tk.DISABLED)

            self.debug_stats_label.config(text="日志: 0 条")
            messagebox.showinfo("成功", "Debug日志已清空")

    def add_message_to_display(self, role: str, content: str):
        """
        在聊天显示区添加消息
        """
        self.chat_display.config(state=tk.NORMAL)

        timestamp = datetime.now().strftime("%H:%M:%S")
        self.chat_display.insert(tk.END, f"[{timestamp}] ", "timestamp")

        if role == "user":
            self.chat_display.insert(tk.END, "你: ", "user")
        elif role == "assistant":
            name = self.agent.character.name if self.agent else "助手"
            self.chat_display.insert(tk.END, f"{name}: ", "assistant")

        self.chat_display.insert(tk.END, f"{content}\n\n")
        self.chat_display.see(tk.END)
        self.chat_display.config(state=tk.DISABLED)

    def add_system_message(self, message: str):
        """
        添加系统消息
        """
        self.chat_display.config(state=tk.NORMAL)
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.chat_display.insert(tk.END, f"[{timestamp}] ", "timestamp")
        self.chat_display.insert(tk.END, f"[系统] {message}\n\n", "system")
        self.chat_display.see(tk.END)
        self.chat_display.config(state=tk.DISABLED)

    def add_archive_message(self, rounds: int, summary: str):
        """
        添加归档消息
        """
        self.chat_display.config(state=tk.NORMAL)
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.chat_display.insert(tk.END, f"[{timestamp}] ", "timestamp")
        self.chat_display.insert(tk.END, f"[记忆归档] 已将前{rounds}轮对话归档\n", "archive")
        self.chat_display.insert(tk.END, f"主题概括: {summary}\n\n", "archive")
        self.chat_display.see(tk.END)
        self.chat_display.config(state=tk.DISABLED)

    def add_knowledge_extraction_message(self, knowledge_count: int):
        """
        添加知识提取消息
        """
        self.chat_display.config(state=tk.NORMAL)
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.chat_display.insert(tk.END, f"[{timestamp}] ", "timestamp")
        self.chat_display.insert(tk.END, f"[知识提取] 已从最近5轮对话中提取 {knowledge_count} 条知识\n\n", "archive")
        self.chat_display.see(tk.END)
        self.chat_display.config(state=tk.DISABLED)

    def send_message(self):
        """
        发送消息
        """
        if self.is_processing:
            messagebox.showwarning("请稍候", "正在处理上一条消息，请稍候...")
            return

        if not self.agent:
            messagebox.showerror("错误", "聊天代理未初始化")
            return

        user_input = self.input_text.get(1.0, tk.END).strip()

        if not user_input:
            messagebox.showwarning("提示", "请输入消息内容")
            return

        self.add_message_to_display("user", user_input)
        self.input_text.delete(1.0, tk.END)

        self.is_processing = True
        self.update_status("思考中...", "orange")
        self.send_button.config(state=tk.DISABLED)

        # 记录当前长期记忆数量
        old_summary_count = len(self.agent.get_long_term_summaries())

        def process_chat():
            try:
                response = self.agent.chat(user_input)
                self.root.after(0, lambda: self.handle_response(response, old_summary_count))
            except Exception as e:
                error_msg = f"处理消息时出错: {str(e)}"
                self.root.after(0, lambda: self.handle_error(error_msg))

        thread = threading.Thread(target=process_chat, daemon=True)
        thread.start()

    def handle_response(self, response: str, old_summary_count: int):
        """
        处理代理回复
        """
        self.add_message_to_display("assistant", response)

        # 更新理解阶段显示
        understanding_result = self.agent.get_last_understanding()
        if understanding_result:
            self.update_understanding_display(understanding_result)

        # 检查是否生成了新的概括
        new_summaries = self.agent.get_long_term_summaries()
        if len(new_summaries) > old_summary_count:
            # 有新的概括生成
            latest_summary = new_summaries[-1]
            self.add_archive_message(latest_summary.get('rounds', 20), latest_summary.get('summary', ''))
            self.update_timeline()

        # 检查是否提取了新知识（通过对话轮数判断）
        stats = self.agent.get_memory_stats()
        current_rounds = stats['total_conversations']
        if current_rounds > 0 and current_rounds % 5 == 0:
            # 刚好是5的倍数，可能提取了知识
            # 通过比较知识数量来确认
            old_kb_count = getattr(self, '_last_kb_count', 0)
            new_kb_count = stats['knowledge_base']['total_knowledge']
            if new_kb_count > old_kb_count:
                extracted_count = new_kb_count - old_kb_count
                self.add_knowledge_extraction_message(extracted_count)
                self._last_kb_count = new_kb_count

        # 检查是否进行了自动情感分析（每10轮）
        short_term_rounds = stats['short_term']['rounds']
        if short_term_rounds > 0 and short_term_rounds % 10 == 0:
            # 可能刚进行了情感分析，检查是否有新的情感数据
            old_emotion_count = getattr(self, '_last_emotion_count', 0)
            emotion_history = self.agent.get_emotion_history()
            new_emotion_count = len(emotion_history)

            if new_emotion_count > old_emotion_count:
                # 有新的情感分析结果，自动刷新显示
                latest_emotion = self.agent.get_latest_emotion()
                if latest_emotion:
                    debug_logger = get_debug_logger()
                    debug_logger.log_info('GUI', '检测到新的情感分析结果，自动刷新显示', {
                        'emotion_count': new_emotion_count,
                        'relationship_type': latest_emotion.get('relationship_type', '未知'),
                        'overall_score': latest_emotion.get('overall_score', 0)
                    })

                    # 刷新情感显示
                    self.update_emotion_display(latest_emotion)

                    # 在聊天窗口显示提示
                    self.add_system_message(
                        f"💖 情感分析已更新 | 关系：{latest_emotion.get('relationship_type', '未知')} | "
                        f"评分：{latest_emotion.get('overall_score', 0)}/100 | "
                        f"基调：{latest_emotion.get('emotional_tone', '未知')}"
                    )

                    self._last_emotion_count = new_emotion_count

        # 更新显示
        self.refresh_all()

        self.is_processing = False
        self.update_status("就绪", "green")
        self.send_button.config(state=tk.NORMAL)
        self.input_text.focus()

    def handle_error(self, error_msg: str):
        """
        处理错误
        """
        self.add_system_message(f"错误: {error_msg}")
        messagebox.showerror("错误", error_msg)

        self.is_processing = False
        self.update_status("出错", "red")
        self.send_button.config(state=tk.NORMAL)

    def clear_input(self):
        """
        清空输入框
        """
        self.input_text.delete(1.0, tk.END)

    def clear_chat_display(self):
        """
        清空聊天显示区
        """
        result = messagebox.askyesno("确认", "确定要清空聊天显示区吗？\n（不会删除历史记忆）")
        if result:
            self.chat_display.config(state=tk.NORMAL)
            self.chat_display.delete(1.0, tk.END)
            self.chat_display.config(state=tk.DISABLED)
            self.add_system_message("聊天显示区已清空")

    def clear_all_memory(self):
        """
        清空所有记忆
        """
        result = messagebox.askyesno(
            "警告",
            "确定要清空所有记忆吗？\n包括短期和长期记忆！\n此操作不可恢复！",
            icon='warning'
        )

        if result:
            if self.agent:
                self.agent.clear_memory()
                self.chat_display.config(state=tk.NORMAL)
                self.chat_display.delete(1.0, tk.END)
                self.chat_display.config(state=tk.DISABLED)
                self.add_system_message("所有记忆已清空")
                self.refresh_all()

    def reload_agent(self):
        """
        重新加载代理
        """
        result = messagebox.askyesno("确认", "确定要重新加载代理吗？\n将重新读取配置文件")
        if result:
            self.initialize_agent()
            messagebox.showinfo("成功", "代理已重新加载")

    # ==================== 环境管理相关方法 ====================

    def refresh_environment_display(self):
        """
        刷新环境显示
        """
        try:
            # 获取所有环境
            environments = self.agent.db.get_all_environments()
            active_env = self.agent.db.get_active_environment()
            
            display_text = "【智能体视觉环境配置】\n\n"
            
            if not environments:
                display_text += "暂无环境配置。\n\n"
                display_text += "💡 提示:\n"
                display_text += "- 点击「创建默认环境」快速创建一个示例环境\n"
                display_text += "- 点击「新建环境」手动创建自定义环境\n"
                display_text += "- 环境配置后，当用户询问周围环境时，智能体会自动使用视觉工具\n"
            else:
                display_text += f"共有 {len(environments)} 个环境配置\n"
                if active_env:
                    display_text += f"当前激活: {active_env['name']}\n"
                display_text += "=" * 60 + "\n\n"
                
                for env in environments:
                    is_active = env['uuid'] == active_env['uuid'] if active_env else False
                    status_icon = "🟢" if is_active else "⚪"
                    
                    display_text += f"{status_icon} 【环境: {env['name']}】\n"
                    display_text += f"UUID: {env['uuid'][:8]}...\n"
                    display_text += f"整体描述: {env['overall_description']}\n"
                    
                    if env.get('atmosphere'):
                        display_text += f"氛围: {env['atmosphere']}\n"
                    if env.get('lighting'):
                        display_text += f"光照: {env['lighting']}\n"
                    if env.get('sounds'):
                        display_text += f"声音: {env['sounds']}\n"
                    if env.get('smells'):
                        display_text += f"气味: {env['smells']}\n"
                    
                    display_text += f"创建时间: {env['created_at']}\n"
                    
                    # 获取环境中的物体
                    objects = self.agent.db.get_environment_objects(env['uuid'])
                    display_text += f"\n物体数量: {len(objects)}\n"
                    
                    if objects:
                        display_text += "物体列表:\n"
                        for obj in objects:
                            visibility = "👁️" if obj['is_visible'] else "👁️‍🗨️"
                            display_text += f"  {visibility} {obj['name']} (优先级: {obj['priority']})\n"
                            display_text += f"     {obj['description']}\n"
                            if obj.get('position'):
                                display_text += f"     位置: {obj['position']}\n"
                    
                    display_text += "\n" + "=" * 60 + "\n\n"
            
            self.update_text_widget(self.environment_display, display_text)
        except Exception as e:
            self.update_text_widget(self.environment_display, f"刷新环境显示时出错: {e}")

    def create_new_environment(self):
        """
        创建新环境
        """
        # 创建对话框
        dialog = tk.Toplevel(self.root)
        dialog.title("创建新环境")
        dialog.geometry("600x500")
        dialog.transient(self.root)
        dialog.grab_set()
        
        # 环境名称
        ttk.Label(dialog, text="环境名称:", font=("微软雅黑", 10)).pack(pady=(10, 0), padx=10, anchor=tk.W)
        name_entry = ttk.Entry(dialog, width=70)
        name_entry.pack(pady=5, padx=10, fill=tk.X)
        
        # 整体描述
        ttk.Label(dialog, text="整体描述:", font=("微软雅黑", 10)).pack(pady=(10, 0), padx=10, anchor=tk.W)
        desc_text = scrolledtext.ScrolledText(dialog, height=6, width=70, wrap=tk.WORD)
        desc_text.pack(pady=5, padx=10, fill=tk.BOTH, expand=True)
        
        # 氛围
        ttk.Label(dialog, text="氛围:", font=("微软雅黑", 10)).pack(pady=(10, 0), padx=10, anchor=tk.W)
        atmosphere_entry = ttk.Entry(dialog, width=70)
        atmosphere_entry.pack(pady=5, padx=10, fill=tk.X)
        
        # 光照
        ttk.Label(dialog, text="光照:", font=("微软雅黑", 10)).pack(pady=(10, 0), padx=10, anchor=tk.W)
        lighting_entry = ttk.Entry(dialog, width=70)
        lighting_entry.pack(pady=5, padx=10, fill=tk.X)
        
        # 声音
        ttk.Label(dialog, text="声音:", font=("微软雅黑", 10)).pack(pady=(10, 0), padx=10, anchor=tk.W)
        sounds_entry = ttk.Entry(dialog, width=70)
        sounds_entry.pack(pady=5, padx=10, fill=tk.X)
        
        # 气味
        ttk.Label(dialog, text="气味:", font=("微软雅黑", 10)).pack(pady=(10, 0), padx=10, anchor=tk.W)
        smells_entry = ttk.Entry(dialog, width=70)
        smells_entry.pack(pady=5, padx=10, fill=tk.X)
        
        # 按钮
        button_frame = ttk.Frame(dialog)
        button_frame.pack(pady=20)
        
        def save_environment():
            name = name_entry.get().strip()
            desc = desc_text.get("1.0", tk.END).strip()
            
            if not name or not desc:
                messagebox.showerror("错误", "环境名称和整体描述不能为空！")
                return
            
            try:
                env_uuid = self.agent.db.create_environment(
                    name=name,
                    overall_description=desc,
                    atmosphere=atmosphere_entry.get().strip(),
                    lighting=lighting_entry.get().strip(),
                    sounds=sounds_entry.get().strip(),
                    smells=smells_entry.get().strip()
                )
                
                # 如果是第一个环境，自动设为激活
                all_envs = self.agent.db.get_all_environments()
                if len(all_envs) == 1:
                    self.agent.db.set_active_environment(env_uuid)
                
                messagebox.showinfo("成功", f"环境创建成功！\nUUID: {env_uuid[:8]}...")
                dialog.destroy()
                self.refresh_environment_display()
            except Exception as e:
                messagebox.showerror("错误", f"创建环境失败: {e}")
        
        ttk.Button(button_frame, text="保存", command=save_environment, width=15).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="取消", command=dialog.destroy, width=15).pack(side=tk.LEFT, padx=5)

    def add_new_object(self):
        """
        添加新物体到当前激活的环境
        """
        # 检查是否有激活的环境
        active_env = self.agent.db.get_active_environment()
        if not active_env:
            messagebox.showerror("错误", "请先创建并激活一个环境！")
            return
        
        # 创建对话框
        dialog = tk.Toplevel(self.root)
        dialog.title(f"添加物体到环境: {active_env['name']}")
        dialog.geometry("600x500")
        dialog.transient(self.root)
        dialog.grab_set()
        
        # 物体名称
        ttk.Label(dialog, text="物体名称:", font=("微软雅黑", 10)).pack(pady=(10, 0), padx=10, anchor=tk.W)
        name_entry = ttk.Entry(dialog, width=70)
        name_entry.pack(pady=5, padx=10, fill=tk.X)
        
        # 物体描述
        ttk.Label(dialog, text="物体描述:", font=("微软雅黑", 10)).pack(pady=(10, 0), padx=10, anchor=tk.W)
        desc_text = scrolledtext.ScrolledText(dialog, height=6, width=70, wrap=tk.WORD)
        desc_text.pack(pady=5, padx=10, fill=tk.BOTH, expand=True)
        
        # 位置
        ttk.Label(dialog, text="位置:", font=("微软雅黑", 10)).pack(pady=(10, 0), padx=10, anchor=tk.W)
        position_entry = ttk.Entry(dialog, width=70)
        position_entry.pack(pady=5, padx=10, fill=tk.X)
        
        # 属性
        ttk.Label(dialog, text="属性:", font=("微软雅黑", 10)).pack(pady=(10, 0), padx=10, anchor=tk.W)
        properties_entry = ttk.Entry(dialog, width=70)
        properties_entry.pack(pady=5, padx=10, fill=tk.X)
        
        # 交互提示
        ttk.Label(dialog, text="交互提示:", font=("微软雅黑", 10)).pack(pady=(10, 0), padx=10, anchor=tk.W)
        hints_entry = ttk.Entry(dialog, width=70)
        hints_entry.pack(pady=5, padx=10, fill=tk.X)
        
        # 优先级
        priority_frame = ttk.Frame(dialog)
        priority_frame.pack(pady=10, padx=10, fill=tk.X)
        ttk.Label(priority_frame, text="优先级 (0-100):", font=("微软雅黑", 10)).pack(side=tk.LEFT)
        priority_var = tk.IntVar(value=50)
        priority_spinbox = ttk.Spinbox(priority_frame, from_=0, to=100, textvariable=priority_var, width=10)
        priority_spinbox.pack(side=tk.LEFT, padx=10)
        
        # 按钮
        button_frame = ttk.Frame(dialog)
        button_frame.pack(pady=20)
        
        def save_object():
            name = name_entry.get().strip()
            desc = desc_text.get("1.0", tk.END).strip()
            
            if not name or not desc:
                messagebox.showerror("错误", "物体名称和描述不能为空！")
                return
            
            try:
                obj_uuid = self.agent.db.add_environment_object(
                    environment_uuid=active_env['uuid'],
                    name=name,
                    description=desc,
                    position=position_entry.get().strip(),
                    properties=properties_entry.get().strip(),
                    interaction_hints=hints_entry.get().strip(),
                    priority=priority_var.get()
                )
                
                messagebox.showinfo("成功", f"物体添加成功！\nUUID: {obj_uuid[:8]}...")
                dialog.destroy()
                self.refresh_environment_display()
            except Exception as e:
                messagebox.showerror("错误", f"添加物体失败: {e}")
        
        ttk.Button(button_frame, text="保存", command=save_object, width=15).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="取消", command=dialog.destroy, width=15).pack(side=tk.LEFT, padx=5)

    def show_vision_logs(self):
        """
        显示视觉工具使用记录
        """
        # 创建对话框
        dialog = tk.Toplevel(self.root)
        dialog.title("视觉工具使用记录")
        dialog.geometry("800x600")
        dialog.transient(self.root)
        
        # 工具栏
        toolbar = ttk.Frame(dialog)
        toolbar.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Label(toolbar, text="最近50条记录", font=("微软雅黑", 10, "bold")).pack(side=tk.LEFT)
        
        # 日志显示
        log_text = scrolledtext.ScrolledText(dialog, wrap=tk.WORD, font=("微软雅黑", 9))
        log_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        try:
            logs = self.agent.db.get_vision_tool_logs(limit=50)
            
            if not logs:
                log_text.insert(tk.END, "暂无视觉工具使用记录\n\n")
                log_text.insert(tk.END, "💡 提示: 当用户询问周围环境时，视觉工具会自动触发并记录")
            else:
                log_text.insert(tk.END, f"共有 {len(logs)} 条记录\n")
                log_text.insert(tk.END, "=" * 80 + "\n\n")
                
                for i, log in enumerate(logs, 1):
                    log_text.insert(tk.END, f"【记录 {i}】\n")
                    log_text.insert(tk.END, f"时间: {log['created_at']}\n")
                    log_text.insert(tk.END, f"触发方式: {log['triggered_by']}\n")
                    log_text.insert(tk.END, f"用户查询: {log['query']}\n")
                    
                    if log.get('environment_uuid'):
                        env = self.agent.db.get_environment(log['environment_uuid'])
                        env_name = env['name'] if env else "已删除的环境"
                        log_text.insert(tk.END, f"环境: {env_name}\n")
                    
                    if log.get('objects_viewed'):
                        log_text.insert(tk.END, f"查看的物体: {log['objects_viewed']}\n")
                    
                    if log.get('context_provided'):
                        preview = log['context_provided'][:100]
                        log_text.insert(tk.END, f"上下文预览: {preview}...\n")
                    
                    log_text.insert(tk.END, "\n" + "-" * 80 + "\n\n")
        except Exception as e:
            log_text.insert(tk.END, f"加载日志时出错: {e}")
        
        log_text.config(state=tk.DISABLED)
        
        # 关闭按钮
        ttk.Button(dialog, text="关闭", command=dialog.destroy, width=15).pack(pady=10)

    def create_default_environment(self):
        """
        创建默认环境（小可的房间）
        """
        result = messagebox.askyesno(
            "确认",
            "将创建默认示例环境「小可的房间」\n包含7个预设物体\n\n确定要创建吗？"
        )
        
        if result:
            try:
                env_uuid = self.agent.vision_tool.create_default_environment()
                messagebox.showinfo(
                    "成功",
                    f"默认环境创建成功！\n\n环境: 小可的房间\nUUID: {env_uuid[:8]}...\n物体数量: 7个\n\n该环境已自动设为激活状态。"
                )
                self.refresh_environment_display()
            except Exception as e:
                messagebox.showerror("错误", f"创建默认环境失败: {e}")

    def show_about(self):
        """
        显示关于对话框
        """
        about_text = """
智能对话代理 v3.0 知识库版
基于LangChain和Python开发

功能特性:
• 角色扮演对话
• 三层记忆系统（短期+长期+知识库）
• 短期记忆：最近20轮详细对话
• 长期记忆：自动主题概括（每20轮）
• 知识库：自动知识提取（每5轮）
• 对话主题时间线可视化
• 知识库搜索和分类管理
• 对话历史持久化
• 可视化调试界面

技术栈: Python + Tkinter + LangChain
开发: 2025
        """
        messagebox.showinfo("关于", about_text)


def main():
    """
    主函数
    """
    root = tk.Tk()

    style = ttk.Style()
    try:
        style.theme_use('clam')
    except:
        pass

    app = EnhancedChatDebugGUI(root)
    root.mainloop()


if __name__ == '__main__':
    main()

