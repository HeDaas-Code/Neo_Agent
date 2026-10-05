"""日程服务 - 管理日程、行程和场景绑定"""
import uuid
from datetime import datetime, date, time
from typing import Optional, List

from ..storage.disk_store import DiskStore


class ScheduleService:
    """日程服务"""
    
    def __init__(self, store: DiskStore):
        self.store = store
    
    def get_today_itinerary(self) -> List[dict]:
        """获取今日行程"""
        today = date.today().isoformat()
        
        # 查找今天的日程
        schedules = self.store.list_documents("itineraries")
        today_schedules = []
        
        for schedule in schedules:
            # 检查日期
            schedule_date = schedule.get("date")
            if schedule_date == today:
                today_schedules.append({
                    "id": schedule["id"],
                    "time": schedule.get("time", "全天"),
                    "activity": schedule.get("activity", "未知活动"),
                    "location": schedule.get("location_name"),
                    "location_id": schedule.get("location_id"),
                    "area_id": schedule.get("area_id"),
                    "type": schedule.get("participant_type", "personal"),
                    "description": schedule.get("description", "")
                })
        
        # 按时间排序
        today_schedules.sort(key=lambda x: x["time"])
        
        return today_schedules
    
    def create_schedule(self, activity: str, schedule_date: str, time_str: Optional[str] = None,
                       participant_type: str = "agent", location_id: Optional[str] = None,
                       area_id: Optional[str] = None, description: str = "") -> dict:
        """创建日程
        
        Args:
            activity: 活动名称
            schedule_date: 日期 (YYYY-MM-DD)
            time_str: 时间 (HH:MM 或 HH:MM-HH:MM)
            participant_type: 参与方类型 (agent=Agent个人, user=用户个人, shared=共同)
            location_id: 地点ID
            area_id: 区域ID
            description: 描述
        """
        schedule_id = f"sch_{uuid.uuid4().hex[:8]}"
        
        schedule = {
            "id": schedule_id,
            "activity": activity,
            "date": schedule_date,
            "time": time_str or "全天",
            "participant_type": participant_type,
            "location_id": location_id,
            "area_id": area_id,
            "description": description,
            "created_at": datetime.now().isoformat(),
            "created_by": "agent"
        }
        
        # 如果有地点ID，获取地点名称
        if location_id:
            from .scene import SceneService
            location = self.store.get_document("places", location_id)
            if location:
                schedule["location_name"] = location["name"]
        
        self.store.save_document("itineraries", schedule_id, schedule)
        
        return schedule
    
    def update_schedule(self, schedule_id: str, updates: dict) -> dict:
        """更新日程"""
        schedule = self.store.get_document("itineraries", schedule_id)
        if not schedule:
            raise ValueError(f"Schedule not found: {schedule_id}")
        
        schedule.update(updates)
        schedule["updated_at"] = datetime.now().isoformat()
        
        self.store.save_document("itineraries", schedule_id, schedule)
        
        return schedule
    
    def delete_schedule(self, schedule_id: str) -> bool:
        """删除日程"""
        return self.store.delete_document("itineraries", schedule_id)
    
    def get_current_activity(self) -> Optional[dict]:
        """获取当前正在进行的活动"""
        now = datetime.now()
        today = now.date().isoformat()
        current_time = now.time()
        
        schedules = self.get_today_itinerary()
        
        for schedule in schedules:
            time_str = schedule.get("time", "")
            if "-" in time_str:
                # 时间段
                start_str, end_str = time_str.split("-")
                try:
                    start_time = time.fromisoformat(start_str.strip())
                    end_time = time.fromisoformat(end_str.strip())
                    
                    if start_time <= current_time <= end_time:
                        return schedule
                except ValueError:
                    continue
            elif time_str != "全天":
                # 单一时间点，假设持续1小时
                try:
                    start_time = time.fromisoformat(time_str.strip())
                    # 简单判断：如果在这个时间点后1小时内
                    if start_time <= current_time:
                        return schedule
                except ValueError:
                    continue
        
        return None
