from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Callable
from urllib.parse import parse_qs, urlparse

import flet as ft

from overlord.app.read_models import TaskListItem
from overlord.app.services import ApplicationServices
from overlord.modules.dashboard.read_models import DashboardReadModel
from overlord.modules.tasks.domain import TaskLifecycle
from overlord.ui.components.complete_task import show_complete_task_dialog
from overlord.ui.components.controls import primary_button
from overlord.ui.components.feedback import empty_state
from overlord.ui.components.layout import card, page_container
from overlord.ui.components.reorder import drag_payload
from overlord.ui.components.task_card import (
    TaskCardVariant,
    task_card,
    task_meta_chips_for_item,
)
from overlord.ui.components.task_ordering import TaskOrderController
from overlord.ui.components.task_details import build_task_details_dialog
from overlord.ui.components.tasks import build_quick_task_dialog
from overlord.ui.components.weather import build_weather_widget
from overlord.ui.design_system.icons import IconName, lucide_icon
from overlord.ui.design_system.tokens import ThemeTokens
from overlord.ui.strings import (
    format_dashboard_date,
    format_dashboard_week_range,
    format_weekday_name,
    ui_error,
    ui_text,
)


def _outcome_label(value: str) -> str:
    if value == "Not set":
        return ui_text("common.not_set")
    normalized = value.lower().replace(" ", "_")
    key = f"cycles.outcome_status.{normalized}"
    return ui_text(key)


def _attention_reason(value: str) -> str:
    if value == "Open blocker":
        return ui_text("dashboard.reason.open_blocker")
    mapping = {
        "No update for seven days": "dashboard.reason.no_update",
        "Legacy status requires review": "dashboard.reason.legacy_status",
    }
    return ui_text(mapping[value]) if value in mapping else value


def _selected_date(route: str) -> date:
    raw = parse_qs(urlparse(route).query).get("date", [date.today().isoformat()])[0]
    try:
        return date.fromisoformat(raw)
    except ValueError:
        return date.today()


def _format_weekly_duration(minutes: int | None) -> str:
    if minutes is None:
        return ui_text("common.not_tracked_yet")
    hours, remainder = divmod(minutes, 60)
    if hours and remainder:
        return ui_text("dashboard.duration.hours_minutes", hours=hours, minutes=remainder)
    if hours:
        return ui_text("dashboard.duration.hours", hours=hours)
    return ui_text("dashboard.duration.minutes", minutes=remainder)


def _weekly_metric(
    label: str,
    value: str,
    tokens: ThemeTokens,
    *,
    align_end: bool = False,
    role: str,
) -> ft.Control:
    return ft.Column(
        [
            ft.Text(label, color=tokens.text_muted, size=tokens.text_body),
            ft.Text(value, color=tokens.text_primary, size=tokens.text_emphasis, weight=ft.FontWeight.W_700),
        ],
        spacing=tokens.space_1,
        expand=True,
        horizontal_alignment=ft.CrossAxisAlignment.END if align_end else ft.CrossAxisAlignment.START,
        data={"role": role},
    )


def _weekly_progress(data: DashboardReadModel, tokens: ThemeTokens) -> ft.Control:
    chart_height = 160
    columns: list[ft.Control] = []
    for bar in data.weekly_bars:
        ratio = min(1.0, bar.completed / bar.planned) if bar.planned else 0.0
        completed_height = max(1, round(chart_height * ratio)) if bar.completed else 0
        is_today = bar.day == data.day
        columns.append(
            ft.Column(
                [
                    ft.Stack(
                        [
                            ft.Container(
                                left=0,
                                right=0,
                                top=0,
                                bottom=0,
                                bgcolor=tokens.dashboard_weekly_bar_track,
                                border_radius=tokens.space_2,
                            ),
                            ft.Container(
                                left=0,
                                right=0,
                                bottom=0,
                                height=completed_height,
                                visible=completed_height > 0,
                                gradient=ft.LinearGradient(
                                    begin=ft.Alignment.TOP_CENTER,
                                    end=ft.Alignment.BOTTOM_CENTER,
                                    colors=[
                                        tokens.dashboard_weekly_bar_fill,
                                        tokens.dashboard_board_background,
                                    ],
                                ),
                                border_radius=tokens.space_2,
                            ),
                        ],
                        height=chart_height,
                        data={
                            "role": "weekly-bar",
                            "day": bar.day.isoformat(),
                            "planned": bar.planned,
                            "completed": bar.completed,
                        },
                        tooltip=ui_text(
                            "dashboard.weekly_tooltip",
                            day=format_weekday_name(bar.day),
                            completed=bar.completed,
                            planned=bar.planned,
                        ),
                    ),
                    ft.Text(
                        format_weekday_name(bar.day)[:3],
                        size=tokens.text_body,
                        color=tokens.dashboard_weekly_today if is_today else tokens.text_muted,
                        text_align=ft.TextAlign.CENTER,
                    ),
                ],
                spacing=tokens.space_2,
                expand=True,
                horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
            )
        )

    score = "—" if data.execution_score is None else f"{data.execution_score:.0%}"
    completed_total = sum(bar.completed for bar in data.weekly_bars)
    planned_total = sum(bar.planned for bar in data.weekly_bars)
    week_start = data.weekly_bars[0].day if data.weekly_bars else data.day
    week_end = data.weekly_bars[-1].day if data.weekly_bars else data.day
    divider = lambda: ft.Divider(color=tokens.dashboard_board_divider, height=1, thickness=1)
    return ft.Container(
        ft.Column(
            [
                ft.Row(
                    [
                        ft.Text(
                            ui_text("dashboard.weekly.title"),
                            color=tokens.text_primary,
                            size=tokens.text_title,
                            weight=ft.FontWeight.W_600,
                            expand=True,
                        ),
                        ft.Container(
                            ft.Text(
                                format_dashboard_week_range(week_start, week_end),
                                color=tokens.text_secondary,
                                size=tokens.text_small,
                            ),
                            height=26,
                            bgcolor=tokens.dashboard_date_chip_background,
                            border=ft.Border.all(tokens.border_width, tokens.dashboard_date_chip_border),
                            border_radius=tokens.radius_pill,
                            padding=ft.Padding.symmetric(horizontal=tokens.space_2, vertical=tokens.space_1),
                            alignment=ft.Alignment.CENTER,
                        ),
                    ],
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                ft.Container(height=18),
                ft.Row(columns, spacing=tokens.space_3, height=181),
                ft.Container(height=17),
                divider(),
                ft.Container(height=18),
                ft.Row(
                    [
                        _weekly_metric(
                            ui_text("dashboard.execution_score"),
                            score,
                            tokens,
                            role="weekly-execution-score",
                        ),
                        _weekly_metric(
                            ui_text("dashboard.completed_planned"),
                            f"{completed_total}/{planned_total}",
                            tokens,
                            align_end=True,
                            role="weekly-completed-planned",
                        ),
                    ]
                ),
                ft.Container(height=14),
                divider(),
                ft.Container(height=18),
                ft.Row(
                    [
                        _weekly_metric(
                            ui_text("dashboard.active_time"),
                            _format_weekly_duration(data.active_time_minutes),
                            tokens,
                            role="weekly-active-time",
                        ),
                        _weekly_metric(
                            ui_text("dashboard.total_time"),
                            _format_weekly_duration(data.total_time_minutes),
                            tokens,
                            align_end=True,
                            role="weekly-total-time",
                        ),
                    ]
                ),
            ],
            spacing=tokens.space_0,
        ),
        height=433,
        expand=True,
        bgcolor=tokens.dashboard_board_background,
        border=ft.Border.all(tokens.border_width, tokens.dashboard_board_border),
        border_radius=tokens.space_4,
        padding=ft.Padding.only(
            left=tokens.space_5,
            top=tokens.space_5,
            right=tokens.space_5,
            bottom=tokens.space_4,
        ),
        clip_behavior=ft.ClipBehavior.HARD_EDGE,
        data={"role": "weekly-progress-widget"},
    )


def build_dashboard(
    services: ApplicationServices,
    tokens: ThemeTokens,
    route: str,
    navigate,
    refresh,
    report_error,
    page: ft.Page | None = None,
    *,
    sidebar_collapsed: bool | Callable[[], bool] = False,
) -> ft.Control:
    selected_day = _selected_date(route)
    data = services.dashboard.execute(selected_day)
    weather_data = services.weather.snapshot()
    projects = services.projects.list_projects.execute()
    dashboard_root: ft.ListView | None = None
    ordering = TaskOrderController(services)

    def items_for(model: DashboardReadModel, day: date) -> tuple[TaskListItem, ...]:
        if day == selected_day - timedelta(days=1):
            return model.yesterday_tasks
        if day == selected_day + timedelta(days=1):
            return model.tomorrow_tasks
        return model.today_tasks

    def close_dialog() -> None:
        if page is not None:
            page.pop_dialog()

    def open_create(day: date) -> None:
        if page is None:
            return

        def created(_task) -> None:
            close_dialog()
            refresh()

        page.show_dialog(
            build_quick_task_dialog(
                services,
                projects,
                tokens,
                created,
                close_dialog,
                preset_start_date=day,
                page=page,
            )
        )

    def open_details(task_id: int, day: date) -> None:
        if page is None:
            return

        def saved() -> None:
            close_dialog()
            refresh()

        page.show_dialog(
            build_task_details_dialog(
                services,
                projects,
                task_id,
                day,
                tokens,
                saved,
                close_dialog,
                report_error,
                page=page,
                on_deleted=saved,
            )
        )

    def toggle_complete(task_id: int, day: date) -> None:
        try:
            task = services.tasks.get_editor.execute(task_id).task
            if task.lifecycle_status is TaskLifecycle.COMPLETED:
                services.tasks.toggle_completion_for_day.execute(task_id, day)
                refresh()
            elif page is not None:
                show_complete_task_dialog(
                    page,
                    services,
                    task_id,
                    tokens,
                    lambda _task: refresh(),
                    report_error,
                    selected_day=day,
                )
        except Exception as error:
            report_error(ui_error(error))

    def reorder(event, day: date, before_task_id: int | None = None) -> None:
        payload = drag_payload(event)
        if not payload or payload.get("kind") != "task":
            return
        if payload.get("day") != day.isoformat():
            return
        task_id = int(payload["task_id"])
        order = tuple(item.task.id for item in items_for(data, day))
        if task_id not in order:
            return
        try:
            ordering.move_before_for_day(day, order, task_id, before_task_id)
            refresh()
        except Exception as error:
            report_error(ui_error(error))

    def task_controls(day: date, items: tuple[TaskListItem, ...]) -> list[ft.Control]:
        controls = []
        for item in items:
            card_control = task_card(
                item,
                tokens,
                variant=TaskCardVariant.FULL,
                project_colors=item.project_colors,
                meta_chips=task_meta_chips_for_item(item, displayed_day=day),
                muted=day < selected_day,
                on_complete=lambda _event, task_id=item.task.id, selected=day: toggle_complete(task_id, selected),
                on_open=lambda _event, task_id=item.task.id, selected=day: open_details(task_id, selected),
                allow_reopen=True,
                role="task-card",
            )
            draggable_card = ft.Draggable(
                card_control,
                group="task-card",
                data={
                    "role": "task-drag-handle",
                    "kind": "task",
                    "task_id": item.task.id,
                    "day": day.isoformat(),
                },
                content_when_dragging=ft.Container(
                    height=card_control.height,
                    bgcolor=tokens.interactive_hover,
                    border_radius=tokens.task_card_radius,
                ),
                content_feedback=ft.Container(
                    ft.Text(
                        item.task.title,
                        color=tokens.text_primary,
                        size=tokens.text_emphasis,
                        max_lines=2,
                        overflow=ft.TextOverflow.ELLIPSIS,
                    ),
                    width=300,
                    bgcolor=tokens.task_card_background,
                    border=ft.Border.all(tokens.border_width, tokens.task_card_hover_border),
                    border_radius=tokens.task_card_radius,
                    padding=tokens.space_4,
                ),
            )
            list_item = ft.Container(
                ft.DragTarget(
                    draggable_card,
                    group="task-card",
                    data={"day": day.isoformat(), "before_task_id": item.task.id},
                    on_accept=lambda event, selected=day, before=item.task.id: reorder(event, selected, before),
                ),
                padding=ft.Padding.only(bottom=tokens.space_2),
                key=f"dashboard-task-{day.isoformat()}-{item.task.id}",
                data={"role": "task-list-item", "task_id": item.task.id, "gap_after": tokens.space_2},
            )
            controls.append(list_item)
        return controls

    def empty_day_control() -> ft.Control:
        return ft.Container(
            ft.Text(ui_text("dashboard.empty_day"), color=tokens.text_muted, size=tokens.text_small),
            alignment=ft.Alignment.CENTER,
            padding=tokens.space_4,
        )

    def contain_dashboard_scroll(_event) -> None:
        if dashboard_root is not None and dashboard_root.scroll is not None:
            dashboard_root.scroll = None
            if page is not None and hasattr(page, "update"):
                page.update()

    def release_dashboard_scroll(_event) -> None:
        if dashboard_root is not None and dashboard_root.scroll is None:
            dashboard_root.scroll = ft.ScrollMode.AUTO
            if page is not None and hasattr(page, "update"):
                page.update()

    def add_task_control(day: date, disabled: bool) -> ft.Control:
        label = ui_text("dashboard.add_task")
        surface = ft.Container(
            ft.Row(
                [
                    ft.Text(
                        label,
                        color=tokens.dashboard_add_disabled_text if disabled else tokens.dashboard_add_text,
                        size=tokens.text_emphasis,
                        expand=True,
                    ),
                    lucide_icon(
                        IconName.PLUS,
                        color=tokens.dashboard_add_disabled_text if disabled else tokens.dashboard_add_icon,
                        size=tokens.icon_small,
                        label=label,
                        disabled=disabled,
                        show_tooltip=False,
                    ),
                ],
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            height=tokens.control_height,
            bgcolor=tokens.dashboard_add_disabled_background if disabled else tokens.dashboard_add_background,
            border=ft.Border.all(
                tokens.border_width,
                tokens.dashboard_add_disabled_border if disabled else tokens.dashboard_add_border,
            ),
            border_radius=tokens.space_2,
            padding=ft.Padding.symmetric(horizontal=tokens.space_3),
        )
        control = ft.GestureDetector(
            surface,
            mouse_cursor=ft.MouseCursor.FORBIDDEN if disabled else ft.MouseCursor.CLICK,
            on_tap=None if disabled else lambda _event: open_create(day),
            data={"role": "add-task", "day": day.isoformat(), "disabled": disabled},
        )

        if not disabled:
            def hover(event) -> None:
                hovering = str(getattr(event, "data", "")).lower() == "true"
                surface.border = ft.Border.all(
                    tokens.border_width,
                    tokens.accent_primary if hovering else tokens.dashboard_add_border,
                )

            surface.on_hover = hover
        return control

    def day_column(day: date, title_key: str, *, disabled_add: bool, last: bool = False) -> ft.Control:
        historical = day < selected_day
        date_chip = ft.Container(
            ft.Text(
                format_dashboard_date(day),
                color=tokens.text_muted if historical else tokens.text_secondary,
                size=tokens.text_small,
                style=ft.TextStyle(decoration=ft.TextDecoration.LINE_THROUGH if historical else ft.TextDecoration.NONE),
            ),
            bgcolor=tokens.dashboard_date_chip_background,
            border=ft.Border.all(tokens.border_width, tokens.dashboard_date_chip_border),
            border_radius=tokens.radius_pill,
            padding=ft.Padding.symmetric(horizontal=tokens.space_2, vertical=tokens.space_1),
            data={"role": "date-chip", "day": day.isoformat()},
        )
        items = items_for(data, day)
        task_list = ft.ListView(
            controls=task_controls(day, items) or [empty_day_control()],
            spacing=tokens.space_0,
            scroll=ft.ScrollMode.HIDDEN,
            clip_behavior=ft.ClipBehavior.HARD_EDGE,
            expand=True,
            build_controls_on_demand=False,
            data={"role": "day-task-list", "day": day.isoformat()},
        )
        scroll_region = ft.GestureDetector(
            ft.DragTarget(
                task_list,
                group="task-card",
                data={"role": "day-task-drop-target", "day": day.isoformat()},
                on_accept=lambda event, selected=day: reorder(event, selected),
            ),
            on_enter=contain_dashboard_scroll,
            on_exit=release_dashboard_scroll,
            expand=True,
            data={"role": "day-scroll-containment", "day": day.isoformat()},
        )
        return ft.Container(
            ft.Column(
                [
                    ft.Row(
                        [
                            ft.Text(
                                ui_text(title_key),
                                color=tokens.text_muted if historical else tokens.text_primary,
                                size=tokens.text_title,
                                weight=ft.FontWeight.W_600,
                                expand=True,
                            ),
                            date_chip,
                        ],
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    add_task_control(day, disabled_add),
                    scroll_region,
                ],
                spacing=tokens.space_3,
                expand=True,
            ),
            expand=True,
            border=(
                None
                if last
                else ft.Border.only(
                    right=ft.BorderSide(tokens.border_width, tokens.dashboard_board_divider)
                )
            ),
            data={"role": "day-column", "day": day.isoformat()},
        )

    yesterday = selected_day - timedelta(days=1)
    tomorrow = selected_day + timedelta(days=1)
    yesterday_column = day_column(yesterday, "dashboard.yesterday.title", disabled_add=True)
    today_column = day_column(selected_day, "dashboard.today.title", disabled_add=False)
    tomorrow_column = day_column(
        tomorrow,
        "dashboard.tomorrow.title",
        disabled_add=False,
        last=True,
    )
    three_day_task_board = ft.Container(
        ft.Row(
            [
                yesterday_column,
                today_column,
                tomorrow_column,
            ],
            spacing=tokens.space_6,
            expand=True,
            vertical_alignment=ft.CrossAxisAlignment.STRETCH,
        ),
        height=433,
        bgcolor=tokens.dashboard_board_background,
        border=ft.Border.all(tokens.border_width, tokens.dashboard_board_border),
        border_radius=tokens.space_4,
        padding=ft.Padding.only(
            left=tokens.space_5,
            top=tokens.space_5,
            right=tokens.space_5,
            bottom=tokens.space_4,
        ),
        clip_behavior=ft.ClipBehavior.HARD_EDGE,
        expand=True,
        data={
            "role": "three-day-task-board",
            "max_width_expanded": 1176,
            "max_width_collapsed": 1300,
            "horizontal_padding": tokens.space_5,
            "column_gap": tokens.space_6,
            "visible_days": ("yesterday", "today", "tomorrow"),
        },
    )

    if data.current_cycle:
        cycle = data.current_cycle
        cycle_controls = [
            ft.Row(
                [
                    ft.Text(ui_text("dashboard.week_of", week=cycle.week_number, length=cycle.length_weeks), color=tokens.accent_primary, weight=ft.FontWeight.W_600),
                    ft.Text(ui_text("dashboard.days_remaining", count=cycle.days_remaining), color=tokens.text_muted, size=tokens.text_small),
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            ),
            ft.Text(cycle.title, color=tokens.text_primary, weight=ft.FontWeight.W_700),
            ft.Text(cycle.main_outcome, color=tokens.text_secondary, size=tokens.text_small),
            ft.ProgressBar(value=cycle.progress, color=tokens.accent_primary, bgcolor=tokens.border_default, border_radius=tokens.radius_pill),
            ft.Text(ui_text("dashboard.current_outcome", value=_outcome_label(cycle.weekly_outcome)), color=tokens.text_secondary, size=tokens.text_small),
            ft.Text(ui_text("dashboard.next_milestone", value=cycle.next_milestone or ui_text("common.not_set")), color=tokens.text_muted, size=tokens.text_small),
            ft.TextButton(ui_text("dashboard.open_cycle"), on_click=lambda _e: navigate(f"/cycles/{cycle.cycle_id}")),
        ]
    else:
        cycle_controls = [
            empty_state(ui_text("dashboard.no_active_cycle"), tokens, primary_button(ui_text("dashboard.create_plan"), tokens, on_click=lambda _e: navigate("/cycles")))
        ]

    attention_controls = [
        ft.Container(
            ft.Row(
                [
                    lucide_icon(IconName.ALERT, color=tokens.warning.main, size=tokens.icon_medium, label=ui_text("dashboard.attention.title")),
                    ft.Column(
                        [
                            ft.Text(item.title, color=tokens.text_primary, weight=ft.FontWeight.W_600),
                            ft.Text(item.project_title or ui_text("tasks.no_project"), color=tokens.text_muted, size=tokens.text_small),
                            ft.Text(ui_text("common.metadata_separator").join(_attention_reason(reason) for reason in item.reasons), color=tokens.text_secondary, size=tokens.text_small),
                        ],
                        spacing=tokens.space_1,
                        expand=True,
                    ),
                    ft.TextButton(ui_text("dashboard.review"), on_click=lambda _e, task_id=item.task_id: navigate(f"/tasks?task={task_id}")),
                ],
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=tokens.space_2,
            ),
            bgcolor=tokens.surface_inner,
            border=ft.Border.only(left=ft.BorderSide(tokens.focus_width, tokens.warning.main)),
            border_radius=tokens.radius_medium,
            padding=tokens.space_3,
        )
        for item in data.attention
    ]

    lower_left: list[ft.Control] = []
    if attention_controls:
        lower_left.append(card(ui_text("dashboard.attention.title"), attention_controls, tokens))

    weekly_progress_widget = _weekly_progress(data, tokens)
    top_row_gap = tokens.space_4
    weekly_preferred_width = 448

    def sidebar_is_collapsed() -> bool:
        return sidebar_collapsed() if callable(sidebar_collapsed) else sidebar_collapsed

    def update_day_dividers(visible: tuple[ft.Container, ...]) -> None:
        for column in (yesterday_column, today_column, tomorrow_column):
            column.border = None
        for column in visible[:-1]:
            column.border = ft.Border.only(
                right=ft.BorderSide(tokens.border_width, tokens.dashboard_board_divider)
            )

    def relayout_day_columns(event) -> None:
        board_width = max(0.0, float(getattr(event, "width", 0) or 0))
        if board_width <= 0:
            return

        if board_width >= 900:
            visible_columns = (yesterday_column, today_column, tomorrow_column)
            visible_days = ("yesterday", "today", "tomorrow")
        elif board_width >= 584:
            visible_columns = (today_column, tomorrow_column)
            visible_days = ("today", "tomorrow")
        else:
            visible_columns = (today_column,)
            visible_days = ("today",)

        state = (round(board_width, 2), visible_days)
        if three_day_task_board.data.get("day_layout_state") == state:
            return

        yesterday_column.visible = yesterday_column in visible_columns
        today_column.visible = True
        tomorrow_column.visible = tomorrow_column in visible_columns
        update_day_dividers(visible_columns)
        three_day_task_board.data.update(
            {
                "measured_width": board_width,
                "visible_days": visible_days,
                "day_layout_state": state,
            }
        )
        three_day_task_board.update()

    three_day_task_board.on_size_change = relayout_day_columns

    def relayout_top_row(event) -> None:
        row_width = max(0.0, float(getattr(event, "width", 0) or 0))
        if row_width <= 0:
            return

        maximum_board_width = 1300 if sidebar_is_collapsed() else 1176
        comfortable_row_width = maximum_board_width + top_row_gap + weekly_preferred_width
        if row_width >= comfortable_row_width:
            layout_mode = "board-max-weekly-fill"
            board_width = maximum_board_width
            board_expand: bool | int = False
            weekly_expand: bool | int = True
        elif row_width >= 1000:
            layout_mode = "balanced-two-day"
            board_width = None
            board_expand = 3
            weekly_expand = 2
        else:
            layout_mode = "balanced-one-day"
            board_width = None
            board_expand = 1
            weekly_expand = 1

        state = (layout_mode, maximum_board_width)
        if first_bento_row.data.get("layout_state") == state:
            return

        three_day_task_board.width = board_width
        three_day_task_board.expand = board_expand
        weekly_progress_widget.width = None
        weekly_progress_widget.expand = weekly_expand
        first_bento_row.data.update(
            {
                "layout_mode": layout_mode,
                "layout_state": state,
                "board_max_width": maximum_board_width,
            }
        )
        first_bento_row.update()

    first_bento_row = ft.Row(
        [three_day_task_board, weekly_progress_widget],
        spacing=top_row_gap,
        alignment=ft.MainAxisAlignment.START,
        vertical_alignment=ft.CrossAxisAlignment.STRETCH,
        height=433,
        on_size_change=relayout_top_row,
        data={
            "role": "first-bento-row",
            "widget_gap": top_row_gap,
            "weekly_preferred_width": weekly_preferred_width,
        },
    )

    today_count = len(data.today_tasks)
    dashboard_upper = ft.Column(
        [first_bento_row, build_weather_widget(weather_data, tokens)],
        spacing=tokens.space_4,
        horizontal_alignment=ft.CrossAxisAlignment.START,
        data={"role": "dashboard-upper", "weather_gap": tokens.space_4},
    )
    dashboard_root = page_container(
        ui_text("dashboard.greeting", name=ui_text("profile.display_name")),
        [
            dashboard_upper,
            ft.ResponsiveRow(
                [
                    ft.Container(ft.Column(lower_left, spacing=tokens.space_4), col={"sm": 12, "lg": 8}),
                    ft.Container(
                        ft.Column(
                            [
                                card(ui_text("dashboard.cycle.title"), cycle_controls, tokens),
                            ],
                            spacing=tokens.space_6,
                        ),
                        col={"sm": 12, "lg": 4},
                    ),
                ],
                spacing=tokens.space_6,
                run_spacing=tokens.space_6,
            ),
        ],
        tokens,
        subtitle=ui_text(
            "dashboard.tasks_today.one" if today_count == 1 else "dashboard.tasks_today.other",
            count=today_count,
        ),
        content_spacing=tokens.space_6,
        page_id="dashboard",
        role="dashboard-scroll-root",
    )
    return dashboard_root
