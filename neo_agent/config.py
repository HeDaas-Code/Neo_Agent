"""配置管理"""
import json
from pathlib import Path
from typing import Optional, Dict, Any


class Config:
    """全局配置管理器"""
    
    def __init__(self, config_path: Optional[Path] = None):
        self.config_path = config_path or (Path.home() / ".neo_agent" / "config.json")
        self._data: Dict[str, Any] = {}
        self.load()
    
    def load(self):
        """加载配置"""
        if self.config_path.exists():
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    self._data = json.load(f)
            except (json.JSONDecodeError, IOError):
                self._data = {}
        else:
            self._data = self._default_config()
    
    def save(self):
        """保存配置"""
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(self._data, f, indent=2, ensure_ascii=False)
    
    def _default_config(self) -> Dict[str, Any]:
        """默认配置"""
        return {
            "llm": {
                "provider": "openai",  # openai | siliconflow
                "model": "gpt-4o-mini",
                "api_key": "",
                "base_url": "",
                "temperature": 0.7,
            },
            "storage": {
                "vdisk_path": str(Path.home() / ".neo_agent" / "data.vdisk"),
            },
            "system": {
                "debug": False,
                "timezone": "Asia/Shanghai",
                "daily_plan_time": "00:05",
            }
        }
    
    def get(self, key: str, default: Any = None) -> Any:
        """获取配置项（支持点号路径，如 'llm.model'）"""
        parts = key.split(".")
        value = self._data
        for part in parts:
            if isinstance(value, dict) and part in value:
                value = value[part]
            else:
                return default
        return value
    
    def set(self, key: str, value: Any):
        """设置配置项（支持点号路径）"""
        parts = key.split(".")
        target = self._data
        for part in parts[:-1]:
            if part not in target:
                target[part] = {}
            target = target[part]
        target[parts[-1]] = value
    
    def get_llm_config(self) -> Dict[str, Any]:
        """获取 LLM 配置"""
        return self._data.get("llm", self._default_config()["llm"])
    
    def is_debug(self) -> bool:
        """是否启用 Debug 模式"""
        return self.get("system.debug", False)
    
    def set_debug(self, enabled: bool):
        """设置 Debug 模式"""
        self.set("system.debug", enabled)
        self.save()


# 全局单例
_config_instance: Optional[Config] = None

def get_config() -> Config:
    """获取全局配置实例"""
    global _config_instance
    if _config_instance is None:
        _config_instance = Config()
    return _config_instance
