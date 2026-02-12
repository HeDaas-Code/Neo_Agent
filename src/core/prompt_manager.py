"""
提示词管理模块
负责加载和管理markdown格式的提示词模板
参考SillyTavern的提示词工程，支持模块化、可配置的提示词系统
"""

import os
from typing import Dict, Any, Optional
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()


class PromptManager:
    """
    提示词管理器
    负责加载、解析和渲染markdown格式的提示词模板
    """

    def __init__(self, prompts_dir: str = None):
        """
        初始化提示词管理器

        Args:
            prompts_dir: 提示词目录路径，默认为项目根目录下的prompts文件夹
        """
        if prompts_dir is None:
            # 获取项目根目录
            current_file = Path(__file__).resolve()
            project_root = current_file.parent.parent.parent
            prompts_dir = project_root / "prompts"

        self.prompts_dir = Path(prompts_dir)
        self._cache: Dict[str, str] = {}

        # 验证目录存在
        if not self.prompts_dir.exists():
            raise FileNotFoundError(f"提示词目录不存在: {self.prompts_dir}")

    def load_prompt(self, category: str, filename: str, use_cache: bool = True) -> str:
        """
        加载指定的提示词模板

        Args:
            category: 提示词类别（character/system/task/worldview）
            filename: 文件名（不含.md后缀）
            use_cache: 是否使用缓存

        Returns:
            提示词内容

        Raises:
            FileNotFoundError: 如果文件不存在
        """
        cache_key = f"{category}/{filename}"

        # 检查缓存
        if use_cache and cache_key in self._cache:
            return self._cache[cache_key]

        # 构建文件路径
        file_path = self.prompts_dir / category / f"{filename}.md"

        if not file_path.exists():
            raise FileNotFoundError(f"提示词文件不存在: {file_path}")

        # 读取文件
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # 缓存内容
        if use_cache:
            self._cache[cache_key] = content

        return content

    def render_prompt(self, template: str, variables: Dict[str, Any]) -> str:
        """
        渲染提示词模板，替换变量

        Args:
            template: 提示词模板
            variables: 变量字典

        Returns:
            渲染后的提示词
        """
        result = template

        # 替换所有变量
        for key, value in variables.items():
            placeholder = f"{{{key}}}"
            # 将None转换为空字符串
            value_str = str(value) if value is not None else ""
            result = result.replace(placeholder, value_str)

        return result

    def load_and_render(
        self,
        category: str,
        filename: str,
        variables: Dict[str, Any],
        use_cache: bool = True
    ) -> str:
        """
        加载并渲染提示词模板

        Args:
            category: 提示词类别
            filename: 文件名
            variables: 变量字典
            use_cache: 是否使用缓存

        Returns:
            渲染后的提示词
        """
        template = self.load_prompt(category, filename, use_cache)
        return self.render_prompt(template, variables)

    def clear_cache(self):
        """清空缓存"""
        self._cache.clear()

    def reload_prompt(self, category: str, filename: str) -> str:
        """
        重新加载提示词（不使用缓存）

        Args:
            category: 提示词类别
            filename: 文件名

        Returns:
            提示词内容
        """
        cache_key = f"{category}/{filename}"
        if cache_key in self._cache:
            del self._cache[cache_key]

        return self.load_prompt(category, filename, use_cache=False)

    def get_character_prompt(
        self,
        character_name: str = None,
        character_data: Dict[str, Any] = None
    ) -> str:
        """
        获取角色提示词

        Args:
            character_name: 角色名称（用于查找自定义角色文件）
            character_data: 角色数据字典

        Returns:
            渲染后的角色提示词
        """
        # 确定使用哪个角色文件
        filename = os.getenv('CHARACTER_PROMPT_FILE', 'default_character')

        # 如果指定了角色名且存在对应文件，使用该文件
        if character_name:
            custom_path = self.prompts_dir / "character" / f"{character_name}.md"
            if custom_path.exists():
                filename = character_name

        # 准备变量
        variables = character_data or {}

        # 加载并渲染
        return self.load_and_render('character', filename, variables)

    def get_system_prompt(
        self,
        prompt_type: str,
        variables: Dict[str, Any] = None
    ) -> str:
        """
        获取系统提示词

        Args:
            prompt_type: 提示词类型（chat_system/emotion_analysis/knowledge_extraction/task_coordination）
            variables: 变量字典

        Returns:
            渲染后的系统提示词
        """
        variables = variables or {}
        return self.load_and_render('system', prompt_type, variables)

    def get_task_prompt(
        self,
        task_type: str,
        variables: Dict[str, Any] = None
    ) -> str:
        """
        获取任务提示词

        Args:
            task_type: 任务类型（sub_agent_task/schedule_intent）
            variables: 变量字典

        Returns:
            渲染后的任务提示词
        """
        variables = variables or {}
        return self.load_and_render('task', task_type, variables)

    def get_worldview_prompt(
        self,
        worldview_name: str = None,
        variables: Dict[str, Any] = None
    ) -> str:
        """
        获取世界观提示词

        Args:
            worldview_name: 世界观名称（用于查找自定义世界观文件）
            variables: 变量字典

        Returns:
            渲染后的世界观提示词
        """
        # 确定使用哪个世界观文件
        filename = os.getenv('WORLDVIEW_FILE', 'default_world')

        # 如果指定了世界观且存在对应文件，使用该文件
        if worldview_name:
            custom_path = self.prompts_dir / "worldview" / f"{worldview_name}.md"
            if custom_path.exists():
                filename = worldview_name

        variables = variables or {}
        return self.load_and_render('worldview', filename, variables)

    def list_prompts(self, category: str = None) -> Dict[str, list]:
        """
        列出所有可用的提示词文件

        Args:
            category: 如果指定，只列出该类别的文件

        Returns:
            提示词文件列表字典
        """
        result = {}

        categories = [category] if category else ['character', 'system', 'task', 'worldview']

        for cat in categories:
            cat_dir = self.prompts_dir / cat
            if cat_dir.exists():
                files = [f.stem for f in cat_dir.glob("*.md")]
                result[cat] = sorted(files)

        return result


# 创建全局实例
_global_prompt_manager: Optional[PromptManager] = None


def get_prompt_manager() -> PromptManager:
    """
    获取全局提示词管理器实例（单例模式）

    Returns:
        PromptManager实例
    """
    global _global_prompt_manager
    if _global_prompt_manager is None:
        _global_prompt_manager = PromptManager()
    return _global_prompt_manager
