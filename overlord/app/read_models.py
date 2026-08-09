from __future__ import annotations

from dataclasses import dataclass

from overlord.modules.planning.domain import TaskPlan
from overlord.modules.tasks.domain import Task


@dataclass(frozen=True, slots=True)
class TaskListItem:
    task: Task
    project_title: str | None
    current_plan: TaskPlan | None
    open_blockers: int = 0
    carry_over_count: int = 0
