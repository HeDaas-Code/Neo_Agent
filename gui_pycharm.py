"""
PyCharm风格增强版GUI界面
重构界面结构和布局，模仿PyCharm IDE设计
包含统一的时间轴数据展示功能

主要特性：
1. PyCharm风格的界面布局
   - 左侧：项目/功能导航面板（可折叠）
   - 中央：主工作区（聊天/数据展示）
   - 右侧：调试信息面板（可折叠）
   - 底部：日志/控制台面板（可折叠）
2. 统一的时间轴数据展示界面
   - 可视化数据历史变化
   - 选中时间点显示详细信息和日志
3. 保留所有原UI功能
"""

import os
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, Canvas, simpledialog
from datetime import datetime, timedelta
import threading
import json
from typing import Dict, Any, List, Optional, Callable
from chat_agent import ChatAgent
from debug_logger import get_debug_logger
from emotion_analyzer import format_emotion_summary


# ==================== 颜色主题（PyCharm Darcula风格） ====================
class ColorTheme:
    """PyCharm Darcula风格颜色主题"""
    # 背景色
    BG_MAIN = "#2b2b2b"
    BG_PANEL = "#3c3f41"
    BG_EDITOR = "#2b2b2b"
    BG_TOOLBAR = "#3c3f41"
    BG_TAB_ACTIVE = "#4e5254"
    BG_TAB_INACTIVE = "#3c3f41"
    BG_INPUT = "#45494a"
    BG_HOVER = "#4e5254"
    BG_SELECTED = "#214283"
    
    # 前景色
    FG_MAIN = "#bbbbbb"
    FG_TITLE = "#ffffff"
    FG_SECONDARY = "#8c8c8c"
    FG_LINK = "#589df6"
    FG_SUCCESS = "#6aab73"
    FG_WARNING = "#d8a742"
    FG_ERROR = "#cf6679"
    FG_KEYWORD = "#cc7832"
    FG_STRING = "#6a8759"
    FG_COMMENT = "#808080"
    
    # 边框色
    BORDER = "#515151"
    BORDER_FOCUS = "#4e94ce"
    
    # 状态色
    STATUS_OK = "#6aab73"
    STATUS_WARNING = "#d8a742"
    STATUS_ERROR = "#cf6679"
    STATUS_INFO = "#589df6"


# ==================== 可折叠面板组件 ====================
class CollapsiblePanel(ttk.Frame):
    """
    可折叠面板组件
    
    注意：此组件是一个通用的可折叠面板实现，
    可用于创建更复杂的可折叠界面布局。
    当前主GUI使用PanedWindow实现面板切换。
    """
    
    def __init__(self, parent, title: str, position: str = "left", 
                 initial_expanded: bool = True, **kwargs):
        super().__init__(parent, **kwargs)
        
        self.title = title
        self.position = position
        self.is_expanded = initial_expanded
        self.content_frame = None
        self.min_size = 200 if position in ['left', 'right'] else 150
        self.max_size = 400 if position in ['left', 'right'] else 300
        
        self._create_widgets()
        
    def _create_widgets(self):
        """创建面板组件"""
        self.header_frame = ttk.Frame(self)
        self.header_frame.pack(fill=tk.X)
        
        self.toggle_btn = ttk.Button(
            self.header_frame,
            text=self._get_toggle_text(),
            width=3,
            command=self.toggle
        )
        self.toggle_btn.pack(side=tk.LEFT, padx=2, pady=2)
        
        self.title_label = ttk.Label(
            self.header_frame,
            text=self.title,
            font=("微软雅黑", 9, "bold")
        )
        self.title_label.pack(side=tk.LEFT, padx=5, pady=2)
        
        self.content_frame = ttk.Frame(self)
        if self.is_expanded:
            self.content_frame.pack(fill=tk.BOTH, expand=True)
            
    def _get_toggle_text(self) -> str:
        if self.position == 'left':
            return "◂" if self.is_expanded else "▸"
        elif self.position == 'right':
            return "▸" if self.is_expanded else "◂"
        else:
            return "▾" if self.is_expanded else "▴"
            
    def toggle(self):
        self.is_expanded = not self.is_expanded
        self.toggle_btn.config(text=self._get_toggle_text())
        
        if self.is_expanded:
            self.content_frame.pack(fill=tk.BOTH, expand=True)
        else:
            self.content_frame.pack_forget()
            
    def get_content_frame(self) -> ttk.Frame:
        return self.content_frame


# ==================== 时间轴组件 ====================
class TimelineWidget(Canvas):
    """统一的时间轴组件"""
    
    def __init__(self, parent, on_time_selected: Callable = None, **kwargs):
        super().__init__(parent, **kwargs)
        
        self.on_time_selected = on_time_selected
        self.time_points: List[Dict[str, Any]] = []
        self.selected_index: Optional[int] = None
        
        self.colors = {
            'bg': ColorTheme.BG_PANEL,
            'line': '#555555',
            'node_normal': '#589df6',
            'node_selected': '#ffc66d',
            'node_hover': '#4fc1ff',
            'text': ColorTheme.FG_MAIN,
            'text_secondary': ColorTheme.FG_SECONDARY,
        }
        
        self.type_colors = {
            'chat': '#6aab73',
            'emotion': '#cf6679',
            'memory': '#589df6',
            'knowledge': '#d8a742',
            'event': '#bb86fc',
            'log': '#808080',
        }
        
        self.bind('<Configure>', self._on_resize)
        self.bind('<Motion>', self._on_mouse_move)
        self.bind('<Button-1>', self._on_click)
        
    def set_time_points(self, points: List[Dict[str, Any]]):
        self.time_points = sorted(points, key=lambda x: x.get('timestamp', ''))
        self.selected_index = None
        self._draw_timeline()
        
    def add_time_point(self, point: Dict[str, Any]):
        self.time_points.append(point)
        self.time_points.sort(key=lambda x: x.get('timestamp', ''))
        self._draw_timeline()
        
    def _draw_timeline(self):
        self.delete('all')
        
        width = self.winfo_width()
        height = self.winfo_height()
        
        if width <= 1 or height <= 1:
            return
            
        self.create_rectangle(0, 0, width, height, 
                             fill=self.colors['bg'], outline='')
        
        if not self.time_points:
            self.create_text(
                width // 2, height // 2,
                text="暂无数据\n系统运行后将自动记录时间线",
                font=('微软雅黑', 10),
                fill=self.colors['text_secondary'],
                justify=tk.CENTER
            )
            return
            
        padding = 60
        timeline_y = height // 2
        available_width = width - 2 * padding
        
        self.create_line(
            padding, timeline_y,
            width - padding, timeline_y,
            fill=self.colors['line'], width=2
        )
        
        if len(self.time_points) == 1:
            step = 0
        else:
            step = available_width / (len(self.time_points) - 1)
            
        for i, point in enumerate(self.time_points):
            x = padding + i * step if len(self.time_points) > 1 else width // 2
            self._draw_node(x, timeline_y, point, i)
            
    def _draw_node(self, x: float, y: float, point: Dict, index: int):
        is_selected = index == self.selected_index
        point_type = point.get('type', 'log')
        
        radius = 10 if not is_selected else 14
        
        if is_selected:
            color = self.colors['node_selected']
        else:
            color = self.type_colors.get(point_type, self.colors['node_normal'])
            
        self.create_oval(
            x - radius, y - radius,
            x + radius, y + radius,
            fill=color, outline='white', width=2,
            tags=(f'node_{index}', 'node')
        )
        
        timestamp = point.get('timestamp', '')
        time_str = ''
        if isinstance(timestamp, str) and timestamp:
            # Prefer extracting HH:MM from a full datetime-like string
            if len(timestamp) >= 16:
                candidate = timestamp[11:16]
                if len(candidate) == 5 and candidate[2] == ':':
                    time_str = candidate
            # Fallback: accept a short HH:MM(/SS) string at the start
            if not time_str and len(timestamp) >= 5:
                candidate = timestamp[:5]
                if len(candidate) == 5 and candidate[2] == ':':
                    time_str = candidate
        
        if time_str:
            self.create_text(
                x, y - 25,
                text=time_str,
                font=('微软雅黑', 8),
                fill=self.colors['text_secondary'],
                tags=(f'time_{index}',)
            )
            
        title = point.get('title', point_type)
        if len(title) > 8:
            title = title[:8] + '..'
        self.create_text(
            x, y + 25,
            text=title,
            font=('微软雅黑', 8),
            fill=self.colors['text'],
            tags=(f'title_{index}',)
        )
        
    def _on_resize(self, event):
        self._draw_timeline()
        
    def _on_mouse_move(self, event):
        items = self.find_overlapping(
            event.x - 5, event.y - 5, 
            event.x + 5, event.y + 5
        )
        
        is_on_node = False
        for item in items:
            tags = self.gettags(item)
            if 'node' in tags:
                is_on_node = True
                break
                
        self.config(cursor='hand2' if is_on_node else '')
        
    def _on_click(self, event):
        items = self.find_overlapping(
            event.x - 10, event.y - 10,
            event.x + 10, event.y + 10
        )
        
        for item in items:
            tags = self.gettags(item)
            for tag in tags:
                if tag.startswith('node_'):
                    try:
                        index = int(tag.split('_')[1])
                        self._select_node(index)
                        return
                    except (ValueError, IndexError):
                        pass
                        
    def _select_node(self, index: int):
        if 0 <= index < len(self.time_points):
            self.selected_index = index
            self._draw_timeline()
            
            if self.on_time_selected:
                self.on_time_selected(self.time_points[index])


# ==================== 时间轴详情面板 ====================
class TimelineDetailPanel(ttk.Frame):
    """时间轴详情面板"""
    
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self._create_widgets()
        
    def _create_widgets(self):
        self.title_label = ttk.Label(
            self,
            text="📋 详细信息",
            font=("微软雅黑", 11, "bold")
        )
        self.title_label.pack(anchor=tk.W, padx=5, pady=5)
        
        self.info_frame = ttk.Frame(self)
        self.info_frame.pack(fill=tk.X, padx=5, pady=2)
        
        self.time_label = ttk.Label(
            self.info_frame,
            text="时间: --",
            font=("微软雅黑", 9)
        )
        self.time_label.pack(side=tk.LEFT)
        
        self.type_label = ttk.Label(
            self.info_frame,
            text="类型: --",
            font=("微软雅黑", 9)
        )
        self.type_label.pack(side=tk.RIGHT)
        
        ttk.Separator(self, orient=tk.HORIZONTAL).pack(fill=tk.X, padx=5, pady=5)
        
        self.detail_text = scrolledtext.ScrolledText(
            self,
            wrap=tk.WORD,
            font=("Consolas", 9),
            bg="#2b2b2b",
            fg="#bbbbbb",
            insertbackground="white"
        )
        self.detail_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.detail_text.config(state=tk.DISABLED)
        
        self.detail_text.tag_config('key', foreground='#cc7832')
        self.detail_text.tag_config('value', foreground='#6a8759')
        self.detail_text.tag_config('header', foreground='#ffc66d', font=('Consolas', 9, 'bold'))
        
    def show_detail(self, point: Dict[str, Any]):
        if not point:
            return
            
        timestamp = point.get('timestamp', '--')
        point_type = point.get('type', '--')
        title = point.get('title', '--')
        data = point.get('data', {})
        
        self.time_label.config(text=f"时间: {timestamp[:19] if len(timestamp) > 19 else timestamp}")
        self.type_label.config(text=f"类型: {point_type}")
        
        self.detail_text.config(state=tk.NORMAL)
        self.detail_text.delete(1.0, tk.END)
        
        self.detail_text.insert(tk.END, f"【{title}】\n", 'header')
        self.detail_text.insert(tk.END, "=" * 40 + "\n\n")
        
        if isinstance(data, dict):
            for key, value in data.items():
                self.detail_text.insert(tk.END, f"{key}: ", 'key')
                if isinstance(value, (dict, list)):
                    value_str = json.dumps(value, ensure_ascii=False, indent=2)
                else:
                    value_str = str(value)
                self.detail_text.insert(tk.END, f"{value_str}\n", 'value')
        else:
            self.detail_text.insert(tk.END, str(data))
            
        self.detail_text.config(state=tk.DISABLED)
        
    def clear(self):
        self.time_label.config(text="时间: --")
        self.type_label.config(text="类型: --")
        self.detail_text.config(state=tk.NORMAL)
        self.detail_text.delete(1.0, tk.END)
        self.detail_text.insert(tk.END, "选择时间轴上的节点查看详情")
        self.detail_text.config(state=tk.DISABLED)


# ==================== 统一数据时间轴视图 ====================
class UnifiedTimelineView(ttk.Frame):
    """统一的数据时间轴视图"""
    
    def __init__(self, parent, db_manager=None, **kwargs):
        super().__init__(parent, **kwargs)
        
        self.db = db_manager
        self.all_time_points: List[Dict[str, Any]] = []
        self.filter_type = "all"
        
        self._create_widgets()
        
    def _create_widgets(self):
        toolbar = ttk.Frame(self)
        toolbar.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(
            toolbar, 
            text="📊 数据时间轴",
            font=("微软雅黑", 11, "bold")
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            toolbar,
            text="🔄 刷新",
            command=self.refresh_data,
            width=8
        ).pack(side=tk.LEFT, padx=2)
        
        ttk.Label(toolbar, text="筛选:").pack(side=tk.LEFT, padx=(10, 2))
        self.filter_var = tk.StringVar(value="全部")
        filter_combo = ttk.Combobox(
            toolbar,
            textvariable=self.filter_var,
            values=['全部', '对话', '情感分析', '记忆', '知识', '事件', '日志'],
            width=10,
            state='readonly'
        )
        filter_combo.pack(side=tk.LEFT, padx=2)
        filter_combo.bind('<<ComboboxSelected>>', self._on_filter_change)
        
        ttk.Label(toolbar, text="范围:").pack(side=tk.LEFT, padx=(10, 2))
        self.range_var = tk.StringVar(value="今天")
        range_combo = ttk.Combobox(
            toolbar,
            textvariable=self.range_var,
            values=['今天', '最近3天', '最近7天', '最近30天', '全部'],
            width=10,
            state='readonly'
        )
        range_combo.pack(side=tk.LEFT, padx=2)
        range_combo.bind('<<ComboboxSelected>>', self._on_range_change)
        
        self.stats_label = ttk.Label(
            toolbar,
            text="共 0 条记录",
            font=("微软雅黑", 9)
        )
        self.stats_label.pack(side=tk.RIGHT, padx=10)
        
        ttk.Separator(self, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=2)
        
        content_paned = ttk.PanedWindow(self, orient=tk.VERTICAL)
        content_paned.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        timeline_frame = ttk.LabelFrame(content_paned, text="时间轴", padding=5)
        content_paned.add(timeline_frame, weight=1)
        
        self.timeline = TimelineWidget(
            timeline_frame,
            on_time_selected=self._on_time_selected,
            bg='#3c3f41',
            highlightthickness=0,
            height=120
        )
        self.timeline.pack(fill=tk.BOTH, expand=True)
        
        detail_frame = ttk.LabelFrame(content_paned, text="详细信息", padding=5)
        content_paned.add(detail_frame, weight=2)
        
        self.detail_panel = TimelineDetailPanel(detail_frame)
        self.detail_panel.pack(fill=tk.BOTH, expand=True)

    def _safe_log_error(self, module: str, message: str):
        """安全地记录错误日志"""
        if hasattr(self, 'debug_logger') and self.debug_logger:
            self.debug_logger.log_error(module, message)
        else:
            print(f"[{module}] {message}")
        
    def set_db_manager(self, db_manager):
        self.db = db_manager
        self.refresh_data()
        
    def refresh_data(self):
        if not self.db:
            return
            
        self.all_time_points = []
        
        try:
            messages = self.db.get_short_term_messages()
            for msg in messages:
                self.all_time_points.append({
                    'timestamp': msg.get('timestamp', ''),
                    'type': 'chat',
                    'title': f"{'用户' if msg['role'] == 'user' else '助手'}消息",
                    'data': {
                        '角色': msg.get('role', ''),
                        '内容': msg.get('content', '')
                    }
                })
        except Exception as e:
            self._safe_log_error("Timeline", f"获取短期记忆失败: {e}")
            
        try:
            summaries = self.db.get_long_term_summaries()
            for summary in summaries:
                self.all_time_points.append({
                    'timestamp': summary.get('created_at', ''),
                    'type': 'memory',
                    'title': '主题概括',
                    'data': {
                        '概括': summary.get('summary', ''),
                        '轮数': summary.get('rounds', 0),
                        '消息数': summary.get('message_count', 0),
                        '开始时间': summary.get('created_at', ''),
                        '结束时间': summary.get('ended_at', '')
                    }
                })
        except Exception as e:
            self._safe_log_error("Timeline", f"获取长期记忆失败: {e}")
            
        try:
            emotions = self.db.get_emotion_history()
            for emotion in emotions:
                self.all_time_points.append({
                    'timestamp': emotion.get('created_at', ''),
                    'type': 'emotion',
                    'title': '情感分析',
                    'data': {
                        '关系类型': emotion.get('relationship_type', ''),
                        '情感基调': emotion.get('emotional_tone', ''),
                        '总评分': emotion.get('overall_score', 0),
                        '亲密度': emotion.get('intimacy', 0),
                        '信任度': emotion.get('trust', 0),
                        '愉悦度': emotion.get('pleasure', 0),
                        '共鸣度': emotion.get('resonance', 0),
                        '依赖度': emotion.get('dependence', 0),
                        '分析摘要': emotion.get('analysis_summary', '')
                    }
                })
        except Exception as e:
            self._safe_log_error("Timeline", f"获取情感分析失败: {e}")
            
        try:
            entities = self.db.get_all_entities()
            for entity in entities:
                self.all_time_points.append({
                    'timestamp': entity.get('created_at', ''),
                    'type': 'knowledge',
                    'title': f"知识:{entity.get('name', '')[:10]}",
                    'data': {
                        '实体名': entity.get('name', ''),
                        'UUID': entity.get('uuid', ''),
                        '创建时间': entity.get('created_at', ''),
                        '更新时间': entity.get('updated_at', '')
                    }
                })
        except Exception as e:
            self._safe_log_error("Timeline", f"获取知识库失败: {e}")
            
        limited_points = self._limit_time_points(self.all_time_points)
        filtered_points = self._apply_filter(limited_points)
        self.timeline.set_time_points(filtered_points)
        self.stats_label.config(text=f"共 {len(filtered_points)} 条记录")
        self.detail_panel.clear()

    def _limit_time_points(self, points: List[Dict], max_points: int = 1000) -> List[Dict]:
        """
        限制时间轴上展示的时间点数量，避免一次性加载过多数据导致内存或性能问题。
        默认只保留按时间排序后的最新 max_points 条记录。
        """
        if not points:
            return []
        # 根据时间倒序排序，缺失时间戳的记录排在最后（使用1970-01-01作为fallback）
        sorted_points = sorted(
            points,
            key=lambda p: p.get('timestamp') or "1970-01-01T00:00:00",
            reverse=True
        )
        if max_points is None or max_points <= 0:
            return sorted_points
        return sorted_points[:max_points]
        
    def _apply_filter(self, points: List[Dict]) -> List[Dict]:
        type_map = {
            '全部': None,
            '对话': 'chat',
            '情感分析': 'emotion',
            '记忆': 'memory',
            '知识': 'knowledge',
            '事件': 'event',
            '日志': 'log'
        }
        
        filter_type = type_map.get(self.filter_var.get())
        if filter_type:
            points = [p for p in points if p.get('type') == filter_type]
            
        now = datetime.now()
        
        range_days = {
            '今天': 1,
            '最近3天': 3,
            '最近7天': 7,
            '最近30天': 30,
            '全部': None
        }
        
        days = range_days.get(self.range_var.get())
        if days:
            cutoff = (now - timedelta(days=days)).isoformat()
            points = [p for p in points if p.get('timestamp', '') >= cutoff]
            
        return points
        
    def _on_filter_change(self, event=None):
        self.refresh_data()
        
    def _on_range_change(self, event=None):
        self.refresh_data()
        
    def _on_time_selected(self, point: Dict[str, Any]):
        self.detail_panel.show_detail(point)


# ==================== 情感印象展示画布 ====================
class EmotionImpressionDisplay(Canvas):
    """情感印象展示画布"""

    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self.emotion_data = None
        self.colors = {
            'bg': '#3c3f41',
            'positive': '#6aab73',
            'neutral': '#8c8c8c',
            'negative': '#cf6679',
            'text': '#bbbbbb',
            'secondary': '#8c8c8c',
            'border': '#515151'
        }
        self.bind('<Configure>', self.on_resize)

    def update_emotion(self, emotion_data: Dict[str, Any]):
        self.emotion_data = emotion_data
        self.draw_impression()

    def draw_impression(self):
        self.delete('all')
        width = self.winfo_width()
        height = self.winfo_height()

        if width <= 1 or height <= 1:
            return

        if not self.emotion_data:
            self.create_text(
                width // 2, height // 2,
                text="暂无情感分析数据\n对话后点击「分析情感关系」按钮",
                font=('微软雅黑', 10),
                fill=self.colors['secondary'],
                justify=tk.CENTER
            )
            return

        overall_score = self.emotion_data.get('overall_score', 50)
        sentiment = self.emotion_data.get('sentiment', 'neutral')
        relationship_type = self.emotion_data.get('relationship_type', '未知')
        emotional_tone = self.emotion_data.get('emotional_tone', '未知')

        if sentiment == 'positive':
            score_color = self.colors['positive']
            sentiment_text = "正面印象"
        elif sentiment == 'negative':
            score_color = self.colors['negative']
            sentiment_text = "负面印象"
        else:
            score_color = self.colors['neutral']
            sentiment_text = "中性印象"

        center_x = width // 2
        center_y = height // 3
        radius = min(width, height) // 5

        self.create_oval(
            center_x - radius, center_y - radius,
            center_x + radius, center_y + radius,
            outline=self.colors['border'], width=15,
            fill=''
        )

        extent = int(360 * (overall_score / 100))
        self.create_arc(
            center_x - radius, center_y - radius,
            center_x + radius, center_y + radius,
            start=90, extent=-extent,
            outline=score_color, width=15,
            style='arc'
        )

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

    def on_resize(self, event):
        self.draw_impression()


# ==================== 主题时间线画布 ====================
class TopicTimelineCanvas(Canvas):
    """主题时间线画布"""

    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self.topics = []
        self.colors = [
            '#FF6B6B', '#4ECDC4', '#45B7D1', '#FFA07A',
            '#98D8C8', '#F7DC6F', '#BB8FCE', '#85C1E2',
            '#F8B739', '#52B788', '#FF8FA3', '#6A9BD1'
        ]
        self.bind('<Configure>', self.on_resize)
        self.bind('<Motion>', self.on_mouse_move)
        self.tooltip = None

    def update_topics(self, summaries):
        self.topics = summaries
        self.draw_timeline()

    def draw_timeline(self):
        self.delete('all')

        if not self.topics:
            width = self.winfo_width()
            height = self.winfo_height()
            self.create_text(
                width // 2, height // 2,
                text="暂无主题数据\n对话超过20轮后将自动生成主题概括",
                font=('微软雅黑', 10),
                fill='#8c8c8c',
                justify=tk.CENTER
            )
            return

        width = self.winfo_width()
        height = self.winfo_height()

        if width <= 1 or height <= 1:
            return

        padding = 40
        timeline_y = height // 2
        available_width = width - 2 * padding

        if len(self.topics) == 1:
            x = width // 2
            self._draw_topic_node(x, timeline_y, self.topics[0], 0)
            return

        step = available_width / (len(self.topics) - 1) if len(self.topics) > 1 else 0

        self.create_line(
            padding, timeline_y,
            width - padding, timeline_y,
            fill='#555555', width=2, tags='timeline'
        )

        for i, topic in enumerate(self.topics):
            x = padding + i * step
            self._draw_topic_node(x, timeline_y, topic, i)

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
        color = self.colors[index % len(self.colors)]
        radius = 12

        node_id = self.create_oval(
            x - radius, y - radius,
            x + radius, y + radius,
            fill=color,
            outline='white',
            width=3,
            tags=f'node_{index}'
        )

        self.create_text(
            x, y,
            text=str(index + 1),
            font=('Arial', 10, 'bold'),
            fill='white',
            tags=f'node_text_{index}'
        )

        date_str = topic.get('created_at', '')[:10] if topic.get('created_at') else ''
        self.create_text(
            x, y - 30,
            text=date_str,
            font=('微软雅黑', 8),
            fill='#8c8c8c',
            tags=f'date_{index}'
        )

        summary = topic.get('summary', '')
        short_summary = summary[:15] + '...' if len(summary) > 15 else summary
        self.create_text(
            x, y + 30,
            text=short_summary,
            font=('微软雅黑', 8),
            fill='#bbbbbb',
            width=100,
            tags=f'summary_{index}'
        )

        self.tag_bind(f'node_{index}', '<Button-1>',
                     lambda e, t=topic, i=index: self.on_node_click(t, i))
        self.itemconfig(node_id, tags=(f'node_{index}', f'tooltip_{index}'))

    def on_node_click(self, topic, index):
        info = f"""主题 {index + 1} 详细信息
        
时间范围: {topic.get('created_at', '')[:19]} 至 {topic.get('ended_at', '')[:19]}
对话轮数: {topic.get('rounds', 0)} 轮
消息数量: {topic.get('message_count', 0)} 条
UUID: {topic.get('uuid', '')}

主题概括:
{topic.get('summary', '')}"""
        messagebox.showinfo(f"主题 {index + 1}", info)

    def on_mouse_move(self, event):
        items = self.find_overlapping(event.x - 2, event.y - 2, event.x + 2, event.y + 2)
        for item in items:
            tags = self.gettags(item)
            for tag in tags:
                if tag.startswith('node_') and not tag.endswith('text'):
                    self.config(cursor='hand2')
                    return
        self.config(cursor='')

    def on_resize(self, event):
        self.draw_timeline()


# ==================== PyCharm风格主GUI类 ====================
class PyCharmStyleGUI:
    """
    PyCharm风格的智能对话代理GUI
    模仿PyCharm IDE的界面布局
    """

    def __init__(self, root):
        self.root = root
        self.root.title("智能对话代理 - PyCharm风格界面")
        self.root.geometry("1600x1000")
        self.root.minsize(1200, 800)

        # 配置深色主题
        self._configure_dark_theme()

        # 初始化状态
        self.agent = None
        self.is_processing = False
        self.debug_logger = get_debug_logger()

        # 创建界面
        self.create_menu()
        self.create_toolbar()
        self.create_main_layout()
        self.create_status_bar()

        # 初始化代理
        self.initialize_agent()

        # 绑定快捷键
        # 按下回车发送消息；如果按下 Ctrl+回车，则只换行不发送
        self.root.bind('<Return>', lambda e: self.send_message() if not e.state & 0x4 else None)
        self.root.bind('<Control-Return>', lambda e: self.input_text.insert(tk.INSERT, '\n'))
        self.root.bind('<F5>', lambda e: self.refresh_all())
        self.root.bind('<Control-Shift-t>', lambda e: self.show_timeline_view())

    def _safe_log_error(self, module: str, message: str):
        """安全地记录错误日志，如果debug_logger不可用则使用print"""
        if hasattr(self, 'debug_logger') and self.debug_logger:
            self.debug_logger.log_error(module, message)
        else:
            print(f"[{module}] {message}")

    def _configure_dark_theme(self):
        """配置深色主题"""
        style = ttk.Style()
        try:
            style.theme_use('clam')
        except Exception:
            pass

        # 配置主要样式
        style.configure('.', 
            background=ColorTheme.BG_MAIN,
            foreground=ColorTheme.FG_MAIN,
            fieldbackground=ColorTheme.BG_INPUT
        )
        
        style.configure('TFrame', background=ColorTheme.BG_MAIN)
        style.configure('TLabel', background=ColorTheme.BG_MAIN, foreground=ColorTheme.FG_MAIN)
        style.configure('TButton', 
            background=ColorTheme.BG_PANEL,
            foreground=ColorTheme.FG_MAIN
        )
        style.configure('TNotebook', background=ColorTheme.BG_MAIN)
        style.configure('TNotebook.Tab', 
            background=ColorTheme.BG_TAB_INACTIVE,
            foreground=ColorTheme.FG_MAIN,
            padding=[10, 5]
        )
        style.map('TNotebook.Tab',
            background=[('selected', ColorTheme.BG_TAB_ACTIVE)],
            foreground=[('selected', ColorTheme.FG_TITLE)]
        )
        style.configure('TLabelframe', 
            background=ColorTheme.BG_MAIN,
            foreground=ColorTheme.FG_MAIN
        )
        style.configure('TLabelframe.Label', 
            background=ColorTheme.BG_MAIN,
            foreground=ColorTheme.FG_MAIN
        )
        style.configure('TPanedwindow', background=ColorTheme.BG_MAIN)
        style.configure('TSeparator', background=ColorTheme.BORDER)
        
        self.root.configure(bg=ColorTheme.BG_MAIN)

    def create_menu(self):
        """创建菜单栏"""
        menubar = tk.Menu(self.root, bg=ColorTheme.BG_TOOLBAR, fg=ColorTheme.FG_MAIN)
        self.root.config(menu=menubar)

        # 文件菜单
        file_menu = tk.Menu(menubar, tearoff=0, bg=ColorTheme.BG_PANEL, fg=ColorTheme.FG_MAIN)
        menubar.add_cascade(label="文件", menu=file_menu)
        file_menu.add_command(label="刷新数据 (F5)", command=self.refresh_all)
        file_menu.add_separator()
        file_menu.add_command(label="退出", command=self.root.quit)

        # 视图菜单
        view_menu = tk.Menu(menubar, tearoff=0, bg=ColorTheme.BG_PANEL, fg=ColorTheme.FG_MAIN)
        menubar.add_cascade(label="视图", menu=view_menu)
        view_menu.add_command(label="时间轴视图 (Ctrl+Shift+T)", command=self.show_timeline_view)
        view_menu.add_command(label="聊天视图", command=self.show_chat_view)
        view_menu.add_separator()
        view_menu.add_command(label="切换左侧面板", command=self.toggle_left_panel)
        view_menu.add_command(label="切换右侧面板", command=self.toggle_right_panel)
        view_menu.add_command(label="切换底部面板", command=self.toggle_bottom_panel)

        # 工具菜单
        tools_menu = tk.Menu(menubar, tearoff=0, bg=ColorTheme.BG_PANEL, fg=ColorTheme.FG_MAIN)
        menubar.add_cascade(label="工具", menu=tools_menu)
        tools_menu.add_command(label="情感分析", command=self.analyze_emotion)
        tools_menu.add_command(label="知识库管理", command=self.show_knowledge_manager)
        tools_menu.add_command(label="事件管理", command=self.show_event_manager)
        tools_menu.add_separator()
        tools_menu.add_command(label="清空记忆", command=self.clear_all_memory)

        # 帮助菜单
        help_menu = tk.Menu(menubar, tearoff=0, bg=ColorTheme.BG_PANEL, fg=ColorTheme.FG_MAIN)
        menubar.add_cascade(label="帮助", menu=help_menu)
        help_menu.add_command(label="关于", command=self.show_about)

    def create_toolbar(self):
        """创建工具栏"""
        toolbar = ttk.Frame(self.root)
        toolbar.pack(fill=tk.X, padx=2, pady=2)

        # 左侧按钮组
        ttk.Button(toolbar, text="💬 聊天", command=self.show_chat_view, width=8).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="📊 时间轴", command=self.show_timeline_view, width=8).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="💖 情感", command=self.analyze_emotion, width=8).pack(side=tk.LEFT, padx=2)
        
        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=5)
        
        ttk.Button(toolbar, text="📚 知识库", command=self.show_knowledge_manager, width=8).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="📅 事件", command=self.show_event_manager, width=8).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="👁️ 环境", command=self.show_environment_manager, width=8).pack(side=tk.LEFT, padx=2)
        
        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=5)
        
        ttk.Button(toolbar, text="🔄 刷新", command=self.refresh_all, width=6).pack(side=tk.LEFT, padx=2)

        # 右侧按钮组
        ttk.Button(toolbar, text="⚙️", command=self.show_settings, width=3).pack(side=tk.RIGHT, padx=2)

    def create_main_layout(self):
        """创建主布局 - PyCharm风格"""
        # 主容器
        self.main_container = ttk.Frame(self.root)
        self.main_container.pack(fill=tk.BOTH, expand=True)

        # 水平分割：左侧面板 | 中央 | 右侧面板
        self.horizontal_paned = ttk.PanedWindow(self.main_container, orient=tk.HORIZONTAL)
        self.horizontal_paned.pack(fill=tk.BOTH, expand=True)

        # 左侧面板 - 导航
        self.left_panel = self._create_left_panel()
        self.horizontal_paned.add(self.left_panel, weight=0)

        # 中央区域
        self.center_container = ttk.Frame(self.horizontal_paned)
        self.horizontal_paned.add(self.center_container, weight=1)

        # 垂直分割：主编辑区 | 底部面板
        self.vertical_paned = ttk.PanedWindow(self.center_container, orient=tk.VERTICAL)
        self.vertical_paned.pack(fill=tk.BOTH, expand=True)

        # 中央主工作区
        self.main_work_area = self._create_main_work_area()
        self.vertical_paned.add(self.main_work_area, weight=1)

        # 底部面板 - 日志/控制台
        self.bottom_panel = self._create_bottom_panel()
        self.vertical_paned.add(self.bottom_panel, weight=0)

        # 右侧面板 - 调试信息
        self.right_panel = self._create_right_panel()
        self.horizontal_paned.add(self.right_panel, weight=0)

    def _create_left_panel(self) -> ttk.Frame:
        """创建左侧导航面板"""
        panel = ttk.Frame(self.horizontal_paned, width=220)
        
        # 标题
        title_frame = ttk.Frame(panel)
        title_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(
            title_frame, 
            text="🗂️ 导航",
            font=("微软雅黑", 10, "bold")
        ).pack(side=tk.LEFT)
        
        self.left_toggle_btn = ttk.Button(
            title_frame, text="◂", width=3,
            command=self.toggle_left_panel
        )
        self.left_toggle_btn.pack(side=tk.RIGHT)

        # 导航树
        self.nav_tree = ttk.Treeview(panel, show='tree', selectmode='browse')
        self.nav_tree.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # 添加导航项
        self.nav_tree.insert('', 'end', 'chat', text='💬 对话', open=True)
        self.nav_tree.insert('', 'end', 'timeline', text='📊 时间轴')
        self.nav_tree.insert('', 'end', 'visualization', text='📈 可视化', open=True)
        self.nav_tree.insert('visualization', 'end', 'topic_timeline', text='  主题时间线')
        self.nav_tree.insert('visualization', 'end', 'emotion_chart', text='  情感关系')
        self.nav_tree.insert('', 'end', 'data', text='💾 数据管理', open=True)
        self.nav_tree.insert('data', 'end', 'short_memory', text='  短期记忆')
        self.nav_tree.insert('data', 'end', 'long_memory', text='  长期记忆')
        self.nav_tree.insert('data', 'end', 'knowledge', text='  知识库')
        self.nav_tree.insert('data', 'end', 'events', text='  事件管理')
        self.nav_tree.insert('data', 'end', 'environment', text='  环境管理')
        self.nav_tree.insert('', 'end', 'settings', text='⚙️ 设置')

        # 绑定选择事件
        self.nav_tree.bind('<<TreeviewSelect>>', self._on_nav_select)

        return panel

    def _create_main_work_area(self) -> ttk.Frame:
        """创建主工作区"""
        area = ttk.Frame(self.vertical_paned)

        # 标签页
        self.main_notebook = ttk.Notebook(area)
        self.main_notebook.pack(fill=tk.BOTH, expand=True)

        # 聊天标签页
        self.chat_tab = self._create_chat_tab()
        self.main_notebook.add(self.chat_tab, text="💬 对话")

        # 时间轴标签页
        self.timeline_tab = self._create_timeline_tab()
        self.main_notebook.add(self.timeline_tab, text="📊 数据时间轴")

        # 可视化标签页
        self.viz_tab = self._create_visualization_tab()
        self.main_notebook.add(self.viz_tab, text="📈 可视化")

        # 数据管理标签页
        self.data_tab = self._create_data_management_tab()
        self.main_notebook.add(self.data_tab, text="💾 数据管理")

        return area

    def _create_chat_tab(self) -> ttk.Frame:
        """创建聊天标签页"""
        tab = ttk.Frame(self.main_notebook)

        # 顶部信息栏
        info_bar = ttk.Frame(tab)
        info_bar.pack(fill=tk.X, padx=10, pady=5)

        self.character_label = ttk.Label(
            info_bar,
            text="📋 角色: 加载中...",
            font=("微软雅黑", 10)
        )
        self.character_label.pack(side=tk.LEFT)

        self.memory_status_label = ttk.Label(
            info_bar,
            text="短期记忆: 0轮 | 长期记忆: 0个主题",
            font=("微软雅黑", 9)
        )
        self.memory_status_label.pack(side=tk.RIGHT)

        # 聊天显示区
        chat_frame = ttk.Frame(tab)
        chat_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        self.chat_display = scrolledtext.ScrolledText(
            chat_frame,
            wrap=tk.WORD,
            font=("微软雅黑", 11),
            bg=ColorTheme.BG_EDITOR,
            fg=ColorTheme.FG_MAIN,
            insertbackground="white",
            padx=10,
            pady=10
        )
        self.chat_display.pack(fill=tk.BOTH, expand=True)
        self.chat_display.config(state=tk.DISABLED)

        # 配置文本标签
        self.chat_display.tag_config("user", foreground="#589df6", font=("微软雅黑", 11, "bold"))
        self.chat_display.tag_config("assistant", foreground="#ffc66d", font=("微软雅黑", 11, "bold"))
        self.chat_display.tag_config("system", foreground="#8c8c8c", font=("微软雅黑", 9, "italic"))
        self.chat_display.tag_config("timestamp", foreground="#606060", font=("微软雅黑", 8))
        self.chat_display.tag_config("archive", foreground="#bb86fc", font=("微软雅黑", 9, "italic"))

        # 输入区
        input_frame = ttk.LabelFrame(tab, text="✏️ 输入消息", padding=5)
        input_frame.pack(fill=tk.X, padx=10, pady=5)

        self.input_text = tk.Text(
            input_frame,
            height=3,
            wrap=tk.WORD,
            font=("微软雅黑", 10),
            bg=ColorTheme.BG_INPUT,
            fg=ColorTheme.FG_MAIN,
            insertbackground="white"
        )
        self.input_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # 按钮栏
        btn_frame = ttk.Frame(input_frame)
        btn_frame.pack(fill=tk.X, padx=5, pady=(0, 5))

        self.send_button = ttk.Button(
            btn_frame,
            text="发送 (Enter)",
            command=self.send_message
        )
        self.send_button.pack(side=tk.LEFT, padx=2)

        ttk.Button(
            btn_frame,
            text="清空输入",
            command=lambda: self.input_text.delete(1.0, tk.END)
        ).pack(side=tk.LEFT, padx=2)

        ttk.Button(
            btn_frame,
            text="清空显示",
            command=self.clear_chat_display
        ).pack(side=tk.LEFT, padx=2)

        return tab

    def _create_timeline_tab(self) -> ttk.Frame:
        """创建时间轴标签页"""
        tab = ttk.Frame(self.main_notebook)
        
        self.unified_timeline = UnifiedTimelineView(tab)
        self.unified_timeline.pack(fill=tk.BOTH, expand=True)
        
        return tab

    def _create_visualization_tab(self) -> ttk.Frame:
        """创建可视化标签页"""
        tab = ttk.Frame(self.main_notebook)

        # 可视化选项卡
        viz_notebook = ttk.Notebook(tab)
        viz_notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # 主题时间线
        topic_tab = ttk.Frame(viz_notebook)
        viz_notebook.add(topic_tab, text="📈 主题时间线")

        self.topic_timeline = TopicTimelineCanvas(
            topic_tab,
            bg=ColorTheme.BG_PANEL,
            highlightthickness=0
        )
        self.topic_timeline.pack(fill=tk.BOTH, expand=True)

        # 情感关系
        emotion_tab = ttk.Frame(viz_notebook)
        viz_notebook.add(emotion_tab, text="💖 情感关系")

        emotion_container = ttk.Frame(emotion_tab)
        emotion_container.pack(fill=tk.BOTH, expand=True)

        # 左侧：图表
        chart_frame = ttk.Frame(emotion_container)
        chart_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.emotion_canvas = EmotionImpressionDisplay(
            chart_frame,
            bg=ColorTheme.BG_PANEL,
            highlightthickness=0
        )
        self.emotion_canvas.pack(fill=tk.BOTH, expand=True)

        # 右侧：控制和详情
        control_frame = ttk.Frame(emotion_container, width=250)
        control_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=5)
        control_frame.pack_propagate(False)

        ttk.Button(
            control_frame,
            text="🔍 分析情感关系",
            command=self.analyze_emotion,
            width=20
        ).pack(pady=5)

        self.emotion_info_text = scrolledtext.ScrolledText(
            control_frame,
            wrap=tk.WORD,
            font=("微软雅黑", 9),
            bg=ColorTheme.BG_EDITOR,
            fg=ColorTheme.FG_MAIN,
            height=12
        )
        self.emotion_info_text.pack(fill=tk.BOTH, expand=True, pady=5)
        self.emotion_info_text.config(state=tk.DISABLED)

        return tab

    def _create_data_management_tab(self) -> ttk.Frame:
        """创建数据管理标签页"""
        tab = ttk.Frame(self.main_notebook)

        # 数据管理选项卡
        data_notebook = ttk.Notebook(tab)
        data_notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # 短期记忆
        short_term_tab = ttk.Frame(data_notebook)
        data_notebook.add(short_term_tab, text="💭 短期记忆")
        self._create_short_term_panel(short_term_tab)

        # 长期记忆
        long_term_tab = ttk.Frame(data_notebook)
        data_notebook.add(long_term_tab, text="📚 长期记忆")
        self._create_long_term_panel(long_term_tab)

        # 知识库
        knowledge_tab = ttk.Frame(data_notebook)
        data_notebook.add(knowledge_tab, text="📖 知识库")
        self._create_knowledge_panel(knowledge_tab)

        # 事件管理
        event_tab = ttk.Frame(data_notebook)
        data_notebook.add(event_tab, text="📅 事件管理")
        self._create_event_panel(event_tab)

        # 环境管理
        env_tab = ttk.Frame(data_notebook)
        data_notebook.add(env_tab, text="👁️ 环境管理")
        self._create_environment_panel(env_tab)

        # 数据库管理
        db_tab = ttk.Frame(data_notebook)
        data_notebook.add(db_tab, text="💾 数据库")
        self._create_database_panel(db_tab)

        return tab

    def _create_short_term_panel(self, parent):
        """创建短期记忆面板"""
        toolbar = ttk.Frame(parent)
        toolbar.pack(fill=tk.X, padx=5, pady=5)

        ttk.Button(toolbar, text="🔄 刷新", command=self.refresh_short_term, width=8).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="🗑️ 清空", command=self.clear_short_term, width=8).pack(side=tk.LEFT, padx=2)

        self.short_term_count_label = ttk.Label(toolbar, text="消息数: 0")
        self.short_term_count_label.pack(side=tk.RIGHT, padx=10)

        self.short_term_display = scrolledtext.ScrolledText(
            parent,
            wrap=tk.WORD,
            font=("微软雅黑", 9),
            bg=ColorTheme.BG_EDITOR,
            fg=ColorTheme.FG_MAIN
        )
        self.short_term_display.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.short_term_display.tag_config("user", foreground="#589df6", font=("微软雅黑", 9, "bold"))
        self.short_term_display.tag_config("assistant", foreground="#ffc66d", font=("微软雅黑", 9, "bold"))
        self.short_term_display.tag_config("timestamp", foreground="#606060", font=("微软雅黑", 8))

    def _create_long_term_panel(self, parent):
        """创建长期记忆面板"""
        toolbar = ttk.Frame(parent)
        toolbar.pack(fill=tk.X, padx=5, pady=5)

        ttk.Button(toolbar, text="🔄 刷新", command=self.refresh_long_term, width=8).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="🗑️ 清空", command=self.clear_long_term, width=8).pack(side=tk.LEFT, padx=2)

        self.long_term_count_label = ttk.Label(toolbar, text="概括数: 0")
        self.long_term_count_label.pack(side=tk.RIGHT, padx=10)

        self.long_term_display = scrolledtext.ScrolledText(
            parent,
            wrap=tk.WORD,
            font=("微软雅黑", 9),
            bg=ColorTheme.BG_EDITOR,
            fg=ColorTheme.FG_MAIN
        )
        self.long_term_display.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

    def _create_knowledge_panel(self, parent):
        """创建知识库面板"""
        toolbar = ttk.Frame(parent)
        toolbar.pack(fill=tk.X, padx=5, pady=5)

        ttk.Button(toolbar, text="🔄 刷新", command=self.refresh_knowledge, width=8).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="🔍 搜索", command=self.search_knowledge, width=8).pack(side=tk.LEFT, padx=2)

        ttk.Label(toolbar, text="搜索:").pack(side=tk.LEFT, padx=(10, 2))
        self.kb_search_var = tk.StringVar()
        kb_search_entry = ttk.Entry(toolbar, textvariable=self.kb_search_var, width=20)
        kb_search_entry.pack(side=tk.LEFT, padx=2)

        self.knowledge_display = scrolledtext.ScrolledText(
            parent,
            wrap=tk.WORD,
            font=("微软雅黑", 9),
            bg=ColorTheme.BG_EDITOR,
            fg=ColorTheme.FG_MAIN
        )
        self.knowledge_display.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

    def _create_event_panel(self, parent):
        """创建事件管理面板"""
        toolbar = ttk.Frame(parent)
        toolbar.pack(fill=tk.X, padx=5, pady=5)

        ttk.Button(toolbar, text="➕ 新建事件", command=self.create_new_event, width=12).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="🔄 刷新", command=self.refresh_events, width=8).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="🚀 触发", command=self.trigger_event, width=8).pack(side=tk.LEFT, padx=2)

        self.event_stats_label = ttk.Label(toolbar, text="事件统计: 加载中...")
        self.event_stats_label.pack(side=tk.RIGHT, padx=10)

        columns = ('标题', '类型', '优先级', '状态', '创建时间')
        self.event_tree = ttk.Treeview(parent, columns=columns, show='tree headings', selectmode='browse')

        self.event_tree.heading('#0', text='ID')
        for col in columns:
            self.event_tree.heading(col, text=col)

        self.event_tree.column('#0', width=80, minwidth=80)
        self.event_tree.column('标题', width=200, minwidth=150)
        self.event_tree.column('类型', width=80, minwidth=80)
        self.event_tree.column('优先级', width=80, minwidth=80)
        self.event_tree.column('状态', width=80, minwidth=80)
        self.event_tree.column('创建时间', width=150, minwidth=120)

        scrollbar = ttk.Scrollbar(parent, orient=tk.VERTICAL, command=self.event_tree.yview)
        self.event_tree.configure(yscrollcommand=scrollbar.set)

        self.event_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y, pady=5)

    def _create_environment_panel(self, parent):
        """创建环境管理面板"""
        toolbar = ttk.Frame(parent)
        toolbar.pack(fill=tk.X, padx=5, pady=5)

        ttk.Button(toolbar, text="🔄 刷新", command=self.refresh_environment, width=8).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="➕ 新建环境", command=self.create_new_environment, width=12).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="➕ 添加物体", command=self.add_new_object, width=12).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="🏠 创建默认", command=self.create_default_environment, width=12).pack(side=tk.LEFT, padx=2)

        self.environment_display = scrolledtext.ScrolledText(
            parent,
            wrap=tk.WORD,
            font=("微软雅黑", 9),
            bg=ColorTheme.BG_EDITOR,
            fg=ColorTheme.FG_MAIN
        )
        self.environment_display.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

    def _create_database_panel(self, parent):
        """创建数据库管理面板"""
        try:
            from database_gui import DatabaseManagerGUI
            # 要求已有已初始化的 agent 和其数据库连接，避免使用独立的数据库实例导致数据不一致
            if hasattr(self, 'agent') and self.agent and hasattr(self.agent, 'db') and self.agent.db:
                db_manager = self.agent.db
                self.db_gui = DatabaseManagerGUI(parent, db_manager)
            else:
                # 代理未初始化，显示提示信息
                ttk.Label(
                    parent,
                    text="数据库管理面板需要已初始化的代理。\n请等待代理初始化完成后刷新此页面。",
                    font=("微软雅黑", 10)
                ).pack(pady=50)
        except Exception as e:
            ttk.Label(
                parent,
                text=f"数据库管理界面加载失败:\n{str(e)}",
                font=("微软雅黑", 10)
            ).pack(pady=50)

    def _create_bottom_panel(self) -> ttk.Frame:
        """创建底部面板 - 日志/控制台"""
        panel = ttk.Frame(self.vertical_paned, height=200)

        # 标题栏
        title_frame = ttk.Frame(panel)
        title_frame.pack(fill=tk.X)

        ttk.Label(
            title_frame,
            text="📝 日志与控制台",
            font=("微软雅黑", 9, "bold")
        ).pack(side=tk.LEFT, padx=5)

        self.bottom_toggle_btn = ttk.Button(
            title_frame, text="▾", width=3,
            command=self.toggle_bottom_panel
        )
        self.bottom_toggle_btn.pack(side=tk.RIGHT, padx=2)

        # 底部选项卡
        self.bottom_notebook = ttk.Notebook(panel)
        self.bottom_notebook.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)

        # 系统日志
        log_tab = ttk.Frame(self.bottom_notebook)
        self.bottom_notebook.add(log_tab, text="系统日志")

        self.system_log = scrolledtext.ScrolledText(
            log_tab,
            wrap=tk.WORD,
            font=("Consolas", 9),
            bg=ColorTheme.BG_EDITOR,
            fg=ColorTheme.FG_MAIN,
            height=8
        )
        self.system_log.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)

        # Debug日志（仅在debug模式）
        debug_mode = os.getenv('DEBUG_MODE', 'False').lower() == 'true'
        if debug_mode:
            debug_tab = ttk.Frame(self.bottom_notebook)
            self.bottom_notebook.add(debug_tab, text="🔧 Debug")

            debug_toolbar = ttk.Frame(debug_tab)
            debug_toolbar.pack(fill=tk.X, padx=2, pady=2)

            ttk.Button(debug_toolbar, text="刷新", command=self.refresh_debug_log, width=8).pack(side=tk.LEFT, padx=2)
            ttk.Button(debug_toolbar, text="清空", command=self.clear_debug_log, width=8).pack(side=tk.LEFT, padx=2)

            self.debug_display = scrolledtext.ScrolledText(
                debug_tab,
                wrap=tk.WORD,
                font=("Consolas", 9),
                bg="#1e1e1e",
                fg="#d4d4d4",
                height=8
            )
            self.debug_display.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)

            self.debug_display.tag_config('module', foreground='#4ec9b0')
            self.debug_display.tag_config('prompt', foreground='#ce9178')
            self.debug_display.tag_config('request', foreground='#569cd6')
            self.debug_display.tag_config('response', foreground='#4fc1ff')
            self.debug_display.tag_config('error', foreground='#f48771')
            self.debug_display.tag_config('info', foreground='#b5cea8')

            self.debug_logger.add_listener(self._on_debug_log_added)

        return panel

    def _create_right_panel(self) -> ttk.Frame:
        """创建右侧面板 - 调试信息"""
        panel = ttk.Frame(self.horizontal_paned, width=280)

        # 标题栏
        title_frame = ttk.Frame(panel)
        title_frame.pack(fill=tk.X)

        self.right_toggle_btn = ttk.Button(
            title_frame, text="▸", width=3,
            command=self.toggle_right_panel
        )
        self.right_toggle_btn.pack(side=tk.LEFT, padx=2)

        ttk.Label(
            title_frame,
            text="🔍 调试信息",
            font=("微软雅黑", 9, "bold")
        ).pack(side=tk.LEFT, padx=5)

        # 调试选项卡
        debug_notebook = ttk.Notebook(panel)
        debug_notebook.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)

        # 系统信息
        info_tab = ttk.Frame(debug_notebook)
        debug_notebook.add(info_tab, text="系统信息")

        self.info_display = scrolledtext.ScrolledText(
            info_tab,
            wrap=tk.WORD,
            font=("Consolas", 9),
            bg=ColorTheme.BG_EDITOR,
            fg=ColorTheme.FG_MAIN
        )
        self.info_display.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)

        # 理解阶段
        understanding_tab = ttk.Frame(debug_notebook)
        debug_notebook.add(understanding_tab, text="🧠 理解阶段")

        self.understanding_display = scrolledtext.ScrolledText(
            understanding_tab,
            wrap=tk.WORD,
            font=("微软雅黑", 9),
            bg=ColorTheme.BG_EDITOR,
            fg=ColorTheme.FG_MAIN
        )
        self.understanding_display.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)

        # 表达风格
        style_tab = ttk.Frame(debug_notebook)
        debug_notebook.add(style_tab, text="🎨 表达风格")

        style_toolbar = ttk.Frame(style_tab)
        style_toolbar.pack(fill=tk.X, padx=2, pady=2)

        ttk.Button(style_toolbar, text="🔄 刷新", command=self.refresh_expression_style, width=8).pack(side=tk.LEFT, padx=2)
        ttk.Button(style_toolbar, text="➕ 添加", command=self.add_agent_expression, width=8).pack(side=tk.LEFT, padx=2)
        ttk.Button(style_toolbar, text="🎯 学习", command=self.learn_user_expressions, width=8).pack(side=tk.LEFT, padx=2)

        self.style_display = scrolledtext.ScrolledText(
            style_tab,
            wrap=tk.WORD,
            font=("微软雅黑", 9),
            bg=ColorTheme.BG_EDITOR,
            fg=ColorTheme.FG_MAIN
        )
        self.style_display.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)

        return panel

    def create_status_bar(self):
        """创建状态栏"""
        status_bar = ttk.Frame(self.root)
        status_bar.pack(fill=tk.X, side=tk.BOTTOM)

        self.status_label = ttk.Label(
            status_bar,
            text="● 就绪",
            font=("微软雅黑", 9)
        )
        self.status_label.pack(side=tk.LEFT, padx=10)

        self.db_status_label = ttk.Label(
            status_bar,
            text="数据库: 正常",
            font=("微软雅黑", 8)
        )
        self.db_status_label.pack(side=tk.RIGHT, padx=10)

        self.time_label = ttk.Label(
            status_bar,
            text=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            font=("微软雅黑", 8)
        )
        self.time_label.pack(side=tk.RIGHT, padx=10)

        self._update_time()

    def _update_time(self):
        """更新时间显示"""
        self.time_label.config(text=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        self.root.after(1000, self._update_time)

    # ==================== 导航和视图切换 ====================

    def _on_nav_select(self, event):
        """导航选择事件"""
        selection = self.nav_tree.selection()
        if not selection:
            return

        item = selection[0]
        nav_map = {
            'chat': lambda: self.main_notebook.select(0),
            'timeline': lambda: self.main_notebook.select(1),
            'visualization': lambda: self.main_notebook.select(2),
            'topic_timeline': lambda: self.main_notebook.select(2),
            'emotion_chart': lambda: self.main_notebook.select(2),
            'data': lambda: self.main_notebook.select(3),
            'short_memory': lambda: self.main_notebook.select(3),
            'long_memory': lambda: self.main_notebook.select(3),
            'knowledge': lambda: self.main_notebook.select(3),
            'events': lambda: self.main_notebook.select(3),
            'environment': lambda: self.main_notebook.select(3),
            'settings': self.show_settings
        }

        if item in nav_map:
            nav_map[item]()

    def show_chat_view(self):
        """显示聊天视图"""
        self.main_notebook.select(0)

    def show_timeline_view(self):
        """显示时间轴视图"""
        self.main_notebook.select(1)
        self.unified_timeline.refresh_data()

    def show_knowledge_manager(self):
        """显示知识库管理"""
        self.main_notebook.select(3)

    def show_event_manager(self):
        """显示事件管理"""
        self.main_notebook.select(3)

    def show_environment_manager(self):
        """显示环境管理"""
        self.main_notebook.select(3)

    def show_settings(self):
        """显示设置"""
        messagebox.showinfo("设置", "设置功能正在开发中...")

    def toggle_left_panel(self):
        """切换左侧面板显示/隐藏"""
        try:
            # 使用显式状态标志而不是宽度判断
            is_visible = getattr(self, "_left_panel_visible", True)
            if is_visible:
                # 当前可见，隐藏它
                self.left_panel.pack_forget()
                self.horizontal_paned.forget(self.left_panel)
                self.left_toggle_btn.config(text="▸")
                self._left_panel_visible = False
            else:
                # 当前隐藏，显示它
                self.horizontal_paned.insert(0, self.left_panel, weight=0)
                self.left_toggle_btn.config(text="◂")
                self._left_panel_visible = True
        except Exception as e:
            self.debug_logger.log_error("GUI", f"切换左侧面板失败: {e}")

    def toggle_right_panel(self):
        """切换右侧面板显示/隐藏"""
        try:
            # 使用显式状态标志而不是宽度判断
            is_visible = getattr(self, "_right_panel_visible", True)
            if is_visible:
                # 当前可见，隐藏它
                self.horizontal_paned.forget(self.right_panel)
                self.right_toggle_btn.config(text="◂")
                self._right_panel_visible = False
            else:
                # 当前隐藏，显示它
                self.horizontal_paned.add(self.right_panel, weight=0)
                self.right_toggle_btn.config(text="▸")
                self._right_panel_visible = True
        except Exception as e:
            self.debug_logger.log_error("GUI", f"切换右侧面板失败: {e}")

    def toggle_bottom_panel(self):
        """切换底部面板显示/隐藏"""
        try:
            # 使用显式状态标志而不是高度判断
            is_visible = getattr(self, "_bottom_panel_visible", True)
            if is_visible:
                # 当前可见，隐藏它
                self.vertical_paned.forget(self.bottom_panel)
                self.bottom_toggle_btn.config(text="▴")
                self._bottom_panel_visible = False
            else:
                # 当前隐藏，显示它
                self.vertical_paned.add(self.bottom_panel, weight=0)
                self.bottom_toggle_btn.config(text="▾")
                self._bottom_panel_visible = True
        except Exception as e:
            self.debug_logger.log_error("GUI", f"切换底部面板失败: {e}")

    # ==================== 代理初始化和聊天功能 ====================

    def initialize_agent(self):
        """初始化聊天代理"""
        try:
            self.update_status("初始化代理...", ColorTheme.STATUS_WARNING)
            self.agent = ChatAgent()
            
            if hasattr(self.agent, 'db'):
                self.unified_timeline.set_db_manager(self.agent.db)
            
            char_info = f"📋 角色: {self.agent.character.name} ({self.agent.character.role})"
            self.character_label.config(text=char_info)
            
            self.update_status("就绪", ColorTheme.STATUS_OK)
            self.add_system_message("系统初始化完成，可以开始对话")
            self.refresh_all()
            
        except Exception as e:
            error_msg = f"初始化代理失败: {str(e)}"
            self.update_status("错误", ColorTheme.STATUS_ERROR)
            self.add_system_message(error_msg)
            messagebox.showerror("错误", error_msg)

    def send_message(self):
        """发送消息"""
        if self.is_processing:
            messagebox.showwarning("请稍候", "正在处理上一条消息...")
            return

        if not self.agent:
            messagebox.showerror("错误", "聊天代理未初始化")
            return

        user_input = self.input_text.get(1.0, tk.END).strip()
        if not user_input:
            return

        self.add_message_to_display("user", user_input)
        self.input_text.delete(1.0, tk.END)

        self.is_processing = True
        self.update_status("思考中...", ColorTheme.STATUS_WARNING)
        self.send_button.config(state=tk.DISABLED)

        old_summary_count = len(self.agent.get_long_term_summaries())

        def process_chat():
            try:
                response = self.agent.chat(user_input)
                # 如果窗口已关闭，则不再尝试更新UI
                try:
                    if not self.root.winfo_exists():
                        return
                except Exception:
                    return  # 窗口已销毁
                self.root.after(0, lambda: self.handle_response(response, old_summary_count))
            except Exception as e:
                # 如果在错误处理期间窗口已经销毁，静默退出以避免崩溃
                try:
                    if not self.root.winfo_exists():
                        return
                except Exception:
                    return  # 窗口已销毁
                error_msg = f"处理消息时出错: {str(e)}"
                try:
                    self.root.after(0, lambda: self.handle_error(error_msg))
                except Exception:
                    # 根窗口或事件循环可能已经被销毁，忽略后续UI更新
                    return

        thread = threading.Thread(target=process_chat, daemon=True)
        thread.start()

    def handle_response(self, response: str, old_summary_count: int):
        """处理代理回复"""
        self.add_message_to_display("assistant", response)

        understanding_result = self.agent.get_last_understanding()
        if understanding_result:
            self.update_understanding_display(understanding_result)

        new_summaries = self.agent.get_long_term_summaries()
        if len(new_summaries) > old_summary_count:
            latest_summary = new_summaries[-1]
            self.add_archive_message(latest_summary.get('rounds', 20), latest_summary.get('summary', ''))
            self.update_topic_timeline()

        self.refresh_all()
        self.is_processing = False
        self.update_status("就绪", ColorTheme.STATUS_OK)
        self.send_button.config(state=tk.NORMAL)
        self.input_text.focus()

    def handle_error(self, error_msg: str):
        """处理错误"""
        self.add_system_message(f"错误: {error_msg}")
        messagebox.showerror("错误", error_msg)
        self.is_processing = False
        self.update_status("出错", ColorTheme.STATUS_ERROR)
        self.send_button.config(state=tk.NORMAL)

    # ==================== 消息显示方法 ====================

    def add_message_to_display(self, role: str, content: str):
        """添加消息到显示区"""
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
        """添加系统消息"""
        self.chat_display.config(state=tk.NORMAL)
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.chat_display.insert(tk.END, f"[{timestamp}] ", "timestamp")
        self.chat_display.insert(tk.END, f"[系统] {message}\n\n", "system")
        self.chat_display.see(tk.END)
        self.chat_display.config(state=tk.DISABLED)

        self.log_message(f"[系统] {message}")

    def add_archive_message(self, rounds: int, summary: str):
        """添加归档消息"""
        self.chat_display.config(state=tk.NORMAL)
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.chat_display.insert(tk.END, f"[{timestamp}] ", "timestamp")
        self.chat_display.insert(tk.END, f"[记忆归档] 已将前{rounds}轮对话归档\n", "archive")
        self.chat_display.insert(tk.END, f"主题概括: {summary}\n\n", "archive")
        self.chat_display.see(tk.END)
        self.chat_display.config(state=tk.DISABLED)

    def log_message(self, message: str):
        """记录到系统日志"""
        self.system_log.config(state=tk.NORMAL)
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.system_log.insert(tk.END, f"[{timestamp}] {message}\n")
        self.system_log.see(tk.END)
        self.system_log.config(state=tk.DISABLED)

    def clear_chat_display(self):
        """清空聊天显示"""
        result = messagebox.askyesno("确认", "确定要清空聊天显示区吗？\n（不会删除历史记忆）")
        if result:
            self.chat_display.config(state=tk.NORMAL)
            self.chat_display.delete(1.0, tk.END)
            self.chat_display.config(state=tk.DISABLED)
            self.add_system_message("聊天显示区已清空")

    def update_status(self, text: str, color: str = None):
        """更新状态栏"""
        self.status_label.config(text=f"● {text}")
        if color:
            self.status_label.config(foreground=color)

    # ==================== 刷新方法 ====================

    def refresh_all(self):
        """刷新所有数据"""
        if not self.agent:
            return

        # 验证代理是否正确初始化
        if not hasattr(self.agent, 'db') or not self.agent.db:
            self.debug_logger.log_error("GUI", "代理数据库未正确初始化")
            return

        try:
            self.refresh_memory_status()
            self.refresh_short_term()
            self.refresh_long_term()
            self.refresh_knowledge()
            self.refresh_events()
            self.refresh_environment()
            self.update_topic_timeline()
            self.update_info_display()
            self.unified_timeline.refresh_data()
        except Exception as e:
            self.debug_logger.log_error("GUI", f"刷新数据时出错: {e}")

    def refresh_memory_status(self):
        """刷新记忆状态"""
        if not self.agent:
            return

        try:
            stats = self.agent.get_memory_stats()
            short_term_rounds = stats.get('short_term', {}).get('rounds', 0)
            long_term_count = len(self.agent.get_long_term_summaries())
            self.memory_status_label.config(
                text=f"短期记忆: {short_term_rounds}轮 | 长期记忆: {long_term_count}个主题"
            )
        except Exception as e:
            self.debug_logger.log_error("GUI", f"刷新记忆状态失败: {e}")

    def refresh_short_term(self):
        """刷新短期记忆"""
        if not self.agent:
            return

        try:
            messages = self.agent.db.get_short_term_messages()
            self.short_term_count_label.config(text=f"消息数: {len(messages)}")

            self.short_term_display.config(state=tk.NORMAL)
            self.short_term_display.delete(1.0, tk.END)

            for msg in messages:
                role_text = "用户" if msg['role'] == 'user' else "助手"
                timestamp = msg.get('timestamp', '')[:19]
                self.short_term_display.insert(tk.END, f"[{timestamp}] ", "timestamp")
                self.short_term_display.insert(tk.END, f"{role_text}:\n", msg['role'])
                self.short_term_display.insert(tk.END, f"{msg['content']}\n\n")

            self.short_term_display.config(state=tk.DISABLED)
        except Exception as e:
            self.debug_logger.log_error("GUI", f"刷新短期记忆失败: {e}")

    def refresh_long_term(self):
        """刷新长期记忆"""
        if not self.agent:
            return

        try:
            summaries = self.agent.db.get_long_term_summaries()
            self.long_term_count_label.config(text=f"概括数: {len(summaries)}")

            self.long_term_display.config(state=tk.NORMAL)
            self.long_term_display.delete(1.0, tk.END)

            for i, summary in enumerate(summaries, 1):
                self.long_term_display.insert(tk.END, f"━━━ 主题 {i} ━━━\n")
                self.long_term_display.insert(tk.END, f"时间: {summary['created_at'][:19]} - {summary['ended_at'][:19]}\n")
                self.long_term_display.insert(tk.END, f"轮数: {summary.get('rounds', 0)} | 消息: {summary.get('message_count', 0)}\n")
                self.long_term_display.insert(tk.END, f"\n{summary['summary']}\n\n\n")

            self.long_term_display.config(state=tk.DISABLED)
        except Exception as e:
            self.debug_logger.log_error("GUI", f"刷新长期记忆失败: {e}")

    def refresh_knowledge(self):
        """刷新知识库"""
        if not self.agent:
            return

        try:
            entities = self.agent.db.get_all_entities()
            base_facts = self.agent.db.get_all_base_facts()

            self.knowledge_display.config(state=tk.NORMAL)
            self.knowledge_display.delete(1.0, tk.END)

            self.knowledge_display.insert(tk.END, f"【基础知识】({len(base_facts)} 条)\n")
            self.knowledge_display.insert(tk.END, "=" * 40 + "\n\n")

            for fact in base_facts[:10]:
                self.knowledge_display.insert(tk.END, f"• {fact['entity_name']}: {fact['content'][:50]}...\n")

            if len(base_facts) > 10:
                self.knowledge_display.insert(tk.END, f"... 还有 {len(base_facts) - 10} 条\n")

            self.knowledge_display.insert(tk.END, f"\n\n【知识实体】({len(entities)} 个)\n")
            self.knowledge_display.insert(tk.END, "=" * 40 + "\n\n")

            for entity in entities[:20]:
                self.knowledge_display.insert(tk.END, f"• {entity['name']} (创建于 {entity['created_at'][:10]})\n")

            if len(entities) > 20:
                self.knowledge_display.insert(tk.END, f"... 还有 {len(entities) - 20} 个\n")

            self.knowledge_display.config(state=tk.DISABLED)
        except Exception as e:
            self.debug_logger.log_error("GUI", f"刷新知识库失败: {e}")

    def refresh_events(self):
        """刷新事件列表"""
        if not self.agent:
            return

        try:
            for item in self.event_tree.get_children():
                self.event_tree.delete(item)

            from event_manager import EventType, EventStatus
            all_events = self.agent.event_manager.get_all_events(limit=100)

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

            for event in all_events:
                event_dict = event.to_dict()
                self.event_tree.insert(
                    '', 'end',
                    text=event_dict['event_id'][:8],
                    values=(
                        event_dict['title'],
                        type_map.get(event_dict['event_type'], event_dict['event_type']),
                        priority_map.get(event_dict['priority'], event_dict['priority']),
                        status_map.get(event_dict['status'], event_dict['status']),
                        event_dict['created_at'][:19]
                    ),
                    tags=(event_dict['event_id'],)
                )

            stats = self.agent.event_manager.get_statistics()
            self.event_stats_label.config(
                text=f"总计: {stats['total_events']} | 待处理: {stats['pending']} | 已完成: {stats['completed']}"
            )
        except Exception as e:
            self.debug_logger.log_error("GUI", f"刷新事件列表失败: {e}")

    def refresh_environment(self):
        """刷新环境显示"""
        if not self.agent:
            return

        try:
            environments = self.agent.db.get_all_environments()
            active_env = self.agent.db.get_active_environment()

            self.environment_display.config(state=tk.NORMAL)
            self.environment_display.delete(1.0, tk.END)

            self.environment_display.insert(tk.END, "【智能体视觉环境配置】\n\n")

            if not environments:
                self.environment_display.insert(tk.END, "暂无环境配置。\n\n")
                self.environment_display.insert(tk.END, "💡 提示:\n")
                self.environment_display.insert(tk.END, "- 点击「创建默认」快速创建示例环境\n")
                self.environment_display.insert(tk.END, "- 点击「新建环境」手动创建自定义环境\n")
            else:
                self.environment_display.insert(tk.END, f"共有 {len(environments)} 个环境\n")
                if active_env:
                    self.environment_display.insert(tk.END, f"当前激活: {active_env['name']}\n")
                self.environment_display.insert(tk.END, "=" * 50 + "\n\n")

                for env in environments:
                    is_active = env['uuid'] == active_env['uuid'] if active_env else False
                    status_icon = "🟢" if is_active else "⚪"

                    self.environment_display.insert(tk.END, f"{status_icon} 【{env['name']}】\n")
                    self.environment_display.insert(tk.END, f"   描述: {env['overall_description'][:50]}...\n")
                    
                    objects = self.agent.db.get_environment_objects(env['uuid'])
                    self.environment_display.insert(tk.END, f"   物体数量: {len(objects)}\n\n")

            self.environment_display.config(state=tk.DISABLED)
        except Exception as e:
            self.debug_logger.log_error("GUI", f"刷新环境显示失败: {e}")

    def update_topic_timeline(self):
        """更新主题时间线"""
        if not self.agent:
            return

        try:
            summaries = self.agent.get_long_term_summaries()
            self.topic_timeline.update_topics(summaries)
        except Exception as e:
            self.debug_logger.log_error("GUI", f"更新主题时间线失败: {e}")

    def update_info_display(self):
        """更新系统信息显示"""
        if not self.agent:
            return

        try:
            stats = self.agent.get_memory_stats()

            info_text = "【系统信息】\n\n"
            info_text += f"角色: {self.agent.character.name}\n"
            info_text += f"身份: {self.agent.character.role}\n"
            info_text += f"性格: {self.agent.character.personality}\n\n"
            info_text += "【记忆统计】\n"
            info_text += f"短期记忆轮数: {stats.get('short_term', {}).get('rounds', 0)}\n"
            info_text += f"短期记忆消息: {stats.get('short_term', {}).get('message_count', 0)}\n"
            info_text += f"长期记忆概括: {len(self.agent.get_long_term_summaries())}\n"
            info_text += f"知识库实体: {stats.get('knowledge_base', {}).get('total_knowledge', 0)}\n"

            self.info_display.config(state=tk.NORMAL)
            self.info_display.delete(1.0, tk.END)
            self.info_display.insert(tk.END, info_text)
            self.info_display.config(state=tk.DISABLED)
        except Exception as e:
            self.debug_logger.log_error("GUI", f"更新系统信息失败: {e}")

    def update_understanding_display(self, understanding_result):
        """更新理解阶段显示"""
        self.understanding_display.config(state=tk.NORMAL)
        self.understanding_display.delete(1.0, tk.END)

        if understanding_result:
            self.understanding_display.insert(tk.END, "【用户意图理解】\n\n")
            self.understanding_display.insert(tk.END, json.dumps(understanding_result, ensure_ascii=False, indent=2))
        else:
            self.understanding_display.insert(tk.END, "暂无理解阶段数据")

        self.understanding_display.config(state=tk.DISABLED)

    # ==================== 情感分析 ====================

    def analyze_emotion(self):
        """分析情感关系"""
        if not self.agent:
            messagebox.showerror("错误", "聊天代理未初始化")
            return

        self.update_status("分析情感中...", ColorTheme.STATUS_WARNING)

        def do_analyze():
            try:
                result = self.agent.analyze_emotion()
                self.root.after(0, lambda: self.update_emotion_display(result))
                self.root.after(0, lambda: self.update_status("就绪", ColorTheme.STATUS_OK))
            except Exception as e:
                self.root.after(0, lambda: self.update_status("分析失败", ColorTheme.STATUS_ERROR))
                self.root.after(0, lambda: messagebox.showerror("错误", f"情感分析失败: {e}"))

        thread = threading.Thread(target=do_analyze, daemon=True)
        thread.start()

    def update_emotion_display(self, emotion_data):
        """更新情感显示"""
        if not emotion_data:
            return

        self.emotion_canvas.update_emotion(emotion_data)

        self.emotion_info_text.config(state=tk.NORMAL)
        self.emotion_info_text.delete(1.0, tk.END)

        try:
            info = format_emotion_summary(emotion_data)
            self.emotion_info_text.insert(tk.END, info)
        except Exception:
            self.emotion_info_text.insert(tk.END, json.dumps(emotion_data, ensure_ascii=False, indent=2))

        self.emotion_info_text.config(state=tk.DISABLED)

    # ==================== 其他功能方法 ====================

    def search_knowledge(self):
        """搜索知识库"""
        search_text = self.kb_search_var.get().strip()
        if not search_text:
            self.refresh_knowledge()
            return

        if not self.agent:
            messagebox.showerror("错误", "聊天代理未初始化，无法搜索知识库")
            return

        # 使用知识库本地搜索
        self.update_status("搜索知识库中...", ColorTheme.STATUS_WARNING)

        def do_search():
            try:
                # 在知识库中搜索实体和基础知识
                entities = self.agent.db.get_all_entities()
                base_facts = self.agent.db.get_all_base_facts()
                
                # 过滤匹配的实体
                matched_entities = [e for e in entities if search_text.lower() in e.get('name', '').lower()]
                matched_facts = [f for f in base_facts if search_text.lower() in f.get('entity_name', '').lower() or search_text.lower() in f.get('content', '').lower()]
                
                result_text = f"搜索关键词: {search_text}\n\n"
                result_text += f"【匹配的实体】({len(matched_entities)} 个)\n"
                for e in matched_entities[:10]:
                    result_text += f"• {e.get('name', '')}\n"
                if len(matched_entities) > 10:
                    result_text += f"... 还有 {len(matched_entities) - 10} 个\n"
                    
                result_text += f"\n【匹配的基础知识】({len(matched_facts)} 条)\n"
                for f in matched_facts[:10]:
                    result_text += f"• {f.get('entity_name', '')}: {f.get('content', '')[:50]}...\n"
                if len(matched_facts) > 10:
                    result_text += f"... 还有 {len(matched_facts) - 10} 条\n"

                def on_success():
                    messagebox.showinfo("搜索结果", result_text)
                    self.update_status("就绪", ColorTheme.STATUS_OK)

                self.root.after(0, on_success)
            except Exception as e:
                def on_error():
                    self.update_status("搜索失败", ColorTheme.STATUS_ERROR)
                    messagebox.showerror("错误", f"知识库搜索失败: {e}")

                self.root.after(0, on_error)

        thread = threading.Thread(target=do_search, daemon=True)
        thread.start()

    def create_new_event(self):
        """创建新事件"""
        from event_manager import EventType, EventPriority

        dialog = tk.Toplevel(self.root)
        dialog.title("创建新事件")
        dialog.geometry("500x500")
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.configure(bg=ColorTheme.BG_MAIN)

        container = ttk.Frame(dialog, padding=20)
        container.pack(fill=tk.BOTH, expand=True)

        ttk.Label(container, text="事件标题:").pack(anchor=tk.W, pady=(0, 5))
        title_entry = ttk.Entry(container)
        title_entry.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(container, text="事件描述:").pack(anchor=tk.W, pady=(0, 5))
        desc_text = scrolledtext.ScrolledText(container, height=5)
        desc_text.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(container, text="事件类型:").pack(anchor=tk.W, pady=(0, 5))
        type_var = tk.StringVar(value="notification")
        type_frame = ttk.Frame(container)
        type_frame.pack(fill=tk.X, pady=(0, 10))
        ttk.Radiobutton(type_frame, text="通知型", variable=type_var, value="notification").pack(side=tk.LEFT)
        ttk.Radiobutton(type_frame, text="任务型", variable=type_var, value="task").pack(side=tk.LEFT)

        ttk.Label(container, text="优先级:").pack(anchor=tk.W, pady=(0, 5))
        priority_var = tk.IntVar(value=2)
        priority_frame = ttk.Frame(container)
        priority_frame.pack(fill=tk.X, pady=(0, 10))
        for val, text in [(1, "低"), (2, "中"), (3, "高"), (4, "紧急")]:
            ttk.Radiobutton(priority_frame, text=text, variable=priority_var, value=val).pack(side=tk.LEFT, padx=5)

        def do_create():
            title = title_entry.get().strip()
            if not title:
                messagebox.showwarning("警告", "请输入事件标题！")
                return

            description = desc_text.get("1.0", tk.END).strip()
            event_type = EventType.TASK if type_var.get() == "task" else EventType.NOTIFICATION
            priority = EventPriority(priority_var.get())

            try:
                event = self.agent.event_manager.create_event(
                    title=title,
                    description=description,
                    event_type=event_type,
                    priority=priority
                )
                messagebox.showinfo("成功", f"事件创建成功！\nID: {event.event_id[:8]}...")
                self.refresh_events()
                dialog.destroy()
            except Exception as e:
                messagebox.showerror("错误", f"创建失败：{str(e)}")

        def on_close():
            """统一处理事件创建对话框的关闭逻辑"""
            dialog.destroy()

        btn_frame = ttk.Frame(container)
        btn_frame.pack(pady=20)
        ttk.Button(btn_frame, text="创建", command=do_create, width=15).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="取消", command=on_close, width=15).pack(side=tk.LEFT, padx=5)

        # 确保点击窗口关闭按钮(X)时也执行统一的关闭逻辑
        dialog.protocol("WM_DELETE_WINDOW", on_close)

    def trigger_event(self):
        """触发选中的事件"""
        selection = self.event_tree.selection()
        if not selection:
            messagebox.showwarning("警告", "请先选择一个事件！")
            return

        item_tags = self.event_tree.item(selection[0], 'tags')
        if not item_tags:
            return

        event_id = item_tags[0]
        
        def process():
            try:
                self.update_status("处理事件中...", ColorTheme.STATUS_WARNING)
                result_message = self.agent.handle_event(event_id)
                self.root.after(0, lambda: self.add_system_message(result_message))
                self.root.after(0, lambda: self.update_status("就绪", ColorTheme.STATUS_OK))
                self.root.after(0, self.refresh_events)
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("错误", f"处理失败: {e}"))
                self.root.after(0, lambda: self.update_status("出错", ColorTheme.STATUS_ERROR))

        thread = threading.Thread(target=process, daemon=True)
        thread.start()

    def create_new_environment(self):
        """创建新环境"""
        dialog = tk.Toplevel(self.root)
        dialog.title("创建新环境")
        dialog.geometry("500x400")
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.configure(bg=ColorTheme.BG_MAIN)

        container = ttk.Frame(dialog, padding=20)
        container.pack(fill=tk.BOTH, expand=True)

        ttk.Label(container, text="环境名称:").pack(anchor=tk.W, pady=(0, 5))
        name_entry = ttk.Entry(container)
        name_entry.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(container, text="整体描述:").pack(anchor=tk.W, pady=(0, 5))
        desc_text = scrolledtext.ScrolledText(container, height=6)
        desc_text.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(container, text="氛围:").pack(anchor=tk.W, pady=(0, 5))
        atmosphere_entry = ttk.Entry(container)
        atmosphere_entry.pack(fill=tk.X, pady=(0, 10))

        def save():
            name = name_entry.get().strip()
            desc = desc_text.get("1.0", tk.END).strip()

            missing_fields = []
            if not name:
                missing_fields.append("名称")
            if not desc:
                missing_fields.append("描述")
            if missing_fields:
                messagebox.showerror("错误", "、".join(missing_fields) + " 不能为空！")
                return

            try:
                env_uuid = self.agent.db.create_environment(
                    name=name,
                    overall_description=desc,
                    atmosphere=atmosphere_entry.get().strip()
                )

                all_envs = self.agent.db.get_all_environments()
                if len(all_envs) == 1:
                    self.agent.db.set_active_environment(env_uuid)

                messagebox.showinfo("成功", f"环境创建成功！\nUUID: {env_uuid[:8]}...")
                dialog.destroy()
                self.refresh_environment()
            except Exception as e:
                messagebox.showerror("错误", f"创建失败: {e}")

        btn_frame = ttk.Frame(container)
        btn_frame.pack(pady=20)
        ttk.Button(btn_frame, text="保存", command=save, width=15).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="取消", command=dialog.destroy, width=15).pack(side=tk.LEFT, padx=5)

    def add_new_object(self):
        """添加新物体"""
        active_env = self.agent.db.get_active_environment()
        if not active_env:
            messagebox.showerror("错误", "请先创建并激活一个环境！")
            return

        dialog = tk.Toplevel(self.root)
        dialog.title(f"添加物体到: {active_env['name']}")
        dialog.geometry("500x400")
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.configure(bg=ColorTheme.BG_MAIN)

        container = ttk.Frame(dialog, padding=20)
        container.pack(fill=tk.BOTH, expand=True)

        ttk.Label(container, text="物体名称:").pack(anchor=tk.W, pady=(0, 5))
        name_entry = ttk.Entry(container)
        name_entry.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(container, text="物体描述:").pack(anchor=tk.W, pady=(0, 5))
        desc_text = scrolledtext.ScrolledText(container, height=6)
        desc_text.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(container, text="位置:").pack(anchor=tk.W, pady=(0, 5))
        position_entry = ttk.Entry(container)
        position_entry.pack(fill=tk.X, pady=(0, 10))

        def save():
            name = name_entry.get().strip()
            desc = desc_text.get("1.0", tk.END).strip()

            if not name or not desc:
                messagebox.showerror("错误", "名称和描述不能为空！")
                return

            try:
                obj_uuid = self.agent.db.add_environment_object(
                    environment_uuid=active_env['uuid'],
                    name=name,
                    description=desc,
                    position=position_entry.get().strip()
                )
                messagebox.showinfo("成功", f"物体添加成功！\nUUID: {obj_uuid[:8]}...")
                dialog.destroy()
                self.refresh_environment()
            except Exception as e:
                messagebox.showerror("错误", f"添加失败: {e}")

        btn_frame = ttk.Frame(container)
        btn_frame.pack(pady=20)
        ttk.Button(btn_frame, text="保存", command=save, width=15).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="取消", command=dialog.destroy, width=15).pack(side=tk.LEFT, padx=5)

    def create_default_environment(self):
        """创建默认环境"""
        result = messagebox.askyesno("确认", "将创建默认示例环境，确定吗？")
        if result:
            try:
                env_uuid = self.agent.vision_tool.create_default_environment()
                messagebox.showinfo("成功", f"默认环境创建成功！\nUUID: {env_uuid[:8]}...")
                self.refresh_environment()
            except Exception as e:
                messagebox.showerror("错误", f"创建失败: {e}")

    def clear_short_term(self):
        """清空短期记忆"""
        if messagebox.askyesno("确认", "确定要清空所有短期记忆吗？"):
            if self.agent.db.clear_short_term_memory():
                self.refresh_short_term()
                self.add_system_message("短期记忆已清空")

    def clear_long_term(self):
        """清空长期记忆"""
        if messagebox.askyesno("确认", "确定要清空所有长期记忆吗？"):
            if self.agent.db.clear_long_term_memory():
                self.refresh_long_term()
                self.update_topic_timeline()
                self.add_system_message("长期记忆已清空")

    def clear_all_memory(self):
        """清空所有记忆"""
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

    def refresh_expression_style(self):
        """刷新表达风格显示"""
        if not self.agent:
            return

        try:
            agent_expressions = self.agent.get_agent_expressions()
            user_habits = self.agent.get_user_expression_habits()

            self.style_display.config(state=tk.NORMAL)
            self.style_display.delete(1.0, tk.END)

            self.style_display.insert(tk.END, "【智能体表达】\n\n")
            if agent_expressions:
                for expr in agent_expressions:
                    self.style_display.insert(tk.END, f"• '{expr['expression']}' => {expr['meaning']}\n")
            else:
                self.style_display.insert(tk.END, "暂无\n")

            self.style_display.insert(tk.END, "\n【用户习惯】\n\n")
            if user_habits:
                for habit in user_habits:
                    self.style_display.insert(tk.END, f"• '{habit['expression_pattern']}' => {habit['meaning']}\n")
            else:
                self.style_display.insert(tk.END, "暂无\n")

            self.style_display.config(state=tk.DISABLED)
        except Exception as e:
            print(f"刷新表达风格失败: {e}")

    def add_agent_expression(self):
        """添加智能体表达"""
        expression = simpledialog.askstring("添加表达", "请输入表达方式:")
        if not expression:
            return

        meaning = simpledialog.askstring("添加表达", "请输入含义:")
        if not meaning:
            return

        try:
            self.agent.add_agent_expression(expression, meaning, "通用")
            messagebox.showinfo("成功", f"已添加表达: '{expression}'")
            self.refresh_expression_style()
        except Exception as e:
            messagebox.showerror("错误", f"添加失败: {e}")

    def learn_user_expressions(self):
        """学习用户表达"""
        if not self.agent:
            return

        try:
            self.update_status("学习用户表达习惯中...", ColorTheme.STATUS_WARNING)
            learned = self.agent.learn_user_expressions_now()
            self.update_status("就绪", ColorTheme.STATUS_OK)

            if learned:
                messagebox.showinfo("成功", f"学习到 {len(learned)} 个用户表达习惯")
            else:
                messagebox.showinfo("提示", "未发现新的表达习惯")

            self.refresh_expression_style()
        except Exception as e:
            messagebox.showerror("错误", f"学习失败: {e}")
            self.update_status("就绪", ColorTheme.STATUS_OK)

    def refresh_debug_log(self):
        """刷新Debug日志"""
        if not hasattr(self, 'debug_display'):
            return

        logs = self.debug_logger.get_recent_logs(100)

        self.debug_display.config(state=tk.NORMAL)
        self.debug_display.delete(1.0, tk.END)

        for log in logs:
            formatted = self.debug_logger.format_log_for_display(log)
            log_type = log.get('type', 'info')
            self.debug_display.insert(tk.END, formatted + "\n", log_type)

        self.debug_display.config(state=tk.DISABLED)

    def clear_debug_log(self):
        """清空Debug日志"""
        if messagebox.askyesno("确认", "确定要清空Debug日志吗？"):
            self.debug_logger.clear_logs()
            if hasattr(self, 'debug_display'):
                self.debug_display.config(state=tk.NORMAL)
                self.debug_display.delete(1.0, tk.END)
                self.debug_display.config(state=tk.DISABLED)

    def _on_debug_log_added(self, log_entry):
        """Debug日志添加回调"""
        if not hasattr(self, 'debug_display'):
            return

        def update():
            self.debug_display.config(state=tk.NORMAL)
            formatted = self.debug_logger.format_log_for_display(log_entry)
            log_type = log_entry.get('type', 'info')
            self.debug_display.insert(tk.END, formatted + "\n", log_type)
            self.debug_display.see(tk.END)
            self.debug_display.config(state=tk.DISABLED)

        self.root.after(0, update)

    def show_about(self):
        """显示关于对话框"""
        about_text = """
智能对话代理 v4.0 PyCharm风格版

功能特性:
• PyCharm风格的现代化界面
• 统一的时间轴数据展示
• 角色扮演对话
• 三层记忆系统
• 情感关系分析
• 知识库管理
• 事件驱动系统
• 环境视觉模拟

技术栈: Python + Tkinter + LangChain
开发: 2025
        """
        messagebox.showinfo("关于", about_text)


# ==================== 主函数 ====================
def main():
    """主函数"""
    root = tk.Tk()
    PyCharmStyleGUI(root)
    root.mainloop()


if __name__ == '__main__':
    main()
