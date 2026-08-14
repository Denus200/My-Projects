from __future__ import annotations

from typing import Callable

import flet as ft

from overlord.app.services import ApplicationServices
from overlord.modules.blockers.domain import BlockerType
from overlord.modules.cycles.domain import CycleStatus
from overlord.modules.projects.domain import Project
from overlord.modules.validation import FieldValidationError
from overlord.ui.components.controls import checkbox, primary_button, select_field, text_field
from overlord.ui.components.task_form_values import (
    datetime_value,
    project_id,
    project_options,
    strict_date_value,
    time_value,
)
from overlord.ui.components.task_workspace import build_tasks_workspace
from overlord.ui.design_system.tokens import ThemeTokens
from overlord.ui.state import AppSessionState
from overlord.ui.strings import ui_error, ui_text


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
        options=project_options(projects),
    )
    title = text_field(tokens, label=ui_text("tasks.field_title"), value=task.title)
    description = text_field(
        tokens,
        label=ui_text("tasks.field_description"),
        value=task.description or "",
        multiline=True,
        min_lines=2,
        max_lines=4,
    )
    definition = text_field(
        tokens,
        label=ui_text("tasks.field_definition"),
        value=task.definition_of_done or "",
        multiline=True,
        min_lines=2,
        max_lines=4,
    )
    next_action = text_field(tokens, label=ui_text("tasks.field_next_action"), value=task.next_action or "")
    estimate = text_field(
        tokens,
        label=ui_text("tasks.field_estimate"),
        value=str(task.estimate_minutes or ""),
        keyboard_type=ft.KeyboardType.NUMBER,
    )
    start_date = text_field(
        tokens,
        label=ui_text("tasks.field_start_date"),
        value=task.schedule_start_date.isoformat() if task.schedule_start_date else "",
        hint_text="YYYY-MM-DD",
    )
    start_time = text_field(
        tokens,
        label=ui_text("tasks.field_start_time"),
        value=task.schedule_start_time.strftime("%H:%M") if task.schedule_start_time else "",
        hint_text="HH:MM",
    )
    end_date = text_field(
        tokens,
        label=ui_text("tasks.field_end_date"),
        value=task.schedule_end_date.isoformat() if task.schedule_end_date else "",
        hint_text="YYYY-MM-DD",
    )
    end_time = text_field(
        tokens,
        label=ui_text("tasks.field_end_time"),
        value=task.schedule_end_time.strftime("%H:%M") if task.schedule_end_time else "",
        hint_text="HH:MM",
    )
    deadline = text_field(
        tokens,
        label=ui_text("tasks.field_deadline"),
        value=task.deadline_at.strftime("%Y-%m-%d %H:%M") if task.deadline_at else "",
        hint_text="YYYY-MM-DD HH:MM",
    )
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
                project_id=project_id(project.value),
                title=title.value or "",
                description=description.value or "",
                definition_of_done=definition.value or None,
                next_action=next_action.value or None,
                importance=True if importance.value else None,
                urgency=True if urgency.value else None,
                estimate_minutes=minutes,
                schedule_start_date=(
                    strict_date_value(start_date.value, field="start_date")
                    if (start_date.value or "").strip()
                    else None
                ),
                schedule_start_time=(
                    time_value(start_time.value, field="start_time")
                    if (start_time.value or "").strip()
                    else None
                ),
                schedule_end_date=(
                    strict_date_value(end_date.value, field="end_date")
                    if (end_date.value or "").strip()
                    else None
                ),
                schedule_end_time=(
                    time_value(end_time.value, field="end_time")
                    if (end_time.value or "").strip()
                    else None
                ),
                deadline_at=(
                    datetime_value(deadline.value, field="deadline")
                    if (deadline.value or "").strip()
                    else None
                ),
                cycle_ids=tuple(cycle_id for cycle_id, field in cycle_fields.items() if field.value),
            )
        except Exception as error:
            text = ui_error(error)
            field = error.field if isinstance(error, FieldValidationError) else None
            if field == "title":
                title.error = text
                title.update()
            elif field == "estimate":
                estimate.error = text
                estimate.update()
            else:
                message.value = text
                message.update()
        else:
            on_saved()

    blocker_type = select_field(
        tokens,
        label=ui_text("tasks.field_blocker_type"),
        value=BlockerType.OTHER.value,
        options=[ft.DropdownOption(value.value, ui_text(f"blocker.type.{value.value}")) for value in BlockerType],
    )
    blocker_description = text_field(tokens, label=ui_text("tasks.field_blocker_description"), expand=True)

    def add_blocker(_event) -> None:
        try:
            services.tasks.open_blocker.execute(
                task.id,
                BlockerType(blocker_type.value),
                blocker_description.value or "",
            )
        except Exception as error:
            blocker_description.error = ui_error(error)
            blocker_description.update()
        else:
            on_changed()

    blocker_controls: list[ft.Control] = [
        ft.ResponsiveRow(
            [
                ft.Container(blocker_type, col={"sm": 12, "md": 4}),
                ft.Container(blocker_description, col={"sm": 12, "md": 6}),
                ft.Container(
                    primary_button(ui_text("tasks.open_blocker"), tokens, on_click=add_blocker),
                    col={"sm": 12, "md": 2},
                ),
            ],
            spacing=tokens.space_2,
            run_spacing=tokens.space_2,
        )
    ]
    for blocker in data.blockers:
        resolution = text_field(tokens, label=ui_text("tasks.resolution"), expand=True)
        if blocker.resolved_at:
            blocker_controls.append(
                ft.Text(
                    f"{ui_text('tasks.resolved')} · {blocker.description} · {blocker.resolution}",
                    color=tokens.text_muted,
                )
            )
        else:
            blocker_controls.append(
                ft.Container(
                    ft.Column(
                        [
                            ft.Text(
                                f"{ui_text(f'blocker.type.{blocker.type.value}')} · {blocker.description}",
                                color=tokens.blocker.text,
                            ),
                            ft.Row(
                                [
                                    resolution,
                                    primary_button(
                                        ui_text("tasks.resolve"),
                                        tokens,
                                        on_click=lambda _e, blocker_id=blocker.id, field=resolution: _resolve_blocker(
                                            services,
                                            blocker_id,
                                            field.value or "",
                                            on_changed,
                                            report_error,
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
