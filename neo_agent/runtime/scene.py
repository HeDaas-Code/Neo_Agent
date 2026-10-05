"""场景服务 - 管理环境、地点和场景池"""
import uuid
from datetime import datetime
from typing import Optional

from ..storage.disk_store import DiskStore


# 初始环境
DEFAULT_ENVIRONMENT = {
    "id": "home_default",
    "name": "家",
    "type": "residence",
    "description": "温馨的小公寓，有客厅、卧室、厨房和阳台。",
    "areas": [
        {
            "id": "living_room",
            "name": "客厅",
            "description": "简洁舒适的客厅，有一个柔软的沙发和小书架。窗外能看到街景。",
            "objects": ["沙发", "书架", "茶几", "窗户"]
        },
        {
            "id": "bedroom",
            "name": "卧室",
            "description": "安静的卧室，床上铺着浅色的床单，书桌上放着几本书和台灯。",
            "objects": ["床", "书桌", "台灯", "衣柜"]
        },
        {
            "id": "kitchen",
            "name": "厨房",
            "description": "干净整洁的厨房，橱柜里有各种餐具和调料。",
            "objects": ["灶台", "冰箱", "橱柜", "餐桌"]
        },
        {
            "id": "balcony",
            "name": "阳台",
            "description": "小小的阳台，种着几盆绿植，能看到远处的街道。",
            "objects": ["绿植", "椅子", "晾衣架"]
        }
    ],
    "visited": True,
    "created_at": None
}


class SceneService:
    """场景服务"""
    
    def __init__(self, store: DiskStore):
        self.store = store
        self._current_location: Optional[str] = None
        self._current_area: Optional[str] = None
    
    def initialize(self) -> dict:
        """初始化场景系统 - 创建初始环境"""
        # 检查是否已有初始环境
        locations = self.store.list_documents("places")
        
        if not locations:
            # 创建初始环境
            env = DEFAULT_ENVIRONMENT.copy()
            env["created_at"] = datetime.now().isoformat()
            
            self.store.save_document("places", env["id"], env)
            
            # 设置为当前场景
            self._current_location = env["id"]
            self._current_area = env["areas"][0]["id"]
            
            # 保存当前场景状态（使用 scene_audits）
            self._save_current_scene()
            
            return self.get_current_scene()
        
        # 已有场景，加载当前场景
        # 尝试从 scene_audits 加载最新状态
        audits = self.store.list_documents("scene_audits")
        if audits:
            # 取最新的
            latest = max(audits, key=lambda x: x.get("updated_at", ""))
            self._current_location = latest.get("location_id")
            self._current_area = latest.get("area_id")
        else:
            # 使用第一个场景作为当前场景
            self._current_location = locations[0]["id"]
            location = self.store.get_document("places", self._current_location)
            self._current_area = location["areas"][0]["id"] if location.get("areas") else None
            self._save_current_scene()
        
        return self.get_current_scene()
    
    def get_current_scene(self) -> dict:
        """获取当前场景"""
        if not self._current_location:
            return self.initialize()
        
        location = self.store.get_document("places", self._current_location)
        if not location:
            return {"error": "Current location not found"}
        
        area = None
        if self._current_area:
            area = next((a for a in location.get("areas", []) if a["id"] == self._current_area), None)
        
        return {
            "location": {
                "id": location["id"],
                "name": location["name"],
                "type": location.get("type", "unknown"),
                "description": location.get("description", "")
            },
            "area": area if area else {},
            "objects": area.get("objects", []) if area else [],
            "description": self._format_scene_description(location, area)
        }
    
    def _format_scene_description(self, location: dict, area: Optional[dict]) -> str:
        """格式化场景描述"""
        desc = f"你在{location['name']}"
        if area:
            desc += f"的{area['name']}"
        desc += "。"
        
        if area and area.get("description"):
            desc += area["description"]
        elif location.get("description"):
            desc += location["description"]
        
        return desc
    
    def _save_current_scene(self):
        """保存当前场景状态"""
        audit_id = "current_scene"
        self.store.save_document("scene_audits", audit_id, {
            "location_id": self._current_location,
            "area_id": self._current_area,
            "updated_at": datetime.now().isoformat()
        })
    
    def switch_scene(self, location_id: str, area_id: Optional[str] = None) -> dict:
        """切换场景"""
        location = self.store.get_document("places", location_id)
        if not location:
            raise ValueError(f"Location not found: {location_id}")
        
        # 标记为已访问
        if not location.get("visited"):
            location["visited"] = True
            location["first_visited_at"] = datetime.now().isoformat()
            self.store.save_document("places", location_id, location)
        
        self._current_location = location_id
        
        if area_id:
            self._current_area = area_id
        else:
            # 使用第一个区域
            self._current_area = location["areas"][0]["id"] if location.get("areas") else None
        
        self._save_current_scene()
        
        return self.get_current_scene()
    
    def get_scene_pool(self) -> list:
        """获取场景池"""
        locations = self.store.list_documents("places")
        
        return [
            {
                "location_id": loc["id"],
                "name": loc["name"],
                "type": loc.get("type", "unknown"),
                "visited": loc.get("visited", False),
                "created_at": loc.get("created_at")
            }
            for loc in locations
        ]
    
    def create_location(self, name: str, location_type: str, description: str, 
                       areas: list, world_context: Optional[dict] = None) -> dict:
        """创建新地点（由 Agent 或日程驱动）"""
        location_id = f"loc_{uuid.uuid4().hex[:8]}"
        
        location = {
            "id": location_id,
            "name": name,
            "type": location_type,
            "description": description,
            "areas": areas,
            "visited": False,
            "created_at": datetime.now().isoformat(),
            "generation_context": world_context or {}
        }
        
        self.store.save_document("places", location_id, location)
        
        return location
