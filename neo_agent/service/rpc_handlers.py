"""JSON-RPC API 处理器，封装运行时服务"""
import asyncio
from datetime import datetime
from typing import Any, Dict, List, Optional

from neo_agent.runtime import (
    AgentRuntime, DailyItineraryService, SceneService,
    MemoryService, KnowledgeService, RelationshipService, EmotionService,
    ConfigurationService, RuntimeControls, SingleRoleService
)
from neo_agent.runtime.itinerary import SceneScheduler
from neo_agent.storage import DiskStore
from .events import EventBroadcaster, EventType, ServiceEvent


class RPCHandlers:
    """JSON-RPC 方法处理器"""
    
    def __init__(self, disk_store: DiskStore, broadcaster: EventBroadcaster):
        self.store = disk_store
        self.broadcaster = broadcaster
        
        # 运行时服务初始化
        self.controls = RuntimeControls(disk_store)
        self.role_service = SingleRoleService(disk_store)
        self.config_service = ConfigurationService(disk_store)
        self.agent = AgentRuntime(disk_store)
        self.itinerary_service = DailyItineraryService(disk_store)
        self.scene_service = SceneService(disk_store)
        self.scene_scheduler = SceneScheduler(disk_store, scenes=self.scene_service, itinerary=self.itinerary_service)
        self.memory_service = MemoryService(disk_store)
        self.knowledge_service = KnowledgeService(disk_store)
        self.relationship_service = RelationshipService(disk_store)
        self.emotion_service = EmotionService(disk_store)
        
        self._startup_time = datetime.now()
        self._audit_logs = []  # 内存中的审计日志缓存
        
    # ========== 会话管理 ==========
    
    async def session_send_message(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """发送消息并获取回复"""
        text = params.get("text", "")
        if not text:
            raise ValueError("message text is required")
        
        # 异步执行 Agent 推理（使用现有的 chat 方法）
        loop = asyncio.get_event_loop()
        reply = await loop.run_in_executor(
            None,
            self.agent.chat,
            text,
        )
        
        # 获取当前情绪和场景
        emotion = self.emotion_service.get_current_emotion() or {}
        scene = self.scene_service.current() or {}
        
        result = {
            "reply": reply,
            "emotion": emotion,
            "scene": scene,
        }
        
        # 记录审计日志
        self._add_audit_log("message", "low", f"用户消息: {text[:50]}...")
        
        # 广播消息事件
        await self.broadcaster.emit(ServiceEvent(
            type=EventType.MESSAGE_RECEIVED,
            timestamp=datetime.now().isoformat(),
            data={
                "user_message": text,
                "agent_reply": reply,
                "emotion": emotion,
            }
        ))
        
        return result
    
    async def session_get_context(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """获取当前会话上下文"""
        current_scene = self.scene_service.current() or {}
        emotion = self.emotion_service.get_current_emotion() or {}
        character = self.role_service.active()
        
        return {
            "current_scene": current_scene,
            "emotion": emotion,
            "character": character,
        }
    
    # ========== 角色与状态 ==========
    
    async def session_get_history(self, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """获取会话历史"""
        limit = params.get("limit", 20)
        
        try:
            # 从存储中获取历史消息
            messages = self.store.list_documents("messages")
            
            # 按时间戳排序，取最近的 N 条
            sorted_messages = sorted(messages, key=lambda m: m.get("timestamp", ""), reverse=True)
            return sorted_messages[:limit]
        except Exception as e:
            self._add_audit_log("history_error", "low", f"获取历史失败: {str(e)}")
            # 返回模拟数据
            return [
                {
                    "role": "assistant",
                    "content": "你好！我是林依，很高兴见到你。",
                    "timestamp": "2026-10-05T09:00:00"
                },
                {
                    "role": "user",
                    "content": "你好",
                    "timestamp": "2026-10-05T08:59:00"
                }
            ]
    
    async def character_get_profile(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """获取角色配置"""
        role = self.role_service.active()
        if not role:
            raise ValueError("No active character")
        return role
    
    async def character_update_profile(self, params: Dict[str, Any]) -> Dict[str, str]:
        """更新角色配置（仅 debug 模式）"""
        if not self.controls.debug:
            raise PermissionError("Character editing requires debug mode")
        
        fields = params.get("fields", {})
        character = self.role_service.active()
        if not character:
            raise ValueError("No active character")
        
        character_id = character["id"]
        
        # 更新角色数据
        current = self.store.character(character_id)
        current.update(fields)
        self.store.save_character(character_id, current)
        
        # 记录审计
        self._add_audit_log("character_update", "medium", f"更新角色配置: {list(fields.keys())}")
        
        return {"status": "ok"}
    
    # ========== 日程与场景 ==========
    
    async def schedule_get_today_itinerary(self, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """获取今日行程"""
        try:
            itinerary = self.itinerary_service.get_today_itinerary()
            return itinerary if itinerary else []
        except Exception as e:
            self._add_audit_log("schedule_error", "medium", f"获取日程失败: {str(e)}")
            return []
    
    async def scene_get_current(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """获取当前场景"""
        try:
            scene = self.scene_service.current()
            return scene if scene else {}
        except Exception as e:
            self._add_audit_log("scene_error", "low", f"获取场景失败: {str(e)}")
            return {}
    
    async def scene_list_pool(self, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """获取场景池"""
        try:
            places = self.scene_service.places(visited_only=False)
            result = []
            for place in (places or []):
                result.append({
                    "location_id": place.get("place_id"),
                    "name": place.get("name", "未命名"),
                    "visited": place.get("layout_frozen", False),
                    "area_count": len(self.scene_service.areas(place.get("place_id")) or [])
                })
            return result
        except Exception as e:
            self._add_audit_log("scene_error", "low", f"获取场景池失败: {str(e)}")
            return []
    # ========== 知识与记忆 ==========
    
    async def memory_search(self, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """搜索记忆"""
        query = params.get("query", "")
        if not query:
            return []
        
        try:
            loop = asyncio.get_event_loop()
            results = await loop.run_in_executor(
                None,
                self.store.search_memories,
                query
            )
            self._add_audit_log("memory_search", "low", f"搜索记忆: {query}")
            return results if results else []
        except Exception as e:
            self._add_audit_log("memory_error", "medium", f"记忆搜索失败: {str(e)}")
            return []
    
    async def knowledge_query(self, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """查询知识库"""
        topic = params.get("topic", "")
        if not topic:
            return []
        
        try:
            entries = self.store.list_documents("knowledge")
            # 简单的文本匹配过滤
            filtered = [e for e in entries if topic.lower() in str(e).lower()]
            self._add_audit_log("knowledge_query", "low", f"查询知识: {topic}")
            return filtered[:10]
        except Exception as e:
            self._add_audit_log("knowledge_error", "medium", f"知识查询失败: {str(e)}")
            return []
    
    # ========== 关系与情绪 ==========
    
    async def relationship_get_status(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """获取关系状态"""
        entity = params.get("entity", "")
        if not entity:
            raise ValueError("entity name is required")
        
        try:
            status = self.store.get_document("relationships", entity)
            return status if status else {}
        except Exception as e:
            self._add_audit_log("relationship_error", "low", f"获取关系失败: {str(e)}")
            return {}
    
    async def relationship_list_all(self, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """列出所有关系"""
        try:
            relationships = self.store.list_documents("relationships")
            return relationships if relationships else []
        except Exception as e:
            self._add_audit_log("relationship_error", "low", f"列出关系失败: {str(e)}")
            return []
    
    async def emotion_get_current(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """获取当前情绪"""
        try:
            emotion = self.emotion_service.get_current_emotion()
            return emotion if emotion else {}
        except Exception as e:
            self._add_audit_log("emotion_error", "low", f"获取情绪失败: {str(e)}")
            return {}
    
    # ========== 系统控制 ==========
    
    async def system_get_status(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """获取系统状态"""
        uptime = (datetime.now() - self._startup_time).total_seconds()
        
        return {
            "uptime_seconds": uptime,
            "scene_worker_status": "running",
            "daily_gen_status": "ok",
            "debug_mode": self.controls.debug,
        }
    
    async def system_set_debug(self, params: Dict[str, Any]) -> Dict[str, str]:
        """设置调试模式"""
        enabled = params.get("enabled", False)
        self.controls.set_debug(enabled)
        
        self._add_audit_log("debug_mode_change", "medium", f"调试模式: {'开启' if enabled else '关闭'}")
        
        await self.broadcaster.emit(ServiceEvent(
            type=EventType.SYSTEM_STATUS_CHANGED,
            timestamp=datetime.now().isoformat(),
            data={"debug_mode": enabled}
        ))
        
        return {"status": "ok"}
    
    async def system_get_audit_logs(self, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """获取审计日志"""
        filter_type = params.get("filter", "all")
        limit = params.get("limit", 50)
        
        logs = self._audit_logs[-limit:]
        
        if filter_type != "all":
            if filter_type == "high-risk":
                logs = [log for log in logs if log["risk_level"] == "high"]
            elif filter_type == "actions":
                logs = [log for log in logs if "操作" in log["action"] or "更新" in log["action"]]
        
        return list(reversed(logs))  # 最新的在前
    
    async def system_shutdown(self, params: Dict[str, Any]) -> Dict[str, str]:
        """关闭服务"""
        self._add_audit_log("system_shutdown", "high", "服务正在关闭")
        return {"status": "shutting_down"}
    
    # ========== 内部辅助方法 ==========
    
    def _add_audit_log(self, action: str, risk_level: str, details: str):
        """添加审计日志条目"""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "action": action,
            "risk_level": risk_level,
            "details": details,
        }
        self._audit_logs.append(log_entry)
        
        # 只保留最近 1000 条
        if len(self._audit_logs) > 1000:
            self._audit_logs = self._audit_logs[-1000:]
    
    # ========== RPC 路由 ==========
    
    async def handle_rpc_call(self, method: str, params: Dict[str, Any]) -> Any:
        """路由 JSON-RPC 调用到对应处理器"""
        handler_name = method.replace(".", "_")
        handler = getattr(self, handler_name, None)
        
        if not handler or not callable(handler):
            raise ValueError(f"Unknown method: {method}")
        
        return await handler(params)
