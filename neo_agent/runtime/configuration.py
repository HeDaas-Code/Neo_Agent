"""Versioned, secret-aware configuration import and export services."""
from __future__ import annotations

import re
from typing import Any


class ConfigurationService:
    """Validate and transfer Neo Agent v1 configuration documents.

    This is a settings/configuration bundle, not a PyVDisk image snapshot and
    not a transcript/event-log export. PyVDisk remains the persistence API.
    """

    FORMAT = "neo-agent/config/v2"
    COLLECTIONS = (
        "knowledge", "base_knowledge", "relationships", "environments", "domains",
        "channels", "memories", "entities", "emotions", "expressions", "short_term",
        "long_term",
    )
    SECRET_MARKERS = (
        "apikey", "accesstoken", "refreshtoken", "password", "passwd", "secret",
        "credential", "privatekey", "authorization", "bearer", "token",
    )
    TOP_LEVEL_KEYS = frozenset({"format", "character", *COLLECTIONS})
    CATEGORY_LABELS = {
        "knowledge": "知识库",
        "base_knowledge": "基础知识",
        "relationships": "关系档案",
        "environments": "环境",
        "domains": "领域 / 世界",
        "channels": "频道连接",
        "memories": "语义记忆",
        "entities": "实体档案",
        "emotions": "情绪记录",
        "expressions": "表达风格",
        "short_term": "短期记忆",
        "long_term": "长期摘要",
    }

    def __init__(self, store: Any):
        self.store = store

    @classmethod
    def category_labels(cls) -> tuple[tuple[str, str], ...]:
        """Return localized labels paired with stable bundle category names."""
        return tuple((cls.CATEGORY_LABELS[name], name) for name in cls.COLLECTIONS)

    @classmethod
    def contains_secret_key(cls, value: Any) -> bool:
        if isinstance(value, dict):
            for key, nested in value.items():
                normalized = re.sub(r"[^a-z0-9]", "", str(key).casefold())
                if any(marker in normalized for marker in cls.SECRET_MARKERS):
                    return True
                if cls.contains_secret_key(nested):
                    return True
        elif isinstance(value, list):
            return any(cls.contains_secret_key(item) for item in value)
        return False

    @classmethod
    def without_secret_keys(cls, value: Any) -> Any:
        if isinstance(value, dict):
            return {
                key: cls.without_secret_keys(nested)
                for key, nested in value.items()
                if not any(
                    marker in re.sub(r"[^a-z0-9]", "", str(key).casefold())
                    for marker in cls.SECRET_MARKERS
                )
            }
        if isinstance(value, list):
            return [cls.without_secret_keys(item) for item in value]
        return value

    @classmethod
    def _selected_categories(cls, categories: Any = None) -> tuple[str, ...]:
        allowed = ("characters", *cls.COLLECTIONS)
        if categories is None:
            return allowed
        if isinstance(categories, str):
            categories = [categories]
        selected = tuple(dict.fromkeys(categories))
        unknown = set(selected) - set(allowed)
        if unknown:
            raise ValueError(f"未知配置类别：{', '.join(sorted(map(str, unknown)))}")
        if not selected:
            raise ValueError("请至少选择一个配置类别")
        return selected

    def export(self, *, categories: Any = None) -> dict[str, Any]:
        selected = self._selected_categories(categories)
        config = {"format": self.FORMAT}
        if "characters" in selected:
            from neo_agent.runtime.control import SingleRoleService
            rows = self.store.characters(include_archived=False)
            active = SingleRoleService(self.store).active()
            if len(rows) > 1 and active is None:
                raise ValueError("存在多个活动角色；请先选择唯一主角色再导出配置")
            config["character"] = active
        for namespace in self.COLLECTIONS:
            if namespace in selected:
                config[namespace] = self.store.list_documents(namespace)
        return self.without_secret_keys(config)

    def validate(self, config: Any) -> dict[str, Any]:
        if not isinstance(config, dict) or config.get("format") != self.FORMAT:
            raise ValueError(f"仅支持 {self.FORMAT} 新格式")
        unknown = set(config) - self.TOP_LEVEL_KEYS
        if unknown:
            raise ValueError(f"配置包含未知字段：{', '.join(sorted(map(str, unknown)))}")
        if self.contains_secret_key(config):
            raise ValueError("配置导入不得包含密钥字段；请先移除密钥并通过环境变量配置")

        normalized = {"format": self.FORMAT, "character": None, **{ns: [] for ns in self.COLLECTIONS}}
        character = config.get("character")
        if character is not None:
            if not isinstance(character, dict) or not isinstance(character.get("id"), str):
                raise ValueError("character 必须是包含字符串 id 的对象")
            self.store.validate_character_id(character["id"])
            if not str(character.get("name", "")).strip():
                raise ValueError(f"character {character['id']} 的 name 不能为空")
            normalized["character"] = dict(character)

        for namespace in self.COLLECTIONS:
            records = config.get(namespace, [])
            if not isinstance(records, list):
                raise ValueError(f"{namespace} 必须是数组")
            seen_ids: set[str] = set()
            for row in records:
                if not isinstance(row, dict) or not isinstance(row.get("id"), str) or not row["id"].strip():
                    raise ValueError(f"{namespace} 中每条记录都必须包含非空字符串 id")
                self.store.validate_document_id(row["id"], f"{namespace} id")
                if row["id"] in seen_ids:
                    raise ValueError(f"{namespace} 中存在重复 ID：{row['id']}")
                seen_ids.add(row["id"])
                if namespace == "memories":
                    if not isinstance(row.get("text"), str) or not row["text"].strip():
                        raise ValueError(f"memory {row['id']} 必须包含非空字符串 text")
                    self.store.validate_document_id(row.get("character_id", "default"), "memory character_id")
                if namespace == "channels" and not isinstance(row.get("config", {}), dict):
                    raise ValueError(f"channel {row['id']} 的 config 必须是 JSON object")
                normalized[namespace].append(dict(row))
        return normalized

    def preview(self, config: Any, *, categories: Any = None) -> dict[str, Any]:
        validated = self.validate(config)
        selected = self._selected_categories(categories)
        counts = self._counts(validated, selected)
        return {"format": self.FORMAT, "categories": list(selected), "counts": counts, "total": sum(counts.values())}

    @staticmethod
    def _counts(validated: dict[str, Any], selected: tuple[str, ...]) -> dict[str, int]:
        counts: dict[str, int] = {}
        for name in selected:
            count = (1 if validated.get("character") is not None else 0) if name == "characters" else len(validated.get(name, []))
            if count:
                counts[name] = count
        return counts

    def import_config(self, config: Any, *, categories: Any = None) -> dict[str, int]:
        """Validate the complete bundle before applying selected document writes."""
        validated = self.validate(config)
        selected = self._selected_categories(categories)
        if "characters" in selected and validated["character"] is not None:
            from neo_agent.runtime.control import SingleRoleService
            character = validated["character"]
            self.store.save_character(character["id"], character)
            SingleRoleService(self.store).initialize(character["id"])
        for namespace in self.COLLECTIONS:
            if namespace not in selected:
                continue
            for record in validated[namespace]:
                if namespace == "memories":
                    self.store.save_memory(
                        record["id"], record["text"],
                        character_id=record.get("character_id", "default"),
                        metadata=record.get("metadata", {}),
                    )
                else:
                    self.store.save_document(namespace, record["id"], record)
        counts = self._counts(validated, selected)
        self.store.append_event("configuration.imported", {"format": self.FORMAT, "categories": list(selected), "counts": counts})
        return counts
