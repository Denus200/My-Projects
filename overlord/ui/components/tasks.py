from __future__ import annotations

from collections.abc import Callable
from datetime import date, datetime, time, timedelta
import re

import flet as ft

from overlord.app.read_models import TaskListItem
from overlord.app.services import ApplicationServices
from overlord.modules.projects.domain import Project
from overlord.modules.tasks.domain import Task, TaskBoardColumn, TaskLifecycle, board_column
from overlord.ui.components.controls import choice_chip, primary_button, secondary_button, select_field, tertiary_button, text_field
from overlord.ui.components.status import state_chip
from overlord.ui.design_system.icons import IconName, lucide_icon
from overlord.ui.design_system.tokens import ThemeTokens
from overlord.ui.strings import format_short_date, ui_error, ui_text


def _date_value(value: str) -> date:
    try:
        return date.fromisoformat(value.strip())
    except ValueError as error:
        raise ValueError(ui_text("tasks.date_error")) from error


def _time_value(value: str) -> time:
    try:
        return time.fromisoformat(value.strip())
    except ValueError as error:
        raise ValueError(ui_text("tasks.time_error")) from error


def _datetime_value(value: str) -> datetime:
    try:
        return datetime.fromisoformat(value.strip().replace(" ", "T"))
    except ValueError as error:
        raise ValueError(ui_text("tasks.datetime_error")) from error


def _display_date(value: date) -> str:
    return value.strftime("%d.%m.%Y")


def _flexible_date_value(value: str) -> date:
    clean = value.strip()
    digits = re.sub(r"\D", "", clean)
    try:
        if len(digits) == 8 and clean == digits:
            return date(int(digits[4:]), int(digits[2:4]), int(digits[:2]))
        for separator in (".", "/", "-"):
            parts = clean.split(separator)
            if len(parts) == 3 and len(parts[0]) <= 2:
                return date(int(parts[2]), int(parts[1]), int(parts[0]))
        return date.fromisoformat(clean)
    except (ValueError, TypeError) as error:
        raise ValueError(ui_text("tasks.human_date_error")) from error


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
    preset_start_date: date | None = None,
    preset_when: str | None = None,
    page: ft.Page | None = None,
) -> ft.AlertDialog:
    today = date.today()
    tomorrow = today + timedelta(days=1)
    settings = services.settings.get_settings.execute()
    first_day = 0 if settings.first_day_of_week == "monday" else 6
    week_end = today + timedelta(days=(first_day + 6 - today.weekday()) % 7)

    if preset_when is not None:
        initial_when = preset_when
    elif preset_start_date == tomorrow:
        initial_when = "tomorrow"
    elif preset_start_date is not None and preset_start_date != today:
        initial_when = "choose_date"
    else:
        initial_when = "today"

    title = text_field(tokens, label=ui_text("tasks.field_title"), autofocus=True)
    description = text_field(
        tokens,
        label=ui_text("tasks.field_description"),
        multiline=True,
        min_lines=2,
        max_lines=3,
    )
    project = select_field(
        tokens,
        label=ui_text("tasks.field_project"),
        value=str(selected_project_id) if selected_project_id is not None else "none",
        options=_project_options(projects),
    )
    when = select_field(
        tokens,
        label=ui_text("tasks.when"),
        value=initial_when,
        options=[
            ft.DropdownOption("today", ui_text("tasks.when.today")),
            ft.DropdownOption("tomorrow", ui_text("tasks.when.tomorrow")),
            ft.DropdownOption("this_week", ui_text("tasks.when.this_week")),
            ft.DropdownOption("no_date", ui_text("tasks.when.no_date")),
            ft.DropdownOption("choose_date", ui_text("tasks.when.choose_date")),
        ],
    )
    custom_date = text_field(
        tokens,
        label=ui_text("tasks.custom_date"),
        value=_display_date(preset_start_date) if initial_when == "choose_date" and preset_start_date else "",
        hint_text=ui_text("tasks.date_hint"),
        expand=True,
    )
    custom_date_row = ft.Row(
        [
            custom_date,
            tertiary_button(ui_text("tasks.open_calendar"), tokens),
        ],
        spacing=tokens.space_2,
        visible=initial_when == "choose_date",
    )

    time_mode = select_field(
        tokens,
        label=ui_text("tasks.time"),
        value="none",
        options=[
            ft.DropdownOption("none", ui_text("tasks.not_set")),
            ft.DropdownOption("custom", ui_text("tasks.set_time")),
        ],
    )
    start_time = text_field(
        tokens,
        label=ui_text("tasks.field_start_time"),
        hint_text="HH:MM",
        visible=False,
        expand=True,
    )
    time_button = tertiary_button(ui_text("tasks.choose_time"), tokens, visible=False)
    time_row = ft.Row([start_time, time_button], spacing=tokens.space_2, visible=False)

    deadline_mode = select_field(
        tokens,
        label=ui_text("tasks.deadline"),
        value="none",
        options=[
            ft.DropdownOption("none", ui_text("tasks.not_set")),
            ft.DropdownOption("custom", ui_text("tasks.set_deadline")),
        ],
    )
    deadline_date = text_field(
        tokens,
        label=ui_text("tasks.deadline_date"),
        hint_text=ui_text("tasks.date_hint"),
        expand=True,
    )
    deadline_button = tertiary_button(ui_text("tasks.open_calendar"), tokens)
    deadline_row = ft.Row([deadline_date, deadline_button], spacing=tokens.space_2, visible=False)

    estimate_mode = select_field(
        tokens,
        label=ui_text("tasks.field_estimate"),
        value="none",
        options=[
            ft.DropdownOption("none", ui_text("tasks.not_set")),
            ft.DropdownOption("15", ui_text("tasks.estimate.15")),
            ft.DropdownOption("30", ui_text("tasks.estimate.30")),
            ft.DropdownOption("60", ui_text("tasks.estimate.60")),
            ft.DropdownOption("custom", ui_text("tasks.estimate.custom")),
        ],
    )
    custom_estimate = text_field(
        tokens,
        label=ui_text("tasks.estimate_custom"),
        keyboard_type=ft.KeyboardType.NUMBER,
        visible=False,
    )
    # Flet toggles Chip.selected internally before on_select runs; the no-op
    # handler enables selection without fighting that built-in behavior.
    importance = choice_chip(ui_text("tasks.important"), tokens, on_select=lambda _event: None)
    urgency = choice_chip(ui_text("tasks.urgent"), tokens, on_select=lambda _event: None)
    advanced = ft.Container(
        ft.Column(
            [
                ft.ResponsiveRow(
                    [
                        ft.Container(time_mode, col={"sm": 12, "md": 4}),
                        ft.Container(deadline_mode, col={"sm": 12, "md": 4}),
                        ft.Container(estimate_mode, col={"sm": 12, "md": 4}),
                    ],
                    spacing=tokens.space_3,
                    run_spacing=tokens.space_3,
                ),
                time_row,
                deadline_row,
                custom_estimate,
                ft.Column(
                    [
                        ft.Text(ui_text("tasks.priority"), color=tokens.text_muted, size=tokens.text_small),
                        ft.Row([importance, urgency], spacing=tokens.space_2, wrap=True),
                    ],
                    spacing=tokens.space_1,
                ),
            ],
            spacing=tokens.space_3,
        ),
        visible=False,
    )
    advanced_label = ft.Text(ui_text("tasks.advanced_options"), color=tokens.accent_primary)
    message = ft.Text("", color=tokens.error.text, size=tokens.text_small)

    def set_picker_value(field: ft.TextField, picker: ft.DatePicker) -> None:
        value = picker.value
        if isinstance(value, datetime):
            value = value.date()
        if isinstance(value, date):
            field.value = _display_date(value)
            field.error = None
            field.update()

    def normalize_date(field: ft.TextField) -> None:
        raw = (field.value or "").strip()
        if not raw:
            return
        try:
            field.value = _display_date(_flexible_date_value(raw))
            field.error = None
            field.update()
        except ValueError:
            # Creation owns validation feedback; leaving the field must not
            # interrupt a user who is still typing a date.
            return

    custom_picker = ft.DatePicker(
        value=preset_start_date or today,
        current_date=preset_start_date or today,
        modal=True,
        help_text=ui_text("tasks.choose_date"),
        cancel_text=ui_text("tasks.cancel"),
        confirm_text=ui_text("common.edit"),
    )
    deadline_picker = ft.DatePicker(
        value=today,
        current_date=today,
        modal=True,
        help_text=ui_text("tasks.set_deadline"),
        cancel_text=ui_text("tasks.cancel"),
        confirm_text=ui_text("common.edit"),
    )
    custom_picker.on_change = lambda _event: set_picker_value(custom_date, custom_picker)
    deadline_picker.on_change = lambda _event: set_picker_value(deadline_date, deadline_picker)
    custom_date.on_blur = lambda _event: normalize_date(custom_date)
    deadline_date.on_blur = lambda _event: normalize_date(deadline_date)

    time_picker = ft.TimePicker(
        modal=True,
        help_text=ui_text("tasks.choose_time"),
        cancel_text=ui_text("tasks.cancel"),
        confirm_text=ui_text("common.edit"),
    )

    def set_time(_event) -> None:
        if time_picker.value is not None:
            start_time.value = time_picker.value.strftime("%H:%M")
            start_time.error = None
            start_time.update()

    time_picker.on_change = set_time

    def show_picker(picker) -> None:
        if page is not None:
            page.show_dialog(picker)

    custom_date_row.controls[1].on_click = lambda _event: show_picker(custom_picker)
    deadline_button.on_click = lambda _event: show_picker(deadline_picker)
    time_button.on_click = lambda _event: show_picker(time_picker)

    def choose_when(_event) -> None:
        custom_date_row.visible = when.value == "choose_date"
        custom_date_row.update()
        if custom_date_row.visible and page is not None and not (custom_date.value or "").strip():
            show_picker(custom_picker)

    def choose_time_mode(_event) -> None:
        selected = time_mode.value == "custom"
        time_row.visible = selected
        start_time.visible = selected
        time_button.visible = selected
        time_row.update()
        if selected and page is not None and not (start_time.value or "").strip():
            show_picker(time_picker)

    def choose_deadline_mode(_event) -> None:
        deadline_row.visible = deadline_mode.value == "custom"
        deadline_row.update()
        if deadline_row.visible and page is not None and not (deadline_date.value or "").strip():
            show_picker(deadline_picker)

    def choose_estimate(_event) -> None:
        custom_estimate.visible = estimate_mode.value == "custom"
        custom_estimate.update()

    def toggle_advanced(_event) -> None:
        advanced.visible = not advanced.visible
        advanced_label.value = (
            ui_text("tasks.hide_advanced_options")
            if advanced.visible
            else ui_text("tasks.advanced_options")
        )
        advanced.update()
        advanced_label.update()

    when.on_select = choose_when
    time_mode.on_select = choose_time_mode
    deadline_mode.on_select = choose_deadline_mode
    estimate_mode.on_select = choose_estimate

    create_button = primary_button(ui_text("tasks.create"), tokens, disabled=True)

    def update_create_enabled(_event=None) -> None:
        create_button.disabled = not bool((title.value or "").strip())
        create_button.update()

    def create(_event) -> None:
        title.error = None
        custom_date.error = None
        start_time.error = None
        deadline_date.error = None
        custom_estimate.error = None
        message.value = ""
        try:
            if when.value == "today":
                chosen_start, chosen_end = today, None
            elif when.value == "tomorrow":
                chosen_start, chosen_end = tomorrow, None
            elif when.value == "this_week":
                chosen_start, chosen_end = today, week_end
            elif when.value == "no_date":
                chosen_start, chosen_end = None, None
            else:
                chosen_start = _flexible_date_value(custom_date.value or "")
                chosen_end = None

            chosen_time = (
                _time_value(start_time.value or "")
                if time_mode.value == "custom" and (start_time.value or "").strip()
                else None
            )
            if deadline_mode.value == "custom":
                try:
                    chosen_deadline = datetime.combine(
                        _flexible_date_value(deadline_date.value or ""),
                        time.max,
                    )
                except ValueError:
                    deadline_date.error = ui_text("tasks.human_date_error")
                    deadline_date.update()
                    return
            else:
                chosen_deadline = None
            if estimate_mode.value == "custom":
                try:
                    minutes = int(custom_estimate.value or "")
                except ValueError as error:
                    raise ValueError(ui_text("tasks.estimate_integer_error")) from error
            elif estimate_mode.value == "none":
                minutes = None
            else:
                minutes = int(estimate_mode.value)

            task = services.tasks.create_task.execute(
                _project_id(project.value),
                title.value or "",
                description=description.value or "",
                schedule_start_date=chosen_start,
                schedule_start_time=chosen_time,
                schedule_end_date=chosen_end,
                deadline_at=chosen_deadline,
                importance=True if importance.selected else None,
                urgency=True if urgency.selected else None,
                estimate_minutes=minutes,
            )
            on_created(task)
        except Exception as error:
            raw = str(error).lower()
            text = ui_error(error)
            if "title" in raw:
                title.error = text
                title.update()
            elif "estimate" in raw:
                custom_estimate.error = text
                custom_estimate.update()
            elif "time" in raw:
                start_time.error = text
                start_time.update()
            elif "deadline" in raw:
                deadline_date.error = text
                deadline_date.update()
            elif "date" in raw:
                custom_date.error = text
                custom_date.update()
            else:
                message.value = text
                message.update()

    create_button.on_click = create
    title.on_change = update_create_enabled
    title.on_submit = create

    return ft.AlertDialog(
        modal=True,
        title=ui_text("tasks.create_title"),
        content=ft.Container(
            ft.Column(
                [
                    title,
                    description,
                    project,
                    when,
                    custom_date_row,
                    tertiary_button(advanced_label, tokens, on_click=toggle_advanced),
                    advanced,
                    message,
                ],
                spacing=tokens.space_3,
                tight=True,
            ),
            width=520,
        ),
        actions=[
            secondary_button(ui_text("tasks.cancel"), tokens, on_click=lambda _event: close()),
            create_button,
        ],
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
        metadata.append(ui_text("tasks.blocked") if item.open_blockers == 1 else ui_text("tasks.blockers", count=item.open_blockers))
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


def task_card(
    item: TaskListItem,
    tokens: ThemeTokens,
    *,
    on_complete: Callable[[object], None] | None = None,
    on_edit: Callable[[object], None] | None = None,
    drag_handle: ft.Control | None = None,
    compact: bool = False,
) -> ft.Container:
    task = item.task
    metadata = [item.project_title or ui_text("tasks.no_project")]
    if task.schedule_start_time:
        metadata.append(task.schedule_start_time.strftime("%H:%M"))
    if task.schedule_end_time:
        metadata.append(ui_text("tasks.until_time", time=task.schedule_end_time.strftime("%H:%M")))
    metadata.extend(item.cycle_titles)
    if item.open_blockers:
        metadata.append(ui_text("tasks.blocked"))
    actions: list[ft.Control] = []
    if on_complete and task.lifecycle_status is not TaskLifecycle.COMPLETED:
        actions.append(
            tertiary_button(
                lucide_icon(
                    IconName.CHECK,
                    color=tokens.accent_primary,
                    size=tokens.icon_small,
                    label=ui_text("common.complete_task"),
                ),
                tokens,
                on_click=on_complete,
                tooltip=ui_text("common.complete_named", name=task.title),
            )
        )
    title = ft.Text(
        task.title,
        color=tokens.text_muted if task.lifecycle_status is TaskLifecycle.COMPLETED else tokens.text_primary,
        weight=ft.FontWeight.W_600,
        size=tokens.text_small if compact else tokens.text_body,
        max_lines=2 if compact else 3,
        overflow=ft.TextOverflow.ELLIPSIS,
    )
    text_body = ft.Column(
        [
            title,
            ft.Text(
                ui_text("common.metadata_separator").join(metadata),
                color=tokens.text_muted,
                size=tokens.text_small,
                max_lines=2,
                overflow=ft.TextOverflow.ELLIPSIS,
            ),
        ],
        spacing=tokens.space_1,
        tight=True,
    )
    body: ft.Control = ft.GestureDetector(
        text_body,
        on_tap=on_edit,
        mouse_cursor=ft.MouseCursor.CLICK if on_edit else ft.MouseCursor.BASIC,
        expand=True,
        data={"role": "task-body", "task_id": task.id},
    )
    return ft.Container(
        ft.Row(
            [body, *actions, *([drag_handle] if drag_handle is not None else [])],
            spacing=tokens.space_1,
            vertical_alignment=ft.CrossAxisAlignment.START,
        ),
        bgcolor=tokens.surface_elevated,
        border=ft.Border.all(tokens.border_width, tokens.border_default),
        border_radius=tokens.radius_medium,
        padding=tokens.space_2 if compact else tokens.space_3,
        data={"role": "workspace-task-card", "task_id": task.id},
    )
