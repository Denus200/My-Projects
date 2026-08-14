from __future__ import annotations

import asyncio
from collections.abc import Callable
from datetime import date, datetime, timedelta

import flet as ft

from overlord.app.read_models import TaskListItem
from overlord.app.services import ApplicationServices
from overlord.modules.tasks.domain import (
    Task,
    TaskBoardColumn,
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
from overlord.ui.components.reorder import drag_payload, draggable_task_handle
from overlord.ui.components.task_workspace_controller import TaskWorkspaceController
from overlord.ui.components.task_workspace_model import (
    group_board_items,
    month_weeks,
    scheduled_items_for_day,
    week_start,
)
from overlord.ui.components.tasks import build_quick_task_dialog, task_card
from overlord.ui.design_system.icons import IconName, lucide_icon
from overlord.ui.design_system.tokens import ThemeTokens
from overlord.ui.state import AppSessionState
from overlord.ui.strings import (
    format_date_with_year,
    format_month_year,
    format_weekday_name,
    ui_error,
    ui_text,
)


TaskEditorBuilder = Callable[..., ft.Control]


def build_tasks_workspace(
    services: ApplicationServices,
    tokens: ThemeTokens,
    state: AppSessionState,
    refresh,
    report_error,
    page: ft.Page | None,
    editor_builder: TaskEditorBuilder,
) -> ft.Control:
    controller = TaskWorkspaceController(services, state.task_workspace)
    projects = controller.list_projects()
    filter_state = controller.filters
    first_day = controller.first_day_of_week()
    controller.initialize_view()
    today = controller.today

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
        return controller.filtered_items(search.value or "", project_filter.value or "all")

    def open_create(
        _event=None,
        *,
        scheduled_for: date | None = None,
        when_value: str | None = None,
    ) -> None:
        if page is None:
            return

        def created(_task: Task) -> None:
            controller.task_committed(
                close_dialog,
                refresh,
                lambda: show_success(page, tokens, ui_text("tasks.created")),
            )

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
            controller.task_committed(
                close_dialog,
                refresh,
                lambda: show_success(page, tokens, ui_text("tasks.updated")),
            )

        def changed() -> None:
            controller.task_changed(
                close_dialog,
                refresh,
                lambda: open_editor(task_id),
            )

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
        result = controller.complete(task_id)
        if result.succeeded:
            refresh()
        else:
            report_error(ui_error(result.error))

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

    def ordered_items(column: TaskBoardColumn, items: tuple[TaskListItem, ...]) -> tuple[TaskListItem, ...]:
        return controller.ordered_items(column, items)

    def move_card(task_id: int, target: TaskBoardColumn, before_task_id: int | None = None) -> None:
        result = controller.move_card(task_id, target, before_task_id)
        if result.succeeded:
            refresh()
            if page is not None:
                show_success(page, tokens, ui_text("tasks.moved"))
        else:
            report_error(ui_error(result.error))

    def accept_card(event, target: TaskBoardColumn, before_task_id: int | None = None) -> None:
        payload = drag_payload(event)
        if payload and payload.get("kind") == "task":
            move_card(int(payload["task_id"]), target, before_task_id)

    def reorder_column(source: TaskBoardColumn, target: TaskBoardColumn) -> None:
        if controller.reorder_column(source, target):
            refresh()

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
        grouped = group_board_items(items, datetime.now())
        controller.normalize_column_order()
        return ft.Row(
            [
                kanban_column(TaskBoardColumn(value), grouped[TaskBoardColumn(value)])
                for value in controller.state.column_order
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
        scheduled = scheduled_items_for_day(items, selected_day)
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
        assert controller.anchor is not None
        start = week_start(controller.anchor, first_day)
        return ft.Row(
            [day_cell(start + timedelta(days=offset), items, compact=False) for offset in range(7)],
            spacing=tokens.space_2,
            scroll=ft.ScrollMode.AUTO,
            vertical_alignment=ft.CrossAxisAlignment.START,
        )

    def build_month(items: tuple[TaskListItem, ...]) -> ft.Control:
        assert controller.anchor is not None
        weeks = month_weeks(controller.anchor, first_day)
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
                            day_cell(day, items, compact=True, in_current_month=day.month == controller.anchor.month)
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
        controller.switch_mode(mode)
        render(update=True)

    def move_calendar(offset: int) -> None:
        controller.move_calendar(offset)
        render(update=True)

    def go_today(_event=None) -> None:
        controller.go_today()
        render(update=True)

    def render(*, update: bool = False) -> None:
        items = filtered_items()
        mode_row.controls = [
            selection_button(ui_text("tasks.view.kanban"), tokens, selected=controller.state.view_mode == "kanban", on_click=lambda _event: switch_mode("kanban")),
            selection_button(ui_text("tasks.view.week"), tokens, selected=controller.state.view_mode == "week", on_click=lambda _event: switch_mode("week")),
            selection_button(ui_text("tasks.view.month"), tokens, selected=controller.state.view_mode == "month", on_click=lambda _event: switch_mode("month")),
        ]
        calendar_header.visible = controller.state.view_mode in {"week", "month"}
        if calendar_header.visible:
            assert controller.anchor is not None
            start = week_start(controller.anchor, first_day)
            title = (
                ui_text(
                    "tasks.calendar.week_title",
                    start=format_date_with_year(start),
                    end=format_date_with_year(start + timedelta(days=6)),
                )
                if controller.state.view_mode == "week"
                else format_month_year(controller.anchor)
            )
            calendar_header.controls = [
                secondary_button(ui_text("tasks.previous"), tokens, on_click=lambda _event: move_calendar(-1)),
                secondary_button(ui_text("tasks.today"), tokens, on_click=go_today),
                secondary_button(ui_text("tasks.next"), tokens, on_click=lambda _event: move_calendar(1)),
                ft.Text(title, color=tokens.text_primary, weight=ft.FontWeight.W_600),
            ]
        if controller.state.view_mode == "kanban":
            view_host.content = build_kanban(items)
        elif controller.state.view_mode == "week":
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
