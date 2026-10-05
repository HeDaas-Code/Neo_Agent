"""场景自动生成服务：根据活动目的生成新场景。"""
from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime
from typing import Any

from neo_agent.storage import DiskStore


class SceneGenerationService:
    """场景生成服务，根据活动需求创建地点、区域和物体。"""

    def __init__(self, store: DiskStore, model: Any | None = None):
        self.store = store
        self.model = model

    def generate_scene_for_activity(self, activity: str, purpose: str, 
                                    location_hint: str = "") -> dict[str, Any]:
        """为活动生成新场景。
        
        Args:
            activity: 活动描述
            purpose: 活动目的
            location_hint: 地点提示
        
        Returns:
            生成的场景数据
        """
        if not self.model:
            return {"status": "error", "reason": "模型未配置"}

        # 获取角色信息和世界观
        character = self.store.get_character()
        if not character:
            return {"status": "error", "reason": "角色未初始化"}

        # 获取历史对话作为世界观参考
        try:
            history = self.store.read_json("/runtime/conversations/default.json", default=[])
            recent_context = "\n".join(
                f"用户: {turn['user']}\n助手: {turn['assistant']}"
                for turn in history[-10:]
            ) if history else ""
        except Exception:
            recent_context = ""

        prompt = f"""为以下活动生成一个真实、具体的场景。

角色信息：
- 姓名：{character.get('name', '未知')}
- 背景：{character.get('background', '未知')}
- 设定：{character.get('setting', '现代都市')}

活动需求：
- 活动：{activity}
- 目的：{purpose}
- 地点提示：{location_hint or '无'}

相关对话片段（世界观参考）：
{recent_context[:500] if recent_context else '无'}

要求：
1. 场景要符合角色的生活背景和世界观
2. 地点名称要具体（如"星光咖啡馆"而非"咖啡馆"）
3. 包含2-4个有意义的区域（如咖啡馆的"吧台区"、"靠窗座位"）
4. 每个区域列出3-5个可交互的物体
5. 提供简短的环境描述（氛围、装饰等）

返回 JSON 格式：
{{
  "place": {{
    "name": "地点名称",
    "description": "整体描述",
    "atmosphere": "氛围描述"
  }},
  "areas": [
    {{
      "name": "区域名称",
      "description": "区域描述",
      "objects": [
        {{"name": "物体名称", "description": "物体描述", "interactive": true/false}}
      ]
    }}
  ]
}}

只返回 JSON，不要额外解释。"""

        try:
            from langchain_core.messages import SystemMessage, HumanMessage
            response = self.model.invoke([
                SystemMessage(content="你是一个精确的场景设计师，只输出 JSON。"),
                HumanMessage(content=prompt)
            ])
            content = str(getattr(response, "content", response))
            
            # 提取 JSON
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if not json_match:
                raise ValueError("无法解析 JSON 响应")
            
            data = json.loads(json_match.group())
            
            # 创建地点
            place_data = data.get("place", {})
            place_id = hashlib.sha256(
                f"{place_data.get('name', 'unknown')}{datetime.now().isoformat()}".encode()
            ).hexdigest()[:20]

            from neo_agent.runtime.itinerary import SceneService
            scene_service = SceneService(self.store)
            
            # 保存地点
            place_doc = {
                "place_id": place_id,
                "name": place_data.get("name", "未命名地点"),
                "description": place_data.get("description", ""),
                "atmosphere": place_data.get("atmosphere", ""),
                "layout_frozen": False,  # 首次访问后会固化
                "created_at": datetime.now().isoformat(),
                "created_by": "scene_generation",
                "generation_context": {
                    "activity": activity,
                    "purpose": purpose,
                    "location_hint": location_hint
                }
            }
            self.store.save_document("places", place_id, place_doc)

            # 保存区域和物体
            area_ids = []
            for area_data in data.get("areas", []):
                area_id = hashlib.sha256(
                    f"{place_id}{area_data.get('name', 'unknown')}".encode()
                ).hexdigest()[:20]

                area_doc = {
                    "area_id": area_id,
                    "place_id": place_id,
                    "name": area_data.get("name", "未命名区域"),
                    "description": area_data.get("description", ""),
                    "objects": area_data.get("objects", []),
                    "created_at": datetime.now().isoformat()
                }
                self.store.save_document("areas", area_id, area_doc)
                area_ids.append(area_id)

            self.store.append_event("scene_generation.scene_created", {
                "place_id": place_id,
                "place_name": place_doc["name"],
                "area_count": len(area_ids),
                "activity": activity
            })

            return {
                "status": "success",
                "place_id": place_id,
                "place": place_doc,
                "areas": area_ids
            }

        except Exception as exc:
            self.store.append_event("scene_generation.generation_failed", {
                "activity": activity,
                "error": type(exc).__name__,
                "message": str(exc)
            })
            return {"status": "error", "reason": str(exc)}

    def freeze_scene_layout(self, place_id: str) -> bool:
        """固化场景布局（首次访问后）。"""
        try:
            place = self.store.get_document("places", place_id)
            if place.get("layout_frozen"):
                return True  # 已固化
            
            place["layout_frozen"] = True
            place["frozen_at"] = datetime.now().isoformat()
            self.store.save_document("places", place_id, place)

            self.store.append_event("scene_generation.layout_frozen", {
                "place_id": place_id,
                "place_name": place.get("name", "未知")
            })

            return True

        except Exception as exc:
            self.store.append_event("scene_generation.freeze_failed", {
                "place_id": place_id,
                "error": type(exc).__name__
            })
            return False
