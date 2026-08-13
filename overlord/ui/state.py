from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class TaskFilterState:
    search: str = ""
    project: str = "all"
    lifecycle: str = "all"
    date_scope: str = "any"
    importance: str = "any"
    urgency: str = "any"
    attention_only: bool = False


@dataclass(slots=True)
class ProjectFilterState:
    search: str = ""
    status: str = "all"


@dataclass(slots=True)
class CycleFilterState:
    search: str = ""
    status: str = "all"


@dataclass(slots=True)
class CycleWizardState:
    step: int = 1
    title: str = ""
    main_outcome: str = ""
    start_date: str = ""
    length_weeks: int = 12
    selected_project_ids: set[int] = field(default_factory=set)
    selected_milestone_ids: set[int] = field(default_factory=set)
    weekly_titles: dict[int, str] = field(default_factory=dict)
    weekly_definitions: dict[int, str] = field(default_factory=dict)


@dataclass(slots=True)
class AppSessionState:
    route: str = "/dashboard"
    locale: str = "en"
    theme_mode: str = "system"
    motion_enabled: bool = True
    reduced_motion: bool = False
    sidebar_collapsed: bool = False
    selected_task_id: int | None = None
    error_message: str | None = None
    notice_message: str | None = None
    task_filters: TaskFilterState | None = None
    task_view_mode: str = "kanban"
    task_calendar_anchor: str | None = None
    task_column_order: list[str] = field(
        default_factory=lambda: ["planned", "in_progress", "missed", "completed", "archive"]
    )
    task_card_order: dict[str, list[int]] = field(default_factory=dict)
    project_filters: ProjectFilterState | None = None
    cycle_filters: CycleFilterState | None = None
    cycle_wizard: CycleWizardState | None = None
    settings_category: str = "appearance"

    @property
    def effective_motion(self) -> bool:
        return self.motion_enabled and not self.reduced_motion
