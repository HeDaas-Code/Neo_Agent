#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ConfigManager - 统一配置管理器
负责加载和管理多个配置文件，支持环境变量覆盖和配置验证
"""

import json
import os
from typing import Dict, Any, Optional
from pathlib import Path


class ConfigManager:
    """配置管理器 - 单例模式"""
    
    _instance = None
    _config = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ConfigManager, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._config is None:
            self.load_config()
    
    def load_config(self, index_path: str = "./config/index.json") -> Dict[str, Any]:
        """加载所有配置文件"""
        try:
            # 加载索引文件
            with open(index_path, 'r', encoding='utf-8') as f:
                index_config = json.load(f)
            
            self._config = {
                'version': index_config.get('version', '1.0.0'),
                'description': index_config.get('description', '')
            }
            
            # 加载各个配置文件
            config_files = index_config.get('config_files', {})
            for config_name, config_info in config_files.items():
                config_path = config_info['path']
                is_required = config_info.get('required', True)
                
                try:
                    with open(config_path, 'r', encoding='utf-8') as f:
                        config_data = json.load(f)
                    self._config[config_name] = config_data
                except FileNotFoundError:
                    if is_required:
                        raise FileNotFoundError(f"必需的配置文件不存在: {config_path}")
                    else:
                        print(f"警告: 可选配置文件不存在: {config_path}")
                except json.JSONDecodeError as e:
                    raise ValueError(f"配置文件格式错误 {config_path}: {e}")
            
            # 应用环境变量覆盖
            self._apply_environment_overrides(index_config.get('environment_variables', {}))
            
            # 验证配置
            self._validate_config()
            
            return self._config
            
        except Exception as e:
            raise RuntimeError(f"配置加载失败: {e}")
    
    def _apply_environment_overrides(self, env_vars: Dict[str, Any]):
        """应用环境变量覆盖"""
        for env_var, env_info in env_vars.items():
            env_value = os.getenv(env_var)
            if env_value:
                if env_var == 'DEEPSEEK_API_KEY':
                    if 'model' in self._config:
                        self._config['model']['deepseek_api_key'] = env_value
                        print(f"使用环境变量覆盖API密钥")
    
    def _validate_config(self):
        """验证配置完整性"""
        required_sections = ['model', 'character', 'knowledge', 'game', 'memory']
        
        for section in required_sections:
            if section not in self._config:
                raise ValueError(f"缺少必需的配置节: {section}")
        
        # 验证模型配置
        model_config = self._config.get('model', {})
        required_model_fields = ['deepseek_api_key', 'api_base', 'model_name', 'embedding_model_name']
        for field in required_model_fields:
            if not model_config.get(field):
                raise ValueError(f"模型配置缺少必需字段: {field}")
        
        # 验证角色配置
        character_config = self._config.get('character', {})
        required_character_fields = ['name', 'role', 'personality']
        for field in required_character_fields:
            if not character_config.get(field):
                raise ValueError(f"角色配置缺少必需字段: {field}")
        
        # 验证内存配置
        memory_config = self._config.get('memory', {})
        if not memory_config.get('memory_db_path') or not memory_config.get('collection_name'):
            raise ValueError("内存配置缺少必需字段: memory_db_path 或 collection_name")
    
    def get(self, path: str, default: Any = None) -> Any:
        """获取配置值，支持点号路径访问"""
        if self._config is None:
            self.load_config()
        
        keys = path.split('.')
        value = self._config
        
        try:
            for key in keys:
                value = value[key]
            return value
        except (KeyError, TypeError):
            return default
    
    def get_all(self) -> Dict[str, Any]:
        """获取所有配置"""
        if self._config is None:
            self.load_config()
        return self._config.copy()
    
    def reload(self):
        """重新加载配置"""
        self._config = None
        self.load_config()
    
    def to_legacy_format(self) -> Dict[str, Any]:
        """转换为旧版config.json格式，保持向后兼容"""
        if self._config is None:
            self.load_config()
        
        legacy_config = {
            'model': self._config.get('model', {}),
            'memory': self._config.get('memory', {}),
            'character': self._config.get('character', {}),
            'knowledge': self._config.get('knowledge', {}),
            'game': self._config.get('game', {})
        }
        
        return legacy_config


# 全局配置实例
config_manager = ConfigManager()


def get_config() -> Dict[str, Any]:
    """获取配置的便捷函数"""
    return config_manager.to_legacy_format()


if __name__ == "__main__":
    # 测试配置管理器
    try:
        config = get_config()
        print("配置加载成功!")
        print(f"模型名称: {config['model']['model_name']}")
        print(f"角色名称: {config['character']['name']}")
        print(f"知识库节点数: {len(config['knowledge']['knowledge_base'])}")
        print(f"游戏事件数: {len(config['game']['events'])}")
    except Exception as e:
        print(f"配置加载失败: {e}")