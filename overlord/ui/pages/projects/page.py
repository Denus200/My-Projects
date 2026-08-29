from __future__ import annotations

from collections.abc import Callable
from datetime import date
from pathlib import Path

import flet as ft

from overlord.app.read_models import TaskListItem
from overlord.app.services import ApplicationServices
from overlord.modules.projects.domain import (
    Project,
    ProjectPlanStatus,
    ProjectStage,
    ProjectStageStatus,
    ProjectStatus,
)
from overlord.modules.projects.read_models import ProjectDetail
from overlord.modules.tasks.domain import TaskLifecycle
from overlord.modules.validation import FieldValidationError
from overlord.ui.components.controls import primary_button, search_field, secondary_button, selection_button, select_field, tertiary_button, text_field
from overlord.ui.components.dialogs import close_dialog, dialog_footer
from overlord.ui.components.feedback import empty_state, show_success
from overlord.ui.components.filter_controls import Multiselect, SelectOption, search_box, single_select, toolbar_menu_bar
from overlord.ui.components.layout import page_container
from overlord.ui.components.project_details import project_details_header, project_details_shell
from overlord.ui.components.project_overview import (
    StageTimelineItem,
    project_plan_progress,
    project_summary_card,
    recent_project_activity,
)
from overlord.ui.components.project_cards import (
    PROJECT_CARD_COLLAPSED_WIDTH,
    PROJECT_CARD_EXPANDED_WIDTH,
    empty_project_card,
    project_card,
)
from overlord.ui.components.status import StatusBadgeSize, state_chip, status_badge
from overlord.ui.components.tabs import NavigationTab, navigation_tabs
from overlord.ui.components.complete_task import show_complete_task_dialog
from overlord.ui.components.task_card import TaskCardVariant, task_card, task_meta_chips_for_item
from overlord.ui.components.tasks import build_quick_task_dialog
from overlord.ui.design_system.icons import IconName, lucide_icon
from overlord.ui.design_system.styles import selection_button_style
from overlord.ui.design_system.tokens import PROJECT_COLOR_PALETTE, StateColors, ThemeTokens
from overlord.ui.state import AppSessionState, ProjectFilterState
from overlord.ui.strings import format_short_date, ui_error, ui_text


DETAIL_TAB_SPECS = (
    ("overview", "projects.tab.overview", IconName.OVERVIEW),
    ("plan", "projects.tab.plan", IconName.PLAN),
    ("tasks", "projects.tab.tasks", IconName.TASKS),
    ("notes", "projects.tab.notes", IconName.NOTES),
    ("archive", "projects.tab.archive", IconName.ARCHIVE),
)


def _detail_tabs() -> tuple[NavigationTab, ...]:
    return tuple(
        NavigationTab(key, ui_text(label_key), icon)
        for key, label_key, icon in DETAIL_TAB_SPECS
    )


def _status_label(status: ProjectStatus) -> str:
    return ui_text(f"projects.status.{status.value}")


def _project_status_badge_key(status: ProjectStatus) -> str:
    return {
        ProjectStatus.ACTIVE: "active",
        ProjectStatus.ON_HOLD: "paused",
        ProjectStatus.COMPLETED: "completed",
        ProjectStatus.ARCHIVED: "archived",
    }[status]


def _task_status_badge_key(status: TaskLifecycle) -> str:
    return {
        TaskLifecycle.BACKLOG: "planned",
        TaskLifecycle.PLANNED: "planned",
        TaskLifecycle.IN_PROGRESS: "in_progress",
        TaskLifecycle.PAUSED: "paused",
        TaskLifecycle.COMPLETED: "completed",
        TaskLifecycle.CANCELLED: "inactive",
    }[status]


def _status_color(status: ProjectStatus, tokens: ThemeTokens) -> StateColors:
    return {
        ProjectStatus.ACTIVE: tokens.success,
        ProjectStatus.ON_HOLD: tokens.warning,
        ProjectStatus.COMPLETED: tokens.info,
        ProjectStatus.ARCHIVED: tokens.neutral,
    }[status]


def _stage_color(status: ProjectStageStatus, tokens: ThemeTokens) -> StateColors:
    return {
        ProjectStageStatus.PLANNED: tokens.neutral,
        ProjectStageStatus.IN_PROGRESS: tokens.blocker,
        ProjectStageStatus.COMPLETED: tokens.success,
        ProjectStageStatus.ARCHIVED: tokens.neutral,
    }[status]


def _minutes(value: int) -> str:
    hours, minutes = divmod(value, 60)
    if hours and minutes:
        return f"{hours}h {minutes}m"
    return f"{hours}h" if hours else f"{minutes}m"


def _small_chip(text: str, tokens: ThemeTokens, *, colors: StateColors | None = None) -> ft.Container:
    palette = colors or tokens.neutral
    return ft.Container(
        ft.Text(text, size=tokens.text_small, color=palette.text),
        bgcolor=palette.background,
        border=ft.Border.all(tokens.border_width, palette.main),
        border_radius=tokens.radius_small,
        padding=ft.Padding.symmetric(horizontal=tokens.space_2, vertical=tokens.space_1),
    )


def _section(
    title: str,
    controls: list[ft.Control],
    tokens: ThemeTokens,
    *,
    action: ft.Control | None = None,
    col: int | dict[str, int] = 12,
    role: str | None = None,
) -> ft.Container:
    return ft.Container(
        ft.Column(
            [
                ft.Row(
                    [
                        ft.Text(title, color=tokens.text_primary, size=tokens.text_emphasis, weight=ft.FontWeight.W_600, expand=True),
                        *([action] if action else []),
                    ],
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                *controls,
            ],
            spacing=tokens.space_3,
        ),
        bgcolor=tokens.surface_card,
        border=ft.Border.all(tokens.border_width, tokens.border_default),
        border_radius=tokens.radius_medium,
        padding=tokens.space_4,
        col=col,
        data={"role": role} if role else None,
    )


def _project_detail_favorite_control(project: Project, tokens: ThemeTokens, on_toggle: Callable[[], None]) -> ft.Control:
    """Project Detail retains its existing lifecycle metadata action; cards do not."""
    label = ui_text("projects.favorite_remove" if project.favorite else "projects.favorite_add")
    surface = ft.Container(
        lucide_icon(IconName.STAR, color=tokens.accent_primary if project.favorite else tokens.text_muted, size=tokens.icon_small, label=label),
        width=tokens.control_height_compact,
        height=tokens.control_height_compact,
        alignment=ft.Alignment.CENTER,
        border_radius=tokens.radius_pill,
        data={"role": "project-detail-favorite", "project_id": project.id, "favorite": project.favorite},
    )
    return ft.GestureDetector(surface, mouse_cursor=ft.MouseCursor.CLICK, on_tap=lambda _event: on_toggle())


def _project_dialog(
    services: ApplicationServices,
    tokens: ThemeTokens,
    on_saved: Callable[[Project, str], None],
    close: Callable[[], None],
    *,
    project: Project | None = None,
) -> ft.AlertDialog:
    title = text_field(tokens, label=ui_text("projects.field_title"), value=project.title if project else "", autofocus=True, width=435)
    description = text_field(tokens, label=ui_text("projects.field_description"), value=project.description if project else "", multiline=True, min_lines=3, max_lines=5, width=435)
    selected_color = {"value": project.color if project else PROJECT_COLOR_PALETTE[1]}
    color_controls: list[ft.Container] = []

    def choose_color(color: str) -> None:
        selected_color["value"] = color
        for control in color_controls:
            active = control.data["color"] == color
            control.border = ft.Border.all(tokens.focus_width if active else tokens.border_width, tokens.accent_primary if active else tokens.border_default)
            control.content = lucide_icon(IconName.CHECK, color=tokens.accent_primary, size=tokens.icon_small, label=ui_text("projects.color_selected"), show_tooltip=False) if active else None
            control.update()

    for color in PROJECT_COLOR_PALETTE:
        active = color == selected_color["value"]
        swatch = ft.Container(
            lucide_icon(IconName.CHECK, color=tokens.accent_primary, size=tokens.icon_small, label=ui_text("projects.color_selected"), show_tooltip=False) if active else None,
            width=40,
            height=40,
            bgcolor=color,
            border=ft.Border.all(tokens.focus_width if active else tokens.border_width, tokens.accent_primary if active else tokens.border_default),
            border_radius=tokens.radius_small,
            alignment=ft.Alignment.CENTER,
            data={"role": "project-color", "color": color},
        )
        swatch.on_click = lambda _event, value=color: choose_color(value)
        color_controls.append(swatch)

    status = select_field(
        tokens,
        label=ui_text("projects.field_status"),
        value=project.status.value if project else ProjectStatus.ACTIVE.value,
        options=[ft.DropdownOption(value.value, _status_label(value)) for value in ProjectStatus if value is not ProjectStatus.ARCHIVED],
        width=435,
    )
    destination = ft.Row(
        spacing=tokens.space_2,
        data={"role": "project-destination", "value": "stay"},
    )

    def choose_destination(value: str) -> None:
        destination.data["value"] = value
        for button in destination.controls:
            button.style = selection_button_style(tokens, selected=button.data["value"] == value)
            button.update()

    for value, label in (
        ("stay", ui_text("projects.destination_stay")),
        ("plan", ui_text("projects.destination_plan")),
        ("tasks", ui_text("projects.destination_tasks")),
    ):
        option = selection_button(
            label,
            tokens,
            selected=value == "stay",
            expand=True,
            data={"role": "project-destination-option", "value": value},
        )
        option.on_click = lambda _event, selected=value: choose_destination(selected)
        destination.controls.append(option)
    message = ft.Text("", color=tokens.error.text, size=tokens.text_small)

    def save(_event) -> None:
        title.error = None
        message.value = ""
        try:
            if project:
                saved = services.projects.update_project.execute(project.id, title=title.value or "", description=description.value or "", color=selected_color["value"], status=ProjectStatus(status.value))
            else:
                saved = services.projects.create_project.execute(title.value or "", description.value or "", color=selected_color["value"], status=ProjectStatus(status.value))
            on_saved(saved, destination.data["value"])
        except Exception as error:
            rendered = ui_error(error)
            if isinstance(error, FieldValidationError) and error.field == "title":
                title.error = rendered
                title.update()
            else:
                message.value = rendered
                message.update()

    controls: list[ft.Control] = [
        ft.Text(ui_text("projects.edit_description" if project else "projects.create_description"), color=tokens.text_secondary, size=tokens.text_small),
        title,
        description,
        ft.Text(ui_text("projects.field_color"), color=tokens.text_primary, size=tokens.text_small, weight=ft.FontWeight.W_600),
        ft.Row(color_controls, spacing=tokens.space_2, wrap=True),
        status,
    ]
    if not project:
        controls.extend([ft.Text(ui_text("projects.open_after_creation"), color=tokens.text_primary, size=tokens.text_small, weight=ft.FontWeight.W_600), destination])
    controls.append(message)
    return ft.AlertDialog(
        modal=True,
        title=ft.Row(
            [
                ft.Text(ui_text("projects.edit_title" if project else "projects.create_title"), color=tokens.text_primary, weight=ft.FontWeight.W_700, expand=True),
                ft.IconButton(
                    icon=lucide_icon(IconName.CLOSE, color=tokens.text_secondary, size=tokens.icon_medium, label=ui_text("projects.cancel")),
                    tooltip=ui_text("projects.cancel"),
                    on_click=lambda _event: close(),
                ),
            ]
        ),
        content=ft.Container(ft.Column(controls, spacing=tokens.space_3, tight=True), width=435),
        actions=dialog_footer(ui_text("projects.cancel"), ui_text("projects.save" if project else "projects.create"), lambda _event: close(), save, tokens),
        bgcolor=tokens.surface_elevated,
        data={"role": "project-dialog", "mode": "edit" if project else "create"},
    )


def _build_list(services, tokens, navigate, report_error, state: AppSessionState, page: ft.Page | None) -> ft.Control:
    filters = state.project_filters or ProjectFilterState()
    state.project_filters = filters
    if filters.status != "all" and not filters.selected_statuses:
        filters.selected_statuses.add(filters.status)
    card_width = PROJECT_CARD_COLLAPSED_WIDTH if state.sidebar_collapsed else PROJECT_CARD_EXPANDED_WIDTH
    column_count = 5 if state.sidebar_collapsed else 4
    column_gap = 11 if state.sidebar_collapsed else tokens.space_3
    available_projects = services.projects.list_projects.execute(sort="name")
    project_multiselect = Multiselect(
        tokens,
        label=ui_text("projects.filter_projects"),
        options=(SelectOption(str(project.id), project.title) for project in available_projects),
        selected=(str(project_id) for project_id in filters.selected_project_ids),
        width=142,
        menu_width=260,
        singular_label=ui_text("projects.filter_project"),
        role="projects-multiselect",
    )
    status_multiselect = Multiselect(
        tokens,
        label=ui_text("projects.status_filter"),
        options=(SelectOption(value.value, _status_label(value)) for value in ProjectStatus),
        selected=filters.selected_statuses,
        width=132,
        menu_width=184,
        role="status-multiselect",
    )
    search = search_box(tokens, hint=ui_text("projects.search"), value=filters.search)
    grid = ft.Row(
        spacing=column_gap,
        run_spacing=tokens.space_3,
        wrap=True,
        vertical_alignment=ft.CrossAxisAlignment.START,
        data={
            "role": "projects-grid",
            "card_width": card_width,
            "sidebar_state": "collapsed" if state.sidebar_collapsed else "expanded",
            "layout": "fixed-width-wrap",
            "column_count": column_count,
            "column_gap": column_gap,
        },
    )
    reset = tertiary_button(ui_text("projects.reset"), tokens, visible=False, data={"role": "projects-reset"})

    def is_dirty() -> bool:
        return bool(
            (search.value or "")
            or filters.selected_project_ids
            or filters.selected_statuses
            or filters.sort != "recent"
        )

    def safe_update(control: ft.Control) -> None:
        try:
            control.update()
        except RuntimeError as error:
            if "Control must be added to the page first" not in str(error):
                raise

    def render(*, update: bool = False) -> None:
        filters.search = search.value or ""
        details = list(
            services.projects.list_summaries.execute(
                None,
                filters.search,
                favorite_only=False,
                sort=filters.sort,
            )
        )
        if filters.selected_project_ids:
            details = [detail for detail in details if detail.project.id in filters.selected_project_ids]
        if filters.selected_statuses:
            details = [detail for detail in details if detail.project.status.value in filters.selected_statuses]
        grid.controls = [
            project_card(
                detail,
                tokens,
                width=card_width,
                on_open=lambda _event, project_id=detail.project.id: navigate(f"/projects/{project_id}"),
                on_add_task=lambda _event, project_id=detail.project.id: open_add_task(project_id),
            )
            for detail in details
        ]
        if details:
            grid.controls.append(empty_project_card(tokens, width=card_width, on_create=open_create))
        if not details:
            if is_dirty():
                grid.controls = [empty_state(ui_text("projects.empty"), tokens)]
            else:
                grid.controls = [empty_project_card(tokens, width=card_width, on_create=open_create)]
        reset.visible = is_dirty()
        if update:
            safe_update(grid)
            safe_update(reset)

    def apply(_event) -> None:
        try:
            render(update=True)
        except Exception as error:
            report_error(ui_error(error))

    def select_projects(values: set[str]) -> None:
        filters.selected_project_ids = {int(value) for value in values}
        apply(None)

    def select_statuses(values: set[str]) -> None:
        filters.selected_statuses = set(values)
        filters.status = next(iter(values)) if len(values) == 1 else "all"
        apply(None)

    def choose_sort(value: str) -> None:
        filters.sort = value
        sort_control.data["value"] = value
        apply(None)

    sort_control = single_select(
        tokens,
        value=filters.sort,
        options=(
            SelectOption("recent", ui_text("projects.sort_recent")),
            SelectOption("name", ui_text("projects.sort_name")),
            SelectOption("favorite", ui_text("projects.sort_favorite")),
        ),
        width=184,
        on_select=choose_sort,
        role="projects-sort",
    )

    def clear_filters(_event) -> None:
        search.value = ""
        filters.search = ""
        filters.status = "all"
        filters.favorite_only = False
        filters.selected_project_ids.clear()
        filters.selected_statuses.clear()
        filters.sort = "recent"
        project_multiselect.set_selected(())
        status_multiselect.set_selected(())
        sort_control.value = "recent"
        sort_control.data["value"] = "recent"
        safe_update(sort_control)
        safe_update(search)
        render(update=True)

    def open_create(_event) -> None:
        if page is None:
            return

        def created(project: Project, destination: str) -> None:
            close_dialog(page)
            show_success(page, tokens, ui_text("projects.created"))
            if destination == "plan":
                navigate(f"/projects/{project.id}/plan")
            elif destination == "tasks":
                navigate(f"/projects/{project.id}/tasks")
            else:
                render(update=True)

        page.show_dialog(_project_dialog(services, tokens, created, lambda: close_dialog(page)))

    def open_add_task(project_id: int) -> None:
        if page is None:
            return

        def created(_task) -> None:
            close_dialog(page)
            show_success(page, tokens, ui_text("tasks.created"))
            render(update=True)

        page.show_dialog(
            build_quick_task_dialog(
                services,
                services.projects.list_projects.execute(),
                tokens,
                created,
                lambda: close_dialog(page),
                selected_project_id=project_id,
                page=page,
            )
        )

    project_multiselect.on_change = select_projects
    status_multiselect.on_change = select_statuses
    search.on_change = apply
    search.on_submit = apply
    reset.on_click = clear_filters
    render()

    def resize_filters(event: object) -> None:
        available = float(getattr(event, "width", 599) or 599)
        search.width = min(599, max(280, available))
        safe_update(search)

    project_multiselect.control.margin = ft.Margin.only(right=tokens.space_2)
    multiselect_group = toolbar_menu_bar(
        tokens,
        [project_multiselect.control, status_multiselect.control],
        role="projects-multiselect-group",
    )
    filter_group = ft.Row(
        [search, multiselect_group, sort_control, reset],
        spacing=tokens.space_2,
        run_spacing=tokens.space_2,
        wrap=True,
        on_size_change=resize_filters,
        data={"role": "projects-toolbar-filters"},
    )
    new_project = primary_button(
        ft.Row(
            [
                lucide_icon(IconName.PLUS, color=tokens.on_accent, size=tokens.icon_small, label=ui_text("projects.new_action"), show_tooltip=False),
                ft.Text(ui_text("projects.new_action"), color=tokens.on_accent),
            ],
            spacing=tokens.space_2,
            tight=True,
        ),
        tokens,
        height=48,
        on_click=open_create,
        data={"role": "projects-new-project"},
    )
    toolbar = ft.ResponsiveRow(
        [
            ft.Container(filter_group, col={"xs": 12, "xl": 10}),
            ft.Container(
                ft.Row([new_project], alignment=ft.MainAxisAlignment.END),
                col={"xs": 12, "xl": 2},
            ),
        ],
        spacing=tokens.space_2,
        run_spacing=tokens.space_2,
        data={"role": "projects-toolbar", "wide_composition": "search-filters-sort-reset-new"},
    )
    return page_container(
        ui_text("projects.title"),
        [toolbar, grid],
        tokens,
        content_spacing=27,
        header_gap=5,
        page_id="projects",
        role="projects-list-page",
    )


def _detail_route(route: str) -> tuple[int, str]:
    parts = route.split("?", 1)[0].strip("/").split("/")
    project_id = int(parts[1])
    tab = parts[2] if len(parts) > 2 else "overview"
    return project_id, tab if tab in {item[0] for item in DETAIL_TAB_SPECS} else "overview"


def _task_matches(item: TaskListItem, value: str) -> bool:
    """Compatibility filter used by existing Project task tests and callers."""
    if value == "completed":
        return item.task.lifecycle_status is TaskLifecycle.COMPLETED
    if value == "blocked":
        return item.open_blockers > 0
    return item.task.lifecycle_status not in {TaskLifecycle.COMPLETED, TaskLifecycle.CANCELLED}


def _overview(
    detail: ProjectDetail,
    tasks: list[TaskListItem],
    tokens: ThemeTokens,
    navigate,
) -> list[ft.Control]:
    project = detail.project

    def calendar_metadata(value: date, *, role: str) -> ft.Row:
        label = format_short_date(value)
        return ft.Row(
            [
                lucide_icon(
                    IconName.CALENDAR,
                    color=tokens.text_secondary,
                    size=tokens.icon_small,
                    label=label,
                    show_tooltip=False,
                ),
                ft.Text(label, color=tokens.text_secondary, size=tokens.text_body),
            ],
            spacing=tokens.space_2,
            tight=True,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            data={"role": role, "date": value.isoformat()},
        )

    milestone = detail.current_milestone
    checkpoint_metadata = (
        [calendar_metadata(milestone.target_date, role="project-checkpoint-date")]
        if milestone is not None and milestone.target_date is not None
        else []
    )
    checkpoint_open = (
        (lambda _event: navigate(f"/cycles/{detail.current_milestone_cycle_id}"))
        if milestone is not None and detail.current_milestone_cycle_id is not None
        else None
    )
    checkpoint_card = project_summary_card(
        tokens,
        role="project-next-checkpoint",
        label=ui_text("projects.next_checkpoint"),
        title=milestone.title if milestone else ui_text("projects.no_current_checkpoint"),
        icon=IconName.CALENDAR,
        icon_color=tokens.accent_primary,
        icon_background=tokens.soft_red_background,
        metadata=checkpoint_metadata,
        on_open=checkpoint_open,
        open_label=ui_text("projects.open_checkpoint"),
        filled=milestone is not None,
    )

    next_action_item = None
    if detail.next_action_task_id is not None:
        next_action_item = next(
            (item for item in tasks if item.task.id == detail.next_action_task_id),
            None,
        )
    next_action_metadata: list[ft.Control] = []
    if next_action_item is not None:
        lifecycle = next_action_item.task.lifecycle_status
        next_action_metadata.append(
            status_badge(
                _task_status_badge_key(lifecycle),
                ui_text(f"lifecycle.{lifecycle.value}"),
                tokens,
                size=StatusBadgeSize.SMALL,
            )
        )
        relevant_date = (
            next_action_item.task.deadline_at.date()
            if next_action_item.task.deadline_at is not None
            else next_action_item.task.schedule_start_date
        )
        if relevant_date is not None:
            next_action_metadata.append(
                calendar_metadata(relevant_date, role="project-next-action-date")
            )
    next_action_card = project_summary_card(
        tokens,
        role="project-next-action",
        label=ui_text("projects.next_action"),
        title=detail.next_action or ui_text("projects.no_next_action"),
        icon=IconName.ZAP,
        icon_color=tokens.warning.main,
        icon_background=tokens.warning.background,
        metadata=next_action_metadata,
        on_open=(
            (lambda _event: navigate(f"/tasks?task={next_action_item.task.id}"))
            if next_action_item is not None
            else None
        ),
        open_label=ui_text("projects.open_next_action"),
        filled=detail.next_action is not None,
    )

    cycle = detail.linked_cycle
    cycle_metadata: list[ft.Control] = []
    if cycle is not None:
        week = cycle.current_week(date.today())
        if week is not None:
            cycle_metadata.append(
                _small_chip(
                    ui_text("projects.cycle_week", week=week, length=cycle.length_weeks),
                    tokens,
                    colors=tokens.blocker,
                )
            )
        cycle_metadata.extend(
            [
                calendar_metadata(cycle.start_date, role="project-linked-cycle-start-date"),
                ft.Text("–", color=tokens.text_muted),
                ft.Text(format_short_date(cycle.end_date), color=tokens.text_secondary, size=tokens.text_body),
            ]
        )
    linked_cycle_card = project_summary_card(
        tokens,
        role="project-linked-cycle",
        label=ui_text("projects.linked_cycle"),
        title=cycle.title if cycle else ui_text("projects.no_linked_cycle"),
        icon=IconName.CALENDAR,
        icon_color=tokens.text_primary,
        icon_background=None,
        metadata=cycle_metadata,
        on_open=(lambda _event: navigate(f"/cycles/{cycle.id}")) if cycle else None,
        open_label=ui_text("projects.open_linked_cycle"),
        strong_label=True,
        filled=cycle is not None,
    )

    summary_row = ft.ResponsiveRow(
        [checkpoint_card, next_action_card, linked_cycle_card],
        spacing=tokens.space_4,
        run_spacing=tokens.space_4,
        data={"role": "project-overview-summary-row", "card_count": 3},
    )

    plan_progress = detail.plan_progress
    timeline: list[StageTimelineItem] = []
    for item in plan_progress.stages if plan_progress is not None else ():
        stage = item.stage
        stage_progress = item.progress
        if stage.status is ProjectStageStatus.COMPLETED:
            state = "completed"
            state_label = ui_text("projects.stage_state.completed")
        elif stage.status is ProjectStageStatus.IN_PROGRESS:
            state = "current"
            state_label = f"{round(stage_progress * 100)}%"
        else:
            state = "future"
            state_label = ui_text("projects.stage_state.not_started")
        timeline.append(StageTimelineItem(stage.title, state, state_label, stage_progress))

    current_stage = plan_progress.current_stage if plan_progress is not None else None
    progress_card = project_plan_progress(
        tokens,
        title=ui_text("projects.plan_progress"),
        empty_message=ui_text("projects.no_project_plan"),
        plan_title=plan_progress.plan.title if plan_progress is not None else None,
        stages=timeline,
        completed_count=plan_progress.completed_stage_count if plan_progress is not None else 0,
        current_stage_title=current_stage.stage.title if current_stage else None,
        current_stage_progress=(
            plan_progress.current_stage_progress
            if plan_progress is not None
            else None
        ),
        overall_progress=plan_progress.overall_progress if plan_progress is not None else 0.0,
        stages_total_label=ui_text("projects.stages_total_label"),
        stages_completed_label=ui_text("projects.stages_completed_label"),
        current_stage_label=ui_text("projects.current_stage"),
        overall_progress_label=ui_text("projects.overall_plan_progress"),
        on_open=(lambda _event: navigate(f"/projects/{project.id}/plan"))
        if detail.active_plan
        else None,
        open_label=ui_text("projects.open_plan"),
    )
    recent = recent_project_activity(
        (),
        tokens,
        title=ui_text("projects.recent_updates"),
        empty_message=ui_text("projects.recent_updates_empty"),
        open_label=ui_text("projects.recent_updates"),
    )
    main_row = ft.ResponsiveRow(
        [progress_card, recent],
        spacing=tokens.space_4,
        run_spacing=tokens.space_4,
        data={"role": "project-overview-main-row", "proportions": "8:4"},
    )
    return [summary_row, main_row]


def _stage_card(stage: ProjectStage, tasks: tuple[TaskListItem, ...], tokens: ThemeTokens) -> ft.Container:
    stage_tasks = [item for item in tasks if any(context.stage_id == stage.id for context in item.project_contexts)]
    completed = sum(item.task.lifecycle_status is TaskLifecycle.COMPLETED for item in stage_tasks)
    return ft.Container(
        ft.Column(
            [
                ft.Row([ft.Text(f"{stage.position + 1}. {stage.title}", color=tokens.text_primary, weight=ft.FontWeight.W_600, expand=True), state_chip(ui_text(f"projects.stage_status.{stage.status.value}"), _stage_color(stage.status, tokens), tokens)]),
                ft.ProgressBar(value=completed / len(stage_tasks) if stage_tasks else 0, color=_stage_color(stage.status, tokens).main, bgcolor=tokens.border_default, border_radius=tokens.radius_pill),
                ft.Text(ui_text("projects.stage_tasks", completed=completed, total=len(stage_tasks)), color=tokens.text_muted, size=tokens.text_small),
            ],
            spacing=tokens.space_2,
        ),
        bgcolor=tokens.surface_inner,
        border=ft.Border.all(tokens.border_width, tokens.border_default),
        border_radius=tokens.radius_medium,
        padding=tokens.space_3,
        width=280,
        data={"role": "project-stage", "stage_id": stage.id},
    )


def _plan_view(detail: ProjectDetail, tasks, services, tokens, refresh, report_error, page: ft.Page | None) -> list[ft.Control]:
    project = detail.project

    def simple_dialog(title_text: str, field_label: str, save_action: Callable[[str], None]) -> None:
        if page is None:
            return
        field = text_field(tokens, label=field_label, autofocus=True)
        message = ft.Text("", color=tokens.error.text, size=tokens.text_small)

        def save(_event) -> None:
            try:
                save_action(field.value or "")
                close_dialog(page)
                refresh()
            except Exception as error:
                message.value = ui_error(error)
                message.update()

        page.show_dialog(ft.AlertDialog(modal=True, title=title_text, content=ft.Container(ft.Column([field, message], spacing=tokens.space_3, tight=True), width=420), actions=dialog_footer(ui_text("projects.cancel"), ui_text("projects.create"), lambda _e: close_dialog(page), save, tokens), bgcolor=tokens.surface_elevated))

    def add_plan(_event) -> None:
        simple_dialog(ui_text("projects.new_plan"), ui_text("projects.plan_name"), lambda value: services.projects.create_plan.execute(project.id, value))

    def add_stage(_event) -> None:
        if detail.active_plan:
            simple_dialog(ui_text("projects.add_stage"), ui_text("projects.stage_name"), lambda value: services.projects.create_stage.execute(project.id, detail.active_plan.id, value))

    def complete_plan(_event) -> None:
        if detail.active_plan is None:
            return
        try:
            services.projects.change_plan_status.execute(detail.active_plan.id, ProjectPlanStatus.COMPLETED)
            refresh()
        except Exception as error:
            report_error(ui_error(error))

    if detail.active_plan is None:
        return [empty_state(ui_text("projects.no_project_plan"), tokens, primary_button(ui_text("projects.new_plan"), tokens, on_click=add_plan))]
    stage_controls = [_stage_card(stage, tasks, tokens) for stage in detail.stages]
    stages: ft.Control = ft.Row(stage_controls, spacing=tokens.space_3, scroll=ft.ScrollMode.HIDDEN) if stage_controls else empty_state(ui_text("projects.no_stages"), tokens, primary_button(ui_text("projects.add_stage"), tokens, on_click=add_stage))
    return [
        ft.ResponsiveRow([
            _section(ui_text("projects.project_goal"), [ft.Text(project.description or ui_text("projects.card_no_description"), color=tokens.text_secondary)], tokens, col={"sm": 12, "lg": 7}),
            _section(ui_text("projects.linked_cycle"), [ft.Text(detail.active_cycle.title if detail.active_cycle else ui_text("projects.not_connected"), color=tokens.text_secondary)], tokens, col={"sm": 12, "lg": 5}),
        ], spacing=tokens.space_3, run_spacing=tokens.space_3),
        _section(
            ui_text("projects.stages"),
            [stages],
            tokens,
            action=ft.Row(
                [
                    ft.TextButton(ui_text("projects.complete_plan"), on_click=complete_plan),
                    ft.TextButton(ui_text("projects.add_stage"), on_click=add_stage),
                ],
                spacing=tokens.space_2,
                tight=True,
            ),
        ),
    ]


def _tasks_view(detail: ProjectDetail, tasks, services, tokens, navigate, refresh, report_error, page: ft.Page | None) -> list[ft.Control]:
    task_list = ft.Column(spacing=tokens.space_2, data={"role": "project-task-list"})
    all_button = selection_button(ui_text("projects.tasks_all"), tokens, selected=True)
    stage_button = selection_button(ui_text("projects.tasks_by_stage"), tokens, selected=False)
    mode = {"value": "all"}
    search = search_field(tokens, label=ui_text("projects.search_tasks"), expand=True)
    status_filter = select_field(
        tokens,
        value="all",
        options=[
            ft.DropdownOption("all", ui_text("projects.tasks_all")),
            ft.DropdownOption("open", ui_text("projects.tasks_open")),
            ft.DropdownOption("completed", ui_text("projects.tasks_completed")),
            ft.DropdownOption("blocked", ui_text("projects.tasks_blocked")),
        ],
    )
    stage_filter = select_field(
        tokens,
        value="all",
        options=[
            ft.DropdownOption("all", ui_text("projects.filter_stage_all")),
            ft.DropdownOption("unassigned", ui_text("projects.unassigned")),
            *[ft.DropdownOption(str(stage.id), stage.title) for stage in detail.stages],
        ],
    )
    sort = select_field(
        tokens,
        value="priority",
        options=[
            ft.DropdownOption("priority", ui_text("projects.sort_priority")),
            ft.DropdownOption("recent", ui_text("projects.sort_recent")),
            ft.DropdownOption("name", ui_text("projects.sort_name")),
        ],
    )

    def complete(task_id: int) -> None:
        try:
            task = services.tasks.get_editor.execute(task_id).task
            if task.lifecycle_status is TaskLifecycle.COMPLETED:
                services.tasks.change_lifecycle.execute(
                    task_id,
                    TaskLifecycle.PLANNED,
                    "Reopened from Project Tasks",
                )
                refresh()
            elif page is not None:
                show_complete_task_dialog(
                    page,
                    services,
                    task_id,
                    tokens,
                    lambda _task: refresh(),
                    report_error,
                )
        except Exception as error:
            report_error(ui_error(error))

    def create_task(_event) -> None:
        if page is None:
            return
        projects = services.projects.list_projects.execute()

        def created(_task) -> None:
            close_dialog(page)
            show_success(page, tokens, ui_text("tasks.created"))
            refresh()

        page.show_dialog(
            build_quick_task_dialog(
                services,
                projects,
                tokens,
                created,
                lambda: close_dialog(page),
                selected_project_id=detail.project.id,
                page=page,
            )
        )

    def task_control(item: TaskListItem) -> ft.Control:
        return task_card(item, tokens, variant=TaskCardVariant.COMPACT, project_colors=item.project_colors, meta_chips=task_meta_chips_for_item(item), on_open=lambda _event, task_id=item.task.id: navigate(f"/tasks?task={task_id}"), on_complete=lambda _event, task_id=item.task.id: complete(task_id), allow_reopen=True, role="project-task-card")

    def render(selected: str, *, update: bool = False) -> None:
        mode["value"] = selected
        filtered = list(tasks)
        query = (search.value or "").strip().lower()
        if query:
            filtered = [item for item in filtered if query in item.task.title.lower()]
        status_value = status_filter.value or "all"
        if status_value != "all":
            filtered = [item for item in filtered if _task_matches(item, status_value)]
        selected_stage = stage_filter.value or "all"
        if selected_stage == "unassigned":
            filtered = [item for item in filtered if not any(context.project_id == detail.project.id and context.stage_id is not None for context in item.project_contexts)]
        elif selected_stage != "all":
            filtered = [item for item in filtered if any(context.stage_id == int(selected_stage) for context in item.project_contexts)]
        if sort.value == "name":
            filtered.sort(key=lambda item: (item.task.title.lower(), item.task.id))
        elif sort.value == "recent":
            filtered.sort(key=lambda item: (item.task.updated_at, item.task.id), reverse=True)
        else:
            filtered.sort(key=lambda item: (not bool(item.task.urgency), not bool(item.task.importance), item.task.id))
        if selected == "all":
            task_list.controls = [task_control(item) for item in filtered] or [empty_state(ui_text("projects.tasks_none"), tokens)]
        elif not detail.stages:
            task_list.controls = [empty_state(ui_text("projects.no_stages"), tokens)]
        else:
            controls: list[ft.Control] = []
            for stage in detail.stages:
                stage_tasks = [item for item in filtered if any(context.stage_id == stage.id for context in item.project_contexts)]
                controls.append(_section(stage.title, [*([task_control(item) for item in stage_tasks] or [ft.Text(ui_text("projects.stage_empty"), color=tokens.text_muted)])], tokens))
            unassigned = [item for item in filtered if not any(context.project_id == detail.project.id and context.stage_id is not None for context in item.project_contexts)]
            if unassigned:
                controls.append(_section(ui_text("projects.unassigned"), [task_control(item) for item in unassigned], tokens))
            task_list.controls = controls
        all_button.style = selection_button_style(tokens, selected=selected == "all")
        stage_button.style = selection_button_style(tokens, selected=selected == "stage")
        if update:
            task_list.update(); all_button.update(); stage_button.update()

    all_button.on_click = lambda _event: render("all", update=True)
    stage_button.on_click = lambda _event: render("stage", update=True)
    search.on_submit = lambda _event: render(mode["value"], update=True)
    status_filter.on_select = lambda _event: render(mode["value"], update=True)
    stage_filter.on_select = lambda _event: render(mode["value"], update=True)
    sort.on_select = lambda _event: render(mode["value"], update=True)
    render("all")
    summary = _section(ui_text("projects.task_summary"), [ft.Text(str(detail.eligible_task_count), color=tokens.text_primary, size=tokens.text_display, weight=ft.FontWeight.W_700), ft.Text(ui_text("projects.card_open", count=detail.open_task_count), color=tokens.text_secondary), ft.Text(ui_text("projects.estimated_time", value=_minutes(detail.estimated_minutes)), color=tokens.text_secondary), ft.Text(ui_text("projects.actual_time"), color=tokens.text_muted)], tokens, role="project-task-summary")
    return [
        ft.ResponsiveRow(
            [
                ft.Container(ft.Row([all_button, stage_button], spacing=tokens.space_2), col={"sm": 12, "lg": 2}),
                ft.Container(search, col={"sm": 12, "lg": 3}),
                ft.Container(status_filter, col={"sm": 12, "lg": 2}),
                ft.Container(stage_filter, col={"sm": 12, "lg": 2}),
                ft.Container(sort, col={"sm": 12, "lg": 1}),
                ft.Container(primary_button(ui_text("projects.create_task"), tokens, on_click=create_task), col={"sm": 12, "lg": 2}),
            ],
            spacing=tokens.space_2,
            run_spacing=tokens.space_2,
            data={"role": "project-task-filters"},
        ),
        ft.ResponsiveRow([ft.Container(task_list, col={"sm": 12, "lg": 9}), ft.Container(summary, col={"sm": 12, "lg": 3})], spacing=tokens.space_3, run_spacing=tokens.space_3),
    ]


def _notes_view(detail: ProjectDetail, services, tokens, refresh, report_error, page: ft.Page | None) -> list[ft.Control]:
    workspace = services.projects.get_workspace.execute(detail.project.id)

    def add_note(_event) -> None:
        if page is None:
            return
        title = text_field(tokens, label=ui_text("projects.note_title"), autofocus=True)
        body = text_field(tokens, label=ui_text("projects.note_content"), multiline=True, min_lines=8, max_lines=14)
        message = ft.Text("", color=tokens.error.text, size=tokens.text_small)

        def save(_save_event) -> None:
            try:
                services.projects.create_note.execute(detail.project.id, title.value or "", body.value or "")
                close_dialog(page); refresh()
            except Exception as error:
                message.value = ui_error(error); message.update()

        page.show_dialog(ft.AlertDialog(modal=True, title=ui_text("projects.new_note"), content=ft.Container(ft.Column([title, body, message], spacing=tokens.space_3, tight=True), width=560), actions=dialog_footer(ui_text("projects.cancel"), ui_text("projects.save"), lambda _e: close_dialog(page), save, tokens), bgcolor=tokens.surface_elevated))

    async def add_file(_event) -> None:
        try:
            selected = await ft.FilePicker().pick_files(allow_multiple=False)
            if selected and selected[0].path:
                services.projects.add_file.execute(detail.project.id, Path(selected[0].path)); refresh()
        except Exception as error:
            report_error(ui_error(error))

    note_controls = [ft.Container(ft.Column([ft.Text(note.title, color=tokens.text_primary, weight=ft.FontWeight.W_600), ft.Text(note.content[:120] or ui_text("projects.note_empty"), color=tokens.text_secondary, size=tokens.text_small, max_lines=3, overflow=ft.TextOverflow.ELLIPSIS)], spacing=tokens.space_1), bgcolor=tokens.surface_inner, border_radius=tokens.radius_small, padding=tokens.space_3) for note in workspace.notes] or [empty_state(ui_text("projects.notes_empty"), tokens)]
    file_controls = [ft.Container(ft.Row([lucide_icon(IconName.NOTES, color=tokens.text_secondary, size=tokens.icon_small, label=item.display_name), ft.Text(item.display_name, color=tokens.text_primary, expand=True), ft.Text(f"{max(1, item.size_bytes // 1024)} KB", color=tokens.text_muted, size=tokens.text_small)], spacing=tokens.space_2), bgcolor=tokens.surface_inner, border_radius=tokens.radius_small, padding=tokens.space_3) for item in workspace.files] or [empty_state(ui_text("projects.files_empty"), tokens)]
    selected_note = workspace.notes[0] if workspace.notes else None
    viewer = _section(selected_note.title if selected_note else ui_text("projects.note_preview"), [ft.Markdown(selected_note.content, selectable=True) if selected_note else empty_state(ui_text("projects.note_preview_empty"), tokens)], tokens, col={"sm": 12, "lg": 6})
    return [ft.ResponsiveRow([
        _section(ui_text("projects.notes"), note_controls, tokens, action=ft.TextButton(ui_text("projects.new_note"), on_click=add_note), col={"sm": 12, "lg": 3}),
        _section(ui_text("projects.files"), file_controls, tokens, action=ft.TextButton(ui_text("projects.add_file"), on_click=add_file), col={"sm": 12, "lg": 3}),
        viewer,
    ], spacing=tokens.space_3, run_spacing=tokens.space_3)]


def _archive_view(detail: ProjectDetail, services, tokens, refresh, report_error) -> list[ft.Control]:
    plans = services.projects.list_plans.execute(detail.project.id)

    def toggle_archive(_event) -> None:
        try:
            target = ProjectStatus.ACTIVE if detail.project.status is ProjectStatus.ARCHIVED else ProjectStatus.ARCHIVED
            services.projects.update_project.execute(detail.project.id, status=target); refresh()
        except Exception as error:
            report_error(ui_error(error))

    rows = [ft.Container(ft.Row([ft.Text(plan.title, color=tokens.text_primary, expand=True), state_chip(ui_text(f"projects.plan_status.{plan.status.value}"), tokens.success if plan.status is ProjectPlanStatus.COMPLETED else tokens.neutral, tokens)], spacing=tokens.space_3), bgcolor=tokens.surface_inner, border_radius=tokens.radius_small, padding=tokens.space_3) for plan in plans] or [empty_state(ui_text("projects.plan_history_empty"), tokens)]
    action_label = ui_text("projects.restore_project" if detail.project.status is ProjectStatus.ARCHIVED else "projects.archive_project")
    return [ft.ResponsiveRow([
        _section(ui_text("projects.plan_history"), rows, tokens, col={"sm": 12, "lg": 8}),
        _section(ui_text("projects.what_archived"), [ft.Text(ui_text("projects.archive_explainer"), color=tokens.text_secondary)], tokens, action=secondary_button(action_label, tokens, on_click=toggle_archive, data={"role": "project-archive-toggle"}), col={"sm": 12, "lg": 4}),
    ], spacing=tokens.space_3, run_spacing=tokens.space_3)]


def _build_detail(services, tokens, route, navigate, refresh, report_error, page: ft.Page | None) -> ft.Control:
    try:
        project_id, selected_tab = _detail_route(route)
        detail = services.projects.get_detail.execute(project_id)
    except Exception as error:
        return page_container(ui_text("projects.unavailable"), [secondary_button(ui_text("projects.back"), tokens, on_click=lambda _event: navigate("/projects"))], tokens, subtitle=ui_error(error), page_id="projects")
    project = detail.project
    tasks = services.tasks.list_tasks.execute(project_id=project.id)

    def tab_route(tab: str) -> None:
        navigate(f"/projects/{project.id}" if tab == "overview" else f"/projects/{project.id}/{tab}")

    def open_edit(_event) -> None:
        if page is None:
            return

        def saved(_project: Project, _destination: str) -> None:
            close_dialog(page); show_success(page, tokens, ui_text("projects.updated")); refresh()

        page.show_dialog(_project_dialog(services, tokens, saved, lambda: close_dialog(page), project=project))

    def toggle_favorite() -> None:
        try:
            services.projects.update_project.execute(project.id, favorite=not project.favorite)
            refresh()
        except Exception as error:
            report_error(ui_error(error))

    favorite_control = _project_detail_favorite_control(project, tokens, toggle_favorite)
    header = project_details_header(
        title=project.title,
        description=project.description,
        project_color=project.color,
        status=_project_status_badge_key(project.status),
        status_label=_status_label(project.status),
        favorite_control=favorite_control,
        tokens=tokens,
        on_back=lambda _event: navigate("/projects"),
        on_more=open_edit,
    )
    tabs = navigation_tabs(_detail_tabs(), selected_tab, tokens, tab_route)
    if selected_tab == "overview":
        body = _overview(detail, list(tasks), tokens, navigate)
    elif selected_tab == "plan":
        body = _plan_view(detail, tasks, services, tokens, refresh, report_error, page)
    elif selected_tab == "tasks":
        body = _tasks_view(detail, tasks, services, tokens, navigate, refresh, report_error, page)
    elif selected_tab == "notes":
        body = _notes_view(detail, services, tokens, refresh, report_error, page)
    else:
        body = _archive_view(detail, services, tokens, refresh, report_error)
    return project_details_shell(header, tabs, body, tokens)


def build_projects(
    services: ApplicationServices,
    tokens: ThemeTokens,
    route: str,
    navigate,
    refresh,
    report_error,
    state: AppSessionState | None = None,
    page: ft.Page | None = None,
) -> ft.Control:
    if route.startswith("/projects/"):
        return _build_detail(services, tokens, route, navigate, refresh, report_error, page)
    return _build_list(services, tokens, navigate, report_error, state or AppSessionState(route=route), page)
