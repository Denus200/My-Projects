from __future__ import annotations

import flet as ft

from .tokens import DARK_TOKENS, LIGHT_TOKENS, ThemeTokens


def _theme(tokens: ThemeTokens) -> ft.Theme:
    return ft.Theme(
        font_family="Segoe UI",
        color_scheme=ft.ColorScheme(
            primary=tokens.accent_primary,
            on_primary=tokens.on_accent,
            secondary=tokens.pink_accent,
            surface=tokens.surface_card,
            on_surface=tokens.text_primary,
            error=tokens.error.main,
            on_error=tokens.on_accent,
            outline=tokens.border_default,
        ),
    )


LIGHT_THEME = _theme(LIGHT_TOKENS)
DARK_THEME = _theme(DARK_TOKENS)


def flet_theme_mode(value: str) -> ft.ThemeMode:
    return {
        "light": ft.ThemeMode.LIGHT,
        "dark": ft.ThemeMode.DARK,
    }.get(value, ft.ThemeMode.SYSTEM)
