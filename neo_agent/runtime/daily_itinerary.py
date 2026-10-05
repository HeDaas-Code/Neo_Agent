"""每日行程自动生成服务：每天为 Agent 生成自己的行程安排。"""
from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, date, timedelta
from typing import Any

from neo_agent.storage import DiskStore


class DailyItineraryService:
    """每日行程生成服务，按天为 Agent 创建日程。"""

    def __init__(self, store: DiskStore, model: Any | None = None):
        self.store = store
        self.model = model

    def should_generate_today(self) -> bool:
        """检查今天是否需要生成行程。"""
        today = date.today().isoformat()
        daily_plans = self.store.list_documents("daily_plans")
        
        for plan in daily_plans:
            if plan.get("date") == today:
                return False  # 已生成
        
        return True

    def generate_today_itinerary(self) -> dict[str, Any]:
        """为今天生成 Agent 的行程。
        
        返回生成的计划对象。
        """
        if not self.model:
            return {"status": "error", "reason": "模型未配置"}

        today = date.today()
        today_str = today.isoformat()
        
        # 获取角色信息
        character = self.store.get_character()
        if not character:
            return {"status": "error", "reason": "角色未初始化"}

        # 获取历史对话上下文
        try:
            history = self.store.read_json("/runtime/conversations/default.json", default=[])
            recent_context = "\n".join(
                f"用户: {turn['user']}\n助手: {turn['assistant']}"
                for turn in history[-5:]
            ) if history else "暂无对话历史"
        except Exception:
            recent_context = "暂无对话历史"

        # 获取已有场景池
        from neo_agent.runtime.itinerary import SceneService
        scene_service = SceneService(self.store)
        places = scene_service.places(visited_only=False)
        place_names = [p.get("name", "") for p in (places or [])]

        prompt = f"""为角色生成今天（{today.strftime('%Y年%m月%d日 %A')}）的日常行程。

角色信息：
- 姓名：{character.get('name', '未知')}
- 性别：{character.get('gender', '未知')}
- 年龄：{character.get('age', '未知')}
- 性格：{character.get('personality', '未知')}
- 背景：{character.get('background', '未知')}

最近对话片段：
{recent_context}

已知场景：{', '.join(place_names) if place_names else '无（可生成新场景）'}

要求：
1. 生成符合角色身份和性格的真实日常行程
2. 包含起床、学习/工作、休闲、用餐、睡觉等活动
3. 时间要合理连贯，不重叠
4. 每个活动指定具体的地点（优先使用已知场景，必要时标注"需生成新场景"）
5. 只生成今天剩余时段的行程（从当前时刻{datetime.now().strftime('%H:%M')}开始）

返回 JSON 格式：
{{
  "activities": [
    {{
      "time": "HH:MM",
      "end_time": "HH:MM",
      "activity": "活动描述",
      "location": "地点名称",
      "area": "具体区域（可选）",
      "purpose": "活动目的/动机",
      "need_new_scene": true/false
    }}
  ]
}}

只返回 JSON，不要额外解释。"""

        try:
            from langchain_core.messages import SystemMessage, HumanMessage
            response = self.model.invoke([
                SystemMessage(content="你是一个精确的日程规划器，只输出 JSON。"),
                HumanMessage(content=prompt)
            ])
            content = str(getattr(response, "content", response))
            
            # 提取 JSON
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if not json_match:
                raise ValueError("无法解析 JSON 响应")
            
            data = json.loads(json_match.group())
            activities = data.get("activities", [])

            # 创建每个活动的日程
            schedule_ids = []
            for activity in activities:
                schedule_id = hashlib.sha256(
                    f"{today_str}{activity['time']}{activity['activity']}".encode()
                ).hexdigest()[:20]

                # 构建完整时间
                time_str = f"{today_str}T{activity['time']}:00"
                end_time_str = f"{today_str}T{activity['end_time']}:00" if activity.get('end_time') else None

                schedule_data = {
                    "id": schedule_id,
                    "activity": activity["activity"],
                    "time": time_str,
                    "end_time": end_time_str,
                    "category": "agent",  # Agent 个人行程
                    "location": activity.get("location", ""),
                    "area": activity.get("area", ""),
                    "purpose": activity.get("purpose", ""),
                    "scene_id": None,  # 稍后绑定或生成
                    "need_new_scene": activity.get("need_new_scene", False),
                    "created_at": datetime.now().isoformat(),
                    "created_by": "daily_itinerary",
                    "source": "auto_generated"
                }

                self.store.save_document("schedules", schedule_id, schedule_data)
                schedule_ids.append(schedule_id)

            # 保存每日计划记录
            plan_id = hashlib.sha256(today_str.encode()).hexdigest()[:20]
            plan_data = {
                "id": plan_id,
                "date": today_str,
                "schedule_ids": schedule_ids,
                "generated_at": datetime.now().isoformat(),
                "status": "generated",
                "activity_count": len(activities)
            }
            self.store.save_document("daily_plans", plan_id, plan_data)

            self.store.append_event("daily_itinerary.generated", {
                "date": today_str,
                "activity_count": len(activities),
                "schedule_ids": schedule_ids
            })

            return {"status": "success", "plan": plan_data, "activities": activities}

        except Exception as exc:
            self.store.append_event("daily_itinerary.generation_failed", {
                "date": today_str,
                "error": type(exc).__name__,
                "message": str(exc)
            })
            return {"status": "error", "reason": str(exc)}

    def run_daily_check(self) -> dict[str, Any]:
        """每日检查并生成行程（通常在 00:05 调用）。"""
        if not self.should_generate_today():
            return {"status": "skipped", "reason": "今日行程已存在"}

        return self.generate_today_itinerary()
