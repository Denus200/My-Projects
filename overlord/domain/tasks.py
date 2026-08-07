from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from enum import StrEnum


class TaskLifecycle(StrEnum):
    BACKLOG = "backlog"
    PLANNED = "planned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class TodayGroup(StrEnum):
    PRIMARY = "primary"
    SECONDARY = "secondary"


class BlockerType(StrEnum):
    DEPENDENCY = "dependency"
    DECISION = "decision"
    RESOURCE = "resource"
    CLARITY = "clarity"
    TECHNICAL = "technical"
    OTHER = "other"


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


@dataclass(frozen=True, slots=True)
class Blocker:
    id: int
    task_id: int
    type: BlockerType
    description: str
    created_at: datetime
    resolved_at: datetime | None = None
    resolution: str | None = None


def require_task_title(title: str) -> str:
    clean = title.strip()
    if not clean:
        raise ValueError("Task title is required.")
    return clean


def validate_estimate(minutes: int | None) -> int | None:
    if minutes is not None and minutes <= 0:
        raise ValueError("Estimate must be a positive number of minutes.")
    return minutes


def require_definition_of_done(value: str | None, *, context: str) -> str:
    clean = (value or "").strip()
    if not clean:
        raise ValueError(f"Definition of Done is required before {context}.")
    return clean


def validate_slot(group: TodayGroup | None, position: int | None) -> None:
    if (group is None) != (position is None):
        raise ValueError("Today group and position must be provided together.")
    if group is TodayGroup.PRIMARY and position not in range(1, 4):
        raise ValueError("Primary position must be from 1 to 3.")
    if group is TodayGroup.SECONDARY and position not in range(1, 5):
        raise ValueError("Secondary position must be from 1 to 4.")


def week_start(value: date, first_day: int = 0) -> date:
    return value.fromordinal(value.toordinal() - ((value.weekday() - first_day) % 7))
