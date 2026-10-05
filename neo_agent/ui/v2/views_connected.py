"""TUI 视图 - 连接服务版本"""
from textual.widgets import Static, Input, RichLog, DataTable
from textual.containers import Vertical, Horizontal, ScrollableContainer
from textual.binding import Binding
from textual import events
import asyncio
from datetime import datetime
from typing import Optional

from .client import ServiceClient


class BaseView(Vertical):
    """视图基类"""
    
    def __init__(self, client: ServiceClient, **kwargs):
        super().__init__(**kwargs)
        self.client = client
        self.loading = False
    
    async def refresh_data(self):
        """刷新视图数据（子类重写）"""
        pass


class ChatView(BaseView):
    """对话视图"""
    
    BINDINGS = [
        Binding("enter", "send_message", "发送", key_display="Enter"),
    ]
    
    def compose(self):
        yield Static("[bold #E9A568]💬 对话[/]\n", classes="view-title")
        
        # 消息历史
        yield RichLog(id="chat-history", wrap=True, markup=True)
        
        # 输入区域
        with Horizontal(id="chat-input-area"):
            yield Input(
                placeholder="输入消息... (Enter 发送)",
                id="chat-input",
                classes="chat-input"
            )
    
    def on_mount(self):
        """挂载时加载历史"""
        self.query_one("#chat-history", RichLog).write(
            "[dim #8A6B4F]欢迎使用 Neo Agent。输入消息开始对话。[/]"
        )
    
    async def action_send_message(self):
        """发送消息"""
        input_widget = self.query_one("#chat-input", Input)
        text = input_widget.value.strip()
        
        if not text:
            return
        
        # 清空输入
        input_widget.value = ""
        
        # 显示用户消息
        history = self.query_one("#chat-history", RichLog)
        history.write(f"[bold #C9B89A]你:[/] {text}")
        
        # 显示思考中
        history.write("[dim #8A7A66]思考中...[/]")
        
        try:
            # 发送到服务
            result = await self.client.send_message(text)
            
            # 显示回复
            reply = result.get("reply", "（无回复）")
            emotion = result.get("emotion", {}).get("state", "平静")
            
            history.write(
                f"\n[bold #E9A568]林依:[/] {reply}\n"
                f"[dim italic #8A6B4F]情绪: {emotion}[/]"
            )
            
        except Exception as e:
            history.write(f"[bold #D97757]✗ 发送失败:[/] {e}")


class ItineraryView(BaseView):
    """今日行程视图"""
    
    def compose(self):
        yield Static("[bold #E9A568]📅 今日行程[/]\n", classes="view-title")
        yield ScrollableContainer(id="itinerary-content")
    
    async def on_mount(self):
        """挂载时加载行程"""
        await self.refresh_data()
    
    async def refresh_data(self):
        """刷新行程"""
        container = self.query_one("#itinerary-content", ScrollableContainer)
        
        try:
            itinerary = await self.client.get_today_itinerary()
            
            container.remove_children()
            
            if not itinerary:
                container.mount(Static("[dim #8A6B4F]今日暂无安排[/]"))
                return
            
            # 按时间排序
            itinerary_sorted = sorted(itinerary, key=lambda x: x.get("time", ""))
            
            for item in itinerary_sorted:
                time = item.get("time", "未知")
                activity = item.get("activity", "未知活动")
                location = item.get("location", "")
                item_type = item.get("type", "personal")
                is_current = item.get("is_current", False)
                
                type_label = {
                    "personal": "个人",
                    "user": "用户",
                    "shared": "共同"
                }.get(item_type, "未知")
                
                location_text = f" @ {location}" if location else ""
                current_mark = "► " if is_current else "  "
                
                container.mount(Static(
                    f"{current_mark}[bold #D4863C]{time}[/] "
                    f"[#C9B89A]{activity}[/]{location_text} "
                    f"[dim italic #8A6B4F]({type_label})[/]",
                    classes="itinerary-item"
                ))
        
        except Exception as e:
            container.remove_children()
            container.mount(Static(f"[bold #D97757]✗ 加载失败:[/] {e}"))


class ScenePoolView(BaseView):
    """场景池视图"""
    
    def compose(self):
        yield Static("[bold #E9A568]🌍 场景池[/]\n", classes="view-title")
        
        with Vertical():
            yield Static("[bold #C9B89A]当前场景[/]", classes="section-title")
            yield Static(id="current-scene-display", classes="scene-display")
            
            yield Static("\n[bold #C9B89A]场景池[/]", classes="section-title")
            yield ScrollableContainer(id="scene-pool-list")
    
    async def on_mount(self):
        """挂载时加载场景"""
        await self.refresh_data()
    
    async def refresh_data(self):
        """刷新场景"""
        current_display = self.query_one("#current-scene-display", Static)
        
        try:
            # 当前场景
            scene = await self.client.get_current_scene()
            location = scene.get("location", {}).get("name", "未知")
            area = scene.get("area", {}).get("name", "")
            description = scene.get("description", "")
            
            current_display.update(
                f"[bold #E9A568]{location}[/]"
                f"{f' - {area}' if area else ''}\n"
                f"[#8A7A66]{description}[/]"
            )
            
            # 场景池
            pool = await self.client.get_scene_pool()
            pool_list = self.query_one("#scene-pool-list", ScrollableContainer)
            pool_list.remove_children()
            
            if not pool:
                pool_list.mount(Static("[dim #8A6B4F]暂无其他场景[/]"))
                return
            
            for scene in pool:
                name = scene.get("name", "未知")
                visited = "✓" if scene.get("visited") else "○"
                scene_type = scene.get("type", "location")
                
                pool_list.mount(Static(
                    f"[#A8C079]{visited}[/] [#C9B89A]{name}[/] [dim #8A6B4F]({scene_type})[/]",
                    classes="scene-item"
                ))
        
        except Exception as e:
            current_display.update(
                f"[bold #D97757]✗ 加载失败:[/] {e}"
            )


class MemoryView(BaseView):
    """记忆与知识视图"""
    
    BINDINGS = [
        Binding("enter", "search", "搜索", key_display="Enter"),
    ]
    
    def compose(self):
        yield Static("[bold #E9A568]🧠 记忆与知识[/]\n", classes="view-title")
        
        with Horizontal():
            yield Input(
                placeholder="搜索记忆或知识... (Enter 搜索)",
                id="memory-search-input",
                classes="search-input"
            )
        
        yield ScrollableContainer(id="memory-results")
    
    def on_mount(self):
        """挂载时显示提示"""
        results = self.query_one("#memory-results", ScrollableContainer)
        results.mount(Static("[dim #8A6B4F]输入关键词搜索记忆与知识[/]"))
    
    async def action_search(self):
        """搜索"""
        input_widget = self.query_one("#memory-search-input", Input)
        query = input_widget.value.strip()
        
        if not query:
            return
        
        results_container = self.query_one("#memory-results", ScrollableContainer)
        results_container.remove_children()
        results_container.mount(Static("[dim #8A6B4F]搜索中...[/]"))
        
        try:
            # 搜索记忆
            memories = await self.client.search_memory(query)
            
            results_container.remove_children()
            
            if not memories:
                results_container.mount(Static("[dim #8A6B4F]未找到相关记忆[/]"))
                return
            
            for mem in memories:
                content = mem.get("content", "")
                relevance = mem.get("relevance", 0)
                timestamp = mem.get("timestamp", "")
                
                results_container.mount(Static(
                    f"[#C9B89A]{content}[/]\n"
                    f"[dim #8A6B4F]相关度: {relevance:.2f} | {timestamp}[/]",
                    classes="memory-item"
                ))
        
        except Exception as e:
            results_container.remove_children()
            results_container.mount(Static(f"[bold #D97757]✗ 搜索失败:[/] {e}"))


    async def refresh_data(self):
        """刷新数据（记忆视图保持当前搜索结果）"""
        pass

class RelationshipView(BaseView):
    """关系网络视图"""
    
    def compose(self):
        yield Static("[bold #E9A568]💭 关系网络[/]\n", classes="view-title")
        yield ScrollableContainer(id="relationship-list")
    
    async def on_mount(self):
        """挂载时加载关系"""
        await self.refresh_data()
    
    async def refresh_data(self):
        """刷新关系"""
        container = self.query_one("#relationship-list", ScrollableContainer)
        container.remove_children()
        
        try:
            # 获取与用户的关系
            status = await self.client.get_relationship_status("user")
            
            score = status.get("score", 0)
            last_update = status.get("last_update", "未知")
            history = status.get("history", [])
            
            # 关系等级
            if score >= 80:
                level = "挚友"
                color = "#A8C079"
            elif score >= 50:
                level = "朋友"
                color = "#E9A568"
            elif score >= 0:
                level = "普通"
                color = "#C9B89A"
            else:
                level = "陌生"
                color = "#8A7A66"
            
            # 进度条
            bar_length = 20
            filled = int((score + 100) / 200 * bar_length)
            bar = "█" * filled + "░" * (bar_length - filled)
            
            container.mount(Static(
                f"[bold #C9B89A]与用户的关系[/]\n\n"
                f"[{color}]{level}[/] [bold]{score}[/]/100\n"
                f"[{color}]{bar}[/]\n\n"
                f"[dim #8A6B4F]最后更新: {last_update}[/]",
                classes="relationship-card"
            ))
            
            # 历史变化
            if history:
                container.mount(Static("\n[bold #C9B89A]最近变化[/]", classes="section-title"))
                for change in history[-5:]:  # 最近 5 条
                    delta = change.get("delta", 0)
                    reason = change.get("reason", "未知")
                    time = change.get("timestamp", "")
                    
                    delta_text = f"+{delta}" if delta > 0 else str(delta)
                    delta_color = "#A8C079" if delta > 0 else "#D97757"
                    
                    container.mount(Static(
                        f"[{delta_color}]{delta_text}[/] {reason} [dim #8A6B4F]{time}[/]"
                    ))
        
        except Exception as e:
            container.mount(Static(f"[bold #D97757]✗ 加载失败:[/] {e}"))


class AuditView(BaseView):
    """审计日志视图"""
    
    def compose(self):
        yield Static("[bold #E9A568]🔍 审计日志[/]\n", classes="view-title")
        yield RichLog(id="audit-log", wrap=True, markup=True, auto_scroll=True)
    
    async def on_mount(self):
        """挂载时加载日志"""
        await self.refresh_data()
    
    async def refresh_data(self):
        """刷新审计日志"""
        log = self.query_one("#audit-log", RichLog)
        log.clear()
        
        try:
            # 获取审计日志
            entries = await self.client.get_audit_log(limit=50)
            
            if not entries:
                log.write("[dim #8A6B4F]暂无审计记录[/]")
                return
            
            for entry in entries:
                timestamp = entry.get("timestamp", "")
                action = entry.get("action", "未知操作")
                risk = entry.get("risk", "low")
                details = entry.get("details", "")
                result = entry.get("result", "")
                
                # 风险颜色
                risk_color = {
                    "high": "#D97757",
                    "medium": "#E9A568",
                    "low": "#A8C079"
                }.get(risk, "#C9B89A")
                
                risk_label = {
                    "high": "高风险",
                    "medium": "中风险",
                    "low": "低风险"
                }.get(risk, "未知")
                
                # 结果图标
                result_icon = "✓" if result == "success" else "✗" if result == "failed" else "•"
                result_color = "#A8C079" if result == "success" else "#D97757" if result == "failed" else "#8A6B4F"
                
                log.write(
                    f"[dim #8A6B4F]{timestamp}[/] "
                    f"[{result_color}]{result_icon}[/] "
                    f"[bold #E9A568]{action}[/] "
                    f"[{risk_color}][{risk_label}][/]"
                )
                
                if details:
                    log.write(f"  [#C9B89A]{details}[/]")
                
                log.write("")  # 空行分隔
        
        except Exception as e:
            log.write(f"[bold #D97757]✗ 加载失败:[/] {e}")
