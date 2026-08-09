from __future__ import annotations

from dataclasses import dataclass

from overlord.modules.blockers.domain import Blocker
from overlord.modules.cycles.domain import Cycle, Milestone
from overlord.modules.projects.domain import Project


@dataclass(frozen=True, slots=True)
class ProjectBlockerItem:
    blocker: Blocker
    task_title: str


@dataclass(frozen=True, slots=True)
class ProjectDetail:
    project: Project
    eligible_task_count: int
    completed_task_count: int
    open_task_count: int
    blockers: tuple[ProjectBlockerItem, ...]
    current_milestone: Milestone | None
    active_cycle: Cycle | None
    next_action: str | None

    @property
    def task_count(self) -> int:
        """Compatibility name for eligible Tasks used by honest progress."""
        return self.eligible_task_count

    @property
    def open_blocker_count(self) -> int:
        return len(self.blockers)

    @property
    def progress(self) -> float | None:
        if not self.eligible_task_count:
            return None
        return self.completed_task_count / self.eligible_task_count
