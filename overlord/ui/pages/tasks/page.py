from __future__ import annotations

import asyncio
import calendar
from datetime import date, datetime, timedelta
from typing import Callable

import flet as ft

from overlord.app.services import ApplicationServices
from overlord.modules.blockers.domain import BlockerType
from overlord.modules.cycles.domain import CycleStatus
from overlord.modules.projects.domain import Project
from overlord.modules.tasks.domain import Task, TaskBoardColumn, TaskLifecycle, board_column, is_scheduled_for_day
from overlord.ui.components.controls import checkbox, primary_button, search_field, secondary_button, select_field, selection_button, tertiary_button, text_field
from overlord.ui.components.feedback import empty_state, show_success
from overlord.ui.components.layout import card, page_container
from overlord.ui.components.tasks import (
    _date_value,
    _datetime_value,
    _project_id,
    _project_options,
    _time_value,
    build_quick_task_dialog,
    task_card,
    task_row,
)
from overlord.ui.components.task_workspace import build_tasks_workspace
from overlord.ui.design_system.icons import IconName, lucide_icon
from overlord.ui.design_system.tokens import ThemeTokens
from overlord.ui.state import AppSessionState, TaskFilterState
from overlord.ui.strings import format_date_with_year, format_month_year, format_weekday_name, ui_error, ui_text


def _status_label(value: str | None) -> str:
    return ui_text(f"lifecycle.{value}") if value else ui_text("tasks.status_unset")


def _status_reason(value: str | None) -> str:
    if value == "Changed in Task editor":
        return ui_text("tasks.reason.changed_editor")
    if value == "Completed":
        return ui_text("tasks.reason.completed")
    return value or ui_text("tasks.no_reason")


def build_task_editor_content(
    services: ApplicationServices,
    projects: tuple[Project, ...],
    task_id: int,
    tokens: ThemeTokens,
    on_saved: Callable[[], None],
    on_changed: Callable[[], None],
    close: Callable[[], None],
    report_error,
) -> ft.Control:
    data = services.tasks.get_editor.execute(task_id)
    task = data.task
    project = select_field(
        tokens,
        label=ui_text("tasks.field_project"),
        value=str(task.project_id) if task.project_id is not None else "none",
        options=_project_options(projects),
    )
    title = text_field(tokens, label=ui_text("tasks.field_title"), value=task.title)
    description = text_field(tokens, label=ui_text("tasks.field_description"), value=task.description or "", multiline=True, min_lines=2, max_lines=4)
    definition = text_field(tokens, label=ui_text("tasks.field_definition"), value=task.definition_of_done or "", multiline=True, min_lines=2, max_lines=4)
    next_action = text_field(tokens, label=ui_text("tasks.field_next_action"), value=task.next_action or "")
    estimate = text_field(tokens, label=ui_text("tasks.field_estimate"), value=str(task.estimate_minutes or ""), keyboard_type=ft.KeyboardType.NUMBER)
    start_date = text_field(tokens, label=ui_text("tasks.field_start_date"), value=task.schedule_start_date.isoformat() if task.schedule_start_date else "", hint_text="YYYY-MM-DD")
    start_time = text_field(tokens, label=ui_text("tasks.field_start_time"), value=task.schedule_start_time.strftime("%H:%M") if task.schedule_start_time else "", hint_text="HH:MM")
    end_date = text_field(tokens, label=ui_text("tasks.field_end_date"), value=task.schedule_end_date.isoformat() if task.schedule_end_date else "", hint_text="YYYY-MM-DD")
    end_time = text_field(tokens, label=ui_text("tasks.field_end_time"), value=task.schedule_end_time.strftime("%H:%M") if task.schedule_end_time else "", hint_text="HH:MM")
    deadline = text_field(tokens, label=ui_text("tasks.field_deadline"), value=task.deadline_at.strftime("%Y-%m-%d %H:%M") if task.deadline_at else "", hint_text="YYYY-MM-DD HH:MM")
    importance = checkbox(tokens, label=ui_text("tasks.important"), value=task.importance is True)
    urgency = checkbox(tokens, label=ui_text("tasks.urgent"), value=task.urgency is True)
    cycles = services.cycles.search_cycles.execute()
    cycle_fields = {
        cycle.id: checkbox(
            tokens,
            label=cycle.title,
            value=cycle.id in data.connected_cycle_ids,
            disabled=cycle.status is CycleStatus.ARCHIVED,
        )
        for cycle in cycles
    }
    message = ft.Text("", color=tokens.error.text, size=tokens.text_small)

    def save(_event) -> None:
        title.error = None
        estimate.error = None
        try:
            minutes = int(estimate.value) if (estimate.value or "").strip() else None
            services.tasks.update_task.execute(
                task.id,
                project_id=_project_id(project.value),
                title=title.value or "",
                description=description.value or "",
                definition_of_done=definition.value or None,
                next_action=next_action.value or None,
                importance=True if importance.value else None,
                urgency=True if urgency.value else None,
                estimate_minutes=minutes,
                schedule_start_date=_date_value(start_date.value) if (start_date.value or "").strip() else None,
                schedule_start_time=_time_value(start_time.value) if (start_time.value or "").strip() else None,
                schedule_end_date=_date_value(end_date.value) if (end_date.value or "").strip() else None,
                schedule_end_time=_time_value(end_time.value) if (end_time.value or "").strip() else None,
                deadline_at=_datetime_value(deadline.value) if (deadline.value or "").strip() else None,
                cycle_ids=tuple(cycle_id for cycle_id, field in cycle_fields.items() if field.value),
            )
            on_saved()
        except Exception as error:
            raw = str(error)
            text = ui_error(error)
            if "title" in raw.lower():
                title.error = text
                title.update()
            elif "estimate" in raw.lower():
                estimate.error = text
                estimate.update()
            else:
                message.value = text
                message.update()

    blocker_type = select_field(
        tokens,
        label=ui_text("tasks.field_blocker_type"),
        value=BlockerType.OTHER.value,
        options=[ft.DropdownOption(value.value, ui_text(f"blocker.type.{value.value}")) for value in BlockerType],
    )
    blocker_description = text_field(tokens, label=ui_text("tasks.field_blocker_description"), expand=True)

    def add_blocker(_event) -> None:
        try:
            services.tasks.open_blocker.execute(task.id, BlockerType(blocker_type.value), blocker_description.value or "")
            on_changed()
        except Exception as error:
            blocker_description.error = ui_error(error)
            blocker_description.update()

    blocker_controls: list[ft.Control] = [
        ft.ResponsiveRow(
            [
                ft.Container(blocker_type, col={"sm": 12, "md": 4}),
                ft.Container(blocker_description, col={"sm": 12, "md": 6}),
                ft.Container(primary_button(ui_text("tasks.open_blocker"), tokens, on_click=add_blocker), col={"sm": 12, "md": 2}),
            ],
            spacing=tokens.space_2,
            run_spacing=tokens.space_2,
        )
    ]
    for blocker in data.blockers:
        resolution = text_field(tokens, label=ui_text("tasks.resolution"), expand=True)
        if blocker.resolved_at:
            blocker_controls.append(ft.Text(f"{ui_text('tasks.resolved')} · {blocker.description} · {blocker.resolution}", color=tokens.text_muted))
        else:
            blocker_controls.append(
                ft.Container(
                    ft.Column(
                        [
                            ft.Text(f"{ui_text(f'blocker.type.{blocker.type.value}')} · {blocker.description}", color=tokens.blocker.text),
                            ft.Row(
                                [
                                    resolution,
                                    primary_button(
                                        ui_text("tasks.resolve"),
                                        tokens,
                                        on_click=lambda _e, blocker_id=blocker.id, field=resolution: _resolve_blocker(
                                            services, blocker_id, field.value or "", on_changed, report_error
                                        ),
                                    ),
                                ]
                            ),
                        ]
                    ),
                    bgcolor=tokens.blocker.background,
                    border_radius=tokens.radius_medium,
                    padding=tokens.space_3,
                )
            )
    status_history = [
        ft.Text(
            f"{_status_label(entry.from_status)} → {_status_label(entry.to_status)} · {_status_reason(entry.reason)}",
            color=tokens.text_muted,
            size=tokens.text_small,
        )
        for entry in data.status_history
    ]
    return ft.Column(
        [
            project,
            title,
            description,
            definition,
            next_action,
            ft.ResponsiveRow(
                [
                    ft.Container(start_date, col={"sm": 12, "md": 4}),
                    ft.Container(start_time, col={"sm": 6, "md": 2}),
                    ft.Container(end_date, col={"sm": 12, "md": 4}),
                    ft.Container(end_time, col={"sm": 6, "md": 2}),
                ]
            ),
            deadline,
            ft.Text(ui_text("tasks.connections_section"), color=tokens.text_secondary, weight=ft.FontWeight.W_600),
            ft.Row(list(cycle_fields.values()), wrap=True, spacing=tokens.space_3)
            if cycle_fields
            else ft.Text(ui_text("tasks.no_cycles"), color=tokens.text_muted, size=tokens.text_small),
            ft.ResponsiveRow(
                [
                    ft.Container(estimate, col={"sm": 12, "md": 4}),
                    ft.Container(importance, col={"sm": 6, "md": 4}),
                    ft.Container(urgency, col={"sm": 6, "md": 4}),
                ]
            ),
            message,
            ft.Text(ui_text("tasks.blockers_section"), color=tokens.text_secondary, weight=ft.FontWeight.W_600),
            *blocker_controls,
            ft.Text(ui_text("tasks.status_history"), color=tokens.text_secondary, weight=ft.FontWeight.W_600),
            *(status_history or [ft.Text(ui_text("tasks.no_status_history"), color=tokens.text_muted)]),
            ft.Row(
                [
                    primary_button(ui_text("tasks.save"), tokens, on_click=save),
                    ft.TextButton(ui_text("tasks.close"), on_click=lambda _e: close()),
                ]
            ),
        ],
        spacing=tokens.space_3,
        tight=True,
    )


def _resolve_blocker(services, blocker_id, resolution, refresh, report_error) -> None:
    try:
        services.tasks.resolve_blocker.execute(blocker_id, resolution)
        refresh()
    except Exception as error:
        report_error(ui_error(error))


def _build_foundation_tasks(
    services: ApplicationServices,
    tokens: ThemeTokens,
    state: AppSessionState,
    refresh,
    report_error,
    page: ft.Page | None = None,
) -> ft.Control:
    projects = services.projects.list_projects.execute()
    filter_state = state.task_filters or TaskFilterState()
    state.task_filters = filter_state

    search = search_field(tokens, label=ui_text("tasks.search"), value=filter_state.search, expand=True)
    filter_project = select_field(
        tokens,
        searchable=True,
        label=ui_text("tasks.project_filter"),
        value=filter_state.project,
        options=[
            ft.DropdownOption("all", ui_text("tasks.project_all")),
            ft.DropdownOption("none", ui_text("tasks.no_project")),
            *[ft.DropdownOption(str(item.id), item.title) for item in projects],
        ],
    )
    lifecycle = select_field(
        tokens,
        label=ui_text("tasks.lifecycle"),
        value=filter_state.lifecycle,
        options=[
            ft.DropdownOption("all", ui_text("tasks.lifecycle_all")),
            *[ft.DropdownOption(value.value, ui_text(f"lifecycle.{value.value}")) for value in TaskLifecycle],
        ],
    )
    date_scope = select_field(
        tokens,
        label=ui_text("tasks.date_scope"),
        value=filter_state.date_scope,
        options=[
            ft.DropdownOption("any", ui_text("tasks.date_any")),
            ft.DropdownOption("today", ui_text("tasks.date_today")),
            ft.DropdownOption("this_week", ui_text("tasks.date_week")),
            ft.DropdownOption("overdue", ui_text("tasks.date_overdue")),
            ft.DropdownOption("unplanned", ui_text("tasks.date_unplanned")),
        ],
    )
    filter_importance = select_field(
        tokens,
        label=ui_text("tasks.importance"),
        value=filter_state.importance,
        options=[
            ft.DropdownOption("any", ui_text("tasks.any")),
            ft.DropdownOption("yes", ui_text("tasks.important")),
            ft.DropdownOption("no", ui_text("tasks.not_important")),
        ],
    )
    filter_urgency = select_field(
        tokens,
        label=ui_text("tasks.urgency"),
        value=filter_state.urgency,
        options=[
            ft.DropdownOption("any", ui_text("tasks.any")),
            ft.DropdownOption("yes", ui_text("tasks.urgent")),
            ft.DropdownOption("no", ui_text("tasks.not_urgent")),
        ],
    )
    attention_only = ft.Switch(label=ui_text("tasks.attention"), value=filter_state.attention_only)
    result_count = ft.Text("", color=tokens.text_muted, size=tokens.text_small)
    list_column = ft.Column(spacing=tokens.space_2)

    def remember_filters() -> None:
        filter_state.search = search.value or ""
        filter_state.project = filter_project.value or "all"
        filter_state.lifecycle = lifecycle.value or "all"
        filter_state.date_scope = date_scope.value or "any"
        filter_state.importance = filter_importance.value or "any"
        filter_state.urgency = filter_urgency.value or "any"
        filter_state.attention_only = bool(attention_only.value)

    def query_filters() -> dict[str, object]:
        remember_filters()
        filters: dict[str, object] = {"search": filter_state.search}
        if filter_state.project == "none":
            filters["without_project"] = True
        elif filter_state.project != "all":
            filters["project_id"] = int(filter_state.project)
        if filter_state.lifecycle != "all":
            filters["lifecycle"] = TaskLifecycle(filter_state.lifecycle)
        if filter_state.date_scope != "any":
            filters["date_scope"] = filter_state.date_scope
            filters["reference_date"] = date.today()
        if filter_state.importance != "any":
            filters["importance"] = filter_state.importance == "yes"
        if filter_state.urgency != "any":
            filters["urgency"] = filter_state.urgency == "yes"
        if filter_state.attention_only:
            filters["attention_only"] = True
        return filters

    def close_dialog() -> None:
        if page is not None:
            page.pop_dialog()

    def render_list(_event=None, *, update: bool = False) -> None:
        matches = services.tasks.list_tasks.execute(**query_filters())
        task_controls: list[ft.Control] = []
        for item in matches:
            def edit(_event, task_id=item.task.id) -> None:
                open_editor(task_id)

            def complete(_event, task_id=item.task.id) -> None:
                try:
                    services.tasks.complete_task.execute(task_id)
                    render_list(update=True)
                except Exception as error:
                    report_error(ui_error(error))

            task_controls.append(task_row(item, tokens, on_complete=complete, on_edit=edit))
        list_column.controls = task_controls or [empty_state(ui_text("tasks.empty"), tokens)]
        result_count.value = ui_text("tasks.results_count", count=len(matches))
        if update:
            list_column.update()
            result_count.update()

    def created(_task: Task) -> None:
        close_dialog()
        render_list(update=True)
        if page is not None:
            show_success(page, tokens, ui_text("tasks.created"))

    def open_quick_task(_event) -> None:
        if page is None:
            return
        page.show_dialog(build_quick_task_dialog(services, projects, tokens, created, close_dialog))

    def open_editor(task_id: int) -> None:
        if page is None:
            return

        def saved() -> None:
            close_dialog()
            render_list(update=True)
            show_success(page, tokens, ui_text("tasks.updated"))

        def changed() -> None:
            close_dialog()
            render_list(update=True)
            open_editor(task_id)

        dialog = ft.AlertDialog(
            modal=True,
            title=ui_text("tasks.edit_title"),
            content=ft.Container(
                build_task_editor_content(
                    services,
                    projects,
                    task_id,
                    tokens,
                    saved,
                    changed,
                    close_dialog,
                    report_error,
                ),
                width=680,
            ),
            bgcolor=tokens.surface_elevated,
            scrollable=True,
        )
        page.show_dialog(dialog)

    def apply_filters(_event) -> None:
        try:
            render_list(update=True)
        except Exception as error:
            report_error(ui_error(error))

    def reset_filters(_event) -> None:
        search.value = ""
        filter_project.value = "all"
        lifecycle.value = "all"
        date_scope.value = "any"
        filter_importance.value = "any"
        filter_urgency.value = "any"
        attention_only.value = False
        for control in (search, filter_project, lifecycle, date_scope, filter_importance, filter_urgency, attention_only):
            control.update()
        render_list(update=True)

    search.on_submit = apply_filters
    render_list()
    content = page_container(
        ui_text("tasks.title"),
        [
            card(
                ui_text("tasks.results"),
                [
                    ft.ResponsiveRow(
                        [
                            ft.Container(search, col={"sm": 12, "lg": 5}),
                            ft.Container(filter_project, col={"sm": 12, "md": 6, "lg": 3}),
                            ft.Container(lifecycle, col={"sm": 12, "md": 6, "lg": 4}),
                            ft.Container(date_scope, col={"sm": 12, "md": 4}),
                            ft.Container(filter_importance, col={"sm": 12, "md": 4}),
                            ft.Container(filter_urgency, col={"sm": 12, "md": 4}),
                        ],
                        spacing=tokens.space_3,
                        run_spacing=tokens.space_3,
                    ),
                    ft.ResponsiveRow(
                        [
                            ft.Container(attention_only, col={"sm": 12, "md": 6}),
                            ft.Container(
                                ft.Row(
                                    [
                                        ft.TextButton(ui_text("tasks.reset_filters"), on_click=reset_filters),
                                        primary_button(ui_text("tasks.apply_filters"), tokens, on_click=apply_filters),
                                    ],
                                    alignment=ft.MainAxisAlignment.END,
                                ),
                                col={"sm": 12, "md": 6},
                            ),
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
        actions=[
            primary_button(
                ft.Row(
                    [
                        lucide_icon(IconName.PLUS, color=tokens.on_accent, size=tokens.icon_small, label=ui_text("tasks.quick_action")),
                        ft.Text(ui_text("tasks.quick_action"), color=tokens.on_accent),
                    ],
                    spacing=tokens.space_2,
                    tight=True,
                ),
                tokens,
                on_click=open_quick_task,
            )
        ],
        content_spacing=tokens.space_5,
        page_id="tasks",
    )
    if state.selected_task_id is not None and page is not None and hasattr(page, "run_task"):
        selected_task_id = state.selected_task_id
        state.selected_task_id = None

        async def open_selected_editor() -> None:
            await asyncio.sleep(0)
            open_editor(selected_task_id)

        page.run_task(open_selected_editor)
    return content


def build_tasks(
    services: ApplicationServices,
    tokens: ThemeTokens,
    state: AppSessionState,
    refresh,
    report_error,
    page: ft.Page | None = None,
) -> ft.Control:
    return build_tasks_workspace(
        services,
        tokens,
        state,
        refresh,
        report_error,
        page,
        build_task_editor_content,
    )
