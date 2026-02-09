"""
LangChain LLM封装模块
使用LangChain的ChatOpenAI兼容接口封装SiliconFlow API
支持多层模型架构
"""

import os
import time
from typing import List, Dict, Any, Optional
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough

from src.core.model_config import ModelType, get_model_config
from src.tools.debug_logger import get_debug_logger

# 获取debug日志记录器
debug_logger = get_debug_logger()


class LangChainLLM:
    """
    基于LangChain的LLM封装类
    使用ChatOpenAI兼容接口访问SiliconFlow API
    支持多层模型架构
    """
    
    def __init__(self, model_type: ModelType = ModelType.MAIN):
        """
        初始化LangChain LLM客户端
        
        Args:
            model_type: 模型类型（主模型、工具模型或多模态模型）
        """
        self.model_type = model_type
        self.config = get_model_config()
        
        # 获取API配置
        api_config = self.config.get_api_config()
        self.api_key = api_config['api_key']
        self.api_url = api_config['api_url']
        
        # 获取模型配置
        model_config = self.config.get_model_config(model_type)
        self.model_name = model_config['name']
        self.temperature = model_config['temperature']
        self.max_tokens = model_config['max_tokens']
        
        # 创建ChatOpenAI实例（兼容SiliconFlow API）
        # SiliconFlow使用OpenAI兼容接口
        self.llm = ChatOpenAI(
            model=self.model_name,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            openai_api_key=self.api_key,
            openai_api_base=self.api_url.replace('/chat/completions', ''),  # 移除末尾的路径
            timeout=30
        )
        
        debug_logger.log_module('LangChainLLM', f'初始化{model_type.value}模型', {
            'model_name': self.model_name,
            'temperature': self.temperature,
            'max_tokens': self.max_tokens
        })
        
        # 验证配置
        if not self.config.is_valid():
            print("警告: 未设置有效的API密钥，请在.env文件中配置SILICONFLOW_API_KEY")
    
    def _convert_messages_to_langchain(self, messages: List[Dict[str, str]]) -> List:
        """
        将标准消息格式转换为LangChain消息对象
        
        Args:
            messages: 消息列表，格式为 [{'role': 'user/assistant/system', 'content': '...'}]
            
        Returns:
            LangChain消息对象列表
        """
        langchain_messages = []
        for msg in messages:
            role = msg.get('role', 'user')
            content = msg.get('content', '')
            
            if role == 'system':
                langchain_messages.append(SystemMessage(content=content))
            elif role == 'assistant':
                langchain_messages.append(AIMessage(content=content))
            else:  # user
                langchain_messages.append(HumanMessage(content=content))
        
        return langchain_messages
    
    def chat(self, messages: List[Dict[str, str]]) -> str:
        """
        发送聊天请求
        
        Args:
            messages: 消息列表，格式为 [{'role': 'user/assistant/system', 'content': '...'}]
            
        Returns:
            AI的回复内容
        """
        try:
            # Debug: 记录请求前的信息
            debug_logger.log_module('LangChainLLM', f'准备发送{self.model_type.value}模型请求', {
                'message_count': len(messages),
                'model_name': self.model_name
            })
            
            # Debug: 记录所有消息
            for i, msg in enumerate(messages):
                debug_logger.log_prompt(
                    'LangChainLLM',
                    msg['role'],
                    msg['content'],
                    {'message_index': i, 'total_messages': len(messages), 'model_type': self.model_type.value}
                )
            
            # 转换消息格式
            langchain_messages = self._convert_messages_to_langchain(messages)
            
            # 调用LLM
            start_time = time.time()
            response = self.llm.invoke(langchain_messages)
            elapsed_time = time.time() - start_time
            
            # 提取回复内容
            reply_content = response.content
            
            # Debug: 记录响应
            debug_logger.log_response('LangChainLLM', {
                'content': reply_content,
                'model': self.model_name,
                'model_type': self.model_type.value
            }, 200, elapsed_time)
            
            debug_logger.log_info('LangChainLLM', '成功获取回复', {
                'reply_length': len(reply_content),
                'elapsed_time': elapsed_time,
                'model_type': self.model_type.value
            })
            
            return reply_content
            
        except Exception as e:
            debug_logger.log_error('LangChainLLM', f'LLM调用错误: {str(e)}', e)
            print(f"LLM调用错误: {e}")
            return f"抱歉，处理请求时出现错误: {str(e)}"
    
    def chat_with_template(
        self,
        template: str,
        variables: Dict[str, Any],
        message_history: Optional[List[Dict[str, str]]] = None
    ) -> str:
        """
        使用模板和变量进行聊天
        
        Args:
            template: 提示词模板
            variables: 模板变量字典
            message_history: 可选的消息历史
            
        Returns:
            AI的回复内容
        """
        try:
            # 创建提示词模板
            if message_history:
                # 如果有消息历史，使用MessagesPlaceholder
                prompt = ChatPromptTemplate.from_messages([
                    ("system", template),
                    MessagesPlaceholder(variable_name="history"),
                    ("human", "{input}")
                ])
                
                # 转换消息历史
                history_messages = self._convert_messages_to_langchain(message_history)
                variables['history'] = history_messages
            else:
                # 没有消息历史，使用简单模板
                prompt = ChatPromptTemplate.from_messages([
                    ("system", template),
                    ("human", "{input}")
                ])
            
            # 创建链
            chain = prompt | self.llm | StrOutputParser()
            
            # 执行链
            start_time = time.time()
            response = chain.invoke(variables)
            elapsed_time = time.time() - start_time
            
            debug_logger.log_info('LangChainLLM', '模板聊天完成', {
                'elapsed_time': elapsed_time,
                'model_type': self.model_type.value,
                'response_length': len(response)
            })
            
            return response
            
        except Exception as e:
            debug_logger.log_error('LangChainLLM', f'模板聊天错误: {str(e)}', e)
            return f"抱歉，处理请求时出现错误: {str(e)}"
    
    def get_model_info(self) -> Dict[str, Any]:
        """
        获取模型信息
        
        Returns:
            包含模型信息的字典
        """
        return {
            'model_type': self.model_type.value,
            'model_name': self.model_name,
            'temperature': self.temperature,
            'max_tokens': self.max_tokens
        }


class ModelRouter:
    """
    模型路由器
    根据任务类型自动选择合适的模型
    """
    
    def __init__(self):
        """初始化模型路由器"""
        self.main_llm = LangChainLLM(ModelType.MAIN)
        self.tool_llm = LangChainLLM(ModelType.TOOL)
        self.vision_llm = LangChainLLM(ModelType.VISION)
        
        debug_logger.log_module('ModelRouter', '模型路由器初始化完成', {
            'main_model': self.main_llm.model_name,
            'tool_model': self.tool_llm.model_name,
            'vision_model': self.vision_llm.model_name
        })
    
    def route(self, task_type: str = 'main') -> LangChainLLM:
        """
        根据任务类型路由到合适的模型
        
        Args:
            task_type: 任务类型 ('main', 'tool', 'vision')
            
        Returns:
            对应的LLM实例
        """
        if task_type == 'tool':
            return self.tool_llm
        elif task_type == 'vision':
            return self.vision_llm
        else:
            return self.main_llm
    
    def get_model_by_type(self, model_type: ModelType) -> LangChainLLM:
        """
        根据模型类型获取LLM实例
        
        Args:
            model_type: 模型类型枚举
            
        Returns:
            对应的LLM实例
        """
        if model_type == ModelType.TOOL:
            return self.tool_llm
        elif model_type == ModelType.VISION:
            return self.vision_llm
        else:
            return self.main_llm
