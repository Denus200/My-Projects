from __future__ import annotations

from dataclasses import dataclass

from overlord.modules.blockers.domain import Blocker
from overlord.modules.cycles.domain import Cycle, Milestone
from overlord.modules.projects.domain import (
    Project,
    ProjectPlan,
    ProjectStage,
    ProjectStageStatus,
)


@dataclass(frozen=True, slots=True)
class ProjectBlockerItem:
    blocker: Blocker
    task_title: str


@dataclass(frozen=True, slots=True)
class ProjectStageProgress:
    """Canonical task-backed progress for one persisted Project Stage."""

    stage: ProjectStage
    eligible_task_count: int
    completed_task_count: int

    @property
    def progress(self) -> float:
        if self.stage.status is ProjectStageStatus.COMPLETED:
            return 1.0
        if not self.eligible_task_count:
            return 0.0
        return min(1.0, self.completed_task_count / self.eligible_task_count)


@dataclass(frozen=True, slots=True)
class ProjectPlanProgress:
    """Reusable whole-Plan and current-Stage progress projection."""

    plan: ProjectPlan
    stage_items: tuple[ProjectStageProgress, ...]

    @property
    def stages(self) -> tuple[ProjectStageProgress, ...]:
        return tuple(
            item
            for item in self.stage_items
            if item.stage.status is not ProjectStageStatus.ARCHIVED
        )

    @property
    def completed_stage_count(self) -> int:
        return sum(
            item.stage.status is ProjectStageStatus.COMPLETED
            for item in self.stages
        )

    @property
    def current_stage_items(self) -> tuple[ProjectStageProgress, ...]:
        return tuple(
            item
            for item in self.stages
            if item.stage.status is ProjectStageStatus.IN_PROGRESS
        )

    @property
    def current_stage(self) -> ProjectStageProgress | None:
        current = self.current_stage_items
        return current[0] if len(current) == 1 else None

    @property
    def has_ambiguous_current_stage(self) -> bool:
        return len(self.current_stage_items) > 1

    @property
    def current_stage_progress(self) -> float | None:
        current = self.current_stage
        return current.progress if current is not None else None

    @property
    def overall_progress(self) -> float:
        stages = self.stages
        if not stages:
            return 0.0
        completed_equivalents = float(self.completed_stage_count)
        current_equivalents = sum(item.progress for item in self.current_stage_items)
        return min(1.0, (completed_equivalents + current_equivalents) / len(stages))


@dataclass(frozen=True, slots=True)
class ProjectDetail:
    project: Project
    eligible_task_count: int
    completed_task_count: int
    open_task_count: int
    in_progress_task_count: int
    blockers: tuple[ProjectBlockerItem, ...]
    current_milestone: Milestone | None
    active_cycle: Cycle | None
    next_action: str | None
    active_plan: ProjectPlan | None = None
    stages: tuple[ProjectStage, ...] = ()
    estimated_minutes: int = 0
    plan_progress: ProjectPlanProgress | None = None
    next_action_task_id: int | None = None
    linked_cycle: Cycle | None = None
    current_milestone_cycle_id: int | None = None

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


@dataclass(frozen=True, slots=True)
class ProjectNote:
    id: int
    project_id: int
    title: str
    relative_path: str
    content: str = ""


@dataclass(frozen=True, slots=True)
class ProjectFile:
    id: int
    project_id: int
    display_name: str
    relative_path: str
    size_bytes: int


@dataclass(frozen=True, slots=True)
class ProjectWorkspace:
    notes: tuple[ProjectNote, ...]
    files: tuple[ProjectFile, ...]
