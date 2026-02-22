"""
LLM辅助工具模块
为各种工具和模块提供便捷的LLM调用接口
"""

from typing import List, Dict, Any, Optional
from src.core.langchain_llm import LangChainLLM, ModelType


class LLMHelper:
    """
    LLM辅助类
    为工具级任务提供简化的LLM调用接口
    """
    
    @staticmethod
    def call_tool_model(
        system_prompt: str,
        user_message: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> str:
        """
        调用工具模型（小模型）处理轻量级任务
        
        Args:
            system_prompt: 系统提示词
            user_message: 用户消息
            temperature: 温度参数（可选，默认使用配置值）
            max_tokens: 最大token数（可选，默认使用配置值）
            
        Returns:
            模型回复
        """
        llm = LangChainLLM(ModelType.TOOL)
        
        # 如果需要自定义参数，更新配置
        if temperature is not None:
            llm.temperature = temperature
            llm.llm.temperature = temperature
        if max_tokens is not None:
            llm.max_tokens = max_tokens
            llm.llm.max_tokens = max_tokens
        
        messages = [
            {'role': 'system', 'content': system_prompt},
            {'role': 'user', 'content': user_message}
        ]
        
        return llm.chat(messages)
    
    @staticmethod
    def call_main_model(
        system_prompt: str,
        user_message: str,
        message_history: Optional[List[Dict[str, str]]] = None
    ) -> str:
        """
        调用主模型处理主要任务
        
        Args:
            system_prompt: 系统提示词
            user_message: 用户消息
            message_history: 消息历史（可选）
            
        Returns:
            模型回复
        """
        llm = LangChainLLM(ModelType.MAIN)
        
        messages = [{'role': 'system', 'content': system_prompt}]
        
        if message_history:
            messages.extend(message_history)
        
        messages.append({'role': 'user', 'content': user_message})
        
        return llm.chat(messages)
    
    @staticmethod
    def call_vision_model(
        system_prompt: str,
        user_message: str
    ) -> str:
        """
        调用多模态模型处理视觉任务
        
        Args:
            system_prompt: 系统提示词
            user_message: 用户消息
            
        Returns:
            模型回复
        """
        llm = LangChainLLM(ModelType.VISION)
        
        messages = [
            {'role': 'system', 'content': system_prompt},
            {'role': 'user', 'content': user_message}
        ]
        
        return llm.chat(messages)
    
    @staticmethod
    def create_simple_messages(
        system_prompt: str,
        user_message: str,
        history: Optional[List[Dict[str, str]]] = None
    ) -> List[Dict[str, str]]:
        """
        创建简单的消息列表
        
        Args:
            system_prompt: 系统提示词
            user_message: 用户消息
            history: 历史消息（可选）
            
        Returns:
            消息列表
        """
        messages = [{'role': 'system', 'content': system_prompt}]
        
        if history:
            messages.extend(history)
        
        messages.append({'role': 'user', 'content': user_message})
        
        return messages
