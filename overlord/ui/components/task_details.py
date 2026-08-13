from __future__ import annotations

from datetime import date, datetime, time
from typing import Callable

import flet as ft

from overlord.app.services import ApplicationServices
from overlord.modules.projects.domain import Project
from overlord.modules.tasks.domain import TaskLifecycle
from overlord.ui.components.controls import checkbox, choice_chip, primary_button, secondary_button, select_field, text_field
from overlord.ui.components.tasks import _display_date, _flexible_date_value, _project_id, _project_options, _time_value
from overlord.ui.design_system.icons import IconName, lucide_icon
from overlord.ui.design_system.tokens import ThemeTokens
from overlord.ui.strings import ui_error, ui_text


def _deadline_display(value: datetime | None) -> str:
    if value is None:
        return ""
    return value.strftime("%d.%m.%Y %H:%M")


def _deadline_value(value: str) -> datetime | None:
    clean = value.strip()
    if not clean:
        return None
    parts = clean.rsplit(" ", 1)
    selected_date = _flexible_date_value(parts[0])
    selected_time = _time_value(parts[1]) if len(parts) == 2 else time.max
    return datetime.combine(selected_date, selected_time)


def build_task_details_dialog(
    services: ApplicationServices,
    projects: tuple[Project, ...],
    task_id: int,
    day: date,
    tokens: ThemeTokens,
    on_saved: Callable[[], None],
    close: Callable[[], None],
    report_error,
) -> ft.AlertDialog:
    task = services.tasks.get_editor.execute(task_id).task
    title = text_field(tokens, label=ui_text("tasks.field_title"), value=task.title, autofocus=True)
    description = text_field(
        tokens,
        label=ui_text("tasks.field_description"),
        value=task.description or "",
        multiline=True,
        min_lines=3,
        max_lines=5,
    )
    project = select_field(
        tokens,
        label=ui_text("tasks.field_project"),
        value=str(task.project_id) if task.project_id is not None else "none",
        options=_project_options(projects),
    )
    scheduled_date = text_field(
        tokens,
        label=ui_text("tasks.field_start_date"),
        value=_display_date(task.schedule_start_date) if task.schedule_start_date else "",
        hint_text=ui_text("tasks.date_hint"),
    )
    scheduled_time = text_field(
        tokens,
        label=ui_text("tasks.field_start_time"),
        value=task.schedule_start_time.strftime("%H:%M") if task.schedule_start_time else "",
        hint_text="HH:MM",
    )
    deadline = text_field(
        tokens,
        label=ui_text("tasks.field_deadline"),
        value=_deadline_display(task.deadline_at),
        hint_text=f"{ui_text('tasks.date_hint')} HH:MM",
    )
    estimate = text_field(
        tokens,
        label=ui_text("tasks.field_estimate"),
        value=str(task.estimate_minutes or ""),
        keyboard_type=ft.KeyboardType.NUMBER,
    )
    importance = choice_chip(
        ui_text("tasks.important"),
        tokens,
        selected=task.importance is True,
        on_select=lambda _event: None,
    )
    urgency = choice_chip(
        ui_text("tasks.urgent"),
        tokens,
        selected=task.urgency is True,
        on_select=lambda _event: None,
    )
    completed = checkbox(
        tokens,
        label=ui_text("tasks.completion_state"),
        value=task.lifecycle_status is TaskLifecycle.COMPLETED,
    )
    message = ft.Text("", color=tokens.error.text, size=tokens.text_small)

    def save(_event) -> None:
        title.error = None
        scheduled_date.error = None
        scheduled_time.error = None
        deadline.error = None
        estimate.error = None
        message.value = ""
        try:
            minutes = int(estimate.value) if (estimate.value or "").strip() else None
            chosen_date = _flexible_date_value(scheduled_date.value or "") if (scheduled_date.value or "").strip() else None
            chosen_time = _time_value(scheduled_time.value or "") if (scheduled_time.value or "").strip() else None
            services.tasks.update_task.execute(
                task.id,
                project_id=_project_id(project.value),
                title=title.value or "",
                description=description.value or "",
                schedule_start_date=chosen_date,
                schedule_start_time=chosen_time,
                schedule_end_date=None if chosen_date != task.schedule_start_date else task.schedule_end_date,
                schedule_end_time=None if chosen_date != task.schedule_start_date else task.schedule_end_time,
                deadline_at=_deadline_value(deadline.value or ""),
                estimate_minutes=minutes,
                importance=True if importance.selected else None,
                urgency=True if urgency.selected else None,
            )
            was_completed = task.lifecycle_status is TaskLifecycle.COMPLETED
            if bool(completed.value) != was_completed:
                updated = services.tasks.get_editor.execute(task.id).task
                if updated.schedule_start_date and updated.schedule_start_date <= day <= (updated.schedule_end_date or updated.schedule_start_date):
                    services.tasks.toggle_completion_for_day.execute(task.id, day)
                else:
                    services.tasks.change_lifecycle.execute(
                        task.id,
                        TaskLifecycle.COMPLETED if completed.value else TaskLifecycle.PLANNED,
                        "Changed in Task Details",
                    )
            on_saved()
        except Exception as error:
            raw = str(error).lower()
            text = ui_error(error)
            if "title" in raw:
                title.error = text
                title.update()
            elif "estimate" in raw:
                estimate.error = text
                estimate.update()
            elif "time" in raw:
                scheduled_time.error = text
                scheduled_time.update()
            elif "date" in raw or "deadline" in raw:
                deadline.error = text
                deadline.update()
            else:
                message.value = text
                message.update()
                report_error(text)

    close_button = ft.IconButton(
        icon=lucide_icon(
            IconName.CLOSE,
            color=tokens.text_secondary,
            size=tokens.icon_medium,
            label=ui_text("tasks.close"),
        ),
        tooltip=ui_text("tasks.close"),
        on_click=lambda _event: close(),
    )
    return ft.AlertDialog(
        modal=True,
        title=ft.Row(
            [
                ft.Text(ui_text("tasks.details_title"), color=tokens.text_primary, weight=ft.FontWeight.W_700, expand=True),
                close_button,
            ]
        ),
        content=ft.Container(
            ft.Column(
                [
                    title,
                    description,
                    project,
                    ft.ResponsiveRow(
                        [
                            ft.Container(scheduled_date, col={"sm": 12, "md": 7}),
                            ft.Container(scheduled_time, col={"sm": 12, "md": 5}),
                        ],
                        spacing=tokens.space_3,
                        run_spacing=tokens.space_3,
                    ),
                    deadline,
                    ft.ResponsiveRow(
                        [
                            ft.Container(estimate, col={"sm": 12, "md": 5}),
                            ft.Container(
                                ft.Column(
                                    [
                                        ft.Text(ui_text("tasks.priority"), color=tokens.text_muted, size=tokens.text_small),
                                        ft.Row([importance, urgency], spacing=tokens.space_2),
                                    ],
                                    spacing=tokens.space_1,
                                ),
                                col={"sm": 12, "md": 7},
                            ),
                        ],
                        spacing=tokens.space_3,
                        run_spacing=tokens.space_3,
                    ),
                    completed,
                    message,
                ],
                spacing=tokens.space_3,
                tight=True,
            ),
            width=650,
        ),
        actions=[
            secondary_button(ui_text("tasks.cancel"), tokens, on_click=lambda _event: close()),
            primary_button(ui_text("tasks.save"), tokens, on_click=save),
        ],
        bgcolor=tokens.surface_elevated,
        scrollable=True,
    )
