"""
关系管理服务
负责关系状态的持久化、累积验证和历史记录
"""
from typing import Any, Dict, List, Optional
from datetime import datetime
from collections import defaultdict


class RelationshipService:
    """关系管理服务
    
    实现关系持久化规则：
    - 同一关系变化需要在至少 3 个不同轮次出现
    - 每次信号的置信度不低于 0.8
    - 分数变化限幅在 -3 到 +3 之间
    """
    
    def __init__(self, store):
        self.store = store
        # 信号缓冲区：entity -> [signals]
        self._signal_buffer: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    
    def record_signal(self, entity: str, signal_type: str, confidence: float, 
                     score_delta: int, reason: str, conversation_id: str) -> Dict[str, Any]:
        """记录关系信号
        
        Args:
            entity: 关系实体名称（通常是用户）
            signal_type: 信号类型 (positive/negative/neutral)
            confidence: 置信度 (0.0-1.0)
            score_delta: 分数变化 (-3 到 +3)
            reason: 变化原因
            conversation_id: 对话轮次 ID
        
        Returns:
            处理结果，包含是否触发持久化
        """
        # 限幅分数变化
        score_delta = max(-3, min(3, score_delta))
        
        # 置信度不足，直接拒绝
        if confidence < 0.8:
            return {
                "status": "rejected",
                "reason": "置信度不足 0.8",
                "confidence": confidence
            }
        
        # 记录信号到缓冲区
        signal = {
            "conversation_id": conversation_id,
            "signal_type": signal_type,
            "confidence": confidence,
            "score_delta": score_delta,
            "reason": reason,
            "timestamp": datetime.now().isoformat()
        }
        
        self._signal_buffer[entity].append(signal)
        
        # 只保留最近 10 次信号
        if len(self._signal_buffer[entity]) > 10:
            self._signal_buffer[entity] = self._signal_buffer[entity][-10:]
        
        # 检查是否满足持久化条件
        recent_signals = self._signal_buffer[entity][-5:]  # 检查最近 5 次
        
        # 统计相同方向的信号
        same_direction_signals = [
            s for s in recent_signals 
            if s["signal_type"] == signal_type and s["confidence"] >= 0.8
        ]
        
        # 需要至少 3 次相同方向的高置信度信号
        if len(same_direction_signals) >= 3:
            # 检查这些信号是否来自不同的对话轮次
            unique_conversations = set(s["conversation_id"] for s in same_direction_signals)
            
            if len(unique_conversations) >= 3:
                # 触发持久化
                result = self._persist_relationship_change(
                    entity, signal_type, same_direction_signals[-3:]
                )
                
                # 清空该实体的缓冲区（避免重复持久化）
                self._signal_buffer[entity] = []
                
                return {
                    "status": "persisted",
                    "entity": entity,
                    "applied_delta": result["applied_delta"],
                    "new_score": result["new_score"],
                    "evidence_count": len(same_direction_signals)
                }
        
        return {
            "status": "buffered",
            "entity": entity,
            "buffer_size": len(self._signal_buffer[entity]),
            "same_direction_count": len(same_direction_signals),
            "need_more": 3 - len(same_direction_signals)
        }
    
    def _persist_relationship_change(self, entity: str, signal_type: str, 
                                    signals: List[Dict[str, Any]]) -> Dict[str, Any]:
        """持久化关系变化
        
        Args:
            entity: 实体名称
            signal_type: 信号类型
            signals: 触发持久化的信号列表（至少 3 个）
        
        Returns:
            持久化结果
        """
        # 获取当前关系状态
        current = self.store.get_document("relationships", entity)
        if not current:
            current = {
                "entity": entity,
                "score": 0,
                "history": [],
                "created_at": datetime.now().isoformat()
            }
        
        current_score = current.get("score", 0)
        
        # 计算平均分数变化（限幅）
        avg_delta = sum(s["score_delta"] for s in signals) // len(signals)
        avg_delta = max(-3, min(3, avg_delta))
        
        # 应用变化
        new_score = current_score + avg_delta
        
        # 记录历史
        history_entry = {
            "timestamp": datetime.now().isoformat(),
            "signal_type": signal_type,
            "old_score": current_score,
            "new_score": new_score,
            "delta": avg_delta,
            "evidence": [
                {
                    "conversation_id": s["conversation_id"],
                    "confidence": s["confidence"],
                    "reason": s["reason"]
                }
                for s in signals
            ]
        }
        
        current["score"] = new_score
        current["history"] = current.get("history", [])
        current["history"].append(history_entry)
        current["last_updated"] = datetime.now().isoformat()
        
        # 只保留最近 50 条历史
        if len(current["history"]) > 50:
            current["history"] = current["history"][-50:]
        
        # 持久化到 PyVDisk
        self.store.put_document("relationships", entity, current)
        
        # 记录审计事件
        self.store.append_event("relationship.persisted", {
            "entity": entity,
            "old_score": current_score,
            "new_score": new_score,
            "delta": avg_delta,
            "signal_type": signal_type,
            "evidence_count": len(signals)
        })
        
        return {
            "applied_delta": avg_delta,
            "new_score": new_score,
            "old_score": current_score
        }
    
    def get_relationship(self, entity: str) -> Dict[str, Any]:
        """获取关系状态"""
        rel = self.store.get_document("relationships", entity)
        return rel if rel else {}
    
    def list_all_relationships(self) -> List[Dict[str, Any]]:
        """列出所有关系"""
        return self.store.list_documents("relationships") or []
    
    def get_relationship_history(self, entity: str, limit: int = 20) -> List[Dict[str, Any]]:
        """获取关系历史变化
        
        Args:
            entity: 实体名称
            limit: 返回最近的 N 条记录
        
        Returns:
            历史变化列表
        """
        rel = self.store.get_document("relationships", entity)
        if not rel:
            return []
        
        history = rel.get("history", [])
        return list(reversed(history[-limit:]))  # 最新的在前
    
    def get_signal_buffer_status(self, entity: str) -> Dict[str, Any]:
        """获取信号缓冲区状态（调试用）"""
        buffer = self._signal_buffer.get(entity, [])
        return {
            "entity": entity,
            "buffer_size": len(buffer),
            "signals": buffer
        }
