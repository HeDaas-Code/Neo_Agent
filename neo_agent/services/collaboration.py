"""Durable, LangChain-native multi-agent task coordination."""
from __future__ import annotations

import json
import re
import uuid
from datetime import datetime, timezone
from typing import Any, Callable

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from neo_agent.services.scheduling import InterruptQuestionService


class TaskUnderstanding(BaseModel):
    summary: str = Field(description="Concise objective and expected outcome")
    requirements: list[str] = Field(default_factory=list)


class PlannedStep(BaseModel):
    description: str
    agent_role: str = Field(default="执行专家", description="Specialist role for this step")


class ExecutionPlan(BaseModel):
    steps: list[PlannedStep] = Field(min_length=1, max_length=5)


class StepResult(BaseModel):
    output: str
    needs_user_input: bool = False
    question: str = ""


class TaskVerification(BaseModel):
    completed: bool
    reason: str


class MultiAgentCoordinator:
    """Analyze, plan, execute, verify and durably resume one task workflow.

    All persistence goes through DiskStore's PyVDisk document/event API. Human
    questions pause the workflow rather than blocking a UI callback/thread.
    """

    def __init__(self, store, model: Any | None = None, progress_callback: Callable[[str], None] | None = None):
        self.store = store
        if model is None:
            from neo_agent.runtime.agent import AgentRuntime
            model = AgentRuntime._build_model()
        self.model = model
        self.progress_callback = progress_callback
        self.questions = InterruptQuestionService(store)

    def run_task(self, *, title: str, description: str, requirements: str = "",
                 completion_criteria: str = "", character_context: dict[str, Any] | None = None,
                 task_id: str | None = None) -> dict[str, Any]:
        title = str(title).strip()
        description = str(description).strip()
        if not title or not description:
            raise ValueError("task title and description are required")
        run_id = task_id or uuid.uuid4().hex[:20]
        if self.store.get_document("workflows", run_id):
            raise ValueError(f"workflow already exists: {run_id}")
        if self.store.get_document("event_records", run_id):
            raise ValueError(f"event record already uses workflow id: {run_id}")
        workspace = self.store.task_workspace(run_id)
        workflow = {
            "id": run_id, "kind": "multi_agent_task", "status": "running",
            "workspace": workspace.root,
            "task": {"title": title, "description": description, "requirements": requirements,
                     "completion_criteria": completion_criteria},
            "character_context": character_context or {}, "plan": [], "results": [],
            "next_step": 0, "created_at": datetime.now(timezone.utc).isoformat(),
            "progress": [],
        }
        self._save(workflow, "workflow.started")
        try:
            understanding = self._invoke_structured(
                TaskUnderstanding, "任务分析专家", "理解任务目标、约束与可验证成果。",
                {"task": workflow["task"], "character_context": workflow["character_context"]},
            )
            workflow["understanding"] = understanding.model_dump()
            self._progress(workflow, "任务已分析，正在制定执行计划")
            plan = self._invoke_structured(
                ExecutionPlan, "任务规划专家", "将任务分解为有序、可执行、最多五步的计划；每步指定最合适的专家角色。",
                {"task": workflow["task"], "understanding": workflow["understanding"]},
            )
            workflow["plan"] = [step.model_dump() for step in plan.steps]
            return self._continue(workflow)
        except Exception as exc:
            workflow.update(status="failed", error={"type": type(exc).__name__, "message": str(exc)[:1000]})
            self._save(workflow, "workflow.failed")
            raise

    def resume(self, run_id: str) -> dict[str, Any]:
        workflow = self.store.get_document("workflows", run_id)
        if not workflow or workflow.get("kind") != "multi_agent_task":
            raise KeyError(run_id)
        if workflow.get("status") != "awaiting_user":
            raise ValueError(f"workflow is not awaiting a user answer: {workflow.get('status')}")
        question = self.store.get_document("question_requests", workflow["question_id"])
        if not question or question.get("status") != "answered":
            raise ValueError("workflow cannot resume before its question is answered")
        index = workflow["next_step"]
        step = workflow["plan"][index]
        workflow["results"].append({"step": step["description"], "agent_role": step["agent_role"],
                                    "output": "", "user_answer": question["answer"], "status": "answered"})
        workflow["next_step"] = index + 1
        workflow.pop("question_id", None)
        workflow["status"] = "running"
        self._progress(workflow, "已收到用户回答，继续后续步骤")
        return self._continue(workflow)

    def runs(self) -> list[dict[str, Any]]:
        return [item for item in self.store.list_documents("workflows") if item.get("kind") == "multi_agent_task"]

    def _continue(self, workflow: dict[str, Any]) -> dict[str, Any]:
        try:
            while workflow["next_step"] < len(workflow["plan"]):
                index = workflow["next_step"]
                step = workflow["plan"][index]
                result = self._invoke_structured(
                    StepResult, step["agent_role"], f"完成协作任务中的指定步骤。你的输出应可交给后续步骤使用。若缺少必要信息，应设置 needs_user_input=true 并只提出一个清晰问题。",
                    {"task": workflow["task"], "step": step, "character_context": workflow["character_context"],
                     "previous_results": workflow["results"]},
                )
                if result.needs_user_input:
                    question = self.questions.ask(result.question or result.output, context=step["description"], conversation_id=workflow["id"])
                    workflow.update(status="awaiting_user", question_id=question["id"])
                    workflow["results"].append({"step": step["description"], "agent_role": step["agent_role"],
                                                "output": result.output, "status": "awaiting_user"})
                    self._progress(workflow, "任务暂停，等待用户补充信息")
                    return workflow
                workflow["results"].append({"step": step["description"], "agent_role": step["agent_role"],
                                            "output": result.output, "status": "completed"})
                workflow["next_step"] = index + 1
                self._progress(workflow, f"步骤 {index + 1}/{len(workflow['plan'])} 已完成")

            verification = self._invoke_structured(
                TaskVerification, "任务验证专家", "依据任务要求和完成标准验证任务结果。不得把缺少证据判定为完成。",
                {"task": workflow["task"], "understanding": workflow.get("understanding"),
                 "results": workflow["results"]},
            )
            workflow["verification"] = verification.model_dump()
            workflow["status"] = "completed" if verification.completed else "needs_review"
            self._save(workflow, "workflow.completed" if verification.completed else "workflow.needs_review")
            return workflow
        except Exception as exc:
            workflow.update(status="failed", error={"type": type(exc).__name__, "message": str(exc)[:1000]})
            self._save(workflow, "workflow.failed")
            raise

    def _invoke_structured(self, schema: type[BaseModel], role: str, instruction: str, payload: dict[str, Any]):
        system = SystemMessage(content=f"你是{role}。{instruction} 请严格给出符合 schema 的结果。")
        user = HumanMessage(content=json.dumps(payload, ensure_ascii=False, default=str))
        structured = getattr(self.model, "with_structured_output", None)
        if structured:
            value = structured(schema).invoke([system, user])
            return value if isinstance(value, schema) else schema.model_validate(value)
        response = self.model.invoke([system, user])
        content = getattr(response, "content", response)
        if isinstance(content, dict):
            data = content
        else:
            text = str(content).strip()
            match = re.search(r"\{.*\}", text, re.S)
            if not match:
                raise ValueError(f"{role} did not return structured JSON")
            data = json.loads(match.group(0))
        return schema.model_validate(data)

    def _progress(self, workflow: dict[str, Any], message: str) -> None:
        progress = {"at": datetime.now(timezone.utc).isoformat(), "message": message}
        workflow["progress"].append(progress)
        self._save(workflow, "workflow.progress")
        if self.progress_callback:
            self.progress_callback(message)

    def _save(self, workflow: dict[str, Any], event_type: str) -> None:
        self.store.save_document("workflows", workflow["id"], workflow)
        self._sync_event_record(workflow)
        self.store.append_event(event_type, {"workflow_id": workflow["id"], "status": workflow["status"],
                                             "next_step": workflow["next_step"]})

    def _sync_event_record(self, workflow: dict[str, Any]) -> None:
        """Keep the operator-facing event projection aligned with workflow state.

        The workflow document is the source of truth; this projection gives the
        global event console a stable, searchable lifecycle entry without
        duplicating execution state or introducing another persistence path.
        """
        status_map = {
            "running": "triggered",
            "awaiting_user": "awaiting_user",
            "needs_review": "needs_review",
            "completed": "completed",
            "failed": "failed",
            "cancelled": "cancelled",
        }
        status = status_map.get(workflow.get("status"), "pending")
        task = workflow.get("task", {})
        changes = {
            "type": "collaboration.task",
            "title": task.get("title", "协作任务"),
            "description": task.get("description", ""),
            "workflow_id": workflow["id"],
            "status": status,
            "workflow_status": workflow.get("status"),
            "next_step": workflow.get("next_step", 0),
            "step_count": len(workflow.get("plan", [])),
            "question_id": workflow.get("question_id"),
            "error": workflow.get("error"),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        if self.store.get_document("event_records", workflow["id"]):
            self.store.update_event_record(workflow["id"], changes)
        else:
            self.store.create_event_record(workflow["id"], {
                **changes,
                "created_at": workflow.get("created_at"),
            })
