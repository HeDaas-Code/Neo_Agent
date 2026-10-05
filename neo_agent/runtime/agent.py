"""Agent 运行时：LangChain 编排与认知门控"""
import os
from typing import Optional, Dict, Any

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

from neo_agent.storage import DiskStore
from neo_agent.config import get_config
from .control import SingleRoleService
from .cognition import CognitionService
from .mock_llm import MockChatModel


class AgentRuntime:
    """Agent 主运行时：协调认知、执行、表达"""
    
    def __init__(self, disk_store: DiskStore, model: Optional[Any] = None):
        self.store = disk_store
        self.model = model or self._build_model()
        
        # 运行时服务
        self.role_service = SingleRoleService(disk_store)
        self.cognition = CognitionService(self.model)
    
    def _build_model(self):
        """构建 LLM 模型"""
        config = get_config()
        llm_config = config.get_llm_config()
        
        api_key = llm_config.get("api_key") or os.getenv("OPENAI_API_KEY") or os.getenv("SILICONFLOW_API_KEY")
        
        # 如果没有 API key，使用 Mock 模型
        if not api_key:
            print("⚠ 未配置 API Key，使用 Mock LLM（仅用于测试）", flush=True)
            return MockChatModel()
        
        base_url = llm_config.get("base_url") or os.getenv("OPENAI_BASE_URL")
        model_name = llm_config.get("model", "gpt-4o-mini")
        temperature = llm_config.get("temperature", 0.7)
        
        kwargs = {
            "model": model_name,
            "temperature": temperature,
            "api_key": api_key,
        }
        if base_url:
            kwargs["base_url"] = base_url
        
        return ChatOpenAI(**kwargs)
    
    async def chat(self, user_message: str, session_id: Optional[str] = None) -> Dict[str, Any]:
        """处理用户消息：认知 → 执行 → 表达"""
        
        # 获取当前角色
        character = self.role_service.active()
        if not character:
            return {
                "reply": "系统错误：未找到活动角色",
                "emotion": "confused",
                "error": "no_active_character"
            }
        
        # 阶段一：认知门控
        personality = f"{character.get('name', 'Unknown')}: {', '.join(character.get('personality', []))}"
        decision = self.cognition.assess(
            message=user_message,
            personality=personality,
            direct_chat=True
        )
        
        if decision.reply_strategy == "silence":
            return {
                "reply": None,
                "emotion": decision.affective_state,
                "decision": "silent"
            }
        
        # 阶段二：语言生成（简化版，无工具权限）
        reply = await self._generate_reply(character, user_message, decision)
        
        return {
            "reply": reply,
            "emotion": decision.affective_state,
            "confidence": decision.confidence
        }
    
    async def _generate_reply(self, character: Dict[str, Any], user_message: str, decision: Any) -> str:
        """生成回复（无工具权限）"""
        from langchain_core.messages import HumanMessage, SystemMessage
        
        name = character.get("name", "Unknown")
        personality = ", ".join(character.get("personality", []))
        background = character.get("background", "")
        
        system_prompt = (
            f"你是 {name}，一个虚拟群友。\n"
            f"性格特点：{personality}\n"
            f"背景：{background}\n"
            "请用符合角色设定的自然语气回复用户。保持简短、真实、符合人设。"
        )
        
        try:
            response = self.model.invoke([
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_message)
            ])
            
            # 处理响应
            if hasattr(response, 'content'):
                return response.content
            else:
                return str(response)
        except Exception as e:
            return f"[生成回复失败: {str(e)}]"
    
    def get_character(self) -> Optional[Dict[str, Any]]:
        """获取当前角色"""
        return self.role_service.active()
