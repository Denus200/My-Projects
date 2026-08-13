from __future__ import annotations

from enum import StrEnum

import flet as ft


class IconName(StrEnum):
    DASHBOARD = "layout-dashboard"
    TASKS = "list-checks"
    PROJECTS = "folder-kanban"
    CYCLES = "repeat-2"
    SETTINGS = "settings"
    COLLAPSE = "panel-left-close"
    EXPAND = "panel-left-open"
    CHECK = "check"
    ALERT = "triangle-alert"
    CLOCK = "clock-3"
    PLUS = "plus"
    CIRCLE = "circle"
    GRIP_VERTICAL = "grip-vertical"
    CLOSE = "x"
    SEARCH = "search"
    CHEVRON = "chevron-right"
    TARGET = "target"
    BLOCKER = "octagon-alert"


def lucide_icon(
    name: IconName,
    *,
    color: str,
    size: int,
    label: str,
    disabled: bool = False,
    show_tooltip: bool = True,
) -> ft.Image:
    return ft.Image(
        src=f"icons/lucide/{name.value}.svg",
        width=size,
        height=size,
        color=color,
        color_blend_mode=ft.BlendMode.SRC_IN,
        semantics_label=label,
        tooltip=label if show_tooltip else None,
        opacity=0.45 if disabled else 1.0,
    )
