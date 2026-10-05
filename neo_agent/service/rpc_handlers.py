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
    
    # === 会话管理 ===
    
    async def session_send_message(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """发送消息到 Agent"""
        text = params.get("text", "")
        
        # TODO: 调用 Agent 运行时
        # 目前返回 Mock 数据
        agent = self.services.get("agent")
        if agent:
            # 真实 Agent
            result = await agent.chat(text)
            return result
        else:
            # Mock 响应
            return {
                "reply": f"收到消息：{text}（这是 Mock 响应，LangChain 尚未集成）",
                "emotion": {
                    "state": "平静",
                    "intensity": 0.5
                },
                "scene": self.services["scene"].get_current_scene()
            }
    
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
        return self.services["schedule"].get_today_itinerary()
    
    async def scene_get_current(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """获取当前场景"""
        return self.services["scene"].get_current_scene()
    
    async def scene_list_pool(self, params: Dict[str, Any]) -> list:
        """获取场景池"""
        return self.services["scene"].get_scene_pool()
    
    # === 记忆与知识 ===
    
    async def memory_search(self, params: Dict[str, Any]) -> list:
        """搜索记忆"""
        query = params.get("query", "")
        
        # TODO: 实现向量搜索
        # 目前返回 Mock
        return [
            {
                "content": f"关于{query}的记忆片段...",
                "relevance": 0.85,
                "timestamp": datetime.now().isoformat()
            }
        ]
    
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
    
    async def emotion_get_current(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """获取当前情绪"""
        return self.services["emotion"].get_current_emotion()
    
    # === 系统控制 ===
    
    async def system_get_status(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """获取系统状态"""
        return {
            "uptime": "运行中",
            "scene_worker": "正常",
            "daily_gen_status": "就绪",
            "character_loaded": self.services["role"].get_character() is not None
        }
    
    async def system_set_debug(self, params: Dict[str, Any]) -> bool:
        """设置调试模式"""
        enabled = params.get("enabled", False)
        
        # TODO: 实现 Debug 模式切换
        return True
    
    async def system_shutdown(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """关闭系统"""
        return {"status": "shutting_down"}

    async def relationship_list_all(self, params: Dict[str, Any]) -> list:
        """列出所有关系"""
        # TODO: 实现从 store 读取所有关系
        return []
    
    async def audit_get_logs(self, params: Dict[str, Any]) -> list:
        """获取审计日志"""
        filter_type = params.get("filter", "all")
        limit = params.get("limit", 100)
        
        # TODO: 实现审计日志查询
        return []
    
    async def memory_get_stats(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """获取记忆统计"""
        # TODO: 实现记忆统计
        return {
            "total": 0,
            "recent_count": 0
        }
    
    async def session_get_history(self, params: Dict[str, Any]) -> list:
        """获取对话历史"""
        limit = params.get("limit", 50)
        
        # TODO: 实现对话历史
        return []
