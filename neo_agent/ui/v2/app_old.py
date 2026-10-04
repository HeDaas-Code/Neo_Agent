"""Neo Agent TUI v2 主应用"""
import asyncio
from datetime import datetime
from typing import Optional

from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Static, Footer, RichLog, Input, Button
from textual.reactive import reactive

from .client import AgentClient
from .theme import FULL_THEME


class StatusBar(Static):
    """顶栏状态栏"""
    
    character_name = reactive("连接中...")
    scene_info = reactive("")
    emotion = reactive("")
    time_str = reactive("")
    
    def compose(self) -> ComposeResult:
        yield Static("", id="status-content", classes="status-bar")
    
    def on_mount(self):
        self.set_interval(1.0, self.update_time)
        self.update_display()
    
    def update_time(self):
        self.time_str = datetime.now().strftime("%H:%M")
        self.update_display()
    
    def update_display(self):
        content = f"{self.character_name}"
        if self.scene_info:
            content += f" • {self.scene_info}"
        if self.emotion:
            content += f" • {self.emotion}"
        content += f" • {self.time_str}"
        
        status_widget = self.query_one("#status-content", Static)
        status_widget.update(content)


class NavigationItem(Button):
    """导航项"""
    
    def __init__(self, label: str, view_id: str, **kwargs):
        super().__init__(label, **kwargs)
        self.label_text = label
        self.view_id = view_id
        self.variant = "default"
        self.add_class("nav-item")
    
    def on_button_pressed(self, event: Button.Pressed):
        """处理自己的点击事件"""
        event.stop()  # 阻止冒泡
        # 获取应用并调用 switch_view
        if hasattr(self.app, 'switch_view'):
            self.app.run_worker(self.app.switch_view(self.view_id))


class Sidebar(Vertical):
    """左侧导航栏"""
    
    def compose(self) -> ComposeResult:
        yield Static("", classes="nav-section-header")
        yield NavigationItem("💬 对话", "chat")
        yield NavigationItem("📅 今日行程", "itinerary")
        yield NavigationItem("🌍 场景池", "scenes")
        yield NavigationItem("🧠 记忆与知识", "memory")
        yield NavigationItem("💭 关系网络", "relationships")
        yield NavigationItem("🔍 审计日志", "audit")
        yield Static("─── 设置 ───", classes="nav-section-header")
        yield Static(":config 全局配置", classes="nav-item")
        yield Static(":debug  开发模式", classes="nav-item")
        yield Static(":export 导出数据", classes="nav-item")


class ChatView(Vertical):
    """对话视图"""
    
    def __init__(self, client: AgentClient, **kwargs):
        super().__init__(**kwargs)
        self.client = client
        self.add_class("chat-container")
    
    def compose(self) -> ComposeResult:
        with Vertical():
            yield RichLog(id="chat-log", classes="chat-log", wrap=True, markup=True)
            with Horizontal(classes="chat-input-container"):
                yield Input(placeholder="输入消息... (Ctrl+Enter 发送)", id="chat-input")
                yield Button("发送", variant="primary", id="send-button")
    
    async def on_mount(self):
        """挂载时初始化"""
        self.query_one("#chat-log", RichLog).write("欢迎使用 Neo Agent！")
        self.query_one("#chat-log", RichLog).write("[dim]正在连接服务...[/dim]")
    
    async def on_input_submitted(self, event: Input.Submitted):
        """处理输入提交"""
        if event.input.id == "chat-input":
            await self.send_message()
    
    async def on_button_pressed(self, event: Button.Pressed):
        """处理按钮点击"""
        # 只处理发送按钮
        """处理按钮点击"""
        if event.button.id == "send-button":
            await self.send_message()
    
    async def send_message(self):
        """发送消息"""
        input_widget = self.query_one("#chat-input", Input)
        log_widget = self.query_one("#chat-log", RichLog)
        
        message = input_widget.value.strip()
        if not message:
            return
        
        # 清空输入框
        input_widget.value = ""
        
        # 显示用户消息
        log_widget.write(f"[bold $accent-primary]你:[/bold $accent-primary] {message}")
        
        # 显示加载状态
        log_widget.write("[dim]思考中...[/dim]")
        
        try:
            # 异步发送消息
            result = await self.client.send_message(message)
            
            # 移除"思考中"
            # （Textual RichLog 不支持删除最后一行，这里暂时跳过）
            
            # 显示回复
            reply = result.get("reply", "")
            emotion = result.get("emotion", {})
            
            emotion_str = ""
            if emotion:
                emotion_state = emotion.get("state", "")
                if emotion_state:
                    emotion_str = f" [dim]({emotion_state})[/dim]"
            
            log_widget.write(f"[bold $accent-secondary]林依:[/bold $accent-secondary]{emotion_str} {reply}")
            
        except Exception as e:
            log_widget.write(f"[bold $status-error]错误:[/bold $status-error] {str(e)}")


class ItineraryView(Vertical):
    """今日行程视图"""
    
    def __init__(self, client: AgentClient, **kwargs):
        super().__init__(**kwargs)
        self.client = client
        self.add_class("itinerary-container")
    
    def compose(self) -> ComposeResult:
        yield Static("[bold $accent-primary]📅 今日行程[/bold $accent-primary]", classes="view-header")
        yield RichLog(id="itinerary-log", classes="itinerary-log", wrap=True, markup=True)
        with Horizontal(classes="itinerary-actions"):
            yield Button("🔄 刷新", id="refresh-itinerary", variant="default")
            yield Button("➕ 添加行程", id="add-itinerary", variant="primary")
    
    async def on_mount(self):
        """挂载时加载今日行程"""
        await self.load_itinerary()
    
    async def load_itinerary(self):
        """加载今日行程"""
        log = self.query_one("#itinerary-log", RichLog)
        log.clear()
        
        try:
            # 获取今日行程
            itinerary = await self.client.schedule_get_today_itinerary()
            
            if not itinerary or len(itinerary) == 0:
                log.write("[dim]今天还没有安排行程[/dim]")
                return
            
            log.write("[bold]今天的行程：[/bold]\n")
            
            for item in itinerary:
                time_slot = item.get("time_slot", "未知时间")
                activity_type = item.get("activity_type", "未知")
                description = item.get("description", "")
                scene = item.get("scene", "")
                is_current = item.get("is_current", False)
                
                # 当前活动高亮
                if is_current:
                    log.write(f"[bold $accent-primary]▶ {time_slot}[/bold $accent-primary]")
                    log.write(f"  [bold]{description}[/bold]")
                else:
                    log.write(f"[dim]  {time_slot}[/dim]")
                    log.write(f"  {description}")
                
                if scene:
                    log.write(f"  [dim]📍 {scene}[/dim]")
                
                log.write("")  # 空行
                
        except Exception as e:
            log.write(f"[bold $status-error]✗ 加载失败:[/bold $status-error] {str(e)}")
    
    async def on_button_pressed(self, event: Button.Pressed):
        """处理按钮点击"""
        if event.button.id == "refresh-itinerary":
            event.stop()
            await self.load_itinerary()
        elif event.button.id == "add-itinerary":
            event.stop()
            log = self.query_one("#itinerary-log", RichLog)
            log.write("[dim]添加行程功能开发中...[/dim]")


class ScenePoolView(Vertical):
    """场景池视图"""
    
    def __init__(self, client: AgentClient, **kwargs):
        super().__init__(**kwargs)
        self.client = client
        self.add_class("scene-container")
    
    def compose(self) -> ComposeResult:
        yield Static("[bold $accent-primary]🌍 场景池[/bold $accent-primary]", classes="view-header")
        yield RichLog(id="scene-log", classes="scene-log", wrap=True, markup=True)
        with Horizontal(classes="scene-actions"):
            yield Button("🔄 刷新", id="refresh-scenes", variant="default")
            yield Button("📍 当前场景", id="current-scene", variant="primary")
    
    async def on_mount(self):
        """挂载时加载场景池"""
        await self.load_scenes()
    
    async def load_scenes(self):
        """加载场景池"""
        log = self.query_one("#scene-log", RichLog)
        log.clear()
        
        try:
            # 获取场景池
            scenes = await self.client.scene_list_pool()
            
            if not scenes or len(scenes) == 0:
                log.write("[dim]场景池为空[/dim]")
                return
            
            log.write("[bold]已访问的场景：[/bold]\n")
            
            for scene in scenes:
                name = scene.get("name", "未命名场景")
                location = scene.get("location", "")
                visit_count = scene.get("visit_count", 0)
                last_visit = scene.get("last_visit", "")
                is_current = scene.get("is_current", False)
                
                # 当前场景高亮
                if is_current:
                    log.write(f"[bold $accent-primary]▶ {name}[/bold $accent-primary] [dim](当前)[/dim]")
                else:
                    log.write(f"[bold]{name}[/bold]")
                
                if location:
                    log.write(f"  📍 {location}")
                
                log.write(f"  [dim]访问次数: {visit_count} | 最后访问: {last_visit}[/dim]")
                log.write("")  # 空行
                
        except Exception as e:
            log.write(f"[bold $status-error]✗ 加载失败:[/bold $status-error] {str(e)}")
    
    async def on_button_pressed(self, event: Button.Pressed):
        """处理按钮点击"""
        if event.button.id == "refresh-scenes":
            event.stop()
            await self.load_scenes()
        elif event.button.id == "current-scene":
            event.stop()
            await self.show_current_scene()
    
    async def show_current_scene(self):
        """显示当前场景详情"""
        log = self.query_one("#scene-log", RichLog)
        
        try:
            scene = await self.client.scene_get_current()
            
            if not scene:
                log.write("[dim]当前没有激活的场景[/dim]")
                return
            
            log.clear()
            log.write("[bold $accent-primary]📍 当前场景详情[/bold $accent-primary]\n")
            
            name = scene.get("name", "未命名")
            location = scene.get("location", "")
            description = scene.get("description", "")
            areas = scene.get("areas", [])
            objects = scene.get("objects", [])
            
            log.write(f"[bold]{name}[/bold]")
            if location:
                log.write(f"📍 {location}")
            if description:
                log.write(f"\n{description}\n")
            
            if areas:
                log.write("\n[bold]区域：[/bold]")
                for area in areas:
                    log.write(f"  • {area}")
            
            if objects:
                log.write("\n[bold]物体：[/bold]")
                for obj in objects:
                    log.write(f"  • {obj}")
                    
        except Exception as e:
            log.write(f"[bold $status-error]✗ 加载失败:[/bold $status-error] {str(e)}")


class MemoryView(Vertical):
    """记忆与知识视图"""
    
    def __init__(self, client: AgentClient, **kwargs):
        super().__init__(**kwargs)
        self.client = client
        self.add_class("memory-container")
    
    def compose(self) -> ComposeResult:
        yield Static("[bold $accent-primary]🧠 记忆与知识[/bold $accent-primary]", classes="view-header")
        with Horizontal(classes="search-bar"):
            yield Input(placeholder="搜索记忆和知识...", id="memory-search")
            yield Button("🔍 搜索", id="search-memory", variant="primary")
        yield RichLog(id="memory-log", classes="memory-log", wrap=True, markup=True)
    
    async def on_mount(self):
        """挂载时显示最近记忆"""
        await self.load_recent()
    
    async def load_recent(self):
        """加载最近的记忆"""
        log = self.query_one("#memory-log", RichLog)
        log.clear()
        log.write("[bold]最近的记忆：[/bold]\n")
        
        try:
            # 获取最近记忆
            memories = await self.client.memory_get_recent(limit=10)
            
            if not memories or len(memories) == 0:
                log.write("[dim]暂无记忆记录[/dim]")
                return
            
            for mem in memories:
                content = mem.get("content", "")
                timestamp = mem.get("timestamp", "")
                memory_type = mem.get("type", "记忆")
                
                log.write(f"[dim]{timestamp}[/dim] [{memory_type}]")
                log.write(f"  {content}")
                log.write("")
                
        except Exception as e:
            log.write(f"[bold $status-error]✗ 加载失败:[/bold $status-error] {str(e)}")
    
    async def on_button_pressed(self, event: Button.Pressed):
        """处理按钮点击"""
        if event.button.id == "search-memory":
            event.stop()
            await self.search_memory()
    
    async def on_input_submitted(self, event: Input.Submitted):
        """处理搜索提交"""
        if event.input.id == "memory-search":
            await self.search_memory()
    
    async def search_memory(self):
        """搜索记忆"""
        search_input = self.query_one("#memory-search", Input)
        query = search_input.value.strip()
        
        if not query:
            return
        
        log = self.query_one("#memory-log", RichLog)
        log.clear()
        log.write(f"[bold]搜索结果：[/bold] \"{query}\"\n")
        
        try:
            # 搜索记忆
            results = await self.client.memory_search(query, limit=20)
            
            if not results or len(results) == 0:
                log.write("[dim]未找到相关记忆[/dim]")
                return
            
            for item in results:
                content = item.get("content", "")
                relevance = item.get("relevance", 0.0)
                timestamp = item.get("timestamp", "")
                
                # 显示相关度
                relevance_bar = "■" * int(relevance * 10)
                log.write(f"[dim]{timestamp}[/dim] [{relevance_bar}]")
                log.write(f"  {content}")
                log.write("")
                
        except Exception as e:
            log.write(f"[bold $status-error]✗ 搜索失败:[/bold $status-error] {str(e)}")


class RelationshipView(Vertical):
    """关系网络视图"""
    
    def __init__(self, client: AgentClient, **kwargs):
        super().__init__(**kwargs)
        self.client = client
        self.add_class("relationship-container")
    
    def compose(self) -> ComposeResult:
        yield Static("[bold $accent-primary]💭 关系网络[/bold $accent-primary]", classes="view-header")
        yield RichLog(id="relationship-log", classes="relationship-log", wrap=True, markup=True)
        with Horizontal(classes="relationship-actions"):
            yield Button("🔄 刷新", id="refresh-relationships", variant="default")
            yield Button("📊 统计", id="stats-relationships", variant="primary")
    
    async def on_mount(self):
        """挂载时加载关系网络"""
        await self.load_relationships()
    
    async def load_relationships(self):
        """加载关系网络"""
        log = self.query_one("#relationship-log", RichLog)
        log.clear()
        
        try:
            # 获取关系列表
            relationships = await self.client.relationship_list()
            
            if not relationships or len(relationships) == 0:
                log.write("[dim]暂无关系记录[/dim]")
                return
            
            log.write("[bold]关系网络：[/bold]\n")
            
            # 按分数排序
            sorted_rels = sorted(relationships, key=lambda x: x.get("score", 0), reverse=True)
            
            for rel in sorted_rels:
                entity = rel.get("entity", "未知")
                score = rel.get("score", 0)
                last_interaction = rel.get("last_interaction", "")
                relation_type = rel.get("type", "未知")
                
                # 使用条形图显示分数
                score_bar = "■" * int(score / 10)
                score_empty = "□" * (10 - int(score / 10))
                
                log.write(f"[bold]{entity}[/bold] [{relation_type}]")
                log.write(f"  亲密度: [{score_bar}{score_empty}] {score}/100")
                log.write(f"  [dim]最后互动: {last_interaction}[/dim]")
                log.write("")
                
        except Exception as e:
            log.write(f"[bold $status-error]✗ 加载失败:[/bold $status-error] {str(e)}")
    
    async def on_button_pressed(self, event: Button.Pressed):
        """处理按钮点击"""
        if event.button.id == "refresh-relationships":
            event.stop()
            await self.load_relationships()
        elif event.button.id == "stats-relationships":
            event.stop()
            await self.show_stats()
    
    async def show_stats(self):
        """显示关系统计"""
        log = self.query_one("#relationship-log", RichLog)
        log.clear()
        
        try:
            stats = await self.client.relationship_get_stats()
            
            log.write("[bold $accent-primary]📊 关系统计[/bold $accent-primary]\n")
            
            total = stats.get("total", 0)
            by_type = stats.get("by_type", {})
            avg_score = stats.get("avg_score", 0)
            
            log.write(f"总关系数: [bold]{total}[/bold]")
            log.write(f"平均亲密度: [bold]{avg_score:.1f}[/bold]/100\n")
            
            if by_type:
                log.write("[bold]按类型分布：[/bold]")
                for rel_type, count in by_type.items():
                    log.write(f"  {rel_type}: {count}")
                    
        except Exception as e:
            log.write(f"[bold $status-error]✗ 加载失败:[/bold $status-error] {str(e)}")


class AuditView(Vertical):
    """审计日志视图"""
    
    def __init__(self, client: AgentClient, **kwargs):
        super().__init__(**kwargs)
        self.client = client
        self.add_class("audit-container")
        self.filter_level = "all"
    
    def compose(self) -> ComposeResult:
        yield Static("[bold $accent-primary]🔍 审计日志[/bold $accent-primary]", classes="view-header")
        with Horizontal(classes="audit-filters"):
            yield Button("全部", id="filter-all", variant="primary")
            yield Button("高风险", id="filter-high", variant="default")
            yield Button("中风险", id="filter-medium", variant="default")
            yield Button("低风险", id="filter-low", variant="default")
        yield RichLog(id="audit-log", classes="audit-log", wrap=True, markup=True)
        with Horizontal(classes="audit-actions"):
            yield Button("🔄 刷新", id="refresh-audit", variant="default")
            yield Button("⬇️ 加载更多", id="load-more-audit", variant="default")
    
    async def on_mount(self):
        """挂载时加载审计日志"""
        await self.load_audit_logs()
    
    async def load_audit_logs(self, append=False):
        """加载审计日志"""
        log = self.query_one("#audit-log", RichLog)
        
        if not append:
            log.clear()
        
        try:
            # 获取审计日志
            logs = await self.client.system_get_audit_logs(
                limit=20,
                filter_level=self.filter_level if self.filter_level != "all" else None
            )
            
            if not logs or len(logs) == 0:
                log.write("[dim]暂无审计日志[/dim]")
                return
            
            if not append:
                log.write("[bold]审计日志（按时间倒序）：[/bold]\n")
            
            for entry in logs:
                timestamp = entry.get("timestamp", "")
                operation = entry.get("operation", "")
                risk_level = entry.get("risk_level", "low")
                details = entry.get("details", "")
                user = entry.get("user", "system")
                
                # 根据风险级别设置颜色
                if risk_level == "high":
                    level_text = "[bold $status-error]⚠ 高风险[/bold $status-error]"
                elif risk_level == "medium":
                    level_text = "[bold $status-warning]⚡ 中风险[/bold $status-warning]"
                else:
                    level_text = "[dim]ℹ 低风险[/dim]"
                
                log.write(f"{level_text} [dim]{timestamp}[/dim]")
                log.write(f"  {operation} (by {user})")
                if details:
                    log.write(f"  [dim]{details}[/dim]")
                log.write("")
                
        except Exception as e:
            log.write(f"[bold $status-error]✗ 加载失败:[/bold $status-error] {str(e)}")
    
    async def on_button_pressed(self, event: Button.Pressed):
        """处理按钮点击"""
        button_id = event.button.id
        
        if button_id == "refresh-audit":
            event.stop()
            await self.load_audit_logs()
        elif button_id == "load-more-audit":
            event.stop()
            await self.load_audit_logs(append=True)
        elif button_id.startswith("filter-"):
            event.stop()
            # 更新过滤器
            filter_level = button_id.replace("filter-", "")
            self.filter_level = filter_level
            
            # 更新按钮样式
            for btn_id in ["filter-all", "filter-high", "filter-medium", "filter-low"]:
                btn = self.query_one(f"#{btn_id}", Button)
                btn.variant = "primary" if btn_id == button_id else "default"
            
            # 重新加载
            await self.load_audit_logs()


class MainContent(Container):
    """主内容区"""
    
    current_view = reactive("chat")
    
    def __init__(self, client: AgentClient, **kwargs):
        super().__init__(**kwargs)
        self.client = client
        self.add_class("main-content")
        self.views = {}
    
    def compose(self) -> ComposeResult:
        # 初始化所有视图
        self.views["chat"] = ChatView(self.client)
        self.views["itinerary"] = ItineraryView(self.client)
        self.views["scenes"] = ScenePoolView(self.client)
        self.views["memory"] = MemoryView(self.client)
        self.views["relationships"] = RelationshipView(self.client)
        self.views["audit"] = AuditView(self.client)
        yield self.views["chat"]
    
    async def switch_to(self, view_id: str):
        """切换视图"""
        # 隐藏所有视图
        for view in self.views.values():
            view.display = False
        
        # 如果视图不存在，创建占位符
        if view_id not in self.views:
            placeholder = Static(
                f"[bold $accent-primary]{view_id.upper()} 视图[/bold $accent-primary]\n\n"
                f"[dim]该功能正在开发中...[/dim]",
                classes="placeholder-view"
            )
            placeholder.styles.padding = (2, 4)
            placeholder.styles.text_align = "center"
            self.views[view_id] = placeholder
            await self.mount(placeholder)
        
        # 显示目标视图
        self.views[view_id].display = True
        self.current_view = view_id


class NeoAgentApp(App):
    """Neo Agent 主应用"""
    
    CSS = FULL_THEME
    TITLE = "Neo Agent"
    
    def __init__(self):
        super().__init__()
        self.client = AgentClient()
        self.connected = False
    
    def on_button_pressed(self, event):
        """处理按钮点击"""
        # 检查是否是 NavigationItem
        if isinstance(event.button, NavigationItem):
            self.run_worker(self.switch_view(event.button.view_id))
    
    def compose(self) -> ComposeResult:
        yield StatusBar(id="status-bar")
        with Horizontal():
            yield Sidebar(classes="sidebar")
            yield MainContent(self.client, id="main-content")
        yield Static("服务连接中... • 按 : 进入命令模式 • 按 q 退出", classes="footer")
    
    async def on_mount(self):
        """应用启动"""
        # 尝试连接服务
        try:
            connected = await self.client.connect(timeout=3.0)
            if connected:
                self.connected = True
                await self.update_status_from_service()
                
                # 更新底栏
                footer = self.query_one(".footer", Static)
                footer.update("服务运行中 • 按 : 进入命令模式 • 按 q 退出")
                
                # 更新对话日志
                chat_log = self.query_one("#chat-log", RichLog)
                chat_log.write("[bold $status-success]✓ 已连接到服务[/bold $status-success]")
            else:
                # 连接失败
                footer = self.query_one(".footer", Static)
                footer.update("[bold $status-error]✗ 无法连接到服务[/bold $status-error] • 按 q 退出")
                
                chat_log = self.query_one("#chat-log", RichLog)
                chat_log.write("[bold $status-error]✗ 无法连接到服务，请确保服务已启动[/bold $status-error]")
        except Exception as e:
            footer = self.query_one(".footer", Static)
            footer.update(f"[bold $status-error]连接错误: {str(e)}[/bold $status-error]")
    
    async def update_status_from_service(self):
        """从服务更新状态栏"""
        try:
            context = await self.client.get_context()
            character = context.get("character", {})
            scene = context.get("current_scene", {})
            emotion = context.get("emotion", {})
            
            status_bar = self.query_one("#status-bar", StatusBar)
            status_bar.character_name = character.get("name", "林依")
            
            scene_location = scene.get("location", "")
            scene_area = scene.get("area", "")
            if scene_location:
                status_bar.scene_info = f"{scene_location}-{scene_area}" if scene_area else scene_location
            
            emotion_state = emotion.get("state", "")
            if emotion_state:
                status_bar.emotion = f"情绪:{emotion_state}"
            
        except Exception:
            pass
    
    async def switch_view(self, view_id: str):
        """切换主内容视图"""
        main_content = self.query_one("#main-content", MainContent)
        await main_content.switch_to(view_id)
    
    async def on_unmount(self):
        """应用退出"""
        if self.connected:
            await self.client.disconnect()


def run_tui():
    """启动 TUI"""
    app = NeoAgentApp()
    app.run()
