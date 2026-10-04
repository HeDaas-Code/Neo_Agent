from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from neo_agent.runtime import DailyItineraryService, SceneScheduler, SceneService
from neo_agent.storage import DiskStore


def _local(day_offset: int = 1, hour: int = 7, minute: int = 0) -> datetime:
    now = datetime.now().astimezone()
    day = now.date() + timedelta(days=day_offset)
    return datetime.combine(day, datetime.min.time(), tzinfo=now.tzinfo).replace(hour=hour, minute=minute)


def test_initial_scene_is_idempotent_and_survives_reopen():
    with TemporaryDirectory() as directory:
        image = str(Path(directory) / "agent.vdisk")
        store = DiskStore.open(image)
        scenes = SceneService(store)
        first = scenes.ensure_initial_environment()
        second = scenes.ensure_initial_environment()
        assert first["place"]["id"] == second["place"]["id"] == "daily_home"
        assert len(store.list_documents("places")) == 1
        assert len(store.list_documents("areas")) == 1
        assert scenes.current()["place_id"] == "daily_home"
        store.close()

        store = DiskStore.open(image)
        scenes = SceneService(store)
        assert scenes.current()["area_id"] == "home_living"
        assert "起居室" in scenes.current_context()
        assert len(store.environment_objects("daily_start", visible_only=False)) == 1
        store.close()


def test_daily_itinerary_is_idempotent_and_late_start_only_materializes_future():
    with TemporaryDirectory() as directory:
        store = DiskStore.open(str(Path(directory) / "agent.vdisk"))
        now = _local(hour=10)
        service = DailyItineraryService(store)
        first = service.ensure_for_day(now=now)
        second = service.ensure_for_day(now=now + timedelta(minutes=1))
        assert first["status"] == second["status"] == "generated"
        assert first["id"] == second["id"]
        schedules = [store.get_schedule(item) for item in first["schedule_ids"]]
        assert schedules
        assert all(datetime.fromisoformat(row["due_at"]) >= now for row in schedules)
        assert all(row["category"] == "agent" and row["scene_binding"] for row in schedules)
        assert len({row["id"] for row in schedules}) == len(schedules)
        assert all(row["schedule_source"] == "autonomous_daily_itinerary" for row in schedules)
        store.close()


def test_generation_failure_is_visible_and_respects_retry_window():
    class BrokenModel:
        def with_structured_output(self, _schema):
            return self

        def invoke(self, _messages):
            raise RuntimeError("model unavailable")

    with TemporaryDirectory() as directory:
        store = DiskStore.open(str(Path(directory) / "agent.vdisk"))
        now = _local()
        service = DailyItineraryService(store, model=BrokenModel())
        failed = service.ensure_for_day(now=now)
        assert failed["status"] == "failed"
        assert "model unavailable" in failed["error"]
        assert failed["retry_at"]
        assert failed["attempts"] == 1
        retried = service.ensure_for_day(now=now + timedelta(minutes=1))
        assert retried["attempts"] == 1
        assert retried["retry_at"] == failed["retry_at"]
        assert not store.schedules()
        store.close()


def test_first_scene_visit_freezes_place_and_area_but_object_state_can_change():
    with TemporaryDirectory() as directory:
        store = DiskStore.open(str(Path(directory) / "agent.vdisk"))
        scenes = SceneService(store)
        scene = scenes.resolve_for_activity(purpose="学习", place_hint="自习室", area_hint="阅读区", stable_key="study")
        place_id, area_id = scene["place"]["id"], scene["area"]["id"]
        scenes.enter(place_id, area_id)
        assert store.get_document("places", place_id)["layout_frozen"] is True
        assert store.get_document("areas", area_id)["layout_frozen"] is True
        obj = next(row for row in store.list_documents("environment_objects") if row.get("place_id") == place_id)
        scenes.update_object_state(obj["id"], state="正在使用")
        assert store.get_document("environment_objects", obj["id"])["state"] == "正在使用"
        store.close()


def test_user_schedule_cannot_bind_scene_or_be_modified_by_agent():
    with TemporaryDirectory() as directory:
        store = DiskStore.open(str(Path(directory) / "agent.vdisk"))
        scenes = SceneService(store)
        scene = scenes.ensure_initial_environment()
        due = _local().isoformat()
        with pytest.raises(ValueError, match="user personal schedules cannot drive"):
            store.create_schedule("user-scene", {
                "title": "用户安排", "due_at": due, "category": "user",
                "place_id": scene["place"]["id"], "area_id": scene["area"]["id"],
                "scene_binding": True,
            })
        user_row = store.create_schedule("user-readonly", {
            "title": "用户安排", "due_at": due, "category": "user", "participants": ["user"],
        })
        with pytest.raises(ValueError, match="cannot modify user"):
            store.update_schedule(user_row["id"], {"title": "被修改"}, actor="agent")
        store.close()


def test_scheduler_switches_and_returns_to_initial_without_notifications():
    with TemporaryDirectory() as directory:
        store = DiskStore.open(str(Path(directory) / "agent.vdisk"))
        scenes = SceneService(store)
        initial = scenes.ensure_initial_environment()
        other = scenes.resolve_for_activity(purpose="散步", place_hint="公园", area_hint="步道", stable_key="walk")
        start = _local(hour=9)
        schedule = store.create_schedule("walk-today", {
            "title": "去公园散步", "due_at": start.isoformat(),
            "end_at": (start + timedelta(hours=1)).isoformat(), "category": "agent",
            "participants": ["agent"], "scene_binding": True,
            "place_id": other["place"]["id"], "area_id": other["area"]["id"],
        })
        scheduler = SceneScheduler(store, scenes=scenes)
        actions = scheduler.run_once(now=start + timedelta(minutes=1), generate=False)
        assert any(action.get("schedule_id") == schedule["id"] for action in actions)
        assert scenes.current()["place_id"] == other["place"]["id"]
        scheduler.run_once(now=start + timedelta(hours=2), generate=False)
        assert scenes.current()["place_id"] == initial["place"]["id"]
        event_names = [str(row.get("message", "")).casefold() for row in store.events()]
        assert not any("reminder" in name or "notification" in name for name in event_names)
        store.close()


def test_scheduler_skips_malformed_bound_item_and_records_visible_error():
    with TemporaryDirectory() as directory:
        store = DiskStore.open(str(Path(directory) / "agent.vdisk"))
        scenes = SceneService(store)
        scenes.ensure_initial_environment()
        # Corruption is injected via PyVDisk VFS to exercise runtime recovery.
        store.write_json("/schedules/bad-schedule.json", {
            "id": "bad-schedule", "title": "坏数据", "due_at": "not-a-date",
            "category": "agent", "scene_binding": True,
            "place_id": "missing", "area_id": "missing",
        })
        scheduler = SceneScheduler(store, scenes=scenes)
        scheduler.run_once(now=_local(hour=8), generate=False)
        audits = store.list_documents("scene_audits")
        assert any(row.get("action") == "scene.scheduler.error" for row in audits)
        before = len([row for row in store.events() if row.get("message") == "scene.scheduler.error"])
        scheduler.run_once(now=_local(hour=8, minute=1), generate=False)
        after = len([row for row in store.events() if row.get("message") == "scene.scheduler.error"])
        assert after == before
        store.close()


def test_reopen_restores_generated_itinerary_and_scene_binding():
    with TemporaryDirectory() as directory:
        image = str(Path(directory) / "agent.vdisk")
        store = DiskStore.open(image)
        itinerary = DailyItineraryService(store).ensure_for_day(now=_local(hour=6))
        ids = itinerary["schedule_ids"]
        assert ids
        store.close()
        store = DiskStore.open(image)
        restored = store.get_document("itineraries", itinerary["id"])
        assert restored["schedule_ids"] == ids
        assert all(store.get_schedule(item)["scene_binding"] for item in ids)
        store.close()


def test_tui_environment_view_shows_scene_pool_and_current_context():
    import asyncio
    from textual.widgets import Static
    from neo_agent.ui.tui import NeoConsole

    async def scenario():
        with TemporaryDirectory() as directory:
            store = DiskStore.open(str(Path(directory) / "agent.vdisk"))
            scenes = SceneService(store)
            scenes.ensure_initial_environment(activate=True)
            app = NeoConsole(store)
            async with app.run_test(size=(140, 50)) as pilot:
                await pilot.press("8")  # 环境与域
                await pilot.pause()
                rendered = str(app.query_one("#scene-pool", Static).render())
                assert "当前场景" in rendered
                assert "日常起点" in rendered or "起居室" in rendered
                assert "日常场景池" in rendered or "场景池" in rendered
            store.close()

    asyncio.run(scenario())


def test_unbounded_scene_schedule_runs_until_next_scene_and_day_end():
    with TemporaryDirectory() as directory:
        store = DiskStore.open(str(Path(directory) / "agent.vdisk"))
        scenes = SceneService(store)
        initial = scenes.ensure_initial_environment()
        first = scenes.resolve_for_activity(purpose="阅读", place_hint="图书馆", area_hint="阅览区", stable_key="library")
        second = scenes.resolve_for_activity(purpose="散步", place_hint="公园", area_hint="草地", stable_key="park")
        day = _local(hour=0).date()
        zone = _local().tzinfo
        start_one = datetime.combine(day, datetime.min.time(), tzinfo=zone).replace(hour=9)
        start_two = start_one.replace(hour=11)
        for schedule_id, title, start, scene in (
            ("open-library", "阅读", start_one, first),
            ("open-park", "散步", start_two, second),
        ):
            store.create_schedule(schedule_id, {
                "title": title, "due_at": start.isoformat(), "category": "agent",
                "participants": ["agent"], "scene_binding": True,
                "place_id": scene["place"]["id"], "area_id": scene["area"]["id"],
            })
        scheduler = SceneScheduler(store, scenes=scenes)
        scheduler.run_once(now=start_one + timedelta(hours=1), generate=False)
        assert scenes.current()["place_id"] == first["place"]["id"]
        scheduler.run_once(now=start_two + timedelta(minutes=1), generate=False)
        assert scenes.current()["place_id"] == second["place"]["id"]
        next_day = datetime.combine(day + timedelta(days=1), datetime.min.time(), tzinfo=zone)
        scheduler.run_once(now=next_day, generate=False)
        assert scenes.current()["place_id"] == initial["place"]["id"]
        store.close()


def test_shared_conflict_autonomously_moves_commitment_without_changing_user_calendar():
    from neo_agent.runtime import ScheduleDecisionService

    with TemporaryDirectory() as directory:
        store = DiskStore.open(str(Path(directory) / "agent.vdisk"))
        start = _local(hour=14)
        shared = store.create_schedule("shared-conflict", {
            "title": "一起看电影", "due_at": start.isoformat(),
            "end_at": (start + timedelta(hours=2)).isoformat(),
            "category": "shared", "participants": ["agent", "user"],
        })
        user = store.create_schedule("user-conflict", {
            "title": "用户自己的安排", "due_at": (start + timedelta(minutes=30)).isoformat(),
            "end_at": (start + timedelta(hours=1)).isoformat(),
            "category": "user", "participants": ["user"],
        })
        decision = ScheduleDecisionService(store).coordinate(now=start)
        assert decision and decision[0]["status"] == "applied"
        assert decision[0]["action"] == "adjust_shared_activity"
        assert store.get_schedule(user["id"])["due_at"] == user["due_at"]
        assert store.get_schedule(shared["id"])["due_at"] != shared["due_at"]
        assert decision[0]["immutable_user_schedule"] is True
        assert decision[0]["explanation_pending"] is True
        store.close()


def test_agent_conflict_resolution_adjusts_agent_not_shared_commitment():
    from neo_agent.runtime import ScheduleDecisionService

    with TemporaryDirectory() as directory:
        store = DiskStore.open(str(Path(directory) / "agent.vdisk"))
        start = _local(hour=14)
        shared = store.create_schedule("shared-agent-conflict", {
            "title": "约好一起吃饭", "due_at": start.isoformat(),
            "end_at": (start + timedelta(hours=2)).isoformat(),
            "category": "shared", "participants": ["agent", "user"],
        })
        agent = store.create_schedule("agent-conflict", {
            "title": "自主学习", "due_at": (start + timedelta(minutes=30)).isoformat(),
            "end_at": (start + timedelta(hours=1)).isoformat(),
            "category": "agent", "participants": ["agent"],
        })
        decision = ScheduleDecisionService(store).coordinate(now=start)
        assert decision and decision[0]["action"] == "adjust_agent_schedule"
        assert store.get_schedule(shared["id"])["due_at"] == shared["due_at"]
        assert store.get_schedule(agent["id"])["due_at"] != agent["due_at"]
        store.close()


def test_tui_remains_responsive_while_startup_scene_scheduler_is_slow():
    import asyncio
    from threading import Event
    from neo_agent.ui.tui import NeoConsole

    async def scenario():
        with TemporaryDirectory() as directory:
            store = DiskStore.open(str(Path(directory) / "agent.vdisk"))
            from neo_agent.runtime import SingleRoleService
            SingleRoleService(store).save_initial("sample", {"name": "林依", "personality": "温柔友善"})
            app = NeoConsole(store)
            started = Event()
            release = Event()

            def slow_scheduler(**_kwargs):
                started.set()
                release.wait(timeout=5)
                return []

            app.scene_scheduler.run_once = slow_scheduler
            try:
                async with app.run_test(size=(140, 50)) as pilot:
                    await pilot.pause(0.1)
                    assert started.is_set()
                    # This used to hang because on_mount called run_once inline.
                    await pilot.press("8")
                    assert app.active_view == "环境与域"
            finally:
                release.set()
                await asyncio.sleep(0.1)
                store.close()

    asyncio.run(scenario())
