from __future__ import annotations

from collections.abc import Iterable

import flet as ft

from overlord.ui.design_system.tokens import ThemeTokens


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
