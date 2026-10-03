from __future__ import annotations

import tempfile

import pytest
from pathlib import Path

from neo_agent.storage import DiskStore
from neo_agent.tools import make_langchain_tools


def test_store_reopens_and_persists_documents():
    with tempfile.TemporaryDirectory() as directory:
        image = str(Path(directory) / "agent.vdisk")
        store = DiskStore.open(image)
        store.write_json("/characters/lin/profile.json", {"name": "小林", "status": "active"})
        assert store.characters() == [{"name": "小林", "status": "active"}]
        store.close()

        reopened = DiskStore.open(image)
        assert reopened.read_json("/characters/lin/profile.json")["name"] == "小林"
        assert reopened.runtime_overview()["audit"]["ok"] is True
        reopened.close()


def test_event_and_task_workspaces_are_confined_to_pyvdisk_vfs_and_reopen():
    with tempfile.TemporaryDirectory() as directory:
        image = Path(directory) / "agent.vdisk"
        store = DiskStore.open(str(image))
        event = store.create_event_record("event-work", {"title": "活动计划"})
        task = store.save_document("workflows", "task-work", {
            "kind": "multi_agent_task", "status": "running", "workspace": "/host/escape",
        })
        event_ws = store.event_workspace(event["id"])
        task_ws = store.task_workspace(task["id"])
        event_ws.write_json("notes/brief.json", {"title": "活动准备"})
        task_ws.write_text("outputs/result.txt", "结果保存在 PyVDisk VFS")

        assert event["workspace"] == "/workspaces/events/event-work"
        assert task["workspace"] == "/workspaces/tasks/task-work"
        assert store.get_document("workflows", "task-work")["workspace"] == task["workspace"]
        assert event_ws.read_json("notes/brief.json") == {"title": "活动准备"}
        assert task_ws.read_text("outputs/result.txt") == "结果保存在 PyVDisk VFS"
        assert [item["path"] for item in event_ws.list_files()] == ["notes/brief.json"]
        assert [item["path"] for item in task_ws.list_files()] == ["outputs/result.txt"]
        assert not (Path(directory) / "workspaces").exists()

        for invalid in ("../escape", "/escape", "C:/escape", "nested/../../escape", r"nested\..\escape", "nested//file"):
            with pytest.raises(ValueError):
                task_ws.write_text(invalid, "must not escape")
        with pytest.raises(ValueError):
            event_ws.delete("")
        with pytest.raises(ValueError):
            store.task_workspace("../outside")

        store.close()
        reopened = DiskStore.open(str(image))
        assert reopened.event_workspace("event-work").read_json("notes/brief.json") == {"title": "活动准备"}
        assert reopened.task_workspace("task-work").read_text("outputs/result.txt") == "结果保存在 PyVDisk VFS"
        reopened.close()


def test_pyvdisk_capabilities_are_adapted_to_langchain():
    with tempfile.TemporaryDirectory() as directory:
        store = DiskStore.open(str(Path(directory) / "agent.vdisk"))
        tools = make_langchain_tools(store.sandbox)
        assert {tool.name for tool in tools} >= {"read_file", "write_file", "list_files"}
        store.close()


def test_tui_navigation_and_refresh():
    import asyncio
    from textual.widgets import Static
    from neo_agent.ui.tui import NeoConsole

    async def scenario():
        with tempfile.TemporaryDirectory() as directory:
            store = DiskStore.open(str(Path(directory) / "agent.vdisk"))
            app = NeoConsole(store)
            async with app.run_test(size=(120, 40)) as pilot:
                await pilot.press("9")
                await pilot.pause()
                assert app.active_view == "能力与 NPS"
                assert "core.pyvdisk-capabilities" in str(app.query_one("#plugin-list", Static).render())
                await pilot.press("r")
                await pilot.pause()
            store.close()

    asyncio.run(scenario())


def test_langchain_runtime_persists_conversation():
    from langchain_core.messages import AIMessage
    from neo_agent.runtime import AgentRuntime

    class ScriptedModel:
        def bind_tools(self, _tools):
            return self

        def invoke(self, _messages):
            return AIMessage(content="你好，我已经记住这次对话。")

    with tempfile.TemporaryDirectory() as directory:
        store = DiskStore.open(str(Path(directory) / "agent.vdisk"))
        agent = AgentRuntime(store, model=ScriptedModel())
        assert agent.chat("你好", conversation_id="group_01") == "你好，我已经记住这次对话。"
        history = store.read_json("/runtime/conversations/group_01.json")
        assert history == [{"user": "你好", "assistant": "你好，我已经记住这次对话。"}]
        assert [row["role"] for row in store.short_term_messages("group_01")] == ["user", "assistant"]
        assert store.search_memories("你好", character_id="group_01")
        assert store.events()[-1]["message"] == "conversation.turn.completed"
        store.close()


def test_runtime_executes_only_sandbox_tools_then_returns_answer():
    from langchain_core.messages import AIMessage
    from neo_agent.runtime import AgentRuntime

    class ToolThenAnswer:
        def __init__(self):
            self.calls = 0

        def bind_tools(self, _tools):
            return self

        def invoke(self, _messages):
            self.calls += 1
            if self.calls == 1:
                return AIMessage(content="", tool_calls=[{
                    "name": "write_file", "args": {"path": "/runtime/tool.txt", "content": "persisted"},
                    "id": "call-1", "type": "tool_call",
                }])
            return AIMessage(content="Done.")

    with tempfile.TemporaryDirectory() as directory:
        store = DiskStore.open(str(Path(directory) / "agent.vdisk"))
        agent = AgentRuntime(store, model=ToolThenAnswer())
        assert agent.chat("Save a small note.") == "Done."
        assert store.sandbox.read_text("/runtime/tool.txt") == "persisted"
        assert store.runtime_overview()["audit"]["length"] >= 1
        store.close()


def test_tui_can_create_and_archive_character():
    import asyncio
    from textual.widgets import Button, Input, TextArea
    from neo_agent.ui.tui import NeoConsole

    async def scenario():
        with tempfile.TemporaryDirectory() as directory:
            store = DiskStore.open(str(Path(directory) / "agent.vdisk"))
            app = NeoConsole(store)
            async with app.run_test(size=(120, 40)) as pilot:
                await pilot.press("2")
                await pilot.pause()
                app.query_one("#character-id", Input).value = "mika"
                app.query_one("#character-name", Input).value = "米卡"
                app.query_one("#character-personality", TextArea).text = "活泼、友善"
                await pilot.click("#save-character")
                await pilot.pause()
                assert store.character("mika")["name"] == "米卡"
                await pilot.click("#archive-character")
                await pilot.pause()
                assert store.character("mika")["status"] == "archived"
                assert store.characters() == []
            store.close()

    asyncio.run(scenario())


def test_plugin_enable_state_persists_and_controls_tools():
    from neo_agent.plugins import PluginRegistry

    with tempfile.TemporaryDirectory() as directory:
        image = str(Path(directory) / "agent.vdisk")
        store = DiskStore.open(image)
        registry = PluginRegistry(store)
        assert registry.tools()
        registry.set_enabled("core.pyvdisk-capabilities", False)
        assert "write_file" not in {tool.name for tool in registry.tools()}
        assert "create_schedule" in {tool.name for tool in registry.tools()}
        registry.set_enabled("core.events-schedules", False)
        assert registry.tools() == []
        store.close()

        reopened = DiskStore.open(image)
        assert PluginRegistry(reopened).tools() == []
        reopened.close()


def test_tui_chat_uses_selected_character_and_persisted_runtime(monkeypatch):
    import asyncio
    from textual.widgets import Select, TextArea
    import neo_agent.ui.tui as tui

    class FakeRuntime:
        def __init__(self, store, **_kwargs):
            self.store = store

        def chat(self, prompt, *, conversation_id, system_prompt):
            self.store.write_json(f"/runtime/conversations/{conversation_id}.json", [
                {"user": prompt, "assistant": f"{system_prompt}: {prompt}"}
            ])
            return f"{system_prompt}: {prompt}"

    monkeypatch.setattr(tui, "AgentRuntime", FakeRuntime)

    async def scenario():
        with tempfile.TemporaryDirectory() as directory:
            store = DiskStore.open(str(Path(directory) / "agent.vdisk"))
            store.save_character("mika", {"name": "米卡", "personality": "活泼"})
            store.save_character("luna", {"name": "露娜", "personality": "冷静"})
            app = tui.NeoConsole(store)
            async with app.run_test(size=(120, 40)) as pilot:
                await pilot.press("3")
                await pilot.pause()
                selector = app.query_one("#chat-character", Select)
                selector.value = "luna"
                app.query_one("#chat-input", TextArea).text = "早上好"
                await pilot.click("#send-chat")
                await pilot.pause(0.2)
                transcript = store.read_json("/runtime/conversations/luna.json")
                assert transcript[0]["assistant"] == "冷静: 早上好"
            store.close()

    asyncio.run(scenario())


def test_domain_events_and_schedule_queue_are_durable_across_reopen():
    with tempfile.TemporaryDirectory() as directory:
        image = str(Path(directory) / "agent.vdisk")
        store = DiskStore.open(image)
        event_id = store.append_event("message.received", {"group": "friends", "text": "hi"}, event_id="evt-1")
        duplicate = store.append_event("message.received", {"ignored": True}, event_id="evt-1")
        assert event_id == duplicate
        created = store.create_schedule("coffee", {
            "title": "咖啡聊天", "due_at": "2026-10-03T18:00:00+08:00", "description": "周末见面"
        })
        assert created["queue_revision"] == 1
        assert store.runtime_overview()["events"] == 2  # duplicate event is idempotent; schedule.created is separate
        store.close()

        reopened = DiskStore.open(image)
        assert reopened.schedules()[0]["title"] == "咖啡聊天"
        assert len(reopened.schedule_tasks()) == 0  # future work is materialized only when due
        assert [row["message"] for row in reopened.events()] == ["message.received", "schedule.created"]
        reopened.close()


def test_schedule_requires_timezone_and_unique_id():
    with tempfile.TemporaryDirectory() as directory:
        store = DiskStore.open(str(Path(directory) / "agent.vdisk"))
        with pytest.raises(ValueError, match="timezone"):
            store.create_schedule("bad", {"title": "No zone", "due_at": "2026-10-03T18:00:00"})
        store.create_schedule("good", {"title": "With zone", "due_at": "2026-10-03T18:00:00Z"})
        with pytest.raises(ValueError, match="already exists"):
            store.create_schedule("good", {"title": "Overwrite", "due_at": "2026-10-04T18:00:00Z"})
        store.close()


def test_schedule_event_plugin_provides_langchain_tools():
    from neo_agent.plugins import PluginRegistry
    with tempfile.TemporaryDirectory() as directory:
        store = DiskStore.open(str(Path(directory) / "agent.vdisk"))
        registry = PluginRegistry(store)
        assert {tool.name for tool in registry.tools()} >= {
            "create_schedule", "record_domain_event", "write_file"
        }
        store.close()


def test_relationship_console_shows_dimension_radar_and_topic_timeline():
    import asyncio
    from textual.widgets import Input, Static
    from neo_agent.ui.tui import NeoConsole

    with tempfile.TemporaryDirectory() as directory:
        store = DiskStore.open(str(Path(directory) / "agent.vdisk"))
        store.save_document("emotions", "mood-one", {
            "relationship_id": "rel_mika", "overall_score": 67, "score_change": 2,
            "relationship_type": "熟悉中", "sentiment": "positive", "emotional_tone": "温暖",
            "impression": "互动自然", "analysis": "主动分享共同兴趣",
            "key_topics": ["旅行"], "dimensions": {"warmth": 80, "trust": 65, "familiarity": 55, "tension": 10},
            "evidence": "一起讨论旅行计划",
        })
        store.save_long_term_summary("sum-one", "开始讨论旅行偏好", conversation_id="mika", rounds=4, message_count=8)
        store.save_long_term_summary("sum-two", "确定周末的旅行路线", conversation_id="mika", rounds=3, message_count=6)
        app = NeoConsole(store)

        async def scenario():
            async with app.run_test(size=(120, 48)) as pilot:
                app.action_navigate("关系")
                app.query_one("#relationship-id", Input).value = "rel_mika"
                app.query_one("#emotion-conversation-id", Input).value = "mika"
                app.refresh_relationship_view()
                radar = str(app.query_one("#emotion-radar", Static).render())
                timeline = str(app.query_one("#topic-timeline", Static).render())
                assert "温暖" in radar and "80.0/100" in radar
                assert "互动自然" in radar
                assert "开始讨论旅行偏好" in timeline
                assert "确定周末的旅行路线" in timeline
                assert "4 轮 / 8 条" in timeline

        asyncio.run(scenario())
        store.close()


def test_tui_event_and_schedule_views_are_operational():
    import asyncio
    from textual.widgets import Button, Input, Static
    from neo_agent.ui.tui import NeoConsole

    async def scenario():
        with tempfile.TemporaryDirectory() as directory:
            store = DiskStore.open(str(Path(directory) / "agent.vdisk"))
            app = NeoConsole(store)
            async with app.run_test(size=(120, 40)) as pilot:
                await pilot.press("5")
                await pilot.pause()
                assert app.active_view == "日程"
                app.query_one("#schedule-id", Input).value = "standup"
                app.query_one("#schedule-title", Input).value = "每日站会"
                app.query_one("#schedule-due", Input).value = "2026-10-03T09:30:00+08:00"
                await pilot.click("#create-schedule")
                await pilot.pause()
                assert len(store.schedules()) == 1
                assert "每日站会" in str(app.query_one("#schedule-list", Static).render())
                await pilot.press("4")
                await pilot.pause()
                assert app.active_view == "事件流"
                assert "schedule.created" in str(app.query_one("#events-list", Static).render())
            store.close()

    asyncio.run(scenario())


def test_vector_memory_domain_records_and_short_term_reopen():
    with tempfile.TemporaryDirectory() as directory:
        image = str(Path(directory) / "agent.vdisk")
        store = DiskStore.open(image)
        store.save_memory("m-1", "周六一起去咖啡馆", character_id="luna")
        store.add_short_term_message("user", "下周见", conversation_id="luna")
        store.add_long_term_summary("用户喜欢咖啡", conversation_id="luna", rounds=3, message_count=6)
        store.add_emotion("luna-alex", "开心", 0.8, evidence="一起约咖啡")
        store.save_document("entities", "alex", {"name": "Alex", "entity_type": "user", "definition": "朋友"})
        store.close()

        reopened = DiskStore.open(image)
        assert reopened.search_memories("咖啡", character_id="luna")[0]["id"] == "m-1"
        assert reopened.short_term_messages("luna")[0]["content"] == "下周见"
        assert reopened.long_term_summaries("luna")[0]["summary"] == "用户喜欢咖啡"
        assert reopened.emotion_history("luna-alex")[0]["tone"] == "开心"
        assert reopened.get_document("entities", "alex")["name"] == "Alex"
        reopened.close()


def test_schedule_worker_delivers_due_and_records_status():
    from datetime import datetime, timezone
    from neo_agent.runtime import ScheduleWorker

    with tempfile.TemporaryDirectory() as directory:
        store = DiskStore.open(str(Path(directory) / "agent.vdisk"))
        store.create_schedule("due-now", {"title": "提醒", "due_at": "2026-10-02T08:00:00+00:00"})
        delivered = []
        worker = ScheduleWorker(store, notifier=delivered.append)
        completed = worker.run_once(now=datetime(2026, 10, 2, 9, tzinfo=timezone.utc))
        assert completed == ["due-now"]
        assert delivered[0]["title"] == "提醒"
        assert store.get_schedule("due-now")["status"] == "notified"
        assert store.events()[-1]["message"] == "schedule.reminder.delivered"
        store.close()


def test_nps_vscript_import_execution_audit_and_capability_denial():
    from neo_agent.nps import NPSManager, NPSRuntimeError

    with tempfile.TemporaryDirectory() as directory:
        store = DiskStore.open(str(Path(directory) / "agent.vdisk"))
        manager = NPSManager(store)
        bundle = {
            "format": "neo.nps/v1",
            "manifest": {
                "id": "demo.echo", "name": "Echo", "version": "1.0.0",
                "description": "Echo JSON arguments", "entrypoint": "main",
                "parameters": {"type": "object", "properties": {"message": {"type": "string"}}, "required": ["message"]},
            },
            "vscript": 'language "1.0"; fn main(args) { return args; }',
        }
        manager.import_json(__import__("json").dumps(bundle), enabled=True)
        assert manager.invoke("demo.echo", {"message": "hello"}) == {"message": "hello"}
        tool = manager.langchain_tools()[0]
        assert tool.invoke({"message": "ok"}) == '{"message": "ok"}'
        assert any(event["message"] == "nps.execution.completed" for event in store.events())
        with pytest.raises(ValueError, match="explicit python.call"):
            manager.validate_bundle({**bundle, "python": "def main(args): return args"})
        with pytest.raises(ValueError, match="explicit python.call"):
            manager.validate_bundle({**bundle, "python": "def main(args): return args"})
        store.close()


def test_nps_test_bundle_is_ephemeral_and_validates_manifest_arguments():
    from neo_agent.nps import NPSManager

    with tempfile.TemporaryDirectory() as directory:
        store = DiskStore.open(str(Path(directory) / "agent.vdisk"))
        manager = NPSManager(store)
        bundle = {
            "format": "neo.nps/v1",
            "manifest": {
                "id": "demo.ephemeral", "name": "Echo", "version": "1.0.0",
                "description": "one-shot test", "entrypoint": "main",
                "parameters": {
                    "type": "object", "properties": {"message": {"type": "string", "minLength": 1}},
                    "required": ["message"],
                },
            },
            "vscript": 'language "1.0"; fn main(args) { return args; }',
        }
        assert manager.test_bundle(bundle, {"message": "hello"}) == {"message": "hello"}
        assert manager.get("demo.ephemeral") is None
        assert any(event["message"] == "nps.test.completed" for event in store.events())
        with pytest.raises(ValueError, match="missing NPS arguments"):
            manager.test_bundle(bundle, {})
        with pytest.raises(ValueError, match="unexpected NPS arguments"):
            manager.test_bundle(bundle, {"message": "hello", "extra": True})

        manager.save(bundle, enabled=True)
        changed = {**bundle, "vscript": 'language "1.0"; fn main(args) { return "test"; }'}
        assert manager.test_bundle(changed, {"message": "hello"}) == "test"
        persisted = manager.get("demo.ephemeral")
        assert persisted["enabled"] is True
        assert persisted["vscript"] == bundle["vscript"]
        assert manager.invoke("demo.ephemeral", {"message": "still enabled"}) == {"message": "still enabled"}
        store.close()


def test_nps_tui_test_action_does_not_install_or_disable_bundle():
    import asyncio
    from textual.widgets import Input, TextArea
    from neo_agent.ui.tui import NeoConsole

    with tempfile.TemporaryDirectory() as directory:
        store = DiskStore.open(str(Path(directory) / "agent.vdisk"))
        app = NeoConsole(store)

        async def scenario():
            async with app.run_test(size=(120, 48)):
                app.query_one("#nps-id", Input).value = "demo.ui_test"
                app.query_one("#nps-name", Input).value = "UI test"
                app.query_one("#nps-description", Input).value = "Transient editor test"
                app.query_one("#nps-parameters", TextArea).text = '{"type":"object","properties":{"message":{"type":"string"}},"required":["message"]}'
                app.query_one("#nps-args", Input).value = '{"message":"hello"}'
                app.query_one("#nps-vscript", TextArea).text = 'language "1.0"; fn main(args) { return args; }'
                app.test_nps()
                assert app.nps.get("demo.ui_test") is None

                persisted = {
                    "format": "neo.nps/v1",
                    "manifest": {
                        "id": "demo.ui_test", "name": "Persisted", "version": "1.0.0",
                        "description": "must stay enabled", "entrypoint": "main",
                        "parameters": {"type": "object", "properties": {}},
                    },
                    "vscript": 'language "1.0"; fn main(args) { return "persisted"; }',
                }
                app.nps.save(persisted, enabled=True)
                app.query_one("#nps-vscript", TextArea).text = 'language "1.0"; fn main(args) { return "test-only"; }'
                app.test_nps()
                current = app.nps.get("demo.ui_test")
                assert current["enabled"] is True
                assert current["vscript"] == persisted["vscript"]
                assert app.nps.invoke("demo.ui_test", {}) == "persisted"

        asyncio.run(scenario())
        store.close()


def test_nps_optional_python_bridge_runs_in_bubblewrap():
    from neo_agent.nps import NPSManager

    with tempfile.TemporaryDirectory() as directory:
        store = DiskStore.open(str(Path(directory) / "agent.vdisk"))
        manager = NPSManager(store)
        bundle = {
            "format": "neo.nps/v1",
            "manifest": {
                "id": "demo.bridge", "name": "Bridge", "version": "1.0.0",
                "description": "Call isolated Python", "entrypoint": "main",
                "python_entrypoint": "main", "capabilities": ["python.call"],
                "parameters": {"type": "object", "properties": {"value": {"type": "integer"}}, "required": ["value"]},
            },
            "vscript": 'language "1.0"; fn main(args) { return python_call(args); }',
            "python": "def main(args): return {'value': args['value'] + 1}",
        }
        manager.save(bundle, enabled=True)
        assert manager.invoke("demo.bridge", {"value": 4}) == {"value": 5}
        store.close()


def test_schedule_edit_supersedes_old_queue_revision_and_worker_uses_new_time():
    from datetime import datetime, timezone
    from neo_agent.runtime import ScheduleWorker

    with tempfile.TemporaryDirectory() as directory:
        store = DiskStore.open(str(Path(directory) / "agent.vdisk"))
        store.create_schedule("revised", {"title": "Before", "due_at": "2026-10-02T10:00:00+00:00"})
        updated = store.update_schedule("revised", {
            "title": "After", "due_at": "2026-10-03T10:00:00+00:00",
        })
        assert updated["queue_revision"] == 2
        assert store.schedule_tasks() == []
        sent = []
        worker = ScheduleWorker(store, notifier=sent.append)
        assert worker.run_once(now=datetime(2026, 10, 2, 12, tzinfo=timezone.utc)) == []
        assert sent == []
        assert store.schedule_tasks() == []
        assert worker.run_once(now=datetime(2026, 10, 3, 12, tzinfo=timezone.utc)) == ["revised"]
        assert sent[0]["title"] == "After"
        store.close()


def test_config_export_strips_secrets_and_import_rejects_secret_fields():
    import json
    from textual.widgets import TextArea
    from neo_agent.ui.tui import NeoConsole

    with tempfile.TemporaryDirectory() as directory:
        store = DiskStore.open(str(Path(directory) / "agent.vdisk"))
        store.save_document("channels", "chat", {
            "name": "test", "config": {"room": "public", "access_token": "do-not-export", "nested": {"clientSecret": "also-secret"}},
        })
        app = NeoConsole(store)

        async def scenario():
            async with app.run_test(size=(120, 40)):
                app.export_config()
                exported = json.loads(app.query_one("#config-json", TextArea).text)
                assert exported["channels"][0]["config"] == {"room": "public", "nested": {}}
                app.query_one("#config-json", TextArea).text = json.dumps({
                    "format": "neo-agent/config/v1", "channels": [{"id": "leak", "config": {"api_key": "x"}}],
                })
                with pytest.raises(ValueError, match="不得包含密钥"):
                    app.import_config()
                assert store.get_document("channels", "leak") is None

        import asyncio
        asyncio.run(scenario())
        store.close()


def test_channel_secret_rejected_and_python_capability_must_be_explicit():
    import asyncio
    import json
    from textual.widgets import Input
    from neo_agent.nps import NPSManager
    from neo_agent.ui.tui import NeoConsole

    with tempfile.TemporaryDirectory() as directory:
        store = DiskStore.open(str(Path(directory) / "agent.vdisk"))
        app = NeoConsole(store)

        async def scenario():
            async with app.run_test(size=(120, 40)):
                app.query_one("#channel-id", Input).value = "chan"
                app.query_one("#channel-name", Input).value = "Test"
                app.query_one("#channel-platform", Input).value = "demo"
                app.query_one("#channel-config", Input).value = json.dumps({"bot_token": "secret"})
                with pytest.raises(ValueError, match="禁止保存密钥"):
                    app.save_channel()
                assert store.get_document("channels", "chan") is None

        asyncio.run(scenario())
        manager = NPSManager(store)
        bundle = {
            "format": "neo.nps/v1",
            "manifest": {"id": "demo.python", "name": "Python", "version": "1.0.0", "description": "test", "entrypoint": "main"},
            "vscript": 'language "1.0"; fn main(args) { return python_call(args); }',
            "python": "def main(args): return args",
        }
        with pytest.raises(ValueError, match="explicit python.call"):
            manager.validate_bundle(bundle)
        bundle["manifest"]["capabilities"] = ["python.call"]
        bundle["manifest"]["python_entrypoint"] = "_hidden"
        with pytest.raises(ValueError, match="public Python identifier"):
            manager.validate_bundle(bundle)
        store.close()


def test_due_worker_does_not_let_future_reminder_block_due_work():
    from datetime import datetime, timezone
    from neo_agent.runtime import ScheduleWorker

    with tempfile.TemporaryDirectory() as directory:
        store = DiskStore.open(str(Path(directory) / "agent.vdisk"))
        store.create_schedule("later", {"title": "Later", "due_at": "2026-10-04T09:00:00+00:00"})
        store.create_schedule("now", {"title": "Now", "due_at": "2026-10-02T08:00:00+00:00"})
        sent = []
        completed = ScheduleWorker(store, notifier=sent.append).run_once(
            now=datetime(2026, 10, 2, 9, tzinfo=timezone.utc),
        )
        assert completed == ["now"]
        assert [item["title"] for item in sent] == ["Now"]
        assert store.get_schedule("later")["status"] == "pending"
        store.close()


def test_tui_event_record_crud_trigger_and_type_filter():
    import asyncio
    from textual.widgets import Button, Input, Static
    from neo_agent.ui.tui import NeoConsole

    async def scenario():
        with tempfile.TemporaryDirectory() as directory:
            store = DiskStore.open(str(Path(directory) / "agent.vdisk"))
            app = NeoConsole(store)
            async with app.run_test(size=(140, 50)) as pilot:
                await pilot.press("4")
                await pilot.pause()
                app.query_one("#event-record-id", Input).value = "evtlaunch"
                app.query_one("#event-record-title", Input).value = "测试发布"
                app.query_one("#event-record-type", Input).value = "release.ready"
                app.query_one("#event-record-details", Input).value = "开始灰度"
                await pilot.click("#create-event-record")
                await pilot.pause()
                assert store.get_document("event_records", "evtlaunch")["status"] == "pending"
                assert store.get_document("event_records", "evtlaunch")["workspace"] == "/workspaces/events/evtlaunch"
                assert "/workspaces/events/evtlaunch" in str(app.query_one("#event-record-list", Static).render())
                await pilot.click("#trigger-event-record")
                await pilot.pause()
                assert store.get_document("event_records", "evtlaunch")["status"] == "triggered"
                assert store.events()[-1]["message"] == "release.ready"
                app.query_one("#event-filter", Input).value = "release.ready"
                app.refresh_events()
                assert "release.ready" in str(app.query_one("#events-list", Static).render())
                app.query_one("#event-record-status", Input).value = "completed"
                await pilot.click("#update-event-record")
                await pilot.pause()
                assert store.get_document("event_records", "evtlaunch")["status"] == "completed"
                app.delete_event_record()
                assert store.get_document("event_records", "evtlaunch") is None
            store.close()

    asyncio.run(scenario())


def test_default_schedule_worker_stages_auditable_outbox_without_claiming_delivery():
    from datetime import datetime, timezone
    from neo_agent.runtime import ScheduleWorker

    with tempfile.TemporaryDirectory() as directory:
        store = DiskStore.open(str(Path(directory) / "agent.vdisk"))
        store.create_schedule("stage", {"title": "提醒内容", "due_at": "2026-10-02T08:00:00+00:00"})
        worker = ScheduleWorker(store)
        assert worker.run_once(now=datetime(2026, 10, 2, 9, tzinfo=timezone.utc)) == ["stage"]
        assert store.get_schedule("stage")["status"] == "awaiting_delivery"
        workflow = store.list_documents("workflows")[0]
        assert workflow["schedule_id"] == "stage"
        assert workflow["delivery_adapter"] is None
        assert store.events()[-1]["message"] == "schedule.reminder.staged"
        assert store.schedule_tasks()[0]["result"]["staged"] is True
        store.close()


def test_tui_can_load_and_edit_existing_character():
    import asyncio
    from textual.widgets import Input, TextArea
    from neo_agent.ui.tui import NeoConsole

    async def scenario():
        with tempfile.TemporaryDirectory() as directory:
            store = DiskStore.open(str(Path(directory) / "agent.vdisk"))
            store.save_character("mika", {
                "name": "米卡", "gender": "女", "role": "旅行者", "age": "20",
                "height": "165cm", "weight": "50kg", "hobby": "摄影",
                "personality": "活泼", "background": "来自北方",
            })
            app = NeoConsole(store)
            async with app.run_test(size=(120, 40)) as pilot:
                await pilot.press("2")
                await pilot.pause()
                app.query_one("#character-id", Input).value = "mika"
                await pilot.click("#load-character")
                await pilot.pause()
                assert app.query_one("#character-name", Input).value == "米卡"
                assert app.query_one("#character-background", TextArea).text == "来自北方"
                app.query_one("#character-hobby", Input).value = "绘画"
                await pilot.click("#save-character")
                assert store.character("mika")["hobby"] == "绘画"
            store.close()

    asyncio.run(scenario())


def test_conversation_history_and_delete_remove_transcript_and_short_term_only():
    with tempfile.TemporaryDirectory() as directory:
        store = DiskStore.open(str(Path(directory) / "agent.vdisk"))
        store.write_json("/runtime/conversations/group01.json", [{"user": "hi", "assistant": "hello"}])
        store.add_short_term_message("user", "hi", conversation_id="group01")
        summary = store.add_long_term_summary("keep this", conversation_id="group01")
        assert store.conversation_transcripts() == [{"id": "group01", "turns": [{"user": "hi", "assistant": "hello"}]}]
        assert store.delete_conversation("group01") is True
        assert store.conversation_transcripts() == []
        assert store.short_term_messages("group01") == []
        assert store.long_term_summaries("group01")[0]["id"] == summary["id"]
        store.close()


def test_schedule_collaboration_decisions_are_audited_and_reject_cancels():
    from datetime import datetime, timedelta, timezone

    with tempfile.TemporaryDirectory() as directory:
        store = DiskStore.open(str(Path(directory) / "agent.vdisk"))
        due = (datetime.now(timezone.utc) + timedelta(days=2)).isoformat()
        store.create_schedule("collab01", {
            "title": "一起看展", "due_at": due, "type": "collaboration",
            "priority": "high", "collaboration_status": "pending_confirmation",
        })
        accepted = store.confirm_schedule("collab01", True)
        assert accepted["collaboration_status"] == "confirmed"
        assert accepted["status"] == "pending"
        rejected = store.confirm_schedule("collab01", False)
        assert rejected["collaboration_status"] == "rejected"
        assert rejected["status"] == "cancelled"
        assert [event["message"] for event in store.query_events(limit=10)].count("schedule.collaboration.decided") == 2
        store.close()


def test_long_term_summaries_support_edit_and_delete():
    with tempfile.TemporaryDirectory() as directory:
        store = DiskStore.open(str(Path(directory) / "agent.vdisk"))
        saved = store.save_long_term_summary("summary01", "初稿", conversation_id="group01")
        edited = store.save_long_term_summary("summary01", "修订版", conversation_id="group01")
        assert edited["id"] == saved["id"]
        assert store.long_term_summaries("group01")[0]["summary"] == "修订版"
        assert store.delete_long_term_summary("summary01") is True
        assert store.long_term_summaries("group01") == []
        store.close()


def test_short_term_memory_handles_max_length_conversation_ids():
    with tempfile.TemporaryDirectory() as directory:
        store = DiskStore.open(str(Path(directory) / "agent.vdisk"))
        conversation_id = "a" * 22
        store.add_short_term_message("user", "persist", conversation_id=conversation_id)
        assert store.short_term_messages(conversation_id) == [{"role": "user", "content": "persist"}]
        assert store.clear_short_term(conversation_id) is True
        store.close()


def test_schedule_conflicts_obey_priority_and_update_validation():
    from datetime import datetime, timedelta, timezone

    with tempfile.TemporaryDirectory() as directory:
        store = DiskStore.open(str(Path(directory) / "agent.vdisk"))
        start = datetime.now(timezone.utc) + timedelta(days=3)
        end = start + timedelta(hours=1)
        low_start, low_end = start.isoformat(), end.isoformat()
        store.create_schedule("lowprio", {
            "title": "普通事项", "due_at": low_start, "end_at": low_end, "priority": "medium",
        })
        with pytest.raises(ValueError, match="conflicts"):
            store.create_schedule("equalprio", {
                "title": "同级冲突", "due_at": low_start, "end_at": low_end, "priority": "low",
            })
        # A higher-priority item may overlap a lower-priority one.
        store.create_schedule("highprio", {
            "title": "关键事项", "due_at": low_start, "end_at": low_end, "priority": "critical",
        })
        with pytest.raises(ValueError, match="conflicts"):
            store.update_schedule("highprio", {"priority": "low"})
        with pytest.raises(ValueError, match="after its start"):
            store.create_schedule("badinterval", {
                "title": "逆序时间", "due_at": low_start, "end_at": start.isoformat(),
            })
        store.close()


def test_recurring_schedule_stages_occurrence_and_advances_weekly():
    from datetime import datetime, timedelta, timezone
    from neo_agent.runtime import ScheduleWorker

    with tempfile.TemporaryDirectory() as directory:
        store = DiskStore.open(str(Path(directory) / "agent.vdisk"))
        due = datetime.now(timezone.utc) + timedelta(days=14)
        due = (due + timedelta(days=(0 - due.weekday()) % 7)).replace(minute=0, second=0, microsecond=0)
        end = due + timedelta(hours=1)
        store.create_schedule("weekly01", {
            "title": "周会", "due_at": due.isoformat(), "end_at": end.isoformat(),
            "type": "recurring", "weekday": due.weekday(), "recurrence_pattern": "weekly",
        })
        ScheduleWorker(store).run_once(now=due + timedelta(minutes=1))
        updated = store.get_schedule("weekly01")
        assert updated["status"] == "pending"
        assert datetime.fromisoformat(updated["due_at"]) == due + timedelta(days=7)
        assert updated["queue_revision"] == 2
        assert store.list_documents("workflows")[0]["due_at"] == due.isoformat()
        assert any(event["message"] == "schedule.recurrence.advanced" for event in store.events())
        store.close()


def test_schedule_range_free_time_and_statistics_api():
    from datetime import datetime, timedelta, timezone

    with tempfile.TemporaryDirectory() as directory:
        store = DiskStore.open(str(Path(directory) / "agent.vdisk"))
        start = datetime(2026, 10, 5, 9, tzinfo=timezone.utc)
        end = start + timedelta(hours=6)
        busy_start = start + timedelta(hours=2)
        busy_end = busy_start + timedelta(hours=1)
        store.create_schedule("range01", {
            "title": "评审", "due_at": busy_start.isoformat(), "end_at": busy_end.isoformat(),
            "type": "appointment", "priority": "high", "collaboration_status": "pending",
        })
        assert [item["id"] for item in store.schedules_in_range(start.isoformat(), end.isoformat())] == ["range01"]
        slots = store.free_time_slots(start.isoformat(), end.isoformat(), duration_minutes=60)
        assert len(slots) == 2
        assert slots[0]["start_at"] == start.isoformat()
        assert slots[0]["end_at"] == busy_start.isoformat()
        stats = store.schedule_statistics()
        assert stats["total"] == 1
        assert stats["by_type"] == {"appointment": 1}
        assert stats["pending_collaboration"] == 1
        store.close()


def test_schedule_analysis_actions_are_available_in_tui():
    import asyncio
    from textual.widgets import Button, Input, Static
    from neo_agent.ui.tui import NeoConsole

    async def scenario():
        with tempfile.TemporaryDirectory() as directory:
            store = DiskStore.open(str(Path(directory) / "agent.vdisk"))
            start = "2026-10-05T09:00:00+00:00"
            store.create_schedule("tui_range", {
                "title": "演示预约", "due_at": "2026-10-05T11:00:00+00:00",
                "end_at": "2026-10-05T12:00:00+00:00",
            })
            app = NeoConsole(store)
            async with app.run_test(size=(140, 50)) as pilot:
                await pilot.press("5")
                app.query_one("#schedule-range-start", Input).value = start
                app.query_one("#schedule-range-end", Input).value = "2026-10-05T15:00:00+00:00"
                app.query_one("#schedules").scroll_end(animate=False)
                await pilot.pause()
                await pilot.click("#query-schedule-range")
                assert "演示预约" in str(app.query_one("#schedule-analysis", Static).render())
                app.query_one("#schedules").scroll_end(animate=False)
                await pilot.pause()
                await pilot.click("#schedule-statistics")
                assert "日程总数：1" in str(app.query_one("#schedule-analysis", Static).render())
            store.close()

    asyncio.run(scenario())


def test_schedule_editor_updates_type_priority_and_recurrence_metadata():
    from datetime import datetime, timedelta, timezone

    with tempfile.TemporaryDirectory() as directory:
        store = DiskStore.open(str(Path(directory) / "agent.vdisk"))
        due = datetime.now(timezone.utc) + timedelta(days=8)
        due = (due + timedelta(days=(0 - due.weekday()) % 7)).replace(minute=0, second=0, microsecond=0)
        end = due + timedelta(minutes=45)
        store.create_schedule("editrec01", {
            "title": "例会", "due_at": due.isoformat(), "end_at": end.isoformat(),
            "type": "appointment", "priority": "medium",
        })
        changed = store.update_schedule("editrec01", {
            "type": "recurring", "priority": "high", "weekday": due.weekday(),
            "recurrence_pattern": "weekly",
        })
        assert changed["type"] == "recurring"
        assert changed["priority"] == "high"
        assert changed["queue_revision"] == 2
        with pytest.raises(ValueError, match="weekday"):
            store.update_schedule("editrec01", {"weekday": (due.weekday() + 1) % 7})
        store.close()


def test_bulk_memory_clear_is_audited_and_preserves_semantic_memories():
    with tempfile.TemporaryDirectory() as directory:
        store = DiskStore.open(str(Path(directory) / "agent.vdisk"))
        store.add_short_term_message("user", "temporary", conversation_id="group01")
        store.save_long_term_summary("summary01", "摘要", conversation_id="group01")
        store.save_memory("semantic01", "长期语义事实", character_id="mika")
        assert store.clear_all_short_term() == 1
        assert store.clear_all_long_term_summaries() == 1
        assert store.short_term_messages("group01") == []
        assert store.long_term_summaries() == []
        assert store.search_memories("长期语义事实", character_id="mika")
        event_names = [event["message"] for event in store.query_events(limit=20)]
        assert "memory.short_term.cleared" in event_names
        assert "memory.long_term.cleared" in event_names
        store.close()


def test_tui_requires_explicit_confirmation_for_bulk_memory_clear():
    import asyncio
    from textual.widgets import Input
    from neo_agent.ui.tui import NeoConsole

    async def scenario():
        with tempfile.TemporaryDirectory() as directory:
            store = DiskStore.open(str(Path(directory) / "agent.vdisk"))
            store.add_short_term_message("user", "keep until confirmation", conversation_id="group01")
            app = NeoConsole(store)
            async with app.run_test(size=(140, 50)):
                app.query_one("#memory-conversation-id", Input).value = "group01"
                with pytest.raises(ValueError, match="CLEAR SHORT TERM"):
                    app.clear_all_short_term()
                assert store.short_term_messages("group01")
                app.query_one("#clear-short-confirm", Input).value = "CLEAR SHORT TERM"
                app.clear_all_short_term()
                assert store.short_term_messages("group01") == []
            store.close()

    asyncio.run(scenario())


def test_environment_objects_connections_and_vision_audit_survive_reopen():
    with tempfile.TemporaryDirectory() as directory:
        image = str(Path(directory) / "agent.vdisk")
        store = DiskStore.open(image)
        store.save_document("environments", "studio", {"name": "工作室"})
        store.save_document("environments", "garden", {"name": "花园"})
        store.save_environment_object("desk", {
            "environment_id": "studio", "name": "书桌", "priority": 90,
            "position": "窗边", "properties": {"material": "wood"},
        })
        with pytest.raises(KeyError, match="unknown environment"):
            store.save_environment_object("orphan", {"environment_id": "missing", "name": "孤立物体"})
        connection = store.create_environment_connection(
            "studio", "garden", connection_type="door", direction="bidirectional", description="后门"
        )
        assert store.can_move_to_environment("garden", "studio")
        with pytest.raises(ValueError, match="self"):
            store.create_environment_connection("studio", "studio")
        with pytest.raises(ValueError, match="already exists"):
            store.create_environment_connection("studio", "garden")
        store.log_vision_usage(
            "窗边有什么？", environment_id="studio", objects_viewed=["desk"],
            context="书桌上有一本书", triggered_by="manual",
        )
        store.close()

        reopened = DiskStore.open(image)
        assert reopened.environment_objects("studio")[0]["name"] == "书桌"
        assert reopened.environment_connections("garden")[0]["id"] == connection["id"]
        assert reopened.can_move_to_environment("garden", "studio")
        assert reopened.vision_logs()[0]["objects_viewed"] == ["desk"]
        assert not reopened.can_move_to_environment("studio", "unknown")
        reopened.close()


def test_environment_tui_can_create_and_inspect_relations_and_vision_log():
    import asyncio
    from textual.widgets import Button, Input, TextArea
    from neo_agent.ui.tui import NeoConsole

    async def scenario():
        with tempfile.TemporaryDirectory() as directory:
            store = DiskStore.open(str(Path(directory) / "agent.vdisk"))
            store.save_document("environments", "studio", {"name": "工作室"})
            store.save_document("environments", "garden", {"name": "花园"})
            app = NeoConsole(store)
            async with app.run_test(size=(140, 60)) as pilot:
                await pilot.press("8")
                await pilot.pause()
                app.query_one("#environment-object-environment", Input).value = "studio"
                app.query_one("#environment-object-name", Input).value = "落地灯"
                app.query_one("#environment-object-description", TextArea).text = "暖色灯光"
                await app.on_button_pressed(Button.Pressed(app.query_one("#save-environment-object", Button)))
                app.query_one("#connection-from", Input).value = "studio"
                app.query_one("#connection-to", Input).value = "garden"
                await app.on_button_pressed(Button.Pressed(app.query_one("#create-environment-connection", Button)))
                app.query_one("#environment-id", Input).value = "studio"
                app.query_one("#vision-query", Input).value = "灯在哪里？"
                await app.on_button_pressed(Button.Pressed(app.query_one("#log-vision-usage", Button)))
                await pilot.pause()
                assert "落地灯" in str(app.query_one("#environment-graph").render())
                assert "工作室" in str(app.query_one("#environment-graph").render())
                assert store.vision_logs()[0]["query"] == "灯在哪里？"
            store.close()

    asyncio.run(scenario())


def test_environment_full_crud_domain_lifecycle_and_cascade_on_pydisk_reopen():
    with tempfile.TemporaryDirectory() as directory:
        image = str(Path(directory) / "agent.vdisk")
        store = DiskStore.open(image)
        store.save_document("environments", "loft", {"name": "阁楼"})
        store.save_document("environments", "yard", {"name": "院子"})
        obj = store.save_environment_object("lamp", {
            "environment_id": "loft", "name": "灯", "priority": 70, "properties": {"color": "amber"}
        })
        obj = store.save_environment_object("lamp", {**obj, "name": "落地灯", "priority": 80})
        assert obj["name"] == "落地灯"
        assert store.environment_objects("loft")[0]["id"] == "lamp"
        assert store.set_environment_object_visibility("lamp", False)["visible"] is False
        assert store.environment_objects("loft") == []
        assert store.environment_objects("loft", visible_only=False)[0]["name"] == "落地灯"
        edge = store.create_environment_connection("loft", "yard", direction="one_way")
        assert store.can_move_to_environment("loft", "yard")
        assert not store.can_move_to_environment("yard", "loft")
        assert store.delete_document("environment_connections", edge["id"])
        store.create_environment_connection("loft", "yard")

        store.save_domain("home", {"name": "家"})
        store.add_environment_to_domain("home", "loft")
        store.add_environment_to_domain("home", "yard")
        store.save_domain("home", {"name": "家", "default_environment_id": "yard"})
        with pytest.raises(KeyError, match="unknown environment"):
            store.save_domain("home", {"name": "家", "default_environment_id": "unknown"})
        with pytest.raises(KeyError, match="unknown environment"):
            store.add_environment_to_domain("home", "missing")
        switched = store.switch_domain("home")
        assert switched["environment"]["id"] == "yard"
        assert store.current_domain()["id"] == "home"
        store.log_vision_usage("描述场景", environment_id="loft", objects_viewed=["lamp"])
        store.close()

        reopened = DiskStore.open(image)
        assert reopened.current_domain()["id"] == "home"
        assert {row["id"] for row in reopened.domain_environments("home")} == {"loft", "yard"}
        assert len(reopened.vision_logs()) == 1
        assert reopened.delete_environment("loft")
        assert reopened.get_document("environment_objects", "lamp") is None
        assert reopened.environment_connections() == []
        domain = reopened.get_document("domains", "home")
        assert domain["environment_ids"] == ["yard"]
        assert domain["default_environment_id"] == "yard"
        assert reopened.vision_logs()[0]["environment_id"] == "loft"  # immutable audit history retained
        reopened.close()


def test_domain_tui_reports_invalid_member_and_supports_switch_flow():
    import asyncio
    from textual.widgets import Button, Input
    from neo_agent.ui.tui import NeoConsole

    async def scenario():
        with tempfile.TemporaryDirectory() as directory:
            store = DiskStore.open(str(Path(directory) / "agent.vdisk"))
            store.save_document("environments", "room", {"name": "客厅"})
            app = NeoConsole(store)
            async with app.run_test(size=(120, 40)) as pilot:
                await pilot.press("8")
                await pilot.pause()
                app.query_one("#domain-id", Input).value = "house"
                app.query_one("#domain-name", Input).value = "小家"
                await app.on_button_pressed(Button.Pressed(app.query_one("#save-domain", Button)))
                app.query_one("#domain-member-environment", Input).value = "missing"
                await app.on_button_pressed(Button.Pressed(app.query_one("#add-domain-environment", Button)))
                assert store.domain_environments("house") == []
                assert any(row["message"] == "tui.operation.failed" for row in store.events())
                app.query_one("#domain-member-environment", Input).value = "room"
                await app.on_button_pressed(Button.Pressed(app.query_one("#add-domain-environment", Button)))
                app.query_one("#domain-default-environment-id", Input).value = "room"
                await app.on_button_pressed(Button.Pressed(app.query_one("#save-domain", Button)))
                app.query_one("#switch-domain-id", Input).value = "house"
                await app.on_button_pressed(Button.Pressed(app.query_one("#switch-domain", Button)))
                assert store.current_domain()["id"] == "house"
            store.close()

    asyncio.run(scenario())


def test_vision_audit_rejects_unknown_or_cross_environment_object_references():
    with tempfile.TemporaryDirectory() as directory:
        store = DiskStore.open(str(Path(directory) / "agent.vdisk"))
        store.save_document("environments", "a", {"name": "A"})
        store.save_document("environments", "b", {"name": "B"})
        store.save_environment_object("thing", {"environment_id": "a", "name": "Thing"})
        with pytest.raises(ValueError, match="not part"):
            store.log_vision_usage("what?", environment_id="a", objects_viewed=["missing"])
        with pytest.raises(ValueError, match="not part"):
            store.log_vision_usage("what?", environment_id="b", objects_viewed=["thing"])
        assert store.vision_logs() == []
        store.close()


def test_expression_service_crud_learning_and_reopen():
    from neo_agent.runtime import ExpressionService

    with tempfile.TemporaryDirectory() as directory:
        image = str(Path(directory) / "agent.vdisk")
        store = DiskStore.open(image)
        service = ExpressionService(store, learner=lambda _text: '[{"expression_pattern":"hhh","meaning":"轻松笑声","confidence":0.8}]')
        service.save_expression("agent-laugh", expression="哈哈", meaning="开心时使用", category="语气词")
        assert "哈哈" in service.prompt()
        assert len(service.learn([
            {"role": "user", "content": "hhh 今天真开心"},
            {"role": "user", "content": "hhh"},
            {"role": "user", "content": "hhh 笑死"},
        ], current_round=3)) == 1
        assert service.habits()[0]["frequency"] == 1
        store.close()

        reopened = DiskStore.open(image)
        service = ExpressionService(reopened)
        assert service.expressions()[0]["meaning"] == "开心时使用"
        assert service.habits()[0]["expression_pattern"] == "hhh"
        assert service.clear_habits() == 1
        assert service.habits() == []
        reopened.close()


def test_expression_learning_validates_minimum_messages_and_model_output():
    from neo_agent.runtime import ExpressionService

    with tempfile.TemporaryDirectory() as directory:
        store = DiskStore.open(str(Path(directory) / "agent.vdisk"))
        service = ExpressionService(store, learner=lambda _text: "not-json")
        with pytest.raises(ValueError, match="至少需要"):
            service.learn([{"role": "user", "content": "hi"}])
        with pytest.raises(ValueError, match="JSON 数组"):
            service.learn([{"role": "user", "content": str(i)} for i in range(3)])
        store.close()


def test_expression_tui_exposes_agent_habits_and_clear_flow():
    import asyncio
    from textual.widgets import Button, Input, Static
    from neo_agent.ui.tui import NeoConsole
    from neo_agent.runtime import ExpressionService

    async def scenario():
        with tempfile.TemporaryDirectory() as directory:
            store = DiskStore.open(str(Path(directory) / "agent.vdisk"))
            ExpressionService(store).save_expression("vibe", expression="欸嘿", meaning="轻松语气")
            store.save_expression("habit", {"kind": "user_habit", "expression_pattern": "yyds", "meaning": "赞美", "confidence": .9})
            app = NeoConsole(store)
            async with app.run_test(size=(120, 40)) as pilot:
                await pilot.press("ctrl+5")
                await pilot.pause()
                assert "欸嘿" in str(app.query_one("#expression-list", Static).render())
                assert "yyds" in str(app.query_one("#user-expression-list", Static).render())
                app.query_one("#clear-user-expressions-confirm", Input).value = "CLEAR USER HABITS"
                app.query_one("#expressions").scroll_to_widget(app.query_one("#clear-user-expressions"))
                await pilot.pause()
                app.query_one("#clear-user-expressions", Button).press()
                await pilot.pause()
                await pilot.pause()
                assert "暂无已学习" in str(app.query_one("#user-expression-list", Static).render())
            store.close()

    asyncio.run(scenario())


def test_expression_learning_uses_durable_ten_round_cursor():
    from neo_agent.runtime import AgentRuntime, ExpressionService

    with tempfile.TemporaryDirectory() as directory:
        store = DiskStore.open(str(Path(directory) / "agent.vdisk"))
        runtime = AgentRuntime(store, model=object())
        service = ExpressionService(store, learner=lambda _text: '[{"expression_pattern":"2333","meaning":"大笑","confidence":0.7}]')
        transcript = [{"user": f"2333 {index}", "assistant": "收到"} for index in range(10)]
        runtime._maybe_learn_user_expressions("chat", transcript[:9], service)
        assert service.habits() == []
        runtime._maybe_learn_user_expressions("chat", transcript, service)
        assert service.habits()[0]["expression_pattern"] == "2333"
        assert store.read_json("/runtime/expression-learning/chat.json")["last_round"] == 10
        store.close()


def test_emotion_service_persists_explainable_dimensions_and_history():
    from neo_agent.runtime import EmotionService
    from langchain_core.messages import AIMessage

    class Model:
        def invoke(self, _messages):
            return AIMessage(content='{"impression":"愿意交流","score_change":2,"sentiment":"positive","relationship_type":"熟悉中","emotional_tone":"积极","key_topics":["项目"],"analysis":"持续合作","dimensions":{"warmth":80,"trust":60,"familiarity":40,"tension":10}}')

    with tempfile.TemporaryDirectory() as directory:
        store = DiskStore.open(str(Path(directory) / "agent.vdisk"))
        record = EmotionService(store, Model()).analyze("r1", [
            {"role": "user", "content": "我们继续开发"}, {"role": "assistant", "content": "好的"},
        ])
        assert record["overall_score"] == 52
        assert record["dimensions"]["warmth"] == 80
        assert store.emotion_history("r1")[0]["relationship_type"] == "熟悉中"
        assert store.events()[-1]["message"] == "relationship.emotion.analyzed"
        store.close()


def test_runtime_log_filter_clear_is_audited_and_non_destructive():
    with tempfile.TemporaryDirectory() as directory:
        store = DiskStore.open(str(Path(directory) / "agent.vdisk"))
        store.append_event("conversation.turn.completed", {"message": "one"})
        store.append_event("plugin.execution.failed", {"message": "denied"})
        assert len(store.runtime_logs(event_type="errors")) == 1
        assert len(store.runtime_logs(search="one")) == 1
        original_count = len(store.events(20))
        cutoff = store.clear_runtime_log_view()
        visible = store.runtime_logs()
        assert visible and all(row["message"] == "runtime.logs.view_cleared" for row in visible)
        assert len(store.events(20)) == original_count + 1
        assert store.runtime_log_cutoff() == cutoff
        store.close()


def test_runtime_logs_tui_filter_and_clear_confirmation():
    import asyncio
    from textual.widgets import Button, Input, Select, Static
    from neo_agent.ui.tui import NeoConsole

    async def scenario():
        with tempfile.TemporaryDirectory() as directory:
            store = DiskStore.open(str(Path(directory) / "agent.vdisk"))
            store.append_event("plugin.execution.failed", {"plugin_id": "demo"})
            store.append_event("conversation.turn.completed", {"conversation_id": "c1"})
            app = NeoConsole(store)
            async with app.run_test(size=(140, 50)) as pilot:
                await pilot.press("0")
                await pilot.pause()
                app.query_one("#runtime-log-filter", Select).value = "errors"
                app.refresh_runtime_logs()
                assert "plugin.execution.failed" in str(app.query_one("#records-view", Static).render())
                assert "conversation.turn.completed" not in str(app.query_one("#records-view", Static).render())
                app.query_one("#clear-runtime-logs-confirm", Input).value = "CLEAR LOG VIEW"
                app.clear_runtime_logs()
                assert "runtime.logs.view_cleared" in str(app.query_one("#records-view", Static).render())
                assert len(store.events(20)) >= 3
            store.close()

    asyncio.run(scenario())


def test_tui_renders_full_entity_and_channel_detail_fields():
    import asyncio
    from textual.widgets import Static
    from neo_agent.ui.tui import NeoConsole

    async def scenario():
        with tempfile.TemporaryDirectory() as directory:
            store = DiskStore.open(str(Path(directory) / "agent.vdisk"))
            store.save_document("entities", "entity-1", {"name": "月球", "entity_type": "place", "definition": "地球的天然卫星"})
            store.save_document("channels", "channel-1", {"name": "开发群", "platform": "demo", "state": "configured", "config": {"room": "neo-dev"}})
            app = NeoConsole(store)
            async with app.run_test(size=(140, 50)) as pilot:
                await pilot.press("ctrl+4")
                await pilot.pause()
                assert "地球的天然卫星" in str(app.query_one("#entity-list", Static).render())
                await pilot.press("ctrl+2")
                await pilot.pause()
                assert "neo-dev" in str(app.query_one("#channel-list", Static).render())
            store.close()

    asyncio.run(scenario())


def test_schedule_intent_planning_and_similarity_are_conservative():
    from datetime import datetime
    from neo_agent.services import SchedulePlanningService

    with tempfile.TemporaryDirectory() as directory:
        store = DiskStore.open(str(Path(directory) / "agent.vdisk"))
        planner = SchedulePlanningService(store)
        now = datetime.fromisoformat("2026-10-02T10:00:00+08:00")
        parsed = planner.detect_intent("明天 19:30 安排一起看电影", now=now)
        assert parsed["intent"] == "create"
        assert parsed["title"] == "一起看电影"
        assert parsed["due_at"] == "2026-10-03T19:30:00+08:00"
        iso_parsed = planner.detect_intent("安排 2026-10-03 19:00 会议", now=now)
        assert iso_parsed["title"] == "会议"
        assert iso_parsed["due_at"] == "2026-10-03T19:00:00+08:00"
        next_weekday = planner.detect_intent("下周三下午3点安排项目复盘", now=now)
        assert next_weekday["date"] == "2026-10-07"
        assert next_weekday["title"] == "项目复盘"
        assert next_weekday["due_at"] == "2026-10-07T15:00:00+08:00"
        next_occurrence = planner.detect_intent("周一 09:30 预约医生", now=now)
        assert next_occurrence["date"] == "2026-10-05"
        assert next_occurrence["title"] == "医生"
        assert planner.detect_intent("帮我安排", now=now)["needs_clarification"]

        store.create_schedule("movie", {
            "title": "一起看电影", "description": "晚上看电影", "due_at": parsed["due_at"],
            "end_at": "2026-10-03T21:00:00+08:00", "type": "appointment",
        })
        similar = planner.compare_similar({"title": "一起看电影", "description": "晚上电影", "due_at": parsed["due_at"]})
        assert similar and similar[0]["schedule"]["id"] == "movie"
        assert similar[0]["recommendation"] == "review_before_create"
        store.close()


def test_human_question_is_durable_and_single_resolution():
    from neo_agent.services import InterruptQuestionService

    with tempfile.TemporaryDirectory() as directory:
        image = str(Path(directory) / "agent.vdisk")
        store = DiskStore.open(image)
        service = InterruptQuestionService(store)
        request = service.ask("几点方便？", context="需要安排会议", conversation_id="room-1")
        assert service.pending()[0]["id"] == request["id"]
        store.close()

        reopened = DiskStore.open(image)
        service = InterruptQuestionService(reopened)
        resolved = service.resolve(request["id"], "下午三点")
        assert resolved["status"] == "answered"
        assert resolved["answer"] == "下午三点"
        assert service.pending() == []
        import pytest
        with pytest.raises(ValueError):
            service.resolve(request["id"], "再次回答")
        reopened.close()


def test_tui_human_question_workflow():
    import asyncio
    from textual.widgets import Input, Static
    from neo_agent.services import InterruptQuestionService
    from neo_agent.ui.tui import NeoConsole

    async def scenario():
        with tempfile.TemporaryDirectory() as directory:
            store = DiskStore.open(str(Path(directory) / "agent.vdisk"))
            request = InterruptQuestionService(store).ask("确认是否参加？", conversation_id="group-9")
            app = NeoConsole(store)
            async with app.run_test(size=(120, 40)) as pilot:
                app.action_navigate("人机协作")
                await pilot.pause()
                assert request["id"] in str(app.query_one("#question-list", Static).render())
                app.query_one("#question-id", Input).value = request["id"]
                app.query_one("#question-answer", Input).value = "参加"
                await pilot.click("#resolve-question")
                await pilot.pause()
                assert store.get_document("question_requests", request["id"])["answer"] == "参加"
            store.close()

    asyncio.run(scenario())


def test_multi_agent_workflow_pauses_persists_and_resumes_after_human_answer():
    import asyncio
    from pydantic import BaseModel
    from neo_agent.services.collaboration import MultiAgentCoordinator
    from neo_agent.services import InterruptQuestionService

    class ScriptedModel:
        def with_structured_output(self, schema):
            parent = self
            class Runner:
                def invoke(self, _messages):
                    if schema.__name__ == "TaskUnderstanding":
                        return schema(summary="完成用户请求", requirements=["按要求执行"])
                    if schema.__name__ == "ExecutionPlan":
                        return schema(steps=[{"description": "收集偏好", "agent_role": "协调专家"}])
                    if schema.__name__ == "StepResult":
                        return schema(output="需要确认具体时间。", needs_user_input=True, question="你偏好上午还是下午？")
                    if schema.__name__ == "TaskVerification":
                        return schema(completed=True, reason="已获得偏好，步骤闭环。")
                    raise AssertionError(schema)
            return Runner()

    async def scenario():
        with tempfile.TemporaryDirectory() as directory:
            image = str(Path(directory) / "agent.vdisk")
            store = DiskStore.open(image)
            coordinator = MultiAgentCoordinator(store, model=ScriptedModel())
            paused = coordinator.run_task(title="安排会面", description="与用户确定会面计划", task_id="meet-run")
            assert paused["status"] == "awaiting_user"
            assert paused["question_id"]
            assert paused["workspace"] == "/workspaces/tasks/meet-run"
            event_record = store.get_document("event_records", "meet-run")
            assert event_record["type"] == "collaboration.task"
            assert event_record["workflow_id"] == paused["id"]
            assert event_record["workspace"] == "/workspaces/events/meet-run"
            assert event_record["status"] == "awaiting_user"
            store.close()

            reopened = DiskStore.open(image)
            question_service = InterruptQuestionService(reopened)
            question_service.resolve(paused["question_id"], "下午")
            resumed = MultiAgentCoordinator(reopened, model=ScriptedModel()).resume("meet-run")
            assert resumed["status"] == "completed"
            assert resumed["results"][-1]["user_answer"] == "下午"
            assert resumed["verification"]["completed"] is True
            assert any(event["message"] == "workflow.completed" for event in reopened.events())
            event_record = reopened.get_document("event_records", "meet-run")
            assert event_record["status"] == "completed"
            assert event_record["workflow_status"] == "completed"
            assert event_record["next_step"] == 1
            reopened.close()

    asyncio.run(scenario())


def test_tui_can_start_multi_agent_workflow():
    import asyncio
    from textual.widgets import Input, Static, TextArea
    from neo_agent.ui.tui import NeoConsole

    class ScriptedModel:
        def with_structured_output(self, schema):
            class Runner:
                def invoke(self, _messages):
                    if schema.__name__ == "TaskUnderstanding":
                        return schema(summary="确认目标")
                    if schema.__name__ == "ExecutionPlan":
                        return schema(steps=[{"description": "完成任务", "agent_role": "执行专家"}])
                    if schema.__name__ == "StepResult":
                        return schema(output="已完成")
                    if schema.__name__ == "TaskVerification":
                        return schema(completed=True, reason="验收通过")
                    raise AssertionError(schema)
            return Runner()

    async def scenario():
        with tempfile.TemporaryDirectory() as directory:
            store = DiskStore.open(str(Path(directory) / "agent.vdisk"))
            app = NeoConsole(store, coordinator_model=ScriptedModel())
            async with app.run_test(size=(120, 48)) as pilot:
                app.action_navigate("任务编排")
                app.query_one("#collaboration-title", Input).value = "测试任务"
                app.query_one("#collaboration-description", TextArea).text = "执行一项可验证工作"
                await pilot.pause()
                await pilot.click("#start-collaboration")
                await pilot.pause()
                runs = str(app.query_one("#collaboration-runs", Static).render())
                assert "completed" in runs
                assert "测试任务" in runs
                assert "VFS 工作区：/workspaces/tasks/" in runs
            store.close()

    asyncio.run(scenario())


def test_tui_shortcuts_reach_every_management_page_and_refresh_its_view():
    import asyncio
    from neo_agent.ui.tui import NeoConsole

    async def scenario():
        with tempfile.TemporaryDirectory() as directory:
            store = DiskStore.open(str(Path(directory) / "agent.vdisk"))
            app = NeoConsole(store)
            keys_and_views = [
                ("1", "总览", "content"), ("2", "虚拟群友", "characters"),
                ("3", "对话", "chat"), ("4", "事件流", "events"),
                ("5", "日程", "schedules"), ("6", "知识库", "knowledge"),
                ("7", "关系", "relationships"), ("8", "环境与域", "environment"),
                ("9", "能力与 NPS", "plugins"), ("0", "运行记录", "records"),
                ("ctrl+1", "存储与记忆", "storage"), ("ctrl+2", "频道连接", "channels"),
                ("ctrl+3", "系统设置", "settings"), ("ctrl+4", "实体管理", "entities"),
                ("ctrl+5", "表达风格", "expressions"), ("ctrl+6", "人机协作", "human-questions"),
                ("ctrl+7", "任务编排", "collaboration"),
            ]
            async with app.run_test(size=(140, 50)) as pilot:
                for key, view, pane_id in keys_and_views:
                    await pilot.press(key)
                    await pilot.pause()
                    assert app.active_view == view
                    assert app.query_one(f"#{pane_id}").display is True
                    await pilot.press("r")
                    await pilot.pause()
                    assert app.active_view == view
                    assert app.query_one(f"#{pane_id}").display is True
            store.close()

    asyncio.run(scenario())


def test_configuration_preview_is_validated_and_import_prevalidates_entire_bundle():
    import asyncio
    import json
    from textual.widgets import SelectionList, TextArea, Static
    from neo_agent.runtime import ConfigurationService
    from neo_agent.ui.tui import NeoConsole

    with tempfile.TemporaryDirectory() as directory:
        store = DiskStore.open(str(Path(directory) / "agent.vdisk"))
        service = ConfigurationService(store)
        bundle = {
            "format": "neo-agent/config/v1",
            "characters": [{"id": "mika", "name": "米卡"}],
            "knowledge": [{"id": "fact-1", "title": "群规"}],
        }
        assert service.preview(bundle) == {
            "format": "neo-agent/config/v1",
            "categories": ["characters", *service.COLLECTIONS],
            "counts": {"characters": 1, "knowledge": 1},
            "total": 2,
        }
        assert dict(service.category_labels())["知识库"] == "knowledge"
        selected = service.export(categories=["knowledge"])
        assert set(selected) == {"format", "knowledge"}
        assert service.import_config({
            "format": service.FORMAT,
            "characters": [{"id": "not-imported", "name": "不导入"}],
            "knowledge": [{"id": "selected", "title": "只导入知识"}],
        }, categories=["knowledge"]) == {"knowledge": 1}
        assert store.character("not-imported") is None
        assert store.get_document("knowledge", "selected")["title"] == "只导入知识"
        invalid = {
            "format": "neo-agent/config/v1",
            "characters": [{"id": "mika", "name": "米卡"}],
            "knowledge": [{"id": "fact-1", "title": "群规"}, {"id": "fact-1", "title": "重复"}],
        }
        with pytest.raises(ValueError, match="重复 ID"):
            service.import_config(invalid)
        assert store.character("mika") is None
        assert store.get_document("knowledge", "fact-1") is None

        app = NeoConsole(store)

        async def scenario():
            async with app.run_test(size=(140, 50)) as pilot:
                editor = app.query_one("#config-json", TextArea)
                editor.text = json.dumps(bundle, ensure_ascii=False)
                await pilot.press("ctrl+1")
                await pilot.pause()
                categories = app.query_one("#config-categories", SelectionList)
                categories.deselect_all()
                assert categories.selected == []
                app.query_one("#select-all-config-categories").press()
                await pilot.pause()
                assert len(categories.selected) == len(service.COLLECTIONS) + 1
                categories.deselect_all()
                categories.select("knowledge")
                app.query_one("#export-config").press()
                await pilot.pause()
                exported = json.loads(editor.text)
                assert set(exported) == {"format", "knowledge"}
                editor.text = json.dumps(bundle, ensure_ascii=False)
                app.query_one("#preview-config").press()
                await pilot.pause()
                assert "knowledge: 1 条" in str(app.query_one("#config-preview", Static).render())
                assert store.character("mika") is None
                app.query_one("#import-config").press()
                await pilot.pause()
                assert store.character("mika") is None
                assert store.get_document("knowledge", "fact-1")["title"] == "群规"

        asyncio.run(scenario())
        store.close()


def test_schedule_suggestions_use_structured_langchain_model_and_stay_inside_free_slots():
    from neo_agent.services import SchedulePlanningService

    class StructuredModel:
        def __init__(self, result):
            self.result = result
            self.schema = None
            self.messages = None

        def with_structured_output(self, schema):
            self.schema = schema
            return self

        def invoke(self, messages):
            self.messages = messages
            return self.result

    with tempfile.TemporaryDirectory() as directory:
        store = DiskStore.open(str(Path(directory) / "agent.vdisk"))
        slot = {"start_at": "2026-10-03T14:00:00+08:00", "end_at": "2026-10-03T15:30:00+08:00"}
        model = StructuredModel({"suggestions": [{
            "title": "一起玩桌游", "description": "挑一款合作桌游", "time_slot_index": 0,
            "duration_minutes": 60, "involves_user": True, "reason": "角色和用户都喜欢桌游",
        }]})
        planner = SchedulePlanningService(store, model=model)
        planner.find_free_slots = lambda *_args, **_kwargs: [slot]
        suggestions = planner.temporary_suggestions(
            "2026-10-03T00:00:00+08:00", "2026-10-04T00:00:00+08:00",
            character_name="米卡", hobbies="桌游", context="最近聊过合作游戏",
        )
        assert model.schema is not None
        assert "桌游" in str(model.messages)
        assert suggestions == [{
            "title": "一起玩桌游", "description": "挑一款合作桌游",
            "due_at": "2026-10-03T14:00:00+08:00", "end_at": "2026-10-03T15:00:00+08:00",
            "type": "temporary", "priority": "low", "status": "suggested",
            "involves_user": True, "reason": "角色和用户都喜欢桌游",
        }]
        assert store.schedules() == []  # suggestions require explicit confirmation before persistence
        store.close()


def test_schedule_model_cannot_place_suggestion_outside_free_time():
    from neo_agent.services import SchedulePlanningService

    class StructuredModel:
        def with_structured_output(self, _schema):
            return self

        def invoke(self, _messages):
            return {"suggestions": [{
                "title": "越界活动", "time_slot_index": 9, "duration_minutes": 60,
                "reason": "invalid slot",
            }]}

    with tempfile.TemporaryDirectory() as directory:
        store = DiskStore.open(str(Path(directory) / "agent.vdisk"))
        planner = SchedulePlanningService(store, model=StructuredModel())
        planner.find_free_slots = lambda *_args, **_kwargs: [{
            "start_at": "2026-10-03T14:00:00+08:00", "end_at": "2026-10-03T15:30:00+08:00",
        }]
        with pytest.raises(ValueError, match="不存在的空闲时段索引"):
            planner.temporary_suggestions("2026-10-03T00:00:00+08:00", "2026-10-04T00:00:00+08:00")
        assert store.schedules() == []
        store.close()


def test_schedule_suggestion_console_requires_explicit_create_after_review():
    import asyncio
    from textual.widgets import Input, Static
    from neo_agent.ui.tui import NeoConsole

    class StructuredModel:
        def with_structured_output(self, _schema):
            return self

        def invoke(self, _messages):
            return {"suggestions": [{
                "title": "米卡读书", "description": "看一本科幻小说", "time_slot_index": 0,
                "duration_minutes": 30, "involves_user": False, "reason": "符合角色兴趣",
            }]}

    async def scenario():
        with tempfile.TemporaryDirectory() as directory:
            store = DiskStore.open(str(Path(directory) / "agent.vdisk"))
            app = NeoConsole(store, schedule_planning_model=StructuredModel())
            async with app.run_test(size=(140, 50)) as pilot:
                await pilot.press("5")
                await pilot.pause()
                app.query_one("#schedule-range-start", Input).value = "2026-10-03T12:00:00+08:00"
                app.query_one("#schedule-range-end", Input).value = "2026-10-03T15:00:00+08:00"
                app.query_one("#generate-schedule-suggestions").press()
                await pilot.pause()
                assert "米卡读书" in str(app.query_one("#schedule-suggestions", Static).render())
                assert store.schedules() == []
                app.query_one("#apply-schedule-suggestion").press()
                await pilot.pause()
                assert app.query_one("#schedule-title", Input).value == "米卡读书"
                assert app.query_one("#schedule-type", Input).value == "temporary"
                assert store.schedules() == []
                app.query_one("#create-schedule").press()
                await pilot.pause()
                rows = store.schedules()
                assert len(rows) == 1
                assert rows[0]["title"] == "米卡读书"
                assert rows[0]["collaboration_status"] == "pending"
            store.close()

    asyncio.run(scenario())


def test_schedule_similarity_uses_langchain_structured_judgment_when_configured():
    from neo_agent.services import SchedulePlanningService

    class StructuredModel:
        def with_structured_output(self, schema):
            self.schema = schema
            return self

        def invoke(self, messages):
            self.messages = messages
            return {"is_similar": True, "reason": "两项都是同一场桌游聚会", "similarity": 0.91}

    with tempfile.TemporaryDirectory() as directory:
        store = DiskStore.open(str(Path(directory) / "agent.vdisk"))
        store.create_schedule("existing", {
            "title": "周末聚会", "description": "周六一起玩桌游", "due_at": "2026-10-03T18:00:00+08:00",
        })
        model = StructuredModel()
        planner = SchedulePlanningService(store, model=model)
        results = planner.compare_similar({
            "title": "棋盘游戏", "description": "约朋友玩桌游", "due_at": "2026-10-03T14:00:00+08:00",
        })
        assert model.schema is not None
        assert results[0]["schedule"]["id"] == "existing"
        assert results[0]["similarity"] == 0.91
        assert results[0]["reason"] == "两项都是同一场桌游聚会"
        assert results[0]["recommendation"] == "review_before_create"
        assert store.get_schedule("existing") is not None
        store.close()


def test_schedule_console_gates_possible_duplicate_until_operator_confirms():
    import asyncio
    from textual.widgets import Button, Input, Static
    from neo_agent.ui.tui import NeoConsole

    async def scenario():
        with tempfile.TemporaryDirectory() as directory:
            store = DiskStore.open(str(Path(directory) / "agent.vdisk"))
            store.create_schedule("existing", {
                "title": "周末玩桌游", "description": "一起玩合作桌游", "due_at": "2026-10-03T14:00:00+08:00",
            })
            app = NeoConsole(store)
            async with app.run_test(size=(140, 50)) as pilot:
                await pilot.press("5")
                await pilot.pause()
                app.query_one("#schedule-id", Input).value = "candidate"
                app.query_one("#schedule-title", Input).value = "周末玩桌游"
                app.query_one("#schedule-due", Input).value = "2026-10-03T16:00:00+08:00"
                app.query_one("#schedule-description", Input).value = "一起玩合作桌游"
                app.query_one("#create-schedule").press()
                await pilot.pause()
                assert len(store.schedules()) == 1
                assert app.query_one("#confirm-create-similar-schedule", Button).disabled is False
                assert "发现可能重复" in str(app.query_one("#schedule-analysis", Static).render())
                app.query_one("#confirm-create-similar-schedule").press()
                await pilot.pause()
                assert len(store.schedules()) == 2
                assert app.query_one("#confirm-create-similar-schedule", Button).disabled is True
            store.close()

    asyncio.run(scenario())


def test_schedule_intent_uses_langchain_structured_analysis_and_conservative_time_resolution():
    from datetime import datetime
    from neo_agent.services import SchedulePlanningService

    class StructuredModel:
        def __init__(self, result):
            self.result = result

        def with_structured_output(self, schema):
            self.schema = schema
            return self

        def invoke(self, messages):
            self.messages = messages
            return self.result

    with tempfile.TemporaryDirectory() as directory:
        store = DiskStore.open(str(Path(directory) / "agent.vdisk"))
        model = StructuredModel({
            "intent": "create", "title": "一起喝咖啡", "description": "和用户见面",
            "time_expression": "明天上午", "start_at": None, "end_at": None,
            "involves_agent": True, "involves_user": True, "confidence": 0.93,
            "reasoning": "对话上下文明确为邀约",
        })
        planner = SchedulePlanningService(store, model=model)
        result = planner.detect_intent(
            "周末一起去喝咖啡吗？", now=datetime.fromisoformat("2026-10-02T10:00:00+08:00"),
            character_name="米卡", context="用户问明天是否有空",
        )
        assert model.schema is not None
        assert "米卡" in str(model.messages)
        assert "用户问明天是否有空" in str(model.messages)
        assert result["intent"] == "create"
        assert result["due_at"] == "2026-10-03T09:00:00+08:00"
        assert result["end_at"] == "2026-10-03T11:00:00+08:00"
        assert result["involves_user"] is True
        assert result["confidence"] == 0.93
        assert result["needs_clarification"] is False
        store.close()


def test_schedule_intent_marks_model_output_with_invalid_interval_for_clarification():
    from datetime import datetime
    from neo_agent.services import SchedulePlanningService

    class StructuredModel:
        def with_structured_output(self, _schema):
            return self

        def invoke(self, _messages):
            return {
                "intent": "create", "title": "会议", "description": "", "time_expression": "",
                "start_at": "2026-10-03T11:00:00", "end_at": "2026-10-03T10:00:00",
                "involves_agent": False, "involves_user": False, "confidence": 0.8, "reasoning": "",
            }

    with tempfile.TemporaryDirectory() as directory:
        store = DiskStore.open(str(Path(directory) / "agent.vdisk"))
        result = SchedulePlanningService(store, model=StructuredModel()).detect_intent(
            "安排会议", now=datetime.fromisoformat("2026-10-02T10:00:00+08:00"),
        )
        assert result["needs_clarification"] is True
        assert result["missing"] == ["valid end time"]
        assert result["due_at"] == "2026-10-03T11:00:00+08:00"
        store.close()


def test_agent_runtime_injects_langchain_model_into_schedule_plugin_tools():
    from neo_agent.runtime import AgentRuntime
    from neo_agent.plugins import PluginRegistry

    class Model:
        def with_structured_output(self, _schema):
            return self

        def invoke(self, _messages):
            return {
                "intent": "create", "title": "一起骑行", "description": "",
                "time_expression": "明天上午", "start_at": None, "end_at": None,
                "involves_agent": True, "involves_user": True, "confidence": 0.9,
                "reasoning": "从对话上下文识别出邀约",
            }

    with tempfile.TemporaryDirectory() as directory:
        store = DiskStore.open(str(Path(directory) / "agent.vdisk"))
        model = Model()
        registry = PluginRegistry(store)
        runtime = AgentRuntime(store, model=model, plugin_registry=registry)
        assert registry.model is model
        result = runtime._tool_by_name["detect_schedule_intent"].invoke({
            "text": "周末一起骑行吗？", "character_name": "米卡", "context": "用户问明天是否有空",
        })
        assert result["due_at"].startswith("2026-10-03T09:00:00")
        assert result["involves_user"] is True
        store.close()
