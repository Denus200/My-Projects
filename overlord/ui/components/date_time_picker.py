from __future__ import annotations

import calendar
import math
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime, time

import flet as ft

from overlord.ui.components.controls import primary_button, secondary_button, text_field
from overlord.ui.components.task_form_values import time_value
from overlord.ui.design_system.icons import IconName, lucide_icon
from overlord.ui.design_system.tokens import ThemeTokens
from overlord.ui.strings import (
    format_month_year,
    format_short_date,
    format_weekday_initial,
    format_weekday_name,
    ui_error,
    ui_text,
)


def _selected_date_label(value: date) -> str:
    return f"{format_weekday_name(value)[:3]},\n{format_short_date(value)}"


def _nav_button(icon: ft.Control, tokens: ThemeTokens, *, label: str, on_click) -> ft.IconButton:
    return ft.IconButton(
        icon=icon,
        width=40,
        height=40,
        on_click=on_click,
        tooltip=label,
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


@dataclass(slots=True)
class DatePickerState:
    selected: date
    visible_month: date
    selected_time: time | None = None


def build_date_time_picker_dialog(
    tokens: ThemeTokens,
    *,
    initial_date: date,
    include_time: bool,
    initial_time: time | None,
    first_day_of_week: int,
    on_apply: Callable[[date | datetime], None],
    close: Callable[[], None],
) -> ft.AlertDialog:
    """Build the shared Create Task calendar overlay.

    The date-only and date+time presentations intentionally share all calendar
    state and rendering. The optional time row is the sole mode difference.
    """

    state = DatePickerState(
        selected=initial_date,
        visible_month=initial_date.replace(day=1),
        selected_time=initial_time or (time(0, 0) if include_time else None),
    )
    selected_label = ft.Text(
        _selected_date_label(state.selected),
        color=tokens.text_primary,
        size=tokens.text_display,
        weight=ft.FontWeight.W_400,
    )
    month_label = ft.Text(
        format_month_year(state.visible_month),
        color=tokens.text_secondary,
        size=tokens.text_emphasis,
    )
    time_field = text_field(
        tokens,
        compact=True,
        value=state.selected_time.strftime("%H:%M") if state.selected_time else "00:00",
        hint_text="HH:MM",
        width=84,
        visible=include_time,
        border=ft.InputBorder.NONE,
        filled=False,
        data={"role": "date-picker-time"},
    )
    calendar_host = ft.Container(data={"role": "date-picker-calendar"})

    def update_selected(day: date) -> None:
        state.selected = day
        selected_label.value = _selected_date_label(day)
        selected_label.update()
        render_calendar(update=True)

    def day_control(day: date) -> ft.Control:
        in_month = day.month == state.visible_month.month
        selected = day == state.selected
        return ft.Container(
            ft.Text(
                str(day.day),
                color=tokens.on_accent if selected else (
                    tokens.text_primary if in_month else tokens.text_disabled
                ),
                size=tokens.text_body,
                text_align=ft.TextAlign.CENTER,
            ),
            width=36,
            height=36,
            alignment=ft.Alignment.CENTER,
            bgcolor=tokens.accent_primary if selected else None,
            border_radius=tokens.radius_pill,
            on_click=(lambda _event, value=day: update_selected(value)) if in_month else None,
            tooltip=ui_text("tasks.date_picker.choose_day", day=day.day),
            data={"role": "date-picker-day", "date": day.isoformat()},
        )

    def render_calendar(*, update: bool = False) -> None:
        calendar_model = calendar.Calendar(firstweekday=first_day_of_week)
        weeks = calendar_model.monthdatescalendar(
            state.visible_month.year,
            state.visible_month.month,
        )
        weekday_start = date(2026, 8, 3 if first_day_of_week == 0 else 2)
        headings = [
            ft.Container(
                ft.Text(
                    format_weekday_initial(weekday_start.fromordinal(weekday_start.toordinal() + offset)),
                    color=tokens.text_primary,
                    weight=ft.FontWeight.W_600,
                    text_align=ft.TextAlign.CENTER,
                ),
                width=36,
                height=28,
                alignment=ft.Alignment.CENTER,
            )
            for offset in range(7)
        ]
        calendar_host.content = ft.Column(
            [
                ft.Row(headings, spacing=tokens.space_2),
                *[
                    ft.Row([day_control(day) for day in week], spacing=tokens.space_2)
                    for week in weeks
                ],
            ],
            spacing=tokens.space_1,
            tight=True,
        )
        month_label.value = format_month_year(state.visible_month)
        if update:
            month_label.update()
            calendar_host.update()

    def move_month(offset: int) -> None:
        month_index = state.visible_month.year * 12 + state.visible_month.month - 1 + offset
        state.visible_month = date(month_index // 12, month_index % 12 + 1, 1)
        render_calendar(update=True)

    def apply(_event) -> None:
        if include_time:
            try:
                state.selected_time = time_value(time_field.value or "", field="deadline")
            except Exception as error:
                time_field.error = ui_error(error)
                time_field.update()
                return
            on_apply(datetime.combine(state.selected, state.selected_time))
        else:
            on_apply(state.selected)
        close()

    render_calendar()
    left_panel = ft.Container(
        ft.Column(
            [
                ft.Text(ui_text("tasks.choose_date"), color=tokens.text_secondary),
                selected_label,
                ft.Row(
                    [
                        lucide_icon(
                            IconName.CLOCK,
                            color=tokens.text_secondary,
                            size=tokens.icon_medium,
                            label=ui_text("tasks.deadline_time"),
                            show_tooltip=False,
                        ),
                        time_field,
                    ],
                    spacing=tokens.space_2,
                    visible=include_time,
                ),
            ],
            spacing=tokens.space_4,
        ),
        width=126,
        padding=ft.Padding.only(top=tokens.space_2, right=tokens.space_4),
    )
    previous_icon = lucide_icon(
        IconName.CHEVRON,
        color=tokens.text_secondary,
        size=tokens.icon_medium,
        label=ui_text("tasks.previous"),
        show_tooltip=False,
    )
    previous_icon.rotate = math.pi
    content = ft.Row(
        [
            left_panel,
            ft.VerticalDivider(width=1, color=tokens.border_default),
            ft.Container(
                ft.Column(
                    [
                        ft.Row(
                            [
                                month_label,
                                ft.Container(expand=True),
                                _nav_button(
                                    previous_icon,
                                    tokens,
                                    on_click=lambda _event: move_month(-1),
                                    label=ui_text("tasks.previous"),
                                ),
                                _nav_button(
                                    lucide_icon(
                                        IconName.CHEVRON,
                                        color=tokens.text_secondary,
                                        size=tokens.icon_medium,
                                        label=ui_text("tasks.next"),
                                        show_tooltip=False,
                                    ),
                                    tokens,
                                    on_click=lambda _event: move_month(1),
                                    label=ui_text("tasks.next"),
                                ),
                            ],
                            spacing=tokens.space_1,
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                        calendar_host,
                    ],
                    spacing=tokens.space_2,
                    tight=True,
                ),
                width=322,
                padding=ft.Padding.only(left=tokens.space_4),
            ),
        ],
        spacing=tokens.space_4,
        vertical_alignment=ft.CrossAxisAlignment.STRETCH,
        tight=True,
    )
    return ft.AlertDialog(
        modal=True,
        content=ft.Container(content, width=486, height=334),
        actions=[
            primary_button(ui_text("tasks.create_save"), tokens, on_click=apply, width=120),
            secondary_button(ui_text("tasks.cancel"), tokens, on_click=lambda _event: close(), width=84),
        ],
        actions_alignment=ft.MainAxisAlignment.END,
        bgcolor=tokens.surface_elevated,
        shape=ft.RoundedRectangleBorder(radius=tokens.radius_large),
        data={
            "role": "date-time-picker" if include_time else "date-picker",
            "state": state,
        },
    )
