"""Mock LLM for testing without API keys"""
from typing import Any, List, Optional
from langchain_core.messages import BaseMessage, AIMessage
from langchain_core.language_models import BaseChatModel
from langchain_core.outputs import ChatGeneration, ChatResult


class MockChatModel(BaseChatModel):
    """Mock LLM that returns predefined responses"""
    
    def _generate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> ChatResult:
        """Generate a mock response"""
        # Simple echo response
        last_message = messages[-1].content if messages else "Hello"
        response_text = f"[Mock] 收到消息: {last_message[:50]}..."
        
        message = AIMessage(content=response_text)
        generation = ChatGeneration(message=message)
        return ChatResult(generations=[generation])
    
    @property
    def _llm_type(self) -> str:
        return "mock"
    
    def _stream(self, *args, **kwargs):
        raise NotImplementedError("Streaming not supported in mock")
    
    async def _agenerate(self, *args, **kwargs):
        return self._generate(*args, **kwargs)
