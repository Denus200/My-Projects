from __future__ import annotations

from dataclasses import dataclass

from overlord.modules.tasks.domain import Task


@dataclass(frozen=True, slots=True)
class TaskListItem:
    task: Task
    project_title: str | None
    open_blockers: int = 0
    cycle_titles: tuple[str, ...] = ()
