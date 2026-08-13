from __future__ import annotations

import asyncio
import calendar
from collections.abc import Callable
from datetime import date, datetime, timedelta

import flet as ft

from overlord.app.read_models import TaskListItem
from overlord.app.services import ApplicationServices
from overlord.modules.projects.domain import Project
from overlord.modules.tasks.domain import (
    Task,
    TaskBoardColumn,
    TaskLifecycle,
    board_column,
    is_scheduled_for_day,
)
from overlord.ui.components.controls import (
    primary_button,
    search_field,
    secondary_button,
    select_field,
    selection_button,
    tertiary_button,
)
from overlord.ui.components.feedback import show_success
from overlord.ui.components.layout import page_container
from overlord.ui.components.reorder import draggable_task_handle
from overlord.ui.components.tasks import build_quick_task_dialog, task_card
from overlord.ui.design_system.icons import IconName, lucide_icon
from overlord.ui.design_system.tokens import ThemeTokens
from overlord.ui.state import AppSessionState, TaskFilterState
from overlord.ui.strings import (
    format_date_with_year,
    format_month_year,
    format_weekday_name,
    ui_error,
    ui_text,
)


TaskEditorBuilder = Callable[..., ft.Control]


def _week_start(day: date, first_day: int) -> date:
    return day - timedelta(days=(day.weekday() - first_day) % 7)


def _month_shift(day: date, offset: int) -> date:
    month_index = day.year * 12 + day.month - 1 + offset
    return date(month_index // 12, month_index % 12 + 1, 1)


def _month_weeks(day: date, first_day: int) -> tuple[tuple[date, ...], ...]:
    first = day.replace(day=1)
    last = day.replace(day=calendar.monthrange(day.year, day.month)[1])
    grid_start = _week_start(first, first_day)
    grid_end = _week_start(last, first_day) + timedelta(days=6)
    days = tuple(grid_start + timedelta(days=offset) for offset in range((grid_end - grid_start).days + 1))
    return tuple(tuple(days[index:index + 7]) for index in range(0, len(days), 7))


def build_tasks_workspace(
    services: ApplicationServices,
    tokens: ThemeTokens,
    state: AppSessionState,
    refresh,
    report_error,
    page: ft.Page | None,
    editor_builder: TaskEditorBuilder,
) -> ft.Control:
    projects = services.projects.list_projects.execute()
    filter_state = state.task_filters or TaskFilterState()
    state.task_filters = filter_state
    settings = services.settings.get_settings.execute()
    first_day = 0 if settings.first_day_of_week == "monday" else 6
    today = date.today()
    try:
        anchor = date.fromisoformat(state.task_calendar_anchor) if state.task_calendar_anchor else today
    except ValueError:
        anchor = today
    if state.task_view_mode not in {"kanban", "week", "month"}:
        state.task_view_mode = "kanban"

    search = search_field(tokens, label=ui_text("tasks.search"), value=filter_state.search, expand=True)
    project_filter = select_field(
        tokens,
        searchable=True,
        label=ui_text("tasks.project_filter"),
        value=filter_state.project,
        options=[
            ft.DropdownOption("all", ui_text("tasks.project_all")),
            ft.DropdownOption("none", ui_text("tasks.no_project")),
            *[ft.DropdownOption(str(project.id), project.title) for project in projects],
        ],
    )
    mode_row = ft.Row(spacing=tokens.space_2, wrap=True, data={"role": "task-view-modes"})
    calendar_header = ft.Row(
        spacing=tokens.space_2,
        wrap=True,
        visible=False,
        data={"role": "task-calendar-header"},
    )
    view_host = ft.Container(expand=True, data={"role": "task-view-host"})

    def close_dialog() -> None:
        if page is not None:
            page.pop_dialog()

    def filtered_items() -> tuple[TaskListItem, ...]:
        filter_state.search = search.value or ""
        filter_state.project = project_filter.value or "all"
        filters: dict[str, object] = {"search": filter_state.search}
        if filter_state.project == "none":
            filters["without_project"] = True
        elif filter_state.project != "all":
            filters["project_id"] = int(filter_state.project)
        return services.tasks.list_tasks.execute(**filters)

    def open_create(
        _event=None,
        *,
        scheduled_for: date | None = None,
        when_value: str | None = None,
    ) -> None:
        if page is None:
            return

        def created(_task: Task) -> None:
            close_dialog()
            render(update=True)
            show_success(page, tokens, ui_text("tasks.created"))

        page.show_dialog(
            build_quick_task_dialog(
                services,
                projects,
                tokens,
                created,
                close_dialog,
                preset_start_date=scheduled_for,
                preset_when=when_value,
                page=page,
            )
        )

    def open_editor(task_id: int) -> None:
        if page is None:
            return

        def saved() -> None:
            close_dialog()
            render(update=True)
            show_success(page, tokens, ui_text("tasks.updated"))

        def changed() -> None:
            close_dialog()
            render(update=True)
            open_editor(task_id)

        page.show_dialog(
            ft.AlertDialog(
                modal=True,
                title=ui_text("tasks.edit_title"),
                content=ft.Container(
                    editor_builder(
                        services,
                        projects,
                        task_id,
                        tokens,
                        saved,
                        changed,
                        close_dialog,
                        report_error,
                    ),
                    width=720,
                ),
                bgcolor=tokens.surface_elevated,
                scrollable=True,
            )
        )

    def complete(task_id: int) -> None:
        try:
            services.tasks.complete_task.execute(task_id)
            render(update=True)
        except Exception as error:
            report_error(ui_error(error))

    def item_card(
        item: TaskListItem,
        *,
        compact: bool = False,
        drag_handle: ft.Control | None = None,
    ) -> ft.Control:
        return task_card(
            item,
            tokens,
            compact=compact,
            drag_handle=drag_handle,
            on_edit=lambda _event, task_id=item.task.id: open_editor(task_id),
            on_complete=lambda _event, task_id=item.task.id: complete(task_id),
        )

    def drag_payload(event) -> dict[str, object] | None:
        source = getattr(event, "src", None)
        payload = getattr(source, "data", None)
        return payload if isinstance(payload, dict) else None

    def ordered_items(column: TaskBoardColumn, items: tuple[TaskListItem, ...]) -> tuple[TaskListItem, ...]:
        order = state.task_card_order.setdefault(column.value, [])
        if column is TaskBoardColumn.IN_PROGRESS and not order:
            persisted_today = services.dashboard.execute(today).today_tasks
            order.extend(
                item.task.id
                for item in persisted_today
                if board_column(item.task) is TaskBoardColumn.IN_PROGRESS
            )
        present = {item.task.id for item in items}
        order[:] = [task_id for task_id in order if task_id in present]
        order.extend(item.task.id for item in items if item.task.id not in order)
        by_id = {item.task.id: item for item in items}
        return tuple(by_id[task_id] for task_id in order)

    def persist_today_suborder() -> None:
        """Reuse persisted per-day ordering for the Kanban column that represents Today."""
        scheduled = list(services.dashboard.execute(today).today_tasks)
        desired = [
            task_id
            for task_id in state.task_card_order.get(TaskBoardColumn.IN_PROGRESS.value, [])
            if any(item.task.id == task_id for item in scheduled)
        ]
        desired_set = set(desired)
        desired_iter = iter(desired)
        ordered_ids: list[int] = []
        for item in scheduled:
            if item.task.id in desired_set:
                ordered_ids.append(next(desired_iter))
            else:
                ordered_ids.append(item.task.id)
        if ordered_ids:
            services.tasks.reorder_for_day.execute(today, tuple(ordered_ids))

    def move_card(task_id: int, target: TaskBoardColumn, before_task_id: int | None = None) -> None:
        try:
            current = services.tasks.get_editor.execute(task_id).task
            source = board_column(current)
            if source is not target:
                services.tasks.move_to_board_column.execute(task_id, target)
            for order in state.task_card_order.values():
                if task_id in order:
                    order.remove(task_id)
            target_order = state.task_card_order.setdefault(target.value, [])
            if before_task_id in target_order:
                target_order.insert(target_order.index(before_task_id), task_id)
            else:
                target_order.append(task_id)
            if source is TaskBoardColumn.IN_PROGRESS or target is TaskBoardColumn.IN_PROGRESS:
                persist_today_suborder()
            render(update=True)
            if page is not None:
                show_success(page, tokens, ui_text("tasks.moved"))
        except Exception as error:
            report_error(ui_error(error))

    def accept_card(event, target: TaskBoardColumn, before_task_id: int | None = None) -> None:
        payload = drag_payload(event)
        if payload and payload.get("kind") == "task":
            move_card(int(payload["task_id"]), target, before_task_id)

    def reorder_column(source: TaskBoardColumn, target: TaskBoardColumn) -> None:
        order = state.task_column_order
        if source.value not in order or target.value not in order or source is target:
            return
        order.remove(source.value)
        order.insert(order.index(target.value), source.value)
        render(update=True)

    def accept_column(event, target: TaskBoardColumn) -> None:
        payload = drag_payload(event)
        if payload and payload.get("kind") == "column":
            reorder_column(TaskBoardColumn(str(payload["column"])), target)

    def draggable_card(item: TaskListItem, column: TaskBoardColumn) -> ft.Control:
        feedback = ft.Container(
            ft.Column(
                [
                    ft.Text(
                        item.task.title,
                        color=tokens.text_primary,
                        weight=ft.FontWeight.W_600,
                        max_lines=2,
                        overflow=ft.TextOverflow.ELLIPSIS,
                    ),
                    ft.Text(
                        item.project_title or ui_text("tasks.no_project"),
                        color=tokens.text_muted,
                        size=tokens.text_small,
                    ),
                ],
                spacing=tokens.space_1,
            ),
            width=262,
            bgcolor=tokens.surface_elevated,
            border=ft.Border.all(tokens.focus_width, tokens.accent_primary),
            border_radius=tokens.radius_medium,
            padding=tokens.space_3,
            shadow=ft.BoxShadow(blur_radius=12, color=tokens.border_strong, offset=ft.Offset(0, 4)),
        )
        handle = draggable_task_handle(
            tokens,
            label=ui_text("tasks.drag_task"),
            data={"kind": "task", "task_id": item.task.id, "column": column.value},
            feedback=feedback,
        )
        card = item_card(item, drag_handle=handle)
        return ft.DragTarget(
            card,
            group="task-card",
            data={"column": column.value, "before_task_id": item.task.id},
            on_accept=lambda event, selected=column, before=item.task.id: accept_card(event, selected, before),
        )

    def add_control(label: str, scheduled_for: date | None, when_value: str | None = None) -> ft.Control:
        return tertiary_button(
            ft.Row(
                [
                    lucide_icon(
                        IconName.PLUS,
                        color=tokens.accent_primary,
                        size=tokens.icon_small,
                        label=label,
                    ),
                    ft.Text(label, color=tokens.accent_primary, size=tokens.text_small),
                ],
                tight=True,
                spacing=tokens.space_1,
            ),
            tokens,
            on_click=lambda event, selected=scheduled_for, selected_when=when_value: open_create(
                event,
                scheduled_for=selected,
                when_value=selected_when,
            ),
        )

    def kanban_column(column: TaskBoardColumn, items: tuple[TaskListItem, ...]) -> ft.Control:
        title = ui_text(f"task_board.{column.value}")
        header = ft.Draggable(
            ft.Row(
                [
                    ft.Text(title, color=tokens.text_primary, weight=ft.FontWeight.W_600, expand=True),
                    ft.Text(str(len(items)), color=tokens.text_muted, size=tokens.text_small),
                ]
            ),
            group="kanban-column",
            data={"kind": "column", "column": column.value},
            content_feedback=ft.Container(
                ft.Text(title, color=tokens.text_primary, weight=ft.FontWeight.W_600),
                width=260,
                bgcolor=tokens.surface_inner,
                border=ft.Border.all(tokens.focus_width, tokens.accent_primary),
                border_radius=tokens.radius_medium,
                padding=tokens.space_3,
            ),
            tooltip=ui_text("tasks.drag_column"),
        )
        controls: list[ft.Control] = [
            header
        ]
        if column is TaskBoardColumn.PLANNED:
            controls.append(add_control(ui_text("tasks.add_planned"), None, "no_date"))
        elif column is TaskBoardColumn.IN_PROGRESS:
            controls.append(add_control(ui_text("tasks.add_today"), today))
        controls.extend(draggable_card(item, column) for item in ordered_items(column, items))
        if not items:
            controls.append(ft.Text(ui_text("tasks.column_empty"), color=tokens.text_muted, size=tokens.text_small))
        card_target = ft.DragTarget(
            ft.Container(
                ft.Column(controls, spacing=tokens.space_2, scroll=ft.ScrollMode.AUTO),
                width=286,
                height=610,
                bgcolor=tokens.surface_inner,
                border=ft.Border.all(tokens.border_width, tokens.border_default),
                border_radius=tokens.radius_card,
                padding=tokens.space_3,
            ),
            group="task-card",
            data={"column": column.value},
            on_accept=lambda event, selected=column: accept_card(event, selected),
        )
        return ft.DragTarget(
            card_target,
            group="kanban-column",
            data={"column": column.value},
            on_accept=lambda event, selected=column: accept_column(event, selected),
        )

    def build_kanban(items: tuple[TaskListItem, ...]) -> ft.Control:
        grouped = {column: [] for column in TaskBoardColumn}
        reference = datetime.now()
        for item in items:
            grouped[board_column(item.task, reference)].append(item)
        valid = [column.value for column in TaskBoardColumn]
        state.task_column_order[:] = [value for value in state.task_column_order if value in valid]
        state.task_column_order.extend(value for value in valid if value not in state.task_column_order)
        return ft.Row(
            [
                kanban_column(TaskBoardColumn(value), tuple(grouped[TaskBoardColumn(value)]))
                for value in state.task_column_order
            ],
            spacing=tokens.space_3,
            scroll=ft.ScrollMode.AUTO,
            vertical_alignment=ft.CrossAxisAlignment.START,
        )

    def day_cell(
        selected_day: date,
        items: tuple[TaskListItem, ...],
        *,
        compact: bool,
        in_current_month: bool = True,
    ) -> ft.Container:
        scheduled = tuple(item for item in items if is_scheduled_for_day(item.task, selected_day))
        label = str(selected_day.day) if compact else format_weekday_name(selected_day)
        if not compact:
            label = f"{label} {selected_day.day}"
        header = ft.Row(
            [
                ft.Text(
                    label,
                    color=tokens.text_primary if in_current_month else tokens.text_muted,
                    weight=ft.FontWeight.W_600,
                    size=tokens.text_small if compact else tokens.text_body,
                    expand=True,
                ),
                tertiary_button(
                    lucide_icon(
                        IconName.PLUS,
                        color=tokens.accent_primary,
                        size=tokens.icon_small,
                        label=ui_text("tasks.add_to_date", date=format_date_with_year(selected_day)),
                    ),
                    tokens,
                    on_click=lambda event, day=selected_day: open_create(event, scheduled_for=day),
                    tooltip=ui_text("tasks.add_to_date", date=format_date_with_year(selected_day)),
                ),
            ],
            spacing=tokens.space_1,
        )
        cards = [item_card(item, compact=compact) for item in scheduled]
        return ft.Container(
            ft.Column(
                [
                    header,
                    *(cards or [ft.Text(ui_text("tasks.day_empty"), color=tokens.text_muted, size=tokens.text_small)]),
                ],
                spacing=tokens.space_2,
                scroll=ft.ScrollMode.AUTO,
            ),
            expand=True if compact else None,
            width=None if compact else 250,
            height=168 if compact else 520,
            bgcolor=tokens.surface_card if in_current_month else tokens.surface_inner,
            border=ft.Border.all(
                tokens.focus_width if selected_day == today else tokens.border_width,
                tokens.accent_primary if selected_day == today else tokens.border_default,
            ),
            border_radius=tokens.radius_medium,
            padding=tokens.space_2 if compact else tokens.space_3,
        )

    def build_week(items: tuple[TaskListItem, ...]) -> ft.Control:
        start = _week_start(anchor, first_day)
        return ft.Row(
            [day_cell(start + timedelta(days=offset), items, compact=False) for offset in range(7)],
            spacing=tokens.space_2,
            scroll=ft.ScrollMode.AUTO,
            vertical_alignment=ft.CrossAxisAlignment.START,
        )

    def build_month(items: tuple[TaskListItem, ...]) -> ft.Control:
        weeks = _month_weeks(anchor, first_day)
        weekday_start = weeks[0][0]
        weekday_header = ft.Row(
            [
                ft.Container(
                    ft.Text(format_weekday_name(weekday_start + timedelta(days=offset)), color=tokens.text_muted, size=tokens.text_small),
                    expand=True,
                    padding=ft.Padding.only(left=tokens.space_2),
                )
                for offset in range(7)
            ],
            spacing=tokens.space_2,
        )
        return ft.Column(
            [
                weekday_header,
                *[
                    ft.Row(
                        [
                            day_cell(day, items, compact=True, in_current_month=day.month == anchor.month)
                            for day in week
                        ],
                        spacing=tokens.space_2,
                    )
                    for week in weeks
                ],
            ],
            spacing=tokens.space_2,
        )

    def switch_mode(mode: str) -> None:
        state.task_view_mode = mode
        render(update=True)

    def move_calendar(offset: int) -> None:
        nonlocal anchor
        if state.task_view_mode == "week":
            anchor += timedelta(days=offset * 7)
        else:
            anchor = _month_shift(anchor, offset)
        state.task_calendar_anchor = anchor.isoformat()
        render(update=True)

    def go_today(_event=None) -> None:
        nonlocal anchor
        anchor = today
        state.task_calendar_anchor = anchor.isoformat()
        render(update=True)

    def render(*, update: bool = False) -> None:
        items = filtered_items()
        mode_row.controls = [
            selection_button(ui_text("tasks.view.kanban"), tokens, selected=state.task_view_mode == "kanban", on_click=lambda _event: switch_mode("kanban")),
            selection_button(ui_text("tasks.view.week"), tokens, selected=state.task_view_mode == "week", on_click=lambda _event: switch_mode("week")),
            selection_button(ui_text("tasks.view.month"), tokens, selected=state.task_view_mode == "month", on_click=lambda _event: switch_mode("month")),
        ]
        calendar_header.visible = state.task_view_mode in {"week", "month"}
        if calendar_header.visible:
            start = _week_start(anchor, first_day)
            title = (
                ui_text(
                    "tasks.calendar.week_title",
                    start=format_date_with_year(start),
                    end=format_date_with_year(start + timedelta(days=6)),
                )
                if state.task_view_mode == "week"
                else format_month_year(anchor)
            )
            calendar_header.controls = [
                secondary_button(ui_text("tasks.previous"), tokens, on_click=lambda _event: move_calendar(-1)),
                secondary_button(ui_text("tasks.today"), tokens, on_click=go_today),
                secondary_button(ui_text("tasks.next"), tokens, on_click=lambda _event: move_calendar(1)),
                ft.Text(title, color=tokens.text_primary, weight=ft.FontWeight.W_600),
            ]
        if state.task_view_mode == "kanban":
            view_host.content = build_kanban(items)
        elif state.task_view_mode == "week":
            view_host.content = build_week(items)
        else:
            view_host.content = build_month(items)
        if update:
            mode_row.update()
            calendar_header.update()
            view_host.update()

    def apply_filters(_event=None) -> None:
        try:
            render(update=True)
        except Exception as error:
            report_error(ui_error(error))

    search.on_submit = apply_filters
    project_filter.on_select = apply_filters
    render()
    content = page_container(
        ui_text("tasks.title"),
        [
            ft.ResponsiveRow(
                [
                    ft.Container(search, col={"sm": 12, "lg": 7}),
                    ft.Container(project_filter, col={"sm": 12, "lg": 5}),
                ],
                spacing=tokens.space_3,
                run_spacing=tokens.space_3,
            ),
            mode_row,
            calendar_header,
            view_host,
        ],
        tokens,
        actions=[
            primary_button(
                ft.Row(
                    [
                        lucide_icon(IconName.PLUS, color=tokens.on_accent, size=tokens.icon_small, label=ui_text("tasks.new")),
                        ft.Text(ui_text("tasks.new"), color=tokens.on_accent),
                    ],
                    spacing=tokens.space_2,
                    tight=True,
                ),
                tokens,
                on_click=open_create,
            )
        ],
        content_spacing=tokens.space_4,
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
