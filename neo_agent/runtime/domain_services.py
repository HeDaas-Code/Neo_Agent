"""Small domain services for the operator console and agent capabilities."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class DomainService:
    """Typed namespace facade over the PyVDisk-backed document API."""
    store: Any
    namespace: str

    def list(self) -> list[dict[str, Any]]:
        return self.store.list_documents(self.namespace)

    def get(self, item_id: str) -> dict[str, Any] | None:
        return self.store.get_document(self.namespace, item_id)

    def save(self, item_id: str, values: dict[str, Any]) -> dict[str, Any]:
        return self.store.save_document(self.namespace, item_id, values)

    def delete(self, item_id: str) -> bool:
        return self.store.delete_document(self.namespace, item_id)


class KnowledgeService(DomainService):
    def __init__(self, store: Any):
        super().__init__(store, "knowledge")

    def search(self, query: str) -> list[dict[str, Any]]:
        needle = query.casefold().strip()
        return [item for item in self.list() if needle in (item.get("title", "") + " " + item.get("content", "")).casefold()]


class RelationshipService(DomainService):
    def __init__(self, store: Any):
        super().__init__(store, "relationships")

    def record_interaction(self, relationship_id: str, *, note: str, delta: float = 0.0,
                           confidence: float = 0.0, round_id: str | None = None) -> dict[str, Any]:
        """Record a turn's proposed change; persist it only after repeated evidence."""
        import hashlib
        import uuid
        confidence = max(0.0, min(1.0, float(confidence)))
        proposed = max(-3.0, min(3.0, float(delta)))
        evidence_round = str(round_id or uuid.uuid4().hex)
        ledger_path = f"/runtime/relationship-evidence/{hashlib.sha256(relationship_id.encode()).hexdigest()[:16]}.json"
        ledger = self.store.read_json(ledger_path, default={"relationship_id": relationship_id, "rounds": {}})
        rounds = dict(ledger.get("rounds", {}))
        if confidence >= 0.8 and proposed:
            rounds.setdefault(evidence_round, {"change": proposed, "confidence": confidence})
        direction = 1 if proposed > 0 else -1 if proposed < 0 else 0
        evidence = [row for row in rounds.values()
                    if (1 if float(row.get("change", 0)) > 0 else -1 if float(row.get("change", 0)) < 0 else 0) == direction
                    and direction != 0]
        committed = direction != 0 and confidence >= 0.8 and len(evidence) >= 3
        change = proposed if committed else 0.0
        if committed:
            rounds = {}
        self.store.write_json(ledger_path, {"relationship_id": relationship_id, "rounds": rounds})
        current = self.get(relationship_id) or {"score": 0.0, "interactions": []}
        score = max(-100.0, min(100.0, float(current.get("score", 0.0)) + change))
        interactions = list(current.get("interactions", []))
        interactions.append({"note": str(note)[:500], "proposed_delta": proposed,
                             "delta": change, "confidence": confidence,
                             "evidence_round": evidence_round, "evidence_count": len(evidence),
                             "persistent_update": committed})
        saved = self.save(relationship_id, {**current, "score": score, "interactions": interactions[-200:]})
        self.store.append_event("relationship.interaction.evidence", {
            "relationship_id": relationship_id, "evidence_round": evidence_round,
            "confidence": confidence, "evidence_count": len(evidence),
            "persistent_update": committed, "score_change": change,
        })
        return saved


class EnvironmentService(DomainService):
    """Environment, scene-object, visual-audit and domain operations."""
    def __init__(self, store: Any):
        super().__init__(store, "environments")

    def activate(self, environment_id: str) -> dict[str, Any]:
        return self.store.activate_environment(environment_id)

    def objects(self, environment_id: str, *, visible_only: bool = True) -> list[dict[str, Any]]:
        return self.store.environment_objects(environment_id, visible_only=visible_only)

    def save_object(self, object_id: str, values: dict[str, Any]) -> dict[str, Any]:
        return self.store.save_environment_object(object_id, values)

    def connections(self, environment_id: str | None = None) -> list[dict[str, Any]]:
        return self.store.environment_connections(environment_id)

    def connect(self, source_id: str, target_id: str, **values: Any) -> dict[str, Any]:
        return self.store.create_environment_connection(source_id, target_id, **values)

    def can_move(self, source_id: str, target_id: str) -> bool:
        return self.store.can_move_to_environment(source_id, target_id)

    def log_vision(self, query: str, **values: Any) -> dict[str, Any]:
        return self.store.log_vision_usage(query, **values)

    def vision_history(self, limit: int = 50) -> list[dict[str, Any]]:
        return self.store.vision_logs(limit)

    def set_object_visibility(self, object_id: str, visible: bool) -> dict[str, Any]:
        return self.store.set_environment_object_visibility(object_id, visible)

    def delete_environment(self, environment_id: str) -> bool:
        return self.store.delete_environment(environment_id)


class DomainRegistry(DomainService):
    def __init__(self, store: Any):
        super().__init__(store, "domains")

    def save_domain(self, domain_id: str, values: dict[str, Any]) -> dict[str, Any]:
        return self.store.save_domain(domain_id, values)

    def members(self, domain_id: str) -> list[dict[str, Any]]:
        return self.store.domain_environments(domain_id)

    def current(self) -> dict[str, Any] | None:
        return self.store.current_domain()

    def switch(self, domain_id: str) -> dict[str, Any]:
        return self.store.switch_domain(domain_id)

    def add_environment(self, domain_id: str, environment_id: str) -> dict[str, Any]:
        return self.store.add_environment_to_domain(domain_id, environment_id)

    def remove_environment(self, domain_id: str, environment_id: str) -> bool:
        return self.store.remove_environment_from_domain(domain_id, environment_id)


class ChannelService(DomainService):
    def __init__(self, store: Any):
        super().__init__(store, "channels")


class MemoryService:
    def __init__(self, store: Any):
        self.store = store

    def remember(self, text: str, *, character_id: str = "default", metadata: dict[str, Any] | None = None) -> dict[str, Any]:
        import uuid
        return self.store.save_memory(uuid.uuid4().hex[:20], text, character_id=character_id, metadata=metadata)

    def recall(self, query: str, *, character_id: str | None = None, limit: int = 8) -> list[dict[str, Any]]:
        return self.store.search_memories(query, character_id=character_id, limit=limit)

    def forget(self, memory_id: str) -> bool:
        return self.store.delete_document("memories", memory_id)
