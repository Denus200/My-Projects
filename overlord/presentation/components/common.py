from __future__ import annotations

from collections.abc import Callable, Iterable

import flet as ft

from overlord.application.common import TaskListItem
from overlord.domain.tasks import TaskLifecycle
from overlord.presentation.design_system.icons import IconName, lucide_icon
from overlord.presentation.design_system.tokens import StateColors, ThemeTokens


def card(
    title: str,
    controls: Iterable[ft.Control],
    tokens: ThemeTokens,
    *,
    subtitle: str | None = None,
    col: int | dict[str, int] = 12,
) -> ft.Container:
    heading = [
        ft.Text(title, size=tokens.text_title, weight=ft.FontWeight.W_600, color=tokens.text_primary)
    ]
    if subtitle:
        heading.append(ft.Text(subtitle, size=tokens.text_small, color=tokens.text_muted))
    return ft.Container(
        content=ft.Column([*heading, *controls], spacing=tokens.space_3),
        bgcolor=tokens.surface_card,
        border=ft.Border.all(tokens.border_width, tokens.border_default),
        border_radius=tokens.radius_card,
        padding=tokens.space_5,
        col=col,
    )


def state_chip(label: str, colors: StateColors, tokens: ThemeTokens) -> ft.Container:
    return ft.Container(
        ft.Text(label, size=tokens.text_small, color=colors.text, weight=ft.FontWeight.W_600),
        bgcolor=colors.background,
        border=ft.Border.all(tokens.border_width, colors.main),
        border_radius=tokens.radius_pill,
        padding=ft.Padding.symmetric(horizontal=tokens.space_2, vertical=tokens.space_1),
    )


def empty_state(message: str, tokens: ThemeTokens, action: ft.Control | None = None) -> ft.Container:
    controls: list[ft.Control] = [ft.Text(message, color=tokens.text_muted, size=tokens.text_body)]
    if action:
        controls.append(action)
    return ft.Container(
        ft.Column(controls, horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=tokens.space_3),
        alignment=ft.Alignment.CENTER,
        bgcolor=tokens.surface_inner,
        border_radius=tokens.radius_medium,
        padding=tokens.space_6,
    )


def loading_state(message: str, tokens: ThemeTokens) -> ft.Container:
    return ft.Container(
        ft.Column(
            [
                ft.ProgressRing(color=tokens.accent_primary, bgcolor=tokens.border_default),
                ft.Text(message, color=tokens.text_secondary, size=tokens.text_body),
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=tokens.space_3,
        ),
        alignment=ft.Alignment.CENTER,
        bgcolor=tokens.surface_inner,
        border_radius=tokens.radius_medium,
        padding=tokens.space_6,
    )


def task_row(
    item: TaskListItem,
    tokens: ThemeTokens,
    *,
    on_complete: Callable[[object], None] | None = None,
    on_edit: Callable[[object], None] | None = None,
) -> ft.Container:
    lifecycle = item.task.lifecycle_status
    status = lifecycle.value.replace("_", " ").title() if lifecycle else "Review status"
    color = tokens.warning if lifecycle is None else (
        tokens.success if lifecycle is TaskLifecycle.COMPLETED else tokens.neutral
    )
    actions: list[ft.Control] = []
    if on_edit:
        actions.append(ft.TextButton("Edit", on_click=on_edit, tooltip=f"Edit {item.task.title}"))
    if on_complete and lifecycle is not TaskLifecycle.COMPLETED:
        actions.append(
            ft.Button(
                lucide_icon(IconName.CHECK, color=tokens.on_accent, size=tokens.icon_small, label="Complete task"),
                bgcolor=tokens.accent_primary,
                elevation=0,
                on_click=on_complete,
                tooltip=f"Complete {item.task.title}",
            )
        )
    metadata = [item.project_title]
    if item.current_plan:
        metadata.append(item.current_plan.planned_date.strftime("%b %d"))
    if item.open_blockers:
        metadata.append(f"{item.open_blockers} open blocker")
    return ft.Container(
        ft.Row(
            [
                ft.Column(
                    [
                        ft.Text(item.task.title, color=tokens.text_primary, weight=ft.FontWeight.W_600),
                        ft.Text(" · ".join(metadata), color=tokens.text_muted, size=tokens.text_small),
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


def page_heading(title: str, subtitle: str, tokens: ThemeTokens, actions: Iterable[ft.Control] = ()) -> ft.Row:
    return ft.Row(
        [
            ft.Column(
                [
                    ft.Text(title, size=tokens.text_display, weight=ft.FontWeight.W_700, color=tokens.text_primary),
                    ft.Text(subtitle, size=tokens.text_body, color=tokens.text_secondary),
                ],
                spacing=tokens.space_1,
                expand=True,
            ),
            *actions,
        ],
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
    )
