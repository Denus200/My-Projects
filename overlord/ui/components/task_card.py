from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import date
from enum import StrEnum

import flet as ft

from overlord.app.read_models import TaskListItem
from overlord.modules.tasks.domain import TaskLifecycle
from overlord.ui.design_system.icons import IconName, lucide_icon
from overlord.ui.design_system.tokens import ThemeTokens
from overlord.ui.strings import format_dashboard_date, ui_text


class TaskCardVariant(StrEnum):
    FULL = "full"
    COMPACT = "compact"


class TaskMetaChipVariant(StrEnum):
    TIME = "time"
    DATE = "date"
    DEADLINE = "deadline"
    CYCLE = "cycle"


@dataclass(frozen=True, slots=True)
class TaskMetaChipData:
    label: str
    variant: TaskMetaChipVariant


def task_meta_chips_for_item(
    item: TaskListItem,
    *,
    displayed_day: date | None = None,
) -> tuple[TaskMetaChipData, ...]:
    """Project only Task data into the chip styles present in the supplied reference."""
    task = item.task
    chips: list[TaskMetaChipData] = []
    if task.schedule_start_time is not None:
        start = task.schedule_start_time.strftime("%H:%M")
        if task.schedule_end_time is not None:
            label = ui_text(
                "task_card.time_range",
                start=start,
                end=task.schedule_end_time.strftime("%H:%M"),
            )
        else:
            label = start
        chips.append(TaskMetaChipData(label, TaskMetaChipVariant.TIME))
    if task.deadline_at is not None:
        comparison_day = displayed_day or date.today()
        variant = (
            TaskMetaChipVariant.DEADLINE
            if task.deadline_at.date() < comparison_day
            and task.lifecycle_status is not TaskLifecycle.COMPLETED
            else TaskMetaChipVariant.DATE
        )
        chips.append(
            TaskMetaChipData(
                format_dashboard_date(task.deadline_at.date()),
                variant,
            )
        )
    chips.extend(
        TaskMetaChipData(title, TaskMetaChipVariant.CYCLE)
        for title in item.cycle_titles
        if title.strip()
    )
    return tuple(chips)


def task_meta_chip(data: TaskMetaChipData, tokens: ThemeTokens) -> ft.Container:
    icon: ft.Control | None = None
    background: str | None
    foreground: str
    if data.variant is TaskMetaChipVariant.TIME:
        background = None
        foreground = tokens.text_primary
        icon = lucide_icon(
            IconName.CLOCK,
            color=foreground,
            size=14,
            label=data.label,
            show_tooltip=False,
        )
    elif data.variant is TaskMetaChipVariant.DATE:
        background = tokens.task_meta_date_background
        foreground = tokens.task_meta_date_text
        icon = lucide_icon(
            IconName.CLOCK,
            color=foreground,
            size=14,
            label=data.label,
            show_tooltip=False,
        )
    elif data.variant is TaskMetaChipVariant.DEADLINE:
        background = tokens.task_meta_deadline_background
        foreground = tokens.task_meta_deadline_text
        icon = lucide_icon(
            IconName.CLOCK,
            color=foreground,
            size=14,
            label=data.label,
            show_tooltip=False,
        )
    else:
        background = tokens.task_meta_cycle_background
        foreground = tokens.task_meta_cycle_text

    controls: list[ft.Control] = []
    if icon is not None:
        controls.append(icon)
    controls.append(
        ft.Text(
            data.label,
            color=foreground,
            size=tokens.text_small,
            max_lines=1,
            overflow=ft.TextOverflow.ELLIPSIS,
        )
    )
    return ft.Container(
        ft.Row(
            controls,
            spacing=tokens.space_1,
            tight=True,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        height=24,
        bgcolor=background,
        border_radius=tokens.space_1,
        padding=(
            ft.Padding.symmetric(horizontal=tokens.space_2)
            if background is not None
            else ft.Padding.all(tokens.space_0)
        ),
        data={"role": "task-meta-chip", "variant": data.variant.value},
    )


def _project_indicators(
    colors: Sequence[str],
    tokens: ThemeTokens,
    *,
    compact: bool,
    muted: bool,
) -> ft.Control | None:
    visible_colors = tuple(color for color in colors if color)[:4]
    if not visible_colors:
        return None
    indicators = [
        ft.Container(
            width=12 if compact else 40,
            height=12 if compact else 8,
            bgcolor=color,
            border_radius=tokens.radius_pill,
            opacity=0.45 if muted else 1.0,
            data={"role": "project-indicator", "color": color},
        )
        for color in visible_colors
    ]
    return ft.Row(
        indicators,
        spacing=tokens.space_1 if compact else tokens.space_2,
        tight=True,
        data={"role": "project-indicators", "count": len(indicators)},
    )


def task_card(
    item: TaskListItem,
    tokens: ThemeTokens,
    *,
    variant: TaskCardVariant = TaskCardVariant.FULL,
    project_colors: Sequence[str] = (),
    meta_chips: Sequence[TaskMetaChipData] | None = None,
    muted: bool = False,
    on_complete: Callable[[object], None] | None = None,
    on_open: Callable[[object], None] | None = None,
    allow_reopen: bool = False,
    trailing: ft.Control | None = None,
    role: str = "workspace-task-card",
) -> ft.Container:
    """Build one data-driven Task Card across full and dense task contexts."""
    task = item.task
    compact = variant is TaskCardVariant.COMPACT
    completed = task.lifecycle_status is TaskLifecycle.COMPLETED
    resolved_meta = tuple(
        task_meta_chips_for_item(item) if meta_chips is None else meta_chips
    )
    indicators = _project_indicators(
        project_colors,
        tokens,
        compact=compact,
        muted=muted,
    )

    title = ft.Text(
        task.title,
        color=tokens.task_card_completed_text if completed else tokens.text_primary,
        size=tokens.text_small if compact else tokens.text_emphasis,
        max_lines=1 if compact else 3,
        overflow=ft.TextOverflow.ELLIPSIS,
        style=ft.TextStyle(
            decoration=(
                ft.TextDecoration.LINE_THROUGH
                if completed
                else ft.TextDecoration.NONE
            ),
            height=1.2,
        ),
    )
    title_target = ft.GestureDetector(
        title,
        on_tap=on_open,
        mouse_cursor=ft.MouseCursor.CLICK if on_open else ft.MouseCursor.BASIC,
        expand=True,
        opacity=0.42 if muted else 1.0,
        data={"role": "task-body", "task_id": task.id},
    )

    completion_label = ui_text("dashboard.toggle_task", name=task.title)
    completion_surface = ft.Container(
        lucide_icon(
            IconName.CHECK,
            color=tokens.dashboard_completion_check,
            size=16 if compact else 18,
            label=completion_label,
            show_tooltip=False,
        )
        if completed
        else None,
        width=16 if compact else 22,
        height=16 if compact else 22,
        alignment=ft.Alignment.CENTER,
        bgcolor=tokens.dashboard_completion_fill if completed else None,
        border=ft.Border.all(
            tokens.border_width,
            (
                tokens.dashboard_completion_fill_border
                if completed
                else tokens.dashboard_completion_border
            ),
        ),
        border_radius=tokens.radius_pill,
        data={"role": "completion-surface", "task_id": task.id},
    )
    completion_action = on_complete if not completed or allow_reopen else None
    completion_target = ft.GestureDetector(
        completion_surface,
        mouse_cursor=(
            ft.MouseCursor.CLICK if completion_action else ft.MouseCursor.BASIC
        ),
        on_tap=completion_action,
        data={"role": "completion", "task_id": task.id},
    )
    completion = ft.Semantics(
        content=completion_target,
        label=completion_label,
        button=completion_action is not None,
        checked=completed,
    )

    title_row_controls: list[ft.Control] = []
    if completed or (compact and on_complete is not None):
        title_row_controls.append(completion)
    title_row_controls.append(title_target)
    if compact and indicators is not None:
        title_row_controls.append(indicators)
    if trailing is not None:
        title_row_controls.append(trailing)
    title_row = ft.Row(
        title_row_controls,
        spacing=tokens.space_2,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
    )

    content_controls: list[ft.Control] = []
    if not compact and indicators is not None:
        content_controls.append(indicators)
    content_controls.append(title_row)
    if not compact and resolved_meta:
        content_controls.append(
            ft.Row(
                [task_meta_chip(chip, tokens) for chip in resolved_meta],
                spacing=tokens.space_2,
                run_spacing=tokens.space_1,
                wrap=True,
                data={"role": "task-meta-row", "count": len(resolved_meta)},
            )
        )

    surface = ft.Container(
        ft.Column(
            content_controls,
            spacing=tokens.space_2,
            tight=True,
        ),
        bgcolor=tokens.task_card_background,
        border=ft.Border.all(tokens.border_width, tokens.task_card_border),
        border_radius=tokens.task_card_radius,
        padding=(
            ft.Padding.symmetric(
                horizontal=tokens.space_2,
                vertical=tokens.space_2 if completed else 6,
            )
            if compact
            else ft.Padding.symmetric(
                horizontal=tokens.space_4,
                vertical=tokens.space_3,
            )
        ),
        animate=ft.Animation(tokens.motion_fast, ft.AnimationCurve.EASE_OUT_CUBIC),
        data={
            "role": role,
            "task_id": task.id,
            "variant": variant.value,
            "completed": completed,
            "project_indicator_count": min(4, len(tuple(project_colors))),
            "meta_chip_count": len(resolved_meta),
        },
    )

    def hover(event: object) -> None:
        hovering = str(getattr(event, "data", "")).lower() == "true"
        surface.border = ft.Border.all(
            tokens.border_width,
            tokens.task_card_hover_border if hovering else tokens.task_card_border,
        )
        if not completed and on_complete is not None:
            if hovering and completion not in title_row.controls:
                title_row.controls.insert(0, completion)
            elif not hovering and completion in title_row.controls:
                title_row.controls.remove(completion)

    if not compact:
        surface.on_hover = hover
    return surface
