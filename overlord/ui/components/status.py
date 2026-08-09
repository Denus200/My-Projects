from __future__ import annotations

import flet as ft

from overlord.ui.design_system.tokens import StateColors, ThemeTokens


def state_chip(label: str, colors: StateColors, tokens: ThemeTokens) -> ft.Container:
    return ft.Container(
        ft.Text(label, size=tokens.text_small, color=colors.text, weight=ft.FontWeight.W_600),
        bgcolor=colors.background,
        border=ft.Border.all(tokens.border_width, colors.main),
        border_radius=tokens.radius_pill,
        padding=ft.Padding.symmetric(horizontal=tokens.space_2, vertical=tokens.space_1),
    )
