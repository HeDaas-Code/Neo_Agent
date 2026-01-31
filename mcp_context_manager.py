"""
MCP上下文管理器
管理智能体的MCP上下文，提供工具和资源管理
"""

import os
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv
from mcp_client import MCPClient
from mcp_config import MCPConfig
from debug_logger import get_debug_logger

load_dotenv()

# 获取debug日志记录器
debug_logger = get_debug_logger()


class MCPContextManager:
    """
    MCP上下文管理器
    为智能体提供MCP协议支持，管理工具、资源和提示词
    """
    
    def __init__(self, enable_mcp: bool = None, config_file: str = "mcp_config.json"):
        """
        初始化MCP上下文管理器
        
        Args:
            enable_mcp: 是否启用MCP，如果为None则从配置文件读取
            config_file: MCP配置文件路径
        """
        # 加载MCP配置
        self.mcp_config = MCPConfig(config_file)
        
        # 确定是否启用MCP
        if enable_mcp is None:
            enable_mcp = self.mcp_config.is_enabled()
        
        self.enable_mcp = enable_mcp
        
        # 创建MCP客户端时传入max_contexts配置
        if enable_mcp:
            max_contexts = self.mcp_config.get_max_contexts()
            self.mcp_client = MCPClient(max_contexts=max_contexts)
        else:
            self.mcp_client = None
        
        if self.enable_mcp:
            debug_logger.log_info("MCPContextManager", "MCP上下文管理器已启用", {})
            self._register_default_tools()
            self._register_default_resources()
            self._register_default_prompts()
        else:
            debug_logger.log_info("MCPContextManager", "MCP上下文管理器已禁用", {})
    
    def _register_default_tools(self):
        """
        注册默认MCP工具（仅注册启用的工具）
        """
        # 获取当前时间工具
        if self.mcp_config.is_tool_enabled("get_current_time"):
            def get_current_time(args: Dict[str, Any]) -> str:
                from datetime import datetime
                return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            self.mcp_client.register_tool(
                name="get_current_time",
                description="获取当前时间",
                handler=get_current_time,
                parameters={
                    "type": "object",
                    "properties": {}
                }
            )
        
        # 计算器工具
        if self.mcp_config.is_tool_enabled("calculate"):
            def calculate(args: Dict[str, Any]) -> float:
                expression = args.get("expression", "")
                try:
                    # 安全的表达式求值 - 仅允许数字、运算符和括号
                    import re
                    # 验证表达式只包含安全字符
                    if not re.match(r'^[\d\s\+\-\*\/\(\)\.\,]+$', expression):
                        raise ValueError("表达式包含不允许的字符")
                    
                    # 使用ast.literal_eval的安全替代方案
                    # 这里我们使用一个简单的数学计算器
                    import ast
                    import operator
                    
                    # 支持的运算符
                    operators = {
                        ast.Add: operator.add,
                        ast.Sub: operator.sub,
                        ast.Mult: operator.mul,
                        ast.Div: operator.truediv,
                        ast.USub: operator.neg,
                        ast.UAdd: operator.pos,
                    }
                    
                    def eval_expr(node):
                        if isinstance(node, ast.Num):  # 数字
                            return node.n
                        elif isinstance(node, ast.BinOp):  # 二元运算
                            return operators[type(node.op)](eval_expr(node.left), eval_expr(node.right))
                        elif isinstance(node, ast.UnaryOp):  # 一元运算
                            return operators[type(node.op)](eval_expr(node.operand))
                        else:
                            raise ValueError("不支持的表达式类型")
                    
                    # 解析并计算表达式
                    node = ast.parse(expression, mode='eval')
                    result = eval_expr(node.body)
                    return float(result)
                except Exception as e:
                    raise ValueError(f"计算错误: {str(e)}")
            
            self.mcp_client.register_tool(
                name="calculate",
                description="执行数学计算",
                handler=calculate,
                parameters={
                    "type": "object",
                    "properties": {
                        "expression": {
                            "type": "string",
                        "description": "要计算的数学表达式"
                    }
                },
                "required": ["expression"]
            }
        )
        
        # 统计实际注册的工具数量
        registered_count = 0
        if self.mcp_config.is_tool_enabled("get_current_time"):
            registered_count += 1
        if self.mcp_config.is_tool_enabled("calculate"):
            registered_count += 1
        
        debug_logger.log_info("MCPContextManager", "默认MCP工具已注册", {"count": registered_count})
    
    def _register_default_resources(self):
        """
        注册默认MCP资源（仅注册启用的资源）
        """
        registered_count = 0
        
        # 系统信息资源
        if self.mcp_config.is_resource_enabled("system://info"):
            self.mcp_client.register_resource(
                uri="system://info",
                name="系统信息",
                description="Neo Agent系统基本信息",
                mime_type="application/json"
            )
            registered_count += 1
        
        # 角色信息资源
        if self.mcp_config.is_resource_enabled("character://profile"):
            self.mcp_client.register_resource(
                uri="character://profile",
                name="角色档案",
                description="智能体角色设定信息",
                mime_type="application/json"
            )
            registered_count += 1
        
        debug_logger.log_info("MCPContextManager", "默认MCP资源已注册", {"count": registered_count})
    
    def _register_default_prompts(self):
        """
        注册默认MCP提示词模板（仅注册启用的提示词）
        """
        registered_count = 0
        
        # 情感分析提示词
        if self.mcp_config.is_prompt_enabled("emotion_analysis"):
            self.mcp_client.register_prompt(
                name="emotion_analysis",
                description="情感分析提示词模板",
                template="请分析以下对话的情感倾向：\n{conversation}\n\n请提供详细的情感分析。",
                arguments=[
                    {
                        "name": "conversation",
                        "description": "要分析的对话内容",
                        "required": True
                    }
                ]
            )
            registered_count += 1
        
        # 任务规划提示词
        if self.mcp_config.is_prompt_enabled("task_planning"):
            self.mcp_client.register_prompt(
                name="task_planning",
                description="任务规划提示词模板",
                template="请为以下任务制定详细的执行计划：\n任务：{task}\n\n请列出具体的步骤。",
                arguments=[
                    {
                        "name": "task",
                        "description": "要规划的任务描述",
                        "required": True
                    }
                ]
            )
            registered_count += 1
        
        debug_logger.log_info("MCPContextManager", "默认MCP提示词已注册", {"count": registered_count})
    
    def register_tool(self, name: str, description: str, handler, parameters: Optional[Dict[str, Any]] = None):
        """
        注册自定义MCP工具
        
        Args:
            name: 工具名称
            description: 工具描述
            handler: 工具处理函数
            parameters: 工具参数定义
        """
        if not self.enable_mcp:
            debug_logger.log_info("MCPContextManager", "MCP未启用，跳过工具注册", {"tool": name})
            return
        
        self.mcp_client.register_tool(name, description, handler, parameters)
    
    def register_resource(self, uri: str, name: str, description: str, mime_type: str = "text/plain"):
        """
        注册自定义MCP资源
        
        Args:
            uri: 资源URI
            name: 资源名称
            description: 资源描述
            mime_type: MIME类型
        """
        if not self.enable_mcp:
            debug_logger.log_info("MCPContextManager", "MCP未启用，跳过资源注册", {"uri": uri})
            return
        
        self.mcp_client.register_resource(uri, name, description, mime_type)
    
    def register_prompt(self, name: str, description: str, template: str, arguments: Optional[List[Dict[str, Any]]] = None):
        """
        注册自定义MCP提示词
        
        Args:
            name: 提示词名称
            description: 提示词描述
            template: 提示词模板
            arguments: 模板参数列表
        """
        if not self.enable_mcp:
            debug_logger.log_info("MCPContextManager", "MCP未启用，跳过提示词注册", {"prompt": name})
            return
        
        self.mcp_client.register_prompt(name, description, template, arguments)
    
    def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        调用MCP工具
        
        Args:
            tool_name: 工具名称
            arguments: 工具参数
            
        Returns:
            工具执行结果
        """
        if not self.enable_mcp:
            return {
                "success": False,
                "error": "MCP未启用"
            }
        
        return self.mcp_client.call_tool(tool_name, arguments)
    
    def get_resource(self, uri: str) -> Dict[str, Any]:
        """
        获取MCP资源
        
        Args:
            uri: 资源URI
            
        Returns:
            资源内容
        """
        if not self.enable_mcp:
            return {
                "success": False,
                "error": "MCP未启用"
            }
        
        return self.mcp_client.get_resource(uri)
    
    def get_prompt(self, name: str, arguments: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        获取MCP提示词
        
        Args:
            name: 提示词名称
            arguments: 模板参数
            
        Returns:
            渲染后的提示词
        """
        if not self.enable_mcp:
            return {
                "success": False,
                "error": "MCP未启用"
            }
        
        return self.mcp_client.get_prompt(name, arguments)
    
    def add_context(self, context: Dict[str, Any]):
        """
        添加上下文信息
        
        Args:
            context: 上下文信息字典
        """
        if not self.enable_mcp:
            return
        
        self.mcp_client.add_context(context)
    
    def get_contexts(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        获取上下文信息
        
        Args:
            limit: 限制返回数量
            
        Returns:
            上下文信息列表
        """
        if not self.enable_mcp:
            return []
        
        return self.mcp_client.get_contexts(limit)
    
    def clear_contexts(self):
        """
        清除所有上下文信息
        """
        if not self.enable_mcp:
            return
        
        self.mcp_client.clear_contexts()
    
    def get_available_tools(self) -> List[Dict[str, Any]]:
        """
        获取可用工具列表
        
        Returns:
            工具列表
        """
        if not self.enable_mcp:
            return []
        
        return self.mcp_client.list_tools()
    
    def get_available_resources(self) -> List[Dict[str, Any]]:
        """
        获取可用资源列表
        
        Returns:
            资源列表
        """
        if not self.enable_mcp:
            return []
        
        return self.mcp_client.list_resources()
    
    def get_available_prompts(self) -> List[Dict[str, Any]]:
        """
        获取可用提示词列表
        
        Returns:
            提示词列表
        """
        if not self.enable_mcp:
            return []
        
        return self.mcp_client.list_prompts()
    
    def get_mcp_info(self) -> Dict[str, Any]:
        """
        获取MCP信息
        
        Returns:
            MCP状态和配置信息
        """
        if not self.enable_mcp:
            return {
                "enabled": False,
                "message": "MCP功能未启用"
            }
        
        server_info = self.mcp_client.get_server_info()
        
        return {
            "enabled": True,
            "server_info": server_info,
            "tools_count": len(self.mcp_client.tools),
            "resources_count": len(self.mcp_client.resources),
            "prompts_count": len(self.mcp_client.prompts),
            "contexts_count": len(self.mcp_client.contexts)
        }
