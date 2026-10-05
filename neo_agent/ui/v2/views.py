"""TUI 视图组件"""
from textual.app import ComposeResult
from textual.containers import Container, Vertical, Horizontal
from textual.widgets import Static, Input, Button, DataTable, RichLog
from textual.reactive import reactive


class ChatView(Container):
    """对话视图"""
    
    CSS = """
    ChatView {
        width: 100%;
        height: 100%;
    }
    
    #chat_log {
        width: 100%;
        height: 1fr;
        background: $surface-0;
        border: solid $surface-3;
        padding: 1;
    }
    
    #chat_input_container {
        width: 100%;
        height: auto;
        margin-top: 1;
    }
    
    #chat_input {
        width: 1fr;
    }
    
    #send_btn {
        width: auto;
        margin-left: 1;
    }
    """
    
    def compose(self) -> ComposeResult:
        yield RichLog(id="chat_log", highlight=True, markup=True)
        with Horizontal(id="chat_input_container"):
            yield Input(
                placeholder="输入消息... (Ctrl+Enter 发送)",
                id="chat_input"
            )
            yield Button("发送", variant="primary", id="send_btn")
    
    async def load_data(self, client) -> None:
        """加载对话历史"""
        try:
            history = await client.call("session.get_history", limit=50)
            log = self.query_one("#chat_log", RichLog)
            log.clear()
            
            if history:
                for msg in history:
                    role = msg.get("role", "user")
                    content = msg.get("content", "")
                    timestamp = msg.get("timestamp", "")
                    
                    if role == "user":
                        log.write(f"[bold cyan]用户[/] [{timestamp}]: {content}")
                    else:
                        log.write(f"[bold $accent-primary]林依[/] [{timestamp}]: {content}")
            else:
                log.write("[dim]暂无对话历史[/]")
        except Exception as e:
            log = self.query_one("#chat_log", RichLog)
            log.write(f"[red]加载失败: {e}[/]")
    
    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "send_btn":
            await self.send_message()
    
    async def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "chat_input":
            await self.send_message()
    
    async def send_message(self) -> None:
        """发送消息"""
        input_widget = self.query_one("#chat_input", Input)
        message = input_widget.value.strip()
        
        if not message:
            return
        
        log = self.query_one("#chat_log", RichLog)
        log.write(f"[bold cyan]用户[/]: {message}")
        input_widget.value = ""
        
        # 显示思考中
        log.write("[dim italic]林依正在思考...[/]")
        
        # TODO: 调用 RPC 发送消息
        # response = await self.app.client.call("session.send_message", text=message)
        # log.write(f"[bold $accent-primary]林依[/]: {response.get('reply', '')}")


class ItineraryView(Container):
    """今日行程视图"""
    
    CSS = """
    ItineraryView {
        width: 100%;
        height: 100%;
        padding: 1;
    }
    
    .itinerary_title {
        width: 100%;
        text-style: bold;
        color: $accent-primary;
        margin-bottom: 1;
    }
    
    #itinerary_table {
        width: 100%;
        height: 1fr;
    }
    
    .refresh_btn {
        width: 100%;
        align: center middle;
        margin-top: 1;
    }
    """
    
    def compose(self) -> ComposeResult:
        yield Static("今日行程", classes="itinerary_title")
        yield DataTable(id="itinerary_table", zebra_stripes=True)
        with Horizontal(classes="refresh_btn"):
            yield Button("刷新", variant="primary", id="refresh_btn")
            yield Button("生成新计划", variant="default", id="generate_btn")
    
    async def on_mount(self) -> None:
        table = self.query_one("#itinerary_table", DataTable)
        table.add_columns("时间", "活动", "地点", "类型")
    
    async def load_data(self, client) -> None:
        """加载今日行程"""
        try:
            itinerary = await client.call("schedule.get_today_itinerary")
            table = self.query_one("#itinerary_table", DataTable)
            table.clear()
            
            if itinerary:
                for item in itinerary:
                    time = item.get("time", "")
                    activity = item.get("activity", "")
                    location = item.get("location", "")
                    owner = item.get("owner", "agent")
                    
                    owner_text = {
                        "agent": "个人",
                        "user": "用户",
                        "shared": "共同"
                    }.get(owner, owner)
                    
                    table.add_row(time, activity, location, owner_text)
            else:
                table.add_row("--", "暂无行程", "--", "--")
        except Exception as e:
            self.app.notify(f"加载行程失败: {e}", severity="error")
    
    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "refresh_btn":
            await self.load_data(self.app.client)
        elif event.button.id == "generate_btn":
            self.app.notify("正在生成今日计划...", timeout=3)
            try:
                await self.app.client.call("schedule.generate_daily_itinerary")
                await self.load_data(self.app.client)
                self.app.notify("计划生成完成", timeout=3)
            except Exception as e:
                self.app.notify(f"生成失败: {e}", severity="error")


class ScenePoolView(Container):
    """场景池视图"""
    
    CSS = """
    ScenePoolView {
        width: 100%;
        height: 100%;
        padding: 1;
    }
    
    .scene_title {
        width: 100%;
        text-style: bold;
        color: $accent-primary;
        margin-bottom: 1;
    }
    
    #scene_table {
        width: 100%;
        height: 1fr;
    }
    """
    
    def compose(self) -> ComposeResult:
        yield Static("场景池", classes="scene_title")
        yield DataTable(id="scene_table", zebra_stripes=True, cursor_type="row")
    
    async def on_mount(self) -> None:
        table = self.query_one("#scene_table", DataTable)
        table.add_columns("地点", "访问次数", "最后访问")
    
    async def load_data(self, client) -> None:
        """加载场景池"""
        try:
            scenes = await client.call("scene.list_pool")
            table = self.query_one("#scene_table", DataTable)
            table.clear()
            
            if scenes:
                for scene in scenes:
                    location = scene.get("location", "")
                    visit_count = scene.get("visit_count", 0)
                    last_visit = scene.get("last_visit", "")
                    
                    table.add_row(location, str(visit_count), last_visit)
            else:
                table.add_row("暂无场景", "0", "--")
        except Exception as e:
            self.app.notify(f"加载场景失败: {e}", severity="error")
    
    async def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """点击行显示详情"""
        # TODO: 获取场景详情并显示模态窗口
        self.app.notify("场景详情开发中...", timeout=2)


class MemoryView(Container):
    """记忆与知识视图"""
    
    CSS = """
    MemoryView {
        width: 100%;
        height: 100%;
        padding: 1;
    }
    
    .memory_title {
        width: 100%;
        text-style: bold;
        color: $accent-primary;
        margin-bottom: 1;
    }
    
    #search_container {
        width: 100%;
        height: auto;
        margin-bottom: 1;
    }
    
    #search_input {
        width: 1fr;
    }
    
    #search_btn {
        width: auto;
        margin-left: 1;
    }
    
    #memory_results {
        width: 100%;
        height: 1fr;
        background: $surface-0;
        border: solid $surface-3;
        padding: 1;
    }
    """
    
    def compose(self) -> ComposeResult:
        yield Static("记忆与知识", classes="memory_title")
        with Horizontal(id="search_container"):
            yield Input(
                placeholder="搜索记忆...",
                id="search_input"
            )
            yield Button("搜索", variant="primary", id="search_btn")
        yield RichLog(id="memory_results", highlight=True, markup=True)
    
    async def load_data(self, client) -> None:
        """加载初始数据"""
        log = self.query_one("#memory_results", RichLog)
        log.clear()
        log.write("[dim]输入关键词搜索记忆...[/]")
    
    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "search_btn":
            await self.search_memory()
    
    async def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "search_input":
            await self.search_memory()
    
    async def search_memory(self) -> None:
        """搜索记忆"""
        input_widget = self.query_one("#search_input", Input)
        query = input_widget.value.strip()
        
        if not query:
            return
        
        log = self.query_one("#memory_results", RichLog)
        log.clear()
        log.write(f"[bold]搜索: {query}[/]\n")
        log.write("[dim]搜索中...[/]")
        
        try:
            results = await self.app.client.call("memory.search", query=query, limit=10)
            log.clear()
            log.write(f"[bold]搜索: {query}[/]\n")
            
            if results:
                for i, result in enumerate(results, 1):
                    content = result.get("content", "")
                    relevance = result.get("relevance", 0)
                    timestamp = result.get("timestamp", "")
                    
                    log.write(f"\n[bold]{i}.[/] [dim]{timestamp}[/] (相关度: {relevance:.2f})")
                    log.write(f"  {content}")
            else:
                log.write("\n[dim]未找到相关记忆[/]")
        except Exception as e:
            log.clear()
            log.write(f"[red]搜索失败: {e}[/]")


class RelationshipView(Container):
    """关系网络视图"""
    
    CSS = """
    RelationshipView {
        width: 100%;
        height: 100%;
        padding: 1;
    }
    
    .relationship_title {
        width: 100%;
        text-style: bold;
        color: $accent-primary;
        margin-bottom: 1;
    }
    
    #relationship_table {
        width: 100%;
        height: 1fr;
    }
    """
    
    def compose(self) -> ComposeResult:
        yield Static("关系网络", classes="relationship_title")
        yield DataTable(id="relationship_table", zebra_stripes=True)
    
    async def on_mount(self) -> None:
        table = self.query_one("#relationship_table", DataTable)
        table.add_columns("实体", "关系分数", "最近更新")
    
    async def load_data(self, client) -> None:
        """加载关系数据"""
        try:
            # TODO: 获取所有关系
            relationships = [
                {"entity": "用户", "score": 85, "updated": "2026-10-05"},
                {"entity": "朋友A", "score": 60, "updated": "2026-10-04"},
            ]
            
            table = self.query_one("#relationship_table", DataTable)
            table.clear()
            
            for rel in relationships:
                entity = rel.get("entity", "")
                score = rel.get("score", 0)
                updated = rel.get("updated", "")
                
                table.add_row(entity, str(score), updated)
        except Exception as e:
            self.app.notify(f"加载关系失败: {e}", severity="error")


class AuditView(Container):
    """审计日志视图"""
    
    CSS = """
    AuditView {
        width: 100%;
        height: 100%;
        padding: 1;
    }
    
    .audit_title {
        width: 100%;
        text-style: bold;
        color: $accent-primary;
        margin-bottom: 1;
    }
    
    #audit_log {
        width: 100%;
        height: 1fr;
        background: $surface-0;
        border: solid $surface-3;
        padding: 1;
    }
    
    .filter_container {
        width: 100%;
        height: auto;
        margin-bottom: 1;
    }
    """
    
    def compose(self) -> ComposeResult:
        yield Static("审计日志", classes="audit_title")
        with Horizontal(classes="filter_container"):
            yield Button("全部", variant="primary", id="filter_all")
            yield Button("高风险", variant="default", id="filter_high_risk")
            yield Button("操作", variant="default", id="filter_actions")
        yield RichLog(id="audit_log", highlight=True, markup=True)
    
    async def load_data(self, client, filter_type: str = "all") -> None:
        """加载审计日志"""
        try:
            logs = await client.call("audit.get_logs", filter=filter_type, limit=100)
            log_widget = self.query_one("#audit_log", RichLog)
            log_widget.clear()
            
            if logs:
                for entry in logs:
                    timestamp = entry.get("timestamp", "")
                    action = entry.get("action", "")
                    risk_level = entry.get("risk_level", "low")
                    result = entry.get("result", "")
                    
                    risk_color = {
                        "high": "red",
                        "medium": "yellow",
                        "low": "green"
                    }.get(risk_level, "white")
                    
                    log_widget.write(
                        f"[dim]{timestamp}[/] "
                        f"[{risk_color}]{risk_level.upper()}[/] "
                        f"[bold]{action}[/] - {result}"
                    )
            else:
                log_widget.write("[dim]暂无审计日志[/]")
        except Exception as e:
            log_widget = self.query_one("#audit_log", RichLog)
            log_widget.write(f"[red]加载失败: {e}[/]")
    
    async def on_button_pressed(self, event: Button.Pressed) -> None:
        filter_map = {
            "filter_all": "all",
            "filter_high_risk": "high_risk",
            "filter_actions": "actions"
        }
        
        filter_type = filter_map.get(event.button.id, "all")
        await self.load_data(self.app.client, filter_type)
