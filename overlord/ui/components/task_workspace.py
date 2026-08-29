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
    TaskLifecycle,
    board_column,
)
from overlord.ui.components.complete_task import show_complete_task_dialog
from overlord.ui.components.controls import (
    primary_button,
    search_field,
    select_field,
    tertiary_button,
)
from overlord.ui.components.feedback import show_success
from overlord.ui.components.layout import page_header, workspace_page
from overlord.ui.components.reorder import drag_payload, draggable_task_handle
from overlord.ui.components.tabs import (
    SegmentedDateNavigation,
    SegmentedTab,
    segmented_tabs,
)
from overlord.ui.components.task_card import (
    TaskCardVariant,
    task_card,
    task_meta_chips_for_item,
)
from overlord.ui.components.task_workspace_controller import TaskWorkspaceController
from overlord.ui.components.task_workspace_model import (
    KANBAN_NEEDS_ATTENTION,
    group_board_items,
    group_kanban_items,
    month_weeks,
    normalized_kanban_column_order,
    scheduled_items_for_day,
    week_start,
)
from overlord.ui.components.tasks import build_quick_task_dialog
from overlord.ui.design_system.icons import IconName, lucide_icon
from overlord.ui.design_system.tokens import ThemeTokens
from overlord.ui.state import AppSessionState
from overlord.ui.strings import (
    format_date_with_year,
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

    search = search_field(
        tokens,
        label=ui_text("tasks.search"),
        value=filter_state.search,
        width=600,
        height=48,
        icon=None,
    )
    search_slot = ft.Stack(
        [
            search,
            ft.Container(
                lucide_icon(
                    IconName.SEARCH,
                    color=tokens.text_muted,
                    size=tokens.icon_medium,
                    label=ui_text("tasks.search"),
                    show_tooltip=False,
                ),
                right=tokens.space_3,
                top=14,
                width=tokens.icon_medium,
                height=tokens.icon_medium,
            ),
        ],
        width=600,
        height=48,
        clip_behavior=ft.ClipBehavior.NONE,
        data={"role": "tasks-search"},
    )
    project_filter = select_field(
        tokens,
        searchable=True,
        label=None,
        hint_text=ui_text("tasks.project_filter"),
        value=filter_state.project,
        width=140,
        height=48,
        options=[
            ft.DropdownOption("all", ui_text("tasks.project_all")),
            ft.DropdownOption("none", ui_text("tasks.no_project")),
            *[ft.DropdownOption(str(project.id), project.title) for project in projects],
        ],
    )
    mode_host = ft.Container(width=241, height=48, data={"role": "task-view-mode-host"})
    view_host = ft.Container(
        expand=True,
        clip_behavior=ft.ClipBehavior.HARD_EDGE,
        data={"role": "task-view-host", "size_source": "parent"},
    )

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
            editor_builder(
                services,
                projects,
                task_id,
                tokens,
                saved,
                changed,
                close_dialog,
                report_error,
                page=page,
            )
        )

    def complete(task_id: int) -> None:
        if page is None:
            return
        show_complete_task_dialog(
            page,
            services,
            task_id,
            tokens,
            lambda _task: (
                refresh(),
                show_success(page, tokens, ui_text("tasks.complete_success")),
            ),
            report_error,
        )

    def item_card(
        item: TaskListItem,
        *,
        compact: bool = False,
        drag_handle: ft.Control | None = None,
    ) -> ft.Control:
        return task_card(
            item,
            tokens,
            variant=TaskCardVariant.COMPACT if compact else TaskCardVariant.FULL,
            project_colors=item.project_colors,
            meta_chips=task_meta_chips_for_item(item),
            trailing=drag_handle,
            on_open=lambda _event, task_id=item.task.id: open_editor(task_id),
            on_complete=lambda _event, task_id=item.task.id: complete(task_id),
        )

    def move_card(task_id: int, target: TaskBoardColumn, before_task_id: int | None = None) -> None:
        task = services.tasks.get_editor.execute(task_id).task
        if target is TaskBoardColumn.COMPLETED and task.lifecycle_status is not TaskLifecycle.COMPLETED:
            if page is not None:
                show_complete_task_dialog(
                    page,
                    services,
                    task_id,
                    tokens,
                    lambda _task: (
                        refresh(),
                        show_success(page, tokens, ui_text("tasks.complete_success")),
                    ),
                    report_error,
                )
            return
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

    def reorder_column(source: str, target: str) -> None:
        if controller.reorder_kanban_column(source, target):
            refresh()

    def accept_column(event, target: str) -> None:
        payload = drag_payload(event)
        if payload and payload.get("kind") == "column":
            reorder_column(str(payload["column"]), target)

    def draggable_card(item: TaskListItem, visual_column: str) -> ft.Control:
        source_column = board_column(item.task)
        drop_column = (
            None
            if visual_column == KANBAN_NEEDS_ATTENTION
            else TaskBoardColumn(visual_column)
        )
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
            data={"kind": "task", "task_id": item.task.id, "column": source_column.value},
            feedback=feedback,
        )
        handle.opacity = 0.0
        handle.content.opacity = 0.0
        card = item_card(item)
        card_with_handle = ft.Stack(
            [
                card,
                ft.Container(
                    handle,
                    right=tokens.space_2,
                    top=tokens.space_2,
                    width=tokens.icon_large,
                    height=tokens.space_8,
                ),
            ],
            clip_behavior=ft.ClipBehavior.NONE,
        )

        def reveal_handle(event: object) -> None:
            handle.opacity = (
                1.0
                if str(getattr(event, "data", "")).lower() == "true"
                else 0.0
            )
            handle.content.opacity = handle.opacity

        card_frame = ft.Container(
            card_with_handle,
            on_hover=reveal_handle,
            data={"role": "kanban-card-frame", "task_id": item.task.id},
        )
        return ft.DragTarget(
            card_frame,
            group="task-card" if drop_column is not None else "task-card-derived",
            data={"column": visual_column, "before_task_id": item.task.id},
            on_accept=(
                None
                if drop_column is None
                else lambda event, selected=drop_column, before=item.task.id: accept_card(
                    event, selected, before
                )
            ),
        )

    def column_add_control(column: str) -> ft.Control:
        if column == TaskBoardColumn.PLANNED.value:
            label = ui_text("tasks.add_planned")
            on_click = lambda event: open_create(event, when_value="no_date")
        elif column == TaskBoardColumn.IN_PROGRESS.value:
            label = ui_text("tasks.add_today")
            on_click = lambda event: open_create(event, scheduled_for=today)
        else:
            label = ui_text("tasks.column_add_unavailable")
            on_click = None
        return ft.Container(
            lucide_icon(
                IconName.PLUS,
                color=tokens.text_muted,
                size=tokens.icon_medium,
                label=label,
            ),
            width=28,
            height=28,
            on_click=on_click,
            disabled=on_click is None,
            tooltip=label,
            alignment=ft.Alignment.CENTER,
            border_radius=tokens.radius_small,
            data={"role": "kanban-column-add", "column": column, "enabled": on_click is not None},
        )

    def column_title(column: str) -> str:
        if column == KANBAN_NEEDS_ATTENTION:
            return ui_text("task_board.needs_attention")
        return ui_text(f"task_board.{column}")

    def column_drag_handle(column: str, title: str) -> ft.Control:
        label = ui_text("tasks.drag_column")
        return ft.Draggable(
            ft.Container(
                lucide_icon(
                    IconName.GRIP_VERTICAL,
                    color=tokens.text_muted,
                    size=tokens.icon_small,
                    label=label,
                    show_tooltip=False,
                ),
                width=tokens.space_6,
                height=28,
                alignment=ft.Alignment.CENTER,
                border_radius=tokens.radius_small,
            ),
            group="kanban-column",
            data={"kind": "column", "column": column, "role": "kanban-column-drag-handle"},
            content_feedback=ft.Container(
                ft.Text(title, color=tokens.text_primary, weight=ft.FontWeight.W_600),
                width=280,
                bgcolor=tokens.surface_inner,
                border=ft.Border.all(tokens.focus_width, tokens.accent_primary),
                border_radius=tokens.radius_medium,
                padding=tokens.space_3,
            ),
            tooltip=ui_text("tasks.drag_column"),
        )

    def kanban_column(column: str, items: tuple[TaskListItem, ...]) -> ft.Control:
        title = column_title(column)
        column_width = 322.0
        header = ft.Row(
            [
                ft.Text(
                    title,
                    color=tokens.text_primary,
                    size=tokens.text_emphasis,
                    weight=ft.FontWeight.W_400,
                ),
                ft.Container(
                    ft.Text(str(len(items)), color=tokens.text_primary, size=tokens.text_small),
                    width=tokens.space_6,
                    height=tokens.space_6,
                    bgcolor=tokens.surface_card,
                    border_radius=tokens.space_1,
                    alignment=ft.Alignment.CENTER,
                    data={"role": "kanban-column-count", "column": column, "count": len(items)},
                ),
                ft.Container(expand=True),
                column_add_control(column),
                column_drag_handle(column, title),
            ],
            spacing=tokens.space_2,
            height=28,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            data={"role": "kanban-column-header", "column": column},
        )
        visible_items = controller.projected_items(items)
        cards: list[ft.Control] = [
            draggable_card(item, column) for item in visible_items
        ]
        if not cards:
            cards.append(
                ft.Text(
                    ui_text("tasks.column_empty"),
                    color=tokens.text_muted,
                    size=tokens.text_small,
                )
            )
        task_list = ft.ListView(
            cards,
            spacing=tokens.space_2,
            padding=tokens.space_0,
            scroll=ft.ScrollMode.AUTO,
            expand=True,
            data={
                "role": "kanban-column-task-list",
                "column": column,
                "internal_scroll": True,
                "visible_count": len(items),
            },
        )
        drop_column = (
            None if column == KANBAN_NEEDS_ATTENTION else TaskBoardColumn(column)
        )
        card_target = ft.DragTarget(
            task_list,
            group="task-card" if drop_column is not None else "task-card-derived",
            data={
                "role": "kanban-column-card-target",
                "column": column,
                "accepts_tasks": drop_column is not None,
            },
            on_accept=(
                None
                if drop_column is None
                else lambda event, selected=drop_column: accept_card(event, selected)
            ),
        )
        card_target.expand = True
        surface = ft.Container(
            ft.Column([header, card_target], spacing=tokens.space_2, expand=True),
            bgcolor=tokens.dashboard_board_background,
            border=ft.Border.all(tokens.border_width, tokens.dashboard_board_border),
            border_radius=tokens.space_2,
            padding=ft.Padding.only(
                left=tokens.space_4,
                top=tokens.space_2,
                right=tokens.space_2,
                bottom=tokens.space_2,
            ),
            width=column_width,
            data={
                "role": "kanban-column",
                "column": column,
                "visible_count": len(items),
                "height_behavior": "available",
            },
        )
        column_target = ft.DragTarget(
            surface,
            group="kanban-column",
            data={"role": "kanban-column-target", "column": column},
            on_accept=lambda event, selected=column: accept_column(event, selected),
        )
        column_target.width = column_width
        return column_target

    def build_kanban(items: tuple[TaskListItem, ...]) -> ft.Control:
        reference = datetime.now()
        controller.initialize_card_orders(
            group_board_items(controller.all_items(), reference)
        )
        controller.normalize_column_order()
        grouped = group_kanban_items(items, reference)
        columns = ft.Row(
            [
                kanban_column(value, grouped[value])
                for value in normalized_kanban_column_order(controller.state.column_order)
            ],
            spacing=tokens.space_4,
            width=322.0 * 4 + tokens.space_4 * 3,
            tight=True,
            vertical_alignment=ft.CrossAxisAlignment.STRETCH,
            data={"role": "kanban-columns", "column_gap": tokens.space_4},
        )
        add_section = ft.Container(
            ft.Row(
                [
                    lucide_icon(
                        IconName.PLUS,
                        color=tokens.text_muted,
                        size=tokens.icon_medium,
                        label=ui_text("tasks.add_section"),
                    ),
                    ft.Text(ui_text("tasks.add_section"), color=tokens.text_muted),
                ],
                spacing=tokens.space_2,
                tight=True,
            ),
            width=288,
            alignment=ft.Alignment.TOP_CENTER,
            padding=ft.Padding.only(top=tokens.space_2),
            data={"role": "kanban-add-section", "placeholder": True},
        )
        return ft.Row(
            [columns, add_section],
            spacing=tokens.space_4,
            scroll=ft.ScrollMode.AUTO,
            expand=True,
            vertical_alignment=ft.CrossAxisAlignment.STRETCH,
            data={
                "role": "kanban-board",
                "column_gap": tokens.space_4,
                "bottom_inset": tokens.space_4,
                "narrow_behavior": "horizontal-scroll",
                "size_source": "view-host",
            },
        )

    def week_day_column(
        selected_day: date,
        items: tuple[TaskListItem, ...],
    ) -> ft.Control:
        scheduled = scheduled_items_for_day(items, selected_day)
        header = ft.Row(
            [
                ft.Text(
                    f"{format_weekday_name(selected_day)} {selected_day.day}",
                    color=tokens.text_primary,
                    size=tokens.text_emphasis,
                    weight=ft.FontWeight.W_400,
                ),
                ft.Container(
                    ft.Text(
                        str(len(scheduled)),
                        color=tokens.text_primary,
                        size=tokens.text_small,
                    ),
                    width=tokens.space_6,
                    height=tokens.space_6,
                    bgcolor=tokens.surface_card,
                    border_radius=tokens.space_1,
                    alignment=ft.Alignment.CENTER,
                    data={
                        "role": "week-day-count",
                        "day": selected_day.isoformat(),
                        "count": len(scheduled),
                    },
                ),
                ft.Container(expand=True),
                ft.Container(
                    lucide_icon(
                        IconName.PLUS,
                        color=tokens.text_muted,
                        size=tokens.icon_medium,
                        label=ui_text(
                            "tasks.add_to_date",
                            date=format_date_with_year(selected_day),
                        ),
                        show_tooltip=False,
                    ),
                    width=28,
                    height=28,
                    on_click=lambda event, day=selected_day: open_create(
                        event, scheduled_for=day
                    ),
                    tooltip=ui_text(
                        "tasks.add_to_date",
                        date=format_date_with_year(selected_day),
                    ),
                    alignment=ft.Alignment.CENTER,
                    border_radius=tokens.radius_small,
                    data={
                        "role": "week-day-add",
                        "day": selected_day.isoformat(),
                    },
                ),
            ],
            spacing=tokens.space_2,
            height=28,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            data={"role": "week-day-header", "day": selected_day.isoformat()},
        )
        task_list = ft.ListView(
            [item_card(item) for item in scheduled],
            spacing=tokens.space_2,
            padding=tokens.space_0,
            scroll=ft.ScrollMode.AUTO,
            expand=True,
            data={
                "role": "week-day-task-list",
                "day": selected_day.isoformat(),
                "internal_scroll": True,
                "visible_count": len(scheduled),
            },
        )
        return ft.Container(
            ft.Column([header, task_list], spacing=tokens.space_2, expand=True),
            width=300,
            bgcolor=tokens.dashboard_board_background,
            border=ft.Border.all(
                tokens.focus_width if selected_day == today else tokens.border_width,
                tokens.accent_primary
                if selected_day == today
                else tokens.dashboard_board_border,
            ),
            border_radius=tokens.space_2,
            padding=ft.Padding.only(
                left=tokens.space_4,
                top=tokens.space_2,
                right=tokens.space_4,
                bottom=tokens.space_2,
            ),
            data={
                "role": "week-day-column",
                "day": selected_day.isoformat(),
                "today": selected_day == today,
                "visible_count": len(scheduled),
                "column_width": 300,
            },
        )

    def month_day_cell(
        selected_day: date,
        items: tuple[TaskListItem, ...],
        *,
        in_current_month: bool = True,
    ) -> ft.Container:
        scheduled = scheduled_items_for_day(items, selected_day)
        add_label = ui_text(
            "tasks.add_to_date",
            date=format_date_with_year(selected_day),
        )
        add_target = ft.GestureDetector(
            ft.Container(
                lucide_icon(
                    IconName.PLUS,
                    color=tokens.text_muted,
                    size=tokens.icon_medium,
                    label=add_label,
                ),
                width=24,
                height=24,
                alignment=ft.Alignment.CENTER,
            ),
            on_tap=lambda event, day=selected_day: open_create(event, scheduled_for=day),
            mouse_cursor=ft.MouseCursor.CLICK,
            data={"role": "month-day-add", "day": selected_day.isoformat()},
        )
        header = ft.Row(
            [
                ft.Text(
                    selected_day.strftime("%d.%m"),
                    color=tokens.text_primary if in_current_month else tokens.text_muted,
                    size=tokens.text_small,
                    expand=True,
                ),
                ft.Semantics(
                    content=add_target,
                    label=add_label,
                    button=True,
                ),
            ],
            spacing=tokens.space_1,
            height=24,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            data={"role": "month-day-header", "day": selected_day.isoformat()},
        )
        cards = [item_card(item, compact=True) for item in scheduled]
        task_list = ft.ListView(
            cards
            or [
                ft.Text(
                    ui_text("tasks.day_empty"),
                    color=tokens.text_muted,
                    size=tokens.text_small,
                )
            ],
            spacing=tokens.space_1,
            padding=tokens.space_0,
            scroll=ft.ScrollMode.AUTO,
            expand=True,
            data={
                "role": "month-day-task-list",
                "day": selected_day.isoformat(),
                "internal_scroll": True,
                "visible_count": len(scheduled),
            },
        )
        return ft.Container(
            ft.Column([header, task_list], spacing=tokens.space_1, expand=True),
            expand=True,
            height=164,
            bgcolor=tokens.surface_card if in_current_month else tokens.surface_inner,
            border=ft.Border.all(
                tokens.border_width,
                tokens.accent_primary if selected_day == today else tokens.border_default,
            ),
            border_radius=tokens.radius_medium,
            padding=tokens.space_2,
            data={
                "role": "month-day-cell",
                "day": selected_day.isoformat(),
                "in_current_month": in_current_month,
                "today": selected_day == today,
                "visible_count": len(scheduled),
                "cell_height": 164,
            },
        )

    def build_week(items: tuple[TaskListItem, ...]) -> ft.Control:
        assert controller.anchor is not None
        start = week_start(controller.anchor, first_day)
        return ft.Row(
            [week_day_column(start + timedelta(days=offset), items) for offset in range(7)],
            spacing=tokens.space_4,
            scroll=ft.ScrollMode.ALWAYS,
            expand=True,
            vertical_alignment=ft.CrossAxisAlignment.STRETCH,
            data={
                "role": "week-board",
                "start": start.isoformat(),
                "end": (start + timedelta(days=6)).isoformat(),
                "day_count": 7,
                "column_width": 300,
                "column_gap": tokens.space_4,
                "horizontal_scroll": True,
                "scrollbar": "always",
                "size_source": "view-host",
            },
        )

    def build_month(items: tuple[TaskListItem, ...]) -> ft.Control:
        assert controller.anchor is not None
        month_first_day = 0
        weeks = month_weeks(controller.anchor, month_first_day)
        weekday_start = weeks[0][0]
        weekday_header = ft.Row(
            [
                ft.Container(
                    ft.Text(format_weekday_name(weekday_start + timedelta(days=offset)), color=tokens.text_muted, size=tokens.text_small),
                    expand=True,
                    padding=ft.Padding.only(left=tokens.space_2),
                    data={
                        "role": "month-weekday-label",
                        "weekday": offset,
                    },
                )
                for offset in range(7)
            ],
            spacing=tokens.space_2,
            height=15,
            data={
                "role": "month-weekday-header",
                "weekday_order": tuple(range(7)),
            },
        )
        rows = [
            ft.Row(
                [
                    month_day_cell(
                        day,
                        items,
                        in_current_month=(day.year, day.month)
                        == (controller.anchor.year, controller.anchor.month),
                    )
                    for day in week
                ],
                spacing=tokens.space_2,
                height=164,
                vertical_alignment=ft.CrossAxisAlignment.START,
                data={
                    "role": "month-week-row",
                    "start": week[0].isoformat(),
                    "end": week[-1].isoformat(),
                },
            )
            for week in weeks
        ]
        return ft.Column(
            [
                weekday_header,
                *rows,
            ],
            spacing=tokens.space_2,
            scroll=ft.ScrollMode.AUTO,
            expand=True,
            data={
                "role": "month-board",
                "anchor_month": controller.anchor.replace(day=1).isoformat(),
                "start": weeks[0][0].isoformat(),
                "end": weeks[-1][-1].isoformat(),
                "week_count": len(weeks),
                "day_count": len(weeks) * 7,
                "weekday_order": tuple(range(7)),
                "cell_height": 164,
                "column_gap": tokens.space_2,
                "row_gap": tokens.space_2,
                "vertical_scroll": True,
                "size_source": "view-host",
            },
        )

    def switch_mode(mode: str) -> None:
        controller.switch_mode(mode)
        render(update=True)

    def toggle_date_navigation(mode: str) -> None:
        controller.toggle_date_navigation(mode)
        render(update=True)

    def move_calendar(offset: int) -> None:
        controller.move_calendar(offset)
        render(update=True)

    def go_today(_event=None) -> None:
        controller.go_today()
        render(update=True)

    def render(*, update: bool = False) -> None:
        items = filtered_items()
        expanded_navigation = controller.state.expanded_date_navigation
        mode_width = (
            241
            if controller.state.view_mode == "kanban"
            else 517 if expanded_navigation is not None else 273
        )
        mode_host.width = mode_width
        mode_host.content = segmented_tabs(
            (
                SegmentedTab("kanban", ui_text("tasks.view.kanban"), 87),
                SegmentedTab("week", ui_text("tasks.view.week"), 72),
                SegmentedTab("month", ui_text("tasks.view.month"), 80),
            ),
            controller.state.view_mode,
            tokens,
            switch_mode,
            width=mode_width,
            role="task-view-modes",
            date_navigation=SegmentedDateNavigation(
                expanded=expanded_navigation,
                on_toggle=toggle_date_navigation,
                previous_label=ui_text("tasks.previous"),
                today_label=ui_text("tasks.today"),
                next_label=ui_text("tasks.next"),
                expand_label=lambda view: ui_text(
                    "tasks.expand_date_navigation", view=view
                ),
                collapse_label=lambda view: ui_text(
                    "tasks.collapse_date_navigation", view=view
                ),
                on_previous=lambda: move_calendar(-1),
                on_today=go_today,
                on_next=lambda: move_calendar(1),
            ),
        )
        if controller.state.view_mode == "kanban":
            view_host.content = ft.Column(
                [build_kanban(items)],
                spacing=tokens.space_0,
                expand=True,
            )
        elif controller.state.view_mode == "week":
            view_host.content = build_week(items)
        else:
            view_host.content = build_month(items)
        if update:
            mode_host.update()
            view_host.update()

    def apply_filters(_event=None) -> None:
        try:
            render(update=True)
        except Exception as error:
            report_error(ui_error(error))

    search.on_change = apply_filters
    search.on_submit = apply_filters
    project_filter.on_select = apply_filters
    render()
    new_task = primary_button(
        ft.Row(
            [
                lucide_icon(
                    IconName.PLUS,
                    color=tokens.on_accent,
                    size=tokens.icon_medium,
                    label=ui_text("tasks.new"),
                ),
                ft.Text(ui_text("tasks.new"), color=tokens.on_accent),
            ],
            spacing=tokens.space_2,
            tight=True,
        ),
        tokens,
        width=130,
        height=48,
        on_click=open_create,
        data={"role": "tasks-new-task"},
    )
    toolbar = ft.Row(
        [
            ft.Row(
                [mode_host, search_slot, project_filter],
                spacing=tokens.space_2,
                wrap=True,
                run_spacing=tokens.space_2,
                data={"role": "tasks-toolbar-filters"},
            ),
            new_task,
        ],
        spacing=tokens.space_4,
        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
        wrap=True,
        run_spacing=tokens.space_2,
        data={"role": "tasks-toolbar", "reference_height": 48},
    )
    header = page_header(ui_text("tasks.title"), tokens)
    header.height = 40
    content = workspace_page(
        header,
        toolbar,
        view_host,
        tokens,
        page_id="tasks",
    )
    content.data["role"] = "tasks-page-container"
    content.data["bottom_inset"] = tokens.space_4
    if state.selected_task_id is not None and page is not None and hasattr(page, "run_task"):
        selected_task_id = state.selected_task_id
        state.selected_task_id = None

        async def open_selected_editor() -> None:
            await asyncio.sleep(0)
            open_editor(selected_task_id)

        page.run_task(open_selected_editor)
    return content
