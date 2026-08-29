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
    MINUS = "minus"
    CIRCLE = "circle"
    GRIP_VERTICAL = "grip-vertical"
    CLOSE = "x"
    SEARCH = "search"
    CHEVRON = "chevron-right"
    ARROW_LEFT = "arrow-left"
    ARROW_UP_RIGHT = "arrow-up-right"
    TARGET = "target"
    BLOCKER = "octagon-alert"
    OVERVIEW = "layout-grid"
    PLAN = "folder-dot"
    NOTES = "file-text"
    ARCHIVE = "archive"
    MORE = "ellipsis"
    EDIT = "edit"
    CALENDAR = "calendar"
    ZAP = "zap"
    LINK = "link-2"
    MESSAGE = "message-circle"
    TASK_CHECK = "square-check-big"
    STAR = "star"
    TRASH = "trash-2"
    SUN = "sun"
    CLOUD_SUN = "cloud-sun"
    CLOUD_RAIN = "cloud-rain"
    CLOUD_LIGHTNING = "cloud-lightning"
    CLOUD = "cloud"
    SNOWFLAKE = "snowflake"


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
