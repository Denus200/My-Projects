from __future__ import annotations

from collections.abc import Callable
from typing import Any

import flet as ft

from overlord.ui.design_system.icons import IconName, lucide_icon
from overlord.ui.design_system.styles import (
    ButtonVariant,
    button_style,
    checkbox_defaults,
    chip_control_defaults,
    dropdown_defaults,
    field_defaults,
    selection_button_style,
    table_theme,
)
from overlord.ui.design_system.tokens import ThemeTokens


def button(
    content: str | ft.Control,
    tokens: ThemeTokens,
    *,
    variant: ButtonVariant = ButtonVariant.PRIMARY,
    motion_enabled: bool = True,
    compact: bool = False,
    **kwargs: Any,
) -> ft.Button:
    kwargs.setdefault("height", tokens.control_height_compact if compact else tokens.control_height)
    kwargs.setdefault("style", button_style(tokens, variant, motion_enabled=motion_enabled, compact=compact))
    return ft.Button(content, **kwargs)


def primary_button(content: str | ft.Control, tokens: ThemeTokens, **kwargs: Any) -> ft.Button:
    return button(content, tokens, variant=ButtonVariant.PRIMARY, **kwargs)


def secondary_button(content: str | ft.Control, tokens: ThemeTokens, **kwargs: Any) -> ft.Button:
    return button(content, tokens, variant=ButtonVariant.SECONDARY, **kwargs)


def tertiary_button(content: str | ft.Control, tokens: ThemeTokens, **kwargs: Any) -> ft.Button:
    return button(content, tokens, variant=ButtonVariant.TERTIARY, compact=True, **kwargs)


def danger_button(content: str | ft.Control, tokens: ThemeTokens, **kwargs: Any) -> ft.Button:
    return button(content, tokens, variant=ButtonVariant.DANGER, **kwargs)


def selection_button(
    content: str | ft.Control,
    tokens: ThemeTokens,
    *,
    selected: bool,
    motion_enabled: bool = True,
    **kwargs: Any,
) -> ft.Button:
    kwargs.setdefault("height", tokens.control_height)
    kwargs.setdefault("style", selection_button_style(tokens, selected=selected, motion_enabled=motion_enabled))
    return ft.Button(content, **kwargs)


def text_field(tokens: ThemeTokens, *, compact: bool = False, **kwargs: Any) -> ft.TextField:
    defaults = field_defaults(tokens, compact=compact)
    defaults.update(kwargs)
    return ft.TextField(**defaults)


def search_field(tokens: ThemeTokens, *, label: str, **kwargs: Any) -> ft.TextField:
    kwargs.setdefault(
        "icon",
        lucide_icon(IconName.SEARCH, color=tokens.text_secondary, size=tokens.icon_small, label=label),
    )
    return text_field(tokens, label=label, **kwargs)


def select_field(
    tokens: ThemeTokens,
    *,
    compact: bool = False,
    searchable: bool = False,
    **kwargs: Any,
) -> ft.Dropdown:
    defaults = dropdown_defaults(tokens, compact=compact)
    defaults["enable_search"] = searchable
    defaults.update(kwargs)
    return ft.Dropdown(**defaults)


def checkbox(tokens: ThemeTokens, **kwargs: Any) -> ft.Checkbox:
    defaults = checkbox_defaults(tokens)
    defaults.update(kwargs)
    if isinstance(defaults.get("label"), str):
        defaults.setdefault("semantics_label", defaults["label"])
    return ft.Checkbox(**defaults)


def choice_chip(
    label: str,
    tokens: ThemeTokens,
    *,
    selected: bool = False,
    on_select: Callable[[object], None] | None = None,
    disabled: bool = False,
    motion_enabled: bool = True,
    **kwargs: Any,
) -> ft.Chip:
    defaults = chip_control_defaults(tokens, motion_enabled=motion_enabled)
    defaults.update(kwargs)
    return ft.Chip(
        label,
        selected=selected,
        on_select=on_select,
        disabled=disabled,
        **defaults,
    )


def data_table(
    columns: list[ft.DataColumn],
    rows: list[ft.DataRow],
    tokens: ThemeTokens,
    **kwargs: Any,
) -> ft.DataTable:
    theme = table_theme(tokens)
    defaults = {
        "border": ft.Border.all(tokens.border_width, tokens.border_default),
        "border_radius": tokens.radius_medium,
        "horizontal_lines": ft.BorderSide(tokens.border_width, tokens.border_default),
        "column_spacing": theme.column_spacing,
        "data_row_color": theme.data_row_color,
        "data_row_min_height": theme.data_row_min_height,
        "data_row_max_height": theme.data_row_max_height,
        "data_text_style": theme.data_text_style,
        "divider_thickness": theme.divider_thickness or tokens.border_width,
        "heading_row_color": theme.heading_row_color,
        "heading_row_height": theme.heading_row_height,
        "heading_text_style": theme.heading_text_style,
        "horizontal_margin": theme.horizontal_margin,
        "bgcolor": tokens.surface_card,
    }
    defaults.update(kwargs)
    return ft.DataTable(columns=columns, rows=rows, **defaults)
