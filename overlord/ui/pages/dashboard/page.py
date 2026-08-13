from __future__ import annotations

from datetime import date, datetime, timedelta
from urllib.parse import parse_qs, urlparse

import flet as ft

from overlord.app.read_models import TaskListItem
from overlord.app.services import ApplicationServices
from overlord.modules.dashboard.read_models import DashboardReadModel
from overlord.modules.tasks.domain import TaskLifecycle
from overlord.ui.components.controls import primary_button
from overlord.ui.components.feedback import empty_state
from overlord.ui.components.layout import card, page_container
from overlord.ui.components.reorder import reorderable_task_handle
from overlord.ui.components.task_details import build_task_details_dialog
from overlord.ui.components.tasks import build_quick_task_dialog
from overlord.ui.design_system.icons import IconName, lucide_icon
from overlord.ui.design_system.tokens import ThemeTokens
from overlord.ui.strings import (
    format_dashboard_date,
    format_weekday_initial,
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


def _dashboard_task_card(
    item: TaskListItem,
    tokens: ThemeTokens,
    *,
    day: date,
    muted_day: bool,
    on_complete,
    on_open,
) -> ft.Control:
    task = item.task
    completed = task.lifecycle_status is TaskLifecycle.COMPLETED
    text_opacity = 0.42 if completed else 0.72 if muted_day else 1.0
    title_style = ft.TextStyle(
        decoration=ft.TextDecoration.LINE_THROUGH if completed else ft.TextDecoration.NONE,
    )
    text_controls: list[ft.Control] = [
        ft.Text(
            task.title,
            color=tokens.text_primary,
            weight=ft.FontWeight.W_600,
            size=tokens.text_emphasis,
            max_lines=1,
            overflow=ft.TextOverflow.ELLIPSIS,
            style=title_style,
        )
    ]
    if (task.description or "").strip():
        text_controls.append(
            ft.Text(
                task.description or "",
                color=tokens.text_muted,
                size=tokens.text_body,
                max_lines=2,
                overflow=ft.TextOverflow.ELLIPSIS,
                style=title_style if completed else None,
            )
        )

    completion_label = ui_text("dashboard.toggle_task", name=task.title)
    completion_surface = ft.Container(
        lucide_icon(
            IconName.CHECK,
            color=tokens.dashboard_completion_check,
            size=18,
            label=completion_label,
            show_tooltip=False,
        ) if completed else None,
        width=22,
        height=22,
        alignment=ft.Alignment.CENTER,
        bgcolor=tokens.dashboard_completion_fill if completed else None,
        border=ft.Border.all(
            tokens.border_width,
            tokens.dashboard_completion_fill_border if completed else tokens.dashboard_completion_border,
        ),
        border_radius=tokens.radius_pill,
    )
    completion_target = ft.GestureDetector(
        completion_surface,
        mouse_cursor=ft.MouseCursor.CLICK,
        on_tap=on_complete,
        data={"role": "completion", "task_id": task.id},
    )
    completion = ft.Semantics(
        content=completion_target,
        label=completion_label,
        button=True,
        checked=completed,
    )
    task_body = ft.GestureDetector(
        ft.Column(text_controls, spacing=tokens.space_0, expand=True),
        mouse_cursor=ft.MouseCursor.CLICK,
        on_tap=on_open,
        expand=True,
        opacity=text_opacity,
        data={"role": "task-body", "task_id": task.id},
    )
    drag_handle = reorderable_task_handle(
        tokens,
        label=ui_text("dashboard.drag_task", name=task.title),
        data={"task_id": task.id, "day": day.isoformat()},
        muted=completed or muted_day,
    )
    surface = ft.Container(
        ft.Row(
            [
                completion,
                task_body,
                drag_handle,
            ],
            vertical_alignment=ft.CrossAxisAlignment.START,
            spacing=tokens.space_2,
        ),
        bgcolor=tokens.surface_card,
        border=ft.Border.all(tokens.border_width, tokens.border_default),
        border_radius=tokens.radius_card,
        padding=tokens.space_3,
        animate=ft.Animation(tokens.motion_fast, ft.AnimationCurve.EASE_OUT_CUBIC),
        data={"role": "task-card", "task_id": task.id},
    )
    hover = ft.GestureDetector(surface, mouse_cursor=ft.MouseCursor.BASIC)

    def enter(event) -> None:
        surface.border = ft.Border.all(tokens.focus_width, tokens.accent_primary)
        surface.update()

    def exit_hover(event) -> None:
        surface.border = ft.Border.all(tokens.border_width, tokens.border_default)
        surface.update()

    hover.on_enter = enter
    hover.on_exit = exit_hover
    return hover


def _weekly_progress(data: DashboardReadModel, tokens: ThemeTokens) -> ft.Control:
    maximum = max((bar.planned for bar in data.weekly_bars), default=1) or 1
    columns: list[ft.Control] = []
    for bar in data.weekly_bars:
        planned_height = max(tokens.space_1, int(tokens.space_12 * bar.planned / maximum))
        completed_height = int(tokens.space_12 * bar.completed / maximum)
        columns.append(
            ft.Column(
                [
                    ft.Container(
                        ft.Stack(
                            [
                                ft.Container(
                                    bgcolor=tokens.border_strong,
                                    height=planned_height,
                                    width=tokens.space_3,
                                    border_radius=tokens.radius_small,
                                    bottom=0,
                                ),
                                ft.Container(
                                    bgcolor=tokens.accent_primary,
                                    height=completed_height,
                                    width=tokens.space_3,
                                    border_radius=tokens.radius_small,
                                    bottom=0,
                                ),
                            ],
                            width=tokens.space_3,
                            height=tokens.space_12,
                        ),
                        height=tokens.space_12,
                        alignment=ft.Alignment.BOTTOM_CENTER,
                        tooltip=ui_text("dashboard.weekly_tooltip", day=format_weekday_name(bar.day), completed=bar.completed, planned=bar.planned),
                    ),
                    ft.Text(format_weekday_initial(bar.day), size=tokens.text_small, color=tokens.text_muted),
                    ft.Text(f"{bar.completed}/{bar.planned}", size=tokens.text_small, color=tokens.text_secondary),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=tokens.space_1,
            )
        )
    score = "—" if data.execution_score is None else f"{data.execution_score:.0%}"
    completed_total = sum(bar.completed for bar in data.weekly_bars)
    planned_total = sum(bar.planned for bar in data.weekly_bars)
    return ft.Column(
        [
            ft.Row(columns, alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            ft.Divider(color=tokens.border_default),
            ft.Row(
                [
                    ft.Column(
                        [
                            ft.Text(ui_text("dashboard.execution_score"), color=tokens.text_muted, size=tokens.text_small),
                            ft.Text(score, color=tokens.text_primary, size=tokens.text_title, weight=ft.FontWeight.W_700),
                        ],
                        spacing=tokens.space_0,
                    ),
                    ft.Column(
                        [
                            ft.Text(ui_text("dashboard.completed_planned"), color=tokens.text_muted, size=tokens.text_small),
                            ft.Text(f"{completed_total}/{planned_total}", color=tokens.text_primary, weight=ft.FontWeight.W_600),
                        ],
                        spacing=tokens.space_0,
                        horizontal_alignment=ft.CrossAxisAlignment.END,
                    ),
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            ),
            ft.Text(ui_text("dashboard.current_outcome", value=_outcome_label(data.outcome_label)), color=tokens.text_secondary, size=tokens.text_small),
            ft.Text(ui_text("dashboard.actual_time", value=ui_text("common.not_tracked_yet")), color=tokens.text_muted, size=tokens.text_small),
        ],
        spacing=tokens.space_3,
    )


def build_dashboard(
    services: ApplicationServices,
    tokens: ThemeTokens,
    route: str,
    navigate,
    refresh,
    report_error,
    page: ft.Page | None = None,
) -> ft.Control:
    selected_day = _selected_date(route)
    data = services.dashboard.execute(selected_day)
    projects = services.projects.list_projects.execute()
    day_lists: dict[date, ft.ReorderableListView] = {}
    dashboard_root: ft.ListView | None = None

    def items_for(model: DashboardReadModel, day: date) -> tuple[TaskListItem, ...]:
        if day == selected_day - timedelta(days=1):
            return model.yesterday_tasks
        if day == selected_day + timedelta(days=1):
            return model.tomorrow_tasks
        return model.today_tasks

    def close_dialog() -> None:
        if page is not None:
            page.pop_dialog()

    def reload_board() -> None:
        nonlocal data
        data = services.dashboard.execute(selected_day)
        for day, task_list in day_lists.items():
            items = items_for(data, day)
            task_list.controls = task_controls(day, items)
            task_list.header = empty_day_control() if not items else None
            task_list.update()

    def open_create(day: date) -> None:
        if page is None:
            return

        def created(_task) -> None:
            close_dialog()
            reload_board()

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
            reload_board()

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
            )
        )

    def toggle_complete(task_id: int, day: date) -> None:
        try:
            services.tasks.toggle_completion_for_day.execute(task_id, day)
            reload_board()
        except Exception as error:
            report_error(ui_error(error))

    def reorder(event, day: date) -> None:
        old_index = getattr(event, "old_index", None)
        new_index = getattr(event, "new_index", None)
        if old_index is None or new_index is None:
            return
        order = [item.task.id for item in items_for(data, day)]
        if old_index < 0 or old_index >= len(order) or new_index < 0 or new_index > len(order):
            return
        if old_index == new_index:
            return
        moved_task_id = order.pop(old_index)
        order.insert(new_index, moved_task_id)
        try:
            services.tasks.reorder_for_day.execute(day, tuple(order))
            reload_board()
        except Exception as error:
            report_error(ui_error(error))

    def task_controls(day: date, items: tuple[TaskListItem, ...]) -> list[ft.Control]:
        controls = [
            ft.Container(
                _dashboard_task_card(
                    item,
                    tokens,
                    day=day,
                    muted_day=day < selected_day,
                    on_complete=lambda _event, task_id=item.task.id, selected=day: toggle_complete(task_id, selected),
                    on_open=lambda _event, task_id=item.task.id, selected=day: open_details(task_id, selected),
                ),
                padding=ft.Padding.only(bottom=tokens.space_2),
                key=f"dashboard-task-{day.isoformat()}-{item.task.id}",
                data={"role": "task-list-item", "task_id": item.task.id, "gap_after": tokens.space_2},
            )
            for item in items
        ]
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
            dashboard_root.update()

    def release_dashboard_scroll(_event) -> None:
        if dashboard_root is not None and dashboard_root.scroll is None:
            dashboard_root.scroll = ft.ScrollMode.AUTO
            dashboard_root.update()

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
            def enter(_event) -> None:
                surface.border = ft.Border.all(tokens.border_width, tokens.accent_primary)
                surface.update()

            def exit_hover(_event) -> None:
                surface.border = ft.Border.all(tokens.border_width, tokens.dashboard_add_border)
                surface.update()

            control.on_enter = enter
            control.on_exit = exit_hover
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
            bgcolor=tokens.surface_card,
            border=ft.Border.all(tokens.border_width, tokens.border_default),
            border_radius=tokens.radius_pill,
            padding=ft.Padding.symmetric(horizontal=tokens.space_2, vertical=tokens.space_1),
            data={"role": "date-chip", "day": day.isoformat()},
        )
        items = items_for(data, day)
        task_list = ft.ReorderableListView(
            controls=task_controls(day, items),
            spacing=tokens.space_0,
            scroll=ft.ScrollMode.HIDDEN,
            clip_behavior=ft.ClipBehavior.HARD_EDGE,
            expand=True,
            build_controls_on_demand=False,
            show_default_drag_handles=False,
            mouse_cursor=ft.MouseCursor.GRAB,
            header=empty_day_control() if not items else None,
            on_reorder=lambda event, selected=day: reorder(event, selected),
            data={"role": "day-task-list", "day": day.isoformat()},
        )
        day_lists[day] = task_list
        scroll_region = ft.GestureDetector(
            task_list,
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
            padding=ft.Padding.only(
                left=tokens.space_5,
                top=tokens.space_5,
                right=tokens.space_5,
                bottom=tokens.space_4,
            ),
            border=None if last else ft.Border.only(right=ft.BorderSide(tokens.border_width, tokens.border_default)),
            data={"role": "day-column", "day": day.isoformat()},
        )

    yesterday = selected_day - timedelta(days=1)
    tomorrow = selected_day + timedelta(days=1)
    three_day_task_board = ft.Container(
        ft.Row(
            [
                day_column(yesterday, "dashboard.yesterday.title", disabled_add=True),
                day_column(selected_day, "dashboard.today.title", disabled_add=False),
                day_column(tomorrow, "dashboard.tomorrow.title", disabled_add=False, last=True),
            ],
            spacing=tokens.space_0,
            expand=True,
            vertical_alignment=ft.CrossAxisAlignment.STRETCH,
        ),
        height=455,
        bgcolor=tokens.surface_inner,
        border=ft.Border.all(tokens.border_width, tokens.border_default),
        border_radius=tokens.radius_large,
        clip_behavior=ft.ClipBehavior.HARD_EDGE,
        width=1080,
        data={"role": "three-day-task-board", "max_width": 1080},
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

    weekly_progress_widget = ft.Container(
        card(ui_text("dashboard.weekly.title"), [_weekly_progress(data, tokens)], tokens),
        width=360,
        data={"role": "weekly-progress-widget"},
    )

    def resize_first_bento_row(event) -> None:
        available_width = max(0, float(event.width))
        minimum_weekly_width = 320
        wide_layout = available_width >= 1080 + tokens.space_6 + minimum_weekly_width
        board_width = min(1080, available_width)
        weekly_width = available_width - board_width - tokens.space_6 if wide_layout else available_width
        if three_day_task_board.width != board_width:
            three_day_task_board.width = board_width
            three_day_task_board.update()
        if weekly_progress_widget.width != weekly_width:
            weekly_progress_widget.width = weekly_width
            weekly_progress_widget.update()

    first_bento_row = ft.Row(
        [three_day_task_board, weekly_progress_widget],
        spacing=tokens.space_6,
        run_spacing=tokens.space_6,
        wrap=True,
        alignment=ft.MainAxisAlignment.START,
        vertical_alignment=ft.CrossAxisAlignment.START,
        on_size_change=resize_first_bento_row,
        data={"role": "first-bento-row", "widget_gap": tokens.space_6, "responsive_fallback": "wrap"},
    )

    today_count = len(data.today_tasks)
    dashboard_root = page_container(
        ui_text("dashboard.greeting", name=ui_text("profile.display_name")),
        [
            first_bento_row,
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
