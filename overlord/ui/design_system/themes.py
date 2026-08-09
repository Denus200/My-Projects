from __future__ import annotations

import flet as ft

from .tokens import DARK_TOKENS, LIGHT_TOKENS, ThemeTokens


def _theme(tokens: ThemeTokens) -> ft.Theme:
    return ft.Theme(
        font_family="Segoe UI",
        focus_color=tokens.accent_primary,
        hover_color=tokens.soft_red_background,
        disabled_color=tokens.text_muted,
        divider_color=tokens.border_default,
        card_bgcolor=tokens.surface_card,
        scaffold_bgcolor=tokens.app_background,
        dialog_theme=ft.DialogTheme(
            bgcolor=tokens.surface_elevated,
            elevation=0,
            actions_padding=tokens.space_4,
        ),
        button_theme=ft.ButtonTheme(
            style=ft.ButtonStyle(elevation=0),
        ),
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


def build_light_theme() -> ft.Theme:
    """Return a session-local theme instance for Flet's mutable patch lifecycle."""
    return _theme(LIGHT_TOKENS)


def build_dark_theme() -> ft.Theme:
    """Return a session-local theme instance for Flet's mutable patch lifecycle."""
    return _theme(DARK_TOKENS)


def flet_theme_mode(value: str) -> ft.ThemeMode:
    return {
        "light": ft.ThemeMode.LIGHT,
        "dark": ft.ThemeMode.DARK,
    }.get(value, ft.ThemeMode.SYSTEM)
