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

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_openai import ChatOpenAI

from src.cortex.config.model_config import ModelType, get_model_config
from src.cortex.tools import ToolRegistry, create_default_tool_registry
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

    def __init__(self, router, tool_registry: Optional[ToolRegistry] = None):
        super().__init__(router)
        self._model_router: Optional[ModelRouter] = None
        self.tool_registry = tool_registry or create_default_tool_registry()

    def _get_model_router(self) -> ModelRouter:
        """
        懒加载模型路由器，避免启动期强制初始化 LLM。
        """
        if self._model_router is None:
            self._model_router = ModelRouter(tool_registry=self.tool_registry)
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
            tools = packet.payload.get("tools")
            reply = model_router.route(task_type).chat(messages, tools=tools)
            return packet.response({"role": "assistant", "content": reply})

        if channel == "llm_stream":
            # 同步场景下返回完整回复；真实流式请使用 handle_stream
            messages = packet.payload.get("messages", [])
            task_type = packet.payload.get("task_type", "main")
            tools = packet.payload.get("tools")
            reply = model_router.route(task_type).chat(messages, tools=tools)
            return packet.response({"role": "assistant", "content": reply, "stream": False})

        if channel == "llm_template":
            template = packet.payload.get("template", "")
            variables = packet.payload.get("variables", {})
            history = packet.payload.get("history")
            task_type = packet.payload.get("task_type", "main")
            tools = packet.payload.get("tools")
            reply = model_router.route(task_type).chat_with_template(template, variables, history, tools=tools)
            return packet.response({"role": "assistant", "content": reply})

        if channel == "llm_info":
            task_type = packet.payload.get("task_type", "main")
            info = model_router.route(task_type).get_model_info()
            return packet.response(info)

        if channel == "tools":
            return packet.response({"tools": self.tool_registry.list_tools()})

        if channel == "tool_call":
            tool_name = packet.payload.get("tool_name")
            tool_args = packet.payload.get("tool_args", {})
            if not tool_name:
                return Packet.error(packet, "tool_name required", code="INVALID_REQUEST")
            result = self._execute_tool(tool_name, tool_args)
            return packet.response({"tool_name": tool_name, "result": result})

        return packet.response({"status": "unknown_channel", "channel": channel})

    def _execute_tool(self, tool_name: str, tool_args: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行指定工具并返回结果。
        """
        tool = self.tool_registry.get(tool_name)
        if tool is None:
            return {"error": f"工具未找到: {tool_name}", "code": "TOOL_NOT_FOUND"}
        try:
            result = tool.invoke(tool_args)
            return {"output": result}
        except Exception as exc:
            logger.log_error('LLMCore', f'工具执行失败: {tool_name}', exc)
            return {"error": str(exc), "code": "TOOL_EXEC_ERROR"}

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
            tools = packet.payload.get("tools")
            try:
                async for chunk in model_router.route(task_type).chat_stream(messages, tools=tools):
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

    def __init__(self, model_type: ModelType = ModelType.MAIN, tool_registry: Optional[ToolRegistry] = None):
        self.model_type = model_type
        self.config = get_model_config()
        self.tool_registry = tool_registry

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

    def chat(self, messages: List[Dict[str, str]], tools: Optional[List[str]] = None) -> str:
        """发送聊天请求，支持工具调用。"""
        try:
            logger.log_module('LangChainLLM', f'准备发送{self.model_type.value}模型请求', {
                'message_count': len(messages),
                'model_name': self.model_name,
                'tools': tools,
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
            llm = self._bind_tools(tools)
            response = llm.invoke(langchain_messages)

            # 处理工具调用
            if getattr(response, 'tool_calls', None):
                langchain_messages.append(response)
                for tool_call in response.tool_calls:
                    tool_result = self._execute_tool_call(tool_call)
                    langchain_messages.append(ToolMessage(
                        content=str(tool_result),
                        tool_call_id=tool_call.get('id', ''),
                    ))
                response = llm.invoke(langchain_messages)

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

    async def chat_stream(self, messages: List[Dict[str, str]], tools: Optional[List[str]] = None) -> AsyncIterator[str]:
        """流式发送聊天请求，逐 token 返回字符串 chunk；带工具时降级为完整回复后分段输出。"""
        try:
            logger.log_module('LangChainLLM', f'准备流式发送{self.model_type.value}模型请求', {
                'message_count': len(messages),
                'model_name': self.model_name,
                'tools': tools,
            })

            for i, msg in enumerate(messages):
                logger.log_prompt(
                    'LangChainLLM',
                    msg['role'],
                    msg['content'],
                    {'message_index': i, 'total_messages': len(messages), 'model_type': self.model_type.value}
                )

            start_time = time.time()
            # 带工具调用时，先走同步 chat 完成工具链，再按字符流式输出
            if tools:
                full_reply = self.chat(messages, tools=tools)
                for char in full_reply:
                    yield char
                elapsed_time = time.time() - start_time
                logger.log_info('LangChainLLM', '流式响应完成（带工具降级）', {
                    'elapsed_time': elapsed_time,
                    'model_type': self.model_type.value,
                })
                return

            langchain_messages = self._convert_messages_to_langchain(messages)
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
        message_history: Optional[List[Dict[str, str]]] = None,
        tools: Optional[List[str]] = None,
    ) -> str:
        """使用模板和变量进行聊天，支持工具调用。"""
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

            llm = self._bind_tools(tools)
            chain = prompt | llm | StrOutputParser()
            start_time = time.time()
            response = chain.invoke(variables)
            elapsed_time = time.time() - start_time

            logger.log_info('LangChainLLM', '模板聊天完成', {
                'elapsed_time': elapsed_time,
                'model_type': self.model_type.value,
                'response_length': len(response),
                'tools': tools,
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

    def _bind_tools(self, tools: Optional[List[str]]) -> ChatOpenAI:
        """
        根据工具名列表绑定工具到 LLM；无工具或无注册表时返回原 LLM。
        """
        if not tools or self.tool_registry is None:
            return self.llm
        tool_instances = []
        for name in tools:
            tool_instance = self.tool_registry.get(name)
            if tool_instance is not None:
                tool_instances.append(tool_instance)
        if not tool_instances:
            return self.llm
        return self.llm.bind_tools(tool_instances)

    def _execute_tool_call(self, tool_call: Dict[str, Any]) -> Any:
        """
        执行单个工具调用并返回结果。
        """
        name = tool_call.get('name')
        args = tool_call.get('args', {})
        if not name or self.tool_registry is None:
            return f"工具调用失败: {name}"
        tool_instance = self.tool_registry.get(name)
        if tool_instance is None:
            return f"工具未找到: {name}"
        try:
            return tool_instance.invoke(args)
        except Exception as exc:
            logger.log_error('LangChainLLM', f'工具执行失败: {name}', exc)
            return f"工具执行失败: {exc}"


class ModelRouter:
    """
    模型路由器：根据任务类型自动选择合适的模型。
    """

    def __init__(self, tool_registry: Optional[ToolRegistry] = None):
        self.main_llm = LangChainLLM(ModelType.MAIN, tool_registry=tool_registry)
        self.tool_llm = LangChainLLM(ModelType.TOOL, tool_registry=tool_registry)
        self.vision_llm = LangChainLLM(ModelType.VISION, tool_registry=tool_registry)

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
