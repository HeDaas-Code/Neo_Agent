"""
Cortex Model Config - v4.0 多层模型配置

位于 src/cortex/config/，属于大脑皮层（Cortex）的认知基础设施。

管理不同类型任务使用的不同模型配置。

注意：本模块从 v3.1.0 的 src.core.model_config 迁移而来，逻辑保持一致。
"""

from __future__ import annotations

import os
from enum import Enum
from typing import Any, Dict, Optional
from dotenv import load_dotenv

from src.cortex.providers import registry as llm_providers

load_dotenv()


class ModelType(Enum):
    """模型类型枚举"""

    MAIN = "main"  # 主模型：处理主要对话和复杂推理
    TOOL = "tool"  # 小模型：处理工具调用和轻量级任务
    VISION = "vision"  # 多模态模型：处理视觉和多模态任务


class ModelConfig:
    """
    模型配置类
    提供多层模型架构的配置管理
    """

    def __init__(self):
        """初始化模型配置"""
        try:
            self.api_url = llm_providers.resolve_base_url(llm_providers.resolve_provider())
        except Exception:
            # 启动期 LLM_BASE_URL 缺失时（custom）不要阻塞；保留空串
            self.api_url = ""
        self.api_key = llm_providers.resolve_api_key()

        # 主模型配置
        self.main_model = {
            'name': os.getenv('MAIN_MODEL_NAME', os.getenv('MODEL_NAME', os.getenv(
                'LLM_MODEL_NAME', llm_providers.resolve_model_name(llm_providers.resolve_provider())))),
            'temperature': float(os.getenv('MAIN_MODEL_TEMPERATURE', os.getenv('TEMPERATURE', '0.8'))),
            'max_tokens': int(os.getenv('MAIN_MODEL_MAX_TOKENS', os.getenv('MAX_TOKENS', '2000'))),
            'base_url': os.getenv('MAIN_MODEL_BASE_URL'),
        }

        # 小模型配置（工具级任务）
        self.tool_model = {
            'name': os.getenv('TOOL_MODEL_NAME', 'zai-org/GLM-4.6V'),
            'temperature': float(os.getenv('TOOL_MODEL_TEMPERATURE', '0.3')),
            'max_tokens': int(os.getenv('TOOL_MODEL_MAX_TOKENS', '500')),
            'base_url': os.getenv('TOOL_MODEL_BASE_URL'),
        }

        # 多模态模型配置
        self.vision_model = {
            'name': os.getenv('VISION_MODEL_NAME', 'Qwen/Qwen3-VL-32B-Instruct'),
            'temperature': float(os.getenv('VISION_MODEL_TEMPERATURE', '0.5')),
            'max_tokens': int(os.getenv('VISION_MODEL_MAX_TOKENS', '1000')),
            'base_url': os.getenv('VISION_MODEL_BASE_URL'),
        }

        # 视觉工具LLM配置（向后兼容）
        self.vision_llm_temperature = float(os.getenv('VISION_LLM_TEMPERATURE', '0.3'))
        self.vision_llm_max_tokens = int(os.getenv('VISION_LLM_MAX_TOKENS', '10'))
        self.vision_llm_timeout = int(os.getenv('VISION_LLM_TIMEOUT', '10'))

        # NPS工具系统LLM配置（向后兼容）
        self.nps_llm_temperature = float(os.getenv('NPS_LLM_TEMPERATURE', '0.3'))
        self.nps_llm_max_tokens = int(os.getenv('NPS_LLM_MAX_TOKENS', '100'))
        self.nps_llm_timeout = int(os.getenv('NPS_LLM_TIMEOUT', '10'))

    def get_model_config(self, model_type: ModelType) -> Dict[str, Any]:
        """
        获取指定类型的模型配置
        """
        if model_type == ModelType.MAIN:
            return self.main_model.copy()
        elif model_type == ModelType.TOOL:
            return self.tool_model.copy()
        elif model_type == ModelType.VISION:
            return self.vision_model.copy()
        else:
            return self.main_model.copy()

    def get_api_config(self) -> Dict[str, str]:
        """
        获取API配置
        """
        return {
            'api_key': self.api_key,
            'api_url': self.api_url,
        }

    def is_valid(self) -> bool:
        """
        检查配置是否有效
        """
        if not self.api_key:
            return False
        return self.api_key not in ('your-api-key', '')

    def get_summary(self) -> str:
        """
        获取配置摘要
        """
        try:
            provider = llm_providers.resolve_provider()
        except Exception:
            provider = "unknown"
        return f"""多层模型配置:
  provider: {provider}
  主模型: {self.main_model['name']}
  工具模型: {self.tool_model['name']}
  多模态模型: {self.vision_model['name']}
  API地址: {self.api_url}"""


_global_config: Optional[ModelConfig] = None


def get_model_config() -> ModelConfig:
    """
    获取全局模型配置实例（单例模式）
    """
    global _global_config
    if _global_config is None:
        _global_config = ModelConfig()
    return _global_config


__all__ = ["ModelType", "ModelConfig", "get_model_config"]
