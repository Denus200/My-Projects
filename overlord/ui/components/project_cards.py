from __future__ import annotations

from collections.abc import Callable

import flet as ft
import flet.canvas as cv

from overlord.modules.projects.domain import ProjectStatus
from overlord.modules.projects.read_models import ProjectDetail
from overlord.ui.components.status import status_badge
from overlord.ui.design_system.icons import IconName, lucide_icon
from overlord.ui.design_system.tokens import (
    PROJECT_CARD_ACTION_BACKGROUND,
    PROJECT_CARD_EMPTY_BACKGROUND,
    PROJECT_CARD_EMPTY_DASH,
    PROJECT_CARD_EMPTY_ICON,
    PROJECT_METRIC_BACKGROUND,
    PROJECT_METRIC_BORDER,
    ThemeTokens,
)
from overlord.ui.strings import format_short_date, ui_text


PROJECT_CARD_EXPANDED_WIDTH = 401
PROJECT_CARD_COLLAPSED_WIDTH = 354
PROJECT_CARD_HEIGHT = 211
PROJECT_CARD_NOTCH_WIDTH = 66
PROJECT_CARD_ADD_SIZE = 42


def darken_color(color: str, amount: float = 0.10) -> str:
    """Darken a six-digit hex color by a reusable proportional amount."""
    value = color.removeprefix("#")
    if len(value) != 6:
        return color
    factor = max(0.0, min(1.0, 1.0 - amount))
    channels = [round(int(value[index:index + 2], 16) * factor) for index in (0, 2, 4)]
    return "#" + "".join(f"{channel:02X}" for channel in channels)


def _card_path(width: int) -> list[cv.Path.PathElement]:
    shoulder = width - PROJECT_CARD_NOTCH_WIDTH
    return [
        cv.Path.MoveTo(shoulder, 0),
        cv.Path.CubicTo(shoulder + 8.837, 0, shoulder + 16, 7.1634, shoulder + 16, 16),
        cv.Path.LineTo(shoulder + 16, 34),
        cv.Path.CubicTo(shoulder + 16, 42.8366, shoulder + 23.163, 50, shoulder + 32, 50),
        cv.Path.LineTo(width - 16, 50),
        cv.Path.CubicTo(width - 7.163, 50, width, 57.1634, width, 66),
        cv.Path.LineTo(width, PROJECT_CARD_HEIGHT - 16),
        cv.Path.CubicTo(width, PROJECT_CARD_HEIGHT - 7.163, width - 7.163, PROJECT_CARD_HEIGHT, width - 16, PROJECT_CARD_HEIGHT),
        cv.Path.LineTo(16, PROJECT_CARD_HEIGHT),
        cv.Path.CubicTo(7.1634, PROJECT_CARD_HEIGHT, 0, PROJECT_CARD_HEIGHT - 7.163, 0, PROJECT_CARD_HEIGHT - 16),
        cv.Path.LineTo(0, 16),
        cv.Path.CubicTo(0, 7.1634, 7.1634, 0, 16, 0),
        cv.Path.Close(),
    ]


class ProjectCardShell:
    """Exact responsive Project Card outline backed by a native Flet canvas path."""

    def __init__(self, width: int, color: str, tokens: ThemeTokens, *, interactive: bool = True) -> None:
        self.width = width
        self.color = color
        self.hover_color = darken_color(color)
        self.tokens = tokens
        self.fill = ft.Paint(color=color, style=ft.PaintingStyle.FILL)
        self.stroke = ft.Paint(
            color=tokens.border_default,
            style=ft.PaintingStyle.STROKE,
            stroke_width=tokens.border_width,
        )
        path = _card_path(width)
        self.canvas = cv.Canvas(
            [cv.Path(path, paint=self.fill), cv.Path(path, paint=self.stroke)],
            width=width,
            height=PROJECT_CARD_HEIGHT,
            data={"role": "project-card-shell-canvas"},
        )
        self.control = ft.GestureDetector(
            self.canvas,
            width=width,
            height=PROJECT_CARD_HEIGHT,
            mouse_cursor=ft.MouseCursor.CLICK if interactive else ft.MouseCursor.BASIC,
            on_enter=self._hover if interactive else None,
            on_exit=self._hover if interactive else None,
            data={
                "role": "project-card-shell",
                "width_state": "collapsed" if width == PROJECT_CARD_COLLAPSED_WIDTH else "expanded",
                "width": width,
                "height": PROJECT_CARD_HEIGHT,
                "notch_width": PROJECT_CARD_NOTCH_WIDTH,
            },
        )

    def _hover(self, event: object) -> None:
        hovered = str(getattr(event, "data", "")).lower() == "true"
        self.fill.color = self.hover_color if hovered else self.color
        try:
            self.canvas.update()
        except RuntimeError as error:
            if "Control must be added to the page first" not in str(error):
                raise


def project_metric_chip(text: str, tokens: ThemeTokens) -> ft.Container:
    return ft.Container(
        ft.Text(text, size=tokens.text_small, color=tokens.text_secondary, max_lines=1),
        height=26,
        bgcolor=PROJECT_METRIC_BACKGROUND,
        border=ft.Border.all(tokens.border_width, PROJECT_METRIC_BORDER),
        border_radius=tokens.space_2,
        padding=ft.Padding.symmetric(horizontal=tokens.space_3),
        alignment=ft.Alignment.CENTER,
        data={"role": "project-metric-chip", "overlay_opacity": 0.04, "border_opacity": 0.16},
    )


def _project_badge(detail: ProjectDetail, tokens: ThemeTokens) -> ft.Control:
    project = detail.project
    style = {
        ProjectStatus.ACTIVE: "active",
        ProjectStatus.ON_HOLD: "paused",
        ProjectStatus.COMPLETED: "completed",
        ProjectStatus.ARCHIVED: "archived",
    }[project.status]
    return status_badge(style, ui_text(f"projects.status.{project.status.value}"), tokens)


def project_card(
    detail: ProjectDetail,
    tokens: ThemeTokens,
    *,
    width: int,
    on_open: Callable[[object], None],
    on_add_task: Callable[[object], None],
) -> ft.Container:
    project = detail.project
    shell = ProjectCardShell(width, project.color, tokens)
    metrics = ft.Row(
        [
            project_metric_chip(ui_text("projects.card_open", count=detail.open_task_count), tokens),
            project_metric_chip(ui_text("projects.card_progress", count=detail.in_progress_task_count), tokens),
            project_metric_chip(ui_text("projects.card_blocked", count=detail.open_blocker_count), tokens),
        ],
        spacing=tokens.space_2,
        tight=True,
    )
    add_surface = ft.Container(
        lucide_icon(IconName.PLUS, color=tokens.text_primary, size=tokens.icon_medium, label=ui_text("projects.add_task")),
        width=PROJECT_CARD_ADD_SIZE,
        height=PROJECT_CARD_ADD_SIZE,
        bgcolor=PROJECT_CARD_ACTION_BACKGROUND,
        border=ft.Border.all(tokens.border_width, tokens.border_default),
        border_radius=PROJECT_CARD_ADD_SIZE / 2,
        alignment=ft.Alignment.CENTER,
        data={"role": "project-add-task-surface", "project_id": project.id},
    )
    add_action = ft.GestureDetector(
        add_surface,
        width=PROJECT_CARD_ADD_SIZE,
        height=PROJECT_CARD_ADD_SIZE,
        mouse_cursor=ft.MouseCursor.CLICK,
        tooltip=ui_text("projects.add_task"),
        on_tap=on_add_task,
        data={"role": "project-add-task", "project_id": project.id},
    )
    content_width = width - (tokens.space_3 * 2)
    body_content = ft.Stack(
        [
            shell.canvas,
            ft.Container(_project_badge(detail, tokens), left=tokens.space_3, top=tokens.space_2),
            ft.Container(
                ft.Text(
                    project.title,
                    color=tokens.text_primary,
                    size=tokens.text_title,
                    weight=ft.FontWeight.W_600,
                    max_lines=1,
                    overflow=ft.TextOverflow.ELLIPSIS,
                ),
                left=tokens.space_3,
                top=61,
                width=content_width,
            ),
            ft.Container(
                ft.Text(
                    project.description or ui_text("projects.card_no_description"),
                    color=tokens.text_secondary,
                    size=tokens.text_emphasis,
                    max_lines=2,
                    overflow=ft.TextOverflow.ELLIPSIS,
                    style=ft.TextStyle(height=1.35),
                ),
                left=tokens.space_3,
                top=91,
                width=content_width,
            ),
            ft.Container(metrics, left=tokens.space_3, top=150),
            ft.Container(
                ft.Text(
                    ui_text("projects.last_activity", date=format_short_date(project.updated_at.date())),
                    color=tokens.text_muted,
                    size=tokens.text_small,
                ),
                left=tokens.space_3,
                top=187,
            ),
        ],
        width=width,
        height=PROJECT_CARD_HEIGHT,
        clip_behavior=ft.ClipBehavior.NONE,
    )
    body = ft.GestureDetector(
        body_content,
        width=width,
        height=PROJECT_CARD_HEIGHT,
        mouse_cursor=ft.MouseCursor.CLICK,
        on_tap=on_open,
        on_enter=shell._hover,
        on_exit=shell._hover,
        data={"role": "project-card-body", "project_id": project.id},
    )
    return ft.Container(
        ft.Stack(
            [
                body,
                ft.Container(add_action, right=0, top=0),
            ],
            width=width,
            height=PROJECT_CARD_HEIGHT,
            clip_behavior=ft.ClipBehavior.NONE,
        ),
        width=width,
        height=PROJECT_CARD_HEIGHT,
        animate_size=ft.Animation(tokens.motion_normal, ft.AnimationCurve.EASE_OUT_CUBIC),
        data={
            "role": "project-card",
            "project_id": project.id,
            "color": project.color,
            "width": width,
            "height": PROJECT_CARD_HEIGHT,
            "hover_color": shell.hover_color,
        },
    )


def empty_project_card(
    tokens: ThemeTokens,
    *,
    width: int,
    on_create: Callable[[object], None],
) -> ft.Container:
    shell = ProjectCardShell(width, PROJECT_CARD_EMPTY_BACKGROUND, tokens)
    plus = ft.Stack(
        [
            cv.Canvas(
                [
                    cv.Circle(
                        36,
                        36,
                        35,
                        paint=ft.Paint(
                            color=PROJECT_CARD_EMPTY_DASH,
                            style=ft.PaintingStyle.STROKE,
                            stroke_width=2,
                            stroke_dash_pattern=[10, 10],
                        ),
                    )
                ],
                width=72,
                height=72,
            ),
            ft.Container(
                lucide_icon(IconName.PLUS, color=PROJECT_CARD_EMPTY_ICON, size=tokens.icon_large, label=ui_text("projects.new_action")),
                width=72,
                height=72,
                alignment=ft.Alignment.CENTER,
            ),
        ],
        width=72,
        height=72,
    )
    visual = ft.Stack(
        [
            shell.canvas,
            ft.Container(plus, left=(width - 72) / 2, top=(PROJECT_CARD_HEIGHT - 72) / 2),
        ],
        width=width,
        height=PROJECT_CARD_HEIGHT,
        clip_behavior=ft.ClipBehavior.NONE,
    )
    detector = ft.GestureDetector(
        visual,
        width=width,
        height=PROJECT_CARD_HEIGHT,
        mouse_cursor=ft.MouseCursor.CLICK,
        tooltip=ui_text("projects.new_action"),
        on_tap=on_create,
        on_enter=shell._hover,
        on_exit=shell._hover,
        data={"role": "project-add-card-action"},
    )
    return ft.Container(
        detector,
        width=width,
        height=PROJECT_CARD_HEIGHT,
        data={"role": "project-add-card", "width": width, "height": PROJECT_CARD_HEIGHT, "full_surface_click": True},
    )
