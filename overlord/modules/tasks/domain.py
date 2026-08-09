from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class TaskLifecycle(StrEnum):
    BACKLOG = "backlog"
    PLANNED = "planned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


@dataclass(frozen=True, slots=True)
class Task:
    id: int
    project_id: int | None
    title: str
    lifecycle_status: TaskLifecycle | None
    created_at: datetime
    updated_at: datetime
    legacy_status: str | None = None
    description: str | None = None
    milestone_id: int | None = None
    definition_of_done: str | None = None
    next_action: str | None = None
    importance: bool | None = None
    urgency: bool | None = None
    estimate_minutes: int | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    archived_at: datetime | None = None


def require_task_title(title: str) -> str:
    clean = title.strip()
    if not clean:
        raise ValueError("Task title is required.")
    return clean


def validate_estimate(minutes: int | None) -> int | None:
    if minutes is not None and minutes <= 0:
        raise ValueError("Estimate must be a positive number of minutes.")
    return minutes
