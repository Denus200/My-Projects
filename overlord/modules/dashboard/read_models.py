from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from overlord.app.read_models import TaskListItem


@dataclass(frozen=True, slots=True)
class WeeklyBar:
    day: date
    planned: int
    completed: int


@dataclass(frozen=True, slots=True)
class AttentionItem:
    task_id: int
    title: str
    project_title: str | None
    reasons: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class CurrentCycleReadModel:
    cycle_id: int
    title: str
    main_outcome: str
    week_number: int
    length_weeks: int
    next_milestone: str | None
    progress: float
    weekly_outcome: str
    days_remaining: int


@dataclass(frozen=True, slots=True)
class DashboardReadModel:
    day: date
    yesterday_tasks: tuple[TaskListItem, ...]
    today_tasks: tuple[TaskListItem, ...]
    tomorrow_tasks: tuple[TaskListItem, ...]
    weekly_bars: tuple[WeeklyBar, ...]
    execution_score: float | None
    current_cycle: CurrentCycleReadModel | None
    attention: tuple[AttentionItem, ...]
    actual_time_label: str = "Not tracked yet"
    outcome_label: str = "Not set"


def execution_score(originally_planned: int, completed: int) -> float | None:
    if originally_planned <= 0:
        return None
    return min(1.0, max(0.0, completed / originally_planned))
