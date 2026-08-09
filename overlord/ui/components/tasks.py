from __future__ import annotations

from collections.abc import Callable
from datetime import date

import flet as ft

from overlord.app.read_models import TaskListItem
from overlord.app.services import ApplicationServices
from overlord.modules.blockers.domain import BlockerType
from overlord.modules.projects.domain import Project
from overlord.modules.tasks.domain import Task, TaskLifecycle
from overlord.ui.components.dialogs import dialog_footer
from overlord.ui.components.status import state_chip
from overlord.ui.design_system.icons import IconName, lucide_icon
from overlord.ui.design_system.tokens import ThemeTokens
from overlord.ui.strings import ui_text


def _date_value(value: str) -> date:
    try:
        return date.fromisoformat(value.strip())
    except ValueError as error:
        raise ValueError(ui_text("tasks.date_error")) from error


def _project_options(projects: tuple[Project, ...]) -> list[ft.DropdownOption]:
    return [
        ft.DropdownOption("none", ui_text("tasks.no_project")),
        *[ft.DropdownOption(str(item.id), item.title) for item in projects],
    ]


def _project_id(value: str | None) -> int | None:
    return None if value in {None, "none"} else int(value)


def build_quick_task_dialog(
    services: ApplicationServices,
    projects: tuple[Project, ...],
    tokens: ThemeTokens,
    on_created: Callable[[Task], None],
    close: Callable[[], None],
    selected_project_id: int | None = None,
) -> ft.AlertDialog:
    title = ft.TextField(label=ui_text("tasks.field_title"), autofocus=True)
    project = ft.Dropdown(
        label=ui_text("tasks.field_project"),
        value=str(selected_project_id) if selected_project_id is not None else "none",
        options=_project_options(projects),
    )
    planned_date = ft.TextField(
        label=ui_text("tasks.field_planned_date"),
        hint_text="YYYY-MM-DD",
    )
    estimate = ft.TextField(
        label=ui_text("tasks.field_estimate"),
        keyboard_type=ft.KeyboardType.NUMBER,
    )
    importance = ft.Checkbox(label=ui_text("tasks.important"), value=False)
    urgency = ft.Checkbox(label=ui_text("tasks.urgent"), value=False)
    definition = ft.TextField(
        label=ui_text("tasks.field_definition"),
        multiline=True,
        min_lines=2,
        max_lines=3,
    )
    next_action = ft.TextField(label=ui_text("tasks.field_next_action"))
    blocker_type = ft.Dropdown(
        label=ui_text("tasks.field_blocker_type"),
        value=BlockerType.OTHER.value,
        options=[ft.DropdownOption(value.value, value.value.title()) for value in BlockerType],
    )
    blocker_description = ft.TextField(
        label=ui_text("tasks.field_blocker_description"),
        multiline=True,
        min_lines=2,
        max_lines=3,
    )
    message = ft.Text("", color=tokens.error.text, size=tokens.text_small)
    details = ft.Container(
        ft.Column(
            [
                ft.ResponsiveRow(
                    [
                        ft.Container(planned_date, col={"sm": 12, "md": 7}),
                        ft.Container(estimate, col={"sm": 12, "md": 5}),
                    ],
                    spacing=tokens.space_3,
                    run_spacing=tokens.space_3,
                ),
                ft.Row([importance, urgency], wrap=True),
                definition,
                next_action,
                ft.ResponsiveRow(
                    [
                        ft.Container(blocker_type, col={"sm": 12, "md": 5}),
                        ft.Container(blocker_description, col={"sm": 12, "md": 7}),
                    ],
                    spacing=tokens.space_3,
                    run_spacing=tokens.space_3,
                ),
            ],
            spacing=tokens.space_3,
        ),
        visible=False,
    )
    details_label = ft.Text(ui_text("tasks.more_details"), color=tokens.accent_primary)

    def toggle_details(_event) -> None:
        details.visible = not details.visible
        details_label.value = ui_text("tasks.fewer_details") if details.visible else ui_text("tasks.more_details")
        details.update()
        details_label.update()

    def create(_event) -> None:
        title.error = None
        planned_date.error = None
        estimate.error = None
        blocker_description.error = None
        message.value = ""
        try:
            chosen_date = _date_value(planned_date.value or "") if (planned_date.value or "").strip() else None
            try:
                minutes = int(estimate.value) if (estimate.value or "").strip() else None
            except ValueError as error:
                raise ValueError(ui_text("tasks.estimate_integer_error")) from error
            blocker_text = (blocker_description.value or "").strip()
            task = services.tasks.create_task.execute(
                _project_id(project.value),
                title.value or "",
                planned_date=chosen_date,
                definition_of_done=definition.value or None,
                next_action=next_action.value or None,
                importance=True if importance.value else None,
                urgency=True if urgency.value else None,
                estimate_minutes=minutes,
                blocker_type=BlockerType(blocker_type.value) if blocker_text else None,
                blocker_description=blocker_text or None,
            )
            on_created(task)
        except Exception as error:
            text = str(error)
            if "title" in text.lower():
                title.error = text
                title.update()
            elif "estimate" in text.lower():
                estimate.error = text
                estimate.update()
            elif "blocker" in text.lower():
                blocker_description.error = text
                blocker_description.update()
            elif "date" in text.lower():
                planned_date.error = text
                planned_date.update()
            else:
                message.value = text
                message.update()

    return ft.AlertDialog(
        modal=True,
        title=ui_text("tasks.quick_title"),
        content=ft.Container(
            ft.Column(
                [
                    ft.Text(ui_text("tasks.quick_description"), color=tokens.text_secondary),
                    title,
                    project,
                    ft.TextButton(details_label, on_click=toggle_details),
                    details,
                    message,
                ],
                spacing=tokens.space_3,
                tight=True,
            ),
            width=620,
        ),
        actions=dialog_footer(
            ui_text("tasks.cancel"),
            ui_text("tasks.create"),
            lambda _e: close(),
            create,
            tokens,
        ),
        bgcolor=tokens.surface_elevated,
        scrollable=True,
    )


def task_row(
    item: TaskListItem,
    tokens: ThemeTokens,
    *,
    on_complete: Callable[[object], None] | None = None,
    on_edit: Callable[[object], None] | None = None,
) -> ft.Container:
    lifecycle = item.task.lifecycle_status
    status = lifecycle.value.replace("_", " ").title() if lifecycle else ui_text("common.review_status")
    color = tokens.warning if lifecycle is None else (
        tokens.success if lifecycle is TaskLifecycle.COMPLETED else tokens.neutral
    )
    actions: list[ft.Control] = []
    if on_edit:
        actions.append(
            ft.TextButton(
                ui_text("common.edit"),
                on_click=on_edit,
                tooltip=ui_text("common.edit_named", name=item.task.title),
            )
        )
    if on_complete and lifecycle is not TaskLifecycle.COMPLETED:
        actions.append(
            ft.Button(
                lucide_icon(
                    IconName.CHECK,
                    color=tokens.on_accent,
                    size=tokens.icon_small,
                    label=ui_text("common.complete_task"),
                ),
                bgcolor=tokens.accent_primary,
                elevation=0,
                on_click=on_complete,
                tooltip=ui_text("common.complete_named", name=item.task.title),
            )
        )
    metadata = [item.project_title or ui_text("tasks.no_project")]
    if item.current_plan:
        metadata.append(item.current_plan.planned_date.strftime("%b %d"))
    if item.task.importance:
        metadata.append(ui_text("tasks.important"))
    if item.task.urgency:
        metadata.append(ui_text("tasks.urgent"))
    if item.open_blockers:
        metadata.append(ui_text("tasks.blocked") if item.open_blockers == 1 else ui_text("tasks.blockers", count=item.open_blockers))
    elif item.carry_over_count >= 2:
        metadata.append(ui_text("tasks.needs_attention_label"))
    return ft.Container(
        ft.Row(
            [
                ft.Column(
                    [
                        ft.Text(item.task.title, color=tokens.text_primary, weight=ft.FontWeight.W_600),
                        ft.Text(ui_text("common.metadata_separator").join(metadata), color=tokens.text_muted, size=tokens.text_small),
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
