from __future__ import annotations

import flet as ft

from overlord.application.dashboard import DashboardReadModel
from overlord.application import ApplicationServices
from overlord.presentation.components.common import card, empty_state, page_heading, task_row
from overlord.presentation.design_system.icons import IconName, lucide_icon
from overlord.presentation.design_system.tokens import ThemeTokens


def _task_slots(
    items,
    capacity: int,
    group_name: str,
    services: ApplicationServices,
    tokens: ThemeTokens,
    refresh,
    report_error,
) -> list[ft.Control]:
    controls: list[ft.Control] = []
    for item in items:
        def complete(_event, task_id=item.task.id):
            try:
                services.tasks.complete_task.execute(task_id)
                refresh()
            except Exception as error:
                report_error(str(error))
        controls.append(task_row(item, tokens, on_complete=complete))
    for position in range(len(items) + 1, capacity + 1):
        controls.append(
            ft.Container(
                ft.Text(f"{group_name} {position} · Available", color=tokens.text_muted, size=tokens.text_body),
                bgcolor=tokens.surface_inner,
                border=ft.Border.all(tokens.border_width, tokens.border_default),
                border_radius=tokens.radius_medium,
                padding=tokens.space_3,
            )
        )
    return controls


def _weekly_progress(data: DashboardReadModel, tokens: ThemeTokens) -> ft.Control:
    maximum = max((bar.planned for bar in data.weekly_bars), default=1) or 1
    columns = []
    for bar in data.weekly_bars:
        planned_height = max(tokens.space_1, int(tokens.space_12 * bar.planned / maximum))
        completed_height = max(tokens.space_0, int(tokens.space_12 * bar.completed / maximum))
        columns.append(
            ft.Column(
                [
                    ft.Container(
                        ft.Stack(
                            [
                                ft.Container(bgcolor=tokens.border_default, height=planned_height, width=tokens.space_3, border_radius=tokens.radius_small),
                                ft.Container(bgcolor=tokens.accent_primary, height=completed_height, width=tokens.space_3, border_radius=tokens.radius_small, bottom=0),
                            ],
                            width=tokens.space_3,
                            height=tokens.space_12,
                        ),
                        height=tokens.space_12,
                        alignment=ft.Alignment.BOTTOM_CENTER,
                        tooltip=f"{bar.day.strftime('%A')}: {bar.completed} completed of {bar.planned} planned",
                    ),
                    ft.Text(bar.day.strftime("%a")[0], size=tokens.text_small, color=tokens.text_muted),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=tokens.space_1,
            )
        )
    score = "—" if data.execution_score is None else f"{data.execution_score:.0%}"
    return ft.Column(
        [
            ft.Row(columns, alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            ft.Row(
                [
                    ft.Text("Execution Score", color=tokens.text_secondary),
                    ft.Text(score, color=tokens.text_primary, weight=ft.FontWeight.W_700),
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            ),
            ft.Text(f"Outcome: {data.outcome_label}", color=tokens.text_muted, size=tokens.text_small),
        ],
        spacing=tokens.space_3,
    )


def build_dashboard(
    services: ApplicationServices,
    tokens: ThemeTokens,
    navigate,
    refresh,
    report_error,
) -> ft.Control:
    data = services.dashboard.execute()
    today_controls = [
        ft.Text("Primary", color=tokens.text_secondary, weight=ft.FontWeight.W_600),
        *_task_slots(data.primary, 3, "Primary", services, tokens, refresh, report_error),
        ft.Text("Secondary", color=tokens.text_secondary, weight=ft.FontWeight.W_600),
        *_task_slots(data.secondary, 4, "Secondary", services, tokens, refresh, report_error),
        ft.Text(f"Actual time: {data.actual_time_label}", color=tokens.text_muted, size=tokens.text_small),
    ]
    if data.current_cycle:
        cycle = data.current_cycle
        cycle_controls = [
            ft.Text(f"Week {cycle.week_number} of {cycle.length_weeks}", color=tokens.accent_primary, weight=ft.FontWeight.W_600),
            ft.Text(cycle.main_outcome, color=tokens.text_primary),
            ft.ProgressBar(value=cycle.progress, color=tokens.accent_primary, bgcolor=tokens.border_default, border_radius=tokens.radius_pill),
            ft.Text(f"Next milestone: {cycle.next_milestone or 'Not set'}", color=tokens.text_muted),
            ft.TextButton("Open cycle", on_click=lambda _e: navigate(f"/cycles/{cycle.cycle_id}")),
        ]
    else:
        cycle_controls = [empty_state(
            "No active cycle yet.",
            tokens,
            ft.Button("Create a 12-week plan", on_click=lambda _e: navigate("/cycles")),
        )]
    attention_controls = []
    for item in data.attention:
        attention_controls.append(
            ft.Container(
                ft.Column(
                    [
                        ft.Text(item.title, color=tokens.text_primary, weight=ft.FontWeight.W_600),
                        ft.Text(item.project_title, color=tokens.text_muted, size=tokens.text_small),
                        ft.Text(" · ".join(item.reasons), color=tokens.warning.text, size=tokens.text_small),
                    ],
                    spacing=tokens.space_1,
                ),
                bgcolor=tokens.warning.background,
                border_radius=tokens.radius_medium,
                padding=tokens.space_3,
                on_click=lambda _e, task_id=item.task_id: navigate(f"/tasks?task={task_id}"),
                tooltip=f"Review {item.title}",
            )
        )
    if not attention_controls:
        attention_controls.append(empty_state("Nothing currently needs attention.", tokens))
    decorative = ft.Container(
        ft.Column(
            [
                lucide_icon(IconName.TARGET, color=tokens.pink_accent, size=tokens.icon_display, label="Focus"),
                ft.Text(data.decorative_label, color=tokens.text_primary, size=tokens.text_title, weight=ft.FontWeight.W_600),
                ft.Text("Static placeholder · reduced-motion safe", color=tokens.text_muted, size=tokens.text_small),
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            alignment=ft.MainAxisAlignment.CENTER,
        ),
        bgcolor=tokens.pink_background,
        border_radius=tokens.radius_card,
        padding=tokens.space_6,
    )
    return ft.Column(
        [
            page_heading("Dashboard", data.day.strftime("%A, %B %d"), tokens),
            ft.ResponsiveRow(
                [
                    card("Today’s Tasks", today_controls, tokens, subtitle="3 Primary · 4 Secondary", col={"sm": 12, "lg": 7}),
                    card("Weekly Progress", [_weekly_progress(data, tokens)], tokens, col={"sm": 12, "lg": 5}),
                    card("Needs Attention", attention_controls, tokens, col={"sm": 12, "lg": 7}),
                    card("Current Cycle", cycle_controls, tokens, col={"sm": 12, "lg": 5}),
                    ft.Container(decorative, col=12),
                ],
                spacing=tokens.space_4,
                run_spacing=tokens.space_4,
            ),
        ],
        spacing=tokens.space_5,
        scroll=ft.ScrollMode.AUTO,
        expand=True,
    )
