"""
NPS Bridge Tool - NPS工具桥接
允许智能体协作系统调用NPS工具获取信息
"""

from typing import Dict, Any, Optional
from src.tools.debug_logger import get_debug_logger

# 获取debug日志记录器
debug_logger = get_debug_logger()


class NPSBridgeTool:
    """
    NPS工具桥接类
    为智能体提供调用NPS工具的接口
    """
    
    def __init__(self, nps_invoker=None):
        """
        初始化NPS桥接工具
        
        Args:
            nps_invoker: NPSInvoker实例，用于调用NPS工具
        """
        self.nps_invoker = nps_invoker
        debug_logger.log_module('NPSBridgeTool', 'NPS桥接工具初始化完成')
    
    def call_nps_tool(self, tool_name: str, query: str, **kwargs) -> Dict[str, Any]:
        """
        调用指定的NPS工具
        
        Args:
            tool_name: 工具名称（如'websearch', 'systime'）
            query: 查询内容或参数
            **kwargs: 其他参数
            
        Returns:
            NPS工具执行结果
        """
        if not self.nps_invoker:
            debug_logger.log_error('NPSBridgeTool', 'NPS调用器未初始化', None)
            return {
                'success': False,
                'error': 'NPS调用器未初始化'
            }
        
        try:
            # 构建执行上下文
            context = {
                'query': query,
                **kwargs
            }
            
            debug_logger.log_module(
                'NPSBridgeTool',
                f'智能体调用NPS工具: {tool_name}',
                {'query': query}
            )
            
            # 通过工具名称调用
            result = self.nps_invoker.invoke_tool_by_name(tool_name, context)
            
            if result.get('success'):
                debug_logger.log_info('NPSBridgeTool', f'NPS工具调用成功: {tool_name}')
            else:
                debug_logger.log_warning('NPSBridgeTool', f'NPS工具调用失败: {tool_name}')
            
            return result
            
        except Exception as e:
            debug_logger.log_error('NPSBridgeTool', f'NPS工具调用出错: {tool_name}', e)
            return {
                'success': False,
                'error': f'调用NPS工具失败: {str(e)}'
            }
    
    def search_web(self, query: str, num_results: int = 5, **kwargs) -> Dict[str, Any]:
        """
        网络搜索快捷方法
        
        Args:
            query: 搜索查询
            num_results: 返回结果数量
            **kwargs: 其他参数
            
        Returns:
            搜索结果
        """
        return self.call_nps_tool('websearch', query, num_results=num_results, **kwargs)
    
    def get_system_time(self) -> Dict[str, Any]:
        """
        获取系统时间快捷方法
        
        Returns:
            系统时间信息
        """
        return self.call_nps_tool('systime', '')
    
    def get_available_tools(self) -> Dict[str, Any]:
        """
        获取可用的NPS工具列表
        
        Returns:
            工具列表
        """
        if not self.nps_invoker:
            return {
                'success': False,
                'error': 'NPS调用器未初始化'
            }
        
        try:
            tools = self.nps_invoker.get_all_tools()
            tool_list = [
                {
                    'tool_id': tool.tool_id,
                    'name': tool.name,
                    'description': tool.description,
                    'enabled': tool.enabled
                }
                for tool in tools
            ]
            
            return {
                'success': True,
                'tools': tool_list,
                'count': len(tool_list)
            }
        except Exception as e:
            debug_logger.log_error('NPSBridgeTool', '获取NPS工具列表失败', e)
            return {
                'success': False,
                'error': str(e)
            }
    
    def format_tool_list_for_agent(self) -> str:
        """
        将工具列表格式化为智能体可读的文本
        
        Returns:
            格式化的工具列表描述
        """
        tools_result = self.get_available_tools()
        
        if not tools_result.get('success'):
            return f"获取工具列表失败：{tools_result.get('error', '未知错误')}"
        
        tools = tools_result.get('tools', [])
        if not tools:
            return "当前没有可用的NPS工具"
        
        output = [f"可用的NPS工具共{len(tools)}个：\n"]
        for tool in tools:
            status = "✅" if tool['enabled'] else "❌"
            output.append(f"{status} {tool['name']} ({tool['tool_id']})")
            output.append(f"   功能：{tool['description']}\n")
        
        return '\n'.join(output)
