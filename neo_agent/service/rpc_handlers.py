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
        scene = self.scene_scheduler.get_current_scene() or {}
        
        result = {
            "reply": reply,
            "emotion": emotion,
            "scene": scene,
        }
        
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
        current_scene = self.scene_scheduler.get_current_scene() or {}
        emotion = self.emotion_service.get_current_emotion() or {}
        character = self.role_service.active()
        
        return {
            "current_scene": current_scene,
            "emotion": emotion,
            "character": character,
        }
    
    # ========== 角色与状态 ==========
    
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
        
        return {"status": "ok"}
    
    # ========== 日程与场景 ==========
    
    async def schedule_get_today_itinerary(self, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """获取今日行程"""
        try:
            itinerary = self.itinerary_service.get_today_itinerary()
            return itinerary if itinerary else []
        except:
            return []
    
    async def scene_get_current(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """获取当前场景"""
        try:
            scene = self.scene_scheduler.get_current_scene()
            return scene if scene else {}
        except:
            return {}
    
    async def scene_list_pool(self, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """获取场景池"""
        try:
            scenes = self.scene_service.list_all_scenes()
            return scenes if scenes else []
        except:
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
            return results if results else []
        except:
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
            return filtered[:10]
        except:
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
        except:
            return {}
    
    async def relationship_list_all(self, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """列出所有关系"""
        try:
            relationships = self.store.list_documents("relationships")
            return relationships if relationships else []
        except:
            return []
    
    async def emotion_get_current(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """获取当前情绪"""
        try:
            emotion = self.emotion_service.get_current_emotion()
            return emotion if emotion else {}
        except:
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
        
        await self.broadcaster.emit(ServiceEvent(
            type=EventType.SYSTEM_STATUS_CHANGED,
            timestamp=datetime.now().isoformat(),
            data={"debug_mode": enabled}
        ))
        
        return {"status": "ok"}
    
    async def system_shutdown(self, params: Dict[str, Any]) -> Dict[str, str]:
        """关闭服务"""
        return {"status": "shutting_down"}
    
    # ========== RPC 路由 ==========
    
    async def handle_rpc_call(self, method: str, params: Dict[str, Any]) -> Any:
        """路由 JSON-RPC 调用到对应处理器"""
        handler_name = method.replace(".", "_")
        handler = getattr(self, handler_name, None)
        
        if not handler or not callable(handler):
            raise ValueError(f"Unknown method: {method}")
        
        return await handler(params)
