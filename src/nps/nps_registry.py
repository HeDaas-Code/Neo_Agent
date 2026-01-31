"""
NPS 工具注册模块
负责自动扫描和加载 NPS/tool 目录下的工具模块
支持通过 .NPS 元数据文件描述工具信息
"""

import os
import json
import importlib.util
from typing import Dict, Any, List, Optional, Callable
from src.tools.debug_logger import get_debug_logger

# 获取debug日志记录器
debug_logger = get_debug_logger()


class NPSTool:
    """
    NPS 工具类
    封装单个工具的元数据和执行函数
    """
    
    def __init__(self, 
                 tool_id: str,
                 name: str,
                 description: str,
                 keywords: List[str],
                 execute_func: Callable,
                 version: str = "1.0.0",
                 author: str = "Unknown",
                 enabled: bool = True):
        """
        初始化 NPS 工具

        Args:
            tool_id: 工具唯一标识符
            name: 工具名称
            description: 工具功能描述（用于LLM判断相关性）
            keywords: 触发关键词列表
            execute_func: 工具执行函数
            version: 工具版本
            author: 工具作者
            enabled: 是否启用
        """
        self.tool_id = tool_id
        self.name = name
        self.description = description
        self.keywords = keywords
        self.execute_func = execute_func
        self.version = version
        self.author = author
        self.enabled = enabled
    
    def execute(self, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        执行工具并返回结果

        Args:
            context: 执行上下文，包含用户输入等信息

        Returns:
            包含工具执行结果的字典
        """
        try:
            result = self.execute_func(context or {})
            return {
                'success': True,
                'tool_id': self.tool_id,
                'tool_name': self.name,
                'result': result
            }
        except Exception as e:
            debug_logger.log_error('NPSTool', f'工具执行失败: {self.name}', e)
            return {
                'success': False,
                'tool_id': self.tool_id,
                'tool_name': self.name,
                'error': str(e)
            }
    
    def to_dict(self) -> Dict[str, Any]:
        """
        转换为字典表示

        Returns:
            工具信息字典
        """
        return {
            'tool_id': self.tool_id,
            'name': self.name,
            'description': self.description,
            'keywords': self.keywords,
            'version': self.version,
            'author': self.author,
            'enabled': self.enabled
        }


class NPSRegistry:
    """
    NPS 工具注册表
    负责扫描、加载和管理所有 NPS 工具
    """
    
    def __init__(self, tools_dir: str = None):
        """
        初始化工具注册表

        Args:
            tools_dir: 工具目录路径，默认为 NPS/tool
        """
        # 获取当前文件所在目录
        current_dir = os.path.dirname(os.path.abspath(__file__))
        self.tools_dir = tools_dir or os.path.join(current_dir, 'tool')
        
        # 已注册的工具
        self._tools: Dict[str, NPSTool] = {}
        
        debug_logger.log_module('NPSRegistry', '工具注册表初始化', {
            'tools_dir': self.tools_dir
        })
    
    def scan_and_register(self) -> List[str]:
        """
        扫描工具目录并自动注册所有有效工具

        Returns:
            成功注册的工具ID列表
        """
        registered = []
        
        if not os.path.exists(self.tools_dir):
            debug_logger.log_info('NPSRegistry', f'工具目录不存在: {self.tools_dir}')
            return registered
        
        # 扫描 .NPS 元数据文件
        for filename in os.listdir(self.tools_dir):
            if filename.endswith('.NPS'):
                nps_path = os.path.join(self.tools_dir, filename)
                tool_id = self._register_from_nps_file(nps_path)
                if tool_id:
                    registered.append(tool_id)
        
        debug_logger.log_info('NPSRegistry', f'工具扫描完成', {
            'total_registered': len(registered),
            'tools': registered
        })
        
        return registered
    
    def _register_from_nps_file(self, nps_path: str) -> Optional[str]:
        """
        从 .NPS 元数据文件注册工具

        Args:
            nps_path: .NPS 文件路径

        Returns:
            注册成功返回工具ID，失败返回None
        """
        try:
            # 读取 .NPS 元数据文件
            with open(nps_path, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
            
            # 验证必需字段
            required_fields = ['tool_id', 'name', 'description', 'module', 'function']
            for field in required_fields:
                if field not in metadata:
                    debug_logger.log_error('NPSRegistry', f'元数据缺少必需字段: {field}', 
                                          f'文件: {nps_path}')
                    return None
            
            # 加载对应的 Python 模块
            module_name = metadata['module']
            module_path = os.path.join(self.tools_dir, f'{module_name}.py')
            
            if not os.path.exists(module_path):
                debug_logger.log_error('NPSRegistry', f'工具模块文件不存在: {module_path}')
                return None
            
            # 动态加载模块
            spec = importlib.util.spec_from_file_location(module_name, module_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # 获取执行函数
            function_name = metadata['function']
            if not hasattr(module, function_name):
                debug_logger.log_error('NPSRegistry', 
                                      f'模块 {module_name} 中找不到函数: {function_name}')
                return None
            
            execute_func = getattr(module, function_name)
            
            # 创建工具实例
            tool = NPSTool(
                tool_id=metadata['tool_id'],
                name=metadata['name'],
                description=metadata['description'],
                keywords=metadata.get('keywords', []),
                execute_func=execute_func,
                version=metadata.get('version', '1.0.0'),
                author=metadata.get('author', 'Unknown'),
                enabled=metadata.get('enabled', True)
            )
            
            # 注册工具
            self._tools[tool.tool_id] = tool
            
            debug_logger.log_info('NPSRegistry', f'工具注册成功: {tool.name}', {
                'tool_id': tool.tool_id,
                'version': tool.version
            })
            
            return tool.tool_id
            
        except json.JSONDecodeError as e:
            debug_logger.log_error('NPSRegistry', f'解析 .NPS 文件失败: {nps_path}', e)
            return None
        except Exception as e:
            debug_logger.log_error('NPSRegistry', f'注册工具失败', e)
            return None
    
    def register_tool(self, tool: NPSTool) -> bool:
        """
        手动注册一个工具

        Args:
            tool: NPSTool 实例

        Returns:
            注册是否成功
        """
        if tool.tool_id in self._tools:
            debug_logger.log_info('NPSRegistry', f'工具已存在，跳过注册: {tool.tool_id}')
            return False
        
        self._tools[tool.tool_id] = tool
        debug_logger.log_info('NPSRegistry', f'手动注册工具成功: {tool.name}')
        return True
    
    def unregister_tool(self, tool_id: str) -> bool:
        """
        注销一个工具

        Args:
            tool_id: 工具ID

        Returns:
            注销是否成功
        """
        if tool_id in self._tools:
            del self._tools[tool_id]
            debug_logger.log_info('NPSRegistry', f'工具已注销: {tool_id}')
            return True
        return False
    
    def get_tool(self, tool_id: str) -> Optional[NPSTool]:
        """
        获取指定工具

        Args:
            tool_id: 工具ID

        Returns:
            工具实例，不存在返回None
        """
        return self._tools.get(tool_id)
    
    def get_all_tools(self) -> List[NPSTool]:
        """
        获取所有已注册的工具

        Returns:
            工具列表
        """
        return list(self._tools.values())
    
    def get_enabled_tools(self) -> List[NPSTool]:
        """
        获取所有已启用的工具

        Returns:
            已启用的工具列表
        """
        return [tool for tool in self._tools.values() if tool.enabled]
    
    def get_tools_summary(self) -> str:
        """
        获取所有工具的摘要信息，用于LLM判断相关性

        Returns:
            工具摘要字符串
        """
        enabled_tools = self.get_enabled_tools()
        if not enabled_tools:
            return ""
        
        summaries = []
        for tool in enabled_tools:
            summary = f"- {tool.name}: {tool.description}"
            if tool.keywords:
                summary += f" (关键词: {', '.join(tool.keywords)})"
            summaries.append(summary)
        
        return "\n".join(summaries)
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        获取注册表统计信息

        Returns:
            统计信息字典
        """
        tools = list(self._tools.values())
        enabled_count = sum(1 for t in tools if t.enabled)
        
        return {
            'total_tools': len(tools),
            'enabled_tools': enabled_count,
            'disabled_tools': len(tools) - enabled_count,
            'tool_ids': list(self._tools.keys())
        }
