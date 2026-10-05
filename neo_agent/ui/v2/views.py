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
        background: $surface-0;
        border: solid $surface-3;
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
                        log.write(f"[bold $accent-primary]林依[/] [{timestamp}]: {content}")
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
            
            log.write(f"[bold $accent-primary]林依[/] [dim](情绪: {emotion})[/]: {reply}\n")
            
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
    
    .itinerary_title {
        width: 100%;
        text-style: bold;
        color: $accent-primary;
        margin-bottom: 1;
    }
    
    #itinerary_table {
        width: 100%;
        height: 1fr;
        margin-bottom: 1;
    }
    
    .action_buttons {
        width: 100%;
        height: auto;
        layout: horizontal;
    }
    
    .action_buttons Button {
        margin-right: 1;
    }
    """
    
    def compose(self) -> ComposeResult:
        yield Label("📅 今日行程", classes="itinerary_title")
        yield DataTable(id="itinerary_table", zebra_stripes=True, cursor_type="row")
        with Horizontal(classes="action_buttons"):
            yield Button("刷新", variant="primary", id="refresh_btn")
            yield Button("生成新计划", variant="default", id="generate_btn")
    
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
                        "completed": "已完成"
                    }.get(status, status)
                    
                    table.add_row(time, activity, location, owner_text, status_text)
            else:
                # 显示空状态
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
        # TODO: 显示行程详情模态框
        self.app.notify("行程详情功能开发中...", timeout=2)


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
        color: $accent-primary;
        margin-bottom: 1;
    }
    
    #current_scene {
        width: 100%;
        background: $surface-2;
        border: solid $accent-primary;
        padding: 1;
        margin-bottom: 1;
    }
    
    #scene_table {
        width: 100%;
        height: 1fr;
    }
    """
    
    def compose(self) -> ComposeResult:
        yield Label("🌍 场景池", classes="scene_title")
        
        with Container(id="current_scene"):
            yield Label("[bold]当前场景:[/]")
            yield Label("", id="current_scene_text")
        
        yield Label("[bold]已访问场景:[/]", classes="scene_title")
        yield DataTable(id="scene_table", zebra_stripes=True, cursor_type="row")
    
    async def on_mount(self) -> None:
        table = self.query_one("#scene_table", DataTable)
        table.add_columns("地点", "区域", "访问次数", "最后访问")
    
    async def load_data(self, client) -> None:
        """加载场景数据"""
        try:
            # 加载当前场景
            current = await client.call("scene.get_current")
            if current:
                current_text = self.query_one("#current_scene_text", Label)
                location = current.get("location", "未知")
                area = current.get("area", "")
                description = current.get("description", "")
                
                text = f"[bold $accent-primary]{location}[/]"
                if area:
                    text += f" - {area}"
                if description:
                    text += f"\n[dim]{description}[/]"
                
                current_text.update(text)
            
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
                table.add_row("暂无场景", "-", "-", "-")
                
        except Exception as e:
            table = self.query_one("#scene_table", DataTable)
            table.clear()
            table.add_row("错误", f"加载失败: {e}", "-", "-")
    
    async def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """显示场景详情"""
        self.app.notify("场景详情功能开发中...", timeout=2)


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
        color: $accent-primary;
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
    
    #memory_log {
        width: 100%;
        height: 1fr;
        background: $surface-0;
        border: solid $surface-3;
        padding: 1;
    }
    
    .stats_container {
        width: 100%;
        layout: horizontal;
        margin-bottom: 1;
    }
    
    .stat_box {
        width: 1fr;
        height: 3;
        background: $surface-2;
        border: solid $surface-3;
        padding: 0 1;
        margin-right: 1;
        text-align: center;
    }
    """
    
    def compose(self) -> ComposeResult:
        yield Label("🧠 记忆与知识", classes="memory_title")
        
        # 统计信息
        with Horizontal(classes="stats_container"):
            with Container(classes="stat_box"):
                yield Label("[bold]短期记忆[/]")
                yield Label("24 条", id="short_memory_count")
            
            with Container(classes="stat_box"):
                yield Label("[bold]长期记忆[/]")
                yield Label("156 条", id="long_memory_count")
            
            with Container(classes="stat_box"):
                yield Label("[bold]知识库[/]")
                yield Label("8 个主题", id="knowledge_count")
        
        # 搜索框
        with Horizontal(id="search_container"):
            yield Input(placeholder="搜索记忆或知识...", id="search_input")
            yield Button("搜索", variant="primary", id="search_btn")
        
        # 结果显示
        yield RichLog(id="memory_log", highlight=True, markup=True)
    
    async def on_mount(self) -> None:
        log = self.query_one("#memory_log", RichLog)
        log.write("[dim]输入关键词搜索记忆和知识...[/]")
    
    async def load_data(self, client) -> None:
        """加载记忆统计"""
        try:
            # 加载统计信息
            stats = await client.call("memory.get_stats")
            if stats:
                short_count = self.query_one("#short_memory_count", Label)
                long_count = self.query_one("#long_memory_count", Label)
                knowledge_count = self.query_one("#knowledge_count", Label)
                
                short_count.update(f"{stats.get('short_term', 0)} 条")
                long_count.update(f"{stats.get('long_term', 0)} 条")
                knowledge_count.update(f"{stats.get('knowledge', 0)} 个主题")
        except Exception as e:
            pass  # 使用默认值
    
    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "search_btn":
            await self.perform_search()
    
    async def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "search_input":
            await self.perform_search()
    
    async def perform_search(self) -> None:
        """执行搜索"""
        input_widget = self.query_one("#search_input", Input)
        query = input_widget.value.strip()
        
        if not query:
            self.app.notify("请输入搜索关键词", severity="warning")
            return
        
        log = self.query_one("#memory_log", RichLog)
        log.clear()
        log.write(f"[bold]搜索: {query}[/]\n")
        log.write("[dim]正在搜索...[/]\n")
        
        try:
            results = await self.app.client.call("memory.search", query=query, limit=10)
            log.clear()
            log.write(f"[bold]搜索: {query}[/]\n")
            
            if results:
                for i, result in enumerate(results, 1):
                    content = result.get("content", "")
                    relevance = result.get("relevance", 0)
                    timestamp = result.get("timestamp", "")
                    memory_type = result.get("type", "")
                    
                    type_icon = "📝" if memory_type == "short" else "📚"
                    
                    log.write(f"\n[bold]{i}. {type_icon}[/] [dim]{timestamp}[/] (相关度: {relevance:.2f})")
                    log.write(f"  {content}")
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
        color: $accent-primary;
        margin-bottom: 1;
    }
    
    #relationship_table {
        width: 100%;
        height: 1fr;
    }
    
    .summary {
        width: 100%;
        background: $surface-2;
        border: solid $surface-3;
        padding: 1;
        margin-bottom: 1;
    }
    """
    
    def compose(self) -> ComposeResult:
        yield Label("💭 关系网络", classes="relationship_title")
        
        with Container(classes="summary"):
            yield Label("[bold]关系总览:[/]")
            yield Label("", id="relationship_summary")
        
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
                summary.update(f"共 {total} 个关系实体，平均分数: {avg_score:.1f}")
                
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
            table = self.query_one("#relationship_table", DataTable)
            table.clear()
            table.add_row("错误", f"加载失败: {e}", "-", "-")


class AuditView(VerticalScroll):
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
        layout: horizontal;
        margin-bottom: 1;
    }
    
    .filter_container Button {
        margin-right: 1;
    }
    """
    
    def compose(self) -> ComposeResult:
        yield Label("🔍 审计日志", classes="audit_title")
        
        with Horizontal(classes="filter_container"):
            yield Button("全部", variant="primary", id="filter_all")
            yield Button("高风险", variant="default", id="filter_high_risk")
            yield Button("操作", variant="default", id="filter_actions")
            yield Button("决策", variant="default", id="filter_decisions")
        
        yield RichLog(id="audit_log", highlight=True, markup=True)
    
    async def load_data(self, client, filter_type: str = "all") -> None:
        """加载审计日志"""
        try:
            logs = await client.call("audit.get_logs", filter=filter_type, limit=100)
            log_widget = self.query_one("#audit_log", RichLog)
            log_widget.clear()
            
            if logs:
                log_widget.write(f"[bold]审计日志 (过滤: {filter_type})[/]\n")
                
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
        
        # 更新按钮样式
        for btn_id in filter_map.keys():
            btn = self.query_one(f"#{btn_id}", Button)
            if btn.id == event.button.id:
                btn.variant = "primary"
            else:
                btn.variant = "default"
        
        filter_type = filter_map.get(event.button.id, "all")
        await self.load_data(self.app.client, filter_type)
