"""JSON-RPC 方法处理器 - 连接真实服务"""
from typing import Any, Dict
from datetime import datetime


class RPCHandlers:
    """RPC 方法处理器"""
    
    def __init__(self, services: dict):
        """
        Args:
            services: 服务字典，包含：
                - role: SingleRoleService
                - scene: SceneService
                - schedule: ScheduleService
                - relationship: RelationshipService
                - emotion: EmotionService
                - agent: AgentRuntime (可选，Mock时为None)
        """
        self.services = services
    
    async def handle_rpc_call(self, method: str, params: Dict[str, Any]) -> Any:
        """路由 JSON-RPC 方法调用"""
        # 方法名格式：category.action，例如 session.send_message
        method_name = method.replace(".", "_")
        handler = getattr(self, method_name, None)
        
        if handler is None:
            raise ValueError(f"Unknown method: {method}")
        
        return await handler(params)

    
    # === 会话管理 ===
    
    async def session_send_message(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """发送消息到 Agent"""
        text = params.get("text", "")
        
        # 保存用户消息
        self._append_message("user", text)
        
        # TODO: 调用 Agent 运行时
        agent = self.services.get("agent")
        if agent:
            # 真实 Agent
            result = await agent.chat(text)
            reply = result.get("reply", "")
        else:
            # Mock 响应
            reply = f"收到消息：{text}（这是 Mock 响应，LangChain 尚未集成）"
        
        # 保存 Agent 回复
        self._append_message("assistant", reply)
        
        return {
            "reply": reply,
            "emotion": self.services["emotion"].get_current_emotion(),
            "scene": self.services["scene"].get_current_scene()
        }
    
    def _append_message(self, role: str, content: str):
        """追加消息到历史"""
        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        self.services["role"].store.append_event("chat_history", message)
    
    async def session_get_context(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """获取会话上下文"""
        scene = self.services["scene"].get_current_scene()
        emotion = self.services["emotion"].get_current_emotion()
        relationship = self.services["relationship"].get_relationship("user")
        
        return {
            "current_scene": scene,
            "emotion": emotion,
            "relationship": relationship
        }
    
    async def session_get_history(self, params: Dict[str, Any]) -> list:
        """获取对话历史"""
        limit = params.get("limit", 50)
        
        # 从事件流读取对话历史
        events = self.services["role"].store.query_events(event_type="chat_history", limit=limit)
        
        return events
    
    # === 角色与状态 ===
    
    async def character_get_profile(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """获取角色资料"""
        character = self.services["role"].get_character()
        return character or {}
    
    async def character_update_profile(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """更新角色资料（仅 Debug 模式）"""
        fields = params.get("fields", {})
        
        # TODO: 检查 Debug 模式
        character = self.services["role"].update_character(fields)
        return character
    
    # === 日程与场景 ===
    
    async def schedule_get_today_itinerary(self, params: Dict[str, Any]) -> list:
        """获取今日行程"""
        schedules = self.services["schedule"].get_today_itinerary()
        
        # 标记当前活动
        current = self.services["schedule"].get_current_activity()
        current_id = current["id"] if current else None
        
        for schedule in schedules:
            schedule["is_current"] = (schedule["id"] == current_id)
        
        return schedules
    
    async def scene_get_current(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """获取当前场景"""
        return self.services["scene"].get_current_scene()
    
    async def scene_list_pool(self, params: Dict[str, Any]) -> list:
        """获取场景池"""
        pool = self.services["scene"].get_scene_pool()
        
        # 补充区域信息
        result = []
        for item in pool:
            location_id = item["location_id"]
            location = self.services["scene"].store.get_document("places", location_id)
            
            if location:
                areas = [area["name"] for area in location.get("areas", [])]
                result.append({
                    "location_id": location_id,
                    "name": item["name"],
                    "type": item.get("type", "unknown"),
                    "visited": item.get("visited", False),
                    "areas": areas,
                    "description": location.get("description", ""),
                    "created_at": item.get("created_at")
                })
        
        return result
    
    # === 记忆与知识 ===
    
    async def memory_search(self, params: Dict[str, Any]) -> list:
        """搜索记忆"""
        query = params.get("query", "")
        limit = params.get("limit", 20)
        
        # TODO: 实现真正的向量搜索
        # 目前从对话历史中简单搜索
        history = self.services["role"].store.query_events(event_type="chat_history", limit=200)
        
        results = []
        for msg in history:
            content = msg.get("content", "")
            if query.lower() in content.lower():
                results.append({
                    "text": content,
                    "relevance": 0.85,  # Mock 相关度
                    "timestamp": msg.get("timestamp", "")
                })
        
        # 限制返回数量
        return results[-limit:]
    
    async def memory_get_stats(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """获取记忆统计"""
        history = self.services["role"].store.query_events(event_type="chat_history", limit=10000)
        
        return {
            "total": len(history),
            "recent_count": min(50, len(history))
        }
    
    async def knowledge_query(self, params: Dict[str, Any]) -> list:
        """查询知识"""
        topic = params.get("topic", "")
        
        # TODO: 实现知识查询
        return []
    
    # === 关系与情绪 ===
    
    async def relationship_get_status(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """获取关系状态"""
        entity = params.get("entity", "user")
        return self.services["relationship"].get_relationship(entity)
    
    async def relationship_list_all(self, params: Dict[str, Any]) -> list:
        """列出所有关系"""
        relationships = self.services["relationship"].store.list_documents("relationships")
        
        result = []
        for rel in relationships:
            result.append({
                "entity": rel.get("id", "unknown"),
                "score": rel.get("score", 50),
                "level": rel.get("level", "普通"),
                "updated": rel.get("last_update", ""),
                "history": rel.get("history", [])
            })
        
        return result
    
    async def emotion_get_current(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """获取当前情绪"""
        return self.services["emotion"].get_current_emotion()
    
    # === 审计日志 ===
    
    async def audit_get_logs(self, params: Dict[str, Any]) -> list:
        """获取审计日志"""
        filter_type = params.get("filter", "all")
        limit = params.get("limit", 100)
        
        # 从多个事件流收集审计数据
        store = self.services["role"].store
        
        logs = []
        
        # 场景切换
        scene_audits = store.list_documents("scene_audits")
        for audit in scene_audits:
            logs.append({
                "timestamp": audit.get("updated_at", ""),
                "action": "场景切换",
                "risk_level": "low",
                "category": "scene",
                "result": f"切换到 {audit.get('location_id', 'unknown')}"
            })
        
        # 关系更新
        relationships = store.list_documents("relationships")
        for rel in relationships:
            for event in rel.get("history", []):
                logs.append({
                    "timestamp": event.get("timestamp", ""),
                    "action": "关系更新",
                    "risk_level": "low",
                    "category": "relationship",
                    "result": f"{rel['id']} 分数 {event.get('old_score')} → {event.get('new_score')}"
                })
        
        # 情绪变化事件
        emotion_events = store.query_events(event_type="emotion_change", limit=100)
        for event in emotion_events:
            logs.append({
                "timestamp": event.get("timestamp", ""),
                "action": "情绪变化",
                "risk_level": "low",
                "category": "emotion",
                "result": f"{event.get('state')} (强度: {event.get('intensity')})"
            })
        
        # 按时间排序
        logs.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        
        # 过滤
        if filter_type != "all":
            if filter_type == "high_risk":
                logs = [log for log in logs if log["risk_level"] == "high"]
            elif filter_type == "actions":
                logs = [log for log in logs if log["category"] in ["scene", "operation"]]
            elif filter_type == "decisions":
                logs = [log for log in logs if log["category"] in ["cognition", "decision"]]
        
        return logs[:limit]
    
    # === 系统控制 ===
    
    async def system_get_status(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """获取系统状态"""
        return {
            "uptime": "运行中",
            "scene_worker": "正常",
            "daily_gen_status": "就绪",
            "character_loaded": self.services["role"].get_character() is not None,
            "current_scene": self.services["scene"]._current_location or "未知"
        }
    
    async def system_set_debug(self, params: Dict[str, Any]) -> bool:
        """设置调试模式"""
        enabled = params.get("enabled", False)
        
        # TODO: 实现 Debug 模式切换
        # 暂时保存到全局配置
        self.services["role"].store.save_document("config", "debug_mode", {
            "enabled": enabled,
            "updated_at": datetime.now().isoformat()
        })
        
        return True
    
    async def system_shutdown(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """关闭系统"""
        return {"status": "shutting_down"}

    # === 调试方法 ===
    
    async def debug_generate_itinerary(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """调试：手动生成今日行程"""
        daily_service = self.services.get("daily_itinerary")
        
        if daily_service is None:
            return {"success": False, "error": "DailyItineraryService not initialized"}
        
        try:
            from datetime import date
            plan = daily_service.generate_today_itinerary()
            count = len(plan.get("schedule_items", []))
            
            return {
                "success": True,
                "date": plan.get("date"),
                "count": count,
                "items": plan.get("schedule_items", [])
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "type": type(e).__name__
            }
