from __future__ import annotations

from collections.abc import Callable

import flet as ft

from overlord.app.read_models import TaskListItem
from overlord.modules.tasks.domain import TaskBoardColumn, TaskLifecycle, board_column
from overlord.ui.components.controls import primary_button, tertiary_button
from overlord.ui.components.create_task import build_create_task_dialog
from overlord.ui.components.status import state_chip
from overlord.ui.design_system.icons import IconName, lucide_icon
from overlord.ui.design_system.tokens import ThemeTokens
from overlord.ui.strings import format_short_date, ui_text


# Stable public name used by Tasks, Dashboard, and Project Tasks.
build_quick_task_dialog = build_create_task_dialog


def task_row(
    item: TaskListItem,
    tokens: ThemeTokens,
    *,
    on_complete: Callable[[object], None] | None = None,
    on_edit: Callable[[object], None] | None = None,
) -> ft.Container:
    lifecycle = item.task.lifecycle_status
    column = board_column(item.task)
    status = ui_text(f"task_board.{column.value}")
    color = tokens.success if column is TaskBoardColumn.COMPLETED else (
        tokens.warning if column is TaskBoardColumn.MISSED else (
            tokens.info if column is TaskBoardColumn.IN_PROGRESS else tokens.neutral
        )
    )
    actions: list[ft.Control] = []
    if on_edit:
        actions.append(
            tertiary_button(
                ui_text("common.edit"),
                tokens,
                on_click=on_edit,
                tooltip=ui_text("common.edit_named", name=item.task.title),
            )
        )
    if on_complete and lifecycle is not TaskLifecycle.COMPLETED:
        actions.append(
            primary_button(
                lucide_icon(
                    IconName.CHECK,
                    color=tokens.on_accent,
                    size=tokens.icon_small,
                    label=ui_text("common.complete_task"),
                ),
                tokens,
                on_click=on_complete,
                tooltip=ui_text("common.complete_named", name=item.task.title),
            )
        )
    metadata = [item.project_title or ui_text("tasks.no_project")]
    if item.task.schedule_start_date:
        schedule = format_short_date(item.task.schedule_start_date)
        if item.task.schedule_start_time:
            schedule += f" {item.task.schedule_start_time.strftime('%H:%M')}"
        if item.task.schedule_end_date:
            schedule += f" - {format_short_date(item.task.schedule_end_date)}"
            if item.task.schedule_end_time:
                schedule += f" {item.task.schedule_end_time.strftime('%H:%M')}"
        metadata.append(schedule)
    if item.task.importance:
        metadata.append(ui_text("tasks.important"))
    if item.task.urgency:
        metadata.append(ui_text("tasks.urgent"))
    metadata.extend(item.cycle_titles)
    if item.open_blockers:
        metadata.append(
            ui_text("tasks.blocked")
            if item.open_blockers == 1
            else ui_text("tasks.blockers", count=item.open_blockers)
        )
    return ft.Container(
        ft.Row(
            [
                ft.Column(
                    [
                        ft.Text(item.task.title, color=tokens.text_primary, weight=ft.FontWeight.W_600),
                        ft.Text(
                            ui_text("common.metadata_separator").join(metadata),
                            color=tokens.text_muted,
                            size=tokens.text_small,
                        ),
                    ],
                    spacing=tokens.space_1,
                    expand=True,
                ),
                state_chip(status, color, tokens),
                *actions,
            ],
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=tokens.space_2,
        ),
        bgcolor=tokens.surface_inner,
        border_radius=tokens.radius_medium,
        padding=tokens.space_3,
    )
