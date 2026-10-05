"""每日行程自动生成服务：每天为 Agent 生成自己的行程安排。"""
from __future__ import annotations

from typing import List, Dict, Any
import hashlib
import json
from datetime import datetime, timezone, timedelta
from typing import Any

from neo_agent.storage import DiskStore


class DailyItineraryService:
    """每日行程自动生成服务"""

    def __init__(self, store: DiskStore, model: Any | None = None):
        self.store = store
        self.model = model

    def should_generate_today(self) -> bool:
        """检查今天是否需要生成行程"""
        from datetime import datetime, timezone

        today_str = datetime.now(timezone.utc).date().isoformat()

        try:
            data = self.store.read(f"daily_plans/{today_str}.json")
            plan = json.loads(data)
            return plan.get("status") != "completed"
        except Exception:
            return True

    def generate_today_itinerary(self) -> dict[str, Any]:
        """为今天生成行程"""
        from datetime import datetime, timezone

        today_str = datetime.now(timezone.utc).date().isoformat()
        now = datetime.now(timezone.utc)

        # 生成时间范围：当前时间到今天结束
        start_hour = now.hour
        end_hour = 23

        # 简单的行程模板
        template_activities = [
            {"hour": 8, "activity": "起床，洗漱", "duration": 1, "location": "home"},
            {"hour": 9, "activity": "早餐", "duration": 1, "location": "home-kitchen"},
            {"hour": 10, "activity": "阅读或学习", "duration": 2, "location": "home-study"},
            {"hour": 12, "activity": "午餐", "duration": 1, "location": "home-kitchen"},
            {"hour": 13, "activity": "午休", "duration": 1, "location": "home-bedroom"},
            {"hour": 14, "activity": "工作或创作", "duration": 3, "location": "home-study"},
            {"hour": 17, "activity": "休闲活动", "duration": 2, "location": "home-living"},
            {"hour": 19, "activity": "晚餐", "duration": 1, "location": "home-kitchen"},
            {"hour": 20, "activity": "散步", "duration": 1, "location": "park"},
            {"hour": 21, "activity": "放松娱乐", "duration": 2, "location": "home-living"},
            {"hour": 23, "activity": "准备休息", "duration": 1, "location": "home-bedroom"},
        ]

        # 过滤出当前时间之后的活动
        schedule_items = []
        for act in template_activities:
            if act["hour"] >= start_hour:
                start_time = now.replace(
                    hour=act["hour"], minute=0, second=0, microsecond=0
                )
                end_time = start_time + timedelta(hours=act["duration"])

                schedule_items.append(
                    {
                        "time": start_time.isoformat(),
                        "end_time": end_time.isoformat(),
                        "activity": act["activity"],
                        "location": act["location"],
                        "type": "personal",
                        "scene_id": None,
                        "is_current": False,
                    }
                )

        plan = {
            "date": today_str,
            "timezone": "UTC",
            "generated_at": now.isoformat(),
            "status": "completed",
            "schedule_items": schedule_items,
        }

        # 保存计划
        try:
            self.store.write(f"daily_plans/{today_str}.json", json.dumps(plan, ensure_ascii=False, indent=2))
        except Exception as e:
            print(f"保存每日计划失败: {e}")

        return plan

    def run_daily_check(self) -> dict[str, Any]:
        """每日检查：如果需要则生成今日行程"""
        if self.should_generate_today():
            return self.generate_today_itinerary()
        else:
            today_str = datetime.now(timezone.utc).date().isoformat()
            try:
                data = self.store.read(f"daily_plans/{today_str}.json")
                return json.loads(data)
            except Exception:
                return {"status": "error", "schedule_items": []}

    def get_today_itinerary(self) -> List[Dict[str, Any]]:
        """获取今日行程"""
        from datetime import datetime, timezone
        
        today_str = datetime.now(timezone.utc).date().isoformat()
        
        try:
            # 尝试从存储中读取今日计划
            data = self.store.read(f"daily_plans/{today_str}.json")
            plan = json.loads(data)
            return plan.get("schedule_items", [])
        except Exception:
            # 如果没有计划，返回空列表
            return []
