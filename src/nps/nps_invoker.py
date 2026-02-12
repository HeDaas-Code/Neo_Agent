"""
NPS 工具调用模块
负责在理解阶段判断用户对话是否需要调用工具，并执行相关工具获取上下文信息
"""

import os
import time
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv
import requests
from src.tools.debug_logger import get_debug_logger
from src.nps.nps_registry import NPSRegistry, NPSTool

load_dotenv()

# 获取debug日志记录器
debug_logger = get_debug_logger()


class NPSInvoker:
    """
    NPS 工具调用器
    负责判断用户对话与哪些工具相关，并调用相关工具获取信息
    """
    
    def __init__(self, registry: NPSRegistry = None, **kwargs):
        """
        初始化工具调用器

        Args:
            registry: 工具注册表实例，如果为空则创建新实例并自动扫描
            **kwargs: 其他参数（用于向后兼容，会被忽略）
        """
        # API配置
        self.api_key = os.getenv('SILICONFLOW_API_KEY')
        self.api_url = os.getenv('SILICONFLOW_API_URL', 'https://api.siliconflow.cn/v1/chat/completions')
        self.model_name = os.getenv('MODEL_NAME', 'Qwen/Qwen2.5-7B-Instruct')
        
        # NPS LLM 判断配置（带错误处理）
        try:
            self.llm_temperature = float(os.getenv('NPS_LLM_TEMPERATURE', '0.3'))
        except ValueError:
            debug_logger.log_error('NPSInvoker', '无效的NPS_LLM_TEMPERATURE配置，使用默认值0.3')
            self.llm_temperature = 0.3
        
        try:
            self.llm_max_tokens = int(os.getenv('NPS_LLM_MAX_TOKENS', '100'))
        except ValueError:
            debug_logger.log_error('NPSInvoker', '无效的NPS_LLM_MAX_TOKENS配置，使用默认值100')
            self.llm_max_tokens = 100
        
        try:
            self.llm_timeout = int(os.getenv('NPS_LLM_TIMEOUT', '10'))
        except ValueError:
            debug_logger.log_info('NPSInvoker', '无效的NPS_LLM_TIMEOUT，使用默认值10')
            self.llm_timeout = 10
        
        # 工具注册表
        self.registry = registry or NPSRegistry()
        
        # 如果使用默认注册表，自动扫描并注册工具
        if registry is None:
            self.registry.scan_and_register()
        
        debug_logger.log_module('NPSInvoker', '工具调用器初始化完成', {
            'tools_count': len(self.registry.get_enabled_tools())
        })
    
    def _match_keywords(self, user_input: str, tool: NPSTool) -> bool:
        """
        使用关键词匹配判断用户输入是否与工具相关

        Args:
            user_input: 用户输入
            tool: 工具实例

        Returns:
            是否匹配
        """
        user_input_lower = user_input.lower()
        for keyword in tool.keywords:
            if keyword.lower() in user_input_lower:
                return True
        return False
    
    def _judge_relevance_with_llm(self, user_input: str, tools: List[NPSTool]) -> List[str]:
        """
        使用LLM判断用户输入与哪些工具相关

        Args:
            user_input: 用户输入
            tools: 可用工具列表

        Returns:
            相关工具的ID列表
        """
        if not tools:
            return []
        
        debug_logger.log_module('NPSInvoker', '使用LLM判断工具相关性', {
            'user_input': user_input[:100],
            'tools_count': len(tools)
        })
        
        try:
            # 构建工具列表描述
            tools_desc = []
            for i, tool in enumerate(tools, 1):
                desc = f"{i}. {tool.tool_id}: {tool.name} - {tool.description}"
                tools_desc.append(desc)
            tools_list = "\n".join(tools_desc)
            
            # 构建判断提示词
            judge_prompt = f"""请判断以下用户消息是否需要获取额外信息来回答。

用户消息："{user_input}"

可用的信息获取工具：
{tools_list}

请分析用户消息的意图，判断需要调用哪些工具来获取有助于回答的信息。
如果需要调用工具，请输出工具的编号（如：1）或ID（如：systime），多个用逗号分隔。
如果不需要任何工具，请输出"无"。

注意：
- 只有当用户消息明确或隐含需要某种特定信息时才调用相应工具
- 例如询问"现在几点"、"什么时候"等时间相关问题时，需要调用时间工具
- 普通的闲聊不需要调用任何工具

请直接输出结果："""

            headers = {
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json'
            }
            
            payload = {
                'model': self.model_name,
                'messages': [{'role': 'user', 'content': judge_prompt}],
                'temperature': self.llm_temperature,
                'max_tokens': self.llm_max_tokens,
                'stream': False
            }
            
            debug_logger.log_request('NPSInvoker', self.api_url, payload, headers)
            
            start_time = time.time()
            response = requests.post(
                self.api_url,
                headers=headers,
                json=payload,
                timeout=self.llm_timeout
            )
            elapsed_time = time.time() - start_time
            
            response.raise_for_status()
            result = response.json()
            
            debug_logger.log_response('NPSInvoker', result, response.status_code, elapsed_time)
            
            if 'choices' in result and len(result['choices']) > 0:
                reply = result['choices'][0]['message']['content'].strip()
                
                debug_logger.log_info('NPSInvoker', f'LLM判断结果: {reply}')
                
                # 解析回复
                if reply == '无' or not reply:
                    return []
                
                # 提取工具ID
                relevant_ids = []
                tool_ids = {t.tool_id.lower(): t.tool_id for t in tools}
                # 创建索引到工具ID的映射（1-based）
                tool_by_index = {str(i): t.tool_id for i, t in enumerate(tools, 1)}
                
                # 尝试分割多个ID
                parts = reply.replace('，', ',').split(',')
                for part in parts:
                    part = part.strip()
                    part_lower = part.lower()
                    
                    # 尝试匹配工具ID
                    if part_lower in tool_ids:
                        relevant_ids.append(tool_ids[part_lower])
                    # 尝试匹配数字索引
                    elif part in tool_by_index:
                        relevant_ids.append(tool_by_index[part])
                
                return relevant_ids
            
            return []
            
        except requests.exceptions.RequestException as e:
            debug_logger.log_error('NPSInvoker', f'LLM请求失败: {str(e)}', e)
            # 降级到关键词匹配
            return self._fallback_keyword_match(user_input, tools)
        except Exception as e:
            debug_logger.log_error('NPSInvoker', f'判断相关性时出错: {str(e)}', e)
            return self._fallback_keyword_match(user_input, tools)
    
    def _fallback_keyword_match(self, user_input: str, tools: List[NPSTool]) -> List[str]:
        """
        关键词匹配降级方案

        Args:
            user_input: 用户输入
            tools: 工具列表

        Returns:
            匹配的工具ID列表
        """
        debug_logger.log_info('NPSInvoker', '使用关键词匹配降级方案')
        
        relevant_ids = []
        for tool in tools:
            if self._match_keywords(user_input, tool):
                relevant_ids.append(tool.tool_id)
        
        return relevant_ids
    
    def invoke_relevant_tools(self, user_input: str, use_llm: bool = True) -> Dict[str, Any]:
        """
        判断并调用与用户输入相关的工具

        Args:
            user_input: 用户输入
            use_llm: 是否使用LLM判断相关性

        Returns:
            包含工具调用结果的字典
        """
        enabled_tools = self.registry.get_enabled_tools()
        
        if not enabled_tools:
            return {
                'tools_invoked': [],
                'context_info': '',
                'has_context': False
            }
        
        # 判断相关工具
        if use_llm and self.api_key:
            relevant_tool_ids = self._judge_relevance_with_llm(user_input, enabled_tools)
        else:
            relevant_tool_ids = self._fallback_keyword_match(user_input, enabled_tools)
        
        if not relevant_tool_ids:
            debug_logger.log_info('NPSInvoker', '无相关工具需要调用')
            return {
                'tools_invoked': [],
                'context_info': '',
                'has_context': False
            }
        
        # 调用相关工具
        tools_results = []
        context_parts = []
        
        for tool_id in relevant_tool_ids:
            tool = self.registry.get_tool(tool_id)
            if tool and tool.enabled:
                debug_logger.log_info('NPSInvoker', f'调用工具: {tool.name}')
                
                # 执行工具
                result = tool.execute({'user_input': user_input})
                tools_results.append(result)
                
                if result['success'] and result.get('result'):
                    # 提取工具返回的上下文信息
                    tool_result = result['result']
                    if isinstance(tool_result, dict):
                        context = tool_result.get('context', '')
                        if context:
                            context_parts.append(f"[{tool.name}] {context}")
                    elif isinstance(tool_result, str):
                        context_parts.append(f"[{tool.name}] {tool_result}")
        
        # 合并上下文
        context_info = '\n'.join(context_parts) if context_parts else ''
        
        debug_logger.log_info('NPSInvoker', f'工具调用完成', {
            'invoked_count': len(tools_results),
            'context_length': len(context_info)
        })
        
        return {
            'tools_invoked': tools_results,
            'context_info': context_info,
            'has_context': bool(context_info)
        }
    
    def get_context_for_understanding(self, user_input: str) -> Optional[str]:
        """
        获取理解阶段需要的上下文信息
        这是提供给 chat_agent 理解阶段使用的主要接口

        Args:
            user_input: 用户输入

        Returns:
            上下文信息字符串，如果没有则返回None
        """
        result = self.invoke_relevant_tools(user_input)
        
        if result['has_context']:
            return result['context_info']
        
        return None
    
    def format_nps_prompt(self, context_info: str) -> str:
        """
        格式化NPS上下文为系统提示词

        Args:
            context_info: 上下文信息

        Returns:
            格式化后的提示词
        """
        return f"""【NPS工具信息】
以下是通过工具获取的实时信息，请在回复中参考使用：
{context_info}"""
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        获取调用器统计信息

        Returns:
            统计信息字典
        """
        registry_stats = self.registry.get_statistics()
        return {
            'registry': registry_stats,
            'llm_config': {
                'temperature': self.llm_temperature,
                'max_tokens': self.llm_max_tokens,
                'timeout': self.llm_timeout
            }
        }
