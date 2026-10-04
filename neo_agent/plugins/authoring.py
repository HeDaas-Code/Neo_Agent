"""Agent-owned, schema-bounded domain authoring tools backed by PyVDisk."""
from __future__ import annotations

import hashlib
import re
from typing import Any

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

from neo_agent.nps import FORMAT, NPSManager
from neo_agent.plugins.base import PluginContext, PluginManifest


class DocumentArgs(BaseModel):
    document_id: str = Field(description="Stable identifier using letters, digits, '_' or '-' (max 22)")
    title: str = Field(description="Short human-readable title")
    content: str = Field(description="Concise content based on explicit conversation facts")
    tags: list[str] = Field(default_factory=list, description="Optional topic tags")


class RelationshipArgs(BaseModel):
    relationship_id: str = Field(description="Stable user/character relationship identifier")
    person: str = Field(description="Person represented by this relationship")
    context: str = Field(default="", description="Neutral context; do not assign an inferred score")


class EventArgs(BaseModel):
    event_id: str = Field(description="Stable event identifier")
    title: str = Field(description="Event title")
    description: str = Field(default="", description="Event context")
    due_at: str = Field(default="", description="Optional timezone-aware ISO-8601 time")


class TaskWorkflowArgs(BaseModel):
    title: str = Field(description="明确请求执行的任务标题")
    description: str = Field(description="期望完成的具体任务")
    requirements: str = Field(default="", description="可选约束")
    completion_criteria: str = Field(default="", description="可验证的完成标准")


class NPSArgs(BaseModel):
    plugin_id: str = Field(description="Dotted identifier such as personal.reminder")
    name: str = Field(description="Plugin display name")
    description: str = Field(description="What the script does")
    vscript: str = Field(description="VScript source for a main(args) controller")
    parameters_json: str = Field(default='{"type":"object","properties":{}}', description="Supported JSON Schema parameter object")


class AgentAuthoringPlugin:
    """Expose only explicit domain APIs; never allow arbitrary path/namespace writes."""

    manifest = PluginManifest(
        plugin_id="core.agent-authoring", name="Agent 自动创作", version="1.0.0",
        description="通过类型化领域接口创建知识、关系基线、事件、环境、领域、工作流及安全 VScript 插件。",
        capabilities=("knowledge.create", "relationships.initialize", "events.create", "environments.create", "domains.create", "workflows.create", "workflows.execute", "nps.create"),
    )

    TOOL_CAPABILITIES = {
        "create_knowledge_entry": ("knowledge.create",),
        "create_environment": ("environments.create",),
        "create_domain": ("domains.create",),
        "create_workflow": ("workflows.create",),
        "start_task_workflow": ("workflows.execute",),
        "initialize_relationship": ("relationships.initialize",),
        "create_event_record": ("events.create",),
        "create_vscript_plugin": ("nps.create",),
    }

    @staticmethod
    def _id(value: str) -> str:
        value = re.sub(r"[^A-Za-z0-9_-]+", "-", value.strip()).strip("-_")[:22]
        if not value:
            raise ValueError("生成的对象 ID 不能为空")
        return value

    @staticmethod
    def _document(context: PluginContext, namespace: str, document_id: str, title: str, content: str, tags: list[str]) -> dict[str, Any]:
        document_id = AgentAuthoringPlugin._id(document_id)
        if not title.strip() or not content.strip():
            raise ValueError("标题与内容不能为空")
        existing = context.store.get_document(namespace, document_id)
        if existing:
            # Idempotent same-fact registration; never silently overwrite authored data.
            if existing.get("title") == title.strip() and existing.get("content") == content.strip():
                return {"id": document_id, "status": "already_exists", "summary": f"{title.strip()} 已登记"}
            raise ValueError(f"{namespace} 中已存在不同内容的同 ID 对象，拒绝覆盖")
        record = context.store.save_document(namespace, document_id, {
            "title": title.strip(), "content": content.strip(), "tags": list(dict.fromkeys(str(tag)[:60] for tag in tags))[:20],
            "created_by": "agent", "status": "active",
        })
        return {"id": record["id"], "status": "created", "summary": f"已创建：{title.strip()}"}

    def load_tools(self, context: PluginContext):
        def knowledge(document_id: str, title: str, content: str, tags: list[str] | None = None):
            return self._document(context, "knowledge", document_id, title, content, tags or [])

        def environment(document_id: str, title: str, content: str, tags: list[str] | None = None):
            return self._document(context, "environments", document_id, title, content, tags or [])

        def domain(document_id: str, title: str, content: str, tags: list[str] | None = None):
            return self._document(context, "domains", document_id, title, content, tags or [])

        def workflow(document_id: str, title: str, content: str, tags: list[str] | None = None):
            return self._document(context, "workflows", document_id, title, content, tags or [])

        def start_task_workflow(title: str, description: str, requirements: str = "",
                                completion_criteria: str = ""):
            # Executing a task is distinct from merely registering a reusable
            # workflow description. The tool is available only when the Agent
            # authoring manifest declares workflows.execute.
            from neo_agent.services.collaboration import MultiAgentCoordinator
            from neo_agent.runtime.control import SingleRoleService
            character = SingleRoleService(context.store).active()
            character_context = ({
                "id": character.get("id"), "name": character.get("name"),
                "personality": character.get("personality", ""),
                "background": character.get("background", ""),
            } if character else {})
            result = MultiAgentCoordinator(context.store, model=context.model).run_task(
                title=title, description=description, requirements=requirements,
                completion_criteria=completion_criteria, character_context=character_context,
            )
            status = str(result.get("status", "running"))
            summary = "任务编排已启动。" if status == "running" else (
                "任务已完成。" if status == "completed" else "任务已创建并等待补充信息。"
            )
            return {"id": result["id"], "status": status, "summary": summary}

        def relationship(relationship_id: str, person: str, context_note: str = ""):
            rid = self._id(relationship_id)
            existing = context.store.get_document("relationships", rid)
            if existing:
                return {"id": rid, "status": "already_exists", "summary": "关系档案已存在，未修改持久关系状态"}
            row = context.store.save_document("relationships", rid, {
                "person": person.strip(), "context": context_note.strip(), "score": 0,
                "stage": "初识", "impression": "", "interactions": [], "created_by": "agent",
            })
            return {"id": row["id"], "status": "created", "summary": f"已建立 {person.strip()} 的中性关系档案"}

        def event(event_id: str, title: str, description: str = "", due_at: str = ""):
            eid = self._id(event_id)
            existing = context.store.get_document("event_records", eid)
            if existing:
                raise ValueError("事件 ID 已存在，拒绝覆盖")
            payload = {"title": title.strip(), "description": description.strip(), "status": "pending", "created_by": "agent"}
            if due_at:
                payload["due_at"] = due_at
            row = context.store.create_event_record(eid, payload)
            return {"id": row["id"], "status": "created", "summary": f"已登记事件：{title.strip()}"}

        def nps(plugin_id: str, name: str, description: str, vscript: str, parameters_json: str = '{"type":"object","properties":{}}'):
            try:
                import json
                parameters = json.loads(parameters_json)
            except (ValueError, TypeError) as exc:
                raise ValueError("parameters_json 必须是有效 JSON") from exc
            bundle = {"format": FORMAT, "manifest": {
                "id": plugin_id.strip(), "name": name.strip(), "version": "1.0.0",
                "description": description.strip(), "entrypoint": "main", "capabilities": [],
                "parameters": parameters,
            }, "vscript": vscript, "python": ""}
            validated = NPSManager.validate_bundle(bundle)
            saved = NPSManager(context.store).save(validated, enabled=False)
            return {"id": saved["manifest"]["id"], "status": "created_disabled", "summary": f"VScript 插件 {name.strip()} 已校验并登记；默认未启用"}

        schemas = [
            ("create_knowledge_entry", "根据对话中的明确事实创建知识条目；冲突内容不得覆盖。", knowledge, DocumentArgs, "knowledge.create"),
            ("create_environment", "创建描述地点/环境的结构化环境档案。", environment, DocumentArgs, "environments.create"),
            ("create_domain", "创建虚拟世界或主题领域档案。", domain, DocumentArgs, "domains.create"),
            ("create_workflow", "将用户明确提出的重复流程登记为工作流说明，不会擅自启动任务。", workflow, DocumentArgs, "workflows.create"),
            ("start_task_workflow", "仅在用户明确要求执行具体任务时启动持久化多步骤任务编排；任务工作区限制于 PyVDisk VFS，缺少信息时会转为待澄清状态。", start_task_workflow, TaskWorkflowArgs, "workflows.execute"),
            ("initialize_relationship", "仅建立中性关系档案，不推断或修改关系分数；持久变化需经过多轮证据门槛。", relationship, RelationshipArgs, "relationships.initialize"),
            ("create_event_record", "按明确用户意图登记事件；不执行外部发送。", event, EventArgs, "events.create"),
            ("create_vscript_plugin", "创建仅含经过编译校验的 VScript NPS；Agent 不得附带 Python 扩展，插件默认停用。", nps, NPSArgs, "nps.create"),
        ]
        return [StructuredTool.from_function(name=name, description=description, func=func, args_schema=schema)
                for name, description, func, schema, _capability in schemas]
