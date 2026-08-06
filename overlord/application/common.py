from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import ContextManager, Protocol

from overlord.domain.cycles import Cycle, CycleStatus, Milestone, WeeklyOutcome
from overlord.domain.planning import TaskPlan
from overlord.domain.projects import Project, ProjectStatus
from overlord.domain.tasks import Blocker, BlockerType, Task, TaskLifecycle, TodayGroup


@dataclass(frozen=True, slots=True)
class SettingsData:
    theme_mode: str = "system"
    motion_enabled: bool = True
    reduced_motion: bool = False
    first_day_of_week: str = "monday"
    default_cycle_length: int = 12
    startup_destination: str = "dashboard"
    sidebar_collapsed: bool = False
    updated_at: datetime | None = None

    @property
    def effective_motion(self) -> bool:
        return self.motion_enabled and not self.reduced_motion


@dataclass(frozen=True, slots=True)
class TaskListItem:
    task: Task
    project_title: str
    current_plan: TaskPlan | None
    open_blockers: int = 0
    carry_over_count: int = 0


@dataclass(frozen=True, slots=True)
class ProjectDetail:
    project: Project
    task_count: int
    completed_task_count: int
    open_blocker_count: int
    next_action: str | None


@dataclass(frozen=True, slots=True)
class StatusHistoryEntry:
    from_status: str | None
    to_status: str
    reason: str | None
    changed_at: datetime


@dataclass(frozen=True, slots=True)
class TaskEditorData:
    task: Task
    blockers: tuple[Blocker, ...]
    planning_history: tuple[TaskPlan, ...]
    status_history: tuple[StatusHistoryEntry, ...]


@dataclass(frozen=True, slots=True)
class CycleDetail:
    cycle: Cycle
    projects: tuple[Project, ...]
    milestones: tuple[Milestone, ...]
    tasks: tuple[TaskListItem, ...]
    weekly_outcomes: tuple[WeeklyOutcome, ...]


class ProjectRepositoryPort(Protocol):
    def create(self, title: str, description: str = "", status: ProjectStatus = ProjectStatus.ACTIVE) -> Project: ...
    def get(self, project_id: int) -> Project | None: ...
    def list(self, status: ProjectStatus | None = None, search: str = "") -> list[Project]: ...
    def detail(self, project_id: int) -> ProjectDetail | None: ...
    def update(self, project_id: int, **changes: object) -> Project: ...


class TaskRepositoryPort(Protocol):
    def create(self, project_id: int, title: str, lifecycle: TaskLifecycle, **fields: object) -> Task: ...
    def get(self, task_id: int) -> Task | None: ...
    def list(self, **filters: object) -> list[TaskListItem]: ...
    def update(self, task_id: int, **changes: object) -> Task: ...
    def change_lifecycle(self, task_id: int, lifecycle: TaskLifecycle, reason: str | None = None) -> Task: ...
    def current_plan(self, task_id: int) -> TaskPlan | None: ...
    def assign_plan(self, task_id: int, planned_date: date, group: TodayGroup | None, position: int | None, planned_week_start: date | None = None) -> TaskPlan: ...
    def open_blocker(self, task_id: int, blocker_type: BlockerType, description: str) -> Blocker: ...
    def resolve_blocker(self, blocker_id: int, resolution: str) -> Blocker: ...
    def list_blockers(self, task_id: int, open_only: bool = False) -> list[Blocker]: ...
    def plan_history(self, task_id: int) -> list[TaskPlan]: ...
    def status_history(self, task_id: int) -> list[StatusHistoryEntry]: ...
    def weekly_counts(self, start: date) -> list[tuple[date, int, int]]: ...
    def execution_counts(self, start: date) -> tuple[int, int]: ...


class SettingsRepositoryPort(Protocol):
    def get(self) -> SettingsData: ...
    def update(self, **changes: object) -> SettingsData: ...


class CycleRepositoryPort(Protocol):
    def create(self, title: str, main_outcome: str, start_date: date, length_weeks: int) -> Cycle: ...
    def get(self, cycle_id: int) -> Cycle | None: ...
    def list(self, status: CycleStatus | None = None, search: str = "") -> list[Cycle]: ...
    def detail(self, cycle_id: int) -> CycleDetail | None: ...
    def active(self) -> CycleDetail | None: ...
    def change_status(self, cycle_id: int, status: CycleStatus) -> Cycle: ...
    def connect_project(self, cycle_id: int, project_id: int) -> None: ...
    def connect_task(self, cycle_id: int, task_id: int) -> None: ...
    def create_milestone(self, cycle_id: int, project_id: int, title: str, definition_of_done: str) -> Milestone: ...
    def set_weekly_outcome(self, cycle_id: int, week_number: int, title: str, definition_of_done: str, status: str) -> WeeklyOutcome: ...


class UnitOfWork(Protocol):
    projects: ProjectRepositoryPort
    tasks: TaskRepositoryPort
    settings: SettingsRepositoryPort
    cycles: CycleRepositoryPort


class UnitOfWorkFactory(Protocol):
    def __call__(self, *, read_only: bool = False) -> ContextManager[UnitOfWork]: ...
