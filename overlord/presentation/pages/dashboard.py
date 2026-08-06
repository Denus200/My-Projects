from __future__ import annotations

from datetime import date
from urllib.parse import parse_qs, urlparse

import flet as ft

from overlord.application import ApplicationServices
from overlord.application.common import TaskListItem
from overlord.application.dashboard import DashboardReadModel
from overlord.domain.tasks import TaskLifecycle
from overlord.presentation.components.common import card, empty_state, page_heading, state_chip
from overlord.presentation.design_system.icons import IconName, lucide_icon
from overlord.presentation.design_system.tokens import ThemeTokens
from overlord.presentation.strings import ui_text


def _selected_date(route: str) -> date:
    raw = parse_qs(urlparse(route).query).get("date", [date.today().isoformat()])[0]
    try:
        return date.fromisoformat(raw)
    except ValueError:
        return date.today()


def _task_status(item: TaskListItem, tokens: ThemeTokens):
    lifecycle = item.task.lifecycle_status
    label = lifecycle.value.replace("_", " ").title() if lifecycle else "Review status"
    colors = tokens.warning if lifecycle is None else (
        tokens.success if lifecycle is TaskLifecycle.COMPLETED else (
            tokens.info if lifecycle is TaskLifecycle.IN_PROGRESS else tokens.neutral
        )
    )
    return label, colors


def _dashboard_task_row(
    item: TaskListItem,
    tokens: ThemeTokens,
    *,
    primary: bool,
    on_complete,
) -> ft.Control:
    task = item.task
    status, status_colors = _task_status(item, tokens)
    metadata = [item.project_title, status]
    if task.estimate_minutes:
        metadata.append(f"{task.estimate_minutes} min")
    if task.importance:
        metadata.append("Important")
    if task.urgency:
        metadata.append("Urgent")
    attention: list[str] = []
    if item.open_blockers:
        attention.append("Open blocker")
    if item.carry_over_count >= 2:
        attention.append(f"Carried over {item.carry_over_count} times")

    trailing: list[ft.Control] = [state_chip(status, status_colors, tokens)]
    if task.lifecycle_status is not TaskLifecycle.COMPLETED:
        trailing.append(
            ft.Button(
                lucide_icon(IconName.CHECK, color=tokens.on_accent, size=tokens.icon_small, label=f"Complete {task.title}"),
                bgcolor=tokens.accent_primary,
                color=tokens.on_accent,
                elevation=0,
                tooltip=f"Complete {task.title}",
                on_click=on_complete,
            )
        )

    details: list[ft.Control] = [
        ft.Text(
            task.title,
            color=tokens.text_muted if task.lifecycle_status is TaskLifecycle.COMPLETED else tokens.text_primary,
            weight=ft.FontWeight.W_600,
            size=tokens.text_emphasis if primary else tokens.text_body,
        ),
        ft.Text(" · ".join(metadata), color=tokens.text_muted, size=tokens.text_small),
    ]
    if primary and task.next_action:
        details.append(ft.Text(f"Next: {task.next_action}", color=tokens.text_secondary, size=tokens.text_small))
    if attention:
        details.append(ft.Text(" · ".join(attention), color=tokens.warning.text, size=tokens.text_small))

    return ft.Container(
        ft.Row(
            [
                ft.Column(details, spacing=tokens.space_1, expand=True),
                *trailing,
            ],
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=tokens.space_2,
        ),
        bgcolor=tokens.surface_elevated if primary else tokens.surface_inner,
        border=ft.Border.only(
            left=ft.BorderSide(tokens.focus_width if primary else tokens.border_width, tokens.accent_primary if primary else tokens.border_default)
        ),
        border_radius=tokens.radius_medium,
        padding=tokens.space_3,
    )


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
                        tooltip=f"{bar.day.strftime('%A')}: {bar.completed} completed of {bar.planned} planned",
                    ),
                    ft.Text(bar.day.strftime("%a")[0], size=tokens.text_small, color=tokens.text_muted),
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
                            ft.Text("Execution Score", color=tokens.text_muted, size=tokens.text_small),
                            ft.Text(score, color=tokens.text_primary, size=tokens.text_title, weight=ft.FontWeight.W_700),
                        ],
                        spacing=tokens.space_0,
                    ),
                    ft.Column(
                        [
                            ft.Text("Completed / planned", color=tokens.text_muted, size=tokens.text_small),
                            ft.Text(f"{completed_total}/{planned_total}", color=tokens.text_primary, weight=ft.FontWeight.W_600),
                        ],
                        spacing=tokens.space_0,
                        horizontal_alignment=ft.CrossAxisAlignment.END,
                    ),
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            ),
            ft.Text(f"Current Outcome: {data.outcome_label}", color=tokens.text_secondary, size=tokens.text_small),
            ft.Text(ui_text("dashboard.actual_time", value=data.actual_time_label), color=tokens.text_muted, size=tokens.text_small),
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
) -> ft.Control:
    selected_day = _selected_date(route)
    data = services.dashboard.execute(selected_day)

    def complete(task_id: int):
        def action(_event):
            try:
                services.tasks.complete_task.execute(task_id)
                refresh()
            except Exception as error:
                report_error(str(error))
        return action

    today_controls: list[ft.Control] = []
    if not data.primary and not data.secondary:
        today_controls.append(
            ft.Container(
                ft.Column(
                    [
                        ft.Text(
                            ui_text("dashboard.today.empty.title"),
                            color=tokens.text_primary,
                            size=tokens.text_title,
                            weight=ft.FontWeight.W_600,
                        ),
                        ft.Text(ui_text("dashboard.today.empty.description"), color=tokens.text_secondary),
                        ft.Button(
                            ui_text("dashboard.plan_day"),
                            bgcolor=tokens.accent_primary,
                            color=tokens.on_accent,
                            on_click=lambda _e: navigate(f"/planning/day?date={data.day.isoformat()}"),
                        ),
                    ],
                    spacing=tokens.space_3,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                alignment=ft.Alignment.CENTER,
                bgcolor=tokens.surface_inner,
                border_radius=tokens.radius_medium,
                padding=tokens.space_8,
            )
        )
    else:
        if data.primary:
            today_controls.extend(
                [
                    ft.Row(
                        [
                            ft.Text(ui_text("dashboard.primary"), color=tokens.text_primary, weight=ft.FontWeight.W_700),
                            ft.Text(f"{len(data.primary)}/3", color=tokens.accent_primary, weight=ft.FontWeight.W_600),
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    ),
                    *[
                        _dashboard_task_row(item, tokens, primary=True, on_complete=complete(item.task.id))
                        for item in data.primary
                    ],
                ]
            )
        if data.secondary:
            today_controls.extend(
                [
                    ft.Row(
                        [
                            ft.Text(ui_text("dashboard.secondary"), color=tokens.text_secondary, weight=ft.FontWeight.W_600),
                            ft.Text(f"{len(data.secondary)}/4", color=tokens.text_muted),
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    ),
                    *[
                        _dashboard_task_row(item, tokens, primary=False, on_complete=complete(item.task.id))
                        for item in data.secondary
                    ],
                ]
            )

    if data.current_cycle:
        cycle = data.current_cycle
        cycle_controls = [
            ft.Row(
                [
                    ft.Text(f"Week {cycle.week_number} of {cycle.length_weeks}", color=tokens.accent_primary, weight=ft.FontWeight.W_600),
                    ft.Text(f"{cycle.days_remaining} days remaining", color=tokens.text_muted, size=tokens.text_small),
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            ),
            ft.Text(cycle.title, color=tokens.text_primary, weight=ft.FontWeight.W_700),
            ft.Text(cycle.main_outcome, color=tokens.text_secondary, size=tokens.text_small),
            ft.ProgressBar(value=cycle.progress, color=tokens.accent_primary, bgcolor=tokens.border_default, border_radius=tokens.radius_pill),
            ft.Text(f"Current Outcome: {cycle.weekly_outcome}", color=tokens.text_secondary, size=tokens.text_small),
            ft.Text(f"Next milestone: {cycle.next_milestone or 'Not set'}", color=tokens.text_muted, size=tokens.text_small),
            ft.TextButton("Open cycle", on_click=lambda _e: navigate(f"/cycles/{cycle.cycle_id}")),
        ]
    else:
        cycle_controls = [
            empty_state("No active Cycle yet.", tokens, ft.Button("Create a 12-week plan", on_click=lambda _e: navigate("/cycles")))
        ]

    attention_controls = [
        ft.Container(
            ft.Row(
                [
                    lucide_icon(IconName.ALERT, color=tokens.warning.main, size=tokens.icon_medium, label="Needs attention"),
                    ft.Column(
                        [
                            ft.Text(item.title, color=tokens.text_primary, weight=ft.FontWeight.W_600),
                            ft.Text(item.project_title, color=tokens.text_muted, size=tokens.text_small),
                            ft.Text(" · ".join(item.reasons), color=tokens.text_secondary, size=tokens.text_small),
                        ],
                        spacing=tokens.space_1,
                        expand=True,
                    ),
                    ft.TextButton("Review", on_click=lambda _e, task_id=item.task_id: navigate(f"/tasks?task={task_id}")),
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

    left_cards: list[ft.Control] = [
        card(
            ui_text("dashboard.today.title"),
            today_controls,
            tokens,
            subtitle=ui_text("dashboard.today.capacity"),
        )
    ]
    if attention_controls:
        left_cards.append(card(ui_text("dashboard.attention.title"), attention_controls, tokens))

    return ft.Column(
        [
            page_heading(
                ui_text("dashboard.title"),
                data.day.strftime("%A, %B %d"),
                tokens,
                [
                    ft.Button(
                        ui_text("dashboard.plan_day"),
                        bgcolor=tokens.accent_primary,
                        color=tokens.on_accent,
                        on_click=lambda _e: navigate(f"/planning/day?date={data.day.isoformat()}"),
                    )
                ],
            ),
            ft.ResponsiveRow(
                [
                    ft.Container(ft.Column(left_cards, spacing=tokens.space_4), col={"sm": 12, "lg": 8}),
                    ft.Container(
                        ft.Column(
                            [
                                card(ui_text("dashboard.cycle.title"), cycle_controls, tokens),
                                card(ui_text("dashboard.weekly.title"), [_weekly_progress(data, tokens)], tokens),
                            ],
                            spacing=tokens.space_4,
                        ),
                        col={"sm": 12, "lg": 4},
                    ),
                ],
                spacing=tokens.space_4,
                run_spacing=tokens.space_4,
            ),
        ],
        spacing=tokens.space_5,
        scroll=ft.ScrollMode.AUTO,
        expand=True,
    )
