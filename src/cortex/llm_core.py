"""
Cortex LLM Core - v4.0 大脑皮层 LLM 核心。

统一的 LLM 推理入口，封装 LangChain/OpenAI 细节，支持：
- 多层模型（main/tool/vision）
- 同步/异步聊天
- 模板渲染
- debug 日志

本模块从 v3.1.0 的 src.core.langchain_llm 迁移并抽象而来。
"""

from __future__ import annotations

import os
import time
from typing import Any, AsyncIterator, Dict, List, Optional

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_openai import ChatOpenAI

from src.cortex.config.model_config import ModelType, get_model_config
from src.nervous_system.base_module import BaseModule
from src.nervous_system.router.packet import Packet
from src.tools.debug_logger import get_debug_logger

logger = get_debug_logger()


class LLMCore(BaseModule):
    """
    大脑皮层 LLM 核心模块。

    对外通过 CentralRouter 接收 llm_chat / llm_stream / llm_template 请求。
    内部管理 LangChainLLM 实例池。
    """

    module_id = "cortex.llm_core"
    module_type = "cortex"

    def __init__(self, router):
        super().__init__(router)
        self._model_router: Optional[ModelRouter] = None

    def _get_model_router(self) -> ModelRouter:
        """
        懒加载模型路由器，避免启动期强制初始化 LLM。
        """
        if self._model_router is None:
            self._model_router = ModelRouter()
        return self._model_router

    async def handle(self, packet: Packet) -> Packet:
        """
        处理 LLM 相关请求。
        """
        channel = packet.channel
        try:
            model_router = self._get_model_router()
        except Exception as exc:
            return Packet.error(packet, f"LLM 初始化失败: {exc}", code="LLM_INIT_ERROR")

        if channel == "llm_chat":
            messages = packet.payload.get("messages", [])
            task_type = packet.payload.get("task_type", "main")
            reply = model_router.route(task_type).chat(messages)
            return packet.response({"role": "assistant", "content": reply})

        if channel == "llm_stream":
            # 同步场景下返回完整回复；真实流式请使用 handle_stream
            messages = packet.payload.get("messages", [])
            task_type = packet.payload.get("task_type", "main")
            reply = model_router.route(task_type).chat(messages)
            return packet.response({"role": "assistant", "content": reply, "stream": False})

        if channel == "llm_template":
            template = packet.payload.get("template", "")
            variables = packet.payload.get("variables", {})
            history = packet.payload.get("history")
            task_type = packet.payload.get("task_type", "main")
            reply = model_router.route(task_type).chat_with_template(template, variables, history)
            return packet.response({"role": "assistant", "content": reply})

        if channel == "llm_info":
            task_type = packet.payload.get("task_type", "main")
            info = model_router.route(task_type).get_model_info()
            return packet.response(info)

        return packet.response({"status": "unknown_channel", "channel": channel})

    async def handle_stream(self, packet: Packet) -> AsyncIterator[Packet]:
        """
        处理 LLM 流式请求。

        支持 channel:
            - llm_stream: 逐 token 返回 content chunk，最后 yield done
        """
        channel = packet.channel
        try:
            model_router = self._get_model_router()
        except Exception as exc:
            yield packet.stream_error(f"LLM 初始化失败: {exc}", code="LLM_INIT_ERROR")
            return

        if channel == "llm_stream":
            messages = packet.payload.get("messages", [])
            task_type = packet.payload.get("task_type", "main")
            try:
                async for chunk in model_router.route(task_type).chat_stream(messages):
                    yield packet.stream_chunk({"role": "assistant", "content": chunk})
            except Exception as exc:
                logger.log_error('LLMCore', f'流式处理异常: {exc}', exc)
                yield packet.stream_error(str(exc), code="LLM_STREAM_ERROR")
            yield packet.stream_done()
            return

        # 其他 channel 默认委托给 handle 并 yield done
        response = await self.handle(packet)
        if response.is_error():
            yield response
            return
        yield packet.stream_chunk(response.payload)
        yield packet.stream_done()


class LangChainLLM:
    """
    基于 LangChain 的 LLM 封装。

    保持与 v3.1.0 基本一致的接口，方便平滑迁移。
    """

    def __init__(self, model_type: ModelType = ModelType.MAIN):
        self.model_type = model_type
        self.config = get_model_config()

        api_config = self.config.get_api_config()
        self.api_key = api_config['api_key'] or 'placeholder-key'
        self.api_url = api_config['api_url']

        model_config = self.config.get_model_config(model_type)
        self.model_name = model_config['name']
        self.temperature = model_config['temperature']
        self.max_tokens = model_config['max_tokens']

        timeout_defaults = {
            ModelType.MAIN: 60,
            ModelType.TOOL: 45,
            ModelType.VISION: 90
        }
        default_timeout = timeout_defaults.get(model_type, 45)
        timeout_env_keys = {
            ModelType.MAIN: 'MAIN_MODEL_TIMEOUT',
            ModelType.TOOL: 'TOOL_MODEL_TIMEOUT',
            ModelType.VISION: 'VISION_MODEL_TIMEOUT'
        }
        timeout_env_key = timeout_env_keys.get(model_type, 'LLM_TIMEOUT')
        self.timeout = int(os.getenv(timeout_env_key, str(default_timeout)))

        base_url = self.api_url
        if '/chat/completions' in base_url:
            base_url = base_url.replace('/chat/completions', '')

        self.llm = ChatOpenAI(
            model=self.model_name,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            api_key=self.api_key,
            base_url=base_url,
            timeout=self.timeout
        )

        logger.log_module('LangChainLLM', f'初始化{model_type.value}模型', {
            'model_name': self.model_name,
            'temperature': self.temperature,
            'max_tokens': self.max_tokens,
            'timeout': self.timeout
        })

        if not self.config.is_valid():
            print("警告: 未设置有效的API密钥，请在.env文件中配置LLM_API_KEY")

    def _convert_messages_to_langchain(self, messages: List[Dict[str, str]]) -> List:
        """将标准消息格式转换为 LangChain 消息对象。"""
        langchain_messages = []
        for msg in messages:
            role = msg.get('role', 'user')
            content = msg.get('content', '')
            if role == 'system':
                langchain_messages.append(SystemMessage(content=content))
            elif role == 'assistant':
                langchain_messages.append(AIMessage(content=content))
            else:
                langchain_messages.append(HumanMessage(content=content))
        return langchain_messages

    def chat(self, messages: List[Dict[str, str]]) -> str:
        """发送聊天请求。"""
        try:
            logger.log_module('LangChainLLM', f'准备发送{self.model_type.value}模型请求', {
                'message_count': len(messages),
                'model_name': self.model_name
            })

            for i, msg in enumerate(messages):
                logger.log_prompt(
                    'LangChainLLM',
                    msg['role'],
                    msg['content'],
                    {'message_index': i, 'total_messages': len(messages), 'model_type': self.model_type.value}
                )

            langchain_messages = self._convert_messages_to_langchain(messages)
            start_time = time.time()
            response = self.llm.invoke(langchain_messages)
            elapsed_time = time.time() - start_time

            reply_content = response.content
            logger.log_response('LangChainLLM', {
                'content': reply_content,
                'model': self.model_name,
                'model_type': self.model_type.value
            }, 200, elapsed_time)

            return reply_content
        except Exception as e:
            logger.log_error('LangChainLLM', f'LLM调用错误: {str(e)}', e)
            return f"抱歉，处理请求时出现错误: {str(e)}"

    async def chat_stream(self, messages: List[Dict[str, str]]) -> AsyncIterator[str]:
        """流式发送聊天请求，逐 token 返回字符串 chunk。"""
        try:
            logger.log_module('LangChainLLM', f'准备流式发送{self.model_type.value}模型请求', {
                'message_count': len(messages),
                'model_name': self.model_name
            })

            for i, msg in enumerate(messages):
                logger.log_prompt(
                    'LangChainLLM',
                    msg['role'],
                    msg['content'],
                    {'message_index': i, 'total_messages': len(messages), 'model_type': self.model_type.value}
                )

            langchain_messages = self._convert_messages_to_langchain(messages)
            start_time = time.time()
            async for chunk in self.llm.astream(langchain_messages):
                content = getattr(chunk, 'content', None)
                if content:
                    yield content
            elapsed_time = time.time() - start_time
            logger.log_info('LangChainLLM', '流式响应完成', {
                'elapsed_time': elapsed_time,
                'model_type': self.model_type.value,
            })
        except Exception as e:
            logger.log_error('LangChainLLM', f'流式LLM调用错误: {str(e)}', e)
            yield f"抱歉，处理请求时出现错误: {str(e)}"

    def chat_with_template(
        self,
        template: str,
        variables: Dict[str, Any],
        message_history: Optional[List[Dict[str, str]]] = None
    ) -> str:
        """使用模板和变量进行聊天。"""
        try:
            if message_history:
                prompt = ChatPromptTemplate.from_messages([
                    ("system", template),
                    MessagesPlaceholder(variable_name="history"),
                    ("human", "{input}")
                ])
                history_messages = self._convert_messages_to_langchain(message_history)
                variables['history'] = history_messages
            else:
                prompt = ChatPromptTemplate.from_messages([
                    ("system", template),
                    ("human", "{input}")
                ])

            chain = prompt | self.llm | StrOutputParser()
            start_time = time.time()
            response = chain.invoke(variables)
            elapsed_time = time.time() - start_time

            logger.log_info('LangChainLLM', '模板聊天完成', {
                'elapsed_time': elapsed_time,
                'model_type': self.model_type.value,
                'response_length': len(response)
            })
            return response
        except Exception as e:
            logger.log_error('LangChainLLM', f'模板聊天错误: {str(e)}', e)
            return f"抱歉，处理请求时出现错误: {str(e)}"

    def get_model_info(self) -> Dict[str, Any]:
        """获取模型信息。"""
        return {
            'model_type': self.model_type.value,
            'model_name': self.model_name,
            'temperature': self.temperature,
            'max_tokens': self.max_tokens
        }


class ModelRouter:
    """
    模型路由器：根据任务类型自动选择合适的模型。
    """

    def __init__(self):
        self.main_llm = LangChainLLM(ModelType.MAIN)
        self.tool_llm = LangChainLLM(ModelType.TOOL)
        self.vision_llm = LangChainLLM(ModelType.VISION)

        logger.log_module('ModelRouter', '模型路由器初始化完成', {
            'main_model': self.main_llm.model_name,
            'tool_model': self.tool_llm.model_name,
            'vision_model': self.vision_llm.model_name
        })

    def route(self, task_type: str = 'main') -> LangChainLLM:
        """根据任务类型路由。"""
        if task_type == 'tool':
            return self.tool_llm
        elif task_type == 'vision':
            return self.vision_llm
        return self.main_llm

    def get_model_by_type(self, model_type: ModelType) -> LangChainLLM:
        """根据模型类型获取实例。"""
        if model_type == ModelType.TOOL:
            return self.tool_llm
        elif model_type == ModelType.VISION:
            return self.vision_llm
        return self.main_llm
