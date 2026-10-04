"""Autonomous daily plans, persistent scene pools, and scene scheduling.

All records are persisted through DiskStore's PyVDisk document/VFS API. This
module never writes reminder queue entries: schedules are lived context, not
notifications.
"""
from __future__ import annotations

import hashlib
import json
import re
from datetime import date, datetime, time, timedelta
from typing import Any, Literal
from zoneinfo import ZoneInfo

from pydantic import BaseModel, Field


def _stable_id(prefix: str, value: str, *, length: int = 16) -> str:
    return f"{prefix}_{hashlib.sha256(value.encode('utf-8')).hexdigest()[:length]}"


def _parse_dt(value: str) -> datetime:
    parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("日期时间必须包含时区")
    return parsed


def _model_result(model: Any, schema: type[BaseModel], system: str, user: str) -> dict[str, Any]:
    """Call a LangChain structured model, with a JSON-only fallback for test adapters."""
    from langchain_core.messages import HumanMessage, SystemMessage
    messages = [SystemMessage(content=system), HumanMessage(content=user)]
    if hasattr(model, "with_structured_output"):
        result = model.with_structured_output(schema).invoke(messages)
        if isinstance(result, BaseModel):
            return result.model_dump()
        if isinstance(result, dict):
            return schema.model_validate(result).model_dump()
    result = model.invoke(messages)
    content = getattr(result, "content", result)
    if isinstance(content, dict):
        return schema.model_validate(content).model_dump()
    if isinstance(content, list):
        content = "".join(part.get("text", "") if isinstance(part, dict) else str(part) for part in content)
    text = str(content).strip()
    fenced = re.search(r"```(?:json)?\s*(.*?)```", text, re.S)
    if fenced:
        text = fenced.group(1)
    return schema.model_validate(json.loads(text)).model_dump()


class _SceneObject(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    description: str = Field(default="", max_length=500)
    state: str = Field(default="正常", max_length=120)
    priority: int = Field(default=50, ge=0, le=100)


class _SceneBlueprint(BaseModel):
    place_name: str = Field(min_length=1, max_length=100)
    place_description: str = Field(min_length=1, max_length=1200)
    tags: list[str] = Field(default_factory=list, max_length=20)
    area_name: str = Field(min_length=1, max_length=100)
    area_description: str = Field(min_length=1, max_length=800)
    objects: list[_SceneObject] = Field(default_factory=list, max_length=30)


class _PlanActivity(BaseModel):
    title: str = Field(min_length=1, max_length=120)
    description: str = Field(default="", max_length=1000)
    purpose: str = Field(min_length=1, max_length=300)
    start_at: str
    end_at: str
    place_name: str = Field(default="日常起点", max_length=100)
    area_name: str = Field(default="起居室", max_length=100)
    scene_description: str = Field(default="", max_length=500)
    tags: list[str] = Field(default_factory=list, max_length=12)
    objects: list[_SceneObject] = Field(default_factory=list, max_length=12)


class _DailyPlan(BaseModel):
    activities: list[_PlanActivity] = Field(default_factory=list, max_length=16)
    summary: str = Field(default="", max_length=500)


class _ScheduleDecision(BaseModel):
    action: Literal[
        "adjust_agent_schedule", "adjust_shared_activity",
        "cancel_agent_schedule", "cancel_shared_activity",
    ]
    target_schedule_id: str
    new_start_at: str | None = None
    new_end_at: str | None = None
    summary: str = Field(min_length=1, max_length=500)


class SceneService:
    """Manages the place → area → object hierarchy and visited scene pool."""

    INITIAL_ENVIRONMENT_ID = "daily_start"
    INITIAL_PLACE_ID = "daily_home"
    INITIAL_AREA_ID = "home_living"

    def __init__(self, store: Any, model: Any | None = None):
        self.store = store
        self.model = model

    def ensure_initial_environment(self, *, activate: bool = False) -> dict[str, Any]:
        """Create the initial place/area/environment exactly once per DataDisk."""
        env = self.store.get_document("environments", self.INITIAL_ENVIRONMENT_ID)
        if env is None:
            env = self.store.save_document("environments", self.INITIAL_ENVIRONMENT_ID, {
                "name": "日常起点", "details": "林依的日常生活起点，是她熟悉且可以回到的地方。",
                "kind": "scene", "scene_role": "initial", "active": False,
                "created_by": "system.initial_scene",
            })
        place = self.store.get_document("places", self.INITIAL_PLACE_ID)
        if place is None:
            place = self.store.save_document("places", self.INITIAL_PLACE_ID, {
                "name": "家", "description": "温暖、安静的日常居所。",
                "environment_id": self.INITIAL_ENVIRONMENT_ID,
                "tags": ["home", "rest", "study", "daily"], "purpose_tags": ["休息", "学习", "日常"],
                "visited": True, "fixed": True, "layout_frozen": True, "initial": True, "layout": "普通住宅的生活空间。",
            })
        area = self.store.get_document("areas", self.INITIAL_AREA_ID)
        if area is None:
            area = self.store.save_document("areas", self.INITIAL_AREA_ID, {
                "place_id": self.INITIAL_PLACE_ID, "name": "起居室",
                "description": "有一张书桌、柔软的沙发和自然光，是放松与阅读的空间。",
                "visited": True, "fixed": True, "layout_frozen": True,
            })
        if not any(row.get("area_id") == self.INITIAL_AREA_ID for row in self.store.environment_objects(self.INITIAL_ENVIRONMENT_ID, visible_only=False)):
            self.store.save_environment_object("home_desk", {
                "environment_id": self.INITIAL_ENVIRONMENT_ID, "place_id": self.INITIAL_PLACE_ID,
                "area_id": self.INITIAL_AREA_ID, "name": "靠窗书桌",
                "description": "日常阅读和写作时会用到的书桌。", "state": "整洁",
                "priority": 75, "properties": {"material": "木质", "position": "窗边"},
            })
        if activate:
            self.store.activate_environment(self.INITIAL_ENVIRONMENT_ID)
        current = self.current()
        if current is None:
            self._set_current(self.INITIAL_PLACE_ID, self.INITIAL_AREA_ID, None, source="initialization")
        return {"environment": self.store.get_document("environments", self.INITIAL_ENVIRONMENT_ID),
                "place": self.store.get_document("places", self.INITIAL_PLACE_ID),
                "area": self.store.get_document("areas", self.INITIAL_AREA_ID)}

    def places(self, *, visited_only: bool = False) -> list[dict[str, Any]]:
        rows = self.store.list_documents("places")
        if visited_only:
            rows = [row for row in rows if row.get("visited")]
        return rows

    def areas(self, place_id: str | None = None) -> list[dict[str, Any]]:
        rows = self.store.list_documents("areas")
        return [row for row in rows if not place_id or row.get("place_id") == place_id]

    def current(self) -> dict[str, Any] | None:
        return self.store.read_json("/runtime/current-scene.json")

    def current_context(self) -> str:
        current = self.current()
        if not current:
            return "当前场景：日常起点。"
        place = self.store.get_document("places", current.get("place_id", "")) or {}
        area = self.store.get_document("areas", current.get("area_id", "")) or {}
        description = (
            f"当前场景：{place.get('name', '未知地点')} · {area.get('name', '未知区域')}。"
            f"{place.get('description', '')} {area.get('description', '')}"
        ).strip()
        env_id = place.get("environment_id")
        if env_id:
            objects = self.store.environment_objects(env_id, visible_only=True)
            relevant = [item for item in objects if item.get("area_id") == area.get("id")][:8]
            if relevant:
                description += " 场景物件：" + "；".join(
                    f"{item.get('name')}（{item.get('state', '正常')}）" for item in relevant
                ) + "。"
        return description[:1800]

    def resolve_for_activity(self, *, purpose: str, place_hint: str = "", area_hint: str = "",
                             tags: list[str] | None = None, character: dict[str, Any] | None = None,
                             context: str = "", objects: list[dict[str, Any]] | None = None,
                             stable_key: str = "") -> dict[str, Any]:
        if place_hint.strip().casefold() in {"日常起点", "家", "home", "家里"}:
            initial = self.store.get_document("places", self.INITIAL_PLACE_ID)
            area = next((row for row in self.areas(self.INITIAL_PLACE_ID)
                         if not area_hint or area_hint.casefold() in row.get("name", "").casefold()), None)
            if initial and area:
                return {"place": initial, "area": area, "reused": True}
        needle = " ".join([purpose, place_hint, *(tags or [])]).casefold().strip()
        visited = self.places(visited_only=True)
        best: tuple[int, dict[str, Any]] | None = None
        for place in visited:
            corpus = " ".join([place.get("name", ""), place.get("description", ""),
                               *place.get("tags", []), *place.get("purpose_tags", [])]).casefold()
            score = sum(2 for word in re.findall(r"[\w\u4e00-\u9fff]+", needle) if word and word in corpus)
            if place_hint and (place_hint.casefold() in str(place.get("name", "")).casefold()
                               or str(place.get("name", "")).casefold() in place_hint.casefold()):
                score += 8
            if best is None or score > best[0]:
                best = (score, place)
        if best and best[0] > 0:
            place = best[1]
            place_areas = self.areas(place["id"])
            area = next((row for row in place_areas if area_hint and area_hint.casefold() in row.get("name", "").casefold()), None)
            if area is None and place_areas:
                area = place_areas[0]
            if area:
                return {"place": place, "area": area, "reused": True}

        blueprint = self._generate_blueprint(
            purpose=purpose, place_hint=place_hint, area_hint=area_hint,
            character=character or {}, context=context, tags=tags or [], objects=objects or [],
        )
        key = stable_key or f"{blueprint['place_name']}:{blueprint['area_name']}"
        place_id = _stable_id("place", re.sub(r"\s+", "", (key + blueprint["place_name"]).casefold()))
        # A retry after partial persistence reuses the same unvisited generated location.
        existing = self.store.get_document("places", place_id)
        if existing:
            area = next((row for row in self.areas(place_id) if row.get("name") == blueprint["area_name"]), None)
            if area:
                return {"place": existing, "area": area, "reused": True}
        env_id = _stable_id("scene", place_id)
        area_id = _stable_id("area", f"{place_id}:{blueprint['area_name']}")
        if self.store.get_document("environments", env_id) is None:
            self.store.save_document("environments", env_id, {
                "name": blueprint["place_name"], "details": blueprint["place_description"],
                "kind": "scene", "scene_role": "location", "scene_place_id": place_id,
                "active": False,
            })
        place = self.store.save_document("places", place_id, {
            "name": blueprint["place_name"], "description": blueprint["place_description"],
            "environment_id": env_id, "tags": blueprint["tags"],
            "purpose_tags": [purpose], "visited": False, "fixed": False,
            "layout": blueprint["area_description"], "generated_for": purpose,
        })
        area = self.store.save_document("areas", area_id, {
            "place_id": place_id, "name": blueprint["area_name"],
            "description": blueprint["area_description"], "visited": False, "fixed": False,
        })
        object_rows = blueprint["objects"]
        if not object_rows:
            object_rows = objects or []
        for index, item in enumerate(object_rows[:30]):
            name = str(item.get("name", "物件")).strip()
            object_id = _stable_id("obj", f"{place_id}:{area_id}:{name}:{index}")
            if self.store.get_document("environment_objects", object_id) is None:
                self.store.save_environment_object(object_id, {
                    "environment_id": env_id, "place_id": place_id, "area_id": area_id,
                    "name": name, "description": str(item.get("description", "")),
                    "state": str(item.get("state", "正常")),
                    "priority": int(item.get("priority", 50)), "properties": dict(item.get("properties", {})),
                })
        self.store.save_document("scene_audits", _stable_id("audit", f"generated:{place_id}"), {
            "action": "scene.generated", "place_id": place_id, "area_id": area_id,
            "purpose": purpose, "reused": False,
        })
        self.store.append_event("scene.generated", {"place_id": place_id, "area_id": area_id, "purpose": purpose})
        return {"place": place, "area": area, "reused": False}

    def _generate_blueprint(self, *, purpose: str, place_hint: str, area_hint: str,
                            character: dict[str, Any], context: str, tags: list[str],
                            objects: list[dict[str, Any]]) -> dict[str, Any]:
        if self.model is not None:
            prompt_context = {
                "character": {key: character.get(key) for key in ("name", "personality", "background", "worldview", "setting") if character.get(key)},
                "recent_history_and_memory": context[:5000], "activity_purpose": purpose,
                "suggested_place": place_hint, "suggested_area": area_hint, "tags": tags,
            }
            try:
                return _model_result(
                    self.model, _SceneBlueprint,
                    "你为虚拟角色构建一个具体、连续、可复用的日常世界场景。只输出结构化地点、一个细分区域和可交互物体；符合角色设定与世界观，避免夸张跳脱。",
                    json.dumps(prompt_context, ensure_ascii=False),
                )
            except Exception as exc:
                self.store.append_event("scene.generation.failed", {"purpose": purpose, "error_type": type(exc).__name__})
                raise
        # Offline/no-model operation remains usable; each generated description is
        # purpose-specific and deliberately modest rather than claiming model work.
        place_name = place_hint.strip() or self._fallback_place_name(purpose)
        area_name = area_hint.strip() or "主要活动区"
        object_rows = objects or [{"name": "随身物品", "description": f"与“{purpose}”相关的日常物品。", "state": "可用", "priority": 40}]
        return _SceneBlueprint(
            place_name=place_name,
            place_description=f"{place_name}是一个适合{purpose}的日常地点。初次到访后，空间设定与布局固定。",
            tags=list(dict.fromkeys([*tags, purpose]))[:20], area_name=area_name,
            area_description=f"{area_name}是{place_name}中用于{purpose}的区域，布置自然、舒适。",
            objects=object_rows,
        ).model_dump()

    @staticmethod
    def _fallback_place_name(purpose: str) -> str:
        lowered = purpose.casefold()
        if any(word in lowered for word in ("买", "购物", "采购")):
            return "街角便利店"
        if any(word in lowered for word in ("运动", "跑步", "锻炼")):
            return "社区公园"
        if any(word in lowered for word in ("学习", "读书", "自习")):
            return "安静的自习空间"
        if any(word in lowered for word in ("吃饭", "午餐", "晚餐", "咖啡")):
            return "附近的小店"
        return "日常街区"

    def enter(self, place_id: str, area_id: str, *, schedule_id: str | None = None,
              occurred_at: datetime | None = None, source: str = "schedule") -> dict[str, Any]:
        place = self.store.get_document("places", place_id)
        area = self.store.get_document("areas", area_id)
        if not place or not area or area.get("place_id") != place_id:
            raise ValueError("场景地点或区域不存在，或区域不属于该地点")
        moment = occurred_at or datetime.now().astimezone()
        first_visit = not bool(place.get("visited"))
        if first_visit:
            self.store.save_document("places", place_id, {
                "visited": True, "fixed": True, "first_visited_at": moment.isoformat(),
                "layout_frozen": True,
            })
            self.store.save_document("areas", area_id, {
                "visited": True, "fixed": True, "first_visited_at": moment.isoformat(),
                "layout_frozen": True,
            })
        else:
            self.store.save_document("areas", area_id, {"visited": True, "fixed": True})
        environment_id = place.get("environment_id")
        if environment_id and self.store.get_document("environments", environment_id):
            self.store.activate_environment(environment_id)
        previous = self.current()
        current = self._set_current(place_id, area_id, schedule_id, source=source, occurred_at=moment)
        if (not previous or previous.get("place_id") != place_id or previous.get("area_id") != area_id):
            audit_id = _stable_id("audit", f"switch:{schedule_id}:{place_id}:{area_id}:{moment.isoformat()}")
            self.store.save_document("scene_audits", audit_id, {
                "action": "scene.switched", "schedule_id": schedule_id,
                "from_place_id": previous.get("place_id") if previous else None,
                "to_place_id": place_id, "to_area_id": area_id,
                "first_visit": first_visit, "occurred_at": moment.isoformat(), "source": source,
            })
            self.store.append_event("scene.switched", {"schedule_id": schedule_id, "place_id": place_id, "area_id": area_id, "first_visit": first_visit})
        return current

    def _set_current(self, place_id: str, area_id: str, schedule_id: str | None,
                     *, source: str, occurred_at: datetime | None = None) -> dict[str, Any]:
        now = occurred_at or datetime.now().astimezone()
        current = {"place_id": place_id, "area_id": area_id, "schedule_id": schedule_id,
                   "source": source, "active_since": now.isoformat(), "local_date": now.date().isoformat()}
        self.store.write_json("/runtime/current-scene.json", current)
        return current

    def return_to_initial(self, *, occurred_at: datetime | None = None, reason: str = "day_end") -> dict[str, Any]:
        self.ensure_initial_environment(activate=False)
        return self.enter(self.INITIAL_PLACE_ID, self.INITIAL_AREA_ID,
                          occurred_at=occurred_at, source=reason)

    def update_object_state(self, object_id: str, *, state: str,
                            properties: dict[str, Any] | None = None) -> dict[str, Any]:
        item = self.store.get_document("environment_objects", object_id)
        if item is None:
            raise KeyError(f"未知场景物体：{object_id}")
        return self.store.save_environment_object(object_id, {
            **item, "state": str(state)[:300],
            "properties": {**item.get("properties", {}), **(properties or {})},
        })


class DailyItineraryService:
    """Generate one non-overlapping, local-time Agent itinerary per calendar day."""

    def __init__(self, store: Any, model: Any | None = None, scene_service: SceneService | None = None):
        self.store = store
        self.model = model
        self.scenes = scene_service or SceneService(store, model=model)

    def ensure_for_day(self, *, now: datetime | None = None,
                       character: dict[str, Any] | None = None,
                       model: Any | None = None) -> dict[str, Any]:
        moment = now or datetime.now().astimezone()
        if moment.tzinfo is None:
            raise ValueError("now must be timezone-aware")
        local_now = moment.astimezone()
        day = local_now.date()
        tz_name = getattr(local_now.tzinfo, "key", None) or local_now.tzname() or "local"
        itinerary_id = "day_" + day.strftime("%Y%m%d")
        existing = self.store.get_document("itineraries", itinerary_id)
        if existing and existing.get("status") == "generated":
            return existing
        if existing and existing.get("status") == "failed":
            retry_at = existing.get("retry_at")
            if retry_at and _parse_dt(retry_at) > local_now:
                return existing
        profile = character or self._active_character()
        active_model = model or self.model
        attempt = int((existing or {}).get("attempts", 0)) + 1
        base = {
            "local_date": day.isoformat(), "timezone": tz_name,
            "status": "generating", "attempts": attempt,
            "schedule_ids": list((existing or {}).get("schedule_ids", [])),
        }
        persisted_activities = list((existing or {}).get("activities", []))
        persisted_summary = str((existing or {}).get("summary", ""))
        materialized_schedule_ids = list((existing or {}).get("schedule_ids", []))
        self.store.save_document("itineraries", itinerary_id, {**(existing or {}), **base})
        try:
            self.scenes.ensure_initial_environment()
            context = self._world_context(profile, day, active_model)
            # Persist the normalized full-day plan before materializing any
            # schedule or scene. If a later write fails, retries use the same
            # plan and stable keys instead of generating a second world.
            stored_activities = (existing or {}).get("activities")
            if stored_activities:
                plan = {"summary": (existing or {}).get("summary", ""), "activities": stored_activities}
            else:
                plan = self._generate_plan(local_now, profile, context, active_model)
                normalized = [item if isinstance(item, dict) else item.model_dump() for item in plan.get("activities", [])]
                persisted_activities = normalized
                persisted_summary = str(plan.get("summary", ""))
                self.store.save_document("itineraries", itinerary_id, {**base, "activities": normalized, "summary": persisted_summary})
            activities = self._remaining_activities(plan, local_now)
            # Validate no overlap before any schedule or scene record is created.
            ordered = sorted(activities, key=lambda item: _parse_dt(item["start_at"]))
            previous_end: datetime | None = None
            for item in ordered:
                start = _parse_dt(item["start_at"]).astimezone(local_now.tzinfo)
                end = _parse_dt(item["end_at"]).astimezone(local_now.tzinfo)
                if start.date() != day or end.date() != day or end <= start:
                    raise ValueError("每日行程必须位于本地当天且结束时间晚于开始时间")
                if previous_end and start < previous_end:
                    raise ValueError("模型生成的 Agent 行程存在时间重叠")
                previous_end = end
            schedule_ids: list[str] = []
            for item in ordered:
                activity_key = f"{day.isoformat()}:{item['title']}:{item.get('_original_start_at', item['start_at'])}:{item['purpose']}"
                scene = self.scenes.resolve_for_activity(
                    purpose=item["purpose"], place_hint=item.get("place_name", ""),
                    area_hint=item.get("area_name", ""), tags=item.get("tags", []),
                    character=profile or {}, context=context,
                    objects=item.get("objects", []),
                    stable_key=activity_key,
                )
                schedule_id = _stable_id("plan", activity_key)
                if self.store.get_schedule(schedule_id) is None:
                    self.store.create_schedule(schedule_id, {
                        "title": item["title"], "description": item.get("description", ""),
                        "due_at": item["start_at"], "end_at": item["end_at"], "type": "activity",
                        "category": "agent", "owner": "agent", "participants": ["agent"],
                        "schedule_source": "autonomous_daily_itinerary", "itinerary_id": itinerary_id,
                        "purpose": item["purpose"], "place_id": scene["place"]["id"],
                        "area_id": scene["area"]["id"], "scene_binding": True,
                        "status": "pending", "is_queryable": True,
                    }, actor="agent")
                schedule_ids.append(schedule_id)
                materialized_schedule_ids = list(schedule_ids)
            generated = self.store.save_document("itineraries", itinerary_id, {
                **base, "status": "generated", "schedule_ids": schedule_ids,
                "activities": persisted_activities or plan.get("activities", []),
                "summary": persisted_summary or plan.get("summary", ""), "generated_at": local_now.isoformat(),
                "error": None, "retry_at": None,
            })
            self.store.append_event("itinerary.generated", {
                "itinerary_id": itinerary_id, "local_date": day.isoformat(),
                "timezone": tz_name, "schedule_count": len(schedule_ids), "late_start": local_now.time() > time(0, 5),
            })
            return generated
        except Exception as exc:
            retry_at = local_now + timedelta(minutes=min(60, 5 * attempt))
            failed = self.store.save_document("itineraries", itinerary_id, {
                **base, "status": "failed", "schedule_ids": materialized_schedule_ids,
                "activities": persisted_activities,
                "summary": persisted_summary,
                "error": f"{type(exc).__name__}: {exc}"[:1000], "retry_at": retry_at.isoformat(),
                "failed_at": local_now.isoformat(),
            })
            self.store.append_event("itinerary.generation.failed", {
                "itinerary_id": itinerary_id, "error_type": type(exc).__name__, "retry_at": retry_at.isoformat(),
            })
            return failed

    def _active_character(self) -> dict[str, Any] | None:
        from neo_agent.runtime.control import SingleRoleService
        return SingleRoleService(self.store).active()

    def _world_context(self, character: dict[str, Any] | None, day: date, model: Any | None) -> str:
        profile = character or {}
        parts = ["角色设定：" + json.dumps({key: profile.get(key) for key in ("name", "personality", "background", "worldview", "setting") if profile.get(key)}, ensure_ascii=False)]
        conversations = self.store.recent_conversation_context(limit=12) if hasattr(self.store, "recent_conversation_context") else ""
        if conversations:
            parts.append("近期对话：" + conversations)
        # Vector recall is grounded in activities and current setting; failure to
        # access memory never prevents the rest of the day from being scheduled.
        try:
            query = "今天的生活安排、兴趣、学习和外出地点 " + " ".join(str(profile.get(key, "")) for key in ("personality", "background"))
            memories = self.store.search_memories(query, limit=8)
            if memories:
                parts.append("相关记忆：" + "；".join(str(item.get("text", ""))[:240] for item in memories))
        except Exception:
            pass
        parts.append(f"计划日期：{day.isoformat()}，时区：{datetime.now().astimezone().tzname()}")
        return "\n".join(parts)[:8000]

    def _generate_plan(self, now: datetime, character: dict[str, Any] | None,
                       context: str, model: Any | None) -> dict[str, Any]:
        if model is not None:
            local_day = now.date().isoformat()
            start = now.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
            end = (now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)).isoformat()
            prompt = {
                "character_name": (character or {}).get("name", "虚拟群友"),
                "local_date": local_day, "timezone": str(now.tzinfo),
                "now": now.isoformat(), "day_start": start, "day_end": end,
                "context": context,
                "instructions": "规划自然、可执行的一天；只安排当前时刻及以后。可安排休息、学习、兴趣、外出。每项给明确本地时区起止时间、目的和场所区域。不得安排与用户共同活动，除非对话明确说明共同参与。",
            }
            return _model_result(model, _DailyPlan, "你是角色的自主生活行程规划器。请只输出结构化计划。时间必须使用给定机器本地时区的 ISO-8601。", json.dumps(prompt, ensure_ascii=False))
        return {"summary": "离线模式下按角色日常节奏生成的基础行程。", "activities": self._template_activities(now)}

    @staticmethod
    def _template_activities(now: datetime) -> list[dict[str, Any]]:
        local = now.astimezone()
        day = local.date()
        zone = local.tzinfo
        windows = [
            (time(8, 0), time(8, 30), "整理与早餐", "吃早餐并整理一天的安排", "日常起点", "起居室", ["home", "breakfast"]),
            (time(9, 0), time(11, 0), "学习与阅读", "安静地学习、阅读或完成手边的事情", "安静的自习空间", "阅读区", ["study", "reading"]),
            (time(12, 0), time(13, 0), "午餐与休息", "吃午餐，稍微放松一下", "附近的小店", "用餐区", ["meal", "rest"]),
            (time(15, 0), time(16, 0), "散步透气", "去附近走走，看看街景和树木", "社区公园", "林荫步道", ["walk", "outdoor"]),
            (time(19, 0), time(20, 0), "晚间放松", "回到熟悉的地方听音乐或看看书", "日常起点", "起居室", ["home", "rest"]),
        ]
        rows = []
        for start_t, end_t, title, purpose, place, area, tags in windows:
            start = datetime.combine(day, start_t, tzinfo=zone)
            end = datetime.combine(day, end_t, tzinfo=zone)
            rows.append({"title": title, "description": purpose, "purpose": purpose,
                         "start_at": start.isoformat(), "end_at": end.isoformat(),
                         "place_name": place, "area_name": area, "tags": tags, "objects": []})
        return rows

    @staticmethod
    def _remaining_activities(plan: dict[str, Any], now: datetime) -> list[dict[str, Any]]:
        remaining = []
        for source in plan.get("activities", []):
            item = source if isinstance(source, dict) else source.model_dump()
            start, end = _parse_dt(item["start_at"]).astimezone(now.tzinfo), _parse_dt(item["end_at"]).astimezone(now.tzinfo)
            if end <= now:
                continue
            if start < now:
                start = now
            remaining.append({**item, "_original_start_at": item["start_at"],
                              "start_at": start.isoformat(), "end_at": end.isoformat()})
        return remaining


class ScheduleDecisionService:
    """Resolve shared-activity conflicts without ever mutating user schedules."""

    def __init__(self, store: Any, model: Any | None = None):
        self.store = store
        self.model = model

    @staticmethod
    def _interval(schedule: dict[str, Any]) -> tuple[datetime, datetime] | None:
        if not schedule.get("due_at") or not schedule.get("end_at"):
            return None
        return _parse_dt(schedule["due_at"]), _parse_dt(schedule["end_at"])

    def conflicts(self, *, now: datetime | None = None) -> list[dict[str, Any]]:
        moment = now or datetime.now().astimezone()
        active = [row for row in self.store.schedules() if row.get("status") not in {"cancelled", "rejected", "completed", "deleted"}]
        shared = [row for row in active if row.get("category", "agent") == "shared"]
        result = []
        for common in shared:
            common_interval = self._interval(common)
            if not common_interval:
                continue
            for other in active:
                if other["id"] == common["id"]:
                    continue
                category = other.get("category", "agent")
                if category not in {"agent", "user"}:
                    continue
                interval = self._interval(other)
                if not interval:
                    continue
                if common_interval[0] < interval[1] and interval[0] < common_interval[1]:
                    result.append({"shared": common, "conflict": other, "conflict_type": category,
                                   "detected_at": moment.isoformat()})
        return result

    def coordinate(self, *, now: datetime | None = None, limit: int = 32) -> list[dict[str, Any]]:
        decisions = []
        for conflict in self.conflicts(now=now)[:limit]:
            shared, other = conflict["shared"], conflict["conflict"]
            current_id = _stable_id("decision", f"{shared['id']}:{other['id']}:{shared['due_at']}:{other['due_at']}", length=12)
            existing = self.store.get_document("schedule_decisions", current_id)
            if existing and existing.get("status") == "applied":
                continue
            decision = self._decide(shared, other, conflict["conflict_type"])
            target_id = decision["target_schedule_id"]
            target = self.store.get_schedule(target_id)
            if target is None or target.get("category", "agent") == "user":
                raise ValueError("ScheduleDecision 不允许修改用户个人日程")
            if decision["action"].startswith("cancel_"):
                self.store.update_schedule(target_id, {"status": "cancelled", "decision_id": current_id}, actor="agent")
            else:
                if not decision.get("new_start_at") or not decision.get("new_end_at"):
                    raise ValueError("调整日程的决定必须包含新的起止时间")
                self.store.update_schedule(target_id, {
                    "due_at": decision["new_start_at"], "end_at": decision["new_end_at"],
                    "decision_id": current_id, "schedule_source": "autonomous_conflict_resolution",
                }, actor="agent")
            audit = self.store.save_document("schedule_decisions", current_id, {
                "status": "applied", "conflict_type": conflict["conflict_type"],
                "shared_schedule_id": shared["id"], "conflicting_schedule_id": other["id"],
                **decision, "applied_at": (now or datetime.now().astimezone()).isoformat(),
                "immutable_user_schedule": conflict["conflict_type"] == "user",
                "explanation_pending": True,
            })
            self.store.append_event("schedule.conflict.decided", {
                "decision_id": current_id, "action": decision["action"],
                "target_schedule_id": target_id, "risk": "medium",
            })
            decisions.append(audit)
        return decisions

    def _decide(self, shared: dict[str, Any], other: dict[str, Any], conflict_type: str) -> dict[str, Any]:
        if self.model is not None:
            prompt = {"shared_activity": self._public_schedule(shared),
                      "conflicting_schedule": self._public_schedule(other),
                      "conflict_type": conflict_type,
                      "policy": "不得修改用户个人日程；可以调整或取消Agent个人行程或双方共同活动；共同活动变化应保存透明摘要，禁止静默假定用户接受。"}
            result = _model_result(self.model, _ScheduleDecision,
                                   "你负责自主协调角色日历冲突。选择对关系影响较小且诚实的调整，只输出结构化决定。",
                                   json.dumps(prompt, ensure_ascii=False))
            target = self.store.get_schedule(result["target_schedule_id"])
            allowed_ids = {shared["id"]}
            if other.get("category", "agent") == "agent":
                allowed_ids.add(other["id"])
            if result["target_schedule_id"] not in allowed_ids:
                raise ValueError("模型决定越权修改无关日程")
            if target and target.get("category", "agent") == "user":
                raise ValueError("模型决定试图修改用户个人日程")
            return result
        # Conservative autonomous fallback: preserve the user's calendar by
        # moving/cancelling the shared commitment; otherwise move Agent's item.
        target = shared if conflict_type == "user" else other
        interval = self._interval(target)
        assert interval is not None
        duration = interval[1] - interval[0]
        candidate = max(interval[1], self._interval(shared)[1]) + timedelta(minutes=15)
        for _ in range(48):
            candidate_end = candidate + duration
            overlapping = any(
                row["id"] not in {shared["id"], other["id"]}
                and row.get("status") not in {"cancelled", "rejected", "completed"}
                and self._interval(row)
                and candidate < self._interval(row)[1] and self._interval(row)[0] < candidate_end
                for row in self.store.schedules()
            )
            if not overlapping:
                return {"action": "adjust_shared_activity" if target is shared else "adjust_agent_schedule",
                        "target_schedule_id": target["id"], "new_start_at": candidate.isoformat(),
                        "new_end_at": candidate_end.isoformat(),
                        "summary": "发现日程冲突，已为保留原有承诺而调整此行程；会在合适的对话中说明。"}
            candidate = candidate_end + timedelta(minutes=15)
        return {"action": "cancel_shared_activity" if target is shared else "cancel_agent_schedule",
                "target_schedule_id": target["id"], "summary": "当天没有合适的替代时段，因此取消了冲突行程；会在合适的对话中说明。"}

    @staticmethod
    def _public_schedule(row: dict[str, Any]) -> dict[str, Any]:
        return {key: row.get(key) for key in ("id", "title", "description", "due_at", "end_at", "category", "participants", "purpose")}


class SceneScheduler:
    """Startup recovery and due-time scene transitions; never delivers reminders."""

    def __init__(self, store: Any, *, model: Any | None = None,
                 itinerary: DailyItineraryService | None = None,
                 scenes: SceneService | None = None,
                 decisions: ScheduleDecisionService | None = None):
        self.store = store
        self.scenes = scenes or SceneService(store, model=model)
        self.itinerary = itinerary or DailyItineraryService(store, model=model, scene_service=self.scenes)
        self.decisions = decisions or ScheduleDecisionService(store, model=model)
        self._last_itinerary_check: str | None = None

    def run_once(self, *, now: datetime | None = None,
                 character: dict[str, Any] | None = None,
                 generate: bool = True) -> list[dict[str, Any]]:
        moment = now or datetime.now().astimezone()
        if moment.tzinfo is None:
            raise ValueError("scene scheduler requires timezone-aware time")
        moment = moment.astimezone()
        self.scenes.ensure_initial_environment(activate=False)
        actions: list[dict[str, Any]] = []
        if generate:
            itinerary = self.itinerary.ensure_for_day(now=moment, character=character)
            actions.append({"kind": "itinerary", "status": itinerary.get("status"), "id": itinerary.get("id")})
        for decision in self.decisions.coordinate(now=moment):
            actions.append({"kind": "decision", "id": decision["id"]})
        day_start = datetime.combine(moment.date(), time.min, tzinfo=moment.tzinfo)
        tomorrow = day_start + timedelta(days=1)
        todays = []
        for row in self.store.schedules():
            if row.get("category", "agent") not in {"agent", "shared"}:
                continue
            if not row.get("scene_binding") or not row.get("place_id") or not row.get("area_id"):
                continue
            if row.get("status") in {"cancelled", "rejected", "completed", "deleted"}:
                continue
            try:
                start_at = _parse_dt(row["due_at"]).astimezone(moment.tzinfo)
                if row.get("end_at"):
                    end_at = _parse_dt(row["end_at"]).astimezone(moment.tzinfo)
                    if end_at <= start_at:
                        raise ValueError("end_at must be after due_at")
                place = self.store.get_document("places", row["place_id"])
                area = self.store.get_document("areas", row["area_id"])
                if not place or not area or area.get("place_id") != place.get("id"):
                    raise ValueError("scene binding references a missing or mismatched place/area")
            except (KeyError, TypeError, ValueError) as exc:
                self._record_schedule_error(row, exc, moment)
                continue
            if day_start <= start_at < tomorrow:
                todays.append((start_at, row))
        todays.sort(key=lambda pair: pair[0])
        target = None
        for index, (start_at, row) in enumerate(todays):
            if start_at > moment:
                break
            next_start = todays[index + 1][0] if index + 1 < len(todays) else tomorrow
            try:
                explicit_end = _parse_dt(row["end_at"]).astimezone(moment.tzinfo) if row.get("end_at") else None
            except (TypeError, ValueError) as exc:
                self._record_schedule_error(row, exc, moment)
                continue
            effective_end = explicit_end if explicit_end else next_start
            if moment < effective_end:
                target = row
        current = self.scenes.current()
        if target:
            if not current or current.get("schedule_id") != target["id"]:
                self.scenes.enter(target["place_id"], target["area_id"], schedule_id=target["id"], occurred_at=moment)
                actions.append({"kind": "scene", "schedule_id": target["id"], "place_id": target["place_id"]})
        else:
            if not current or current.get("local_date") != moment.date().isoformat() or current.get("place_id") != SceneService.INITIAL_PLACE_ID:
                self.scenes.return_to_initial(occurred_at=moment, reason="day_start_or_scene_gap")
                actions.append({"kind": "scene", "place_id": SceneService.INITIAL_PLACE_ID})
        return actions


    def _record_schedule_error(self, row: dict[str, Any], exc: Exception, moment: datetime) -> None:
        """Persist a visible, deduplicated failure without stopping other transitions."""
        schedule_id = str(row.get("id", "unknown"))
        summary = f"{type(exc).__name__}: {exc}"[:300]
        audit_id = _stable_id("audit", f"scene.scheduler.error:{schedule_id}:{summary}")
        if self.store.get_document("scene_audits", audit_id) is None:
            self.store.save_document("scene_audits", audit_id, {
                "action": "scene.scheduler.error", "schedule_id": schedule_id,
                "summary": summary, "occurred_at": moment.isoformat(),
            })
            self.store.append_event("scene.scheduler.error", {
                "schedule_id": schedule_id, "error_type": type(exc).__name__,
                "summary": summary,
            })
        itinerary_id = row.get("itinerary_id")
        if itinerary_id:
            itinerary = self.store.get_document("itineraries", itinerary_id)
            if itinerary is not None:
                retry_at = moment + timedelta(minutes=15)
                self.store.save_document("itineraries", itinerary_id, {
                    **itinerary, "status": "failed", "error": summary,
                    "retry_at": retry_at.isoformat(), "failed_at": moment.isoformat(),
                })
