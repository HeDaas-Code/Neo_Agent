"""Persisted runtime controls and single-active-character lifecycle."""
from __future__ import annotations
from typing import Any


class RuntimeControls:
    PATH = "/runtime/controls.json"

    def __init__(self, store: Any):
        self.store = store

    @property
    def debug(self) -> bool:
        return bool(self.store.read_json(self.PATH, default={}).get("debug", False))

    def set_debug(self, enabled: bool) -> bool:
        state = {**self.store.read_json(self.PATH, default={}), "debug": bool(enabled)}
        self.store.write_json(self.PATH, state)
        self.store.append_event("runtime.debug.changed", {"enabled": bool(enabled)})
        return bool(enabled)


class SingleRoleService:
    def __init__(self, store: Any):
        self.store = store

    def active(self) -> dict[str, Any] | None:
        rows = self.store.characters()
        if len(rows) > 1:
            selected = self.store.read_json("/runtime/active-character.json", default={}).get("id")
            return next((row for row in rows if row["id"] == selected), None)
        return rows[0] if rows else None

    def initialize(self, character_id: str) -> dict[str, Any]:
        rows = self.store.characters()
        selected = next((row for row in rows if row["id"] == character_id), None)
        if selected is None:
            raise KeyError(f"找不到要设为主角色的角色：{character_id}")
        for row in rows:
            if row["id"] != character_id:
                self.store.archive_character(row["id"])
        self.store.write_json("/runtime/active-character.json", {"id": character_id})
        from neo_agent.runtime.itinerary import SceneService
        SceneService(self.store).ensure_initial_environment(activate=True)
        self.store.append_event("character.single_role.initialized", {
            "selected": character_id, "archived_count": max(0, len(rows) - 1),
        })
        return selected

    def save_initial(self, character_id: str, profile: dict[str, Any]) -> dict[str, Any]:
        if not str(profile.get("name", "")).strip():
            raise ValueError("初始化角色必须填写显示名称")
        if not str(profile.get("personality", profile.get("system_prompt", ""))).strip():
            raise ValueError("初始化角色必须填写性格设定")
        if self.store.characters():
            raise ValueError("首次初始化仅在尚无活动角色时可用")
        self.store.save_character(character_id, profile)
        self.store.write_json("/runtime/active-character.json", {"id": character_id})
        from neo_agent.runtime.itinerary import SceneService
        SceneService(self.store).ensure_initial_environment(activate=True)
        self.store.append_event("character.single_role.initialized", {"selected": character_id, "archived_count": 0})
        return self.store.character(character_id)
