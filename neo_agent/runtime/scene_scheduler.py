"""场景调度器：根据日程自动切换场景。"""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
from typing import Any

from neo_agent.storage import DiskStore


class SceneScheduler:
    """场景调度器，监控日程并自动切换场景。"""

    def __init__(self, store: DiskStore):
        self.store = store
        self.running = False
        self._task = None

    async def start(self):
        """启动调度器。"""
        if self.running:
            return
        
        self.running = True
        self._task = asyncio.create_task(self._scheduler_loop())
        
        self.store.append_event("scene_scheduler.started", {
            "timestamp": datetime.now().isoformat()
        })

    async def stop(self):
        """停止调度器。"""
        self.running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        
        self.store.append_event("scene_scheduler.stopped", {
            "timestamp": datetime.now().isoformat()
        })

    async def _scheduler_loop(self):
        """调度循环，每分钟检查一次。"""
        while self.running:
            try:
                await self._check_and_switch_scene()
            except Exception as exc:
                self.store.append_event("scene_scheduler.error", {
                    "error": type(exc).__name__,
                    "message": str(exc)
                })
            
            # 每60秒检查一次
            await asyncio.sleep(60)

    async def _check_and_switch_scene(self):
        """检查当前时间是否需要切换场景。"""
        now = datetime.now()
        now_str = now.isoformat()
        
        # 获取所有 Agent 和共同活动的日程
        schedules = [
            s for s in self.store.list_documents("schedules")
            if s.get("category") in ("agent", "shared")
        ]
        
        # 找到当前应该激活的场景
        current_schedule = None
        for schedule in schedules:
            time_str = schedule.get("time", "")
            end_time_str = schedule.get("end_time")
            
            try:
                start_time = datetime.fromisoformat(time_str)
                end_time = datetime.fromisoformat(end_time_str) if end_time_str else start_time + timedelta(hours=2)
                
                if start_time <= now <= end_time:
                    current_schedule = schedule
                    break
            except Exception:
                continue
        
        if not current_schedule:
            # 没有当前活动，保持在初始环境
            await self._ensure_initial_environment()
            return
        
        # 获取或生成场景
        scene_id = current_schedule.get("scene_id")
        
        if not scene_id and current_schedule.get("need_new_scene"):
            # 需要生成新场景
            scene_id = await self._generate_scene_for_schedule(current_schedule)
            if scene_id:
                # 更新日程绑定
                current_schedule["scene_id"] = scene_id
                self.store.save_document("schedules", current_schedule["id"], current_schedule)
        
        if scene_id:
            # 切换到目标场景
            await self._switch_to_scene(scene_id, current_schedule)
        else:
            # 场景不可用，保持当前环境
            pass

    async def _ensure_initial_environment(self):
        """确保初始环境存在并激活。"""
        from neo_agent.runtime.itinerary import SceneService
        scene_service = SceneService(self.store)
        
        # 确保初始环境存在
        initial = scene_service.ensure_initial_environment(activate=False)
        
        # 检查当前场景
        current = scene_service.current()
        
        if not current or current.get("place_id") != initial.get("place_id"):
            # 切换到初始环境
            scene_service.ensure_initial_environment(activate=True)
            
            self.store.append_event("scene_scheduler.returned_to_initial", {
                "place_name": initial.get("name", "未知"),
                "timestamp": datetime.now().isoformat()
            })

    async def _generate_scene_for_schedule(self, schedule: dict[str, Any]) -> str | None:
        """为日程生成场景。"""
        try:
            from neo_agent.runtime.scene_generation import SceneGenerationService
            from neo_agent.runtime.agent import AgentRuntime
            
            # 获取模型（从 runtime 初始化）
            model = AgentRuntime._build_model()
            
            scene_gen = SceneGenerationService(self.store, model)
            result = scene_gen.generate_scene_for_activity(
                schedule.get("activity", ""),
                schedule.get("purpose", ""),
                schedule.get("location", "")
            )
            
            if result.get("status") == "success":
                return result.get("place_id")
            
            return None
            
        except Exception as exc:
            self.store.append_event("scene_scheduler.generation_failed", {
                "schedule_id": schedule.get("id"),
                "error": type(exc).__name__
            })
            return None

    async def _switch_to_scene(self, place_id: str, schedule: dict[str, Any]):
        """切换到指定场景。"""
        try:
            from neo_agent.runtime.itinerary import SceneService
            scene_service = SceneService(self.store)
            
            # 获取地点信息
            place = self.store.get_document("places", place_id)
            areas = scene_service.areas(place_id)
            
            # 选择默认区域（第一个）
            area_id = areas[0].get("area_id") if areas else None
            
            # 激活场景
            current_scene = {
                "place_id": place_id,
                "place_name": place.get("name", "未知"),
                "area_id": area_id,
                "area_name": areas[0].get("name", "") if areas else "",
                "activated_at": datetime.now().isoformat(),
                "schedule_id": schedule.get("id"),
                "activity": schedule.get("activity", "")
            }
            
            self.store.write_json("/runtime/scene/current.json", current_scene)
            
            # 首次访问固化布局
            if not place.get("layout_frozen"):
                from neo_agent.runtime.scene_generation import SceneGenerationService
                scene_gen = SceneGenerationService(self.store)
                scene_gen.freeze_scene_layout(place_id)
            
            self.store.append_event("scene_scheduler.scene_switched", {
                "place_id": place_id,
                "place_name": place.get("name", "未知"),
                "activity": schedule.get("activity", ""),
                "timestamp": datetime.now().isoformat()
            })
            
        except Exception as exc:
            self.store.append_event("scene_scheduler.switch_failed", {
                "place_id": place_id,
                "error": type(exc).__name__,
                "message": str(exc)
            })
