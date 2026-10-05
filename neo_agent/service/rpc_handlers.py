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
        conversation_id = params.get("conversation_id", "default")
        
        try:
            # 从运行时对话历史读取
            import hashlib
            storage_id = conversation_id if len(conversation_id) <= 22 else hashlib.sha256(conversation_id.encode()).hexdigest()[:20]
            history_path = f"/runtime/conversations/{storage_id}.json"
            transcript = self.store.read_json(history_path, default=[])
            
            # 转换为消息格式
            messages = []
            for turn in transcript[-limit:]:
                if isinstance(turn, dict):
                    if turn.get("user"):
                        messages.append({
                            "role": "user",
                            "content": turn["user"],
                            "timestamp": turn.get("timestamp", "")
                        })
                    if turn.get("assistant"):
                        messages.append({
                            "role": "assistant", 
                            "content": turn["assistant"],
                            "timestamp": turn.get("timestamp", "")
                        })
            
            return messages
        except Exception as e:
            self._add_audit_log("history_error", "low", f"获取历史失败: {str(e)}")
            return []
    
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
    
    async def schedule_get_today_itinerary(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """获取今日行程"""
        try:
            itinerary = self.itinerary_service.get_today_itinerary()
            
            # 转换为视图期望的格式
            items = []
            for schedule in (itinerary or []):
                start_time = schedule.get("start_at", "")
                end_time = schedule.get("end_at", "")
                
                # 格式化时间显示
                time_str = ""
                if start_time:
                    try:
                        from datetime import datetime
                        start = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
                        time_str = start.strftime("%H:%M")
                        if end_time:
                            end = datetime.fromisoformat(end_time.replace("Z", "+00:00"))
                            time_str += f" - {end.strftime('%H:%M')}"
                    except Exception:
                        time_str = start_time[:5] if len(start_time) >= 5 else start_time
                
                items.append({
                    "time": time_str,
                    "activity": schedule.get("title", ""),
                    "location": schedule.get("location", "未指定"),
                    "area": schedule.get("area", ""),
                    "description": schedule.get("description", ""),
                    "schedule_type": schedule.get("type", "agent"),
                    "status": schedule.get("status", "待开始"),
                })
            
            return {"items": items}
        except Exception as e:
            self._add_audit_log("schedule_error", "medium", f"获取日程失败: {str(e)}")
            return {"items": []}
    
    async def scene_get_current(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """获取当前场景"""
        try:
            scene = self.scene_service.current()
            return scene if scene else {}
        except Exception as e:
            self._add_audit_log("scene_error", "low", f"获取场景失败: {str(e)}")
            return {}
    
    async def scene_list_pool(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """获取场景池"""
        try:
            places = self.scene_service.places(visited_only=False)
            current = self.scene_service.current() or {}
            
            scenes = []
            for place in (places or []):
                place_id = place.get("place_id")
                areas = self.scene_service.areas(place_id) or []
                objects_list = []
                
                # 收集该地点的物体
                for area in areas:
                    area_objects = self.scene_service.objects(area.get("area_id")) or []
                    objects_list.extend(area_objects)
                
                scenes.append({
                    "location_id": place_id,
                    "name": place.get("name", "未命名"),
                    "location": place,
                    "areas": areas,
                    "objects": objects_list,
                    "layout_frozen": place.get("layout_frozen", False),
                })
            
            return {
                "scenes": scenes,
                "current_scene": {
                    "location": current.get("place", {}).get("name", ""),
                    "area": current.get("area", {}).get("name", ""),
                }
            }
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
    
    async def audit_list_recent(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """列出最近的审计日志（别名方法）"""
        logs = await self.system_get_audit_logs(params)
        
        # 转换为视图期望的格式
        audits = []
        for log in logs:
            audits.append({
                "timestamp": log.get("timestamp", ""),
                "operation": log.get("action", ""),
                "risk_level": log.get("risk_level", "low"),
                "details": log.get("details", ""),
                "result": "success",  # 可以根据 details 扩展
            })
        
        return {"audits": audits}
    
    async def relationship_get_status(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """获取指定实体的关系状态"""
        entity = params.get("entity", "user")
        try:
            rel_data = self.agent.store.get_document("relationships", entity)
            return {
                "entity": entity,
                "score": rel_data.get("score", 0),
                "stage": rel_data.get("stage", "stranger"),
                "history": rel_data.get("history", [])
            }
        except Exception:
            return {
                "entity": entity,
                "score": 0,
                "stage": "stranger",
                "history": []
            }
    
    async def relationship_get_history(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """获取关系变化历史"""
        entity = params.get("entity", "user")
        limit = params.get("limit", 20)
        
        try:
            history = self.agent.relationship_service.get_relationship_history(entity, limit)
            return {"history": history or []}
        except Exception as exc:
            self._add_audit_log(
                "relationship_get_history_failed",
                "medium",
                f"获取关系历史失败: {type(exc).__name__}"
            )
            return {"history": []}
    
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

    # ========== 每日行程与场景生成 ==========
    
    async def schedule_generate_daily_itinerary(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """生成今日行程"""
        try:
            from neo_agent.runtime.daily_itinerary import DailyItineraryService
            itinerary_service = DailyItineraryService(self.store, self.model)
            result = itinerary_service.generate_today_itinerary()
            self._add_audit_log("schedule_generate", "low", f"生成今日行程: {result.get('status')}")
            return result
        except Exception as e:
            self._add_audit_log("schedule_error", "low", f"生成今日行程失败: {str(e)}")
            return {"status": "error", "reason": str(e)}
    
    async def scene_generate_for_activity(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """为活动生成场景"""
        activity = params.get("activity", "")
        purpose = params.get("purpose", "")
        location_hint = params.get("location_hint", "")
        
        if not activity:
            return {"status": "error", "reason": "缺少 activity 参数"}
        
        try:
            from neo_agent.runtime.scene_generation import SceneGenerationService
            scene_gen = SceneGenerationService(self.store, self.model)
            result = scene_gen.generate_scene_for_activity(activity, purpose, location_hint)
            self._add_audit_log("scene_generate", "medium", 
                              f"生成场景: {result.get('place', {}).get('name', '未知')}")
            return result
        except Exception as e:
            self._add_audit_log("scene_error", "low", f"生成场景失败: {str(e)}")
            return {"status": "error", "reason": str(e)}
    
    async def scene_freeze_layout(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """固化场景布局"""
        place_id = params.get("place_id", "")
        
        if not place_id:
            return {"status": "error", "reason": "缺少 place_id 参数"}
        
        try:
            from neo_agent.runtime.scene_generation import SceneGenerationService
            scene_gen = SceneGenerationService(self.store, self.model)
            success = scene_gen.freeze_scene_layout(place_id)
            return {"status": "success" if success else "error"}
        except Exception as e:
            return {"status": "error", "reason": str(e)}

    async def relationship_list_all(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """列出所有关系"""
        try:
            # 目前只支持单个用户关系
            status = await self.relationship_get_status({"entity": "user"})
            relationships = [status] if status else []
            
            return {"relationships": relationships}
        except Exception as e:
            return {"relationships": []}
