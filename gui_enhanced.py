"""
增强版Tkinter GUI界面
包含聊天主题时间线可视化功能和Debug日志界面
"""

import os
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, Canvas, simpledialog, filedialog
from datetime import datetime
import threading
import math
from typing import Dict, Any, List, Optional
from chat_agent import ChatAgent
from database_manager import DatabaseManager
from debug_logger import get_debug_logger
from emotion_analyzer import format_emotion_summary
from tooltip_utils import ToolTip, create_treeview_tooltip
from agent_config_manager import AgentConfigManager


class EmotionImpressionDisplay(Canvas):
    """
    情感印象展示画布
    用于展示基于印象的情感分析结果
    """

    def __init__(self, parent, **kwargs):
        """
        初始化印象展示画布

        Args:
            parent: 父容器
        """
        super().__init__(parent, **kwargs)
        self.emotion_data = None
        self.colors = {
            'bg': '#f8f9fa',
            'positive': '#4caf50',
            'neutral': '#9e9e9e',
            'negative': '#f44336',
            'text': '#212121',
            'secondary': '#757575',
            'border': '#e0e0e0'
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
        debug_logger.log_info('EmotionImpressionDisplay', '更新情感数据', {
            'has_data': bool(emotion_data),
            'keys': list(emotion_data.keys()) if emotion_data else []
        })

        self.emotion_data = emotion_data
        self.draw_impression()

        debug_logger.log_info('EmotionImpressionDisplay', '印象展示重绘完成')

    def draw_impression(self):
        """
        绘制印象展示
        """
        self.delete('all')  # 清空画布

        width = self.winfo_width()
        height = self.winfo_height()

        if width <= 1 or height <= 1:
            return

        # 如果没有数据，显示提示
        if not self.emotion_data:
            self.create_text(
                width // 2, height // 2,
                text="暂无情感分析数据\n对话后点击「分析情感关系」按钮",
                font=('微软雅黑', 10),
                fill=self.colors['secondary'],
                justify=tk.CENTER
            )
            return

        # 提取数据
        overall_score = self.emotion_data.get('overall_score', 50)
        sentiment = self.emotion_data.get('sentiment', 'neutral')
        relationship_type = self.emotion_data.get('relationship_type', '未知')
        emotional_tone = self.emotion_data.get('emotional_tone', '未知')

        # 根据情感倾向选择颜色
        if sentiment == 'positive':
            score_color = self.colors['positive']
            sentiment_text = "正面印象"
        elif sentiment == 'negative':
            score_color = self.colors['negative']
            sentiment_text = "负面印象"
        else:
            score_color = self.colors['neutral']
            sentiment_text = "中性印象"

        # 绘制评分圆环
        center_x = width // 2
        center_y = height // 3
        radius = min(width, height) // 5

        # 背景圆
        self.create_oval(
            center_x - radius, center_y - radius,
            center_x + radius, center_y + radius,
            outline=self.colors['border'], width=15,
            fill=''
        )

        # 评分圆弧（根据分数显示）
        extent = int(360 * (overall_score / 100))
        self.create_arc(
            center_x - radius, center_y - radius,
            center_x + radius, center_y + radius,
            start=90, extent=-extent,
            outline=score_color, width=15,
            style='arc'
        )

        # 中心显示评分
        self.create_text(
            center_x, center_y - 10,
            text=str(overall_score),
            font=('微软雅黑', 32, 'bold'),
            fill=score_color
        )
        self.create_text(
            center_x, center_y + 20,
            text=sentiment_text,
            font=('微软雅黑', 10),
            fill=self.colors['text']
        )

        # 绘制关系信息
        info_y = center_y + radius + 40
        self.create_text(
            center_x, info_y,
            text=f"关系类型：{relationship_type}",
            font=('微软雅黑', 11, 'bold'),
            fill=self.colors['text']
        )
        self.create_text(
            center_x, info_y + 25,
            text=f"情感基调：{emotional_tone}",
            font=('微软雅黑', 10),
            fill=self.colors['secondary']
        )

    def _draw_pentagon(self, cx, cy, radius, **kwargs):
        """
        绘制五边形（保留以兼容旧方法）

        Args:
            cx: 中心x坐标
            cy: 中心y坐标
            radius: 半径
        """
        points = []
        for i in range(5):
            angle = math.radians(90 - i * 72)
            x = cx + radius * math.cos(angle)
            y = cy - radius * math.sin(angle)
            points.extend([x, y])
        return self.create_polygon(points, **kwargs)

    def on_resize(self, event):
        """
        响应窗口大小变化

        Args:
            event: 事件对象
        """
        self.draw_impression()


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

        self.emotion_canvas = EmotionImpressionDisplay(
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

        # 角色信息栏（固定高度，添加滚动条）
        self.character_frame = ttk.LabelFrame(parent, text="📋 当前角色", padding=5, height=60)
        self.character_frame.pack(fill=tk.X, padx=5, pady=3, side=tk.TOP)
        self.character_frame.pack_propagate(False)

        self.character_label = ttk.Label(
            self.character_frame,
            text="加载中...",
            font=("微软雅黑", 9),
            wraplength=1300  # 设置换行宽度
        )
        self.character_label.pack(fill=tk.BOTH, expand=True)
        
        # 添加工具提示支持
        self.character_tooltip = None

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

        # 环境管理工具栏 - 第一行
        env_toolbar1 = ttk.Frame(environment_tab)
        env_toolbar1.pack(fill=tk.X, padx=5, pady=5)

        ttk.Label(
            env_toolbar1,
            text="智能体视觉环境配置",
            font=("微软雅黑", 10, "bold")
        ).pack(side=tk.LEFT, padx=5)

        ttk.Button(
            env_toolbar1,
            text="🔄 刷新",
            command=self.refresh_environment_display,
            width=10
        ).pack(side=tk.LEFT, padx=2)

        ttk.Button(
            env_toolbar1,
            text="➕ 新建环境",
            command=self.create_new_environment,
            width=12
        ).pack(side=tk.LEFT, padx=2)

        ttk.Button(
            env_toolbar1,
            text="➕ 添加物体",
            command=self.add_new_object,
            width=12
        ).pack(side=tk.LEFT, padx=2)

        ttk.Button(
            env_toolbar1,
            text="🏠 创建默认环境",
            command=self.create_default_environment,
            width=15
        ).pack(side=tk.LEFT, padx=2)

        # 环境管理工具栏 - 第二行（新增）
        env_toolbar2 = ttk.Frame(environment_tab)
        env_toolbar2.pack(fill=tk.X, padx=5, pady=(0, 5))

        ttk.Button(
            env_toolbar2,
            text="🔀 切换环境",
            command=self.switch_active_environment_dialog,
            width=12
        ).pack(side=tk.LEFT, padx=2)

        ttk.Button(
            env_toolbar2,
            text="🔗 管理连接",
            command=self.manage_environment_connections,
            width=12
        ).pack(side=tk.LEFT, padx=2)

        ttk.Button(
            env_toolbar2,
            text="🗺️ 关系图",
            command=self.show_environment_relationship_map,
            width=12
        ).pack(side=tk.LEFT, padx=2)

        ttk.Button(
            env_toolbar2,
            text="📋 使用记录",
            command=self.show_vision_logs,
            width=12
        ).pack(side=tk.LEFT, padx=2)

        # 环境管理工具栏 - 第三行（域管理）
        env_toolbar3 = ttk.Frame(environment_tab)
        env_toolbar3.pack(fill=tk.X, padx=5, pady=(0, 5))

        ttk.Label(
            env_toolbar3,
            text="域管理:",
            font=("微软雅黑", 9, "bold")
        ).pack(side=tk.LEFT, padx=5)

        ttk.Button(
            env_toolbar3,
            text="🏘️ 创建域",
            command=self.create_domain_dialog,
            width=12
        ).pack(side=tk.LEFT, padx=2)

        ttk.Button(
            env_toolbar3,
            text="✏️ 编辑域",
            command=self.edit_domain_dialog,
            width=12
        ).pack(side=tk.LEFT, padx=2)

        ttk.Button(
            env_toolbar3,
            text="📍 管理域环境",
            command=self.manage_domain_environments_dialog,
            width=14
        ).pack(side=tk.LEFT, padx=2)

        ttk.Button(
            env_toolbar3,
            text="🎯 切换域",
            command=self.switch_to_domain_dialog,
            width=12
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

        # 选项卡9: 事件管理
        event_tab = ttk.Frame(notebook)
        notebook.add(event_tab, text="📅 事件管理")

        self.create_event_management_panel(event_tab)

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

        # 个性化表达管理
        ttk.Label(control_container, text="个性化表达", font=("微软雅黑", 10, "bold")).pack(anchor=tk.W, pady=5)

        ttk.Button(
            control_container,
            text="🎯 立即学习用户习惯",
            command=self.learn_user_expressions_now,
            width=25
        ).pack(fill=tk.X, pady=2)

        ttk.Button(
            control_container,
            text="➕ 添加智能体表达",
            command=self.add_agent_expression_dialog,
            width=25
        ).pack(fill=tk.X, pady=2)

        ttk.Button(
            control_container,
            text="📋 查看表达风格",
            command=self.show_expression_style,
            width=25
        ).pack(fill=tk.X, pady=2)

        ttk.Separator(control_container, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=10)

        ttk.Label(control_container, text="系统设置", font=("微软雅黑", 10, "bold")).pack(anchor=tk.W, pady=5)

        ttk.Button(
            control_container,
            text="📤 导出智能体配置",
            command=self.export_agent_config,
            width=25
        ).pack(fill=tk.X, pady=2)

        ttk.Button(
            control_container,
            text="📥 导入智能体配置",
            command=self.import_agent_config,
            width=25
        ).pack(fill=tk.X, pady=2)

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

    def create_event_management_panel(self, parent):
        """
        创建事件管理面板

        Args:
            parent: 父容器
        """
        # 主容器
        main_container = ttk.Frame(parent, padding=10)
        main_container.pack(fill=tk.BOTH, expand=True)

        # 顶部工具栏
        toolbar = ttk.Frame(main_container)
        toolbar.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(toolbar, text="事件管理系统", font=("微软雅黑", 12, "bold")).pack(side=tk.LEFT, padx=5)

        ttk.Button(
            toolbar,
            text="➕ 新建事件",
            command=self.create_new_event,
            width=12
        ).pack(side=tk.LEFT, padx=5)

        ttk.Button(
            toolbar,
            text="🔄 刷新列表",
            command=self.refresh_event_list,
            width=12
        ).pack(side=tk.LEFT, padx=5)
        ttk.Button(
            toolbar,
            text="🚀 触发事件",
            command=self.trigger_selected_event,
            width=15
        ).pack(side=tk.LEFT, padx=5)

        ttk.Button(
            toolbar,
            text="📝 查看详情",
            command=self.view_event_details,
            width=15
        ).pack(side=tk.LEFT, padx=5)

        ttk.Button(
            toolbar,
            text="🗑️ 删除事件",
            command=self.delete_selected_event,
            width=15
        ).pack(side=tk.LEFT, padx=5)
        
        # 事件统计
        stats_frame = ttk.LabelFrame(main_container, text="📊 事件统计", padding=10)
        stats_frame.pack(fill=tk.X, pady=(0, 10))

        self.event_stats_label = ttk.Label(
            stats_frame,
            text="加载中...",
            font=("微软雅黑", 9)
        )
        self.event_stats_label.pack(anchor=tk.W)

        # 事件列表容器
        list_frame = ttk.LabelFrame(main_container, text="📋 事件列表", padding=5)
        list_frame.pack(fill=tk.BOTH, expand=True)

        # 创建Treeview显示事件列表
        columns = ('标题', '类型', '优先级', '状态', '创建时间')
        self.event_tree = ttk.Treeview(
            list_frame,
            columns=columns,
            show='tree headings',
            selectmode='browse'
        )

        # 设置列标题
        self.event_tree.heading('#0', text='ID')
        for col in columns:
            self.event_tree.heading(col, text=col)

        # 设置列宽 - 优化以更好显示内容
        self.event_tree.column('#0', width=100, minwidth=80, stretch=False)
        self.event_tree.column('标题', width=300, minwidth=200, stretch=True)
        self.event_tree.column('类型', width=80, minwidth=60, stretch=False)
        self.event_tree.column('优先级', width=80, minwidth=60, stretch=False)
        self.event_tree.column('状态', width=80, minwidth=60, stretch=False)
        self.event_tree.column('创建时间', width=160, minwidth=140, stretch=False)

        # 滚动条
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.event_tree.yview)
        self.event_tree.configure(yscrollcommand=scrollbar.set)

        self.event_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 为事件树添加鼠标悬停提示
        def get_event_tooltip(item_id, values, tags):
            """获取事件的工具提示文本"""
            if values and tags:
                tooltip_text = f"标题: {values[0]}\n"
                tooltip_text += f"类型: {values[1]}\n"
                tooltip_text += f"优先级: {values[2]}\n"
                tooltip_text += f"状态: {values[3]}\n"
                tooltip_text += f"创建时间: {values[4]}\n"
                tooltip_text += f"完整ID: {tags[0] if tags else 'N/A'}"
                return tooltip_text
            return None
        
        create_treeview_tooltip(self.event_tree, get_event_tooltip)

        
    def refresh_event_list(self):
        """刷新事件列表"""
        if not self.agent:
            return
        
        # 检查 event_tree 是否存在
        if not hasattr(self, 'event_tree'):
            return

        try:
            # 清空现有列表
            for item in self.event_tree.get_children():
                self.event_tree.delete(item)

            # 获取所有事件
            from event_manager import EventType, EventStatus
            all_events = self.agent.event_manager.get_all_events(limit=100)

            # 类型和状态的中文映射
            type_map = {
                EventType.NOTIFICATION.value: '通知',
                EventType.TASK.value: '任务'
            }
            
            status_map = {
                EventStatus.PENDING.value: '待处理',
                EventStatus.PROCESSING.value: '处理中',
                EventStatus.COMPLETED.value: '已完成',
                EventStatus.FAILED.value: '失败',
                EventStatus.CANCELLED.value: '已取消'
            }

            priority_map = {1: '低', 2: '中', 3: '高', 4: '紧急'}

            # 添加事件到列表
            for event in all_events:
                event_dict = event.to_dict()
                self.event_tree.insert(
                    '',
                    'end',
                    text=event_dict['event_id'][:8],  # 只显示前8位ID
                    values=(
                        event_dict['title'],
                        type_map.get(event_dict['event_type'], event_dict['event_type']),
                        priority_map.get(event_dict['priority'], event_dict['priority']),
                        status_map.get(event_dict['status'], event_dict['status']),
                        event_dict['created_at'][:19]  # 只显示日期时间部分
                    ),
                    tags=(event_dict['event_id'],)  # 将完整ID存在tags中
                )

            # 更新统计信息
            if hasattr(self, 'event_stats_label'):
                stats = self.agent.event_manager.get_statistics()
                stats_text = f"""总事件数：{stats['total_events']}
待处理：{stats['pending']}  |  处理中：{stats['processing']}  |  已完成：{stats['completed']}
通知型：{stats['notifications']}  |  任务型：{stats['tasks']}"""
                self.event_stats_label.config(text=stats_text)
        except Exception as e:
            print(f"刷新事件列表时出错: {e}")
            import traceback
            traceback.print_exc()
    
    def create_new_event(self):
        """创建新事件对话框"""
        from event_manager import EventType, EventPriority

        dialog = tk.Toplevel(self.root)
        dialog.title("创建新事件")
        dialog.geometry("500x600")
        dialog.transient(self.root)
        dialog.grab_set()

        # 主容器
        container = ttk.Frame(dialog, padding=20)
        container.pack(fill=tk.BOTH, expand=True)

        # 事件标题
        ttk.Label(container, text="事件标题:", font=("微软雅黑", 10)).pack(anchor=tk.W, pady=(0, 5))
        title_entry = ttk.Entry(container, font=("微软雅黑", 10))
        title_entry.pack(fill=tk.X, pady=(0, 10))

        # 事件描述
        ttk.Label(container, text="事件描述:", font=("微软雅黑", 10)).pack(anchor=tk.W, pady=(0, 5))
        desc_text = scrolledtext.ScrolledText(container, height=5, font=("微软雅黑", 9))
        desc_text.pack(fill=tk.X, pady=(0, 10))

        # 事件类型
        ttk.Label(container, text="事件类型:", font=("微软雅黑", 10)).pack(anchor=tk.W, pady=(0, 5))
        type_var = tk.StringVar(value="notification")
        type_frame = ttk.Frame(container)
        type_frame.pack(fill=tk.X, pady=(0, 10))
        ttk.Radiobutton(
            type_frame,
            text="通知型（向用户说明信息）",
            variable=type_var,
            value="notification"
        ).pack(anchor=tk.W)
        ttk.Radiobutton(
            type_frame,
            text="任务型（需要完成任务）",
            variable=type_var,
            value="task"
        ).pack(anchor=tk.W)

        # 优先级
        ttk.Label(container, text="优先级:", font=("微软雅黑", 10)).pack(anchor=tk.W, pady=(0, 5))
        priority_var = tk.IntVar(value=2)
        priority_frame = ttk.Frame(container)
        priority_frame.pack(fill=tk.X, pady=(0, 10))
        for val, text in [(1, "低"), (2, "中"), (3, "高"), (4, "紧急")]:
            ttk.Radiobutton(
                priority_frame,
                text=text,
                variable=priority_var,
                value=val
            ).pack(side=tk.LEFT, padx=5)

        # 任务特定字段（只在任务型时显示）
        task_frame = ttk.LabelFrame(container, text="任务专用字段", padding=10)
        
        ttk.Label(task_frame, text="任务要求:", font=("微软雅黑", 9)).pack(anchor=tk.W, pady=(0, 5))
        task_req_text = scrolledtext.ScrolledText(task_frame, height=3, font=("微软雅黑", 9))
        task_req_text.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(task_frame, text="完成标准:", font=("微软雅黑", 9)).pack(anchor=tk.W, pady=(0, 5))
        task_crit_text = scrolledtext.ScrolledText(task_frame, height=3, font=("微软雅黑", 9))
        task_crit_text.pack(fill=tk.X, pady=(0, 10))

        def toggle_task_fields():
            if type_var.get() == "task":
                task_frame.pack(fill=tk.X, pady=(0, 10))
            else:
                task_frame.pack_forget()

        # 绑定类型变化事件
        type_frame.winfo_children()[0].configure(command=toggle_task_fields)
        type_frame.winfo_children()[1].configure(command=toggle_task_fields)

        # 按钮
        button_frame = ttk.Frame(container)
        button_frame.pack(pady=(10, 0))

        def do_create():
            title = title_entry.get().strip()
            if not title:
                messagebox.showwarning("警告", "请输入事件标题！")
                return

            description = desc_text.get("1.0", tk.END).strip()
            event_type = EventType.TASK if type_var.get() == "task" else EventType.NOTIFICATION
            priority = EventPriority(priority_var.get())

            task_requirements = ""
            completion_criteria = ""
            if event_type == EventType.TASK:
                task_requirements = task_req_text.get("1.0", tk.END).strip()
                completion_criteria = task_crit_text.get("1.0", tk.END).strip()

            try:
                # 创建事件
                event = self.agent.event_manager.create_event(
                    title=title,
                    description=description,
                    event_type=event_type,
                    priority=priority,
                    task_requirements=task_requirements,
                    completion_criteria=completion_criteria
                )

                messagebox.showinfo("成功", f"事件创建成功！\nID: {event.event_id[:8]}...")
                self.refresh_event_list()
                dialog.destroy()

            except Exception as e:
                messagebox.showerror("错误", f"创建事件失败：{str(e)}")

        ttk.Button(button_frame, text="创建", command=do_create, width=15).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="取消", command=dialog.destroy, width=15).pack(side=tk.LEFT, padx=5)

    def trigger_selected_event(self):
        """触发选中的事件"""
        selection = self.event_tree.selection()
        if not selection:
            messagebox.showwarning("警告", "请先选择一个事件！")
            return

        # 获取完整的事件ID（从tags中）
        item_tags = self.event_tree.item(selection[0], 'tags')
        if not item_tags:
            messagebox.showerror("错误", "无法获取事件ID！")
            return

        event_id = item_tags[0]

        # 确认
        event = self.agent.event_manager.get_event(event_id)
        if not event:
            messagebox.showerror("错误", "事件不存在！")
            return

        from event_manager import EventStatus
        if event.status != EventStatus.PENDING:
            result = messagebox.askyesno(
                "确认",
                f"事件状态为「{event.status.value}」\n确定要重新触发吗？"
            )
            if not result:
                return

        # 在新线程中处理事件
        def process_event_thread():
            try:
                self.update_status("处理事件中...", "orange")
                self.is_processing = True

                # 设置中断性提问的回调 - 使用线程安全的方式
                def question_callback(question):
                    # 使用事件和共享变量在主线程安全地显示对话框并获取结果
                    result_event = threading.Event()
                    result_holder = {"answer": ""}
                    
                    def ask_on_main_thread():
                        answer = simpledialog.askstring(
                            "智能体提问",
                            question,
                            parent=self.root
                        )
                        result_holder["answer"] = answer or ""
                        result_event.set()
                    
                    self.root.after(0, ask_on_main_thread)
                    result_event.wait()
                    return result_holder["answer"]

                self.agent.interrupt_question_tool.set_question_callback(question_callback)

                # 处理事件
                result_message = self.agent.handle_event(event_id)

                # 在聊天区域显示结果
                self.root.after(0, lambda: self.add_system_message(result_message))

                self.is_processing = False
                self.update_status("就绪", "green")
                
                # 刷新事件列表
                self.root.after(0, self.refresh_event_list)
            
            except Exception as e:
                # 出错时的处理
                error_msg = f"处理事件时发生错误：{str(e)}"
                print(error_msg)
                import traceback
                traceback.print_exc()
                
                self.is_processing = False
                self.update_status("错误", "red")
                
                # 在主线程显示错误消息
                self.root.after(0, lambda: messagebox.showerror("处理错误", error_msg))

        import threading
        thread = threading.Thread(target=process_event_thread)
        thread.daemon = True
        thread.start()

    def view_event_details(self):
        """查看事件详情"""
        selection = self.event_tree.selection()
        if not selection:
            messagebox.showwarning("警告", "请先选择一个事件！")
            return

        item_tags = self.event_tree.item(selection[0], 'tags')
        if not item_tags:
            messagebox.showerror("错误", "无法获取事件ID！")
            return

        event_id = item_tags[0]
        event = self.agent.event_manager.get_event(event_id)

        if not event:
            messagebox.showerror("错误", "事件不存在！")
            return

        # 创建详情对话框
        dialog = tk.Toplevel(self.root)
        dialog.title(f"事件详情 - {event.title}")
        dialog.geometry("600x700")
        dialog.transient(self.root)

        container = ttk.Frame(dialog, padding=20)
        container.pack(fill=tk.BOTH, expand=True)

        # 事件基本信息
        info_frame = ttk.LabelFrame(container, text="基本信息", padding=10)
        info_frame.pack(fill=tk.X, pady=(0, 10))

        event_dict = event.to_dict()
        info_text = f"""事件ID: {event_dict['event_id']}
标题: {event_dict['title']}
类型: {event_dict['event_type']}
优先级: {event_dict['priority']}
状态: {event_dict['status']}
创建时间: {event_dict['created_at']}

描述:
{event_dict['description']}"""

        from event_manager import EventType
        if event.event_type == EventType.TASK:
            info_text += f"""

任务要求:
{event_dict['metadata'].get('task_requirements', '')}

完成标准:
{event_dict['metadata'].get('completion_criteria', '')}"""

        info_label = ttk.Label(
            info_frame,
            text=info_text,
            font=("微软雅黑", 9),
            justify=tk.LEFT
        )
        info_label.pack(anchor=tk.W)

        # 处理日志
        log_frame = ttk.LabelFrame(container, text="处理日志", padding=10)
        log_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        log_text = scrolledtext.ScrolledText(
            log_frame,
            wrap=tk.WORD,
            font=("微软雅黑", 9),
            height=15
        )
        log_text.pack(fill=tk.BOTH, expand=True)

        logs = self.agent.event_manager.get_event_logs(event_id)
        if logs:
            for log in logs:
                log_text.insert(tk.END, f"[{log['created_at']}] {log['log_type']}\n")
                log_text.insert(tk.END, f"{log['log_content']}\n\n")
        else:
            log_text.insert(tk.END, "暂无处理日志")

        log_text.config(state=tk.DISABLED)

        # 关闭按钮
        ttk.Button(
            container,
            text="关闭",
            command=dialog.destroy,
            width=15
        ).pack(pady=(10, 0))

    def delete_selected_event(self):
        """删除选中的事件"""
        selection = self.event_tree.selection()
        if not selection:
            messagebox.showwarning("警告", "请先选择一个事件！")
            return

        item_tags = self.event_tree.item(selection[0], 'tags')
        if not item_tags:
            messagebox.showerror("错误", "无法获取事件ID！")
            return

        event_id = item_tags[0]
        event = self.agent.event_manager.get_event(event_id)

        if not event:
            messagebox.showerror("错误", "事件不存在！")
            return

        # 确认删除
        result = messagebox.askyesno(
            "确认删除",
            f"确定要删除事件「{event.title}」吗？\n此操作不可恢复！"
        )

        if result:
            success = self.agent.event_manager.delete_event(event_id)
            if success:
                messagebox.showinfo("成功", "事件已删除")
                self.refresh_event_list()
            else:
                messagebox.showerror("错误", "删除事件失败！")

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
            
            # 刷新事件列表
            self.refresh_event_list()

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
            # 简化显示文本，主要信息在第一行
            info_text = f"姓名: {char_info['name']} | 性别: {char_info['gender']} | 身份: {char_info['role']} | 年龄: {char_info['age']}岁\n"
            info_text += f"性格: {char_info['personality'][:50]}{'...' if len(char_info['personality']) > 50 else ''}"
            
            # 完整信息用于工具提示
            full_info = f"姓名: {char_info['name']}\n"
            full_info += f"性别: {char_info['gender']}\n"
            full_info += f"身份: {char_info['role']}\n"
            full_info += f"年龄: {char_info['age']}岁\n"
            full_info += f"身高: {char_info['height']}\n"
            full_info += f"体重: {char_info['weight']}\n"
            full_info += f"性格: {char_info['personality']}\n"
            full_info += f"背景: {char_info.get('background', '未设置')}\n"
            full_info += f"爱好: {char_info.get('hobbies', '未设置')}"

            self.character_label.config(text=info_text)
            
            # 更新工具提示
            if self.character_tooltip:
                self.character_tooltip.update_text(full_info)
            else:
                self.character_tooltip = ToolTip(self.character_label, full_info, delay=500, wraplength=500)

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
        base_kb_count = stats['knowledge_base'].get('total_base_knowledge', 0)
        
        # 优化状态文本，更紧凑
        status_text = f"短期: {stats['short_term']['rounds']}轮 | 长期: {stats['long_term']['total_summaries']}主题 | 知识: {stats['knowledge_base']['total_knowledge']}条"
        if base_kb_count > 0:
            status_text += f" | 基础: {base_kb_count}条"
        
        self.memory_status_label.config(text=status_text)
        
        # 添加完整信息工具提示
        full_info = f"短期记忆:\n"
        full_info += f"  - 对话轮数: {stats['short_term']['rounds']}\n"
        full_info += f"  - 消息数量: {stats['short_term']['total_messages']}\n\n"
        full_info += f"长期记忆:\n"
        full_info += f"  - 主题概括: {stats['long_term']['total_summaries']} 个\n"
        full_info += f"  - 总轮数: {stats['long_term']['total_archived_rounds']}\n"
        full_info += f"  - 总消息: {stats['long_term']['total_archived_messages']}\n\n"
        full_info += f"知识库:\n"
        full_info += f"  - 普通知识: {stats['knowledge_base']['total_knowledge']} 条\n"
        full_info += f"  - 基础知识: {base_kb_count} 条\n"
        full_info += f"  - 主体数量: {stats['knowledge_base'].get('total_entities', 0)}"
        
        # 更新或创建工具提示
        if not hasattr(self, 'memory_status_tooltip'):
            self.memory_status_tooltip = ToolTip(self.memory_status_label, full_info, delay=500, wraplength=300)
        else:
            self.memory_status_tooltip.update_text(full_info)

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
            status_dist = stats.get('status_distribution', {})
            text.append(f"基础知识: {stats.get('base_knowledge_facts', 0)} 条 (优先级100%) | "
                       f"主体数: {stats.get('total_entities', 0)} | "
                       f"定义: {stats.get('total_definitions', 0)} | "
                       f"相关信息: {stats.get('total_related_info', 0)}")
            if status_dist:
                text.append(f"知识状态: 确认 {status_dist.get('确认', 0)} 条 | "
                           f"疑似 {status_dist.get('疑似', 0)} 条")

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
                    
                    # 显示状态和提及次数
                    status = info.get('status', DatabaseManager.STATUS_SUSPECTED)
                    mention_count = info.get('mention_count', 1)
                    status_icon = "✓" if status == DatabaseManager.STATUS_CONFIRMED else "?"
                    status_text = f"{status_icon} {status}"
                    if status == DatabaseManager.STATUS_SUSPECTED:
                        status_text += f" (提及×{mention_count})"
                    
                    text.append(f"    {confidence_icon} [{info.get('type', '其他')}] {status_text} (置信度: {confidence:.2f})")
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
                
                # 显示状态信息（如果不是定义）
                if not is_def:
                    status = item.get('status', DatabaseManager.STATUS_SUSPECTED)
                    mention_count = item.get('mention_count', 1)
                    status_icon = "✓" if status == DatabaseManager.STATUS_CONFIRMED else "?"
                    status_text = f"{status_icon} {status}"
                    if status == DatabaseManager.STATUS_SUSPECTED:
                        status_text += f" (提及×{mention_count})"
                    text.append(f"     状态: {status_text}")
                
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
                
                # 显示状态信息（如果不是定义）
                if not is_def:
                    status = item.get('status', DatabaseManager.STATUS_SUSPECTED)
                    mention_count = item.get('mention_count', 1)
                    status_icon = "✓" if status == DatabaseManager.STATUS_CONFIRMED else "?"
                    status_text = f"{status_icon} {status}"
                    if status == DatabaseManager.STATUS_SUSPECTED:
                        status_text += f" (提及×{mention_count})"
                    text.append(f"     状态: {status_text}")
                
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

    def export_agent_config(self):
        """
        导出智能体配置
        """
        try:
            # 打开文件对话框选择保存位置
            file_path = filedialog.asksaveasfilename(
                title="导出智能体配置",
                defaultextension=".json",
                filetypes=[("JSON文件", "*.json"), ("所有文件", "*.*")],
                initialfile=f"agent_config_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            )
            
            if not file_path:
                return  # 用户取消
            
            # 创建配置管理器并导出
            config_manager = AgentConfigManager(db_manager=self.agent.db)
            
            # 显示进度提示
            self.update_system_info("正在导出配置...")
            
            # 执行导出
            success = config_manager.export_config(file_path)
            
            if success:
                messagebox.showinfo(
                    "导出成功",
                    f"智能体配置已导出到:\n{file_path}\n\n"
                    "该配置包含:\n"
                    "- 环境变量设置\n"
                    "- 环境描述和物体\n"
                    "- 基础知识库\n"
                    "- 智能体表达风格"
                )
                self.update_system_info("配置导出成功")
            else:
                messagebox.showerror("导出失败", "导出配置时发生错误，请查看控制台日志")
                self.update_system_info("配置导出失败")
        
        except Exception as e:
            messagebox.showerror("错误", f"导出配置时出错:\n{str(e)}")
            self.update_system_info(f"配置导出错误: {str(e)}")
    
    def import_agent_config(self):
        """
        导入智能体配置
        """
        try:
            # 打开文件对话框选择要导入的文件
            file_path = filedialog.askopenfilename(
                title="导入智能体配置",
                filetypes=[("JSON文件", "*.json"), ("所有文件", "*.*")]
            )
            
            if not file_path:
                return  # 用户取消
            
            # 询问是否覆盖现有配置
            overwrite = messagebox.askyesno(
                "导入模式",
                "是否覆盖现有配置?\n\n"
                "选择「是」: 覆盖已存在的配置项\n"
                "选择「否」: 只添加新配置，保留已存在的配置\n\n"
                "注意: 环境变量将保存到新文件，需要手动替换"
            )
            
            # 创建配置管理器并导入
            config_manager = AgentConfigManager(db_manager=self.agent.db)
            
            # 显示进度提示
            self.update_system_info("正在导入配置...")
            
            # 执行导入
            success = config_manager.import_config(file_path, overwrite=overwrite)
            
            if success:
                result_msg = (
                    f"智能体配置已导入!\n\n"
                    "导入内容:\n"
                    "- 环境描述和物体\n"
                    "- 基础知识库\n"
                    "- 智能体表达风格\n"
                )
                
                if not overwrite:
                    result_msg += "\n⚠️ 环境变量已保存到 .env.new 文件\n请手动检查并重命名为 .env"
                
                result_msg += "\n\n建议重新加载代理以应用新配置"
                
                messagebox.showinfo("导入成功", result_msg)
                self.update_system_info("配置导入成功")
                
                # 刷新显示
                self.refresh_all()
            else:
                messagebox.showerror("导入失败", "导入配置时发生错误，请查看控制台日志")
                self.update_system_info("配置导入失败")
        
        except Exception as e:
            messagebox.showerror("错误", f"导入配置时出错:\n{str(e)}")
            self.update_system_info(f"配置导入错误: {str(e)}")

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
            # 获取所有环境和域
            environments = self.agent.db.get_all_environments()
            domains = self.agent.db.get_all_domains()
            active_env = self.agent.db.get_active_environment()
            
            display_text = "【智能体视觉环境配置】\n\n"
            
            # 显示域信息
            if domains:
                display_text += f"📊 域(Domain)总览: {len(domains)} 个\n"
                display_text += "=" * 60 + "\n\n"
                
                for domain in domains:
                    domain_envs = self.agent.db.get_domain_environments(domain['uuid'])
                    default_env = None
                    if domain.get('default_environment_uuid'):
                        default_env = self.agent.db.get_environment(domain['default_environment_uuid'])
                    
                    display_text += f"🏘️ 【域: {domain['name']}】\n"
                    display_text += f"描述: {domain.get('description', '无描述')}\n"
                    display_text += f"包含环境: {len(domain_envs)} 个\n"
                    if default_env:
                        display_text += f"默认环境: {default_env['name']}\n"
                    
                    if domain_envs:
                        display_text += "环境列表: "
                        display_text += ", ".join([e['name'] for e in domain_envs])
                        display_text += "\n"
                    
                    display_text += "\n"
                
                display_text += "=" * 60 + "\n\n"
            
            # 显示环境信息
            if not environments:
                display_text += "暂无环境配置。\n\n"
                display_text += "💡 提示:\n"
                display_text += "- 点击「创建默认环境」快速创建一个示例环境\n"
                display_text += "- 点击「新建环境」手动创建自定义环境\n"
                display_text += "- 环境配置后，当用户询问周围环境时，智能体会自动使用视觉工具\n"
            else:
                display_text += f"📍 环境总览: {len(environments)} 个环境\n"
                if active_env:
                    display_text += f"当前激活: {active_env['name']}\n"
                    
                    # 显示当前环境所属的域
                    current_domains = self.agent.db.get_environment_domains(active_env['uuid'])
                    if current_domains:
                        display_text += f"所属域: {', '.join([d['name'] for d in current_domains])}\n"
                
                display_text += "=" * 60 + "\n\n"
                
                for env in environments:
                    is_active = env['uuid'] == active_env['uuid'] if active_env else False
                    status_icon = "🟢" if is_active else "⚪"
                    
                    display_text += f"{status_icon} 【环境: {env['name']}】\n"
                    display_text += f"UUID: {env['uuid'][:8]}...\n"
                    display_text += f"整体描述: {env['overall_description']}\n"
                    
                    # 显示环境所属的域
                    env_domains = self.agent.db.get_environment_domains(env['uuid'])
                    if env_domains:
                        display_text += f"所属域: {', '.join([d['name'] for d in env_domains])}\n"
                    
                    if env.get('atmosphere'):
                        display_text += f"氛围: {env['atmosphere']}\n"
                    if env.get('lighting'):
                        display_text += f"光照: {env['lighting']}\n"
                    if env.get('sounds'):
                        display_text += f"声音: {env['sounds']}\n"
                    if env.get('smells'):
                        display_text += f"气味: {env['smells']}\n"
                    
                    display_text += f"创建时间: {env['created_at']}\n"
                    
                    # 获取环境连接信息
                    connections = self.agent.db.get_environment_connections(env['uuid'])
                    if connections:
                        display_text += f"\n连接关系: {len(connections)}个\n"
                        for conn in connections[:3]:  # 只显示前3个连接
                            if conn['from_environment_uuid'] == env['uuid']:
                                other_env = self.agent.db.get_environment(conn['to_environment_uuid'])
                                direction_symbol = "→" if conn['direction'] == 'one_way' else "⟷"
                                display_text += f"  {direction_symbol} {other_env['name'] if other_env else '未知'} ({conn['connection_type']})\n"
                            elif conn['to_environment_uuid'] == env['uuid'] and conn['direction'] == 'bidirectional':
                                other_env = self.agent.db.get_environment(conn['from_environment_uuid'])
                                display_text += f"  ⟷ {other_env['name'] if other_env else '未知'} ({conn['connection_type']})\n"
                        if len(connections) > 3:
                            display_text += f"  ... 还有 {len(connections) - 3} 个连接\n"
                    else:
                        display_text += "\n连接关系: 无（孤立环境）\n"
                    
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

    def manage_environment_connections(self):
        """
        管理环境连接关系
        """
        # 创建对话框
        dialog = tk.Toplevel(self.root)
        dialog.title("环境连接管理")
        dialog.geometry("900x600")
        dialog.transient(self.root)
        
        # 标题
        title_label = ttk.Label(
            dialog,
            text="🔗 环境连接管理",
            font=("微软雅黑", 12, "bold")
        )
        title_label.pack(pady=10)
        
        # 工具栏
        toolbar = ttk.Frame(dialog)
        toolbar.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Button(
            toolbar,
            text="➕ 新建连接",
            command=self.create_environment_connection_dialog,
            width=15
        ).pack(side=tk.LEFT, padx=2)
        
        ttk.Button(
            toolbar,
            text="🔄 刷新",
            command=lambda: self.refresh_connections_display(connections_text),
            width=10
        ).pack(side=tk.LEFT, padx=2)
        
        ttk.Button(
            toolbar,
            text="🗺️ 查看关系图",
            command=self.show_environment_relationship_map,
            width=15
        ).pack(side=tk.LEFT, padx=2)
        
        # 连接列表显示区域
        connections_text = scrolledtext.ScrolledText(
            dialog,
            wrap=tk.WORD,
            font=("微软雅黑", 9),
            bg="#f9f9f9"
        )
        connections_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 初始加载
        self.refresh_connections_display(connections_text)
        
        # 关闭按钮
        ttk.Button(dialog, text="关闭", command=dialog.destroy, width=15).pack(pady=10)

    def refresh_connections_display(self, text_widget):
        """
        刷新连接显示
        """
        try:
            text_widget.config(state=tk.NORMAL)
            text_widget.delete(1.0, tk.END)
            
            connections = self.agent.db.get_all_environment_connections()
            
            if not connections:
                text_widget.insert(tk.END, "暂无环境连接。\n\n")
                text_widget.insert(tk.END, "💡 提示: 点击「新建连接」创建环境之间的连接关系。")
            else:
                text_widget.insert(tk.END, f"共有 {len(connections)} 个环境连接\n")
                text_widget.insert(tk.END, "=" * 80 + "\n\n")
                
                for i, conn in enumerate(connections, 1):
                    from_env = self.agent.db.get_environment(conn['from_environment_uuid'])
                    to_env = self.agent.db.get_environment(conn['to_environment_uuid'])
                    
                    text_widget.insert(tk.END, f"【连接 {i}】\n")
                    text_widget.insert(tk.END, f"UUID: {conn['uuid'][:8]}...\n")
                    text_widget.insert(tk.END, f"起点: {from_env['name'] if from_env else '未知'}\n")
                    text_widget.insert(tk.END, f"终点: {to_env['name'] if to_env else '未知'}\n")
                    
                    # 方向图示
                    if conn['direction'] == 'bidirectional':
                        direction_str = f"{from_env['name'] if from_env else '?'} ⟷ {to_env['name'] if to_env else '?'}"
                    else:
                        direction_str = f"{from_env['name'] if from_env else '?'} → {to_env['name'] if to_env else '?'}"
                    text_widget.insert(tk.END, f"方向: {direction_str}\n")
                    
                    text_widget.insert(tk.END, f"类型: {conn['connection_type']}\n")
                    if conn.get('description'):
                        text_widget.insert(tk.END, f"描述: {conn['description']}\n")
                    text_widget.insert(tk.END, f"创建时间: {conn['created_at']}\n")
                    text_widget.insert(tk.END, "\n" + "-" * 80 + "\n\n")
            
            text_widget.config(state=tk.DISABLED)
        except Exception as e:
            text_widget.config(state=tk.NORMAL)
            text_widget.insert(tk.END, f"刷新连接显示时出错: {e}")
            text_widget.config(state=tk.DISABLED)

    def create_environment_connection_dialog(self):
        """
        创建环境连接对话框
        """
        # 获取所有环境
        environments = self.agent.db.get_all_environments()
        if len(environments) < 2:
            messagebox.showerror("错误", "至少需要2个环境才能创建连接！\n请先创建更多环境。")
            return
        
        # 创建对话框
        dialog = tk.Toplevel(self.root)
        dialog.title("创建环境连接")
        dialog.geometry("500x450")
        dialog.transient(self.root)
        dialog.grab_set()
        
        # 起始环境
        ttk.Label(dialog, text="起始环境:", font=("微软雅黑", 10)).pack(pady=(10, 0), padx=10, anchor=tk.W)
        from_env_var = tk.StringVar()
        from_env_combo = ttk.Combobox(dialog, textvariable=from_env_var, width=50, state="readonly")
        from_env_combo['values'] = [f"{env['name']} ({env['uuid'][:8]}...)" for env in environments]
        from_env_combo.pack(pady=5, padx=10, fill=tk.X)
        
        # 目标环境
        ttk.Label(dialog, text="目标环境:", font=("微软雅黑", 10)).pack(pady=(10, 0), padx=10, anchor=tk.W)
        to_env_var = tk.StringVar()
        to_env_combo = ttk.Combobox(dialog, textvariable=to_env_var, width=50, state="readonly")
        to_env_combo['values'] = [f"{env['name']} ({env['uuid'][:8]}...)" for env in environments]
        to_env_combo.pack(pady=5, padx=10, fill=tk.X)
        
        # 连接类型
        ttk.Label(dialog, text="连接类型:", font=("微软雅黑", 10)).pack(pady=(10, 0), padx=10, anchor=tk.W)
        conn_type_var = tk.StringVar(value="normal")
        conn_type_combo = ttk.Combobox(dialog, textvariable=conn_type_var, width=50, state="readonly")
        conn_type_combo['values'] = ['normal', 'door', 'portal', 'stairs', 'corridor', 'window', 'other']
        conn_type_combo.pack(pady=5, padx=10, fill=tk.X)
        
        # 方向
        ttk.Label(dialog, text="连接方向:", font=("微软雅黑", 10)).pack(pady=(10, 0), padx=10, anchor=tk.W)
        direction_var = tk.StringVar(value="bidirectional")
        direction_frame = ttk.Frame(dialog)
        direction_frame.pack(pady=5, padx=10, fill=tk.X)
        ttk.Radiobutton(direction_frame, text="双向 (⟷)", variable=direction_var, value="bidirectional").pack(side=tk.LEFT, padx=10)
        ttk.Radiobutton(direction_frame, text="单向 (→)", variable=direction_var, value="one_way").pack(side=tk.LEFT, padx=10)
        
        # 描述
        ttk.Label(dialog, text="连接描述:", font=("微软雅黑", 10)).pack(pady=(10, 0), padx=10, anchor=tk.W)
        desc_text = scrolledtext.ScrolledText(dialog, height=4, width=50, wrap=tk.WORD)
        desc_text.pack(pady=5, padx=10, fill=tk.BOTH, expand=True)
        
        # 按钮
        button_frame = ttk.Frame(dialog)
        button_frame.pack(pady=20)
        
        def save_connection():
            from_idx = from_env_combo.current()
            to_idx = to_env_combo.current()
            
            if from_idx < 0 or to_idx < 0:
                messagebox.showerror("错误", "请选择起始环境和目标环境！")
                return
            
            if from_idx == to_idx:
                messagebox.showerror("错误", "起始环境和目标环境不能相同！")
                return
            
            from_env = environments[from_idx]
            to_env = environments[to_idx]
            
            try:
                conn_uuid = self.agent.db.create_environment_connection(
                    from_env_uuid=from_env['uuid'],
                    to_env_uuid=to_env['uuid'],
                    connection_type=conn_type_var.get(),
                    direction=direction_var.get(),
                    description=desc_text.get("1.0", tk.END).strip()
                )
                
                messagebox.showinfo("成功", f"环境连接创建成功！\n\n{from_env['name']} → {to_env['name']}\nUUID: {conn_uuid[:8]}...")
                dialog.destroy()
            except ValueError as e:
                messagebox.showerror("错误", str(e))
            except Exception as e:
                messagebox.showerror("错误", f"创建连接失败: {e}")
        
        ttk.Button(button_frame, text="保存", command=save_connection, width=15).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="取消", command=dialog.destroy, width=15).pack(side=tk.LEFT, padx=5)

    def show_environment_relationship_map(self):
        """
        显示环境关系图
        """
        # 创建对话框
        dialog = tk.Toplevel(self.root)
        dialog.title("环境关系图")
        dialog.geometry("800x600")
        dialog.transient(self.root)
        
        # 标题
        title_label = ttk.Label(
            dialog,
            text="🗺️ 环境关系图",
            font=("微软雅黑", 12, "bold")
        )
        title_label.pack(pady=10)
        
        # 创建Canvas显示关系图
        canvas_frame = ttk.Frame(dialog)
        canvas_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        canvas = Canvas(canvas_frame, bg='#f8f9fa', highlightthickness=0)
        canvas.pack(fill=tk.BOTH, expand=True)
        
        # 绘制关系图
        self.draw_environment_relationship_map(canvas)
        
        # 关闭按钮
        ttk.Button(dialog, text="关闭", command=dialog.destroy, width=15).pack(pady=10)

    def draw_environment_relationship_map(self, canvas):
        """
        在Canvas上绘制环境关系图
        """
        try:
            # 获取所有环境和连接
            environments = self.agent.db.get_all_environments()
            connections = self.agent.db.get_all_environment_connections()
            
            if not environments:
                canvas.create_text(
                    400, 300,
                    text="暂无环境数据",
                    font=('微软雅黑', 12),
                    fill='#999999'
                )
                return
            
            # 计算布局
            width = canvas.winfo_width() if canvas.winfo_width() > 1 else 800
            height = canvas.winfo_height() if canvas.winfo_height() > 1 else 600
            
            # 使用简单的圆形布局
            center_x = width // 2
            center_y = height // 2
            radius = min(width, height) // 3
            
            # 计算每个环境的位置
            env_positions = {}
            angle_step = 2 * 3.14159 / len(environments)
            for i, env in enumerate(environments):
                angle = i * angle_step
                x = center_x + radius * math.cos(angle)
                y = center_y + radius * math.sin(angle)
                env_positions[env['uuid']] = (x, y)
            
            # 绘制连接线
            for conn in connections:
                from_uuid = conn['from_environment_uuid']
                to_uuid = conn['to_environment_uuid']
                
                if from_uuid in env_positions and to_uuid in env_positions:
                    from_pos = env_positions[from_uuid]
                    to_pos = env_positions[to_uuid]
                    
                    # 绘制线条
                    if conn['direction'] == 'bidirectional':
                        canvas.create_line(
                            from_pos[0], from_pos[1],
                            to_pos[0], to_pos[1],
                            fill='#4ECDC4', width=2,
                            arrow=tk.BOTH, arrowshape=(10, 12, 5)
                        )
                    else:
                        canvas.create_line(
                            from_pos[0], from_pos[1],
                            to_pos[0], to_pos[1],
                            fill='#45B7D1', width=2,
                            arrow=tk.LAST, arrowshape=(10, 12, 5)
                        )
            
            # 获取当前激活的环境
            active_env = self.agent.db.get_active_environment()
            active_uuid = active_env['uuid'] if active_env else None
            
            # 绘制环境节点
            for env in environments:
                x, y = env_positions[env['uuid']]
                
                # 节点颜色
                if env['uuid'] == active_uuid:
                    color = '#FF6B6B'  # 激活的环境用红色
                else:
                    color = '#98D8C8'
                
                # 绘制圆形节点
                radius_node = 30
                canvas.create_oval(
                    x - radius_node, y - radius_node,
                    x + radius_node, y + radius_node,
                    fill=color, outline='white', width=3
                )
                
                # 绘制环境名称
                canvas.create_text(
                    x, y + radius_node + 20,
                    text=env['name'],
                    font=('微软雅黑', 9, 'bold'),
                    fill='#333333'
                )
                
                # 如果是激活的环境，添加标记
                if env['uuid'] == active_uuid:
                    canvas.create_text(
                        x, y,
                        text="✓",
                        font=('Arial', 16, 'bold'),
                        fill='white'
                    )
            
            # 添加图例
            legend_x = 20
            legend_y = 20
            canvas.create_text(legend_x, legend_y, text="图例:", font=('微软雅黑', 9, 'bold'), anchor=tk.W)
            canvas.create_oval(legend_x, legend_y + 20, legend_x + 20, legend_y + 40, fill='#FF6B6B', outline='white', width=2)
            canvas.create_text(legend_x + 30, legend_y + 30, text="当前环境", font=('微软雅黑', 8), anchor=tk.W)
            canvas.create_oval(legend_x, legend_y + 50, legend_x + 20, legend_y + 70, fill='#98D8C8', outline='white', width=2)
            canvas.create_text(legend_x + 30, legend_y + 60, text="其他环境", font=('微软雅黑', 8), anchor=tk.W)
            
        except Exception as e:
            canvas.create_text(
                400, 300,
                text=f"绘制关系图时出错: {e}",
                font=('微软雅黑', 10),
                fill='red'
            )

    def switch_active_environment_dialog(self):
        """
        切换当前激活环境的对话框
        """
        # 获取所有环境
        environments = self.agent.db.get_all_environments()
        if not environments:
            messagebox.showerror("错误", "没有可用的环境！\n请先创建环境。")
            return
        
        current_env = self.agent.db.get_active_environment()
        
        # 创建对话框
        dialog = tk.Toplevel(self.root)
        dialog.title("切换环境")
        dialog.geometry("500x400")
        dialog.transient(self.root)
        dialog.grab_set()
        
        ttk.Label(
            dialog,
            text="选择要切换到的环境:",
            font=("微软雅黑", 10, "bold")
        ).pack(pady=10)
        
        if current_env:
            ttk.Label(
                dialog,
                text=f"当前环境: {current_env['name']}",
                font=("微软雅黑", 9),
                foreground="#0066cc"
            ).pack(pady=5)
        
        # 环境列表
        listbox_frame = ttk.Frame(dialog)
        listbox_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        scrollbar = ttk.Scrollbar(listbox_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        env_listbox = tk.Listbox(
            listbox_frame,
            font=("微软雅黑", 9),
            yscrollcommand=scrollbar.set
        )
        env_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=env_listbox.yview)
        
        # 填充环境列表
        env_map = {}
        for i, env in enumerate(environments):
            label = f"{env['name']}"
            if current_env and env['uuid'] == current_env['uuid']:
                label += " (当前)"
            env_listbox.insert(tk.END, label)
            env_map[i] = env
        
        # 按钮
        button_frame = ttk.Frame(dialog)
        button_frame.pack(pady=10)
        
        def do_switch():
            selection = env_listbox.curselection()
            if not selection:
                messagebox.showwarning("警告", "请选择一个环境！")
                return
            
            selected_env = env_map[selection[0]]
            
            # 如果是当前环境，不需要切换
            if current_env and selected_env['uuid'] == current_env['uuid']:
                messagebox.showinfo("提示", "已经在该环境中了！")
                dialog.destroy()
                return
            
            # 如果有当前环境，检查是否可以切换
            if current_env:
                can_switch = self.agent.db.can_move_to_environment(
                    current_env['uuid'],
                    selected_env['uuid']
                )
                if not can_switch:
                    result = messagebox.askyesno(
                        "警告",
                        f"环境「{current_env['name']}」与「{selected_env['name']}」没有建立连接！\n\n是否仍然要切换？"
                    )
                    if not result:
                        return
            
            # 执行切换
            try:
                success = self.agent.db.set_active_environment(selected_env['uuid'])
                if success:
                    messagebox.showinfo("成功", f"已切换到环境: {selected_env['name']}")
                    self.refresh_environment_display()
                    dialog.destroy()
                else:
                    messagebox.showerror("错误", "切换环境失败！")
            except Exception as e:
                messagebox.showerror("错误", f"切换环境时出错: {e}")
        
        ttk.Button(button_frame, text="切换", command=do_switch, width=15).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="取消", command=dialog.destroy, width=15).pack(side=tk.LEFT, padx=5)

    # ==================== 域管理相关方法 ====================

    def create_domain_dialog(self):
        """创建域的对话框"""
        if not self.agent:
            messagebox.showerror("错误", "聊天代理未初始化")
            return

        dialog = tk.Toplevel(self.root)
        dialog.title("创建环境域")
        dialog.geometry("600x450")
        dialog.transient(self.root)
        dialog.grab_set()

        # 标题
        ttk.Label(
            dialog,
            text="创建环境域（Domain）",
            font=("微软雅黑", 12, "bold")
        ).pack(pady=10)

        ttk.Label(
            dialog,
            text="域是多个环境的集合，如'小可家'包含房间、客厅、厨房",
            font=("微软雅黑", 9),
            foreground="#666666"
        ).pack(pady=5)

        # 输入框架
        input_frame = ttk.Frame(dialog)
        input_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)

        # 域名称
        ttk.Label(input_frame, text="域名称:", font=("微软雅黑", 10)).grid(row=0, column=0, sticky=tk.W, pady=10)
        name_entry = ttk.Entry(input_frame, width=50, font=("微软雅黑", 10))
        name_entry.grid(row=0, column=1, pady=10, padx=10, sticky=tk.W+tk.E)

        # 域描述
        ttk.Label(input_frame, text="域描述:", font=("微软雅黑", 10)).grid(row=1, column=0, sticky=tk.NW, pady=10)
        desc_text = scrolledtext.ScrolledText(input_frame, width=50, height=6, wrap=tk.WORD, font=("微软雅黑", 9))
        desc_text.grid(row=1, column=1, pady=10, padx=10, sticky=tk.W+tk.E)

        # 默认环境
        ttk.Label(input_frame, text="默认环境:", font=("微软雅黑", 10)).grid(row=2, column=0, sticky=tk.W, pady=10)
        
        all_envs = self.agent.db.get_all_environments()
        env_names = ["(暂不设置)"] + [env['name'] for env in all_envs]
        env_combo = ttk.Combobox(input_frame, values=env_names, state="readonly", width=47, font=("微软雅黑", 9))
        env_combo.set("(暂不设置)")
        env_combo.grid(row=2, column=1, pady=10, padx=10, sticky=tk.W+tk.E)

        input_frame.columnconfigure(1, weight=1)

        # 按钮
        button_frame = ttk.Frame(dialog)
        button_frame.pack(pady=20)

        def save_domain():
            name = name_entry.get().strip()
            description = desc_text.get("1.0", tk.END).strip()
            default_env_name = env_combo.get()

            if not name:
                messagebox.showwarning("警告", "域名称不能为空！")
                return

            # 获取默认环境UUID
            default_env_uuid = None
            if default_env_name != "(暂不设置)":
                for env in all_envs:
                    if env['name'] == default_env_name:
                        default_env_uuid = env['uuid']
                        break

            try:
                domain_uuid = self.agent.db.create_domain(
                    name=name,
                    description=description,
                    default_environment_uuid=default_env_uuid
                )
                messagebox.showinfo("成功", f"域创建成功！\n域名: {name}")
                self.add_system_message(f"🏘️ 创建了新域: {name}")
                self.refresh_environment_display()
                dialog.destroy()
            except Exception as e:
                messagebox.showerror("错误", f"创建域失败: {str(e)}")

        ttk.Button(button_frame, text="创建", command=save_domain, width=15).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="取消", command=dialog.destroy, width=15).pack(side=tk.LEFT, padx=5)

    def edit_domain_dialog(self):
        """编辑域的对话框"""
        if not self.agent:
            messagebox.showerror("错误", "聊天代理未初始化")
            return

        # 获取所有域
        domains = self.agent.db.get_all_domains()
        if not domains:
            messagebox.showinfo("提示", "还没有创建任何域。\n请先使用'创建域'功能创建域。")
            return

        # 选择域对话框
        select_dialog = tk.Toplevel(self.root)
        select_dialog.title("选择要编辑的域")
        select_dialog.geometry("500x400")
        select_dialog.transient(self.root)
        select_dialog.grab_set()

        ttk.Label(
            select_dialog,
            text="选择要编辑的域:",
            font=("微软雅黑", 10, "bold")
        ).pack(pady=10)

        # 域列表
        listbox_frame = ttk.Frame(select_dialog)
        listbox_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        scrollbar = ttk.Scrollbar(listbox_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        domain_listbox = tk.Listbox(
            listbox_frame,
            font=("微软雅黑", 9),
            yscrollcommand=scrollbar.set
        )
        domain_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=domain_listbox.yview)

        # 填充域列表
        domain_map = {}
        for i, domain in enumerate(domains):
            envs = self.agent.db.get_domain_environments(domain['uuid'])
            label = f"{domain['name']} ({len(envs)}个环境)"
            domain_listbox.insert(tk.END, label)
            domain_map[i] = domain

        def do_edit():
            selection = domain_listbox.curselection()
            if not selection:
                messagebox.showwarning("警告", "请选择一个域！")
                return

            selected_domain = domain_map[selection[0]]
            select_dialog.destroy()
            self._show_edit_domain_form(selected_domain)

        # 按钮
        button_frame = ttk.Frame(select_dialog)
        button_frame.pack(pady=10)

        ttk.Button(button_frame, text="编辑", command=do_edit, width=15).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="取消", command=select_dialog.destroy, width=15).pack(side=tk.LEFT, padx=5)

    def _show_edit_domain_form(self, domain):
        """显示编辑域的表单"""
        dialog = tk.Toplevel(self.root)
        dialog.title(f"编辑域: {domain['name']}")
        dialog.geometry("600x450")
        dialog.transient(self.root)
        dialog.grab_set()

        # 标题
        ttk.Label(
            dialog,
            text=f"编辑域: {domain['name']}",
            font=("微软雅黑", 12, "bold")
        ).pack(pady=10)

        # 输入框架
        input_frame = ttk.Frame(dialog)
        input_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)

        # 域名称
        ttk.Label(input_frame, text="域名称:", font=("微软雅黑", 10)).grid(row=0, column=0, sticky=tk.W, pady=10)
        name_entry = ttk.Entry(input_frame, width=50, font=("微软雅黑", 10))
        name_entry.insert(0, domain['name'])
        name_entry.grid(row=0, column=1, pady=10, padx=10, sticky=tk.W+tk.E)

        # 域描述
        ttk.Label(input_frame, text="域描述:", font=("微软雅黑", 10)).grid(row=1, column=0, sticky=tk.NW, pady=10)
        desc_text = scrolledtext.ScrolledText(input_frame, width=50, height=6, wrap=tk.WORD, font=("微软雅黑", 9))
        desc_text.insert("1.0", domain.get('description', ''))
        desc_text.grid(row=1, column=1, pady=10, padx=10, sticky=tk.W+tk.E)

        # 默认环境
        ttk.Label(input_frame, text="默认环境:", font=("微软雅黑", 10)).grid(row=2, column=0, sticky=tk.W, pady=10)
        
        all_envs = self.agent.db.get_all_environments()
        env_names = ["(暂不设置)"] + [env['name'] for env in all_envs]
        env_combo = ttk.Combobox(input_frame, values=env_names, state="readonly", width=47, font=("微软雅黑", 9))
        
        # 设置当前默认环境
        if domain.get('default_environment_uuid'):
            default_env = self.agent.db.get_environment(domain['default_environment_uuid'])
            if default_env:
                env_combo.set(default_env['name'])
            else:
                env_combo.set("(暂不设置)")
        else:
            env_combo.set("(暂不设置)")
        
        env_combo.grid(row=2, column=1, pady=10, padx=10, sticky=tk.W+tk.E)

        input_frame.columnconfigure(1, weight=1)

        # 按钮
        button_frame = ttk.Frame(dialog)
        button_frame.pack(pady=20)

        def save_changes():
            name = name_entry.get().strip()
            description = desc_text.get("1.0", tk.END).strip()
            default_env_name = env_combo.get()

            if not name:
                messagebox.showwarning("警告", "域名称不能为空！")
                return

            # 获取默认环境UUID
            default_env_uuid = None
            if default_env_name != "(暂不设置)":
                for env in all_envs:
                    if env['name'] == default_env_name:
                        default_env_uuid = env['uuid']
                        break

            try:
                self.agent.db.update_domain(
                    domain['uuid'],
                    name=name,
                    description=description,
                    default_environment_uuid=default_env_uuid
                )
                messagebox.showinfo("成功", f"域更新成功！\n域名: {name}")
                self.add_system_message(f"🏘️ 更新了域: {name}")
                self.refresh_environment_display()
                dialog.destroy()
            except Exception as e:
                messagebox.showerror("错误", f"更新域失败: {str(e)}")

        ttk.Button(button_frame, text="保存", command=save_changes, width=15).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="取消", command=dialog.destroy, width=15).pack(side=tk.LEFT, padx=5)

    def manage_domain_environments_dialog(self):
        """管理域中的环境"""
        if not self.agent:
            messagebox.showerror("错误", "聊天代理未初始化")
            return

        # 获取所有域
        domains = self.agent.db.get_all_domains()
        if not domains:
            messagebox.showinfo("提示", "还没有创建任何域。\n请先使用'创建域'功能创建域。")
            return

        # 选择域对话框
        select_dialog = tk.Toplevel(self.root)
        select_dialog.title("选择要管理的域")
        select_dialog.geometry("500x400")
        select_dialog.transient(self.root)
        select_dialog.grab_set()

        ttk.Label(
            select_dialog,
            text="选择要管理环境的域:",
            font=("微软雅黑", 10, "bold")
        ).pack(pady=10)

        # 域列表
        listbox_frame = ttk.Frame(select_dialog)
        listbox_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        scrollbar = ttk.Scrollbar(listbox_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        domain_listbox = tk.Listbox(
            listbox_frame,
            font=("微软雅黑", 9),
            yscrollcommand=scrollbar.set
        )
        domain_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=domain_listbox.yview)

        # 填充域列表
        domain_map = {}
        for i, domain in enumerate(domains):
            envs = self.agent.db.get_domain_environments(domain['uuid'])
            label = f"{domain['name']} ({len(envs)}个环境)"
            domain_listbox.insert(tk.END, label)
            domain_map[i] = domain

        def do_manage():
            selection = domain_listbox.curselection()
            if not selection:
                messagebox.showwarning("警告", "请选择一个域！")
                return

            selected_domain = domain_map[selection[0]]
            select_dialog.destroy()
            self._show_manage_domain_envs_form(selected_domain)

        # 按钮
        button_frame = ttk.Frame(select_dialog)
        button_frame.pack(pady=10)

        ttk.Button(button_frame, text="管理", command=do_manage, width=15).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="取消", command=select_dialog.destroy, width=15).pack(side=tk.LEFT, padx=5)

    def _show_manage_domain_envs_form(self, domain):
        """显示管理域环境的表单"""
        dialog = tk.Toplevel(self.root)
        dialog.title(f"管理域的环境: {domain['name']}")
        dialog.geometry("800x550")
        dialog.transient(self.root)
        dialog.grab_set()

        # 标题
        ttk.Label(
            dialog,
            text=f"域: {domain['name']}",
            font=("微软雅黑", 12, "bold")
        ).pack(pady=10)

        ttk.Label(
            dialog,
            text=domain.get('description', ''),
            font=("微软雅黑", 9),
            foreground="#666666"
        ).pack(pady=5)

        # 主框架
        main_frame = ttk.Frame(dialog)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # 左侧：域中的环境
        left_frame = ttk.Frame(main_frame)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)

        ttk.Label(left_frame, text="域中的环境:", font=("微软雅黑", 10, "bold")).pack(pady=5)
        
        domain_env_frame = ttk.Frame(left_frame)
        domain_env_frame.pack(fill=tk.BOTH, expand=True)

        scrollbar1 = ttk.Scrollbar(domain_env_frame)
        domain_env_list = tk.Listbox(domain_env_frame, yscrollcommand=scrollbar1.set, font=("微软雅黑", 9))
        scrollbar1.config(command=domain_env_list.yview)
        scrollbar1.pack(side=tk.RIGHT, fill=tk.Y)
        domain_env_list.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # 中间：操作按钮
        middle_frame = ttk.Frame(main_frame)
        middle_frame.pack(side=tk.LEFT, padx=15)

        ttk.Button(middle_frame, text="← 添加", command=lambda: add_to_domain(), width=12).pack(pady=10)
        ttk.Button(middle_frame, text="移除 →", command=lambda: remove_from_domain(), width=12).pack(pady=10)
        ttk.Button(middle_frame, text="🔄 刷新", command=lambda: refresh_lists(), width=12).pack(pady=10)

        # 右侧：所有环境
        right_frame = ttk.Frame(main_frame)
        right_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)

        ttk.Label(right_frame, text="所有环境:", font=("微软雅黑", 10, "bold")).pack(pady=5)
        
        all_env_frame = ttk.Frame(right_frame)
        all_env_frame.pack(fill=tk.BOTH, expand=True)

        scrollbar2 = ttk.Scrollbar(all_env_frame)
        all_env_list = tk.Listbox(all_env_frame, yscrollcommand=scrollbar2.set, font=("微软雅黑", 9))
        scrollbar2.config(command=all_env_list.yview)
        scrollbar2.pack(side=tk.RIGHT, fill=tk.Y)
        all_env_list.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # 存储环境UUID
        domain_env_data = {}
        all_env_data = {}

        def refresh_lists():
            """刷新环境列表"""
            domain_env_list.delete(0, tk.END)
            all_env_list.delete(0, tk.END)
            domain_env_data.clear()
            all_env_data.clear()

            # 获取域中的环境
            domain_envs = self.agent.db.get_domain_environments(domain['uuid'])
            for env in domain_envs:
                domain_env_list.insert(tk.END, env['name'])
                domain_env_data[env['name']] = env['uuid']

            # 获取所有环境（排除已在域中的）
            all_envs = self.agent.db.get_all_environments()
            domain_env_uuids = set(domain_env_data.values())
            for env in all_envs:
                if env['uuid'] not in domain_env_uuids:
                    all_env_list.insert(tk.END, env['name'])
                    all_env_data[env['name']] = env['uuid']

        def add_to_domain():
            """添加环境到域"""
            selection = all_env_list.curselection()
            if not selection:
                messagebox.showwarning("警告", "请先选择一个环境！")
                return

            env_name = all_env_list.get(selection[0])
            env_uuid = all_env_data[env_name]

            try:
                self.agent.db.add_environment_to_domain(domain['uuid'], env_uuid)
                refresh_lists()
                self.add_system_message(f"🏘️ 将环境 '{env_name}' 添加到域 '{domain['name']}'")
                messagebox.showinfo("成功", f"已添加环境 '{env_name}' 到域")
            except Exception as e:
                messagebox.showerror("错误", f"添加失败: {str(e)}")

        def remove_from_domain():
            """从域中移除环境"""
            selection = domain_env_list.curselection()
            if not selection:
                messagebox.showwarning("警告", "请先选择一个环境！")
                return

            env_name = domain_env_list.get(selection[0])
            env_uuid = domain_env_data[env_name]

            result = messagebox.askyesno("确认", f"确定要从域中移除环境 '{env_name}' 吗？")
            if result:
                try:
                    self.agent.db.remove_environment_from_domain(domain['uuid'], env_uuid)
                    refresh_lists()
                    self.add_system_message(f"🏘️ 从域 '{domain['name']}' 移除了环境 '{env_name}'")
                    messagebox.showinfo("成功", f"已从域中移除环境 '{env_name}'")
                except Exception as e:
                    messagebox.showerror("错误", f"移除失败: {str(e)}")

        # 初始加载
        refresh_lists()

        # 底部关闭按钮
        ttk.Button(dialog, text="关闭", command=dialog.destroy, width=15).pack(pady=10)

    def switch_to_domain_dialog(self):
        """切换到域的对话框"""
        if not self.agent:
            messagebox.showerror("错误", "聊天代理未初始化")
            return

        # 获取所有域
        domains = self.agent.db.get_all_domains()
        if not domains:
            messagebox.showinfo("提示", "还没有创建任何域。\n请先使用'创建域'功能创建域。")
            return

        # 获取当前环境和域
        current_env = self.agent.db.get_active_environment()
        current_domain = None
        if current_env:
            current_domains = self.agent.db.get_environment_domains(current_env['uuid'])
            if current_domains:
                current_domain = current_domains[0]

        # 创建对话框
        dialog = tk.Toplevel(self.root)
        dialog.title("切换域")
        dialog.geometry("550x450")
        dialog.transient(self.root)
        dialog.grab_set()

        ttk.Label(
            dialog,
            text="选择要切换到的域:",
            font=("微软雅黑", 10, "bold")
        ).pack(pady=10)

        if current_domain:
            ttk.Label(
                dialog,
                text=f"当前域: {current_domain['name']}",
                font=("微软雅黑", 9),
                foreground="#0066cc"
            ).pack(pady=5)

        # 域列表
        listbox_frame = ttk.Frame(dialog)
        listbox_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        scrollbar = ttk.Scrollbar(listbox_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        domain_listbox = tk.Listbox(
            listbox_frame,
            font=("微软雅黑", 9),
            yscrollcommand=scrollbar.set
        )
        domain_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=domain_listbox.yview)

        # 填充域列表
        domain_map = {}
        for i, domain in enumerate(domains):
            envs = self.agent.db.get_domain_environments(domain['uuid'])
            default_env = None
            if domain.get('default_environment_uuid'):
                default_env = self.agent.db.get_environment(domain['default_environment_uuid'])
            
            label = f"{domain['name']} ({len(envs)}个环境"
            if default_env:
                label += f", 默认: {default_env['name']}"
            label += ")"
            
            if current_domain and domain['uuid'] == current_domain['uuid']:
                label += " (当前)"
            
            domain_listbox.insert(tk.END, label)
            domain_map[i] = domain

        # 按钮
        button_frame = ttk.Frame(dialog)
        button_frame.pack(pady=10)

        def do_switch():
            selection = domain_listbox.curselection()
            if not selection:
                messagebox.showwarning("警告", "请选择一个域！")
                return

            selected_domain = domain_map[selection[0]]

            # 如果是当前域，不需要切换
            if current_domain and selected_domain['uuid'] == current_domain['uuid']:
                messagebox.showinfo("提示", "已经在该域中了！")
                dialog.destroy()
                return

            try:
                # 使用vision_tool的切换域方法
                success = self.agent.vision_tool.switch_to_domain(selected_domain['uuid'])
                
                if success:
                    new_env = self.agent.db.get_active_environment()
                    messagebox.showinfo(
                        "成功",
                        f"已切换到域: {selected_domain['name']}\n当前位置: {new_env['name']}"
                    )
                    self.add_system_message(
                        f"🎯 切换到域: {selected_domain['name']} (位置: {new_env['name']})"
                    )
                    self.refresh_environment_display()
                    dialog.destroy()
                else:
                    messagebox.showerror("错误", "切换域失败！请检查域的配置。")
            except Exception as e:
                messagebox.showerror("错误", f"切换域时出错: {str(e)}")

        ttk.Button(button_frame, text="切换", command=do_switch, width=15).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="取消", command=dialog.destroy, width=15).pack(side=tk.LEFT, padx=5)

    # ==================== 个性化表达相关方法 ====================

    def learn_user_expressions_now(self):
        """
        立即学习用户表达习惯
        """
        if not self.agent:
            messagebox.showerror("错误", "聊天代理未初始化")
            return

        result = messagebox.askyesno(
            "确认",
            "将分析最近的对话记录，学习用户的表达习惯。\n\n确定要开始学习吗？"
        )

        if not result:
            return

        try:
            self.update_status("学习用户表达习惯中...", "orange")
            self.root.update()

            learned_habits = self.agent.learn_user_expressions_now()

            if learned_habits:
                habit_list = "\n".join([
                    f"• '{h['expression_pattern']}' => {h['meaning']}"
                    for h in learned_habits[:5]  # 最多显示5个
                ])
                if len(learned_habits) > 5:
                    habit_list += f"\n... 还有 {len(learned_habits) - 5} 个"

                messagebox.showinfo(
                    "学习完成",
                    f"成功学习到 {len(learned_habits)} 个用户表达习惯：\n\n{habit_list}"
                )
                self.add_system_message(f"🎯 已学习到 {len(learned_habits)} 个用户表达习惯")
            else:
                messagebox.showinfo("学习完成", "未发现新的表达习惯。")
                self.add_system_message("🎯 未发现新的用户表达习惯")

            self.update_status("就绪", "green")

        except Exception as e:
            self.update_status("错误", "red")
            messagebox.showerror("错误", f"学习用户表达习惯时出错：{str(e)}")

    def add_agent_expression_dialog(self):
        """
        添加智能体表达对话框
        """
        if not self.agent:
            messagebox.showerror("错误", "聊天代理未初始化")
            return

        # 创建对话框
        dialog = tk.Toplevel(self.root)
        dialog.title("添加智能体个性化表达")
        dialog.geometry("500x350")
        dialog.transient(self.root)
        dialog.grab_set()

        # 主容器
        container = ttk.Frame(dialog, padding=20)
        container.pack(fill=tk.BOTH, expand=True)

        # 说明
        ttk.Label(
            container,
            text="添加智能体个性化表达",
            font=("微软雅黑", 12, "bold")
        ).pack(pady=(0, 10))

        ttk.Label(
            container,
            text="定义智能体在对话中可以使用的个性化表达方式",
            font=("微软雅黑", 9),
            foreground="#666666"
        ).pack(pady=(0, 15))

        # 表达方式
        ttk.Label(container, text="表达方式:", font=("微软雅黑", 10)).pack(anchor=tk.W, pady=(0, 5))
        expression_entry = ttk.Entry(container, font=("微软雅黑", 10), width=40)
        expression_entry.pack(fill=tk.X, pady=(0, 10))
        expression_entry.insert(0, "例如: wc、hhh、orz")

        # 含义
        ttk.Label(container, text="含义:", font=("微软雅黑", 10)).pack(anchor=tk.W, pady=(0, 5))
        meaning_text = scrolledtext.ScrolledText(container, height=4, font=("微软雅黑", 9))
        meaning_text.pack(fill=tk.X, pady=(0, 10))
        meaning_text.insert(tk.END, "例如: 表示对突发事情的感叹")

        # 分类
        ttk.Label(container, text="分类:", font=("微软雅黑", 10)).pack(anchor=tk.W, pady=(0, 5))
        category_var = tk.StringVar(value="通用")
        category_combo = ttk.Combobox(
            container,
            textvariable=category_var,
            font=("微软雅黑", 10),
            width=38,
            state="readonly"
        )
        category_combo['values'] = ['通用', '感叹词', '网络用语', '表情替代', '语气词', '口头禅']
        category_combo.pack(fill=tk.X, pady=(0, 15))

        # 按钮
        button_frame = ttk.Frame(container)
        button_frame.pack(pady=10)

        def save_expression():
            expression = expression_entry.get().strip()
            meaning = meaning_text.get("1.0", tk.END).strip()
            category = category_var.get()

            # 清除示例文本
            if expression.startswith("例如"):
                expression = ""
            if meaning.startswith("例如"):
                meaning = ""

            if not expression or not meaning:
                messagebox.showwarning("输入错误", "表达方式和含义不能为空")
                return

            try:
                self.agent.add_agent_expression(expression, meaning, category)
                messagebox.showinfo("成功", f"已添加智能体表达:\n'{expression}' => '{meaning}'")
                self.add_system_message(f"✨ 已添加智能体表达: '{expression}'")
                dialog.destroy()
            except Exception as e:
                messagebox.showerror("错误", f"添加表达失败: {str(e)}")

        ttk.Button(button_frame, text="保存", command=save_expression, width=15).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="取消", command=dialog.destroy, width=15).pack(side=tk.LEFT, padx=5)

        # 清除示例文本的事件处理
        def clear_entry_example(event):
            if expression_entry.get().startswith("例如"):
                expression_entry.delete(0, tk.END)

        def clear_text_example(event):
            if meaning_text.get("1.0", tk.END).strip().startswith("例如"):
                meaning_text.delete("1.0", tk.END)

        expression_entry.bind("<FocusIn>", clear_entry_example)
        meaning_text.bind("<FocusIn>", clear_text_example)

    def show_expression_style(self):
        """
        显示表达风格详情
        """
        if not self.agent:
            messagebox.showerror("错误", "聊天代理未初始化")
            return

        # 创建对话框
        dialog = tk.Toplevel(self.root)
        dialog.title("个性化表达风格")
        dialog.geometry("700x600")
        dialog.transient(self.root)

        # 标题
        title_frame = ttk.Frame(dialog, padding=10)
        title_frame.pack(fill=tk.X)

        ttk.Label(
            title_frame,
            text="🎨 个性化表达风格",
            font=("微软雅黑", 12, "bold")
        ).pack()

        # 统计信息
        stats = self.agent.get_expression_statistics()
        stats_text = (
            f"智能体表达: {stats['agent_expressions']['total']} 个 "
            f"(总使用次数: {stats['agent_expressions']['total_usage']}) | "
            f"用户习惯: {stats['user_habits']['total']} 个 "
            f"(高置信度: {stats['user_habits']['high_confidence']})"
        )
        ttk.Label(title_frame, text=stats_text, font=("微软雅黑", 9)).pack()

        # 工具栏
        toolbar = ttk.Frame(dialog)
        toolbar.pack(fill=tk.X, padx=10, pady=5)

        ttk.Button(
            toolbar,
            text="🔄 刷新",
            command=lambda: self.refresh_expression_display(text_widget),
            width=10
        ).pack(side=tk.LEFT, padx=2)

        def add_expression_and_refresh():
            self.add_agent_expression_dialog()
            self.refresh_expression_display(text_widget)

        def learn_and_refresh():
            self.learn_user_expressions_now()
            self.refresh_expression_display(text_widget)

        ttk.Button(
            toolbar,
            text="➕ 添加表达",
            command=add_expression_and_refresh,
            width=12
        ).pack(side=tk.LEFT, padx=2)

        ttk.Button(
            toolbar,
            text="🎯 立即学习",
            command=learn_and_refresh,
            width=12
        ).pack(side=tk.LEFT, padx=2)

        ttk.Button(
            toolbar,
            text="🗑️ 清空用户习惯",
            command=lambda: self.clear_user_expression_habits(text_widget),
            width=15
        ).pack(side=tk.LEFT, padx=2)

        # 显示区域
        text_widget = scrolledtext.ScrolledText(
            dialog,
            wrap=tk.WORD,
            font=("微软雅黑", 10),
            bg="#f9f9f9"
        )
        text_widget.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # 初始加载
        self.refresh_expression_display(text_widget)

        # 关闭按钮
        ttk.Button(dialog, text="关闭", command=dialog.destroy, width=15).pack(pady=10)

    def refresh_expression_display(self, text_widget):
        """
        刷新表达风格显示

        Args:
            text_widget: 文本组件
        """
        if not self.agent:
            return

        text_widget.config(state=tk.NORMAL)
        text_widget.delete(1.0, tk.END)

        # 智能体表达
        agent_expressions = self.agent.get_agent_expressions()
        text_widget.insert(tk.END, "【智能体个性化表达】\n", "title")
        text_widget.insert(tk.END, "以下表达方式会在智能体回复时自然使用：\n\n")

        if agent_expressions:
            for expr in agent_expressions:
                text_widget.insert(tk.END, f"  ✨ '{expr['expression']}' => {expr['meaning']}\n")
                uuid_value = expr.get('uuid', '')
                display_uuid = uuid_value[:8] if isinstance(uuid_value, str) and len(uuid_value) >= 8 else (uuid_value if uuid_value else "N/A")
                text_widget.insert(tk.END, f"     分类: {expr['category']} | 使用次数: {expr['usage_count']} | UUID: {display_uuid}...\n\n")
        else:
            text_widget.insert(tk.END, "  暂无智能体表达。点击「添加表达」创建新的表达方式。\n\n")

        text_widget.insert(tk.END, "\n" + "=" * 60 + "\n\n")

        # 用户表达习惯
        user_habits = self.agent.get_user_expression_habits()
        text_widget.insert(tk.END, "【用户表达习惯（自动学习）】\n", "title")
        text_widget.insert(tk.END, "以下是从对话中学习到的用户表达习惯：\n\n")

        if user_habits:
            for habit in user_habits:
                confidence_icon = "🟢" if habit['confidence'] >= 0.8 else "🟡" if habit['confidence'] >= 0.5 else "🔴"
                text_widget.insert(tk.END, f"  {confidence_icon} '{habit['expression_pattern']}' => {habit['meaning']}\n")
                text_widget.insert(tk.END, f"     频率: {habit['frequency']} | 置信度: {habit['confidence']:.2f} | 学习于第 {habit.get('learned_from_rounds', '未记录')} 轮\n\n")
        else:
            text_widget.insert(tk.END, "  暂无用户表达习惯。对话10轮后会自动学习，或点击「立即学习」。\n\n")

        text_widget.config(state=tk.DISABLED)

    def clear_user_expression_habits(self, text_widget=None):
        """
        清空用户表达习惯

        Args:
            text_widget: 文本组件（可选，用于刷新显示）
        """
        if not self.agent:
            return

        result = messagebox.askyesno(
            "确认",
            "确定要清空所有用户表达习惯吗？\n此操作不可恢复。"
        )

        if result:
            success = self.agent.clear_user_expression_habits()
            if success:
                messagebox.showinfo("成功", "用户表达习惯已清空")
                self.add_system_message("🗑️ 用户表达习惯已清空")
                if text_widget:
                    self.refresh_expression_display(text_widget)
            else:
                messagebox.showerror("错误", "清空用户表达习惯失败")

    def show_about(self):
        """
        显示关于对话框
        """
        about_text = """
智能对话代理 v3.1 个性化表达版
基于LangChain和Python开发

功能特性:
• 角色扮演对话
• 三层记忆系统（短期+长期+知识库）
• 短期记忆：最近20轮详细对话
• 长期记忆：自动主题概括（每20轮）
• 知识库：自动知识提取（每5轮）
• 个性化表达：智能体表达定制
• 用户习惯学习：自动学习用户表达（每10轮）
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

