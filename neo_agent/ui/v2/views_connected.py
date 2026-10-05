"""TUI 视图 - 连接服务版本"""
from textual.widgets import Static, Input, RichLog
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
    
    def show_loading(self, message: str = "加载中..."):
        """显示加载状态"""
        self.loading = True
        # 子类实现具体逻辑
    
    def hide_loading(self):
        """隐藏加载状态"""
        self.loading = False


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
            
            # 移除"思考中"
            history.clear()
            history.write(f"[bold #C9B89A]你:[/] {text}")
            
            # 显示回复
            reply = result.get("reply", "（无回复）")
            emotion = result.get("emotion", {}).get("state", "平静")
            
            history.write(
                f"[bold #E9A568]林依:[/] {reply}\n"
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
        await self.refresh_itinerary()
    
    async def refresh_itinerary(self):
        """刷新行程"""
        container = self.query_one("#itinerary-content", ScrollableContainer)
        
        try:
            itinerary = await self.client.get_today_itinerary()
            
            container.remove_children()
            
            if not itinerary:
                container.mount(Static("[dim #8A6B4F]今日暂无安排[/]"))
                return
            
            for item in itinerary:
                time = item.get("time", "未知")
                activity = item.get("activity", "未知活动")
                location = item.get("location", "")
                item_type = item.get("type", "personal")
                
                type_label = {
                    "personal": "个人",
                    "user": "用户",
                    "shared": "共同"
                }.get(item_type, "未知")
                
                location_text = f" @ {location}" if location else ""
                
                container.mount(Static(
                    f"[bold #D4863C]{time}[/] "
                    f"[#C9B89A]{activity}[/]{location_text} "
                    f"[dim italic #8A6B4F]({type_label})[/]",
                    classes="itinerary-item"
                ))
        
        except Exception as e:
            container.mount(Static(f"[bold #D97757]✗ 加载失败:[/] {e}"))


class ScenePoolView(BaseView):
    """场景池视图"""
    
    def compose(self):
        yield Static("[bold #E9A568]🌍 场景池[/]\n", classes="view-title")
        
        with Vertical():
            yield Static("[bold #C9B89A]当前场景[/]", classes="section-title")
            yield Static(id="current-scene-display", classes="scene-display")
            
            yield Static("\n[bold #C9B89A]已访问场景[/]", classes="section-title")
            yield ScrollableContainer(id="scene-pool-list")
    
    async def on_mount(self):
        """挂载时加载场景"""
        await self.refresh_scenes()
    
    async def refresh_scenes(self):
        """刷新场景"""
        try:
            # 当前场景
            current = await self.client.get_current_scene()
            current_display = self.query_one("#current-scene-display", Static)
            
            location = current.get("location", {}).get("name", "未知")
            area = current.get("area", {}).get("name", "")
            description = current.get("description", "")
            
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
                
                pool_list.mount(Static(
                    f"[#A8C079]{visited}[/] [#C9B89A]{name}[/]",
                    classes="scene-item"
                ))
        
        except Exception as e:
            self.query_one("#current-scene-display", Static).update(
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
                placeholder="搜索记忆或知识...",
                id="memory-search-input",
                classes="search-input"
            )
        
        yield ScrollableContainer(id="memory-results")
    
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
                
                results_container.mount(Static(
                    f"[#C9B89A]{content}[/] "
                    f"[dim #8A6B4F](相关度: {relevance:.2f})[/]",
                    classes="memory-item"
                ))
        
        except Exception as e:
            results_container.remove_children()
            results_container.mount(Static(f"[bold #D97757]✗ 搜索失败:[/] {e}"))


class RelationshipView(BaseView):
    """关系网络视图"""
    
    def compose(self):
        yield Static("[bold #E9A568]💭 关系网络[/]\n", classes="view-title")
        yield ScrollableContainer(id="relationship-list")
    
    async def on_mount(self):
        """挂载时加载关系"""
        await self.refresh_relationships()
    
    async def refresh_relationships(self):
        """刷新关系"""
        container = self.query_one("#relationship-list", ScrollableContainer)
        
        try:
            # 获取与用户的关系
            status = await self.client.get_relationship_status("user")
            
            container.remove_children()
            
            score = status.get("score", 0)
            last_update = status.get("last_update", "未知")
            
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
            
            container.mount(Static(
                f"[bold #C9B89A]与用户的关系[/]\n"
                f"[{color}]{level}[/] ([bold]{score}[/])\n"
                f"[dim #8A6B4F]最后更新: {last_update}[/]",
                classes="relationship-card"
            ))
        
        except Exception as e:
            container.mount(Static(f"[bold #D97757]✗ 加载失败:[/] {e}"))


class AuditView(BaseView):
    """审计日志视图"""
    
    def compose(self):
        yield Static("[bold #E9A568]🔍 审计日志[/]\n", classes="view-title")
        yield RichLog(id="audit-log", wrap=True, markup=True)
    
    def on_mount(self):
        """挂载时显示提示"""
        log = self.query_one("#audit-log", RichLog)
        log.write("[dim #8A6B4F]审计日志功能即将推出...[/]")
