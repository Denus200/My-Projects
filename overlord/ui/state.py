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
class TaskWorkspaceState:
    filters: TaskFilterState | None = None
    view_mode: str = "kanban"
    calendar_anchor: str | None = None
    expanded_date_navigation: str | None = None
    column_order: list[str] = field(
        default_factory=lambda: ["planned", "in_progress", "missed", "completed", "archive"]
    )
    card_order: dict[str, list[int]] = field(default_factory=dict)


@dataclass(slots=True)
class ProjectFilterState:
    search: str = ""
    status: str = "all"
    favorite_only: bool = False
    sort: str = "recent"
    selected_project_ids: set[int] = field(default_factory=set)
    selected_statuses: set[str] = field(default_factory=set)


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


@dataclass(slots=True, init=False)
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
    task_workspace: TaskWorkspaceState = field(default_factory=TaskWorkspaceState)
    project_filters: ProjectFilterState | None = None
    cycle_filters: CycleFilterState | None = None
    cycle_wizard: CycleWizardState | None = None
    settings_category: str = "appearance"

    def __init__(
        self,
        route: str = "/dashboard",
        locale: str = "en",
        theme_mode: str = "system",
        motion_enabled: bool = True,
        reduced_motion: bool = False,
        sidebar_collapsed: bool = False,
        selected_task_id: int | None = None,
        error_message: str | None = None,
        notice_message: str | None = None,
        task_filters: TaskFilterState | None = None,
        task_view_mode: str = "kanban",
        task_calendar_anchor: str | None = None,
        task_expanded_date_navigation: str | None = None,
        task_column_order: list[str] | None = None,
        task_card_order: dict[str, list[int]] | None = None,
        project_filters: ProjectFilterState | None = None,
        cycle_filters: CycleFilterState | None = None,
        cycle_wizard: CycleWizardState | None = None,
        settings_category: str = "appearance",
        task_workspace: TaskWorkspaceState | None = None,
    ) -> None:
        self.route = route
        self.locale = locale
        self.theme_mode = theme_mode
        self.motion_enabled = motion_enabled
        self.reduced_motion = reduced_motion
        self.sidebar_collapsed = sidebar_collapsed
        self.selected_task_id = selected_task_id
        self.error_message = error_message
        self.notice_message = notice_message
        self.task_workspace = task_workspace or TaskWorkspaceState(
            filters=task_filters,
            view_mode=task_view_mode,
            calendar_anchor=task_calendar_anchor,
            expanded_date_navigation=task_expanded_date_navigation,
            column_order=(
                task_column_order
                if task_column_order is not None
                else ["planned", "in_progress", "missed", "completed", "archive"]
            ),
            card_order=(
                task_card_order
                if task_card_order is not None
                else {}
            ),
        )
        self.project_filters = project_filters
        self.cycle_filters = cycle_filters
        self.cycle_wizard = cycle_wizard
        self.settings_category = settings_category

    @property
    def effective_motion(self) -> bool:
        return self.motion_enabled and not self.reduced_motion

    @property
    def task_filters(self) -> TaskFilterState | None:
        return self.task_workspace.filters

    @task_filters.setter
    def task_filters(self, value: TaskFilterState | None) -> None:
        self.task_workspace.filters = value

    @property
    def task_view_mode(self) -> str:
        return self.task_workspace.view_mode

    @task_view_mode.setter
    def task_view_mode(self, value: str) -> None:
        self.task_workspace.view_mode = value

    @property
    def task_calendar_anchor(self) -> str | None:
        return self.task_workspace.calendar_anchor

    @task_calendar_anchor.setter
    def task_calendar_anchor(self, value: str | None) -> None:
        self.task_workspace.calendar_anchor = value

    @property
    def task_expanded_date_navigation(self) -> str | None:
        return self.task_workspace.expanded_date_navigation

    @task_expanded_date_navigation.setter
    def task_expanded_date_navigation(self, value: str | None) -> None:
        self.task_workspace.expanded_date_navigation = value

    @property
    def task_column_order(self) -> list[str]:
        return self.task_workspace.column_order

    @task_column_order.setter
    def task_column_order(self, value: list[str]) -> None:
        self.task_workspace.column_order = value

    @property
    def task_card_order(self) -> dict[str, list[int]]:
        return self.task_workspace.card_order

    @task_card_order.setter
    def task_card_order(self, value: dict[str, list[int]]) -> None:
        self.task_workspace.card_order = value
