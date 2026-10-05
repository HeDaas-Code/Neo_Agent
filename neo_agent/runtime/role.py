"""单角色服务 - 管理唯一活动角色"""
import uuid
from datetime import datetime
from typing import Optional

from ..storage.disk_store import DiskStore


# 预设角色：林依
DEFAULT_CHARACTER = {
    "id": "lin_yi_default",
    "name": "林依",
    "gender": "女",
    "age": 17,
    "personality": ["温柔", "善良", "有点害羞", "喜欢安静", "细心"],
    "interests": ["阅读", "音乐", "绘画", "散步"],
    "background": "一个普通的高中女生，喜欢安静的生活，有点内向但对朋友很真诚。喜欢在图书馆看书，偶尔会弹吉他。",
    "traits": {
        "openness": 0.7,
        "conscientiousness": 0.8,
        "extraversion": 0.3,
        "agreeableness": 0.9,
        "neuroticism": 0.4
    },
    "speaking_style": "温和礼貌，语气柔和，偶尔会有些害羞的停顿。不喜欢大声说话。",
    "world_view": "相信善良和真诚，认为每个人都有自己的闪光点。",
    "created_at": None,  # 将在初始化时设置
    "status": "active"
}


class SingleRoleService:
    """单角色服务 - 确保只有一个活动角色"""
    
    def __init__(self, store: DiskStore):
        self.store = store
        self._character_id: Optional[str] = None
        self._character: Optional[dict] = None
    
    def initialize(self) -> dict:
        """初始化角色系统 - 确保有且只有一个活动角色"""
        # 获取所有活动角色
        characters = self.store.characters(include_archived=False)
        
        if not characters:
            # 没有角色，创建预设角色
            return self._create_default_character()
        
        if len(characters) == 1:
            # 恰好一个角色，加载它
            self._character = characters[0]
            self._character_id = self._character["id"]
            return self._character
        
        # 多个角色，需要用户选择一个（这里暂时选第一个）
        # TODO: 在 TUI 中让用户选择
        self._character = characters[0]
        self._character_id = self._character["id"]
        
        # 归档其他角色
        for char in characters[1:]:
            self.store.archive_character(char["id"])
        
        return self._character
    
    def _create_default_character(self) -> dict:
        """创建预设角色"林依" """
        character = DEFAULT_CHARACTER.copy()
        character["id"] = f"lin_yi_{uuid.uuid4().hex[:8]}"
        character["created_at"] = datetime.now().isoformat()
        
        self.store.save_character(character["id"], character)
        
        self._character_id = character["id"]
        self._character = character
        
        return character
    
    def get_character(self) -> Optional[dict]:
        """获取当前活动角色"""
        if not self._character:
            # 尝试初始化
            return self.initialize()
        return self._character
    
    def update_character(self, updates: dict) -> dict:
        """更新角色信息（仅 Debug 模式）"""
        if not self._character_id:
            raise RuntimeError("No active character")
        
        # 合并更新
        character = self.get_character()
        character.update(updates)
        character["updated_at"] = datetime.now().isoformat()
        
        # 保存
        self.store.save_character(self._character_id, character)
        self._character = character
        
        return character
    
    def export_character(self) -> dict:
        """导出角色数据"""
        if not self._character:
            raise RuntimeError("No active character")
        return self._character.copy()
    
    def import_character(self, character_data: dict) -> dict:
        """导入角色数据（替换当前角色）"""
        # 归档当前角色
        if self._character_id:
            self.store.archive_character(self._character_id)
        
        # 创建新角色
        new_id = f"imported_{uuid.uuid4().hex[:8]}"
        character = character_data.copy()
        character["id"] = new_id
        character["created_at"] = datetime.now().isoformat()
        character["status"] = "active"
        
        self.store.save_character(new_id, character)
        
        self._character_id = new_id
        self._character = character
        
        return character
