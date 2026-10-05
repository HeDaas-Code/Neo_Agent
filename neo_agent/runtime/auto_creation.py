"""Agent 自动创作服务：根据对话自动创建事件、日程、场景、关系等实体。"""
from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timedelta
from typing import Any

from neo_agent.storage import DiskStore


class AutoCreationService:
    """Agent 自动创作服务，无需人工干预即可创建运行时实体。"""

    def __init__(self, store: DiskStore, model: Any | None = None):
        self.store = store
        self.model = model

    def extract_schedule_intent(self, message: str, reply: str, context: dict[str, Any]) -> list[dict[str, Any]]:
        """从对话中提取日程意图并自动创建。
        
        返回创建的日程项列表。
        """
        if not self.model:
            return []

        prompt = f"""分析以下对话，判断是否包含明确的时间安排意图。

对话：
用户: {message}
助手: {reply}

当前场景: {context.get('current_scene', '无')}
当前时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}

如果对话中包含明确的时间安排（如"明天"、"下午3点"、"晚上一起"等），返回 JSON 格式：
{{
  "has_schedule": true,
  "schedules": [
    {{
      "activity": "活动描述",
      "time": "ISO 8601 格式时间",
      "end_time": "ISO 8601 格式结束时间（可选）",
      "category": "agent/user/shared",
      "location_hint": "地点提示（如有）"
    }}
  ]
}}

如果没有时间安排，返回：
{{"has_schedule": false}}

只返回 JSON，不要额外解释。"""

        try:
            from langchain_core.messages import SystemMessage, HumanMessage
            response = self.model.invoke([
                SystemMessage(content="你是一个精确的日程提取器，只输出 JSON。"),
                HumanMessage(content=prompt)
            ])
            content = str(getattr(response, "content", response))
            
            # 提取 JSON
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if not json_match:
                return []
            
            data = json.loads(json_match.group())
            if not data.get("has_schedule"):
                return []

            created = []
            for schedule in data.get("schedules", []):
                schedule_id = hashlib.sha256(
                    f"{schedule['activity']}{schedule['time']}".encode()
                ).hexdigest()[:20]

                schedule_data = {
                    "id": schedule_id,
                    "activity": schedule["activity"],
                    "time": schedule["time"],
                    "end_time": schedule.get("end_time"),
                    "category": schedule.get("category", "shared"),
                    "location_hint": schedule.get("location_hint", ""),
                    "scene_id": None,  # 稍后绑定
                    "created_at": datetime.now().isoformat(),
                    "created_by": "agent_auto",
                    "source": "conversation"
                }

                self.store.save_document("schedules", schedule_id, schedule_data)
                created.append(schedule_data)

                self.store.append_event("auto_creation.schedule_created", {
                    "schedule_id": schedule_id,
                    "activity": schedule["activity"],
                    "category": schedule["category"]
                })

            return created

        except Exception as exc:
            self.store.append_event("auto_creation.schedule_extraction_failed", {
                "error": type(exc).__name__,
                "message": str(exc)
            })
            return []

    def extract_relationship_updates(self, message: str, reply: str, 
                                    conversation_id: str) -> dict[str, Any] | None:
        """从对话中提取关系变化信号。
        
        注意：需要连续3轮置信度>=0.8才会持久化。
        """
        if not self.model:
            return None

        prompt = f"""分析以下对话中的关系信号。

用户: {message}
助手: {reply}

判断这次对话是否体现了明确的关系变化（如增进好感、产生误会、建立信任等）。

返回 JSON：
{{
  "has_signal": true/false,
  "signal": "positive/negative/neutral",
  "confidence": 0.0-1.0,
  "score_delta": -3到+3的整数,
  "reason": "简短原因"
}}

只返回 JSON。"""

        try:
            from langchain_core.messages import SystemMessage, HumanMessage
            response = self.model.invoke([
                SystemMessage(content="你是一个精确的关系分析器，只输出 JSON。"),
                HumanMessage(content=prompt)
            ])
            content = str(getattr(response, "content", response))
            
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if not json_match:
                return None
            
            data = json.loads(json_match.group())
            if not data.get("has_signal"):
                return None

            # 通过 RelationshipService 记录信号（自动处理持久化）
            # 假设关系实体是 "user"（未来可从对话中提取）
            entity = "user"
            
            # 先记录到事件日志
            self.store.append_event("auto_creation.relationship_signal", {
                "entity": entity,
                "conversation_id": conversation_id,
                "signal": data["signal"],
                "confidence": data["confidence"],
                "score_delta": data["score_delta"],
                "reason": data["reason"]
            })
            
            # 返回数据供外部使用（包含 entity）
            data["entity"] = entity
            return data

        except Exception as exc:
            self.store.append_event("auto_creation.relationship_extraction_failed", {
                "error": type(exc).__name__
            })
            return None

    def maybe_create_knowledge_entry(self, message: str, reply: str) -> dict[str, Any] | None:
        """从对话中提取值得保存的知识条目。"""
        if not self.model:
            return None

        # 简单规则：如果助手回答包含事实性信息且超过50字，可能值得保存
        if len(reply) < 50:
            return None

        # 检查是否包含事实性关键词
        factual_markers = ["是", "叫做", "位于", "包括", "由于", "因为", "所以", "表示"]
        if not any(marker in reply for marker in factual_markers):
            return None

        try:
            entry_id = hashlib.sha256(f"{message}{reply}".encode()).hexdigest()[:20]
            
            knowledge_data = {
                "id": entry_id,
                "topic": message[:50],  # 截取前50字作为主题
                "content": reply,
                "source": "conversation",
                "created_at": datetime.now().isoformat(),
                "created_by": "agent_auto"
            }

            self.store.save_document("knowledge", entry_id, knowledge_data)
            
            self.store.append_event("auto_creation.knowledge_created", {
                "entry_id": entry_id,
                "topic": knowledge_data["topic"]
            })

            return knowledge_data

        except Exception as exc:
            self.store.append_event("auto_creation.knowledge_creation_failed", {
                "error": type(exc).__name__
            })
            return None
