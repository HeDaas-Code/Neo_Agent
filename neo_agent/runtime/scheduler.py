"""Durable schedule reminder worker."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Callable


class ScheduleWorker:
    """Claims persisted reminder jobs, records due notifications and retries failures."""

    def __init__(self, store, notifier: Callable[[dict], None] | None = None):
        self.store = store
        self.notifier = notifier

    def run_once(self, *, now: datetime | None = None, limit: int = 32) -> list[dict]:
        moment = now or datetime.now(timezone.utc)
        completed = []

        # Schedules are durable records in PyVDisk FS. Materialize queue work
        # only when due, so a far-future FIFO item cannot block other reminders.
        for schedule in self.store.schedules():
            if schedule.get("status") != "pending":
                continue
            due = datetime.fromisoformat(schedule["due_at"].replace("Z", "+00:00"))
            if due > moment:
                continue
            schedule_id = schedule["id"]
            revision = int(schedule.get("queue_revision", 1))
            same_revision = [
                task for task in self.store.schedule_queue.list()
                if (task.payload or {}).get("schedule_id") == schedule_id
                and (task.payload or {}).get("revision", 1) == revision
            ]
            # A failed task is deliberately observable and requires explicit
            # retry; do not silently create a second delivery attempt.
            if not same_revision:
                self.store.schedule_queue.enqueue(
                    {"kind": "schedule.reminder", "schedule_id": schedule_id,
                     "due_at": schedule["due_at"], "revision": revision},
                    idempotency_key=f"schedule:{schedule_id}:{revision}",
                )

        for _ in range(max(1, limit)):
            task = self.store.schedule_queue.claim()
            if task is None:
                break
            payload = task.payload or {}
            schedule_id = payload.get("schedule_id")
            try:
                schedule = self.store.get_schedule(schedule_id) if schedule_id else None
                if not schedule:
                    self.store.schedule_queue.fail(task.id, "schedule record missing", retry=False, lease_id=task.lease_id)
                    continue
                if payload.get("revision", 1) != schedule.get("queue_revision", 1):
                    self.store.schedule_queue.complete(task.id, {"skipped": True, "reason": "superseded"}, lease_id=task.lease_id)
                    continue
                due = datetime.fromisoformat(schedule["due_at"].replace("Z", "+00:00"))
                if due > moment:
                    # Defensive guard for queue records created by an earlier
                    # runtime version; new future reminders are not enqueued.
                    self.store.schedule_queue.fail(task.id, "not due yet", retry=True, lease_id=task.lease_id)
                    continue
                if schedule.get("status") != "pending":
                    self.store.schedule_queue.complete(task.id, {"skipped": True}, lease_id=task.lease_id)
                    continue
                if self.notifier is None:
                    import hashlib
                    workflow_id = hashlib.sha256(f"schedule:{schedule_id}:{revision}".encode()).hexdigest()[:20]
                    self.store.save_document("workflows", workflow_id, {
                        "kind": "schedule.reminder", "schedule_id": schedule_id,
                        "title": schedule["title"], "due_at": schedule["due_at"],
                        "status": "awaiting_delivery", "delivery_adapter": None,
                    })
                    self.store.update_schedule(schedule_id, {
                        "status": "awaiting_delivery", "staged_at": moment.isoformat(),
                    })
                    self.store.append_event("schedule.reminder.staged", {"schedule_id": schedule_id, "workflow_id": workflow_id})
                    if schedule.get("type") == "recurring":
                        self.store.advance_recurring_schedule(schedule_id, occurred_at=moment.isoformat())
                    self.store.schedule_queue.complete(task.id, {"schedule_id": schedule_id, "staged": True}, lease_id=task.lease_id)
                else:
                    self.notifier(schedule)
                    self.store.update_schedule(schedule_id, {"status": "notified", "notified_at": moment.isoformat()})
                    self.store.append_event("schedule.reminder.delivered", {"schedule_id": schedule_id})
                    if schedule.get("type") == "recurring":
                        self.store.advance_recurring_schedule(schedule_id, occurred_at=moment.isoformat())
                    self.store.schedule_queue.complete(task.id, {"schedule_id": schedule_id, "notified": True}, lease_id=task.lease_id)
                completed.append(schedule_id)
            except Exception as exc:
                self.store.schedule_queue.fail(task.id, {"type": type(exc).__name__, "message": str(exc)}, retry=True, lease_id=task.lease_id)
                self.store.append_event("schedule.reminder.failed", {"schedule_id": schedule_id, "error": str(exc)})
        return completed
