from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from enum import StrEnum

import flet as ft

from overlord.ui.components.status import StatusBadgeSize, status_badge
from overlord.ui.design_system.icons import IconName, lucide_icon
from overlord.ui.design_system.tokens import ThemeTokens


@dataclass(frozen=True, slots=True)
class StageTimelineItem:
    title: str
    state: str
    state_label: str
    progress: float = 0.0


class ProjectActivityKind(StrEnum):
    REVIEW = "review"
    TASK = "task"
    EDIT = "edit"
    RELATION = "relation"
    CHECKPOINT = "checkpoint"


@dataclass(frozen=True, slots=True)
class ProjectActivityItem:
    message: str
    when: str
    kind: ProjectActivityKind


def _open_action(
    tokens: ThemeTokens,
    label: str,
    on_open: Callable[[object], None] | None,
    *,
    role: str,
) -> ft.Control | None:
    if on_open is None:
        return None
    return ft.IconButton(
        icon=lucide_icon(
            IconName.ARROW_UP_RIGHT,
            color=tokens.text_primary,
            size=tokens.icon_medium,
            label=label,
            show_tooltip=False,
        ),
        width=tokens.space_8,
        height=tokens.space_8,
        padding=tokens.space_0,
        tooltip=label,
        on_click=on_open,
        data={"role": role},
    )


def _overview_card(
    controls: Sequence[ft.Control],
    tokens: ThemeTokens,
    *,
    height: int,
    col: dict[str, int],
    role: str,
    filled: bool,
) -> ft.Container:
    return ft.Container(
        ft.Column(
            list(controls),
            spacing=tokens.space_3,
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
        ),
        height=height,
        bgcolor=tokens.surface_card,
        border=ft.Border.all(tokens.border_width, tokens.border_default),
        border_radius=tokens.radius_card,
        padding=tokens.space_5,
        col=col,
        data={"role": role, "filled": filled, "height": height},
    )


def project_summary_card(
    tokens: ThemeTokens,
    *,
    role: str,
    label: str,
    title: str,
    icon: IconName,
    icon_color: str,
    icon_background: str | None,
    metadata: Sequence[ft.Control] = (),
    on_open: Callable[[object], None] | None = None,
    open_label: str,
    strong_label: bool = False,
    filled: bool,
) -> ft.Container:
    icon_control = lucide_icon(
        icon,
        color=icon_color,
        size=tokens.icon_medium,
        label=label,
        show_tooltip=False,
    )
    if icon_background is not None:
        leading: ft.Control = ft.Container(
            icon_control,
            width=48,
            height=48,
            bgcolor=icon_background,
            border_radius=tokens.radius_pill,
            alignment=ft.Alignment.CENTER,
        )
    else:
        leading = ft.Container(icon_control, width=28, height=28, alignment=ft.Alignment.CENTER)
    action = _open_action(tokens, open_label, on_open, role=f"{role}-open")
    heading = ft.Column(
        [
            ft.Text(
                label,
                color=tokens.text_primary if strong_label else tokens.text_muted,
                size=tokens.text_emphasis if strong_label else tokens.text_small,
                weight=ft.FontWeight.W_600 if strong_label else ft.FontWeight.W_400,
            ),
            ft.Text(
                title,
                color=tokens.text_primary,
                size=tokens.text_emphasis,
                weight=ft.FontWeight.W_600,
                max_lines=2,
                overflow=ft.TextOverflow.ELLIPSIS,
            ),
        ],
        spacing=tokens.space_1,
        expand=True,
    )
    top_controls: list[ft.Control] = [leading, heading]
    if action is not None:
        top_controls.append(action)
    controls: list[ft.Control] = [
        ft.Row(
            top_controls,
            spacing=tokens.space_3,
            vertical_alignment=ft.CrossAxisAlignment.START,
        )
    ]
    if metadata:
        controls.extend(
            [
                ft.Container(expand=True),
                ft.Row(
                    list(metadata),
                    spacing=tokens.space_3,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    data={"role": f"{role}-metadata"},
                ),
            ]
        )
    return _overview_card(
        controls,
        tokens,
        height=150,
        col={"sm": 12, "lg": 4},
        role=role,
        filled=filled,
    )


def _stage_node(item: StageTimelineItem, tokens: ThemeTokens) -> ft.Container:
    if item.state == "completed":
        return ft.Container(
            lucide_icon(
                IconName.CHECK,
                color=tokens.on_accent,
                size=tokens.icon_medium,
                label=item.state_label,
                show_tooltip=False,
            ),
            width=40,
            height=40,
            bgcolor=tokens.success.main,
            border_radius=tokens.radius_pill,
            alignment=ft.Alignment.CENTER,
        )
    if item.state == "current":
        return ft.Container(
            ft.Container(
                width=20,
                height=20,
                bgcolor=tokens.blocker.main,
                border_radius=tokens.radius_pill,
            ),
            width=40,
            height=40,
            bgcolor=tokens.surface_card,
            border=ft.Border.all(tokens.space_1, tokens.blocker.main),
            border_radius=tokens.radius_pill,
            alignment=ft.Alignment.CENTER,
        )
    return ft.Container(
        width=40,
        height=40,
        bgcolor=tokens.surface_card,
        border=ft.Border.all(tokens.focus_width, tokens.border_strong),
        border_radius=tokens.radius_pill,
    )


def stage_progress_timeline(
    items: Sequence[StageTimelineItem],
    tokens: ThemeTokens,
) -> ft.Control:
    expanded = len(items) <= 5
    steps: list[ft.Control] = []
    for index, item in enumerate(items):
        previous = items[index - 1] if index else None
        left_color = (
            ft.Colors.TRANSPARENT
            if previous is None
            else tokens.success.main
            if previous.state == "completed"
            else tokens.blocker.main
            if previous.state == "current"
            else tokens.border_strong
        )
        right_color = (
            ft.Colors.TRANSPARENT
            if index == len(items) - 1
            else tokens.success.main
            if item.state == "completed"
            else tokens.blocker.main
            if item.state == "current"
            else tokens.border_strong
        )
        state_color = (
            tokens.success.text
            if item.state == "completed"
            else tokens.blocker.main
            if item.state == "current"
            else tokens.text_muted
        )
        step = ft.Container(
            ft.Column(
                [
                    ft.Row(
                        [
                            ft.Container(height=2, bgcolor=left_color, expand=True),
                            _stage_node(item, tokens),
                            ft.Container(height=2, bgcolor=right_color, expand=True),
                        ],
                        spacing=tokens.space_0,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    ft.Text(
                        item.title,
                        color=tokens.text_primary,
                        size=tokens.text_body,
                        text_align=ft.TextAlign.CENTER,
                        max_lines=2,
                        overflow=ft.TextOverflow.ELLIPSIS,
                    ),
                    ft.Text(
                        item.state_label,
                        color=state_color,
                        size=tokens.text_body,
                        text_align=ft.TextAlign.CENTER,
                        max_lines=1,
                    ),
                ],
                spacing=tokens.space_1,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            width=None if expanded else 168,
            expand=expanded,
            data={
                "role": "project-stage-timeline-step",
                "index": index,
                "state": item.state,
                "progress": item.progress,
            },
        )
        steps.append(step)
    return ft.Row(
        steps,
        spacing=tokens.space_0,
        scroll=ft.ScrollMode.AUTO if not expanded else None,
        data={
            "role": "project-stage-timeline",
            "stage_count": len(items),
            "scrollable": not expanded,
        },
    )


def project_plan_progress(
    tokens: ThemeTokens,
    *,
    title: str,
    empty_message: str,
    plan_title: str | None,
    stages: Sequence[StageTimelineItem],
    completed_count: int,
    current_stage_title: str | None,
    current_stage_progress: float | None,
    overall_progress: float,
    stages_total_label: str,
    stages_completed_label: str,
    current_stage_label: str,
    overall_progress_label: str,
    on_open: Callable[[object], None] | None,
    open_label: str,
) -> ft.Container:
    action = _open_action(tokens, open_label, on_open if plan_title else None, role="project-plan-progress-open")
    header_controls: list[ft.Control] = [
        ft.Text(title, color=tokens.text_primary, size=tokens.text_emphasis, weight=ft.FontWeight.W_600, expand=True)
    ]
    if action is not None:
        header_controls.append(action)
    controls: list[ft.Control] = [ft.Row(header_controls, vertical_alignment=ft.CrossAxisAlignment.CENTER)]
    if plan_title is None:
        controls.append(ft.Text(empty_message, color=tokens.text_secondary, size=tokens.text_body))
        return _overview_card(
            controls,
            tokens,
            height=386,
            col={"sm": 12, "lg": 8},
            role="project-plan-progress",
            filled=False,
        )
    normalized_overall = max(0.0, min(1.0, overall_progress))
    overall_percentage = round(normalized_overall * 100)
    current_percentage = (
        round(max(0.0, min(1.0, current_stage_progress)) * 100)
        if current_stage_progress is not None
        else None
    )
    metrics = [
        (str(len(stages)), stages_total_label),
        (str(completed_count), stages_completed_label),
        (
            current_stage_title or "—",
            (
                f"{current_stage_label}   {current_percentage}%"
                if current_percentage is not None
                else current_stage_label
            ),
        ),
    ]
    metric_controls: list[ft.Control] = []
    for index, (value, label) in enumerate(metrics):
        metric_controls.append(
            ft.Container(
                ft.Column(
                    [
                        ft.Text(value, color=tokens.text_primary, size=tokens.text_emphasis, weight=ft.FontWeight.W_600),
                        ft.Text(label, color=tokens.text_muted, size=tokens.text_body),
                    ],
                    spacing=tokens.space_0,
                ),
                expand=True,
                data={
                    "role": "project-plan-metric",
                    "metric": ("total", "completed", "current")[index],
                    "progress": current_stage_progress if index == 2 else None,
                },
                border=ft.Border.only(
                    right=ft.BorderSide(tokens.border_width, tokens.border_default)
                    if index < len(metrics) - 1
                    else ft.BorderSide(0, ft.Colors.TRANSPARENT)
                ),
                padding=ft.Padding.only(right=tokens.space_4),
            )
        )
    controls.extend(
        [
            ft.Text(plan_title, color=tokens.text_primary, size=tokens.text_title, weight=ft.FontWeight.W_600),
            ft.Row(metric_controls, spacing=tokens.space_5),
            stage_progress_timeline(stages, tokens),
            ft.Container(expand=True),
            ft.Row(
                [
                    ft.Text(overall_progress_label, color=tokens.text_muted, size=tokens.text_body, expand=True),
                    ft.Text(f"{overall_percentage}%", color=tokens.text_muted, size=tokens.text_body),
                ]
            ),
            ft.ProgressBar(
                value=normalized_overall,
                color=tokens.blocker.main,
                bgcolor=tokens.border_default,
                border_radius=tokens.radius_pill,
                height=tokens.space_3,
                data={"role": "project-overall-plan-progress", "value": normalized_overall},
            ),
        ]
    )
    return _overview_card(
        controls,
        tokens,
        height=386,
        col={"sm": 12, "lg": 8},
        role="project-plan-progress",
        filled=True,
    )


def _activity_visual(kind: ProjectActivityKind, tokens: ThemeTokens) -> tuple[IconName, str, str]:
    return {
        ProjectActivityKind.REVIEW: (IconName.MESSAGE, tokens.blocker.main, tokens.blocker.background),
        ProjectActivityKind.TASK: (IconName.TASK_CHECK, tokens.warning.main, tokens.warning.background),
        ProjectActivityKind.EDIT: (IconName.EDIT, tokens.blocker.main, tokens.blocker.background),
        ProjectActivityKind.RELATION: (IconName.LINK, tokens.success.main, tokens.success.background),
        ProjectActivityKind.CHECKPOINT: (IconName.CALENDAR, tokens.accent_primary, tokens.soft_red_background),
    }[kind]


def recent_project_activity(
    events: Sequence[ProjectActivityItem],
    tokens: ThemeTokens,
    *,
    title: str,
    empty_message: str,
    on_open: Callable[[object], None] | None = None,
    open_label: str,
) -> ft.Container:
    action = _open_action(tokens, open_label, on_open, role="recent-project-activity-open")
    header_controls: list[ft.Control] = [
        ft.Text(title, color=tokens.text_primary, size=tokens.text_emphasis, weight=ft.FontWeight.W_600, expand=True)
    ]
    if action is not None:
        header_controls.append(action)
    controls: list[ft.Control] = [ft.Row(header_controls, vertical_alignment=ft.CrossAxisAlignment.CENTER)]
    if events:
        rows: list[ft.Control] = []
        for event in events:
            icon, color, background = _activity_visual(event.kind, tokens)
            rows.append(
                ft.Row(
                    [
                        ft.Container(
                            lucide_icon(icon, color=color, size=tokens.icon_medium, label=event.kind.value, show_tooltip=False),
                            width=40,
                            height=40,
                            bgcolor=background,
                            border_radius=tokens.radius_pill,
                            alignment=ft.Alignment.CENTER,
                        ),
                        ft.Text(event.message, color=tokens.text_secondary, size=tokens.text_body, expand=True, max_lines=2),
                        ft.Text(event.when, color=tokens.text_muted, size=tokens.text_body),
                    ],
                    spacing=tokens.space_3,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    data={"role": "project-activity-row", "kind": event.kind.value},
                )
            )
        controls.append(ft.ListView(rows, spacing=tokens.space_2, height=532, scroll=ft.ScrollMode.AUTO))
    else:
        controls.append(ft.Text(empty_message, color=tokens.text_secondary, size=tokens.text_body))
    return _overview_card(
        controls,
        tokens,
        height=630,
        col={"sm": 12, "lg": 4},
        role="recent-project-activity",
        filled=bool(events),
    )
