from __future__ import annotations

from dataclasses import dataclass

from overlord.modules.tasks.domain import Task


@dataclass(frozen=True, slots=True)
class TaskProjectContext:
    project_id: int
    project_title: str
    project_color: str
    stage_id: int | None = None
    stage_title: str | None = None


@dataclass(frozen=True, slots=True)
class TaskListItem:
    task: Task
    project_title: str | None
    open_blockers: int = 0
    cycle_titles: tuple[str, ...] = ()
    project_contexts: tuple[TaskProjectContext, ...] = ()

    @property
    def project_colors(self) -> tuple[str, ...]:
        return tuple(context.project_color for context in self.project_contexts)

    @property
    def project_titles(self) -> tuple[str, ...]:
        return tuple(context.project_title for context in self.project_contexts)
