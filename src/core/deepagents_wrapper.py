"""
DeepAgents 集成模块
使用 deepagents 库实现高级子智能体生成、长期记忆和文件系统功能
"""

import os
from typing import List, Dict, Any, Optional, Callable
from dotenv import load_dotenv
from deepagents import create_deep_agent, SubAgent as DeepSubAgent, MemoryMiddleware, FilesystemMiddleware
from deepagents.backends import StateBackend
from langgraph.checkpoint.memory import MemorySaver
from langchain_openai import ChatOpenAI

from src.tools.debug_logger import get_debug_logger
from src.core.langchain_llm import LangChainLLM, ModelType

load_dotenv()

# 获取debug日志记录器
debug_logger = get_debug_logger()


class DeepSubAgentWrapper:
    """
    深度子智能体包装器
    使用deepagents库解决以下问题：
    1. 每次执行都需要传递完整上下文 -> 使用checkpointer持久化状态
    2. 没有持久化状态管理 -> 使用MemorySaver和store
    3. 无法处理大型工具结果 -> 使用FilesystemMiddleware
    4. 缺乏任务规划能力 -> 使用内置的todo list功能
    """

    def __init__(
        self,
        agent_id: str,
        role: str,
        description: str,
        system_prompt: Optional[str] = None,
        tools: List[Any] = None,
        memory_paths: List[str] = None,
        enable_filesystem: bool = True,
        enable_memory: bool = True
    ):
        """
        初始化深度子智能体

        Args:
            agent_id: 智能体唯一标识
            role: 角色名称
            description: 角色描述
            system_prompt: 系统提示词（如果为None，则使用role和description生成）
            tools: 额外的工具列表
            memory_paths: 记忆文件路径列表
            enable_filesystem: 是否启用文件系统功能
            enable_memory: 是否启用长期记忆功能
        """
        self.agent_id = agent_id
        self.role = role
        self.description = description
        self.tools = tools or []
        
        # 构建系统提示词
        if system_prompt is None:
            system_prompt = f"""你是一个{role}。

你的职责：{description}

请按照任务要求完成你的工作，如有需要可以使用可用的工具。
你可以：
1. 使用write_todos管理待办事项，规划任务步骤
2. 使用文件系统工具（ls, read_file, write_file等）处理大型结果
3. 保持状态跨会话持久化
"""
        
        self.system_prompt = system_prompt
        
        # 创建checkpointer用于状态持久化
        self.checkpointer = MemorySaver()
        
        # 配置记忆路径
        self.memory_paths = memory_paths or []
        
        # 构建中间件栈
        middleware = []
        
        # 添加长期记忆中间件
        if enable_memory and self.memory_paths:
            try:
                memory_middleware = MemoryMiddleware(sources=self.memory_paths)
                middleware.append(memory_middleware)
                debug_logger.log_info('DeepSubAgentWrapper', f'已启用长期记忆: {self.memory_paths}')
            except Exception as e:
                debug_logger.log_error('DeepSubAgentWrapper', f'启用长期记忆失败: {str(e)}', e)
        
        # 创建LLM（使用工具模型）
        try:
            llm_wrapper = LangChainLLM(ModelType.TOOL)
            model = llm_wrapper.llm
        except Exception as e:
            debug_logger.log_error('DeepSubAgentWrapper', f'创建LLM失败，使用默认模型: {str(e)}', e)
            # 降级到OpenAI兼容API
            api_base = os.getenv('SILICON_FLOW_API_BASE', 'https://api.siliconflow.cn/v1')
            api_key = os.getenv('SILICON_FLOW_API_KEY', '')
            model_name = os.getenv('TOOL_MODEL_NAME', 'Qwen/Qwen2.5-7B-Instruct')
            
            model = ChatOpenAI(
                model=model_name,
                openai_api_base=api_base,
                openai_api_key=api_key,
                temperature=0.7
            )
        
        # 创建深度智能体
        try:
            self.agent = create_deep_agent(
                model=model,
                tools=self.tools,
                system_prompt=self.system_prompt,
                middleware=middleware,
                checkpointer=self.checkpointer,  # 启用状态持久化
                backend=StateBackend,  # 使用状态后端（内存中的文件系统）
                name=agent_id
            )
            
            debug_logger.log_module('DeepSubAgentWrapper', f'深度子智能体[{role}]初始化成功', {
                'agent_id': agent_id,
                'has_checkpointer': True,
                'has_filesystem': enable_filesystem,
                'has_memory': enable_memory and bool(self.memory_paths),
                'tools_count': len(self.tools)
            })
            
        except Exception as e:
            debug_logger.log_error('DeepSubAgentWrapper', f'创建深度智能体失败: {str(e)}', e)
            raise

    def execute_task(
        self,
        task_description: str,
        context: Dict[str, Any],
        thread_id: Optional[str] = None,
        files: Optional[Dict[str, str]] = None
    ) -> str:
        """
        执行任务（带状态持久化和文件系统支持）

        Args:
            task_description: 任务描述
            context: 上下文信息
            thread_id: 线程ID（用于跨会话状态管理，如果为None则使用agent_id）
            files: 虚拟文件系统中的文件（路径->内容的映射）

        Returns:
            执行结果
        """
        debug_logger.log_module('DeepSubAgentWrapper', f'智能体[{self.role}]开始执行任务', {
            'agent_id': self.agent_id,
            'task_length': len(task_description),
            'has_context': bool(context),
            'has_files': bool(files)
        })
        
        try:
            # 使用thread_id实现跨会话状态管理
            if thread_id is None:
                thread_id = self.agent_id
            
            # 准备配置
            config = {
                "configurable": {
                    "thread_id": thread_id
                }
            }
            
            # 准备输入
            input_data = {
                "messages": [
                    {
                        "role": "user",
                        "content": f"""任务：{task_description}

上下文信息：
{self._format_context(context)}

请完成这个任务。你可以使用以下工具：
1. write_todos - 规划任务步骤，管理待办事项
2. 文件系统工具（ls, read_file, write_file等）- 处理大型数据
3. 其他可用工具

开始执行吧！"""
                    }
                ]
            }
            
            # 如果有文件，添加到输入
            if files:
                input_data["files"] = files
            
            # 调用智能体
            result = self.agent.invoke(input_data, config=config)
            
            # 提取最后的消息作为结果
            if "messages" in result:
                last_message = result["messages"][-1]
                if hasattr(last_message, "content"):
                    output = last_message.content
                else:
                    output = str(last_message)
            else:
                output = str(result)
            
            debug_logger.log_info('DeepSubAgentWrapper', f'智能体[{self.role}]任务完成', {
                'output_length': len(output),
                'thread_id': thread_id
            })
            
            return output
            
        except Exception as e:
            debug_logger.log_error('DeepSubAgentWrapper', f'智能体[{self.role}]执行失败: {str(e)}', e)
            return f"【执行失败】{str(e)}"
    
    def _format_context(self, context: Dict[str, Any]) -> str:
        """
        格式化上下文信息

        Args:
            context: 上下文字典

        Returns:
            格式化后的字符串
        """
        import json
        return json.dumps(context, ensure_ascii=False, indent=2)
    
    def get_state(self, thread_id: Optional[str] = None) -> Dict[str, Any]:
        """
        获取智能体的持久化状态

        Args:
            thread_id: 线程ID

        Returns:
            状态字典
        """
        if thread_id is None:
            thread_id = self.agent_id
        
        try:
            config = {"configurable": {"thread_id": thread_id}}
            state = self.checkpointer.get(config)
            return state if state else {}
        except Exception as e:
            debug_logger.log_error('DeepSubAgentWrapper', f'获取状态失败: {str(e)}', e)
            return {}


class DeepAgentsKnowledgeManager:
    """
    基于DeepAgents的知识管理器
    使用FilesystemMiddleware和MemoryMiddleware实现结构化知识管理
    """
    
    def __init__(
        self,
        knowledge_dir: str = "/knowledge",
        memory_file: str = "/memory/AGENTS.md"
    ):
        """
        初始化知识管理器

        Args:
            knowledge_dir: 知识存储目录（虚拟文件系统）
            memory_file: 记忆文件路径
        """
        self.knowledge_dir = knowledge_dir
        self.memory_file = memory_file
        self.checkpointer = MemorySaver()
        
        debug_logger.log_module('DeepAgentsKnowledgeManager', '知识管理器初始化', {
            'knowledge_dir': knowledge_dir,
            'memory_file': memory_file
        })
    
    def create_knowledge_agent(
        self,
        model: Optional[Any] = None,
        tools: List[Any] = None
    ):
        """
        创建知识管理智能体

        Args:
            model: LLM模型
            tools: 额外工具

        Returns:
            配置好的深度智能体
        """
        if model is None:
            try:
                llm_wrapper = LangChainLLM(ModelType.TOOL)
                model = llm_wrapper.llm
            except Exception as e:
                debug_logger.log_error('DeepAgentsKnowledgeManager', f'创建LLM失败: {str(e)}', e)
                raise
        
        system_prompt = """你是一个专业的知识管理专家。

你的职责：
1. 从对话中提取结构化知识
2. 将知识存储到文件系统中，保持良好的组织结构
3. 检索和管理知识，确保信息的准确性和完整性

你可以使用以下工具：
- write_file: 写入知识到文件
- read_file: 读取已存储的知识
- ls: 列出目录内容
- grep: 搜索知识内容
- write_todos: 管理知识提取任务

请保持知识的结构化和可检索性。"""
        
        agent = create_deep_agent(
            model=model,
            tools=tools or [],
            system_prompt=system_prompt,
            memory=[self.memory_file],  # 启用长期记忆
            checkpointer=self.checkpointer,
            backend=StateBackend,
            name="knowledge_manager"
        )
        
        debug_logger.log_info('DeepAgentsKnowledgeManager', '知识管理智能体创建成功')
        
        return agent
    
    def extract_and_store_knowledge(
        self,
        conversation: List[Dict[str, Any]],
        thread_id: str = "knowledge_extraction"
    ) -> Dict[str, Any]:
        """
        从对话中提取并存储知识

        Args:
            conversation: 对话历史
            thread_id: 线程ID

        Returns:
            提取结果
        """
        try:
            agent = self.create_knowledge_agent()
            
            # 格式化对话
            conversation_text = "\n".join([
                f"{msg['role']}: {msg['content']}"
                for msg in conversation
            ])
            
            input_data = {
                "messages": [
                    {
                        "role": "user",
                        "content": f"""请从以下对话中提取知识，并存储到文件系统中。

对话内容：
{conversation_text}

请：
1. 识别关键信息和事实
2. 按主题组织知识
3. 使用write_file工具将知识存储到{self.knowledge_dir}目录
4. 返回提取的知识摘要"""
                    }
                ]
            }
            
            config = {"configurable": {"thread_id": thread_id}}
            result = agent.invoke(input_data, config=config)
            
            # 提取结果
            if "messages" in result:
                last_message = result["messages"][-1]
                summary = last_message.content if hasattr(last_message, "content") else str(last_message)
            else:
                summary = str(result)
            
            debug_logger.log_info('DeepAgentsKnowledgeManager', '知识提取完成', {
                'summary_length': len(summary)
            })
            
            return {
                'success': True,
                'summary': summary
            }
            
        except Exception as e:
            debug_logger.log_error('DeepAgentsKnowledgeManager', f'知识提取失败: {str(e)}', e)
            return {
                'success': False,
                'error': str(e)
            }
    
    def retrieve_knowledge(
        self,
        query: str,
        thread_id: str = "knowledge_retrieval"
    ) -> Dict[str, Any]:
        """
        检索知识

        Args:
            query: 查询内容
            thread_id: 线程ID

        Returns:
            检索结果
        """
        try:
            agent = self.create_knowledge_agent()
            
            input_data = {
                "messages": [
                    {
                        "role": "user",
                        "content": f"""请检索与以下查询相关的知识：

查询：{query}

请：
1. 使用grep搜索相关知识文件
2. 使用read_file读取相关内容
3. 整理并返回最相关的知识"""
                    }
                ]
            }
            
            config = {"configurable": {"thread_id": thread_id}}
            result = agent.invoke(input_data, config=config)
            
            # 提取结果
            if "messages" in result:
                last_message = result["messages"][-1]
                knowledge = last_message.content if hasattr(last_message, "content") else str(last_message)
            else:
                knowledge = str(result)
            
            debug_logger.log_info('DeepAgentsKnowledgeManager', '知识检索完成', {
                'knowledge_length': len(knowledge)
            })
            
            return {
                'success': True,
                'knowledge': knowledge
            }
            
        except Exception as e:
            debug_logger.log_error('DeepAgentsKnowledgeManager', f'知识检索失败: {str(e)}', e)
            return {
                'success': False,
                'error': str(e)
            }
