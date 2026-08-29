from __future__ import annotations

from enum import StrEnum

import flet as ft

from overlord.ui.design_system.tokens import STATUS_BADGE_COLORS, StateColors, ThemeTokens


class StatusBadgeSize(StrEnum):
    DEFAULT = "default"
    SMALL = "small"


class StatusBadgeFill(StrEnum):
    SOLID = "solid"
    SUBTLE = "subtle"
    TEXT = "text"


def status_badge(
    status: str,
    label: str,
    tokens: ThemeTokens,
    *,
    size: StatusBadgeSize = StatusBadgeSize.DEFAULT,
    fill: StatusBadgeFill = StatusBadgeFill.SOLID,
) -> ft.Container:
    """Canonical UI-kit status badge shared across presentation surfaces."""
    main, background, text = STATUS_BADGE_COLORS.get(status, STATUS_BADGE_COLORS["inactive"])
    small = size is StatusBadgeSize.SMALL
    if fill is StatusBadgeFill.SUBTLE:
        background = f"1A{main.removeprefix('#')}"
        border_color = f"59{main.removeprefix('#')}"
    elif fill is StatusBadgeFill.TEXT:
        background = ft.Colors.TRANSPARENT
        border_color = ft.Colors.TRANSPARENT
    else:
        border_color = main
    dot_size = 6 if small else 8
    height = 24 if small else 32
    return ft.Container(
        ft.Row(
            [
                ft.Container(width=dot_size, height=dot_size, bgcolor=main, border_radius=dot_size / 2),
                ft.Text(
                    label,
                    size=tokens.text_small if small else tokens.text_body,
                    color=text,
                    weight=ft.FontWeight.W_500,
                    max_lines=1,
                    overflow=ft.TextOverflow.ELLIPSIS,
                ),
            ],
            spacing=tokens.space_1,
            tight=True,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        height=height,
        bgcolor=background,
        border=ft.Border.all(tokens.border_width, border_color),
        border_radius=tokens.space_1 if small else tokens.space_2,
        padding=ft.Padding.symmetric(horizontal=tokens.space_2 if small else tokens.space_4),
        alignment=ft.Alignment.CENTER,
        data={"role": "status-badge", "status": status, "size": size.value, "fill": fill.value},
    )


def state_chip(label: str, colors: StateColors, tokens: ThemeTokens) -> ft.Container:
    return ft.Container(
        ft.Text(label, size=tokens.text_small, color=colors.text, weight=ft.FontWeight.W_600),
        bgcolor=colors.background,
        border=ft.Border.all(tokens.border_width, colors.main),
        border_radius=tokens.radius_pill,
        padding=ft.Padding.symmetric(horizontal=tokens.space_2, vertical=tokens.space_1),
    )
