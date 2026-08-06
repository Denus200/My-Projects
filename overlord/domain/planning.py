from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime

from .tasks import TodayGroup


@dataclass(frozen=True, slots=True)
class TaskPlan:
    id: int
    task_id: int
    planned_date: date
    planned_week_start: date
    today_group: TodayGroup | None
    position: int | None
    supersedes_plan_id: int | None
    created_at: datetime
    ended_at: datetime | None = None


def execution_score(originally_planned: int, completed: int) -> float | None:
    if originally_planned <= 0:
        return None
    return min(1.0, max(0.0, completed / originally_planned))
