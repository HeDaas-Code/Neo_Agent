"""
MCP客户端模块
实现Model Context Protocol (MCP)客户端，支持与MCP服务器通信
"""

import json
import uuid
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime
from debug_logger import get_debug_logger

# 获取debug日志记录器
debug_logger = get_debug_logger()


class MCPClient:
    """
    MCP客户端
    实现基于Model Context Protocol的上下文管理和工具调用
    
    警告：这是一个实验性功能，API可能会在未来版本中发生变化。
    """
    
    def __init__(self, max_contexts: int = 100):
        """
        初始化MCP客户端
        
        Args:
            max_contexts: 最大上下文数量限制
        """
        self.tools: Dict[str, Dict[str, Any]] = {}
        self.resources: Dict[str, Dict[str, Any]] = {}
        self.prompts: Dict[str, Dict[str, Any]] = {}
        self.session_id = str(uuid.uuid4())
        self.contexts: List[Dict[str, Any]] = []
        self.max_contexts = max_contexts
        
        debug_logger.log_info("MCPClient", "MCP客户端已初始化", {
            "session_id": self.session_id,
            "max_contexts": max_contexts
        })
    
    def register_tool(
        self,
        name: str,
        description: str,
        handler: Callable[[Dict[str, Any]], Any],
        parameters: Optional[Dict[str, Any]] = None
    ):
        """
        注册MCP工具
        
        Args:
            name: 工具名称
            description: 工具描述
            handler: 工具处理函数
            parameters: 工具参数定义（JSON Schema格式）
        """
        self.tools[name] = {
            "name": name,
            "description": description,
            "handler": handler,
            "parameters": parameters or {},
            "registered_at": datetime.now().isoformat()
        }
        
        debug_logger.log_info("MCPClient", f"MCP工具已注册: {name}", {"description": description})
    
    def register_resource(
        self,
        uri: str,
        name: str,
        description: str,
        mime_type: str = "text/plain"
    ):
        """
        注册MCP资源
        
        Args:
            uri: 资源URI
            name: 资源名称
            description: 资源描述
            mime_type: MIME类型
        """
        self.resources[uri] = {
            "uri": uri,
            "name": name,
            "description": description,
            "mimeType": mime_type,
            "registered_at": datetime.now().isoformat()
        }
        
        debug_logger.log_info("MCPClient", f"MCP资源已注册: {uri}", {"name": name})
    
    def register_prompt(
        self,
        name: str,
        description: str,
        template: str,
        arguments: Optional[List[Dict[str, Any]]] = None
    ):
        """
        注册MCP提示词模板
        
        Args:
            name: 提示词名称
            description: 提示词描述
            template: 提示词模板
            arguments: 模板参数列表
        """
        self.prompts[name] = {
            "name": name,
            "description": description,
            "template": template,
            "arguments": arguments or [],
            "registered_at": datetime.now().isoformat()
        }
        
        debug_logger.log_info("MCPClient", f"MCP提示词已注册: {name}", {"description": description})
    
    def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        调用MCP工具
        
        Args:
            tool_name: 工具名称
            arguments: 工具参数
            
        Returns:
            工具执行结果
        """
        if tool_name not in self.tools:
            error_msg = f"工具未找到: {tool_name}"
            debug_logger.log_error("MCPClient", error_msg, None)
            return {
                "success": False,
                "error": error_msg
            }
        
        tool = self.tools[tool_name]
        
        try:
            debug_logger.log_info("MCPClient", f"调用MCP工具: {tool_name}", {"arguments": arguments})
            
            # 调用工具处理函数
            result = tool["handler"](arguments)
            
            debug_logger.log_info("MCPClient", f"MCP工具执行成功: {tool_name}", {"result": result})
            
            return {
                "success": True,
                "result": result
            }
        except Exception as e:
            error_msg = "工具执行失败，请稍后重试"
            debug_logger.log_error("MCPClient", f"工具执行失败: {tool_name}", e)
            return {
                "success": False,
                "error": error_msg
            }
    
    def get_resource(self, uri: str) -> Dict[str, Any]:
        """
        获取MCP资源
        
        Args:
            uri: 资源URI
            
        Returns:
            资源内容
        """
        if uri not in self.resources:
            error_msg = f"资源未找到: {uri}"
            debug_logger.log_error("MCPClient", error_msg, None)
            return {
                "success": False,
                "error": error_msg
            }
        
        resource = self.resources[uri]
        
        debug_logger.log_info("MCPClient", f"获取MCP资源: {uri}", {"resource": resource})
        
        return {
            "success": True,
            "resource": resource
        }
    
    def get_prompt(self, name: str, arguments: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        获取MCP提示词
        
        Args:
            name: 提示词名称
            arguments: 模板参数
            
        Returns:
            渲染后的提示词
        """
        if name not in self.prompts:
            error_msg = f"提示词未找到: {name}"
            debug_logger.log_error("MCPClient", error_msg, None)
            return {
                "success": False,
                "error": error_msg
            }
        
        prompt = self.prompts[name]
        template = prompt["template"]
        
        # 简单的模板渲染
        if arguments:
            try:
                rendered = template.format(**arguments)
            except Exception as e:
                error_msg = "提示词渲染失败，请检查参数"
                debug_logger.log_error("MCPClient", f"提示词渲染失败: {name}", e)
                return {
                    "success": False,
                    "error": error_msg
                }
        else:
            rendered = template
        
        debug_logger.log_info("MCPClient", f"获取MCP提示词: {name}", {"rendered": rendered})
        
        return {
            "success": True,
            "prompt": rendered
        }
    
    def add_context(self, context: Dict[str, Any]):
        """
        添加上下文信息到MCP会话
        
        自动维护上下文数量在MAX_CONTEXTS限制内，超过时移除最早的上下文
        
        Args:
            context: 上下文信息字典
        """
        context_with_meta = {
            "content": context,
            "timestamp": datetime.now().isoformat(),
            "context_id": str(uuid.uuid4())
        }
        
        self.contexts.append(context_with_meta)
        
        # 自动清理旧上下文，保持数量在限制内
        if len(self.contexts) > self.max_contexts:
            removed = self.contexts.pop(0)
            debug_logger.log_info("MCPClient", "移除旧上下文", {
                "removed_id": removed["context_id"],
                "current_count": len(self.contexts)
            })
        
        debug_logger.log_info("MCPClient", "MCP上下文已添加", {"context_id": context_with_meta["context_id"]})
    
    def get_contexts(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        获取上下文信息
        
        Args:
            limit: 限制返回数量
            
        Returns:
            上下文信息列表
        """
        if limit:
            return self.contexts[-limit:]
        return self.contexts
    
    def clear_contexts(self):
        """
        清除所有上下文信息
        """
        self.contexts.clear()
        debug_logger.log_info("MCPClient", "MCP上下文已清除", {})
    
    def list_tools(self) -> List[Dict[str, Any]]:
        """
        列出所有已注册的工具
        
        Returns:
            工具列表
        """
        return [
            {
                "name": tool["name"],
                "description": tool["description"],
                "parameters": tool["parameters"]
            }
            for tool in self.tools.values()
        ]
    
    def list_resources(self) -> List[Dict[str, Any]]:
        """
        列出所有已注册的资源
        
        Returns:
            资源列表
        """
        return [
            {
                "uri": resource["uri"],
                "name": resource["name"],
                "description": resource["description"],
                "mimeType": resource["mimeType"]
            }
            for resource in self.resources.values()
        ]
    
    def list_prompts(self) -> List[Dict[str, Any]]:
        """
        列出所有已注册的提示词
        
        Returns:
            提示词列表
        """
        return [
            {
                "name": prompt["name"],
                "description": prompt["description"],
                "arguments": prompt["arguments"]
            }
            for prompt in self.prompts.values()
        ]
    
    def get_server_info(self) -> Dict[str, Any]:
        """
        获取MCP服务器信息
        
        Returns:
            服务器信息
        """
        return {
            "name": "Neo Agent MCP Server",
            "version": "0.1.0",
            "protocol_version": "2024-11-05",
            "capabilities": {
                "tools": len(self.tools) > 0,
                "resources": len(self.resources) > 0,
                "prompts": len(self.prompts) > 0
            },
            "session_id": self.session_id
        }
