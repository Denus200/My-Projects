from __future__ import annotations

from dataclasses import dataclass

import flet as ft

from overlord.modules.projects.domain import ProjectStage, ProjectStageStatus
from overlord.ui.components.controls import text_field
from overlord.ui.design_system.tokens import ThemeTokens
from overlord.ui.strings import ui_text


@dataclass(frozen=True, slots=True)
class TaskDurationControl:
    control: ft.Container
    hours: ft.TextField
    minutes: ft.TextField


def delayed_tooltip(message: str) -> ft.Tooltip:
    return ft.Tooltip(message=message, wait_duration=600)


def task_duration_control(
    tokens: ThemeTokens,
    *,
    hours_value: str = "",
    minutes_value: str = "",
    hint_text: str = "0",
    label: str | None = None,
    role_prefix: str = "estimate",
    control_role: str = "estimated-time",
    disabled: bool = False,
    read_only: bool = False,
) -> TaskDurationControl:
    """Build the shared nullable hours/minutes input used by Task forms."""

    hours = text_field(
        tokens,
        compact=True,
        value=hours_value,
        hint_text=hint_text,
        keyboard_type=ft.KeyboardType.NUMBER,
        text_align=ft.TextAlign.RIGHT,
        width=64,
        disabled=disabled,
        read_only=read_only,
        tooltip=delayed_tooltip(ui_text("tasks.estimate_hours")),
        data={"role": f"{role_prefix}-hours"},
    )
    minutes = text_field(
        tokens,
        compact=True,
        value=minutes_value,
        hint_text=hint_text,
        keyboard_type=ft.KeyboardType.NUMBER,
        text_align=ft.TextAlign.RIGHT,
        width=52,
        disabled=disabled,
        read_only=read_only,
        tooltip=delayed_tooltip(ui_text("tasks.estimate_minutes")),
        data={"role": f"{role_prefix}-minutes"},
    )
    hour_suffix = ft.Container(
        ft.Text(
            ui_text("tasks.estimate_hour_suffix"),
            color=tokens.text_secondary,
            no_wrap=True,
        ),
        width=16,
    )
    minute_suffix = ft.Container(
        ft.Text(
            ui_text("tasks.estimate_minute_suffix"),
            color=tokens.text_secondary,
            no_wrap=True,
        ),
        width=32,
    )
    control = ft.Container(
        ft.Row(
            [hours, hour_suffix, minutes, minute_suffix],
            spacing=tokens.space_1,
            tight=True,
        ),
        border=ft.Border.all(tokens.border_width, tokens.border_default),
        border_radius=tokens.radius_medium,
        bgcolor=(
            tokens.control_background_disabled
            if disabled or read_only
            else tokens.control_background
        ),
        padding=ft.Padding.symmetric(horizontal=tokens.space_1, vertical=tokens.space_1),
        tooltip=delayed_tooltip(label or ui_text("tasks.estimated_time")),
        width=186,
        data={"role": control_role, "read_only": read_only},
    )
    return TaskDurationControl(control, hours, minutes)


def task_form_icon_button(
    icon: ft.Control,
    tokens: ThemeTokens,
    *,
    label: str,
    on_click,
) -> ft.IconButton:
    return ft.IconButton(
        icon=icon,
        width=40,
        height=40,
        on_click=on_click,
        tooltip=delayed_tooltip(label),
        bgcolor=ft.Colors.TRANSPARENT,
        hover_color=tokens.interactive_hover,
        focus_color=ft.Colors.TRANSPARENT,
        highlight_color=tokens.interactive_pressed,
        style=ft.ButtonStyle(
            side={
                ft.ControlState.FOCUSED: ft.BorderSide(tokens.focus_width, tokens.focus_ring),
                ft.ControlState.DEFAULT: ft.BorderSide(tokens.border_width, ft.Colors.TRANSPARENT),
            },
            padding=0,
            shape=ft.RoundedRectangleBorder(radius=tokens.radius_small),
        ),
    )


def project_count_label(count: int) -> str:
    return ui_text(
        "tasks.projects_count.one" if count == 1 else "tasks.projects_count.other",
        count=count,
    )


def project_stage_label(stage: ProjectStage) -> str:
    if stage.status is ProjectStageStatus.IN_PROGRESS:
        return f"Current — {stage.title}"
    return stage.title
