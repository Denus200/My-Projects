from __future__ import annotations

from collections.abc import Callable
from datetime import date

import flet as ft

from overlord.app.services import ApplicationServices
from overlord.modules.tasks.domain import Task
from overlord.modules.validation import FieldValidationError
from overlord.ui.components.controls import primary_button, secondary_button
from overlord.ui.components.dialogs import close_dialog
from overlord.ui.components.task_form_shared import (
    TaskDurationControl,
    task_duration_control,
    task_form_icon_button,
)
from overlord.ui.components.task_form_values import duration_minutes_value
from overlord.ui.design_system.icons import IconName, lucide_icon
from overlord.ui.design_system.tokens import ThemeTokens
from overlord.ui.strings import ui_error, ui_text


def _duration_parts(minutes: int | None) -> tuple[str, str]:
    if minutes is None:
        return "", ""
    hours, remainder = divmod(minutes, 60)
    return str(hours), str(remainder)


def build_complete_task_dialog(
    services: ApplicationServices,
    task_id: int,
    tokens: ThemeTokens,
    on_completed: Callable[[Task], None],
    close: Callable[[], None],
    report_error,
    *,
    selected_day: date | None = None,
) -> ft.AlertDialog:
    """Build the single completion-time flow used by every Task origin."""

    task = services.tasks.get_editor.execute(task_id).task
    estimate_hours, estimate_minutes = _duration_parts(task.estimate_minutes)
    total_hours, total_minutes = _duration_parts(task.total_time_minutes)
    active_hours, active_minutes = _duration_parts(task.active_time_minutes)
    estimate_read_only = task.estimate_minutes is not None

    estimate = task_duration_control(
        tokens,
        hours_value=estimate_hours,
        minutes_value=estimate_minutes,
        label=ui_text("tasks.estimated_time"),
        role_prefix="complete-estimate",
        control_role="complete-estimated-time",
        read_only=estimate_read_only,
    )
    total = task_duration_control(
        tokens,
        hours_value=total_hours,
        minutes_value=total_minutes,
        label=ui_text("tasks.total_time"),
        role_prefix="complete-total",
        control_role="complete-total-time",
    )
    active = task_duration_control(
        tokens,
        hours_value=active_hours,
        minutes_value=active_minutes,
        label=ui_text("tasks.active_time"),
        role_prefix="complete-active",
        control_role="complete-active-time",
    )
    message = ft.Text(
        "",
        color=tokens.error.text,
        size=tokens.text_small,
        data={"role": "complete-task-message"},
    )

    duration_by_field = {
        "estimate": estimate,
        "total_time": total,
        "active_time": active,
    }

    def value(control: TaskDurationControl, *, field: str, label: str) -> int | None:
        return duration_minutes_value(
            control.hours.value,
            control.minutes.value,
            field=field,
            label=label,
        )

    def confirm(_event) -> None:
        message.value = ""
        for control in duration_by_field.values():
            control.hours.error = None
            control.minutes.error = None
        try:
            estimated = (
                task.estimate_minutes
                if estimate_read_only
                else value(estimate, field="estimate", label=ui_text("tasks.estimated_time"))
            )
            completed = services.tasks.complete_task.execute(
                task_id,
                estimate_minutes=estimated,
                total_time_minutes=value(total, field="total_time", label=ui_text("tasks.total_time")),
                active_time_minutes=value(active, field="active_time", label=ui_text("tasks.active_time")),
                selected_day=selected_day,
            )
        except Exception as error:
            text = ui_error(error)
            if isinstance(error, FieldValidationError) and error.field in duration_by_field:
                field = duration_by_field[error.field].minutes
                field.error = text
                field.update()
            else:
                message.value = text
                message.update()
                report_error(text)
        else:
            on_completed(completed)

    def duration_row(label: str, control: TaskDurationControl, *, read_only: bool = False) -> ft.Control:
        return ft.Column(
            [
                ft.Text(label, color=tokens.text_muted, size=tokens.text_small),
                control.control,
            ],
            spacing=tokens.space_1,
            tight=True,
            data={"role": "complete-duration-row", "read_only": read_only},
        )

    close_button = task_form_icon_button(
        lucide_icon(
            IconName.CLOSE,
            color=tokens.text_primary,
            size=tokens.icon_large,
            label=ui_text("tasks.close"),
            show_tooltip=False,
        ),
        tokens,
        label=ui_text("tasks.close"),
        on_click=lambda _event: close(),
    )
    close_button.data = {"role": "complete-task-close"}
    save_button = primary_button(
        ui_text("tasks.create_save"),
        tokens,
        width=180,
        on_click=confirm,
        data={"role": "complete-task-confirm"},
    )
    cancel_button = secondary_button(
        ui_text("tasks.cancel"),
        tokens,
        width=118,
        on_click=lambda _event: close(),
        data={"role": "complete-task-cancel"},
    )

    return ft.AlertDialog(
        modal=True,
        title=ft.Row(
            [
                ft.Text(
                    ui_text("tasks.complete_title"),
                    color=tokens.text_primary,
                    size=tokens.text_title,
                    weight=ft.FontWeight.W_700,
                    expand=True,
                ),
                close_button,
            ],
            spacing=tokens.space_2,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        content=ft.Container(
            ft.Column(
                [
                    ft.Text(ui_text("tasks.complete_subtitle"), color=tokens.text_secondary),
                    duration_row(ui_text("tasks.estimated_time"), estimate, read_only=estimate_read_only),
                    duration_row(ui_text("tasks.total_time"), total),
                    duration_row(ui_text("tasks.active_time"), active),
                    message,
                ],
                spacing=tokens.space_3,
                tight=True,
            ),
            width=308,
        ),
        actions=[ft.Row([save_button, cancel_button], spacing=tokens.space_2)],
        title_padding=ft.Padding.only(left=tokens.space_5, top=tokens.space_4, right=tokens.space_2),
        content_padding=ft.Padding.only(left=tokens.space_5, right=tokens.space_5, top=tokens.space_1),
        actions_padding=ft.Padding.only(left=tokens.space_5, right=tokens.space_5, bottom=tokens.space_5),
        bgcolor=tokens.surface_elevated,
        data={
            "role": "complete-task-dialog",
            "task_id": task_id,
            "estimate_read_only": estimate_read_only,
        },
    )


def show_complete_task_dialog(
    page: ft.Page,
    services: ApplicationServices,
    task_id: int,
    tokens: ThemeTokens,
    on_completed: Callable[[Task], None],
    report_error,
    *,
    selected_day: date | None = None,
) -> ft.AlertDialog:
    def completed(task: Task) -> None:
        close_dialog(page)
        on_completed(task)

    dialog = build_complete_task_dialog(
        services,
        task_id,
        tokens,
        completed,
        lambda: close_dialog(page),
        report_error,
        selected_day=selected_day,
    )
    page.show_dialog(dialog)
    return dialog
