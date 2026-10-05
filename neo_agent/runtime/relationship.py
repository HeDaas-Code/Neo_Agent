"""关系与情绪服务"""
from datetime import datetime
from typing import Optional

from ..storage.disk_store import DiskStore


class RelationshipService:
    """关系服务"""
    
    def __init__(self, store: DiskStore):
        self.store = store
    
    def get_relationship(self, entity: str = "user") -> dict:
        """获取与某个实体的关系状态"""
        rel = self.store.get_document("relationships", entity)
        
        if not rel:
            # 初始化关系
            rel = {
                "id": entity,
                "score": 50,  # 初始分数
                "level": "普通",
                "history": [],
                "created_at": datetime.now().isoformat(),
                "last_update": datetime.now().isoformat()
            }
            self.store.save_document("relationships", entity, rel)
        
        return rel
    
    def update_relationship(self, entity: str, score_change: int, reason: str = "") -> dict:
        """更新关系分数（限幅 -3 到 +3）"""
        # 限制变化幅度
        score_change = max(-3, min(3, score_change))
        
        rel = self.get_relationship(entity)
        
        old_score = rel["score"]
        new_score = max(0, min(100, old_score + score_change))
        
        rel["score"] = new_score
        rel["last_update"] = datetime.now().isoformat()
        
        # 记录历史
        if "history" not in rel:
            rel["history"] = []
        
        rel["history"].append({
            "timestamp": datetime.now().isoformat(),
            "old_score": old_score,
            "new_score": new_score,
            "change": score_change,
            "reason": reason
        })
        
        # 只保留最近50条历史
        if len(rel["history"]) > 50:
            rel["history"] = rel["history"][-50:]
        
        # 更新关系等级
        if new_score >= 80:
            rel["level"] = "挚友"
        elif new_score >= 50:
            rel["level"] = "朋友"
        elif new_score >= 20:
            rel["level"] = "普通"
        else:
            rel["level"] = "陌生"
        
        self.store.save_document("relationships", entity, rel)
        
        return rel


class EmotionService:
    """情绪服务"""
    
    def __init__(self, store: DiskStore):
        self.store = store
        self._current_emotion = {
            "state": "平静",
            "intensity": 0.5,
            "timestamp": datetime.now().isoformat()
        }
    
    def get_current_emotion(self) -> dict:
        """获取当前情绪（临时状态）"""
        return self._current_emotion.copy()
    
    def update_emotion(self, state: str, intensity: float = 0.5) -> dict:
        """更新情绪状态（临时，不持久化）"""
        self._current_emotion = {
            "state": state,
            "intensity": max(0.0, min(1.0, intensity)),
            "timestamp": datetime.now().isoformat()
        }
        return self._current_emotion
    
    def record_emotion_event(self, state: str, intensity: float, trigger: str = "") -> dict:
        """记录情绪事件（持久化）"""
        event = {
            "state": state,
            "intensity": intensity,
            "trigger": trigger,
            "timestamp": datetime.now().isoformat()
        }
        
        self.store.append_event("emotion_change", event)
        
        return event
