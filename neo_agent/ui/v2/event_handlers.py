"""WebSocket 事件处理器"""
from typing import TYPE_CHECKING, Dict, Any
from datetime import datetime

if TYPE_CHECKING:
    from .app import NeoAgentApp


class EventHandlers:
    """处理来自服务端的 WebSocket 事件"""
    
    def __init__(self, app: "NeoAgentApp"):
        self.app = app
        
    async def handle_event(self, event_type: str, data: Dict[str, Any]):
        """路由事件到对应处理器"""
        handler_name = f"on_{event_type}"
        handler = getattr(self, handler_name, None)
        
        if handler and callable(handler):
            await handler(data)
        else:
            # 未知事件，记录但不报错
            pass
    
    async def on_scene_changed(self, data: Dict[str, Any]):
        """场景切换事件"""
        scene = data.get("scene", {})
        location = scene.get("location", "未知")
        area = scene.get("area", "")
        
        # 更新状态栏
        status_bar = self.app.query_one("#status-bar")
        status_bar.update_scene(f"{location} - {area}" if area else location)
        
        # 刷新场景池视图
        main_content = self.app.query_one("#main-content")
        if "scenes" in main_content.views:
            scene_view = main_content.views["scenes"]
            await scene_view.reload_data()
        
        # 显示通知
        self.app.notify(f"📍 场景切换：{location}", severity="information", timeout=3)
    
    async def on_emotion_updated(self, data: Dict[str, Any]):
        """情绪更新事件"""
        emotion = data.get("emotion", {})
        state = emotion.get("state", "平静")
        
        # 更新状态栏
        status_bar = self.app.query_one("#status-bar")
        status_bar.update_emotion(state)
        
        # 显示通知（低优先级，不打扰）
        # self.app.notify(f"💭 情绪变化：{state}", timeout=2)
    
    async def on_message_received(self, data: Dict[str, Any]):
        """新消息事件"""
        reply = data.get("agent_reply", "")
        
        # 刷新对话视图
        main_content = self.app.query_one("#main-content")
        if "chat" in main_content.views:
            chat_view = main_content.views["chat"]
            # 如果在对话视图，自动刷新
            if main_content.current_view_id == "chat":
                await chat_view.reload_data()
        
        # 不显示通知，避免打扰
    
    async def on_schedule_triggered(self, data: Dict[str, Any]):
        """日程触发事件"""
        activity = data.get("activity", "")
        location = data.get("location", "")
        
        # 刷新行程视图
        main_content = self.app.query_one("#main-content")
        if "itinerary" in main_content.views:
            itinerary_view = main_content.views["itinerary"]
            await itinerary_view.reload_data()
        
        # 显示通知
        self.app.notify(
            f"⏰ 日程提醒：{activity}",
            title=f"地点：{location}" if location else None,
            severity="information",
            timeout=5
        )
    
    async def on_relationship_changed(self, data: Dict[str, Any]):
        """关系变化事件"""
        entity = data.get("entity", "")
        change = data.get("change", 0)
        
        # 刷新关系视图
        main_content = self.app.query_one("#main-content")
        if "relationships" in main_content.views:
            rel_view = main_content.views["relationships"]
            await rel_view.reload_data()
        
        # 显示通知（仅显著变化）
        if abs(change) >= 2:
            direction = "上升" if change > 0 else "下降"
            self.app.notify(f"💭 与 {entity} 的关系{direction}", timeout=3)
    
    async def on_daily_itinerary_generated(self, data: Dict[str, Any]):
        """每日行程生成完成"""
        date = data.get("date", "")
        count = data.get("count", 0)
        
        # 刷新行程视图
        main_content = self.app.query_one("#main-content")
        if "itinerary" in main_content.views:
            itinerary_view = main_content.views["itinerary"]
            await itinerary_view.reload_data()
        
        # 显示通知
        self.app.notify(
            f"📅 今日行程已生成",
            title=f"共 {count} 项活动",
            severity="information",
            timeout=5
        )
    
    async def on_system_status_changed(self, data: Dict[str, Any]):
        """系统状态变化"""
        debug_mode = data.get("debug_mode")
        
        if debug_mode is not None:
            mode_text = "开启" if debug_mode else "关闭"
            self.app.notify(f"⚙️  调试模式已{mode_text}", severity="warning", timeout=3)
            
            # 刷新所有视图（可能需要显示/隐藏编辑入口）
            main_content = self.app.query_one("#main-content")
            current_view_id = main_content.current_view_id
            if current_view_id in main_content.views:
                await main_content.views[current_view_id].reload_data()
    
    async def on_audit_logged(self, data: Dict[str, Any]):
        """新审计日志"""
        risk_level = data.get("risk_level", "low")
        
        # 仅高风险操作才刷新审计视图
        if risk_level == "high":
            main_content = self.app.query_one("#main-content")
            if "audit" in main_content.views:
                audit_view = main_content.views["audit"]
                await audit_view.reload_data()
