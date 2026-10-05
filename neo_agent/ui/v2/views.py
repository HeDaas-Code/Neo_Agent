"""TUI 视图组件 - 完整实现版"""
from textual.app import ComposeResult
from textual.containers import Container, Vertical, Horizontal, VerticalScroll
from textual.widgets import Static, Input, Button, DataTable, RichLog, Label
from textual.reactive import reactive
from datetime import datetime


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
        log.write("[#E9A568]欢迎与林依对话！[/]")
        log.write("[dim]提示：输入消息后按 Enter 或点击发送按钮[/]\n")
    
    async def load_data(self, client) -> None:
        """加载对话历史"""
        try:
            history = await client.call("session.get_history", limit=50)
            log = self.query_one("#chat_log", RichLog)
            log.clear()
            
            if history and len(history) > 0:
                log.write("[#E9A568]─── 对话历史 ───[/]\n")
                for msg in history:
                    role = msg.get("role", "user")
                    content = msg.get("content", "")
                    timestamp = msg.get("timestamp", "")
                    
                    if role == "user":
                        log.write(f"[bold cyan]你[/] [{dim}{timestamp}[/]]: {content}")
                    else:
                        log.write(f"[bold #E9A568]林依[/] [{dim}{timestamp}[/]]: {content}")
                log.write("")
            else:
                log.write("[#E9A568]欢迎与林依对话！[/]")
                log.write("[dim]开始新的对话吧！[/]\n")
        except Exception as e:
            log = self.query_one("#chat_log", RichLog)
            log.write(f"[yellow]提示: 使用模拟数据模式 ({e})[/]\n")
    
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
        timestamp = datetime.now().strftime("%H:%M:%S")
        log.write(f"\n[bold cyan]你[/] [dim]{timestamp}[/]: {message}")
        input_widget.value = ""
        
        # 显示思考中
        log.write("[dim italic]林依正在思考...[/]")
        
        try:
            # 调用服务发送消息
            response = await self.app.client.call("session.send_message", text=message)
            
            # 显示回复
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
        background: #0A0805;
        border: solid #1C1812;
        padding: 1;
        margin-bottom: 1;
    }
    
    .itinerary_title {
        text-style: bold;
        color: #E9A568;
        margin-bottom: 1;
    }
    
    .stats_line {
        color: #C9B89A;
    }
    
    #itinerary_content {
        width: 100%;
        height: 1fr;
        background: #0A0805;
        border: solid #1C1812;
        padding: 1;
    }
    
    .timeline_item {
        margin-bottom: 2;
    }
    
    .timeline_time {
        color: #E9A568;
        text-style: bold;
    }
    
    .timeline_activity {
        color: #F5E6D3;
        margin-left: 2;
    }
    
    .timeline_location {
        color: #8A6B4F;
        margin-left: 2;
    }
    
    .timeline_type {
        color: #D4863C;
        margin-left: 2;
    }
    
    .current_activity {
        background: #12100D;
        padding: 0 1;
    }
    """
    
    def compose(self) -> ComposeResult:
        with Vertical(classes="itinerary_header"):
            yield Label("📅 今日行程时间线", classes="itinerary_title")
            yield Label("统计信息加载中...", id="itinerary_stats", classes="stats_line")
        
        yield RichLog(id="itinerary_content", highlight=True, markup=True)
    
    async def load_data(self, client) -> None:
        """加载今日行程"""
        try:
            itinerary = await client.call("schedule.get_today_itinerary")
            content = self.query_one("#itinerary_content", RichLog)
            stats = self.query_one("#itinerary_stats", Label)
            content.clear()
            
            if itinerary and len(itinerary) > 0:
                # 更新统计
                total = len(itinerary)
                agent_count = sum(1 for i in itinerary if i.get("type") == "agent")
                user_count = sum(1 for i in itinerary if i.get("type") == "user")
                shared_count = sum(1 for i in itinerary if i.get("type") == "shared")
                
                stats.update(
                    f"共 {total} 项行程 • "
                    f"林依个人: {agent_count} • "
                    f"你的: {user_count} • "
                    f"共同: {shared_count}"
                )
                
                # 显示时间线
                current_time = datetime.now().strftime("%H:%M")
                content.write("[#E9A568]═══ 今日行程时间线 ═══[/]\n")
                
                for item in itinerary:
                    start_time = item.get("start_time", "")
                    end_time = item.get("end_time", "")
                    activity = item.get("activity", "")
                    location = item.get("location", "")
                    item_type = item.get("type", "agent")
                    is_current = item.get("is_current", False)
                    
                    # 类型标签
                    type_label = {
                        "agent": "[#E9A568]林依[/]",
                        "user": "[cyan]你[/]",
                        "shared": "[#D4863C]共同[/]"
                    }.get(item_type, "")
                    
                    # 时间范围
                    time_str = f"{start_time}"
                    if end_time:
                        time_str += f" - {end_time}"
                    
                    # 当前活动高亮
                    if is_current:
                        content.write(f"\n[reverse][bold #E9A568]▶ 当前[/][/]")
                    
                    content.write(f"[bold]{time_str}[/] {type_label}")
                    content.write(f"  📍 {activity}")
                    if location:
                        content.write(f"  🌍 {location}")
                    content.write("")
                
            else:
                stats.update("今日暂无行程安排")
                content.write("[dim]今日还没有安排行程[/]")
                content.write("[dim]林依会在每天 00:05 自动生成当日计划[/]")
                
        except Exception as e:
            content = self.query_one("#itinerary_content", RichLog)
            stats = self.query_one("#itinerary_stats", Label)
            stats.update(f"加载失败: {e}")
            content.write(f"[red]无法加载行程数据: {e}[/]")


class ScenePoolView(VerticalScroll):
    """场景池视图"""
    
    CSS = """
    ScenePoolView {
        width: 100%;
        height: 100%;
        padding: 1;
    }
    
    .scene_header {
        width: 100%;
        height: auto;
        background: #0A0805;
        border: solid #1C1812;
        padding: 1;
        margin-bottom: 1;
    }
    
    .scene_title {
        text-style: bold;
        color: #E9A568;
        margin-bottom: 1;
    }
    
    #scene_content {
        width: 100%;
        height: 1fr;
        background: #0A0805;
        border: solid #1C1812;
        padding: 1;
    }
    
    .scene_item {
        margin-bottom: 2;
        padding: 1;
        background: #12100D;
        border-left: thick #E9A568;
    }
    
    .scene_item.current {
        background: #1C1812;
        border-left: thick #D4863C;
    }
    
    .scene_name {
        color: #E9A568;
        text-style: bold;
    }
    
    .scene_visited {
        color: #8A6B4F;
    }
    """
    
    def compose(self) -> ComposeResult:
        with Vertical(classes="scene_header"):
            yield Label("🌍 场景池", classes="scene_title")
            yield Label("统计信息加载中...", id="scene_stats")
        
        yield RichLog(id="scene_content", highlight=True, markup=True)
    
    async def load_data(self, client) -> None:
        """加载场景池"""
        try:
            scenes = await client.call("scene.list_pool")
            current_scene = await client.call("scene.get_current")
            
            content = self.query_one("#scene_content", RichLog)
            stats = self.query_one("#scene_stats", Label)
            content.clear()
            
            current_location = current_scene.get("location", "") if current_scene else ""
            
            if scenes and len(scenes) > 0:
                visited_count = sum(1 for s in scenes if s.get("visited", False))
                stats.update(f"共 {len(scenes)} 个场景 • 已访问: {visited_count}")
                
                content.write("[#E9A568]═══ 场景池 ═══[/]\n")
                
                for scene in scenes:
                    location_id = scene.get("location_id", "")
                    name = scene.get("name", "")
                    visited = scene.get("visited", False)
                    areas = scene.get("areas", [])
                    description = scene.get("description", "")
                    
                    is_current = (name == current_location or location_id == current_location)
                    
                    if is_current:
                        content.write(f"\n[reverse][bold #D4863C]▶ 当前场景[/][/]")
                    
                    content.write(f"[bold #E9A568]{name}[/]")
                    
                    if visited:
                        content.write(f"  [dim]已访问[/]")
                    else:
                        content.write(f"  [#8A6B4F]未访问[/]")
                    
                    if description:
                        content.write(f"  {description}")
                    
                    if areas and len(areas) > 0:
                        area_names = ", ".join(areas)
                        content.write(f"  区域: {area_names}")
                    
                    content.write("")
                
            else:
                stats.update("场景池为空")
                content.write("[dim]还没有创建任何场景[/]")
                content.write("[dim]场景会在林依外出时自动生成[/]")
                
        except Exception as e:
            content = self.query_one("#scene_content", RichLog)
            stats = self.query_one("#scene_stats", Label)
            stats.update(f"加载失败: {e}")
            content.write(f"[red]无法加载场景数据: {e}[/]")


class MemoryView(VerticalScroll):
    """记忆与知识视图"""
    
    CSS = """
    MemoryView {
        width: 100%;
        height: 100%;
        padding: 1;
    }
    
    .memory_header {
        width: 100%;
        height: auto;
        background: #0A0805;
        border: solid #1C1812;
        padding: 1;
        margin-bottom: 1;
    }
    
    .search_container {
        width: 100%;
        height: auto;
        layout: horizontal;
        margin-top: 1;
    }
    
    #memory_search {
        width: 1fr;
        margin-right: 1;
    }
    
    #memory_content {
        width: 100%;
        height: 1fr;
        background: #0A0805;
        border: solid #1C1812;
        padding: 1;
    }
    """
    
    def compose(self) -> ComposeResult:
        with Vertical(classes="memory_header"):
            yield Label("🧠 记忆与知识", classes="scene_title")
            with Horizontal(classes="search_container"):
                yield Input(placeholder="搜索记忆...", id="memory_search")
                yield Button("搜索", variant="primary", id="search_btn")
        
        yield RichLog(id="memory_content", highlight=True, markup=True)
    
    async def on_mount(self) -> None:
        content = self.query_one("#memory_content", RichLog)
        content.write("[#E9A568]记忆系统[/]")
        content.write("[dim]输入关键词搜索相关记忆[/]\n")
    
    async def load_data(self, client) -> None:
        """加载记忆统计"""
        try:
            # 获取记忆统计信息
            stats = await client.call("memory.get_stats")
            content = self.query_one("#memory_content", RichLog)
            content.clear()
            
            if stats:
                total = stats.get("total", 0)
                recent = stats.get("recent_count", 0)
                
                content.write(f"[#E9A568]记忆统计[/]")
                content.write(f"总记忆数: {total}")
                content.write(f"近期记忆: {recent}\n")
                content.write("[dim]输入关键词搜索相关记忆[/]")
            else:
                content.write("[#E9A568]记忆系统[/]")
                content.write("[dim]输入关键词搜索相关记忆[/]\n")
                
        except Exception as e:
            content = self.query_one("#memory_content", RichLog)
            content.clear()
            content.write("[#E9A568]记忆系统[/]")
            content.write("[dim]输入关键词搜索相关记忆[/]\n")
    
    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "search_btn":
            await self.perform_search()
    
    async def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "memory_search":
            await self.perform_search()
    
    async def perform_search(self) -> None:
        """执行搜索"""
        search_input = self.query_one("#memory_search", Input)
        query = search_input.value.strip()
        
        if not query:
            return
        
        content = self.query_one("#memory_content", RichLog)
        content.clear()
        content.write(f"[#E9A568]搜索: {query}[/]\n")
        content.write("[dim]搜索中...[/]")
        
        try:
            results = await self.app.client.call("memory.search", query=query, limit=20)
            content.clear()
            content.write(f"[#E9A568]搜索: {query}[/]\n")
            
            if results and len(results) > 0:
                content.write(f"找到 {len(results)} 条相关记忆：\n")
                
                for i, result in enumerate(results, 1):
                    text = result.get("text", "")
                    relevance = result.get("relevance", 0.0)
                    timestamp = result.get("timestamp", "")
                    
                    content.write(f"[bold]{i}.[/] [dim]{timestamp}[/] [#8A6B4F](相关度: {relevance:.2f})[/]")
                    content.write(f"  {text}\n")
            else:
                content.write("[dim]未找到相关记忆[/]")
                
        except Exception as e:
            content.write(f"[red]搜索失败: {e}[/]")


class RelationshipView(VerticalScroll):
    """关系网络视图"""
    
    CSS = """
    RelationshipView {
        width: 100%;
        height: 100%;
        padding: 1;
    }
    
    .relationship_header {
        width: 100%;
        height: auto;
        background: #0A0805;
        border: solid #1C1812;
        padding: 1;
        margin-bottom: 1;
    }
    
    #relationship_content {
        width: 100%;
        height: 1fr;
        background: #0A0805;
        border: solid #1C1812;
        padding: 1;
    }
    """
    
    def compose(self) -> ComposeResult:
        with Vertical(classes="relationship_header"):
            yield Label("💭 关系网络", classes="scene_title")
            yield Label("统计信息加载中...", id="relationship_stats")
        
        yield RichLog(id="relationship_content", highlight=True, markup=True)
    
    async def load_data(self, client) -> None:
        """加载关系网络"""
        try:
            relationships = await client.call("relationship.list_all")
            content = self.query_one("#relationship_content", RichLog)
            stats = self.query_one("#relationship_stats", Label)
            content.clear()
            
            if relationships and len(relationships) > 0:
                total = len(relationships)
                total_score = sum(r.get("score", 0) for r in relationships)
                avg_score = total_score / total if total > 0 else 0
                
                stats.update(f"共 {total} 个关系实体 • 平均分数: {avg_score:.1f}")
                
                content.write("[#E9A568]═══ 关系网络 ═══[/]\n")
                
                # 按分数排序
                sorted_rels = sorted(relationships, key=lambda x: x.get("score", 0), reverse=True)
                
                for rel in sorted_rels:
                    entity = rel.get("entity", "")
                    score = rel.get("score", 0)
                    updated = rel.get("updated", "")
                    history = rel.get("history", [])
                    
                    # 计算亲密度等级和颜色
                    if score >= 80:
                        intimacy = "亲密"
                        color = "#A8C079"  # 绿色
                    elif score >= 60:
                        intimacy = "友好"
                        color = "#E9A568"  # 琥珀
                    elif score >= 40:
                        intimacy = "普通"
                        color = "#C9B89A"  # 米黄
                    elif score >= 20:
                        intimacy = "陌生"
                        color = "#8A7A66"  # 灰褐
                    else:
                        intimacy = "疏远"
                        color = "#D97757"  # 暖红
                    
                    content.write(f"[bold]{entity}[/]")
                    content.write(f"  [{color}]{intimacy}[/] [dim]({score} 分)[/]")
                    content.write(f"  [dim]更新: {updated}[/]")
                    
                    if history and len(history) > 0:
                        recent = history[-1] if isinstance(history, list) else {}
                        if isinstance(recent, dict) and "event" in recent:
                            content.write(f"  最近: {recent.get('event', '')}")
                    
                    content.write("")
                
            else:
                stats.update("暂无关系数据")
                content.write("[dim]还没有建立任何关系[/]")
                content.write("[dim]关系会在对话和互动中自动建立[/]")
                
        except Exception as e:
            content = self.query_one("#relationship_content", RichLog)
            stats = self.query_one("#relationship_stats", Label)
            stats.update(f"加载失败: {e}")
            content.write(f"[red]无法加载关系数据: {e}[/]")


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
        background: #0A0805;
        border: solid #1C1812;
        padding: 1;
        margin-bottom: 1;
    }
    
    .filter_buttons {
        width: 100%;
        height: auto;
        layout: horizontal;
        margin-top: 1;
    }
    
    .filter_buttons Button {
        margin-right: 1;
    }
    
    #audit_content {
        width: 100%;
        height: 1fr;
        background: #0A0805;
        border: solid #1C1812;
        padding: 1;
    }
    """
    
    current_filter = reactive("all")
    
    def compose(self) -> ComposeResult:
        with Vertical(classes="audit_header"):
            yield Label("🔍 审计日志", classes="scene_title")
            with Horizontal(classes="filter_buttons"):
                yield Button("全部", variant="primary", id="filter_all")
                yield Button("高风险", variant="default", id="filter_high_risk")
                yield Button("操作", variant="default", id="filter_actions")
                yield Button("决策", variant="default", id="filter_decisions")
        
        yield RichLog(id="audit_content", highlight=True, markup=True)
    
    async def load_data(self, client, filter_type: str = "all") -> None:
        """加载审计日志"""
        self.current_filter = filter_type
        
        try:
            logs = await client.call("audit.get_logs", filter=filter_type, limit=100)
            content = self.query_one("#audit_content", RichLog)
            content.clear()
            
            if logs and len(logs) > 0:
                content.write(f"[#E9A568]审计日志[/] [dim](过滤: {filter_type})[/]\n")
                
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
                    
                    content.write(
                        f"\n[dim]{timestamp}[/] "
                        f"[{risk_color}]●[/] "
                        f"[bold]{action}[/] "
                        f"[dim]({category})[/]"
                    )
                    if result:
                        content.write(f"  {result}")
            else:
                content.write("[dim]暂无审计日志[/]")
                content.write("[dim]审计日志会记录 Agent 的所有操作和决策[/]")
                
        except Exception as e:
            content = self.query_one("#audit_content", RichLog)
            content.clear()
            content.write(f"[red]无法加载审计日志: {e}[/]")
    
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
