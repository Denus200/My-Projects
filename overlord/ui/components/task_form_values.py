from __future__ import annotations

from datetime import date, datetime, time
import re

import flet as ft

from overlord.modules.projects.domain import Project
from overlord.modules.validation import FieldValidationError
from overlord.ui.strings import ui_text


def strict_date_value(value: str, *, field: str = "date") -> date:
    try:
        return date.fromisoformat(value.strip())
    except ValueError as error:
        raise FieldValidationError(field, "date_format", ui_text("tasks.date_error")) from error


def time_value(value: str, *, field: str = "time") -> time:
    try:
        return time.fromisoformat(value.strip())
    except ValueError as error:
        raise FieldValidationError(field, "time_format", ui_text("tasks.time_error")) from error


def datetime_value(value: str, *, field: str = "deadline") -> datetime:
    try:
        return datetime.fromisoformat(value.strip().replace(" ", "T"))
    except ValueError as error:
        raise FieldValidationError(field, "datetime_format", ui_text("tasks.datetime_error")) from error


def display_date(value: date) -> str:
    return value.strftime("%d.%m.%Y")


def flexible_date_value(value: str, *, field: str = "date") -> date:
    clean = value.strip()
    digits = re.sub(r"\D", "", clean)
    try:
        if len(digits) == 8 and clean == digits:
            return date(int(digits[4:]), int(digits[2:4]), int(digits[:2]))
        for separator in (".", "/", "-"):
            parts = clean.split(separator)
            if len(parts) == 3 and len(parts[0]) <= 2:
                return date(int(parts[2]), int(parts[1]), int(parts[0]))
        return date.fromisoformat(clean)
    except (ValueError, TypeError) as error:
        raise FieldValidationError(field, "human_date_format", ui_text("tasks.human_date_error")) from error


def project_options(projects: tuple[Project, ...]) -> list[ft.DropdownOption]:
    return [
        ft.DropdownOption("none", ui_text("tasks.no_project")),
        *[ft.DropdownOption(str(item.id), item.title) for item in projects],
    ]


def project_id(value: str | None) -> int | None:
    return None if value in {None, "none"} else int(value)


def deadline_display(value: datetime | None) -> str:
    if value is None:
        return ""
    return value.strftime("%d.%m.%Y %H:%M")


def deadline_value(value: str, *, field: str = "deadline") -> datetime | None:
    clean = value.strip()
    if not clean:
        return None
    parts = clean.rsplit(" ", 1)
    selected_date = flexible_date_value(parts[0], field=field)
    selected_time = time_value(parts[1], field=field) if len(parts) == 2 else time.max
    return datetime.combine(selected_date, selected_time)


def duration_minutes_value(
    hours_value: str | None,
    minutes_value: str | None,
    *,
    field: str = "estimate",
    label: str | None = None,
) -> int | None:
    hours_raw = (hours_value or "").strip()
    minutes_raw = (minutes_value or "").strip()
    if not hours_raw and not minutes_raw:
        return None
    try:
        hours = int(hours_raw or "0")
        minutes = int(minutes_raw or "0")
    except ValueError as error:
        message = (
            ui_text("tasks.duration_nonnegative", field=label)
            if label
            else ui_text("tasks.estimate_nonnegative")
        )
        raise FieldValidationError(field, "integer", message) from error
    if hours < 0 or minutes < 0:
        message = (
            ui_text("tasks.duration_nonnegative", field=label)
            if label
            else ui_text("tasks.estimate_nonnegative")
        )
        raise FieldValidationError(field, "nonnegative", message)
    if minutes > 59:
        raise FieldValidationError(field, "minute_range", ui_text("tasks.estimate_minute_range"))
    total = hours * 60 + minutes
    if total <= 0:
        message = (
            ui_text("tasks.duration_positive", field=label)
            if label
            else "Estimate must be a positive number of minutes."
        )
        raise FieldValidationError(field, "positive", message)
    return total
