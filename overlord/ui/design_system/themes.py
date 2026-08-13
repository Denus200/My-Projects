from __future__ import annotations

import flet as ft

from .styles import (
    ButtonVariant,
    alt_role,
    button_style,
    checkbox_defaults,
    menu_style,
    table_theme,
    text_button_style,
)
from .tokens import DARK_TOKENS, LIGHT_TOKENS, ThemeTokens


def _text_theme(tokens: ThemeTokens) -> ft.TextTheme:
    return ft.TextTheme(
        body_large=ft.TextStyle(size=tokens.text_emphasis, height=tokens.line_height_body, color=tokens.text_primary),
        body_medium=ft.TextStyle(size=tokens.text_body, height=tokens.line_height_body, color=tokens.text_primary),
        body_small=ft.TextStyle(size=tokens.text_small, height=tokens.line_height_body, color=tokens.text_secondary),
        headline_small=ft.TextStyle(size=tokens.text_title, height=1.25, color=tokens.text_primary, weight=ft.FontWeight.W_600),
        title_large=ft.TextStyle(size=tokens.text_display, height=1.2, color=tokens.text_primary, weight=ft.FontWeight.W_700),
        title_medium=ft.TextStyle(size=tokens.text_title, height=1.25, color=tokens.text_primary, weight=ft.FontWeight.W_600),
        title_small=ft.TextStyle(size=tokens.text_emphasis, height=1.3, color=tokens.text_primary, weight=ft.FontWeight.W_600),
        label_large=ft.TextStyle(size=tokens.text_body, height=1.2, color=tokens.text_primary, weight=ft.FontWeight.W_600),
        label_medium=ft.TextStyle(size=tokens.text_small, height=1.2, color=tokens.text_secondary, weight=ft.FontWeight.W_600),
        label_small=ft.TextStyle(size=tokens.text_small, height=1.2, color=tokens.text_muted),
    )


def _theme(tokens: ThemeTokens, *, motion_enabled: bool = True) -> ft.Theme:
    check = checkbox_defaults(tokens)
    return ft.Theme(
        font_family="Segoe UI",
        visual_density=ft.VisualDensity.COMPACT,
        focus_color=tokens.accent_primary,
        hover_color=tokens.interactive_hover,
        disabled_color=tokens.text_disabled,
        divider_color=tokens.border_default,
        card_bgcolor=tokens.surface_card,
        scaffold_bgcolor=tokens.app_background,
        text_theme=_text_theme(tokens),
        card_theme=ft.CardTheme(
            color=tokens.surface_card,
            elevation=0,
            shape=ft.RoundedRectangleBorder(
                side=ft.BorderSide(tokens.border_width, tokens.border_default),
                radius=tokens.radius_card,
            ),
        ),
        dialog_theme=ft.DialogTheme(
            bgcolor=tokens.surface_elevated,
            elevation=0,
            shape=ft.RoundedRectangleBorder(
                side=ft.BorderSide(tokens.border_width, tokens.border_default),
                radius=tokens.radius_large,
            ),
            title_text_style=ft.TextStyle(
                size=tokens.text_title,
                color=tokens.text_primary,
                weight=ft.FontWeight.W_600,
            ),
            content_text_style=ft.TextStyle(size=tokens.text_body, color=tokens.text_secondary),
            actions_padding=tokens.space_4,
            barrier_color=tokens.scrim,
        ),
        button_theme=ft.ButtonTheme(
            style=button_style(tokens, ButtonVariant.PRIMARY, motion_enabled=motion_enabled),
        ),
        filled_button_theme=ft.FilledButtonTheme(
            style=button_style(tokens, ButtonVariant.PRIMARY, motion_enabled=motion_enabled),
        ),
        outlined_button_theme=ft.OutlinedButtonTheme(
            style=button_style(tokens, ButtonVariant.SECONDARY, motion_enabled=motion_enabled),
        ),
        text_button_theme=ft.TextButtonTheme(style=text_button_style(tokens, motion_enabled=motion_enabled)),
        dropdown_theme=ft.DropdownTheme(
            menu_style=menu_style(tokens),
            text_style=ft.TextStyle(size=tokens.text_body, color=tokens.text_primary),
        ),
        checkbox_theme=ft.CheckboxTheme(
            overlay_color=check["overlay_color"],
            check_color=check["check_color"],
            fill_color=check["fill_color"],
            splash_radius=check["splash_radius"],
            border_side=ft.BorderSide(tokens.border_width, tokens.border_strong),
            visual_density=ft.VisualDensity.COMPACT,
            mouse_cursor={
                ft.ControlState.DISABLED: ft.MouseCursor.FORBIDDEN,
                ft.ControlState.DEFAULT: ft.MouseCursor.CLICK,
            },
        ),
        switch_theme=ft.SwitchTheme(
            thumb_color={
                ft.ControlState.DISABLED: tokens.text_disabled,
                ft.ControlState.SELECTED: tokens.on_accent,
                ft.ControlState.DEFAULT: tokens.surface_card,
            },
            track_color={
                ft.ControlState.DISABLED: tokens.control_background_disabled,
                ft.ControlState.SELECTED: tokens.accent_primary,
                ft.ControlState.HOVERED: tokens.interactive_hover,
                ft.ControlState.DEFAULT: tokens.border_strong,
            },
            overlay_color={
                ft.ControlState.PRESSED: tokens.interactive_pressed,
                ft.ControlState.HOVERED: tokens.interactive_hover,
                ft.ControlState.FOCUSED: tokens.interactive_selected,
                ft.ControlState.DEFAULT: ft.Colors.TRANSPARENT,
            },
            track_outline_color={
                ft.ControlState.FOCUSED: tokens.focus_ring,
                ft.ControlState.DEFAULT: tokens.border_strong,
            },
            track_outline_width={
                ft.ControlState.FOCUSED: tokens.focus_width,
                ft.ControlState.DEFAULT: tokens.border_width,
            },
            mouse_cursor={
                ft.ControlState.DISABLED: ft.MouseCursor.FORBIDDEN,
                ft.ControlState.DEFAULT: ft.MouseCursor.CLICK,
            },
            padding=tokens.space_1,
        ),
        chip_theme=ft.ChipTheme(
            color={
                ft.ControlState.DISABLED: tokens.text_disabled,
                ft.ControlState.SELECTED: alt_role(tokens, tokens.accent_alt, tokens.accent_primary),
                ft.ControlState.HOVERED: alt_role(tokens, tokens.accent_alt_hover, tokens.accent_primary_hover),
                ft.ControlState.DEFAULT: tokens.text_secondary,
            },
            bgcolor=tokens.control_background,
            selected_color=alt_role(tokens, tokens.interactive_selected_alt, tokens.interactive_selected),
            disabled_color=tokens.control_background_disabled,
            check_color=alt_role(tokens, tokens.accent_alt, tokens.accent_primary),
            elevation=0,
            elevation_on_click=0,
            shape=ft.RoundedRectangleBorder(radius=tokens.radius_pill),
            padding=ft.Padding.symmetric(horizontal=tokens.space_2, vertical=tokens.space_1),
            label_text_style=ft.TextStyle(size=tokens.text_small, weight=ft.FontWeight.W_600),
            border_side=ft.BorderSide(tokens.border_width, tokens.border_strong),
            show_checkmark=True,
        ),
        data_table_theme=table_theme(tokens),
        color_scheme=ft.ColorScheme(
            primary=tokens.accent_primary,
            on_primary=tokens.on_accent,
            secondary=alt_role(tokens, tokens.accent_alt, tokens.pink_accent),
            surface=tokens.surface_card,
            on_surface=tokens.text_primary,
            error=tokens.error.main,
            on_error=tokens.on_accent,
            outline=tokens.border_default,
        ),
    )


def build_light_theme(*, motion_enabled: bool = True) -> ft.Theme:
    """Return a session-local theme instance for Flet's mutable patch lifecycle."""
    return _theme(LIGHT_TOKENS, motion_enabled=motion_enabled)


def build_dark_theme(*, motion_enabled: bool = True) -> ft.Theme:
    """Return a session-local theme instance for Flet's mutable patch lifecycle."""
    return _theme(DARK_TOKENS, motion_enabled=motion_enabled)


def flet_theme_mode(value: str) -> ft.ThemeMode:
    return {
        "light": ft.ThemeMode.LIGHT,
        "dark": ft.ThemeMode.DARK,
    }.get(value, ft.ThemeMode.SYSTEM)
