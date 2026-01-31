"""
MCP配置管理模块
独立于.env文件的MCP配置管理
"""

import os
import json
from typing import Dict, Any, Optional
from datetime import datetime
from debug_logger import get_debug_logger

# 获取debug日志记录器
debug_logger = get_debug_logger()


class MCPConfig:
    """
    MCP配置管理器
    使用JSON文件存储配置，独立于.env文件
    """
    
    DEFAULT_CONFIG = {
        "enabled": False,
        "tools": {
            "get_current_time": {"enabled": True},
            "calculate": {"enabled": True}
        },
        "resources": {
            "system://info": {"enabled": True},
            "character://profile": {"enabled": True}
        },
        "prompts": {
            "emotion_analysis": {"enabled": True},
            "task_planning": {"enabled": True}
        },
        "context": {
            "max_contexts": 100,
            "auto_cleanup": True
        },
        "created_at": None,
        "updated_at": None
    }
    
    def __init__(self, config_file: str = "mcp_config.json"):
        """
        初始化MCP配置管理器
        
        Args:
            config_file: 配置文件路径
        """
        self.config_file = config_file
        self.config = self._load_config()
        
        debug_logger.log_info("MCPConfig", "MCP配置管理器已初始化", {
            "config_file": config_file,
            "enabled": self.config["enabled"]
        })
    
    def _load_config(self) -> Dict[str, Any]:
        """
        从文件加载配置
        
        Returns:
            配置字典
        """
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    
                # 合并默认配置（补充缺失的键）
                merged_config = self.DEFAULT_CONFIG.copy()
                merged_config.update(config)
                
                debug_logger.log_info("MCPConfig", "配置加载成功", {
                    "file": self.config_file
                })
                
                return merged_config
            except Exception as e:
                debug_logger.log_error("MCPConfig", f"配置加载失败: {str(e)}", e)
                return self._create_default_config()
        else:
            return self._create_default_config()
    
    def _create_default_config(self) -> Dict[str, Any]:
        """
        创建默认配置
        
        Returns:
            默认配置字典
        """
        config = self.DEFAULT_CONFIG.copy()
        config["created_at"] = datetime.now().isoformat()
        config["updated_at"] = datetime.now().isoformat()
        
        self._save_config(config)
        
        debug_logger.log_info("MCPConfig", "创建默认配置", {
            "file": self.config_file
        })
        
        return config
    
    def _save_config(self, config: Optional[Dict[str, Any]] = None):
        """
        保存配置到文件
        
        Args:
            config: 要保存的配置字典，如果为None则保存当前配置
        """
        if config is None:
            config = self.config
        
        config["updated_at"] = datetime.now().isoformat()
        
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
            
            debug_logger.log_info("MCPConfig", "配置保存成功", {
                "file": self.config_file
            })
        except Exception as e:
            debug_logger.log_error("MCPConfig", f"配置保存失败: {str(e)}", e)
    
    def is_enabled(self) -> bool:
        """
        检查MCP是否启用
        
        Returns:
            是否启用
        """
        return self.config.get("enabled", False)
    
    def set_enabled(self, enabled: bool):
        """
        设置MCP启用状态
        
        Args:
            enabled: 是否启用
        """
        self.config["enabled"] = enabled
        self._save_config()
        
        debug_logger.log_info("MCPConfig", f"MCP状态已更新", {
            "enabled": enabled
        })
    
    def is_tool_enabled(self, tool_name: str) -> bool:
        """
        检查工具是否启用
        
        Args:
            tool_name: 工具名称
            
        Returns:
            是否启用
        """
        return self.config.get("tools", {}).get(tool_name, {}).get("enabled", True)
    
    def set_tool_enabled(self, tool_name: str, enabled: bool):
        """
        设置工具启用状态
        
        Args:
            tool_name: 工具名称
            enabled: 是否启用
        """
        if "tools" not in self.config:
            self.config["tools"] = {}
        
        if tool_name not in self.config["tools"]:
            self.config["tools"][tool_name] = {}
        
        self.config["tools"][tool_name]["enabled"] = enabled
        self._save_config()
        
        debug_logger.log_info("MCPConfig", f"工具状态已更新", {
            "tool": tool_name,
            "enabled": enabled
        })
    
    def is_resource_enabled(self, uri: str) -> bool:
        """
        检查资源是否启用
        
        Args:
            uri: 资源URI
            
        Returns:
            是否启用
        """
        return self.config.get("resources", {}).get(uri, {}).get("enabled", True)
    
    def set_resource_enabled(self, uri: str, enabled: bool):
        """
        设置资源启用状态
        
        Args:
            uri: 资源URI
            enabled: 是否启用
        """
        if "resources" not in self.config:
            self.config["resources"] = {}
        
        if uri not in self.config["resources"]:
            self.config["resources"][uri] = {}
        
        self.config["resources"][uri]["enabled"] = enabled
        self._save_config()
        
        debug_logger.log_info("MCPConfig", f"资源状态已更新", {
            "uri": uri,
            "enabled": enabled
        })
    
    def is_prompt_enabled(self, prompt_name: str) -> bool:
        """
        检查提示词是否启用
        
        Args:
            prompt_name: 提示词名称
            
        Returns:
            是否启用
        """
        return self.config.get("prompts", {}).get(prompt_name, {}).get("enabled", True)
    
    def set_prompt_enabled(self, prompt_name: str, enabled: bool):
        """
        设置提示词启用状态
        
        Args:
            prompt_name: 提示词名称
            enabled: 是否启用
        """
        if "prompts" not in self.config:
            self.config["prompts"] = {}
        
        if prompt_name not in self.config["prompts"]:
            self.config["prompts"][prompt_name] = {}
        
        self.config["prompts"][prompt_name]["enabled"] = enabled
        self._save_config()
        
        debug_logger.log_info("MCPConfig", f"提示词状态已更新", {
            "prompt": prompt_name,
            "enabled": enabled
        })
    
    def get_max_contexts(self) -> int:
        """
        获取最大上下文数量
        
        Returns:
            最大上下文数量
        """
        return self.config.get("context", {}).get("max_contexts", 100)
    
    def set_max_contexts(self, max_contexts: int):
        """
        设置最大上下文数量
        
        Args:
            max_contexts: 最大上下文数量
        """
        if "context" not in self.config:
            self.config["context"] = {}
        
        self.config["context"]["max_contexts"] = max_contexts
        self._save_config()
        
        debug_logger.log_info("MCPConfig", f"最大上下文数量已更新", {
            "max_contexts": max_contexts
        })
    
    def get_config(self) -> Dict[str, Any]:
        """
        获取完整配置
        
        Returns:
            配置字典
        """
        return self.config.copy()
    
    def reset_to_default(self):
        """
        重置为默认配置
        """
        self.config = self._create_default_config()
        
        debug_logger.log_info("MCPConfig", "配置已重置为默认值", {})
