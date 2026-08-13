from __future__ import annotations

from enum import StrEnum

import flet as ft

from .tokens import ThemeTokens


class ButtonVariant(StrEnum):
    PRIMARY = "primary"
    SECONDARY = "secondary"
    TERTIARY = "tertiary"
    DANGER = "danger"


def _cursor_states() -> dict[ft.ControlState, ft.MouseCursor]:
    return {
        ft.ControlState.DISABLED: ft.MouseCursor.FORBIDDEN,
        ft.ControlState.DEFAULT: ft.MouseCursor.CLICK,
    }


def alt_role(tokens: ThemeTokens, alt: str | None, current: str) -> str:
    """Use the approved light alt role without changing the current dark palette."""
    return alt if alt is not None else current


def _button_colors(tokens: ThemeTokens, variant: ButtonVariant) -> tuple[dict, dict, dict]:
    if variant is ButtonVariant.PRIMARY:
        foreground = {
            ft.ControlState.DISABLED: tokens.text_disabled,
            ft.ControlState.DEFAULT: tokens.on_accent,
        }
        background = {
            ft.ControlState.DISABLED: tokens.accent_primary_disabled,
            ft.ControlState.PRESSED: tokens.accent_primary_pressed,
            ft.ControlState.HOVERED: tokens.accent_primary_hover,
            ft.ControlState.FOCUSED: tokens.accent_primary,
            ft.ControlState.DEFAULT: tokens.accent_primary,
        }
        border = {
            ft.ControlState.DISABLED: ft.BorderSide(tokens.border_width, tokens.accent_primary_disabled),
            ft.ControlState.FOCUSED: ft.BorderSide(tokens.focus_width, tokens.focus_ring),
            ft.ControlState.DEFAULT: ft.BorderSide(tokens.border_width, tokens.accent_primary),
        }
        return foreground, background, border

    if variant is ButtonVariant.DANGER:
        foreground = {
            ft.ControlState.DISABLED: tokens.text_disabled,
            ft.ControlState.DEFAULT: tokens.error.text,
        }
        background = {
            ft.ControlState.DISABLED: tokens.control_background_disabled,
            ft.ControlState.PRESSED: tokens.error.background,
            ft.ControlState.HOVERED: tokens.error.background,
            ft.ControlState.FOCUSED: tokens.control_background,
            ft.ControlState.DEFAULT: tokens.control_background,
        }
        border = {
            ft.ControlState.DISABLED: ft.BorderSide(tokens.border_width, tokens.border_default),
            ft.ControlState.FOCUSED: ft.BorderSide(tokens.focus_width, tokens.error.main),
            ft.ControlState.DEFAULT: ft.BorderSide(tokens.border_width, tokens.error.main),
        }
        return foreground, background, border

    is_tertiary = variant is ButtonVariant.TERTIARY
    foreground = {
        ft.ControlState.DISABLED: tokens.text_disabled,
        ft.ControlState.PRESSED: alt_role(tokens, tokens.accent_alt_pressed, tokens.accent_primary) if is_tertiary else tokens.text_primary,
        ft.ControlState.HOVERED: alt_role(tokens, tokens.accent_alt_hover, tokens.accent_primary) if is_tertiary else tokens.text_primary,
        ft.ControlState.DEFAULT: tokens.text_primary if variant is ButtonVariant.SECONDARY else alt_role(tokens, tokens.accent_alt, tokens.accent_primary),
    }
    background = {
        ft.ControlState.DISABLED: tokens.control_background_disabled,
        ft.ControlState.PRESSED: alt_role(tokens, tokens.interactive_pressed_alt, tokens.interactive_pressed) if is_tertiary else tokens.interactive_pressed,
        ft.ControlState.HOVERED: alt_role(tokens, tokens.interactive_hover_alt, tokens.interactive_hover) if is_tertiary else tokens.interactive_hover,
        ft.ControlState.FOCUSED: tokens.control_background,
        ft.ControlState.DEFAULT: tokens.control_background if variant is ButtonVariant.SECONDARY else ft.Colors.TRANSPARENT,
    }
    border = {
        ft.ControlState.DISABLED: ft.BorderSide(tokens.border_width, tokens.border_default),
        ft.ControlState.FOCUSED: ft.BorderSide(tokens.focus_width, tokens.focus_ring),
        ft.ControlState.DEFAULT: ft.BorderSide(
            tokens.border_width,
            tokens.border_default if variant is ButtonVariant.SECONDARY else ft.Colors.TRANSPARENT,
        ),
    }
    return foreground, background, border


def button_style(
    tokens: ThemeTokens,
    variant: ButtonVariant = ButtonVariant.PRIMARY,
    *,
    motion_enabled: bool = True,
    compact: bool = False,
) -> ft.ButtonStyle:
    foreground, background, border = _button_colors(tokens, variant)
    return ft.ButtonStyle(
        color=foreground,
        bgcolor=background,
        side=border,
        overlay_color=ft.Colors.TRANSPARENT,
        elevation={ft.ControlState.DEFAULT: 0},
        animation_duration=tokens.motion_fast if motion_enabled else tokens.motion_none,
        padding=ft.Padding.symmetric(
            horizontal=tokens.space_3 if compact else tokens.button_padding_horizontal,
            vertical=tokens.space_2,
        ),
        shape=ft.RoundedRectangleBorder(radius=tokens.radius_medium),
        text_style=ft.TextStyle(
            size=tokens.text_body,
            height=tokens.line_height_body,
            weight=ft.FontWeight.W_600,
        ),
        mouse_cursor=_cursor_states(),
        enable_feedback=True,
    )


def text_button_style(tokens: ThemeTokens, *, motion_enabled: bool = True) -> ft.ButtonStyle:
    return button_style(tokens, ButtonVariant.TERTIARY, motion_enabled=motion_enabled, compact=True)


def selection_button_style(
    tokens: ThemeTokens,
    *,
    selected: bool,
    motion_enabled: bool = True,
) -> ft.ButtonStyle:
    style = button_style(tokens, ButtonVariant.SECONDARY, motion_enabled=motion_enabled, compact=True)
    selected_accent = alt_role(tokens, tokens.accent_alt, tokens.accent_primary)
    selected_surface = alt_role(tokens, tokens.interactive_selected_alt, tokens.interactive_selected)
    style.color = {
        ft.ControlState.DISABLED: tokens.text_disabled,
        ft.ControlState.SELECTED: selected_accent,
        ft.ControlState.DEFAULT: selected_accent if selected else tokens.text_secondary,
    }
    style.bgcolor = {
        ft.ControlState.DISABLED: tokens.control_background_disabled,
        ft.ControlState.PRESSED: alt_role(tokens, tokens.interactive_pressed_alt, tokens.interactive_pressed),
        ft.ControlState.HOVERED: alt_role(tokens, tokens.interactive_hover_alt, tokens.interactive_hover),
        ft.ControlState.FOCUSED: selected_surface if selected else tokens.control_background,
        ft.ControlState.DEFAULT: selected_surface if selected else tokens.control_background,
    }
    style.side = {
        ft.ControlState.DISABLED: ft.BorderSide(tokens.border_width, tokens.border_default),
        ft.ControlState.FOCUSED: ft.BorderSide(tokens.focus_width, tokens.focus_ring),
        ft.ControlState.DEFAULT: ft.BorderSide(
            tokens.focus_width if selected else tokens.border_width,
            selected_accent if selected else tokens.border_default,
        ),
    }
    return style


def field_defaults(tokens: ThemeTokens, *, compact: bool = False) -> dict:
    vertical = tokens.space_2 if compact else tokens.field_padding_vertical
    return {
        "border": ft.InputBorder.OUTLINE,
        "border_radius": tokens.radius_medium,
        "border_width": tokens.border_width,
        "border_color": tokens.border_default,
        "focused_border_width": tokens.focus_width,
        "focused_border_color": tokens.focus_ring,
        "filled": True,
        "fill_color": tokens.control_background,
        "focused_bgcolor": tokens.control_background,
        "hover_color": tokens.control_background_hover,
        "color": tokens.text_primary,
        "cursor_color": tokens.accent_primary,
        "selection_color": tokens.interactive_selected,
        "text_size": tokens.text_body,
        "label_style": ft.TextStyle(size=tokens.text_small, color=tokens.text_secondary),
        "hint_style": ft.TextStyle(size=tokens.text_body, color=tokens.text_muted),
        "helper_style": ft.TextStyle(size=tokens.text_small, color=tokens.text_muted),
        "error_style": ft.TextStyle(size=tokens.text_small, color=tokens.error.text),
        "content_padding": ft.Padding.symmetric(
            horizontal=tokens.field_padding_horizontal,
            vertical=vertical,
        ),
        "dense": compact,
    }


def menu_style(tokens: ThemeTokens) -> ft.MenuStyle:
    return ft.MenuStyle(
        bgcolor={ft.ControlState.DEFAULT: tokens.surface_elevated},
        elevation={ft.ControlState.DEFAULT: 4},
        padding=tokens.space_1,
        side={ft.ControlState.DEFAULT: ft.BorderSide(tokens.border_width, tokens.border_default)},
        shape={ft.ControlState.DEFAULT: ft.RoundedRectangleBorder(radius=tokens.radius_medium)},
        mouse_cursor=_cursor_states(),
    )


def dropdown_defaults(tokens: ThemeTokens, *, compact: bool = False) -> dict:
    defaults = field_defaults(tokens, compact=compact)
    defaults.pop("cursor_color")
    defaults.pop("selection_color")
    defaults.pop("focused_bgcolor")
    defaults.pop("helper_style")
    defaults.pop("error_style")
    defaults.update(
        {
            "bgcolor": {
                ft.ControlState.DISABLED: tokens.control_background_disabled,
                ft.ControlState.HOVERED: tokens.control_background_hover,
                ft.ControlState.DEFAULT: tokens.control_background,
            },
            "menu_height": 320,
            "menu_style": menu_style(tokens),
            "enable_search": True,
            "elevation": 4,
        }
    )
    return defaults


def checkbox_defaults(tokens: ThemeTokens) -> dict:
    return {
        "fill_color": {
            ft.ControlState.DISABLED: tokens.control_background_disabled,
            ft.ControlState.SELECTED: tokens.accent_primary,
            ft.ControlState.HOVERED: tokens.control_background_hover,
            ft.ControlState.DEFAULT: tokens.control_background,
        },
        "check_color": tokens.on_accent,
        "overlay_color": {
            ft.ControlState.PRESSED: tokens.interactive_pressed,
            ft.ControlState.HOVERED: tokens.interactive_hover,
            ft.ControlState.FOCUSED: tokens.interactive_selected,
            ft.ControlState.DEFAULT: ft.Colors.TRANSPARENT,
        },
        "border_side": {
            ft.ControlState.DISABLED: ft.BorderSide(tokens.border_width, tokens.border_default),
            ft.ControlState.FOCUSED: ft.BorderSide(tokens.focus_width, tokens.focus_ring),
            ft.ControlState.DEFAULT: ft.BorderSide(tokens.border_width, tokens.border_strong),
        },
        "label_style": ft.TextStyle(size=tokens.text_body, color=tokens.text_primary),
        "mouse_cursor": ft.MouseCursor.CLICK,
        "visual_density": ft.VisualDensity.COMPACT,
        "splash_radius": tokens.control_height / 2,
    }


def table_theme(tokens: ThemeTokens) -> ft.DataTableTheme:
    return ft.DataTableTheme(
        column_spacing=tokens.space_6,
        data_row_min_height=tokens.table_row_height,
        data_row_max_height=tokens.table_row_height,
        data_row_color={
            ft.ControlState.SELECTED: alt_role(tokens, tokens.interactive_selected_alt, tokens.interactive_selected),
            ft.ControlState.HOVERED: alt_role(tokens, tokens.interactive_hover_alt, tokens.interactive_hover),
            ft.ControlState.DEFAULT: tokens.surface_card,
        },
        data_text_style=ft.TextStyle(size=tokens.text_body, color=tokens.text_primary),
        divider_thickness=tokens.border_width,
        horizontal_margin=tokens.space_4,
        heading_text_style=ft.TextStyle(
            size=tokens.text_small,
            color=tokens.text_secondary,
            weight=ft.FontWeight.W_600,
        ),
        heading_row_color={ft.ControlState.DEFAULT: tokens.surface_inner},
        heading_row_height=tokens.table_heading_height,
        data_row_cursor=_cursor_states(),
        heading_cell_cursor=_cursor_states(),
        decoration=ft.BoxDecoration(
            bgcolor=tokens.surface_card,
            border=ft.Border.all(tokens.border_width, tokens.border_default),
            border_radius=tokens.radius_medium,
        ),
    )
