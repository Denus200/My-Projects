from __future__ import annotations

import flet as ft

from overlord.ui.design_system.icons import IconName, lucide_icon
from overlord.ui.design_system.tokens import ThemeTokens


def task_drag_handle_surface(
    tokens: ThemeTokens,
    *,
    label: str,
    muted: bool = False,
) -> ft.Container:
    """Shared six-dot surface used by native and cross-column task reordering."""
    return ft.Container(
        lucide_icon(
            IconName.GRIP_VERTICAL,
            color=tokens.text_muted,
            size=tokens.icon_small,
            label=label,
            show_tooltip=False,
        ),
        width=tokens.icon_large,
        height=tokens.space_8,
        alignment=ft.Alignment.TOP_CENTER,
        bgcolor=tokens.control_background_disabled,
        border_radius=tokens.radius_small,
        padding=ft.Padding.symmetric(vertical=tokens.space_2),
        opacity=0.72 if muted else 1.0,
        data={"role": "task-drag-handle-surface"},
    )


def reorderable_task_handle(
    tokens: ThemeTokens,
    *,
    label: str,
    data: dict[str, object],
    muted: bool = False,
) -> ft.ReorderableDragHandle:
    return ft.ReorderableDragHandle(
        task_drag_handle_surface(tokens, label=label, muted=muted),
        data={"role": "task-drag-handle", **data},
        mouse_cursor=ft.MouseCursor.GRAB,
    )


def draggable_task_handle(
    tokens: ThemeTokens,
    *,
    label: str,
    data: dict[str, object],
    feedback: ft.Control,
) -> ft.Draggable:
    return ft.Draggable(
        task_drag_handle_surface(tokens, label=label),
        group="task-card",
        data={"role": "task-drag-handle", **data},
        content_when_dragging=ft.Container(
            width=tokens.icon_large,
            height=tokens.space_8,
            border_radius=tokens.radius_small,
            bgcolor=tokens.interactive_hover,
        ),
        content_feedback=feedback,
    )
