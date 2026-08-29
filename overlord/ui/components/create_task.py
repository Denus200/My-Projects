from __future__ import annotations

import math
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta

import flet as ft

from overlord.app.services import ApplicationServices
from overlord.modules.projects.domain import Project, ProjectStageStatus
from overlord.modules.tasks.domain import (
    ChecklistItemDraft,
    Task,
    TaskCreationMode,
    TaskProjectAssignment,
)
from overlord.modules.validation import FieldValidationError
from overlord.ui.components.controls import (
    checkbox,
    primary_button,
    secondary_button,
    select_field,
    text_field,
    tertiary_button,
)
from overlord.ui.components.date_time_picker import build_date_time_picker_dialog
from overlord.ui.components.task_form_shared import (
    delayed_tooltip as _tooltip,
    project_count_label as _project_count,
    project_stage_label as _stage_label,
    task_duration_control,
    task_form_icon_button as _icon_button,
)
from overlord.ui.components.task_form_values import duration_minutes_value
from overlord.ui.design_system.icons import IconName, lucide_icon
from overlord.ui.design_system.tokens import ThemeTokens
from overlord.ui.strings import (
    format_compact_datetime,
    format_date_with_year,
    ui_error,
    ui_text,
)


@dataclass(slots=True)
class ChecklistFormItem:
    client_id: int
    title: str = ""
    completed: bool = False
    children: list["ChecklistFormItem"] = field(default_factory=list)


@dataclass(slots=True)
class CreateTaskFormState:
    creation_mode: TaskCreationMode = TaskCreationMode.NORMAL
    advanced_expanded: bool = False
    scheduled_date: date | None = None
    deadline_at: datetime | None = None
    selected_project_ids: list[int] = field(default_factory=list)
    selected_stage_ids: dict[int, int] = field(default_factory=dict)
    checklist_enabled: bool = False
    checklist_items: list[ChecklistFormItem] = field(default_factory=list)
    next_checklist_id: int = 1


def _checklist_drafts(items: list[ChecklistFormItem]) -> tuple[ChecklistItemDraft, ...]:
    return tuple(
        ChecklistItemDraft(
            item.title,
            item.completed,
            _checklist_drafts(item.children),
        )
        for item in items
    )


def build_create_task_dialog(
    services: ApplicationServices,
    projects: tuple[Project, ...],
    tokens: ThemeTokens,
    on_created: Callable[[Task], None],
    close: Callable[[], None],
    selected_project_id: int | None = None,
    preset_start_date: date | None = None,
    preset_when: str | None = None,
    page: ft.Page | None = None,
) -> ft.AlertDialog:
    """Build the single state-driven Create Task flow used across Overlord."""

    if preset_when == "no_date":
        initial_date = None
    elif preset_when == "tomorrow":
        initial_date = date.today() + timedelta(days=1)
    else:
        initial_date = preset_start_date
    initial_projects = (
        [selected_project_id]
        if selected_project_id is not None and any(p.id == selected_project_id for p in projects)
        else []
    )
    state = CreateTaskFormState(
        scheduled_date=initial_date,
        selected_project_ids=initial_projects,
    )
    project_by_id = {project.id: project for project in projects}
    stages_by_project = {
        project.id: tuple(
            stage
            for stage in services.projects.list_stages.execute(project.id)
            if stage.status is not ProjectStageStatus.ARCHIVED
        )
        for project in projects
    }

    title = text_field(
        tokens,
        hint_text=ui_text("tasks.field_title"),
        autofocus=True,
        height=48,
        width=558,
        data={"role": "create-task-title"},
    )
    description = text_field(
        tokens,
        hint_text=ui_text("tasks.field_description"),
        multiline=True,
        min_lines=8,
        max_lines=8,
        height=180,
        width=558,
        data={"role": "create-task-description"},
    )
    message = ft.Text("", color=tokens.error.text, size=tokens.text_small)
    advanced_host = ft.Container(visible=False, data={"role": "create-task-advanced"})
    stage_host = ft.Column(spacing=tokens.space_3, tight=True, data={"role": "project-stage-controls"})
    checklist_host = ft.Container(visible=False, data={"role": "create-task-checklist"})
    creation_selector_host = ft.Container(data={"role": "creation-mode-selector"})
    project_selector_host = ft.Container(data={"role": "project-selector"})

    date_text = ft.Text(
        format_date_with_year(state.scheduled_date) if state.scheduled_date else ui_text("tasks.date"),
        color=tokens.text_primary,
        expand=True,
    )
    date_chevron = lucide_icon(
        IconName.CHEVRON,
        color=tokens.text_primary,
        size=tokens.icon_small,
        label=ui_text("tasks.open_calendar"),
        show_tooltip=False,
    )
    date_chevron.rotate = math.pi / 2
    date_button = secondary_button(
        ft.Row(
            [
                date_text,
                lucide_icon(
                    IconName.CALENDAR,
                    color=tokens.text_primary,
                    size=tokens.icon_medium,
                    label=ui_text("tasks.open_calendar"),
                    show_tooltip=False,
                ),
                date_chevron,
            ],
            spacing=tokens.space_3,
        ),
        tokens,
        height=48,
        data={"role": "create-task-date"},
    )

    deadline_text = ft.Text(ui_text("tasks.deadline"), color=tokens.text_primary, expand=True)
    deadline_button = secondary_button(
        ft.Row(
            [
                lucide_icon(
                    IconName.CLOCK,
                    color=tokens.text_primary,
                    size=tokens.icon_medium,
                    label=ui_text("tasks.deadline"),
                    show_tooltip=False,
                ),
                deadline_text,
            ],
            spacing=tokens.space_2,
        ),
        tokens,
        tooltip=_tooltip(ui_text("tasks.deadline_time")),
        width=174,
        data={"role": "deadline-trigger"},
    )
    duration = task_duration_control(tokens)
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
        page.show_dialog(
            build_date_time_picker_dialog(
                tokens,
                initial_date=state.scheduled_date or date.today(),
                include_time=False,
                initial_time=None,
                first_day_of_week=0 if settings.first_day_of_week == "monday" else 6,
                on_apply=apply_date,
                close=pop_overlay,
            )
        )

    def apply_deadline(value: date | datetime) -> None:
        assert isinstance(value, datetime)
        state.deadline_at = value
        deadline_text.value = format_compact_datetime(value)
        deadline_text.update()

    def open_deadline(_event) -> None:
        if page is None:
            return
        settings = services.settings.get_settings.execute()
        initial = state.deadline_at
        page.show_dialog(
            build_date_time_picker_dialog(
                tokens,
                initial_date=initial.date() if initial else (state.scheduled_date or date.today()),
                include_time=True,
                initial_time=initial.time() if initial else time(0, 0),
                first_day_of_week=0 if settings.first_day_of_week == "monday" else 6,
                on_apply=apply_deadline,
                close=pop_overlay,
            )
        )

    date_button.on_click = open_date
    deadline_button.on_click = open_deadline

    def set_creation_mode(mode: TaskCreationMode) -> None:
        state.creation_mode = mode
        render_creation_selector(update=True)

    def render_creation_selector(*, update: bool = False) -> None:
        label = ui_text(f"tasks.creation.{state.creation_mode.value}")
        items = [
            ft.PopupMenuItem(
                content=ui_text(f"tasks.creation.{mode.value}"),
                checked=state.creation_mode is mode,
                on_click=lambda _event, selected=mode: set_creation_mode(selected),
                data={"role": "creation-mode-option", "mode": mode.value},
            )
            for mode in TaskCreationMode
        ]
        chevron = lucide_icon(
            IconName.CHEVRON,
            color=tokens.text_secondary,
            size=tokens.icon_small,
            label=ui_text("tasks.creation_mode"),
            show_tooltip=False,
        )
        chevron.rotate = math.pi / 2
        creation_selector_host.content = ft.PopupMenuButton(
            content=ft.Row(
                [
                    ft.Container(width=6, height=6, bgcolor=tokens.text_muted, border_radius=tokens.radius_pill),
                    ft.Text(label, color=tokens.text_secondary, size=tokens.text_small),
                    chevron,
                ],
                spacing=tokens.space_1,
                tight=True,
            ),
            items=items,
            tooltip=_tooltip(ui_text("tasks.creation_mode")),
            data={"role": "creation-mode-menu"},
        )
        if update:
            creation_selector_host.update()

    def render_stage_controls(*, update: bool = False) -> None:
        controls: list[ft.Control] = []
        for project_id in state.selected_project_ids:
            stages = stages_by_project.get(project_id, ())
            if not stages:
                state.selected_stage_ids.pop(project_id, None)
                continue
            project = project_by_id[project_id]
            selector = select_field(
                tokens,
                value=str(state.selected_stage_ids.get(project_id, 0)),
                options=[
                    ft.DropdownOption(
                        "0",
                        f"PS-{project.title}: {ui_text('tasks.project_stage_none')}",
                    ),
                    *[
                        ft.DropdownOption(
                            str(stage.id),
                            f"PS-{project.title}: {_stage_label(stage)}",
                        )
                        for stage in stages
                    ],
                ],
                tooltip=_tooltip(ui_text("tasks.project_stage", project=project.title)),
                width=558,
                data={"role": "project-stage", "project_id": project_id},
            )

            def select_stage(_event, *, selected_project_id=project_id, field=selector) -> None:
                selected = int(field.value or 0)
                if selected:
                    state.selected_stage_ids[selected_project_id] = selected
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
                            width=10,
                            height=10,
                            bgcolor=project.color,
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
        project_chevron = lucide_icon(
            IconName.CHEVRON,
            color=tokens.text_primary,
            size=tokens.icon_small,
            label=ui_text("tasks.projects"),
            show_tooltip=False,
        )
        project_chevron.rotate = math.pi / 2
        project_selector_host.content = ft.PopupMenuButton(
            content=ft.Container(
                ft.Row(
                    [
                        ft.Container(
                            ft.Text(str(count), color=tokens.on_accent, size=tokens.text_small),
                            bgcolor=tokens.text_primary,
                            border_radius=tokens.radius_small,
                            padding=ft.Padding.symmetric(horizontal=tokens.space_2, vertical=tokens.space_1),
                            visible=count > 0,
                        ),
                        ft.Text(label, color=tokens.text_primary, expand=True),
                        project_chevron,
                    ],
                    spacing=tokens.space_2,
                ),
                height=tokens.control_height,
                width=174,
                padding=ft.Padding.symmetric(horizontal=tokens.space_3),
                border=ft.Border.all(tokens.border_width, tokens.border_default),
                border_radius=tokens.radius_medium,
                bgcolor=tokens.control_background,
            ),
            items=items or [ft.PopupMenuItem(content=ui_text("tasks.projects_none"), disabled=True)],
            data={"role": "project-menu"},
        )
        if update:
            project_selector_host.update()

    def new_checklist_item() -> ChecklistFormItem:
        item = ChecklistFormItem(state.next_checklist_id)
        state.next_checklist_id += 1
        return item

    def all_checklist_items(items: list[ChecklistFormItem] | None = None) -> list[ChecklistFormItem]:
        flattened: list[ChecklistFormItem] = []
        for item in state.checklist_items if items is None else items:
            flattened.append(item)
            flattened.extend(all_checklist_items(item.children))
        return flattened

    def remove_checklist_item(client_id: int, items: list[ChecklistFormItem] | None = None) -> bool:
        target = state.checklist_items if items is None else items
        for index, item in enumerate(target):
            if item.client_id == client_id:
                target.pop(index)
                return True
            if remove_checklist_item(client_id, item.children):
                return True
        return False

    def checklist_row(item: ChecklistFormItem, depth: int) -> ft.Control:
        completed = checkbox(tokens, value=item.completed, tooltip=_tooltip(ui_text("tasks.checklist_item")))
        field_control = text_field(
            tokens,
            compact=True,
            value=item.title,
            hint_text=ui_text("tasks.checklist_item"),
            expand=True,
            data={"role": "checklist-item-title", "client_id": item.client_id},
        )
        completed.data = {"role": "checklist-item-completed", "client_id": item.client_id}

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
        return ft.Container(
            ft.Row(
                [
                    completed,
                    field_control,
                    _icon_button(
                        lucide_icon(
                            IconName.PLUS,
                            color=tokens.text_primary,
                            size=tokens.icon_medium,
                            label=ui_text("tasks.add_checklist_child"),
                            show_tooltip=False,
                        ),
                        tokens,
                        on_click=add_child,
                        label=ui_text("tasks.add_checklist_child"),
                    ),
                    _icon_button(
                        lucide_icon(
                            IconName.CLOSE,
                            color=tokens.text_secondary,
                            size=tokens.icon_medium,
                            label=ui_text("tasks.remove_checklist_item"),
                            show_tooltip=False,
                        ),
                        tokens,
                        on_click=remove,
                        label=ui_text("tasks.remove_checklist_item"),
                    ),
                ],
                spacing=tokens.space_2,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            margin=ft.Margin.only(left=depth * tokens.space_8),
            data={"role": "checklist-item", "client_id": item.client_id, "depth": depth},
        )

    def checklist_controls(items: list[ChecklistFormItem], depth: int = 0) -> list[ft.Control]:
        controls: list[ft.Control] = []
        for item in items:
            controls.append(checklist_row(item, depth))
            controls.extend(checklist_controls(item.children, depth + 1))
        return controls

    def disable_checklist(_event=None) -> None:
        state.checklist_enabled = False
        state.checklist_items.clear()
        render_advanced(update=True)

    def add_checklist(_event=None) -> None:
        state.checklist_enabled = True
        if not state.checklist_items:
            state.checklist_items.append(new_checklist_item())
        render_advanced(update=True)

    def add_root_item(_event=None) -> None:
        state.checklist_items.append(new_checklist_item())
        render_checklist(update=True)

    def render_checklist(*, update: bool = False) -> None:
        items = all_checklist_items()
        completed_count = sum(item.completed for item in items)
        progress = completed_count / len(items) if items else 0.0
        checklist_host.visible = state.checklist_enabled
        checklist_host.content = ft.Column(
            [
                ft.Row(
                    [
                        checkbox(tokens, label=ui_text("tasks.checklist"), value=True, on_change=disable_checklist),
                        ft.Container(expand=True),
                        secondary_button(
                            ui_text("tasks.remove_checklist"),
                            tokens,
                            compact=True,
                            on_click=disable_checklist,
                        ),
                    ],
                    spacing=tokens.space_2,
                ),
                ft.Row(
                    [
                        ft.Text(
                            ui_text("tasks.checklist_progress", percent=round(progress * 100)),
                            color=tokens.text_primary,
                            size=tokens.text_small,
                        ),
                        ft.ProgressBar(
                            value=progress,
                            color=tokens.text_primary,
                            bgcolor=tokens.border_default,
                            border_radius=tokens.radius_pill,
                            expand=True,
                        ),
                    ],
                    spacing=tokens.space_2,
                ),
                *checklist_controls(state.checklist_items),
                secondary_button(
                    ui_text("tasks.add_checklist_item"),
                    tokens,
                    compact=True,
                    on_click=add_root_item,
                    data={"role": "add-checklist-item"},
                ),
            ],
            spacing=tokens.space_2,
            tight=True,
        )
        if update:
            checklist_host.update()

    checklist_toggle = secondary_button(
        ft.Row(
            [
                lucide_icon(
                    IconName.CHECK,
                    color=tokens.text_primary,
                    size=tokens.icon_medium,
                    label=ui_text("tasks.checklist"),
                    show_tooltip=False,
                ),
                ft.Text(ui_text("tasks.checklist"), color=tokens.text_primary),
            ],
            spacing=tokens.space_2,
            tight=True,
        ),
        tokens,
        on_click=add_checklist,
        width=174,
        data={"role": "checklist-toggle"},
    )

    def render_advanced(*, update: bool = False) -> None:
        advanced_host.visible = state.advanced_expanded
        if state.advanced_expanded:
            render_project_selector()
            render_stage_controls()
            render_checklist()
            advanced_host.content = ft.Column(
                [
                    ft.Row(
                        [
                            project_selector_host,
                            deadline_button,
                            estimate_control if state.checklist_enabled else checklist_toggle,
                        ],
                        spacing=tokens.space_3,
                    ),
                    *(
                        []
                        if state.checklist_enabled
                        else [
                            ft.Container(
                                ft.Row(
                                    [
                                        ft.Text(ui_text("tasks.estimated_time"), color=tokens.text_primary, expand=True),
                                        estimate_control,
                                    ],
                                    spacing=tokens.space_3,
                                ),
                                border=ft.Border.all(tokens.border_width, tokens.border_default),
                                border_radius=tokens.radius_medium,
                                bgcolor=tokens.control_background,
                                padding=ft.Padding.only(left=tokens.space_3),
                            )
                        ]
                    ),
                    stage_host,
                    checklist_host,
                ],
                spacing=tokens.space_3,
                tight=True,
            )
        if update:
            advanced_host.update()

    advanced_label = ft.Text(ui_text("tasks.advanced_options"), color=tokens.text_secondary)

    def toggle_advanced(_event) -> None:
        state.advanced_expanded = not state.advanced_expanded
        advanced_label.value = (
            ui_text("tasks.hide_advanced_options")
            if state.advanced_expanded
            else ui_text("tasks.advanced_options")
        )
        advanced_label.update()
        render_advanced(update=True)

    advanced_toggle = ft.Container(
        ft.Row(
            [
                ft.Divider(color=tokens.border_strong, expand=True),
                advanced_label,
                ft.Divider(color=tokens.border_strong, expand=True),
            ],
            spacing=tokens.space_3,
        ),
        on_click=toggle_advanced,
        data={"role": "advanced-toggle"},
    )

    create_button = primary_button(
        ui_text("tasks.create_save"),
        tokens,
        width=370,
        data={"role": "create-task-save"},
    )
    cancel_button = secondary_button(
        ui_text("tasks.cancel"),
        tokens,
        on_click=lambda _event: close(),
        width=178,
        data={"role": "create-task-cancel"},
    )

    def estimated_minutes_value() -> int | None:
        return duration_minutes_value(estimate_hours.value, estimate_minutes.value)

    def create(_event) -> None:
        title.error = None
        estimate_hours.error = None
        estimate_minutes.error = None
        message.value = ""
        try:
            assignments = tuple(
                TaskProjectAssignment(project_id, state.selected_stage_ids.get(project_id))
                for project_id in state.selected_project_ids
            )
            task = services.tasks.create_task.execute(
                assignments[0].project_id if assignments else None,
                title.value or "",
                description=description.value or "",
                schedule_start_date=state.scheduled_date,
                deadline_at=state.deadline_at,
                estimate_minutes=estimated_minutes_value(),
                project_links=assignments,
                creation_mode=state.creation_mode,
                checklist_items=(
                    _checklist_drafts(state.checklist_items)
                    if state.checklist_enabled
                    else ()
                ),
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
        else:
            on_created(task)

    create_button.on_click = create
    title.on_submit = create
    render_creation_selector()
    render_advanced()

    close_button = _icon_button(
        lucide_icon(
            IconName.CLOSE,
            color=tokens.text_primary,
            size=tokens.icon_large,
            label=ui_text("tasks.cancel"),
            show_tooltip=False,
        ),
        tokens,
        on_click=lambda _event: close(),
        label=ui_text("tasks.cancel"),
    )
    close_button.data = {"role": "create-task-close"}
    return ft.AlertDialog(
        modal=True,
        title=ft.Row(
            [
                ft.Text(
                    ui_text("tasks.create_title"),
                    color=tokens.text_primary,
                    size=tokens.text_title,
                    weight=ft.FontWeight.W_700,
                    expand=True,
                ),
                creation_selector_host,
                close_button,
            ],
            spacing=tokens.space_3,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        content=ft.Container(
            ft.Column(
                [title, description, date_button, advanced_toggle, advanced_host, message],
                spacing=tokens.space_3,
                tight=True,
                scroll=ft.ScrollMode.AUTO,
            ),
            width=558,
        ),
        actions=[ft.Row([create_button, cancel_button], spacing=tokens.space_2)],
        title_padding=ft.Padding.only(left=tokens.space_5, top=tokens.space_5, right=tokens.space_3),
        content_padding=ft.Padding.symmetric(horizontal=tokens.space_5, vertical=tokens.space_4),
        actions_padding=ft.Padding.only(left=tokens.space_5, right=tokens.space_5, bottom=tokens.space_5),
        bgcolor=tokens.surface_elevated,
        shape=ft.RoundedRectangleBorder(radius=tokens.radius_large),
        scrollable=False,
        data={"role": "create-task-dialog", "state": state},
    )
