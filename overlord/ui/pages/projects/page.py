from __future__ import annotations

from datetime import date
from typing import Callable

import flet as ft

from overlord.app.read_models import TaskListItem
from overlord.app.services import ApplicationServices
from overlord.modules.projects.read_models import ProjectDetail
from overlord.modules.projects.domain import Project, ProjectStatus
from overlord.modules.tasks.domain import Task, TaskLifecycle
from overlord.modules.validation import FieldValidationError
from overlord.ui.components.controls import primary_button, search_field, secondary_button, select_field, text_field
from overlord.ui.components.dialogs import close_dialog, dialog_footer
from overlord.ui.components.feedback import empty_state, show_success
from overlord.ui.components.layout import card, page_container
from overlord.ui.components.status import state_chip
from overlord.ui.components.tasks import build_quick_task_dialog, task_row
from overlord.ui.design_system.icons import IconName, lucide_icon
from overlord.ui.design_system.tokens import StateColors, ThemeTokens
from overlord.ui.state import AppSessionState, ProjectFilterState
from overlord.ui.strings import format_short_date, ui_error, ui_text


def _status_label(status: ProjectStatus) -> str:
    return ui_text(f"projects.status.{status.value}")


def _status_color(status: ProjectStatus, tokens: ThemeTokens) -> StateColors:
    return {
        ProjectStatus.ACTIVE: tokens.success,
        ProjectStatus.ON_HOLD: tokens.warning,
        ProjectStatus.COMPLETED: tokens.info,
        ProjectStatus.ARCHIVED: tokens.neutral,
    }[status]


def _current_week(detail: ProjectDetail) -> str:
    cycle = detail.active_cycle
    if cycle is None:
        return ui_text("projects.not_connected")
    offset = (date.today() - cycle.start_date).days // 7 + 1
    week = max(1, min(cycle.length_weeks, offset))
    return ui_text("projects.cycle_context", title=cycle.title, week=week, length=cycle.length_weeks)


def _progress_controls(detail: ProjectDetail, tokens: ThemeTokens) -> list[ft.Control]:
    if detail.progress is None:
        return [ft.Text(ui_text("projects.progress_unavailable"), color=tokens.text_muted)]
    percent = round(detail.progress * 100)
    return [
        ft.Row(
            [
                ft.Text(f"{percent}%", color=tokens.text_primary, weight=ft.FontWeight.W_600),
                ft.Text(
                    ui_text(
                        "projects.progress_count",
                        completed=detail.completed_task_count,
                        total=detail.eligible_task_count,
                    ),
                    color=tokens.text_muted,
                    size=tokens.text_small,
                ),
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        ),
        ft.ProgressBar(
            value=detail.progress,
            color=tokens.accent_primary,
            bgcolor=tokens.border_default,
            border_radius=tokens.radius_pill,
        ),
    ]


def _context_line(label: str, value: str, tokens: ThemeTokens) -> ft.Column:
    return ft.Column(
        [
            ft.Text(label, color=tokens.text_muted, size=tokens.text_small),
            ft.Text(value, color=tokens.text_primary, max_lines=2),
        ],
        spacing=tokens.space_1,
        tight=True,
    )


def _project_summary_card(
    detail: ProjectDetail,
    tokens: ThemeTokens,
    navigate: Callable[[str], None],
) -> ft.Container:
    project = detail.project
    milestone = detail.current_milestone.title if detail.current_milestone else ui_text("projects.no_milestone")
    next_action = detail.next_action or ui_text("projects.no_next_action")
    cycle = _current_week(detail)
    blocker_text = (
        (
            ui_text("projects.blocker_one")
            if detail.open_blocker_count == 1
            else ui_text("projects.blocker_count", count=detail.open_blocker_count)
        )
        if detail.open_blocker_count
        else ui_text("projects.no_blockers")
    )
    return ft.Container(
        ft.Column(
            [
                ft.Row(
                    [
                        ft.Column(
                            [
                                ft.Text(project.title, color=tokens.text_primary, size=tokens.text_emphasis, weight=ft.FontWeight.W_600),
                                ft.Text(project.stage_label or ui_text("projects.no_stage"), color=tokens.text_secondary, size=tokens.text_small),
                            ],
                            spacing=tokens.space_1,
                            expand=True,
                        ),
                        state_chip(_status_label(project.status), _status_color(project.status, tokens), tokens),
                    ],
                    vertical_alignment=ft.CrossAxisAlignment.START,
                ),
                ft.ResponsiveRow(
                    [
                        ft.Container(_context_line(ui_text("projects.current_milestone"), milestone, tokens), col={"sm": 12, "md": 6}),
                        ft.Container(_context_line(ui_text("projects.next_action"), next_action, tokens), col={"sm": 12, "md": 6}),
                    ],
                    spacing=tokens.space_3,
                    run_spacing=tokens.space_2,
                ),
                *_progress_controls(detail, tokens),
                ft.Row(
                    [
                        ft.Text(ui_text("projects.open_tasks", count=detail.open_task_count), color=tokens.text_muted, size=tokens.text_small),
                        ft.Text(blocker_text, color=tokens.blocker.text if detail.open_blocker_count else tokens.text_muted, size=tokens.text_small),
                        ft.Text(cycle, color=tokens.text_muted, size=tokens.text_small, expand=True),
                        ft.TextButton(ui_text("projects.open"), on_click=lambda _e: navigate(f"/projects/{project.id}")),
                    ],
                    spacing=tokens.space_3,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
            ],
            spacing=tokens.space_3,
        ),
        bgcolor=tokens.surface_inner,
        border=ft.Border.all(tokens.border_width, tokens.border_default),
        border_radius=tokens.radius_medium,
        padding=tokens.space_4,
    )


def _new_project_dialog(
    services: ApplicationServices,
    tokens: ThemeTokens,
    on_created: Callable[[Project], None],
    close: Callable[[], None],
) -> ft.AlertDialog:
    title = text_field(tokens, label=ui_text("projects.field_title"), autofocus=True)
    description = text_field(
        tokens,
        label=ui_text("projects.field_description"),
        multiline=True,
        min_lines=2,
        max_lines=4,
    )
    message = ft.Text("", color=tokens.error.text, size=tokens.text_small)

    def create(_event) -> None:
        title.error = None
        message.value = ""
        try:
            project = services.projects.create_project.execute(title.value or "", description.value or "")
            on_created(project)
        except Exception as error:
            text = ui_error(error)
            if isinstance(error, FieldValidationError) and error.field == "title":
                title.error = text
                title.update()
            else:
                message.value = text
                message.update()

    return ft.AlertDialog(
        modal=True,
        title=ui_text("projects.new_title"),
        content=ft.Container(
            ft.Column(
                [
                    ft.Text(ui_text("projects.new_description"), color=tokens.text_secondary),
                    title,
                    description,
                    message,
                ],
                spacing=tokens.space_3,
                tight=True,
            ),
            width=540,
        ),
        actions=dialog_footer(
            ui_text("projects.cancel"),
            ui_text("projects.create"),
            lambda _e: close(),
            create,
            tokens,
        ),
        bgcolor=tokens.surface_elevated,
    )


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

    state = state or AppSessionState(route=route)
    filter_state = state.project_filters or ProjectFilterState()
    state.project_filters = filter_state
    search = search_field(tokens, label=ui_text("projects.search"), value=filter_state.search, expand=True)
    status_filter = select_field(
        tokens,
        label=ui_text("projects.status_filter"),
        value=filter_state.status,
        options=[
            ft.DropdownOption("all", ui_text("projects.status_all")),
            *[ft.DropdownOption(value.value, _status_label(value)) for value in ProjectStatus],
        ],
    )
    result_count = ft.Text("", color=tokens.text_muted, size=tokens.text_small)
    list_column = ft.Column(spacing=tokens.space_3)

    def remember_filters() -> None:
        filter_state.search = search.value or ""
        filter_state.status = status_filter.value or "all"

    def render_list(_event=None, *, update: bool = False) -> None:
        remember_filters()
        selected = None if filter_state.status == "all" else ProjectStatus(filter_state.status)
        projects = services.projects.list_summaries.execute(selected, filter_state.search)
        if projects:
            list_column.controls = [_project_summary_card(project, tokens, navigate) for project in projects]
        elif filter_state.search or filter_state.status != "all":
            list_column.controls = [
                empty_state(
                    ui_text("projects.empty"),
                    tokens,
                    ft.TextButton(ui_text("projects.clear_filters"), on_click=clear_filters),
                )
            ]
        else:
            list_column.controls = [
                empty_state(
                    ui_text("projects.none_description"),
                    tokens,
                    primary_button(ui_text("projects.new_action"), tokens, on_click=open_new_project),
                )
            ]
        result_count.value = ui_text("projects.results_count", count=len(projects))
        if update:
            list_column.update()
            result_count.update()

    def apply_filters(_event) -> None:
        try:
            render_list(update=True)
        except Exception as error:
            report_error(ui_error(error))

    def clear_filters(_event) -> None:
        search.value = ""
        status_filter.value = "all"
        search.update()
        status_filter.update()
        render_list(update=True)

    def created(_project: Project) -> None:
        close_dialog(page)
        render_list(update=True)
        show_success(page, tokens, ui_text("projects.created"))

    def open_new_project(_event) -> None:
        if page is not None:
            page.show_dialog(_new_project_dialog(services, tokens, created, lambda: close_dialog(page)))

    search.on_submit = apply_filters
    status_filter.on_select = apply_filters
    render_list()
    return page_container(
        ui_text("projects.title"),
        [
            card(
                ui_text("projects.browse"),
                [
                    ft.ResponsiveRow(
                        [
                            ft.Container(search, col={"sm": 12, "md": 7}),
                            ft.Container(status_filter, col={"sm": 12, "md": 3}),
                            ft.Container(ft.TextButton(ui_text("projects.clear_filters"), on_click=clear_filters), col={"sm": 12, "md": 2}),
                        ],
                        spacing=tokens.space_3,
                        run_spacing=tokens.space_2,
                    ),
                    result_count,
                    list_column,
                ],
                tokens,
            ),
        ],
        tokens,
        subtitle=ui_text("projects.subtitle"),
        actions=[
            primary_button(
                ft.Row(
                    [
                        lucide_icon(IconName.PLUS, color=tokens.on_accent, size=tokens.icon_small, label=ui_text("projects.new_action")),
                        ft.Text(ui_text("projects.new_action"), color=tokens.on_accent),
                    ],
                    spacing=tokens.space_2,
                    tight=True,
                ),
                tokens,
                on_click=open_new_project,
            )
        ],
        content_spacing=tokens.space_5,
        page_id="projects",
    )


def _task_matches(item: TaskListItem, value: str) -> bool:
    if value == "completed":
        return item.task.lifecycle_status is TaskLifecycle.COMPLETED
    if value == "blocked":
        return item.open_blockers > 0
    return item.task.lifecycle_status not in {TaskLifecycle.COMPLETED, TaskLifecycle.CANCELLED}


def _build_detail(services, tokens, route, navigate, refresh, report_error, page):
    try:
        project_id = int(route.rsplit("/", 1)[1])
        detail = services.projects.get_detail.execute(project_id)
    except Exception as error:
        return page_container(
            ui_text("projects.unavailable"),
            [
                secondary_button(ui_text("projects.back"), tokens, on_click=lambda _e: navigate("/projects")),
            ],
            tokens,
            subtitle=ui_error(error),
            page_id="projects",
        )
    project = detail.project
    all_projects = services.projects.list_projects.execute()
    tasks = services.tasks.list_tasks.execute(project_id=project.id)
    task_filter = select_field(
        tokens,
        label=ui_text("projects.task_filter"),
        value="open",
        options=[
            ft.DropdownOption("open", ui_text("projects.tasks_open")),
            ft.DropdownOption("completed", ui_text("projects.tasks_completed")),
            ft.DropdownOption("blocked", ui_text("projects.tasks_blocked")),
        ],
        width=190,
    )
    task_list = ft.Column(spacing=tokens.space_2)

    def complete(task_id: int):
        def action(_event) -> None:
            try:
                services.tasks.complete_task.execute(task_id)
                refresh()
            except Exception as error:
                report_error(ui_error(error))

        return action

    def render_tasks(_event=None, *, update: bool = False) -> None:
        matches = [item for item in tasks if _task_matches(item, task_filter.value or "open")]
        if matches:
            task_list.controls = [task_row(item, tokens, on_complete=complete(item.task.id)) for item in matches]
        elif not tasks:
            task_list.controls = [
                empty_state(
                    ui_text("projects.tasks_none"),
                    tokens,
                    primary_button(ui_text("projects.quick_task"), tokens, on_click=open_quick_task),
                )
            ]
        else:
            task_list.controls = [empty_state(ui_text("projects.tasks_empty_filter"), tokens)]
        if update:
            task_list.update()

    def quick_created(_task: Task) -> None:
        close_dialog(page)
        show_success(page, tokens, ui_text("tasks.created"))
        refresh()

    def open_quick_task(_event) -> None:
        if page is not None:
            page.show_dialog(
                build_quick_task_dialog(
                    services,
                    all_projects,
                    tokens,
                    quick_created,
                    lambda: close_dialog(page),
                    selected_project_id=project.id,
                    page=page,
                )
            )

    def open_lifecycle(_event) -> None:
        if page is None:
            return
        status = select_field(
            tokens,
            label=ui_text("projects.status_filter"),
            value=project.status.value,
            options=[ft.DropdownOption(value.value, _status_label(value)) for value in ProjectStatus],
        )
        message = ft.Text(ui_text("projects.lifecycle_note"), color=tokens.text_muted, size=tokens.text_small)

        def save(_save_event) -> None:
            try:
                services.projects.update_project.execute(project.id, status=ProjectStatus(status.value))
                close_dialog(page)
                show_success(page, tokens, ui_text("projects.updated"))
                refresh()
            except Exception as error:
                report_error(ui_error(error))

        page.show_dialog(
            ft.AlertDialog(
                modal=True,
                title=ui_text("projects.lifecycle_title"),
                content=ft.Container(ft.Column([status, message], spacing=tokens.space_3, tight=True), width=420),
                actions=[
                    ft.TextButton(ui_text("projects.cancel"), on_click=lambda _e: close_dialog(page)),
                    primary_button(ui_text("projects.save"), tokens, on_click=save),
                ],
                bgcolor=tokens.surface_elevated,
            )
        )

    task_filter.on_select = lambda event: render_tasks(event, update=True)
    render_tasks()
    milestone_value = detail.current_milestone.title if detail.current_milestone else ui_text("projects.no_milestone")
    next_action_value = detail.next_action or ui_text("projects.no_next_action")
    cycle_value = _current_week(detail)
    blocker_controls = [
        ft.Container(
            ft.Column(
                [
                    ft.Text(ui_text(f"blocker.type.{item.blocker.type.value}"), color=tokens.blocker.text, weight=ft.FontWeight.W_600),
                    ft.Text(item.blocker.description, color=tokens.text_primary),
                    ft.Text(
                        ui_text("projects.blocker_task", task=item.task_title, date=format_short_date(item.blocker.created_at.date())),
                        color=tokens.text_muted,
                        size=tokens.text_small,
                    ),
                ],
                spacing=tokens.space_1,
            ),
            bgcolor=tokens.blocker.background,
            border=ft.Border.all(tokens.border_width, tokens.blocker.main),
            border_radius=tokens.radius_medium,
            padding=tokens.space_3,
        )
        for item in detail.blockers
    ]
    milestone_controls: list[ft.Control] = [ft.Text(milestone_value, color=tokens.text_primary)]
    if detail.current_milestone:
        milestone_controls.extend(
            [
                ft.Text(
                    ui_text(f"cycles.milestone_status.{detail.current_milestone.status.value}"),
                    color=tokens.text_muted,
                    size=tokens.text_small,
                ),
                ft.Text(detail.current_milestone.definition_of_done, color=tokens.text_secondary, size=tokens.text_small),
            ]
        )
        if detail.current_milestone.target_date:
            milestone_controls.append(
                ft.Text(
                    ui_text("projects.milestone_target", date=format_short_date(detail.current_milestone.target_date)),
                    color=tokens.text_muted,
                    size=tokens.text_small,
                )
            )
    cycle_controls: list[ft.Control] = [
        ft.Text(cycle_value, color=tokens.text_primary),
        ft.Text(ui_text("projects.cycle_optional"), color=tokens.text_muted, size=tokens.text_small),
    ]
    if detail.active_cycle:
        cycle_controls.append(
            ft.TextButton(
                ui_text("projects.open_cycle"),
                on_click=lambda _e: navigate(f"/cycles/{detail.active_cycle.id}"),
            )
        )
    return page_container(
        project.title,
        [
            ft.ResponsiveRow(
                [
                    card(ui_text("projects.current_stage"), [ft.Text(project.stage_label or ui_text("projects.no_stage"), color=tokens.text_primary)], tokens, col={"sm": 12, "lg": 4}),
                    card(ui_text("projects.current_milestone"), milestone_controls, tokens, col={"sm": 12, "lg": 4}),
                    card(ui_text("projects.next_action"), [ft.Text(next_action_value, color=tokens.text_primary)], tokens, col={"sm": 12, "lg": 4}),
                ],
                spacing=tokens.space_4,
                run_spacing=tokens.space_4,
            ),
            ft.ResponsiveRow(
                [
                    card(
                        ui_text("projects.progress"),
                        [
                            *_progress_controls(detail, tokens),
                            ft.Text(ui_text("projects.open_tasks", count=detail.open_task_count), color=tokens.text_muted),
                            ft.Text(ui_text("projects.actual_time"), color=tokens.text_muted),
                        ],
                        tokens,
                        col={"sm": 12, "lg": 5},
                    ),
                    card(
                        ui_text("projects.cycle"),
                        cycle_controls,
                        tokens,
                        col={"sm": 12, "lg": 7},
                    ),
                ],
                spacing=tokens.space_4,
                run_spacing=tokens.space_4,
            ),
            card(
                ui_text("projects.blockers_title"),
                blocker_controls or [empty_state(ui_text("projects.blockers_empty"), tokens)],
                tokens,
            ),
            card(
                ui_text("projects.tasks_title"),
                [
                    ft.Row(
                        [
                            task_filter,
                            ft.Container(expand=True),
                            primary_button(
                                ft.Row(
                                    [
                                        lucide_icon(IconName.PLUS, color=tokens.on_accent, size=tokens.icon_small, label=ui_text("projects.quick_task")),
                                        ft.Text(ui_text("projects.quick_task"), color=tokens.on_accent),
                                    ],
                                    spacing=tokens.space_2,
                                    tight=True,
                                ),
                                tokens,
                                on_click=open_quick_task,
                            ),
                        ],
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    task_list,
                ],
                tokens,
            ),
        ],
        tokens,
        subtitle=project.description or ui_text("projects.detail_subtitle"),
        actions=[
            state_chip(_status_label(project.status), _status_color(project.status, tokens), tokens),
            ft.TextButton(ui_text("projects.more"), on_click=open_lifecycle),
            ft.TextButton(ui_text("projects.back"), on_click=lambda _e: navigate("/projects")),
        ],
        content_spacing=tokens.space_5,
        page_id="projects",
    )
