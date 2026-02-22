"""
NPS插件配置管理模块
负责管理每个NPS插件的独立配置
"""

import os
import json
from typing import Dict, Any, Optional
from pathlib import Path
from src.tools.debug_logger import get_debug_logger

# 获取debug日志记录器
debug_logger = get_debug_logger()

# 配置文件目录
CONFIG_DIR = Path("configs/nps_plugins")


class NPSConfigManager:
    """
    NPS插件配置管理器
    负责读取、写入和管理插件的独立配置
    """
    
    def __init__(self, config_dir: str = None):
        """
        初始化配置管理器
        
        Args:
            config_dir: 配置文件目录路径，默认为 configs/nps_plugins
        """
        self.config_dir = Path(config_dir) if config_dir else CONFIG_DIR
        self.config_file = self.config_dir / "plugins_config.json"
        self._configs = {}
        
        # 确保配置目录存在
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        # 加载配置
        self.load_configs()
    
    def load_configs(self):
        """从文件加载所有插件配置"""
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    self._configs = json.load(f)
                debug_logger.log_module('NPSConfigManager', '配置加载成功',
                                      {'plugins_count': len(self._configs)})
            else:
                self._configs = {}
                debug_logger.log_info('NPSConfigManager', '配置文件不存在，使用默认配置')
        except Exception as e:
            debug_logger.log_error('NPSConfigManager', '加载配置失败', e)
            self._configs = {}
    
    def save_configs(self) -> bool:
        """保存所有插件配置到文件"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self._configs, f, indent=4, ensure_ascii=False)
            debug_logger.log_info('NPSConfigManager', '配置保存成功',
                                {'file': str(self.config_file)})
            return True
        except Exception as e:
            debug_logger.log_error('NPSConfigManager', '保存配置失败', e)
            return False
    
    def get_plugin_config(self, tool_id: str) -> Dict[str, Any]:
        """
        获取指定插件的配置
        
        Args:
            tool_id: 插件ID
            
        Returns:
            插件配置字典，如果不存在则返回空字典
        """
        return self._configs.get(tool_id, {})
    
    def set_plugin_config(self, tool_id: str, config: Dict[str, Any]) -> bool:
        """
        设置指定插件的配置
        
        Args:
            tool_id: 插件ID
            config: 配置字典
            
        Returns:
            是否成功
        """
        try:
            self._configs[tool_id] = config
            return self.save_configs()
        except Exception as e:
            debug_logger.log_error('NPSConfigManager', f'设置插件配置失败: {tool_id}', e)
            return False
    
    def update_plugin_config(self, tool_id: str, updates: Dict[str, Any]) -> bool:
        """
        更新指定插件的部分配置
        
        Args:
            tool_id: 插件ID
            updates: 要更新的配置项
            
        Returns:
            是否成功
        """
        try:
            if tool_id not in self._configs:
                self._configs[tool_id] = {}
            
            self._configs[tool_id].update(updates)
            return self.save_configs()
        except Exception as e:
            debug_logger.log_error('NPSConfigManager', f'更新插件配置失败: {tool_id}', e)
            return False
    
    def delete_plugin_config(self, tool_id: str) -> bool:
        """
        删除指定插件的配置
        
        Args:
            tool_id: 插件ID
            
        Returns:
            是否成功
        """
        try:
            if tool_id in self._configs:
                del self._configs[tool_id]
                return self.save_configs()
            return True
        except Exception as e:
            debug_logger.log_error('NPSConfigManager', f'删除插件配置失败: {tool_id}', e)
            return False
    
    def get_config_value(self, tool_id: str, key: str, default: Any = None) -> Any:
        """
        获取插件配置中的特定值
        
        Args:
            tool_id: 插件ID
            key: 配置键名
            default: 默认值
            
        Returns:
            配置值
        """
        config = self.get_plugin_config(tool_id)
        value = config.get(key, default)
        
        # 如果值是环境变量引用，尝试从环境变量获取
        if isinstance(value, str) and value.startswith('${') and value.endswith('}'):
            env_var = value[2:-1]
            return os.getenv(env_var, default)
        
        return value
    
    def set_config_value(self, tool_id: str, key: str, value: Any) -> bool:
        """
        设置插件配置中的特定值
        
        Args:
            tool_id: 插件ID
            key: 配置键名
            value: 配置值
            
        Returns:
            是否成功
        """
        return self.update_plugin_config(tool_id, {key: value})
    
    def get_all_configs(self) -> Dict[str, Dict[str, Any]]:
        """
        获取所有插件的配置
        
        Returns:
            所有配置的字典
        """
        return self._configs.copy()
    
    def export_config(self, tool_id: str, output_file: str) -> bool:
        """
        导出插件配置到文件
        
        Args:
            tool_id: 插件ID
            output_file: 输出文件路径
            
        Returns:
            是否成功
        """
        try:
            config = self.get_plugin_config(tool_id)
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=4, ensure_ascii=False)
            return True
        except Exception as e:
            debug_logger.log_error('NPSConfigManager', f'导出配置失败: {tool_id}', e)
            return False
    
    def import_config(self, tool_id: str, input_file: str) -> bool:
        """
        从文件导入插件配置
        
        Args:
            tool_id: 插件ID
            input_file: 输入文件路径
            
        Returns:
            是否成功
        """
        try:
            with open(input_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
            return self.set_plugin_config(tool_id, config)
        except Exception as e:
            debug_logger.log_error('NPSConfigManager', f'导入配置失败: {tool_id}', e)
            return False
