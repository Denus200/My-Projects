from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time
from enum import StrEnum


class TaskLifecycle(StrEnum):
    BACKLOG = "backlog"
    PLANNED = "planned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class TaskBoardColumn(StrEnum):
    PLANNED = "planned"
    IN_PROGRESS = "in_progress"
    MISSED = "missed"
    COMPLETED = "completed"
    ARCHIVE = "archive"


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
    schedule_start_date: date | None = None
    schedule_start_time: time | None = None
    schedule_end_date: date | None = None
    schedule_end_time: time | None = None
    deadline_at: datetime | None = None
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


def validate_schedule(
    start_date: date | None,
    start_time: time | None,
    end_date: date | None,
    end_time: time | None,
    deadline_at: datetime | None,
) -> None:
    if start_time is not None and start_date is None:
        raise ValueError("A start time requires a start date.")
    if end_date is not None and start_date is None:
        raise ValueError("An end date requires a start date.")
    if end_time is not None and end_date is None:
        raise ValueError("An end time requires an end date.")
    if deadline_at is not None and start_date is None:
        raise ValueError("A deadline requires a start date.")
    if start_date is not None and end_date is not None:
        if end_date < start_date:
            raise ValueError("The end date cannot be before the start date.")
        if end_date == start_date and start_time is not None and end_time is not None and end_time < start_time:
            raise ValueError("The end time cannot be before the start time.")
    if start_date is not None and deadline_at is not None:
        start_at = datetime.combine(start_date, start_time or time.min)
        if deadline_at < start_at:
            raise ValueError("The deadline cannot be before the task starts.")


def is_scheduled_for_day(task: Task, day: date) -> bool:
    if task.schedule_start_date is None:
        return False
    if task.schedule_end_date is not None:
        return task.schedule_start_date <= day <= task.schedule_end_date
    return task.schedule_start_date == day


def board_column(task: Task, now: datetime | None = None) -> TaskBoardColumn:
    reference = now or datetime.now()
    if task.lifecycle_status is TaskLifecycle.COMPLETED:
        return TaskBoardColumn.COMPLETED
    if task.lifecycle_status is TaskLifecycle.CANCELLED or task.archived_at is not None:
        return TaskBoardColumn.ARCHIVE
    if task.deadline_at is not None and reference > task.deadline_at:
        return TaskBoardColumn.MISSED
    if task.schedule_end_date is not None:
        end_at = datetime.combine(task.schedule_end_date, task.schedule_end_time or time.max)
        if reference > end_at:
            return TaskBoardColumn.MISSED
    if is_scheduled_for_day(task, reference.date()):
        return TaskBoardColumn.IN_PROGRESS
    if (
        task.schedule_start_date is not None
        and task.schedule_end_date is None
        and task.deadline_at is None
        and reference.date() > task.schedule_start_date
    ):
        return TaskBoardColumn.ARCHIVE
    return TaskBoardColumn.PLANNED
