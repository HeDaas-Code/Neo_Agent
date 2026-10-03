"""Application persistence on PyVDisk's confined DataDisk sandbox.

All durable application state lives in one .vdisk image. There is deliberately
no SQLite or host-directory persistence fallback: PyVDisk is the storage API.
"""
from __future__ import annotations

import json
import hashlib
import math
import re
import uuid
from pathlib import PurePosixPath
from typing import Any

from pyvdisk import AgentSandbox, DurableQueue

from .vfs_workspace import VFSWorkspace


class DiskStore:
    """JSON document store over the audited PyVDisk AgentSandbox surface."""

    def __init__(self, sandbox: AgentSandbox):
        self.sandbox = sandbox
        self._ensure_dir("/characters")
        self._ensure_dir("/groups")
        self._ensure_dir("/schedules")
        self._ensure_dir("/runtime")
        self._ensure_dir("/runtime/conversations")
        self._ensure_dir("/workspaces/events")
        self._ensure_dir("/workspaces/tasks")
        for namespace in ("knowledge", "memories", "relationships", "environments", "domains", "channels", "plugins", "base_knowledge", "entities", "short_term", "long_term", "emotions", "expressions", "workflows", "groups", "event_records", "question_requests", "environment_objects", "environment_connections", "vision_logs"):
            self._ensure_dir(f"/{namespace}")
        self._ensure_event_stream()
        self.schedule_queue = DurableQueue(checkpoint_store=self.sandbox.disk.checkpoints, namespace="neo-agent-schedules", max_attempts=8, backoff_base=15, backoff_max=900)
        self._ensure_memory_collection()

    @classmethod
    def open(cls, image: str, *, size_bytes: int = 128 << 20) -> "DiskStore":
        try:
            sandbox = AgentSandbox.open(image, name="neo-agent", allow_delete=True)
        except FileNotFoundError:
            sandbox = AgentSandbox.create(
                image, size_bytes=size_bytes, label="Neo Agent runtime",
                name="neo-agent", allow_delete=True,
            )
        return cls(sandbox)

    def ensure_directory(self, path: str) -> None:
        """Ensure a directory exists through the PyVDisk sandbox boundary."""
        if not path.startswith("/") or ".." in PurePosixPath(path).parts:
            raise ValueError("DataDisk paths must be absolute and cannot traverse parents")
        if not self.sandbox.exists(path):
            self.sandbox.make_directory(path)

    def event_workspace(self, event_id: str) -> VFSWorkspace:
        """Return the PyVDisk-VFS-only workspace for one managed event."""
        return VFSWorkspace(self.sandbox, "events", self._validate_id(event_id, "event_id"))

    def task_workspace(self, task_id: str) -> VFSWorkspace:
        """Return the PyVDisk-VFS-only workspace for one task/workflow."""
        return VFSWorkspace(self.sandbox, "tasks", self._validate_id(task_id, "task_id"))

    def _ensure_dir(self, path: str) -> None:
        # Private convenience for DiskStore internals; external services use the
        # public ensure_directory() boundary.
        self.ensure_directory(path)

    def read_json(self, path: str, default: Any = None) -> Any:
        if not self.sandbox.exists(path):
            return default
        return json.loads(self.sandbox.read_text(path))

    def write_json(self, path: str, value: Any) -> None:
        parent = str(PurePosixPath(path).parent)
        self._ensure_dir(parent)
        payload = json.dumps(value, ensure_ascii=False, indent=2) + "\n"
        self.sandbox.write(path, payload)

    @staticmethod
    def validate_character_id(character_id: str) -> str:
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,27}", character_id):
            raise ValueError("character_id may contain only letters, digits, '_' and '-' (max 27)")
        return character_id

    def character(self, character_id: str) -> dict[str, Any] | None:
        character_id = self.validate_character_id(character_id)
        return self.read_json(f"/characters/{character_id}/profile.json")

    def save_character(self, character_id: str, profile: dict[str, Any]) -> None:
        character_id = self.validate_character_id(character_id)
        cleaned = {**profile, "id": character_id}
        if not str(cleaned.get("name", "")).strip():
            raise ValueError("character name must not be empty")
        cleaned.setdefault("status", "active")
        self.write_json(f"/characters/{character_id}/profile.json", cleaned)

    def archive_character(self, character_id: str) -> None:
        profile = self.character(character_id)
        if profile is None:
            raise KeyError(f"unknown character: {character_id}")
        profile["status"] = "archived"
        self.save_character(character_id, profile)

    def characters(self, *, include_archived: bool = False) -> list[dict[str, Any]]:
        result = []
        for entry in self.sandbox.list("/characters"):
            if entry["type"] != "dir":
                continue
            profile = self.read_json(f'{entry["path"]}/profile.json')
            if profile and (include_archived or profile.get("status") != "archived"):
                result.append(profile)
        return sorted(result, key=lambda item: item.get("name", "").casefold())

    EVENT_STREAM = "neo-agent-events"

    def _ensure_event_stream(self) -> None:
        if self.EVENT_STREAM not in {item["name"] for item in self.sandbox.disk.logs.list_streams()}:
            self.sandbox.disk.logs.create_stream(self.EVENT_STREAM, segment_events=256)

    def append_event(self, event_type: str, payload: dict[str, Any], *, event_id: str | None = None) -> str:
        """Append a durable, idempotent domain event to PyVDisk LogDisk."""
        import time
        import uuid
        from pyvdisk import LogEvent
        event = LogEvent(
            timestamp_ns=time.time_ns(), level="INFO", logger="neo_agent.events",
            message=event_type, fields={"event_type": event_type, "payload": payload},
            tags={"domain": "agentic"}, event_id=event_id or uuid.uuid4().hex,
        )
        return self.sandbox.disk.logs.append(self.EVENT_STREAM, event).event_id

    def events(self, limit: int = 100) -> list[dict[str, Any]]:
        rows = self.sandbox.disk.logs.tail(self.EVENT_STREAM, limit)
        return [row.to_dict() for row in rows]

    def query_events(self, *, event_type: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
        rows = self.events(limit)
        if event_type:
            rows = [row for row in rows if row.get("message") == event_type or row.get("fields", {}).get("event_type") == event_type]
        return rows

    def runtime_log_cutoff(self) -> int:
        return int(self.read_json("/runtime/log-view.json", default={}).get("cutoff_sequence", -1))

    def clear_runtime_log_view(self) -> int:
        """Hide prior diagnostics from the operator view without erasing audit history."""
        latest = self.events(limit=1)
        cutoff = int(latest[-1].get("sequence", 0)) if latest else self.runtime_log_cutoff()
        self.write_json("/runtime/log-view.json", {"cutoff_sequence": cutoff})
        self.append_event("runtime.logs.view_cleared", {"through_sequence": cutoff})
        return cutoff

    def runtime_logs(self, *, event_type: str | None = None, search: str = "", limit: int = 500) -> list[dict[str, Any]]:
        if not 1 <= limit <= 5000:
            raise ValueError("limit must be between 1 and 5000")
        rows = [row for row in self.events(limit=limit) if int(row.get("sequence", 0)) > self.runtime_log_cutoff()]
        if event_type and event_type != "all":
            if event_type == "errors":
                rows = [row for row in rows if any(word in str(row.get("message", "")).casefold() for word in ("failed", "error", "denied"))]
            else:
                rows = [row for row in rows if event_type.casefold() in str(row.get("message", "")).casefold()]
        needle = search.casefold().strip()
        if needle:
            rows = [row for row in rows if needle in json.dumps(row, ensure_ascii=False).casefold()]
        return rows

    def create_event_record(self, event_id: str, event: dict[str, Any]) -> dict[str, Any]:
        """Create an operator-managed event projection; execution remains in LogDisk."""
        record = self.save_document("event_records", event_id, {**event, "status": event.get("status", "pending")})
        self.append_event("event.record.created", {"id": event_id})
        return record

    def update_event_record(self, event_id: str, changes: dict[str, Any]) -> dict[str, Any]:
        current = self.get_document("event_records", event_id)
        if current is None:
            raise KeyError(f"unknown event record: {event_id}")
        if "status" in changes and changes["status"] not in {
            "pending", "triggered", "awaiting_user", "needs_review", "completed", "failed", "cancelled"
        }:
            raise ValueError("unsupported event status")
        updated = self.save_document("event_records", event_id, changes)
        self.append_event("event.record.updated", {"id": event_id, "status": updated.get("status")})
        return updated

    def delete_event_record(self, event_id: str) -> bool:
        current = self.get_document("event_records", event_id)
        if current is None:
            return False
        self.sandbox.delete(f"/event_records/{self._validate_id(event_id)}.json")
        self.append_event("event.record.deleted", {"id": event_id})
        return True

    def event_records(self) -> list[dict[str, Any]]:
        return self.list_documents("event_records")

    # Domain document API -------------------------------------------------
    # Documents are deliberately stored through the sandbox VFS API, never by
    # opening the image or reaching into its backing files.
    @staticmethod
    def _validate_id(value: str, field: str = "id") -> str:
        if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,22}", value):
            raise ValueError(f"{field} may contain only letters, digits, '_' and '-' (max 22)")
        return value

    @staticmethod
    def validate_document_id(value: str, field: str = "id") -> str:
        """Validate an ID accepted by namespaced PyVDisk documents."""
        return DiskStore._validate_id(value, field)

    DOCUMENT_NAMESPACES = frozenset({"knowledge", "memories", "relationships", "environments", "domains", "channels", "base_knowledge", "entities", "short_term", "long_term", "emotions", "expressions", "workflows", "groups", "event_records", "question_requests", "environment_objects", "environment_connections", "vision_logs"})

    def list_documents(self, namespace: str) -> list[dict[str, Any]]:
        if namespace not in self.DOCUMENT_NAMESPACES:
            raise ValueError(f"unsupported namespace: {namespace}")
        result = []
        for entry in self.sandbox.list(f"/{namespace}"):
            if entry["type"] == "file" and entry["path"].endswith(".json"):
                document = self.read_json(entry["path"])
                if document:
                    result.append(document)
        return sorted(result, key=lambda item: item.get("updated_at", item.get("created_at", "")), reverse=True)

    def get_document(self, namespace: str, document_id: str) -> dict[str, Any] | None:
        if namespace not in self.DOCUMENT_NAMESPACES:
            raise ValueError(f"unsupported namespace: {namespace}")
        document_id = self._validate_id(document_id)
        return self.read_json(f"/{namespace}/{document_id}.json")

    def save_document(self, namespace: str, document_id: str, document: dict[str, Any]) -> dict[str, Any]:
        if namespace not in self.DOCUMENT_NAMESPACES:
            raise ValueError(f"unsupported namespace: {namespace}")
        document_id = self._validate_id(document_id)
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc).isoformat()
        old = self.get_document(namespace, document_id)
        record = {**(old or {}), **document, "id": document_id,
                  "created_at": (old or {}).get("created_at", now), "updated_at": now}
        # Event/task workspace paths are canonical and always point into the
        # PyVDisk VFS. Caller-supplied paths cannot redirect a record elsewhere.
        if namespace == "event_records":
            record["workspace"] = self.event_workspace(document_id).root
        elif namespace == "workflows":
            record["workspace"] = self.task_workspace(document_id).root
        self.write_json(f"/{namespace}/{document_id}.json", record)
        self.append_event(f"{namespace}.saved", {"id": document_id})
        return record

    def delete_document(self, namespace: str, document_id: str) -> bool:
        if namespace not in self.DOCUMENT_NAMESPACES:
            raise ValueError(f"unsupported namespace: {namespace}")
        document_id = self._validate_id(document_id)
        path = f"/{namespace}/{document_id}.json"
        if not self.sandbox.exists(path):
            return False
        self.sandbox.delete(path)
        self.append_event(f"{namespace}.deleted", {"id": document_id})
        if namespace == "memories":
            try:
                self.sandbox.disk.vectors.delete("neo-agent-memory", document_id)
            except Exception:
                pass
        return True

    # Domain projections expose only PyVDisk-backed records and event logs.
    @staticmethod
    def _short_term_id(conversation_id: str) -> str:
        conversation_id = DiskStore._validate_id(conversation_id, "conversation_id")
        return "st-" + hashlib.sha256(conversation_id.encode()).hexdigest()[:19]

    def add_short_term_message(self, role: str, content: str, *, conversation_id: str = "default") -> dict[str, Any]:
        conversation_id = self._validate_id(conversation_id, "conversation_id")
        key = self._short_term_id(conversation_id)
        current = self.get_document("short_term", key) or {"conversation_id": conversation_id, "messages": []}
        current["messages"] = [*current.get("messages", []), {"role": str(role), "content": str(content)}][-100:]
        return self.save_document("short_term", key, current)

    def short_term_messages(self, conversation_id: str = "default", limit: int | None = None) -> list[dict[str, Any]]:
        key = self._short_term_id(conversation_id)
        record = self.get_document("short_term", key) or {}
        rows = list(record.get("messages", []))
        return rows[-limit:] if limit else rows

    def clear_short_term(self, conversation_id: str = "default") -> bool:
        return self.delete_document("short_term", self._short_term_id(conversation_id))

    def clear_all_short_term(self) -> int:
        """Clear short-term conversation windows and write an audit event."""
        rows = self.list_documents("short_term")
        for row in rows:
            self.delete_document("short_term", row["id"])
        self.append_event("memory.short_term.cleared", {"documents": len(rows)})
        return len(rows)

    def clear_all_long_term_summaries(self) -> int:
        """Clear curated long-term summaries (semantic memories are not affected)."""
        rows = self.list_documents("long_term")
        for row in rows:
            self.delete_document("long_term", row["id"])
        self.append_event("memory.long_term.cleared", {"summaries": len(rows)})
        return len(rows)

    def conversation_transcripts(self) -> list[dict[str, Any]]:
        """List persisted conversation transcripts through the sandbox VFS API."""
        rows = []
        for entry in self.sandbox.list("/runtime/conversations"):
            if entry["type"] != "file" or not entry["path"].endswith(".json"):
                continue
            conversation_id = PurePosixPath(entry["path"]).stem
            turns = self.read_json(entry["path"], default=[])
            rows.append({"id": conversation_id, "turns": turns})
        return sorted(rows, key=lambda row: row["id"])

    def delete_conversation(self, conversation_id: str) -> bool:
        """Delete a transcript and its short-term buffer; long-term summaries are retained."""
        conversation_id = self._validate_id(conversation_id, "conversation_id")
        path = f"/runtime/conversations/{conversation_id}.json"
        existed = self.sandbox.exists(path)
        if existed:
            self.sandbox.delete(path)
        short_term_deleted = self.clear_short_term(conversation_id)
        if existed or short_term_deleted:
            self.append_event("conversation.deleted", {"conversation_id": conversation_id})
            return True
        return False

    def add_long_term_summary(self, summary: str, *, conversation_id: str = "default", rounds: int = 0, message_count: int = 0) -> dict[str, Any]:
        record_id = uuid.uuid4().hex[:20]
        return self.save_document("long_term", record_id, {"summary": str(summary), "conversation_id": self._validate_id(conversation_id, "conversation_id"), "rounds": int(rounds), "message_count": int(message_count)})

    def save_long_term_summary(self, summary_id: str, summary: str, *, conversation_id: str = "default", rounds: int = 0, message_count: int = 0) -> dict[str, Any]:
        return self.save_document("long_term", summary_id, {
            "summary": str(summary), "conversation_id": self._validate_id(conversation_id, "conversation_id"),
            "rounds": int(rounds), "message_count": int(message_count),
        })

    def delete_long_term_summary(self, summary_id: str) -> bool:
        return self.delete_document("long_term", summary_id)

    def long_term_summaries(self, conversation_id: str | None = None) -> list[dict[str, Any]]:
        rows = self.list_documents("long_term")
        return [row for row in rows if not conversation_id or row.get("conversation_id") == conversation_id]

    def add_emotion(self, relationship_id: str, tone: str, score: float, *, evidence: str = "") -> dict[str, Any]:
        emotion_id = uuid.uuid4().hex[:20]
        return self.save_document("emotions", emotion_id, {"relationship_id": self._validate_id(relationship_id, "relationship_id"), "tone": str(tone), "score": max(-1.0, min(1.0, float(score))), "evidence": str(evidence)})

    def emotion_history(self, relationship_id: str | None = None) -> list[dict[str, Any]]:
        rows = self.list_documents("emotions")
        return [row for row in rows if not relationship_id or row.get("relationship_id") == relationship_id]

    def activate_environment(self, environment_id: str) -> dict[str, Any]:
        selected = self.get_document("environments", environment_id)
        if selected is None:
            raise KeyError(f"unknown environment: {environment_id}")
        for environment in self.list_documents("environments"):
            active = environment["id"] == environment_id
            if bool(environment.get("active")) != active:
                self.save_document("environments", environment["id"], {"active": active})
        self.append_event("environment.activated", {"environment_id": environment_id})
        return self.get_document("environments", environment_id) or selected

    def link_environment_domain(self, domain_id: str, environment_id: str, *, linked: bool = True) -> dict[str, Any]:
        domain = self.get_document("domains", domain_id)
        if domain is None:
            raise KeyError(f"unknown domain: {domain_id}")
        environment = self.get_document("environments", environment_id)
        if environment is None:
            raise KeyError(f"unknown environment: {environment_id}")
        ids = set(domain.get("environment_ids", []))
        if linked:
            ids.add(environment_id)
        else:
            ids.discard(environment_id)
        return self.save_document("domains", domain_id, {"environment_ids": sorted(ids)})

    def environment_objects(self, environment_id: str, *, visible_only: bool = True) -> list[dict[str, Any]]:
        """Return objects in an environment, ordered by importance then name."""
        if self.get_document("environments", environment_id) is None:
            raise KeyError(f"unknown environment: {environment_id}")
        rows = [row for row in self.list_documents("environment_objects") if row.get("environment_id") == environment_id]
        if visible_only:
            rows = [row for row in rows if row.get("visible", True)]
        return sorted(rows, key=lambda row: (-int(row.get("priority", 50)), row.get("name", "").casefold()))

    def save_environment_object(self, object_id: str, values: dict[str, Any]) -> dict[str, Any]:
        environment_id = self._validate_id(str(values.get("environment_id", "")), "environment_id")
        if self.get_document("environments", environment_id) is None:
            raise KeyError(f"unknown environment: {environment_id}")
        name = str(values.get("name", "")).strip()
        if not name:
            raise ValueError("object name must not be empty")
        priority = int(values.get("priority", 50))
        if not 0 <= priority <= 100:
            raise ValueError("priority must be between 0 and 100")
        properties = values.get("properties", {})
        if not isinstance(properties, dict):
            raise ValueError("properties must be a JSON object")
        return self.save_document("environment_objects", object_id, {
            **values, "environment_id": environment_id, "name": name,
            "priority": priority, "properties": properties,
            "visible": bool(values.get("visible", True)),
        })

    def create_environment_connection(self, from_environment_id: str, to_environment_id: str, *,
                                      connection_type: str = "normal", direction: str = "bidirectional",
                                      description: str = "", connection_id: str | None = None) -> dict[str, Any]:
        from_id = self._validate_id(from_environment_id, "from_environment_id")
        to_id = self._validate_id(to_environment_id, "to_environment_id")
        if from_id == to_id:
            raise ValueError("cannot connect an environment to itself")
        for environment_id in (from_id, to_id):
            if self.get_document("environments", environment_id) is None:
                raise KeyError(f"unknown environment: {environment_id}")
        if direction not in {"bidirectional", "one_way"}:
            raise ValueError("direction must be 'bidirectional' or 'one_way'")
        if any(row.get("from_environment_id") == from_id and row.get("to_environment_id") == to_id
               for row in self.list_documents("environment_connections")):
            raise ValueError("environment connection already exists")
        connection_id = self._validate_id(connection_id or uuid.uuid4().hex[:20])
        return self.save_document("environment_connections", connection_id, {
            "from_environment_id": from_id, "to_environment_id": to_id,
            "connection_type": str(connection_type).strip() or "normal",
            "direction": direction, "description": str(description),
        })

    def environment_connections(self, environment_id: str | None = None) -> list[dict[str, Any]]:
        rows = self.list_documents("environment_connections")
        if environment_id is not None:
            rows = [row for row in rows if environment_id in (row.get("from_environment_id"), row.get("to_environment_id"))]
        return rows

    def can_move_to_environment(self, from_environment_id: str, to_environment_id: str) -> bool:
        if from_environment_id == to_environment_id:
            return self.get_document("environments", from_environment_id) is not None
        return any(
            row.get("from_environment_id") == from_environment_id and row.get("to_environment_id") == to_environment_id
            or row.get("direction") == "bidirectional" and row.get("from_environment_id") == to_environment_id and row.get("to_environment_id") == from_environment_id
            for row in self.list_documents("environment_connections")
        )

    def log_vision_usage(self, query: str, *, environment_id: str | None = None,
                         objects_viewed: list[str] | None = None, context: str = "",
                         triggered_by: str = "auto") -> dict[str, Any]:
        if not str(query).strip():
            raise ValueError("vision query must not be empty")
        if environment_id and self.get_document("environments", environment_id) is None:
            raise KeyError(f"unknown environment: {environment_id}")
        viewed = list(objects_viewed or [])
        for object_id in viewed:
            item = self.get_document("environment_objects", object_id)
            if item is None or environment_id and item.get("environment_id") != environment_id:
                raise ValueError(f"viewed object is not part of the selected environment: {object_id}")
        record_id = uuid.uuid4().hex[:20]
        return self.save_document("vision_logs", record_id, {
            "query": str(query).strip(), "environment_id": environment_id,
            "objects_viewed": viewed, "context": str(context),
            "triggered_by": triggered_by,
        })

    def vision_logs(self, limit: int = 50) -> list[dict[str, Any]]:
        if limit < 1:
            raise ValueError("limit must be positive")
        return self.list_documents("vision_logs")[:limit]

    def set_environment_object_visibility(self, object_id: str, visible: bool) -> dict[str, Any]:
        item = self.get_document("environment_objects", object_id)
        if item is None:
            raise KeyError(f"unknown environment object: {object_id}")
        return self.save_environment_object(object_id, {**item, "visible": bool(visible)})

    def delete_environment(self, environment_id: str) -> bool:
        """Delete an environment and dependent scene objects/edges; retain immutable audits."""
        environment_id = self._validate_id(environment_id, "environment_id")
        if self.get_document("environments", environment_id) is None:
            return False
        for obj in self.list_documents("environment_objects"):
            if obj.get("environment_id") == environment_id:
                self.delete_document("environment_objects", obj["id"])
        for edge in self.list_documents("environment_connections"):
            if environment_id in (edge.get("from_environment_id"), edge.get("to_environment_id")):
                self.delete_document("environment_connections", edge["id"])
        for domain in self.list_documents("domains"):
            member_ids = [item for item in domain.get("environment_ids", []) if item != environment_id]
            if member_ids != domain.get("environment_ids", []) or domain.get("default_environment_id") == environment_id:
                self.save_document("domains", domain["id"], {
                    "environment_ids": member_ids,
                    "default_environment_id": None if domain.get("default_environment_id") == environment_id else domain.get("default_environment_id"),
                })
        return self.delete_document("environments", environment_id)

    def save_domain(self, domain_id: str, values: dict[str, Any]) -> dict[str, Any]:
        name = str(values.get("name", "")).strip()
        if not name:
            raise ValueError("domain name must not be empty")
        default_id = values.get("default_environment_id")
        current = self.get_document("domains", domain_id)
        if default_id:
            if self.get_document("environments", str(default_id)) is None:
                raise KeyError(f"unknown environment: {default_id}")
            member_ids = set((current or {}).get("environment_ids", []))
            if str(default_id) not in member_ids:
                raise ValueError("default environment must be a member of the domain")
        return self.save_document("domains", domain_id, {**values, "name": name})

    def add_environment_to_domain(self, domain_id: str, environment_id: str) -> dict[str, Any]:
        domain = self.get_document("domains", domain_id)
        if domain is None:
            raise KeyError(f"unknown domain: {domain_id}")
        if self.get_document("environments", environment_id) is None:
            raise KeyError(f"unknown environment: {environment_id}")
        ids = set(domain.get("environment_ids", []))
        ids.add(environment_id)
        return self.save_document("domains", domain_id, {"environment_ids": sorted(ids)})

    def remove_environment_from_domain(self, domain_id: str, environment_id: str) -> bool:
        domain = self.get_document("domains", domain_id)
        if domain is None:
            raise KeyError(f"unknown domain: {domain_id}")
        ids = set(domain.get("environment_ids", []))
        if environment_id not in ids:
            return False
        ids.remove(environment_id)
        changes: dict[str, Any] = {"environment_ids": sorted(ids)}
        if domain.get("default_environment_id") == environment_id:
            changes["default_environment_id"] = None
        self.save_document("domains", domain_id, changes)
        return True

    def domain_environments(self, domain_id: str) -> list[dict[str, Any]]:
        domain = self.get_document("domains", domain_id)
        if domain is None:
            raise KeyError(f"unknown domain: {domain_id}")
        members = set(domain.get("environment_ids", []))
        return [row for row in self.list_documents("environments") if row["id"] in members]

    def current_domain(self) -> dict[str, Any] | None:
        active = next((row for row in self.list_documents("environments") if row.get("active")), None)
        if not active:
            return None
        return next((domain for domain in self.list_documents("domains") if active["id"] in domain.get("environment_ids", [])), None)

    def switch_domain(self, domain_id: str) -> dict[str, Any]:
        domain = self.get_document("domains", domain_id)
        if domain is None:
            raise KeyError(f"unknown domain: {domain_id}")
        members = self.domain_environments(domain_id)
        preferred = domain.get("default_environment_id")
        target = next((row for row in members if row["id"] == preferred), None)
        if target is None and members:
            target = members[0]
        if target is None:
            raise ValueError("domain has no member environments; add one before switching")
        self.activate_environment(target["id"])
        self.append_event("domain.switched", {"domain_id": domain_id, "environment_id": target["id"]})
        return {"domain": domain, "environment": self.get_document("environments", target["id"])}

    def advance_recurring_schedule(self, schedule_id: str, *, occurred_at: str) -> dict[str, Any] | None:
        """Advance a weekly schedule after delivery; block the next occurrence on a conflict."""
        schedule = self.get_schedule(schedule_id)
        if schedule is None or schedule.get("type") != "recurring":
            return schedule
        from datetime import datetime, timedelta
        current_due = datetime.fromisoformat(schedule["due_at"].replace("Z", "+00:00"))
        next_due = current_due + timedelta(days=7)
        changes = {"due_at": next_due.isoformat(), "last_occurrence_at": occurred_at,
                   "status": "pending", "queue_revision": int(schedule.get("queue_revision", 1)) + 1}
        if schedule.get("end_at"):
            current_end = datetime.fromisoformat(schedule["end_at"].replace("Z", "+00:00"))
            changes["end_at"] = (current_end + timedelta(days=7)).isoformat()
        conflicts = self.schedule_conflicts(changes["due_at"], changes.get("end_at", changes["due_at"]),
                                            priority=schedule.get("priority", "critical"), exclude_id=schedule_id) if changes.get("end_at") else []
        if conflicts:
            changes["status"] = "recurrence_blocked"
            changes["recurrence_conflicts"] = [item["id"] for item in conflicts]
        updated = {**schedule, **changes}
        self.write_json(f"/schedules/{schedule_id}.json", updated)
        self.append_event("schedule.recurrence.advanced" if not conflicts else "schedule.recurrence.blocked", {
            "schedule_id": schedule_id, "next_due_at": changes["due_at"],
            "conflicts": changes.get("recurrence_conflicts", []),
        })
        return updated

    def confirm_schedule(self, schedule_id: str, confirmed: bool) -> dict[str, Any]:
        schedule = self.get_schedule(schedule_id)
        if schedule is None:
            raise KeyError(f"unknown schedule: {schedule_id}")
        status = "confirmed" if confirmed else "rejected"
        updated = self.update_schedule(schedule_id, {"collaboration_status": status, "status": "pending" if confirmed else "cancelled"})
        self.append_event("schedule.collaboration.decided", {"schedule_id": schedule_id, "confirmed": confirmed})
        return updated

    def save_expression(self, expression_id: str, expression: dict[str, Any]) -> dict[str, Any]:
        return self.save_document("expressions", expression_id, expression)

    def expressions(self) -> list[dict[str, Any]]:
        return self.list_documents("expressions")

    # PyVDisk VectorDisk-backed memory. Hash embeddings are a deterministic
    # baseline; deployments can replace this encoder with model embeddings.
    MEMORY_COLLECTION = "neo-agent-memory"
    MEMORY_DIMENSION = 128

    def _ensure_memory_collection(self) -> None:
        names = {item["name"] for item in self.sandbox.disk.vectors.list_collections()}
        if self.MEMORY_COLLECTION not in names:
            self.sandbox.disk.vectors.create_collection(
                self.MEMORY_COLLECTION, self.MEMORY_DIMENSION, metric="cosine", max_elements=10000
            )

    @classmethod
    def _embed_text(cls, text: str) -> list[float]:
        vector = [0.0] * cls.MEMORY_DIMENSION
        tokens = re.findall(r"[\w\u4e00-\u9fff]+", text.casefold())
        for token in tokens:
            digest = hashlib.blake2b(token.encode("utf-8"), digest_size=8).digest()
            index = int.from_bytes(digest[:4], "little") % cls.MEMORY_DIMENSION
            vector[index] += 1.0 if digest[4] & 1 else -1.0
        norm = math.sqrt(sum(value * value for value in vector)) or 1.0
        return [value / norm for value in vector]

    def save_memory(self, memory_id: str, text: str, *, character_id: str = "default", metadata: dict[str, Any] | None = None) -> dict[str, Any]:
        memory_id = self._validate_id(memory_id)
        text = str(text).strip()
        if not text:
            raise ValueError("memory text must not be empty")
        record = self.save_document("memories", memory_id, {
            "text": text, "character_id": self._validate_id(character_id, "character_id"),
            "metadata": metadata or {},
        })
        self.sandbox.disk.vectors.upsert(
            self.MEMORY_COLLECTION, memory_id, self._embed_text(text),
            {"character_id": record["character_id"], "text": text},
        )
        return record

    def search_memories(self, query: str, *, character_id: str | None = None, limit: int = 8) -> list[dict[str, Any]]:
        if limit < 1 or limit > 100:
            raise ValueError("limit must be between 1 and 100")
        where = {"character_id": self._validate_id(character_id, "character_id")} if character_id else None
        hits = self.sandbox.disk.vectors.search(self.MEMORY_COLLECTION, self._embed_text(query), k=limit, where=where)
        return [{"id": hit["id"], **(self.get_document("memories", hit["id"]) or {}), "distance": hit["distance"]} for hit in hits]

    @staticmethod
    def _validate_schedule_id(schedule_id: str) -> str:
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,22}", schedule_id):
            raise ValueError("schedule_id may contain only letters, digits, '_' and '-' (max 22)")
        return schedule_id

    @staticmethod
    def _schedule_priority_rank(value: Any) -> int:
        ranks = {"low": 1, "1": 1, "medium": 2, "normal": 2, "2": 2,
                 "high": 3, "3": 3, "critical": 4, "4": 4}
        key = str(value if value is not None else "medium").casefold()
        if key not in ranks:
            raise ValueError("priority must be low, medium, high, or critical")
        return ranks[key]

    def schedule_conflicts(self, start_at: str, end_at: str, *, priority: Any = "medium", exclude_id: str | None = None) -> list[dict[str, Any]]:
        from datetime import datetime
        start = datetime.fromisoformat(str(start_at).replace("Z", "+00:00"))
        end = datetime.fromisoformat(str(end_at).replace("Z", "+00:00"))
        if start.tzinfo is None or end.tzinfo is None:
            raise ValueError("schedule interval must include explicit timezones")
        if end <= start:
            raise ValueError("schedule end must be after its start")
        rank = self._schedule_priority_rank(priority)
        conflicts = []
        for existing in self.schedules():
            if existing.get("id") == exclude_id or existing.get("status") in {"cancelled", "rejected", "completed"}:
                continue
            old_end = existing.get("end_at")
            if not old_end:
                continue
            old_start = datetime.fromisoformat(existing["due_at"].replace("Z", "+00:00"))
            old_end = datetime.fromisoformat(old_end.replace("Z", "+00:00"))
            if start < old_end and end > old_start and self._schedule_priority_rank(existing.get("priority", "medium")) >= rank:
                conflicts.append(existing)
        return conflicts

    def create_schedule(self, schedule_id: str, schedule: dict[str, Any]) -> dict[str, Any]:
        """Persist a schedule in PyVDisk FS and enqueue its durable reminder."""
        schedule_id = self._validate_schedule_id(schedule_id)
        from datetime import datetime
        title = str(schedule.get("title", "")).strip()
        due_at = str(schedule.get("due_at", "")).strip()
        if not title or not due_at:
            raise ValueError("schedule requires non-empty title and due_at")
        try:
            parsed_due = datetime.fromisoformat(due_at.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValueError("due_at must be a valid ISO-8601 timestamp") from exc
        if parsed_due.tzinfo is None:
            raise ValueError("due_at must include an explicit timezone")
        schedule_type = str(schedule.get("type", "appointment")).casefold()
        if schedule_type not in {"appointment", "recurring", "temporary", "reminder", "collaboration", "activity"}:
            raise ValueError("type must be appointment, recurring, temporary, reminder, collaboration, or activity")
        schedule["type"] = schedule_type
        if "priority" not in schedule or schedule.get("priority") in (None, ""):
            schedule["priority"] = {"recurring": "critical", "temporary": "low"}.get(schedule_type, "medium")
        priority = schedule["priority"]
        self._schedule_priority_rank(priority)
        if schedule_type == "recurring":
            weekday = schedule.get("weekday")
            if not isinstance(weekday, int) or not 0 <= weekday <= 6:
                raise ValueError("recurring schedule requires weekday in range 0..6")
            if parsed_due.weekday() != weekday:
                raise ValueError("recurring weekday must match due_at weekday")
            if not str(schedule.get("recurrence_pattern", "")).strip():
                raise ValueError("recurring schedule requires recurrence_pattern")
        end_at = schedule.get("end_at")
        if end_at:
            conflicts = self.schedule_conflicts(due_at, str(end_at), priority=priority)
            if conflicts:
                raise ValueError("schedule conflicts with equal-or-higher-priority item(s): " + ", ".join(item["id"] for item in conflicts))
        if self.read_json(f"/schedules/{schedule_id}.json") is not None:
            raise ValueError(f"schedule already exists: {schedule_id}")
        record = {**schedule, "id": schedule_id, "title": title, "due_at": due_at,
                  "status": "pending", "created_at": datetime.now(__import__("datetime").timezone.utc).isoformat()}
        record["queue_revision"] = 1
        self.write_json(f"/schedules/{schedule_id}.json", record)
        self.append_event("schedule.created", {"schedule_id": schedule_id, "title": title, "due_at": due_at})
        return record

    def get_schedule(self, schedule_id: str) -> dict[str, Any] | None:
        schedule_id = self._validate_schedule_id(schedule_id)
        return self.read_json(f"/schedules/{schedule_id}.json")

    def update_schedule(self, schedule_id: str, changes: dict[str, Any]) -> dict[str, Any]:
        """Update a schedule and supersede its queued reminder revision."""
        schedule_id = self._validate_schedule_id(schedule_id)
        current = self.get_schedule(schedule_id)
        if current is None:
            raise KeyError(f"unknown schedule: {schedule_id}")
        changes = dict(changes)
        if "title" in changes:
            changes["title"] = str(changes["title"]).strip()
            if not changes["title"]:
                raise ValueError("schedule title must not be empty")
        if "due_at" in changes:
            from datetime import datetime
            try:
                due = datetime.fromisoformat(str(changes["due_at"]).replace("Z", "+00:00"))
            except ValueError as exc:
                raise ValueError("due_at must be a valid ISO-8601 timestamp") from exc
            if due.tzinfo is None:
                raise ValueError("due_at must include an explicit timezone")
            changes["due_at"] = str(changes["due_at"]).strip()
        if "priority" in changes:
            self._schedule_priority_rank(changes["priority"])
        if "type" in changes:
            changes["type"] = str(changes["type"]).casefold()
            if changes["type"] not in {"appointment", "recurring", "temporary", "reminder", "collaboration", "activity"}:
                raise ValueError("unsupported schedule type")
        if "end_at" in changes and changes["end_at"]:
            from datetime import datetime
            try:
                end = datetime.fromisoformat(str(changes["end_at"]).replace("Z", "+00:00"))
            except ValueError as exc:
                raise ValueError("end_at must be a valid ISO-8601 timestamp") from exc
            if end.tzinfo is None:
                raise ValueError("end_at must include an explicit timezone")
            changes["end_at"] = str(changes["end_at"]).strip()
        updated = {**current, **changes}
        if updated.get("type") == "recurring":
            from datetime import datetime
            weekday = updated.get("weekday")
            due = datetime.fromisoformat(updated["due_at"].replace("Z", "+00:00"))
            if not isinstance(weekday, int) or not 0 <= weekday <= 6 or due.weekday() != weekday:
                raise ValueError("recurring schedule weekday must be 0..6 and match due_at")
            if not str(updated.get("recurrence_pattern", "")).strip():
                raise ValueError("recurring schedule requires recurrence_pattern")
        if updated.get("end_at"):
            conflicts = self.schedule_conflicts(updated["due_at"], updated["end_at"],
                                                priority=updated.get("priority", "medium"), exclude_id=schedule_id)
            if conflicts:
                raise ValueError("schedule conflicts with equal-or-higher-priority item(s): " + ", ".join(item["id"] for item in conflicts))
        reschedule = updated.get("status") == "pending" and (
            updated.get("due_at") != current.get("due_at")
            or updated.get("end_at") != current.get("end_at")
            or updated.get("type") != current.get("type")
            or updated.get("priority") != current.get("priority")
            or current.get("status") != "pending"
        )
        if reschedule:
            revision = int(current.get("queue_revision", 1)) + 1
            for task in self.schedule_queue.list():
                payload = task.payload or {}
                if payload.get("schedule_id") == schedule_id and task.status in ("queued", "running"):
                    self.schedule_queue.cancel(task.id)
            updated["queue_revision"] = revision
        self.write_json(f"/schedules/{schedule_id}.json", updated)
        self.append_event("schedule.updated", {"schedule_id": schedule_id, "rescheduled": reschedule,
                                                "queue_revision": updated.get("queue_revision", 1)})
        return updated

    def delete_schedule(self, schedule_id: str) -> bool:
        schedule_id = self._validate_schedule_id(schedule_id)
        current = self.get_schedule(schedule_id)
        if current is None:
            return False
        for task in self.schedule_queue.list():
            if (task.payload or {}).get("schedule_id") == schedule_id and task.status in ("queued", "running"):
                self.schedule_queue.cancel(task.id)
        self.sandbox.delete(f"/schedules/{schedule_id}.json")
        self.append_event("schedule.deleted", {"schedule_id": schedule_id})
        return True

    def schedules(self) -> list[dict[str, Any]]:
        result = []
        for entry in self.sandbox.list("/schedules"):
            if entry["type"] == "file" and entry["path"].endswith(".json"):
                record = self.read_json(entry["path"])
                if record:
                    result.append(record)
        return sorted(result, key=lambda item: item.get("due_at", ""))

    def schedules_in_range(
        self, start_at: str, end_at: str, *, queryable_only: bool = True,
        active_only: bool = True, include_inactive: bool = False,
    ) -> list[dict[str, Any]]:
        """Return schedules overlapping a timezone-aware half-open time window."""
        from datetime import datetime

        start = datetime.fromisoformat(str(start_at).replace("Z", "+00:00"))
        end = datetime.fromisoformat(str(end_at).replace("Z", "+00:00"))
        if start.tzinfo is None or end.tzinfo is None:
            raise ValueError("time range must include explicit timezones")
        if end <= start:
            raise ValueError("range end must be after its start")
        rows = []
        for item in self.schedules():
            if active_only or not include_inactive:
                if item.get("status") in {"cancelled", "rejected", "completed", "deleted"}:
                    continue
            if queryable_only and item.get("is_queryable", True) is False:
                continue
            item_start = datetime.fromisoformat(item["due_at"].replace("Z", "+00:00"))
            item_end = datetime.fromisoformat(item.get("end_at", item["due_at"]).replace("Z", "+00:00"))
            if item_start < end and item_end > start:
                rows.append(item)
        return sorted(rows, key=lambda item: item["due_at"])

    def free_time_slots(
        self, start_at: str, end_at: str, *, duration_minutes: int,
        queryable_only: bool = True,
    ) -> list[dict[str, str]]:
        """Find gaps of at least duration_minutes in a timezone-aware window."""
        from datetime import datetime, timedelta

        start = datetime.fromisoformat(str(start_at).replace("Z", "+00:00"))
        end = datetime.fromisoformat(str(end_at).replace("Z", "+00:00"))
        if start.tzinfo is None or end.tzinfo is None:
            raise ValueError("time range must include explicit timezones")
        if end <= start:
            raise ValueError("range end must be after its start")
        if isinstance(duration_minutes, bool) or duration_minutes <= 0:
            raise ValueError("duration_minutes must be a positive integer")
        required = timedelta(minutes=duration_minutes)
        cursor = start
        slots = []
        for item in self.schedules_in_range(
            start_at, end_at, queryable_only=queryable_only, active_only=True,
        ):
            item_start = datetime.fromisoformat(item["due_at"].replace("Z", "+00:00"))
            item_end = datetime.fromisoformat(item.get("end_at", item["due_at"]).replace("Z", "+00:00"))
            item_start = max(start, item_start)
            item_end = min(end, item_end)
            if item_start - cursor >= required:
                slots.append({"start_at": cursor.isoformat(), "end_at": item_start.isoformat()})
            cursor = max(cursor, item_end)
        if end - cursor >= required:
            slots.append({"start_at": cursor.isoformat(), "end_at": end.isoformat()})
        return slots

    def schedule_statistics(self) -> dict[str, Any]:
        rows = self.schedules()
        by_status: dict[str, int] = {}
        by_type: dict[str, int] = {}
        by_priority: dict[str, int] = {}
        for item in rows:
            for bucket, key, default in (
                (by_status, "status", "unknown"),
                (by_type, "type", "appointment"),
                (by_priority, "priority", "medium"),
            ):
                label = str(item.get(key, default))
                bucket[label] = bucket.get(label, 0) + 1
        return {"total": len(rows), "by_status": by_status, "by_type": by_type,
                "by_priority": by_priority, "pending_collaboration": sum(
                    item.get("collaboration_status") in {"pending", "pending_confirmation"}
                    for item in rows
                )}

    def schedule_tasks(self) -> list[dict[str, Any]]:
        return [task.__dict__ for task in self.schedule_queue.list()]

    def runtime_overview(self) -> dict[str, Any]:
        return {
            "characters": len(self.characters()),
            "disk_image": getattr(self.sandbox.disk, "path", "configured"),
            "audit": self.sandbox.verify_audit(),
            "tools": len(self.sandbox.tools()),
            "events": self.sandbox.disk.logs.count(self.EVENT_STREAM),
            "schedules": len(self.schedules()),
            "knowledge": len(self.list_documents("knowledge")),
            "relationships": len(self.list_documents("relationships")),
            "emotions": len(self.list_documents("emotions")),
            "memories": len(self.list_documents("memories")),
        }

    def close(self) -> None:
        self.sandbox.close()
