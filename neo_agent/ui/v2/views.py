"""
Neo Agent TUI 视图组件
完善各功能视图的实现
"""
import asyncio
from datetime import datetime
from typing import Optional
from textual.app import ComposeResult
from textual.message import Message
from textual.message import Message
from textual.containers import Container, Horizontal, Vertical, ScrollableContainer
from textual.widgets import Static, Button, Input, RichLog, DataTable, Label
from textual.reactive import reactive
from rich.text import Text
from rich.table import Table as RichTable

from neo_agent.ui.v2.client import AgentClient


class ChatView(Vertical):
    """对话视图"""
    
    class ChatUpdated(Message):
        """对话更新消息"""
        def __init__(self, reply: str, emotion: dict, scene: dict):
            super().__init__()
            self.reply = reply
            self.emotion = emotion
            self.scene = scene
    
    def __init__(self, client: AgentClient, **kwargs):
        super().__init__(**kwargs)
        self.client = client
        self.add_class("view-container")
    
    def compose(self) -> ComposeResult:
        yield RichLog(id="chat-log", classes="chat-log", wrap=True, markup=True)
        with Horizontal(classes="chat-input-container"):
            yield Input(placeholder="输入消息... (Ctrl+Enter 发送)", id="chat-input", classes="chat-input")
            yield Button("发送", variant="primary", id="send-button")
    
    async def on_mount(self):
        """挂载时加载历史消息"""
        log = self.query_one("#chat-log", RichLog)
        log.write("[bold #E9A568]欢迎使用 Neo Agent！[/bold #E9A568]")
        log.write("[dim]正在加载历史消息...[/dim]")
        
        try:
            history = await self.client.call("session.get_history", {"limit": 20})
            log.clear()
            log.write("[bold #E9A568]═══ 对话历史 ═══[/bold #E9A568]\n")
            
            for msg in reversed(history):
                role = msg.get("role", "user")
                content = msg.get("content", "")
                
                if role == "user":
                    log.write(f"[bold #F5E6D3]你[/bold #F5E6D3]: {content}")
                else:
                    log.write(f"[bold #E9A568]林依[/bold #E9A568]: {content}")
            
            log.write("\n[dim]─────────────────[/dim]\n")
        except Exception as e:
            log.clear()
            log.write(f"[yellow]无法加载历史消息: {e}[/yellow]")
    
    async def on_button_pressed(self, event: Button.Pressed):
        """发送按钮点击"""
        if event.button.id == "send-button":
            await self._send_message()
    
    async def on_input_submitted(self, event: Input.Submitted):
        """输入框提交"""
        if event.input.id == "chat-input":
            await self._send_message()
    
    async def _send_message(self):
        """发送消息到 Agent"""
        input_widget = self.query_one("#chat-input", Input)
        log = self.query_one("#chat-log", RichLog)
        
        message = input_widget.value.strip()
        if not message:
            return
        
        input_widget.value = ""
        
        log.write(f"\n[bold #F5E6D3]你[/bold #F5E6D3]: {message}")
        log.write("[dim #8A6B4F]思考中...[/dim #8A6B4F]")
        
        try:
            result = await self.client.call("session.send_message", {"text": message})
            
            reply = result.get("reply", "")
            emotion = result.get("emotion", {})
            scene = result.get("scene", {})
            
            log.write(f"[bold #E9A568]林依[/bold #E9A568]: {reply}")
            
            self.post_message(self.ChatUpdated(reply, emotion, scene))
            
        except Exception as e:
            log.write(f"[bold red]错误[/bold red]: {str(e)}")


class ItineraryView(Vertical):
    """今日行程视图 - 时间线展示"""
    
    def __init__(self, client: AgentClient, **kwargs):
        super().__init__(**kwargs)
        self.client = client
        self.add_class("view-container")
    
    def compose(self) -> ComposeResult:
        yield Static("今日行程", classes="view-title")
        with Horizontal(classes="action-bar"):
            yield Button("刷新", id="refresh-itinerary", variant="primary")
            yield Button("生成计划", id="generate-itinerary")
        yield DataTable(id="itinerary-table", classes="itinerary-table")
        yield RichLog(id="itinerary-details", classes="detail-log", wrap=True, markup=True)
    
    async def on_mount(self):
        table = self.query_one("#itinerary-table", DataTable)
        table.add_columns("时间", "活动", "地点", "类型", "状态")
        table.cursor_type = "row"
        await self.refresh_itinerary()
    
    async def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == "refresh-itinerary":
            await self.refresh_itinerary()
        elif event.button.id == "generate-itinerary":
            await self.generate_today_itinerary()
    
    async def on_data_table_row_selected(self, event: DataTable.RowSelected):
        """显示选中行程的详情"""
        table = self.query_one("#itinerary-table", DataTable)
        details_log = self.query_one("#itinerary-details", RichLog)
        
        if event.row_key.value < len(self.current_data):
            item = self.current_data[event.row_key.value]
            details_log.clear()
            details_log.write(f"[bold #E9A568]活动详情[/bold #E9A568]\n")
            details_log.write(f"时间: {item.get('time', '')}")
            details_log.write(f"活动: {item.get('activity', '')}")
            details_log.write(f"地点: {item.get('location', '未指定')}")
            details_log.write(f"区域: {item.get('area', '未指定')}")
            details_log.write(f"类型: {item.get('schedule_type', 'agent')}")
            details_log.write(f"状态: {item.get('status', '待开始')}")
            if item.get('description'):
                details_log.write(f"\n描述: {item['description']}")
    
    async def refresh_itinerary(self):
        table = self.query_one("#itinerary-table", DataTable)
        details_log = self.query_one("#itinerary-details", RichLog)
        
        table.clear()
        details_log.clear()
        details_log.write("[dim]正在加载今日行程...[/dim]")
        
        try:
            result = await self.client.call("schedule.get_today_itinerary", {})
            items = result.get("items", [])
            
            if not items:
                details_log.write("[dim]今日暂无行程[/dim]")
                self.current_data = []
                return
            
            self.current_data = items
            details_log.clear()
            
            for idx, item in enumerate(items):
                time_str = item.get("time", "")
                activity = item.get("activity", "")
                location = item.get("location", "未指定")
                schedule_type = item.get("schedule_type", "agent")
                status = item.get("status", "待开始")
                
                # 类型标记
                type_marker = {"agent": "🤖", "user": "👤", "shared": "🤝"}.get(schedule_type, "📅")
                # 状态颜色
                status_color = {"进行中": "#E9A568", "已完成": "#A8C079", "待开始": "#8A7A66"}.get(status, "#8A7A66")
                
                table.add_row(
                    time_str,
                    activity,
                    location,
                    type_marker + " " + schedule_type,
                    Text(status, style=status_color),
                    key=str(idx)
                )
            
            details_log.write(f"[bold #C9B89A]共 {len(items)} 项行程[/bold #C9B89A]")
            details_log.write("[dim]点击行程查看详情[/dim]")
            
        except Exception as e:
            details_log.write(f"[dim red]加载失败: {e}[/dim red]")
            self.current_data = []
    
    async def generate_today_itinerary(self):
        details_log = self.query_one("#itinerary-details", RichLog)
        details_log.clear()
        details_log.write("[dim]正在生成今日计划...[/dim]")
        
        try:
            result = await self.client.call("schedule.generate_daily_itinerary", {})
            if result.get("success"):
                details_log.write("[#A8C079]✓ 计划生成成功[/#A8C079]")
                await asyncio.sleep(1)
                await self.refresh_itinerary()
            else:
                details_log.write(f"[dim red]生成失败: {result.get('error', '未知错误')}[/dim red]")
        except Exception as e:
            details_log.write(f"[dim red]生成失败: {e}[/dim red]")


class ScenePoolView(Vertical):
    """场景池视图 - 已访问场景与详情"""
    
    def __init__(self, client: AgentClient, **kwargs):
        super().__init__(**kwargs)
        self.client = client
        self.add_class("view-container")
        self.current_scenes = []
    
    def compose(self) -> ComposeResult:
        yield Static("场景池", classes="view-title")
        yield Button("刷新", id="refresh-scenes", variant="primary", classes="refresh-button")
        
        with Horizontal(classes="split-view"):
            with Vertical(classes="scene-list"):
                yield Static("已访问场景", classes="section-header")
                yield DataTable(id="scenes-table", classes="scenes-table")
            
            with Vertical(classes="scene-detail"):
                yield Static("场景详情", classes="section-header")
                yield RichLog(id="scene-details", classes="detail-log", wrap=True, markup=True)
    
    async def on_mount(self):
        table = self.query_one("#scenes-table", DataTable)
        table.add_columns("场景", "状态")
        table.cursor_type = "row"
        await self.refresh_scenes()
    
    async def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == "refresh-scenes":
            await self.refresh_scenes()
    
    async def on_data_table_row_selected(self, event: DataTable.RowSelected):
        """显示选中场景的详情"""
        details_log = self.query_one("#scene-details", RichLog)
        
        if event.row_key.value < len(self.current_scenes):
            scene = self.current_scenes[event.row_key.value]
            details_log.clear()
            
            name = scene.get("name", "未知场景")
            location = scene.get("location", {})
            areas = scene.get("areas", [])
            objects_list = scene.get("objects", [])
            frozen = scene.get("layout_frozen", False)
            
            details_log.write(f"[bold #E9A568]{name}[/bold #E9A568]\n")
            details_log.write(f"状态: {'已固化' if frozen else '可编辑'}\n")
            
            if isinstance(location, dict):
                details_log.write(f"[bold #C9B89A]地点信息[/bold #C9B89A]")
                details_log.write(f"  {location.get('description', '无描述')}\n")
            
            if areas:
                details_log.write(f"[bold #C9B89A]区域 ({len(areas)})[/bold #C9B89A]")
                for area in areas:
                    details_log.write(f"  • {area.get('name', '未命名区域')}")
            
            if objects_list:
                details_log.write(f"\n[bold #C9B89A]物体 ({len(objects_list)})[/bold #C9B89A]")
                for obj in objects_list[:10]:  # 只显示前10个
                    details_log.write(f"  • {obj.get('name', '未命名物体')}")
                if len(objects_list) > 10:
                    details_log.write(f"  ... 还有 {len(objects_list) - 10} 个物体")
    
    async def refresh_scenes(self):
        table = self.query_one("#scenes-table", DataTable)
        details_log = self.query_one("#scene-details", RichLog)
        
        table.clear()
        details_log.clear()
        details_log.write("[dim]正在加载场景池...[/dim]")
        
        try:
            result = await self.client.call("scene.list_pool", {})
            scenes = result.get("scenes", [])
            current_scene = result.get("current_scene", {})
            
            if not scenes:
                details_log.write("[dim]暂无已访问场景[/dim]")
                self.current_scenes = []
                return
            
            self.current_scenes = scenes
            details_log.clear()
            
            # 先显示当前场景
            if current_scene:
                details_log.write(f"[bold #E9A568]当前场景:[/bold #E9A568]")
                details_log.write(f"  {current_scene.get('location', '未知')} - {current_scene.get('area', '未知')}\n")
            
            details_log.write("[dim]点击场景查看详情[/dim]")
            
            # 填充表格
            for idx, scene in enumerate(scenes):
                name = scene.get("name", "未命名场景")
                frozen = scene.get("layout_frozen", False)
                is_current = (current_scene.get('location') == scene.get('location'))
                
                status_icon = "★" if is_current else ("🔒" if frozen else "📝")
                status_text = "当前" if is_current else ("已固化" if frozen else "可编辑")
                
                table.add_row(
                    f"{status_icon} {name}",
                    status_text,
                    key=str(idx)
                )
            
        except Exception as e:
            details_log.write(f"[dim red]加载失败: {e}[/dim red]")
            self.current_scenes = []


class MemoryView(Vertical):
    """记忆与知识视图 - 改进搜索体验"""
    
    def __init__(self, client: AgentClient, **kwargs):
        super().__init__(**kwargs)
        self.client = client
        self.add_class("view-container")
        self.search_history = []
    
    def compose(self) -> ComposeResult:
        yield Static("记忆与知识", classes="view-title")
        
        with Horizontal(classes="search-container"):
            yield Input(placeholder="搜索记忆关键词...", id="memory-search", classes="search-input")
            yield Button("搜索", id="search-memory", variant="primary")
            yield Button("清空", id="clear-memory")
        
        yield Static("搜索结果", classes="section-header")
        yield RichLog(id="memory-results", classes="memory-log", wrap=True, markup=True)
    
    async def on_mount(self):
        log = self.query_one("#memory-results", RichLog)
        log.write("[dim]输入关键词搜索记忆...[/dim]")
        log.write("[dim]提示: 可以搜索对话内容、事件、地点等[/dim]")
    
    async def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == "search-memory":
            await self.search_memory()
        elif event.button.id == "clear-memory":
            input_widget = self.query_one("#memory-search", Input)
            log = self.query_one("#memory-results", RichLog)
            input_widget.value = ""
            log.clear()
            log.write("[dim]已清空搜索结果[/dim]")
    
    async def on_input_submitted(self, event: Input.Submitted):
        if event.input.id == "memory-search":
            await self.search_memory()
    
    async def search_memory(self):
        input_widget = self.query_one("#memory-search", Input)
        log = self.query_one("#memory-results", RichLog)
        
        query = input_widget.value.strip()
        if not query:
            log.clear()
            log.write("[dim]请输入搜索关键词[/dim]")
            return
        
        log.clear()
        log.write(f"[dim]正在搜索: [bold]{query}[/bold]...[/dim]\n")
        
        try:
            result = await self.client.call("memory.search", {"query": query, "limit": 20})
            memories = result.get("results", [])
            
            if not memories:
                log.write("[dim]未找到相关记忆[/dim]")
                log.write("[dim]尝试其他关键词或更具体的描述[/dim]")
                return
            
            log.clear()
            log.write(f"[bold #E9A568]找到 {len(memories)} 条相关记忆[/bold #E9A568]\n")
            
            for idx, mem in enumerate(memories, 1):
                content = mem.get("content", "")
                relevance = mem.get("relevance", 0.0)
                timestamp = mem.get("timestamp", "")
                memory_type = mem.get("type", "chat")
                
                # 相关度颜色
                if relevance >= 0.8:
                    rel_color = "#A8C079"
                elif relevance >= 0.6:
                    rel_color = "#E9A568"
                else:
                    rel_color = "#8A7A66"
                
                type_icon = {"chat": "💬", "event": "📅", "knowledge": "📚"}.get(memory_type, "📝")
                
                log.write(f"{idx}. {type_icon} [bold {rel_color}]相关度: {relevance:.2f}[/bold {rel_color}]")
                log.write(f"   {content[:200]}{'...' if len(content) > 200 else ''}")
                log.write(f"   [dim]{timestamp}[/dim]\n")
            
            # 保存搜索历史
            if query not in self.search_history:
                self.search_history.append(query)
            
        except Exception as e:
            log.write(f"[dim red]搜索失败: {e}[/dim red]")


class RelationshipView(Vertical):
    """关系网络视图 - 显示关系历史与变化"""
    
    def __init__(self, client: AgentClient, **kwargs):
        super().__init__(**kwargs)
        self.client = client
        self.add_class("view-container")
    
    def compose(self) -> ComposeResult:
        yield Static("关系网络", classes="view-title")
        yield Button("刷新", id="refresh-relationships", variant="primary", classes="refresh-button")
        
        with Vertical(classes="relationship-container"):
            yield Static("当前关系状态", classes="section-header")
            yield RichLog(id="relationship-status", classes="status-log", wrap=True, markup=True)
            
            yield Static("关系变化历史", classes="section-header")
            yield RichLog(id="relationship-history", classes="history-log", wrap=True, markup=True)
    
    async def on_mount(self):
        await self.refresh_relationships()
    
    async def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == "refresh-relationships":
            await self.refresh_relationships()
    
    async def refresh_relationships(self):
        status_log = self.query_one("#relationship-status", RichLog)
        history_log = self.query_one("#relationship-history", RichLog)
        
        status_log.clear()
        history_log.clear()
        status_log.write("[dim]正在加载关系数据...[/dim]")
        
        try:
            # 获取当前关系状态
            result = await self.client.call("relationship.list_all", {})
            relationships = result.get("relationships", [])
            
            status_log.clear()
            
            if not relationships:
                status_log.write("[dim]暂无关系记录[/dim]")
                status_log.write("[dim]关系会在对话互动中自动建立[/dim]")
                history_log.write("[dim]无历史记录[/dim]")
                return
            
            # 显示当前状态
            for rel in relationships:
                entity = rel.get("entity", "用户")
                score = rel.get("score", 0)
                last_updated = rel.get("last_updated", "")
                
                # 分数颜色
                if score >= 10:
                    score_color = "#A8C079"
                    level = "亲密"
                elif score >= 5:
                    score_color = "#E9A568"
                    level = "友好"
                elif score >= 0:
                    score_color = "#C9B89A"
                    level = "中立"
                elif score >= -5:
                    score_color = "#D4863C"
                    level = "疏远"
                else:
                    score_color = "#D97757"
                    level = "冷淡"
                
                status_log.write(f"[bold #E9A568]{entity}[/bold #E9A568]")
                status_log.write(f"  关系分数: [bold {score_color}]{score:+d}[/bold {score_color}] ({level})")
                status_log.write(f"  最后更新: [dim]{last_updated}[/dim]\n")
            
            # 获取关系历史
            try:
                history_result = await self.client.call("relationship.get_history", {
                    "entity": "user",
                    "limit": 30
                })
                history = history_result.get("history", [])
                
                if history:
                    history_log.write(f"[bold #C9B89A]最近 {len(history)} 次变化[/bold #C9B89A]\n")
                    
                    for event in history:
                        timestamp = event.get("timestamp", "")
                        signal = event.get("signal", "unknown")
                        delta = event.get("score_delta", 0)
                        reason = event.get("reason", "")
                        confidence = event.get("confidence", 0.0)
                        
                        # Delta 颜色
                        delta_color = "#A8C079" if delta > 0 else ("#D97757" if delta < 0 else "#8A7A66")
                        delta_str = f"{delta:+d}"
                        
                        signal_icon = {
                            "positive": "😊",
                            "negative": "😔",
                            "neutral": "😐"
                        }.get(signal, "📝")
                        
                        history_log.write(f"{signal_icon} [{timestamp}]")
                        history_log.write(f"  变化: [bold {delta_color}]{delta_str}[/bold {delta_color}] | 置信度: {confidence:.2f}")
                        history_log.write(f"  原因: {reason}\n")
                else:
                    history_log.write("[dim]暂无历史变化记录[/dim]")
            
            except Exception as e:
                history_log.write(f"[dim red]历史加载失败: {e}[/dim red]")
            
        except Exception as e:
            status_log.write(f"[dim red]加载失败: {e}[/dim red]")


class AuditView(Vertical):
    """审计日志视图 - 添加过滤功能"""
    
    def __init__(self, client: AgentClient, **kwargs):
        super().__init__(**kwargs)
        self.client = client
        self.add_class("view-container")
        self.current_filter = "all"
    
    def compose(self) -> ComposeResult:
        yield Static("审计日志", classes="view-title")
        
        with Horizontal(classes="action-bar"):
            yield Button("全部", id="filter-all", variant="primary")
            yield Button("高风险", id="filter-high")
            yield Button("中风险", id="filter-medium")
            yield Button("低风险", id="filter-low")
            yield Button("刷新", id="refresh-audit")
        
        yield RichLog(id="audit-log", classes="audit-log", wrap=True, markup=True)
    
    async def on_mount(self):
        await self.refresh_audit()
    
    async def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == "refresh-audit":
            await self.refresh_audit()
        elif event.button.id.startswith("filter-"):
            # 更新过滤器
            filter_type = event.button.id.replace("filter-", "")
            self.current_filter = filter_type
            
            # 更新按钮样式
            for btn in self.query("Button"):
                if btn.id and btn.id.startswith("filter-"):
                    btn.variant = "primary" if btn.id == event.button.id else "default"
            
            await self.refresh_audit()
    
    async def refresh_audit(self):
        log = self.query_one("#audit-log", RichLog)
        log.clear()
        log.write("[dim]正在加载审计日志...[/dim]")
        
        try:
            result = await self.client.call("audit.list_recent", {"limit": 100})
            audits = result.get("audits", [])
            
            if not audits:
                log.write("[dim]暂无审计记录[/dim]")
                return
            
            # 过滤
            if self.current_filter != "all":
                audits = [a for a in audits if a.get("risk_level") == self.current_filter]
            
            log.clear()
            log.write(f"[bold #E9A568]审计日志 (过滤: {self.current_filter})[/bold #E9A568]")
            log.write(f"[dim]共 {len(audits)} 条记录[/dim]\n")
            
            for audit in audits:
                timestamp = audit.get("timestamp", "")
                operation = audit.get("operation", "")
                risk_level = audit.get("risk_level", "low")
                details = audit.get("details", "")
                result_status = audit.get("result", "success")
                
                # 风险颜色
                risk_colors = {
                    "high": "#D97757",
                    "medium": "#E9A568",
                    "low": "#A8C079"
                }
                risk_color = risk_colors.get(risk_level, "#8A7A66")
                
                # 结果图标
                result_icon = "✓" if result_status == "success" else "✗"
                
                log.write(f"[{risk_color}]●[/{risk_color}] [{timestamp}] {result_icon} {operation}")
                if details:
                    log.write(f"   {details}")
                log.write("")
            
        except Exception as e:
            log.write(f"[dim red]加载失败: {e}[/dim red]")
