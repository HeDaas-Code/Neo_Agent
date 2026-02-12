"""
NPS LangChain Tool Wrapper
将NPS工具包装为LangChain Tool，使其可以被智能体调用
"""

from typing import Optional, Dict, Any
from langchain.tools import BaseTool
from pydantic import Field
from src.tools.debug_logger import get_debug_logger

debug_logger = get_debug_logger()


class NPSWebSearchTool(BaseTool):
    """NPS网络搜索工具 - LangChain兼容"""
    
    name: str = "nps_web_search"
    description: str = """
    使用SerpAPI进行网络搜索，获取实时信息、新闻、知识等。
    
    适用场景：
    - 需要查询最新信息、新闻、动态
    - 搜索特定内容、知识、资料
    - 获取网络上的公开信息
    - 需要验证或补充信息
    
    输入格式：搜索查询文本（如"明日方舟终末地"、"最新AI新闻"等）
    输出格式：格式化的搜索结果，包含标题、摘要、链接等
    """
    
    nps_bridge: Any = Field(default=None, exclude=True)
    
    def _run(self, query: str) -> str:
        """执行搜索"""
        if not self.nps_bridge:
            return "错误：NPS桥接工具未初始化"
        
        try:
            result = self.nps_bridge.search_web(query, num_results=5)
            
            if not result.get('success'):
                return f"搜索失败：{result.get('error', '未知错误')}"
            
            # 格式化结果
            from src.nps.tool.websearch import format_search_results_for_agent
            return format_search_results_for_agent(result.get('result', result))
            
        except Exception as e:
            debug_logger.log_error('NPSWebSearchTool', '搜索失败', e)
            return f"搜索失败：{str(e)}"
    
    async def _arun(self, query: str) -> str:
        """异步执行（降级到同步）"""
        return self._run(query)


class NPSSystemTimeTool(BaseTool):
    """NPS系统时间工具 - LangChain兼容"""
    
    name: str = "nps_system_time"
    description: str = """
    获取当前系统时间、日期、星期等信息。
    
    适用场景：
    - 回答"现在几点"、"今天星期几"等时间相关问题
    - 需要知道当前日期、时间来完成任务
    - 判断时间段（早上/中午/晚上等）
    
    输入格式：不需要输入，直接调用即可
    输出格式：当前时间的详细信息（年月日、时分秒、星期、时段等）
    """
    
    nps_bridge: Any = Field(default=None, exclude=True)
    
    def _run(self, query: str = "") -> str:
        """获取系统时间"""
        if not self.nps_bridge:
            return "错误：NPS桥接工具未初始化"
        
        try:
            result = self.nps_bridge.get_system_time()
            
            if not result.get('success'):
                return f"获取时间失败：{result.get('error', '未知错误')}"
            
            # 提取时间信息
            time_data = result.get('result', {})
            if isinstance(time_data, dict) and 'context' in time_data:
                return time_data['context']
            
            return str(time_data)
            
        except Exception as e:
            debug_logger.log_error('NPSSystemTimeTool', '获取时间失败', e)
            return f"获取时间失败：{str(e)}"
    
    async def _arun(self, query: str = "") -> str:
        """异步执行（降级到同步）"""
        return self._run(query)


def create_nps_tools(nps_bridge) -> list:
    """
    创建所有NPS工具的LangChain包装
    
    Args:
        nps_bridge: NPSBridgeTool实例
        
    Returns:
        LangChain Tool列表
    """
    tools = []
    
    # 网络搜索工具
    web_search_tool = NPSWebSearchTool()
    web_search_tool.nps_bridge = nps_bridge
    tools.append(web_search_tool)
    
    # 系统时间工具
    system_time_tool = NPSSystemTimeTool()
    system_time_tool.nps_bridge = nps_bridge
    tools.append(system_time_tool)
    
    debug_logger.log_module('NPSLangChainTools', f'创建了{len(tools)}个NPS LangChain工具')
    
    return tools
