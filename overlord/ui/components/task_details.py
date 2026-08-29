from __future__ import annotations

import math
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date, datetime, time

import flet as ft

from overlord.app.services import ApplicationServices
from overlord.modules.projects.domain import Project, ProjectStageStatus
from overlord.modules.tasks.domain import (
    ChecklistItemDraft,
    TaskChecklistItem,
    TaskDetailsStatus,
    TaskProjectAssignment,
    is_scheduled_for_day,
    task_details_status,
)
from overlord.modules.validation import FieldValidationError
from overlord.ui.components.controls import checkbox, danger_button, primary_button, secondary_button, select_field, text_field
from overlord.ui.components.complete_task import show_complete_task_dialog
from overlord.ui.components.date_time_picker import build_date_time_picker_dialog
from overlord.ui.components.status import state_chip
from overlord.ui.components.task_form_shared import (
    delayed_tooltip as _tooltip,
    project_count_label as _project_count,
    project_stage_label as _stage_label,
    task_duration_control,
    task_form_icon_button as _icon_button,
)
from overlord.ui.components.task_form_values import duration_minutes_value
from overlord.ui.design_system.icons import IconName, lucide_icon
from overlord.ui.design_system.tokens import StateColors, ThemeTokens
from overlord.ui.strings import format_compact_datetime, format_date_with_year, ui_error, ui_text


@dataclass(slots=True)
class TaskDetailsChecklistItem:
    client_id: int
    item_id: int | None = None
    title: str = ""
    completed: bool = False
    children: list["TaskDetailsChecklistItem"] = field(default_factory=list)


@dataclass(slots=True)
class TaskDetailsFormState:
    status: TaskDetailsStatus
    status_touched: bool = False
    scheduled_date: date | None = None
    deadline_at: datetime | None = None
    selected_project_ids: list[int] = field(default_factory=list)
    selected_stage_ids: dict[int, int] = field(default_factory=dict)
    checklist_enabled: bool = False
    checklist_items: list[TaskDetailsChecklistItem] = field(default_factory=list)
    next_checklist_id: int = 1


def _checklist_tree(records: tuple[TaskChecklistItem, ...]) -> list[TaskDetailsChecklistItem]:
    by_id = {
        item.id: TaskDetailsChecklistItem(item.id, item.id, item.title, item.completed)
        for item in records
    }
    roots: list[TaskDetailsChecklistItem] = []
    for item in sorted(records, key=lambda value: (value.parent_item_id or 0, value.position, value.id)):
        current = by_id[item.id]
        parent = by_id.get(item.parent_item_id) if item.parent_item_id is not None else None
        (parent.children if parent is not None else roots).append(current)
    return roots


def _checklist_drafts(items: list[TaskDetailsChecklistItem]) -> tuple[ChecklistItemDraft, ...]:
    return tuple(
        ChecklistItemDraft(item.title, item.completed, _checklist_drafts(item.children), item.item_id)
        for item in items
    )


def _status_label(status: TaskDetailsStatus) -> str:
    return ui_text("tasks.details_blocked") if status is TaskDetailsStatus.BLOCKED else ui_text(f"lifecycle.{status.value}")


def _status_colors(status: TaskDetailsStatus, tokens: ThemeTokens) -> StateColors:
    return {
        TaskDetailsStatus.PLANNED: tokens.neutral,
        TaskDetailsStatus.IN_PROGRESS: tokens.info,
        TaskDetailsStatus.BLOCKED: tokens.blocker,
        TaskDetailsStatus.PAUSED: tokens.warning,
        TaskDetailsStatus.COMPLETED: tokens.success,
        TaskDetailsStatus.CANCELLED: tokens.error,
    }[status]


def build_delete_task_confirmation(
    services: ApplicationServices,
    task_id: int,
    tokens: ThemeTokens,
    *,
    close_confirmation: Callable[[], None],
    on_deleted: Callable[[], None],
    report_error,
) -> ft.AlertDialog:
    message = ft.Text("", color=tokens.error.text, size=tokens.text_small)

    def confirm(_event) -> None:
        try:
            services.tasks.delete_task.execute(task_id)
        except Exception as error:
            text = ui_error(error)
            message.value = text
            message.update()
            report_error(text)
        else:
            close_confirmation()
            on_deleted()

    return ft.AlertDialog(
        modal=True,
        title=ft.Text(ui_text("tasks.delete_confirm_title"), color=tokens.text_primary, weight=ft.FontWeight.W_700),
        content=ft.Container(
            ft.Column(
                [ft.Text(ui_text("tasks.delete_confirm_body"), color=tokens.text_secondary), message],
                spacing=tokens.space_3,
                tight=True,
            ),
            width=360,
        ),
        actions=[
            secondary_button(
                ui_text("tasks.cancel"), tokens, on_click=lambda _event: close_confirmation(),
                data={"role": "delete-task-cancel"},
            ),
            danger_button(
                ui_text("tasks.delete"), tokens, on_click=confirm,
                data={"role": "delete-task-confirm"},
            ),
        ],
        bgcolor=tokens.surface_elevated,
        data={"role": "delete-task-confirmation"},
    )


def build_task_details_dialog(
    services: ApplicationServices,
    projects: tuple[Project, ...],
    task_id: int,
    day: date,
    tokens: ThemeTokens,
    on_saved: Callable[[], None],
    close: Callable[[], None],
    report_error,
    *,
    page: ft.Page | None = None,
    on_deleted: Callable[[], None] | None = None,
) -> ft.AlertDialog:
    """Build the one reusable Task Details flow used by every Task origin."""

    data = services.tasks.get_editor.execute(task_id)
    task = data.task
    open_blockers = tuple(blocker for blocker in data.blockers if blocker.resolved_at is None)
    checklist_items = _checklist_tree(task.checklist_items)
    state = TaskDetailsFormState(
        status=task_details_status(task, has_open_blockers=bool(open_blockers)),
        scheduled_date=task.schedule_start_date,
        deadline_at=task.deadline_at,
        selected_project_ids=[link.project_id for link in task.project_links],
        selected_stage_ids={link.project_id: link.stage_id for link in task.project_links if link.stage_id is not None},
        checklist_enabled=bool(checklist_items),
        checklist_items=checklist_items,
        next_checklist_id=max((item.id for item in task.checklist_items), default=0) + 1,
    )
    project_by_id = {project.id: project for project in projects}
    stages_by_project = {
        project.id: tuple(
            stage for stage in services.projects.list_stages.execute(project.id)
            if stage.status is not ProjectStageStatus.ARCHIVED
        )
        for project in projects
    }

    title = text_field(
        tokens, hint_text=ui_text("tasks.field_title"), value=task.title, autofocus=True,
        height=48, width=558, data={"role": "task-details-title"},
    )
    description = text_field(
        tokens, hint_text=ui_text("tasks.field_description"), value=task.description or "",
        multiline=True, min_lines=8, max_lines=8, height=180, width=558,
        data={"role": "task-details-description"},
    )
    message = ft.Text("", color=tokens.error.text, size=tokens.text_small, data={"role": "task-details-message"})
    status_host = ft.Container(data={"role": "task-details-status"})
    project_selector_host = ft.Container(data={"role": "task-details-project-selector"})
    stage_host = ft.Column(spacing=tokens.space_3, tight=True, data={"role": "task-details-stage-controls"})
    deadline_host = ft.Container(width=174, data={"role": "task-details-deadline"})
    checklist_host = ft.Container(data={"role": "task-details-checklist"})

    date_text = ft.Text(
        format_date_with_year(state.scheduled_date) if state.scheduled_date else ui_text("tasks.date"),
        color=tokens.text_primary, expand=True,
    )
    date_chevron = lucide_icon(
        IconName.CHEVRON, color=tokens.text_primary, size=tokens.icon_small,
        label=ui_text("tasks.open_calendar"), show_tooltip=False,
    )
    date_chevron.rotate = math.pi / 2
    date_button = secondary_button(
        ft.Row(
            [
                date_text,
                lucide_icon(
                    IconName.CALENDAR, color=tokens.text_primary, size=tokens.icon_medium,
                    label=ui_text("tasks.open_calendar"), show_tooltip=False,
                ),
                date_chevron,
            ],
            spacing=tokens.space_3,
        ),
        tokens, height=48, width=558, data={"role": "task-details-date"},
    )

    deadline_text = ft.Text(
        format_compact_datetime(state.deadline_at) if state.deadline_at else ui_text("tasks.deadline"),
        color=tokens.text_primary, expand=True, no_wrap=True, overflow=ft.TextOverflow.ELLIPSIS,
    )
    deadline_button = secondary_button(
        ft.Row(
            [
                lucide_icon(
                    IconName.CLOCK, color=tokens.text_primary, size=tokens.icon_medium,
                    label=ui_text("tasks.deadline"), show_tooltip=False,
                ),
                deadline_text,
            ],
            spacing=tokens.space_2,
        ),
        tokens, tooltip=_tooltip(ui_text("tasks.deadline_time")), data={"role": "deadline-trigger"},
    )
    clear_deadline_button = _icon_button(
        lucide_icon(
            IconName.CLOSE, color=tokens.text_secondary, size=tokens.icon_small,
            label=ui_text("tasks.remove_deadline"), show_tooltip=False,
        ),
        tokens, label=ui_text("tasks.remove_deadline"), on_click=lambda _event: clear_deadline(),
    )
    clear_deadline_button.data = {"role": "remove-deadline"}

    duration = task_duration_control(
        tokens,
        hours_value=str(task.estimate_minutes // 60) if task.estimate_minutes is not None else "",
        minutes_value=str(task.estimate_minutes % 60) if task.estimate_minutes is not None else "",
        hint_text="",
    )
    estimate_control = duration.control
    estimate_hours = duration.hours
    estimate_minutes = duration.minutes

    def pop_overlay() -> None:
        if page is not None:
            page.pop_dialog()

    def apply_date(value: date | datetime) -> None:
        state.scheduled_date = value.date() if isinstance(value, datetime) else value
        date_text.value = format_date_with_year(state.scheduled_date)
        date_text.update()

    def open_date(_event) -> None:
        if page is None:
            return
        settings = services.settings.get_settings.execute()
        page.show_dialog(build_date_time_picker_dialog(
            tokens, initial_date=state.scheduled_date or day, include_time=False, initial_time=None,
            first_day_of_week=0 if settings.first_day_of_week == "monday" else 6,
            on_apply=apply_date, close=pop_overlay,
        ))

    def apply_deadline(value: date | datetime) -> None:
        assert isinstance(value, datetime)
        state.deadline_at = value
        deadline_text.value = format_compact_datetime(value)
        render_deadline(update=True)

    def open_deadline(_event) -> None:
        if page is None:
            return
        settings = services.settings.get_settings.execute()
        initial = state.deadline_at
        page.show_dialog(build_date_time_picker_dialog(
            tokens,
            initial_date=initial.date() if initial else (state.scheduled_date or day),
            include_time=True, initial_time=initial.time() if initial else time(0, 0),
            first_day_of_week=0 if settings.first_day_of_week == "monday" else 6,
            on_apply=apply_deadline, close=pop_overlay,
        ))

    def clear_deadline() -> None:
        state.deadline_at = None
        deadline_text.value = ui_text("tasks.deadline")
        render_deadline(update=True)

    def render_deadline(*, update: bool = False) -> None:
        if state.deadline_at is None:
            deadline_button.width = 174
            deadline_host.content = deadline_button
        else:
            deadline_button.width = 134
            deadline_host.content = ft.Row([deadline_button, clear_deadline_button], spacing=0, tight=True)
        if update:
            deadline_host.update()

    date_button.on_click = open_date
    deadline_button.on_click = open_deadline

    def set_status(selected: TaskDetailsStatus) -> None:
        if selected is TaskDetailsStatus.COMPLETED and state.status is not TaskDetailsStatus.COMPLETED:
            if page is not None:
                show_complete_task_dialog(
                    page,
                    services,
                    task.id,
                    tokens,
                    lambda _task: on_saved(),
                    report_error,
                    selected_day=day if is_scheduled_for_day(task, day) else None,
                )
            return
        state.status = selected
        state.status_touched = True
        render_status(update=True)

    selectable_statuses = (
        TaskDetailsStatus.PLANNED, TaskDetailsStatus.IN_PROGRESS, TaskDetailsStatus.BLOCKED,
        TaskDetailsStatus.PAUSED, TaskDetailsStatus.COMPLETED,
    )

    def render_status(*, update: bool = False) -> None:
        status_host.content = ft.PopupMenuButton(
            content=state_chip(_status_label(state.status), _status_colors(state.status, tokens), tokens),
            items=[
                ft.PopupMenuItem(
                    content=_status_label(status), checked=state.status is status,
                    on_click=lambda _event, value=status: set_status(value),
                    data={"role": "task-status-option", "status": status.value},
                )
                for status in selectable_statuses
            ],
            tooltip=_tooltip(ui_text("tasks.details_status")), data={"role": "task-status-menu"},
        )
        if update:
            status_host.update()

    def render_stage_controls(*, update: bool = False) -> None:
        controls: list[ft.Control] = []
        for project_id in state.selected_project_ids:
            stages = stages_by_project.get(project_id, ())
            if not stages:
                state.selected_stage_ids.pop(project_id, None)
                continue
            project = project_by_id[project_id]
            selector = select_field(
                tokens, value=str(state.selected_stage_ids.get(project_id, 0)),
                options=[
                    ft.DropdownOption("0", f"PS-{project.title}: {ui_text('tasks.project_stage_none')}"),
                    *[ft.DropdownOption(str(stage.id), f"PS-{project.title}: {_stage_label(stage)}") for stage in stages],
                ],
                tooltip=_tooltip(ui_text("tasks.project_stage", project=project.title)),
                width=558, data={"role": "project-stage", "project_id": project_id},
            )

            def select_stage(_event, *, selected_project_id=project_id, field=selector) -> None:
                stage_id = int(field.value or 0)
                if stage_id:
                    state.selected_stage_ids[selected_project_id] = stage_id
                else:
                    state.selected_stage_ids.pop(selected_project_id, None)

            selector.on_select = select_stage
            controls.append(selector)
        stage_host.controls = controls
        if update:
            stage_host.update()

    def toggle_project(project_id: int) -> None:
        if project_id in state.selected_project_ids:
            state.selected_project_ids.remove(project_id)
            state.selected_stage_ids.pop(project_id, None)
        elif len(state.selected_project_ids) >= 4:
            message.value = ui_text("tasks.projects_limit")
            message.update()
            return
        else:
            state.selected_project_ids.append(project_id)
        message.value = ""
        render_project_selector(update=True)
        render_stage_controls(update=True)

    def render_project_selector(*, update: bool = False) -> None:
        count = len(state.selected_project_ids)
        label = _project_count(count) if count else ui_text("tasks.projects")
        items = [
            ft.PopupMenuItem(
                content=ft.Row(
                    [
                        ft.Container(
                            width=10, height=10, bgcolor=project.color,
                            border=ft.Border.all(tokens.border_width, tokens.border_default),
                            border_radius=tokens.radius_pill,
                        ),
                        ft.Text(project.title, color=tokens.text_primary),
                    ],
                    spacing=tokens.space_2,
                ),
                checked=project.id in state.selected_project_ids,
                disabled=count >= 4 and project.id not in state.selected_project_ids,
                on_click=lambda _event, project_id=project.id: toggle_project(project_id),
                data={"role": "project-option", "project_id": project.id},
            )
            for project in projects
        ]
        chevron = lucide_icon(
            IconName.CHEVRON, color=tokens.text_primary, size=tokens.icon_small,
            label=ui_text("tasks.projects"), show_tooltip=False,
        )
        chevron.rotate = math.pi / 2
        project_selector_host.content = ft.PopupMenuButton(
            content=ft.Container(
                ft.Row(
                    [
                        ft.Container(
                            ft.Text(str(count), color=tokens.on_accent, size=tokens.text_small),
                            bgcolor=tokens.text_primary, border_radius=tokens.radius_small,
                            padding=ft.Padding.symmetric(horizontal=tokens.space_2, vertical=tokens.space_1),
                            visible=count > 0,
                        ),
                        ft.Text(label, color=tokens.text_primary, expand=True),
                        chevron,
                    ],
                    spacing=tokens.space_2,
                ),
                height=tokens.control_height, width=174,
                padding=ft.Padding.symmetric(horizontal=tokens.space_3),
                border=ft.Border.all(tokens.border_width, tokens.border_default),
                border_radius=tokens.radius_medium, bgcolor=tokens.control_background,
            ),
            items=items or [ft.PopupMenuItem(content=ui_text("tasks.projects_none"), disabled=True)],
            data={"role": "project-menu"},
        )
        if update:
            project_selector_host.update()

    def new_checklist_item() -> TaskDetailsChecklistItem:
        item = TaskDetailsChecklistItem(state.next_checklist_id)
        state.next_checklist_id += 1
        return item

    def all_checklist_items(items: list[TaskDetailsChecklistItem] | None = None) -> list[TaskDetailsChecklistItem]:
        flattened: list[TaskDetailsChecklistItem] = []
        for item in state.checklist_items if items is None else items:
            flattened.append(item)
            flattened.extend(all_checklist_items(item.children))
        return flattened

    def remove_checklist_item(client_id: int, items: list[TaskDetailsChecklistItem] | None = None) -> bool:
        target = state.checklist_items if items is None else items
        for index, item in enumerate(target):
            if item.client_id == client_id:
                target.pop(index)
                return True
            if remove_checklist_item(client_id, item.children):
                return True
        return False

    def checklist_row(item: TaskDetailsChecklistItem, depth: int) -> ft.Control:
        completed = checkbox(
            tokens, value=item.completed,
            tooltip=_tooltip(ui_text("tasks.checklist_item")),
            data={"role": "checklist-item-completed", "client_id": item.client_id},
        )
        field_control = text_field(
            tokens, compact=True, value=item.title, hint_text=ui_text("tasks.checklist_item"), expand=True,
            data={"role": "checklist-item-title", "client_id": item.client_id, "item_id": item.item_id},
        )

        def change_title(_event) -> None:
            item.title = field_control.value or ""

        def change_completed(_event) -> None:
            item.completed = bool(completed.value)
            render_checklist(update=True)

        def add_child(_event) -> None:
            item.children.append(new_checklist_item())
            render_checklist(update=True)

        def remove(_event) -> None:
            remove_checklist_item(item.client_id)
            render_checklist(update=True)

        field_control.on_change = change_title
        completed.on_change = change_completed
        add_child_button = _icon_button(
            lucide_icon(
                IconName.PLUS, color=tokens.text_primary, size=tokens.icon_medium,
                label=ui_text("tasks.add_checklist_child"), show_tooltip=False,
            ),
            tokens, on_click=add_child, label=ui_text("tasks.add_checklist_child"),
        )
        add_child_button.data = {"role": "add-checklist-child", "client_id": item.client_id}
        remove_button = _icon_button(
            lucide_icon(
                IconName.CLOSE, color=tokens.text_secondary, size=tokens.icon_medium,
                label=ui_text("tasks.remove_checklist_item"), show_tooltip=False,
            ),
            tokens, on_click=remove, label=ui_text("tasks.remove_checklist_item"),
        )
        remove_button.data = {"role": "remove-checklist-item", "client_id": item.client_id}
        return ft.Container(
            ft.Row(
                [completed, field_control, add_child_button, remove_button],
                spacing=tokens.space_2, vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            margin=ft.Margin.only(left=depth * tokens.space_8),
            data={"role": "checklist-item", "client_id": item.client_id, "depth": depth},
        )

    def checklist_controls(items: list[TaskDetailsChecklistItem], depth: int = 0) -> list[ft.Control]:
        controls: list[ft.Control] = []
        for item in items:
            controls.append(checklist_row(item, depth))
            controls.extend(checklist_controls(item.children, depth + 1))
        return controls

    def disable_checklist(_event=None) -> None:
        state.checklist_enabled = False
        state.checklist_items.clear()
        render_checklist(update=True)

    def add_checklist(_event=None) -> None:
        state.checklist_enabled = True
        if not state.checklist_items:
            state.checklist_items.append(new_checklist_item())
        render_checklist(update=True)

    def add_root_item(_event=None) -> None:
        state.checklist_items.append(new_checklist_item())
        render_checklist(update=True)

    def render_checklist(*, update: bool = False) -> None:
        if not state.checklist_enabled:
            checklist_host.content = secondary_button(
                ui_text("tasks.add_checklist"), tokens, on_click=add_checklist, width=174,
                data={"role": "checklist-toggle"},
            )
        else:
            items = all_checklist_items()
            completed_count = sum(item.completed for item in items)
            progress = completed_count / len(items) if items else 0.0
            checklist_host.content = ft.Column(
                [
                    ft.Row(
                        [
                            checkbox(
                                tokens, label=ui_text("tasks.checklist"), value=True,
                                on_change=disable_checklist,
                            ),
                            ft.Container(expand=True),
                            secondary_button(
                                ui_text("tasks.remove_checklist"), tokens, compact=True,
                                on_click=disable_checklist, data={"role": "remove-checklist"},
                            ),
                        ],
                        spacing=tokens.space_2,
                    ),
                    ft.Row(
                        [
                            ft.Text(
                                ui_text("tasks.checklist_progress", percent=round(progress * 100)),
                                color=tokens.text_primary, size=tokens.text_small,
                            ),
                            ft.ProgressBar(
                                value=progress, color=tokens.text_primary, bgcolor=tokens.border_default,
                                border_radius=tokens.radius_pill, expand=True,
                            ),
                        ],
                        spacing=tokens.space_2,
                    ),
                    *checklist_controls(state.checklist_items),
                    secondary_button(
                        ui_text("tasks.add_checklist_item"), tokens, compact=True,
                        on_click=add_root_item, data={"role": "add-checklist-item"},
                    ),
                ],
                spacing=tokens.space_2, tight=True,
            )
        if update:
            checklist_host.update()

    def estimated_minutes_value() -> int | None:
        return duration_minutes_value(estimate_hours.value, estimate_minutes.value)

    def save(_event) -> None:
        title.error = None
        estimate_hours.error = None
        estimate_minutes.error = None
        message.value = ""
        try:
            assignments = tuple(
                TaskProjectAssignment(project_id, state.selected_stage_ids.get(project_id))
                for project_id in state.selected_project_ids
            )
            services.tasks.update_details.execute(
                task.id, title=title.value or "", description=description.value or "",
                schedule_start_date=state.scheduled_date, deadline_at=state.deadline_at,
                estimate_minutes=estimated_minutes_value(), project_links=assignments,
                checklist_items=_checklist_drafts(state.checklist_items) if state.checklist_enabled else (),
                status=state.status if state.status_touched else None,
            )
        except Exception as error:
            text = ui_error(error)
            error_field = error.field if isinstance(error, FieldValidationError) else None
            if error_field == "title":
                title.error = text
                title.update()
            elif error_field == "estimate":
                estimate_minutes.error = text
                estimate_minutes.update()
            else:
                message.value = text
                message.update()
                report_error(text)
        else:
            on_saved()

    def open_delete(_event) -> None:
        if page is None:
            return
        page.show_dialog(build_delete_task_confirmation(
            services, task.id, tokens, close_confirmation=pop_overlay,
            on_deleted=on_deleted or on_saved, report_error=report_error,
        ))

    delete_button = _icon_button(
        lucide_icon(
            IconName.TRASH, color=tokens.text_primary, size=tokens.icon_large,
            label=ui_text("tasks.delete_tooltip"), show_tooltip=False,
        ),
        tokens, on_click=open_delete, label=ui_text("tasks.delete_tooltip"),
    )
    delete_button.data = {"role": "delete-task"}
    close_button = _icon_button(
        lucide_icon(
            IconName.CLOSE, color=tokens.text_primary, size=tokens.icon_large,
            label=ui_text("tasks.close"), show_tooltip=False,
        ),
        tokens, on_click=lambda _event: close(), label=ui_text("tasks.close"),
    )
    close_button.data = {"role": "task-details-close"}
    save_button = primary_button(
        ui_text("tasks.save"), tokens, width=370, on_click=save,
        data={"role": "task-details-save"},
    )
    cancel_button = secondary_button(
        ui_text("tasks.cancel"), tokens, width=178, on_click=lambda _event: close(),
        data={"role": "task-details-cancel"},
    )

    render_status()
    render_project_selector()
    render_stage_controls()
    render_deadline()
    render_checklist()
    return ft.AlertDialog(
        modal=True,
        title=ft.Row(
            [
                ft.Text(
                    ui_text("tasks.details_title"), color=tokens.text_primary, size=tokens.text_title,
                    weight=ft.FontWeight.W_700, expand=True,
                ),
                status_host, delete_button, close_button,
            ],
            spacing=tokens.space_2, vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        content=ft.Container(
            ft.Column(
                [
                    title, description, date_button,
                    ft.Row([project_selector_host, deadline_host, estimate_control], spacing=tokens.space_3),
                    stage_host, checklist_host, message,
                ],
                spacing=tokens.space_3, tight=True, scroll=ft.ScrollMode.AUTO,
            ),
            width=558,
        ),
        actions=[ft.Row([save_button, cancel_button], spacing=tokens.space_2)],
        title_padding=ft.Padding.only(left=tokens.space_5, top=tokens.space_5, right=tokens.space_3),
        content_padding=ft.Padding.symmetric(horizontal=tokens.space_5, vertical=tokens.space_4),
        actions_padding=ft.Padding.only(left=tokens.space_5, right=tokens.space_5, bottom=tokens.space_5),
        bgcolor=tokens.surface_elevated, scrollable=True,
        data={"role": "task-details-dialog", "state": state},
    )
