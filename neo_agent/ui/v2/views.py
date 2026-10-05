"""TUI 视图组件"""
from textual.app import ComposeResult
from textual.containers import Container, Vertical, Horizontal, VerticalScroll
from textual.widgets import Static, Input, Button, DataTable, RichLog, Label
from textual.reactive import reactive


class ChatView(VerticalScroll):
    """对话视图"""
    
    CSS = """
    ChatView {
        width: 100%;
        height: 100%;
        padding: 1;
    }
    
    #chat_log {
        width: 100%;
        height: 1fr;
        background: #0A0805;
        border: solid #1C1812;
        padding: 1;
        margin-bottom: 1;
    }
    
    #chat_input_container {
        width: 100%;
        height: auto;
        layout: horizontal;
    }
    
    #chat_input {
        width: 1fr;
        margin-right: 1;
    }
    
    #send_btn {
        width: auto;
    }
    """
    
    def compose(self) -> ComposeResult:
        yield RichLog(id="chat_log", highlight=True, markup=True)
        with Horizontal(id="chat_input_container"):
            yield Input(
                placeholder="输入消息... (Enter 发送)",
                id="chat_input"
            )
            yield Button("发送", variant="primary", id="send_btn")
    
    async def on_mount(self) -> None:
        """挂载时初始化"""
        log = self.query_one("#chat_log", RichLog)
        log.write("[dim]欢迎！输入消息开始对话。[/]")
    
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
                        log.write(f"[bold #E9A568]林依[/] [{timestamp}]: {content}")
            else:
                log.write("[dim]暂无对话历史，开始新的对话吧！[/]")
        except Exception as e:
            log = self.query_one("#chat_log", RichLog)
            log.write(f"[yellow]提示: 使用模拟数据模式[/]")
    
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
        log.write(f"\n[bold cyan]用户[/]: {message}")
        input_widget.value = ""
        
        # 显示思考中
        log.write("[dim italic]林依正在思考...[/]")
        
        try:
            # 调用服务发送消息
            response = await self.app.client.call("session.send_message", text=message)
            
            # 移除"思考中"提示并显示回复
            reply = response.get('reply', '抱歉，我暂时无法回复。')
            emotion = response.get('emotion', '平静')
            
            log.write(f"[bold #E9A568]林依[/] [dim](情绪: {emotion})[/]: {reply}\n")
            
            # 更新顶栏情绪
            top_bar = self.app.query_one("#top_bar")
            top_bar.emotion = emotion
            
        except Exception as e:
            log.write(f"[red]发送失败: {e}[/]\n")


class ItineraryView(VerticalScroll):
    """今日行程视图"""
    
    CSS = """
    ItineraryView {
        width: 100%;
        height: 100%;
        padding: 1;
    }
    
    .itinerary_header {
        width: 100%;
        height: auto;
        layout: horizontal;
        margin-bottom: 1;
    }
    
    .itinerary_title {
        width: 1fr;
        text-style: bold;
        color: #E9A568;
    }
    
    .action_buttons {
        width: auto;
        height: auto;
        layout: horizontal;
    }
    
    .action_buttons Button {
        margin-left: 1;
    }
    
    #itinerary_table {
        width: 100%;
        height: 1fr;
    }
    
    .stats_container {
        width: 100%;
        height: auto;
        background: #12100D;
        border: solid #1C1812;
        padding: 1;
        margin-bottom: 1;
    }
    """
    
    def compose(self) -> ComposeResult:
        with Horizontal(classes="itinerary_header"):
            yield Label("📅 今日行程", classes="itinerary_title")
            with Horizontal(classes="action_buttons"):
                yield Button("刷新", variant="default", id="refresh_btn")
                yield Button("生成新计划", variant="primary", id="generate_btn")
        
        with Container(classes="stats_container"):
            yield Label("", id="itinerary_stats")
        
        yield DataTable(id="itinerary_table", zebra_stripes=True, cursor_type="row")
    
    async def on_mount(self) -> None:
        table = self.query_one("#itinerary_table", DataTable)
        table.add_columns("时间", "活动", "地点", "类型", "状态")
    
    async def load_data(self, client) -> None:
        """加载今日行程"""
        try:
            itinerary = await client.call("schedule.get_today_itinerary")
            table = self.query_one("#itinerary_table", DataTable)
            table.clear()
            
            if itinerary:
                # 统计信息
                total = len(itinerary)
                completed = sum(1 for item in itinerary if item.get("status") == "completed")
                active = sum(1 for item in itinerary if item.get("status") == "active")
                
                stats = self.query_one("#itinerary_stats", Label)
                stats.update(
                    f"[bold]今日计划:[/] 共 {total} 项 | "
                    f"进行中 {active} | 已完成 {completed}"
                )
                
                for item in itinerary:
                    time = item.get("time", "")
                    activity = item.get("activity", "")
                    location = item.get("location", "")
                    owner = item.get("owner", "agent")
                    status = item.get("status", "pending")
                    
                    owner_text = {
                        "agent": "个人",
                        "user": "用户",
                        "shared": "共同"
                    }.get(owner, owner)
                    
                    status_text = {
                        "pending": "待开始",
                        "active": "进行中",
                        "completed": "已完成",
                        "cancelled": "已取消"
                    }.get(status, status)
                    
                    table.add_row(time, activity, location, owner_text, status_text)
            else:
                # 显示空状态
                stats = self.query_one("#itinerary_stats", Label)
                stats.update("[dim]今日暂无行程[/]")
                table.add_row("--:--", "暂无行程", "-", "-", "-")
                
        except Exception as e:
            table = self.query_one("#itinerary_table", DataTable)
            table.clear()
            table.add_row("错误", f"加载失败: {e}", "-", "-", "-")
    
    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "refresh_btn":
            await self.load_data(self.app.client)
            self.app.notify("行程已刷新", timeout=2)
        
        elif event.button.id == "generate_btn":
            self.app.notify("正在生成新的行程计划...", timeout=3)
            try:
                await self.app.client.call("schedule.generate_daily_itinerary")
                await self.load_data(self.app.client)
                self.app.notify("行程生成成功", timeout=3)
            except Exception as e:
                self.app.notify(f"生成失败: {e}", severity="error")
    
    async def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """行选中事件 - 显示详情"""
        self.app.notify("行程详情: 点击查看完整信息", timeout=2)


class ScenePoolView(VerticalScroll):
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
        color: #E9A568;
        margin-bottom: 1;
    }
    
    #current_scene_container {
        width: 100%;
        background: #12100D;
        border: solid #E9A568;
        padding: 1;
        margin-bottom: 2;
    }
    
    #current_scene_text {
        width: 100%;
        margin-top: 1;
    }
    
    #scene_table {
        width: 100%;
        height: 1fr;
    }
    """
    
    def compose(self) -> ComposeResult:
        yield Label("🌍 场景池", classes="scene_title")
        
        with Container(id="current_scene_container"):
            yield Label("[bold #E9A568]当前场景[/]")
            yield Label("加载中...", id="current_scene_text")
        
        yield Label("[bold]已访问场景[/]", classes="scene_title")
        yield DataTable(id="scene_table", zebra_stripes=True, cursor_type="row")
    
    async def on_mount(self) -> None:
        table = self.query_one("#scene_table", DataTable)
        table.add_columns("地点", "区域", "访问次数", "最后访问")
    
    async def load_data(self, client) -> None:
        """加载场景数据"""
        try:
            # 加载当前场景
            current = await client.call("scene.get_current")
            current_text = self.query_one("#current_scene_text", Label)
            
            if current:
                location = current.get("location", "未知")
                area = current.get("area", "")
                description = current.get("description", "")
                
                text = f"[bold]{location}[/]"
                if area:
                    text += f" - {area}"
                if description:
                    text += f"\n[dim]{description}[/]"
                
                current_text.update(text)
            else:
                current_text.update("[dim]暂无当前场景[/]")
            
            # 加载场景池
            scenes = await client.call("scene.list_pool")
            table = self.query_one("#scene_table", DataTable)
            table.clear()
            
            if scenes:
                for scene in scenes:
                    location = scene.get("name", "")
                    area = scene.get("area", "-")
                    visits = scene.get("visits", 0)
                    last_visit = scene.get("last_visit", "-")
                    
                    table.add_row(location, area, str(visits), last_visit)
            else:
                table.add_row("暂无数据", "-", "-", "-")
                
        except Exception as e:
            current_text = self.query_one("#current_scene_text", Label)
            current_text.update(f"[red]加载失败: {e}[/]")
    
    async def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """场景选中事件"""
        self.app.notify("场景详情: 查看地点描述和物体", timeout=2)


class MemoryView(VerticalScroll):
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
        color: #E9A568;
        margin-bottom: 1;
    }
    
    #search_container {
        width: 100%;
        height: auto;
        layout: horizontal;
        margin-bottom: 1;
    }
    
    #search_input {
        width: 1fr;
        margin-right: 1;
    }
    
    #search_btn {
        width: auto;
    }
    
    #memory_log {
        width: 100%;
        height: 1fr;
        background: #0A0805;
        border: solid #1C1812;
        padding: 1;
    }
    """
    
    def compose(self) -> ComposeResult:
        yield Label("🧠 记忆与知识", classes="memory_title")
        
        with Horizontal(id="search_container"):
            yield Input(
                placeholder="搜索记忆或知识...",
                id="search_input"
            )
            yield Button("搜索", variant="primary", id="search_btn")
        
        yield RichLog(id="memory_log", highlight=True, markup=True)
    
    async def on_mount(self) -> None:
        log = self.query_one("#memory_log", RichLog)
        log.write("[dim]输入关键词搜索记忆和知识库...[/]")
    
    async def load_data(self, client) -> None:
        """加载记忆统计"""
        try:
            stats = await client.call("memory.get_stats")
            log = self.query_one("#memory_log", RichLog)
            log.clear()
            
            if stats:
                total_memories = stats.get("total_memories", 0)
                total_knowledge = stats.get("total_knowledge", 0)
                
                log.write(f"[bold]记忆库统计[/]")
                log.write(f"  短期记忆: {total_memories} 条")
                log.write(f"  知识条目: {total_knowledge} 条")
                log.write("\n[dim]输入关键词开始搜索...[/]")
            else:
                log.write("[dim]暂无记忆数据[/]")
                
        except Exception:
            log = self.query_one("#memory_log", RichLog)
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
            self.app.notify("请输入搜索关键词", severity="warning")
            return
        
        log = self.query_one("#memory_log", RichLog)
        log.clear()
        log.write(f"[bold]搜索: {query}[/]\n")
        
        try:
            results = await self.app.client.call("memory.search", query=query)
            
            if results:
                for idx, result in enumerate(results, 1):
                    content = result.get("content", "")
                    relevance = result.get("relevance", 0)
                    timestamp = result.get("timestamp", "")
                    
                    log.write(f"\n[bold cyan]{idx}.[/] [dim]相关度: {relevance:.2f}[/]")
                    log.write(f"  {content}")
                    log.write(f"  [dim]{timestamp}[/]")
            else:
                log.write("\n[dim]未找到相关记忆[/]")
        except Exception as e:
            log.clear()
            log.write(f"[red]搜索失败: {e}[/]")


class RelationshipView(VerticalScroll):
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
        color: #E9A568;
        margin-bottom: 1;
    }
    
    #relationship_table {
        width: 100%;
        height: 1fr;
    }
    
    .summary {
        width: 100%;
        background: #12100D;
        border: solid #1C1812;
        padding: 1;
        margin-bottom: 1;
    }
    """
    
    def compose(self) -> ComposeResult:
        yield Label("💭 关系网络", classes="relationship_title")
        
        with Container(classes="summary"):
            yield Label("[bold]关系总览[/]")
            yield Label("加载中...", id="relationship_summary")
        
        yield DataTable(id="relationship_table", zebra_stripes=True, cursor_type="row")
    
    async def on_mount(self) -> None:
        table = self.query_one("#relationship_table", DataTable)
        table.add_columns("实体", "关系分数", "亲密度", "最近更新")
    
    async def load_data(self, client) -> None:
        """加载关系数据"""
        try:
            relationships = await client.call("relationship.list_all")
            
            table = self.query_one("#relationship_table", DataTable)
            table.clear()
            
            if relationships:
                # 计算统计
                total = len(relationships)
                avg_score = sum(r.get("score", 0) for r in relationships) / total if total > 0 else 0
                
                summary = self.query_one("#relationship_summary", Label)
                summary.update(
                    f"共 {total} 个关系实体 | 平均分数: {avg_score:.1f}"
                )
                
                for rel in relationships:
                    entity = rel.get("entity", "")
                    score = rel.get("score", 0)
                    updated = rel.get("updated", "")
                    
                    # 计算亲密度等级
                    if score >= 80:
                        intimacy = "亲密"
                    elif score >= 60:
                        intimacy = "友好"
                    elif score >= 40:
                        intimacy = "普通"
                    elif score >= 20:
                        intimacy = "陌生"
                    else:
                        intimacy = "疏远"
                    
                    table.add_row(entity, str(score), intimacy, updated)
            else:
                summary = self.query_one("#relationship_summary", Label)
                summary.update("暂无关系数据")
                table.add_row("暂无数据", "-", "-", "-")
                
        except Exception as e:
            summary = self.query_one("#relationship_summary", Label)
            summary.update(f"加载失败: {e}")


class AuditView(VerticalScroll):
    """审计日志视图"""
    
    CSS = """
    AuditView {
        width: 100%;
        height: 100%;
        padding: 1;
    }
    
    .audit_header {
        width: 100%;
        height: auto;
        layout: horizontal;
        margin-bottom: 1;
    }
    
    .audit_title {
        width: 1fr;
        text-style: bold;
        color: #E9A568;
    }
    
    .filter_buttons {
        width: auto;
        height: auto;
        layout: horizontal;
    }
    
    .filter_buttons Button {
        margin-left: 1;
    }
    
    #audit_log {
        width: 100%;
        height: 1fr;
        background: #0A0805;
        border: solid #1C1812;
        padding: 1;
    }
    """
    
    current_filter = reactive("all")
    
    def compose(self) -> ComposeResult:
        with Horizontal(classes="audit_header"):
            yield Label("🔍 审计日志", classes="audit_title")
            with Horizontal(classes="filter_buttons"):
                yield Button("全部", variant="primary", id="filter_all")
                yield Button("高风险", variant="default", id="filter_high_risk")
                yield Button("操作", variant="default", id="filter_actions")
                yield Button("决策", variant="default", id="filter_decisions")
        
        yield RichLog(id="audit_log", highlight=True, markup=True)
    
    async def load_data(self, client, filter_type: str = "all") -> None:
        """加载审计日志"""
        self.current_filter = filter_type
        
        try:
            logs = await client.call("audit.get_logs", filter=filter_type, limit=100)
            log_widget = self.query_one("#audit_log", RichLog)
            log_widget.clear()
            
            if logs:
                log_widget.write(f"[bold]审计日志[/] [dim](过滤: {filter_type})[/]\n")
                
                for entry in logs:
                    timestamp = entry.get("timestamp", "")
                    action = entry.get("action", "")
                    risk_level = entry.get("risk_level", "low")
                    result = entry.get("result", "")
                    category = entry.get("category", "")
                    
                    risk_color = {
                        "high": "red",
                        "medium": "yellow",
                        "low": "green"
                    }.get(risk_level, "white")
                    
                    log_widget.write(
                        f"\n[dim]{timestamp}[/] "
                        f"[{risk_color}]●[/] "
                        f"[bold]{action}[/] "
                        f"[dim]({category})[/]"
                    )
                    if result:
                        log_widget.write(f"  {result}")
            else:
                log_widget.write("[dim]暂无审计日志[/]")
                
        except Exception as e:
            log_widget = self.query_one("#audit_log", RichLog)
            log_widget.clear()
            log_widget.write(f"[red]加载失败: {e}[/]")
    
    async def on_button_pressed(self, event: Button.Pressed) -> None:
        filter_map = {
            "filter_all": "all",
            "filter_high_risk": "high_risk",
            "filter_actions": "actions",
            "filter_decisions": "decisions"
        }
        
        if event.button.id not in filter_map:
            return
        
        # 更新按钮样式
        for btn_id in filter_map.keys():
            btn = self.query_one(f"#{btn_id}", Button)
            if btn.id == event.button.id:
                btn.variant = "primary"
            else:
                btn.variant = "default"
        
        filter_type = filter_map[event.button.id]
        await self.load_data(self.app.client, filter_type)
