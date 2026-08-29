from __future__ import annotations

from collections.abc import Iterable
import math

import flet as ft

from overlord.ui.design_system.icons import IconName, lucide_icon
from overlord.ui.design_system.tokens import ThemeTokens
from overlord.ui.strings import ui_text


def card(
    title: str,
    controls: Iterable[ft.Control],
    tokens: ThemeTokens,
    *,
    subtitle: str | None = None,
    col: int | dict[str, int] = 12,
) -> ft.Container:
    heading = [
        ft.Text(title, size=tokens.text_title, weight=ft.FontWeight.W_600, color=tokens.text_primary)
    ]
    if subtitle:
        heading.append(ft.Text(subtitle, size=tokens.text_small, color=tokens.text_muted))
    return ft.Container(
        content=ft.Column([*heading, *controls], spacing=tokens.space_3),
        bgcolor=tokens.surface_card,
        border=ft.Border.all(tokens.border_width, tokens.border_default),
        border_radius=tokens.radius_card,
        padding=tokens.space_5,
        col=col,
    )


def page_heading(title: str, subtitle: str, tokens: ThemeTokens, actions: Iterable[ft.Control] = ()) -> ft.Row:
    return ft.Row(
        [
            ft.Column(
                [
                    ft.Text(title, size=tokens.text_display, weight=ft.FontWeight.W_700, color=tokens.text_primary),
                    ft.Text(subtitle, size=tokens.text_body, color=tokens.text_secondary),
                ],
                spacing=tokens.space_1,
                expand=True,
            ),
            *actions,
        ],
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
    )


def profile_trigger(tokens: ThemeTokens, *, display_name: str | None = None) -> ft.Semantics:
    """Canonical global profile trigger used by standard and feature headers."""
    resolved_name = display_name or ui_text("profile.display_name")
    chevron = lucide_icon(
        IconName.CHEVRON,
        color=tokens.profile_trigger_foreground,
        size=tokens.icon_large,
        label=ui_text("profile.menu"),
        show_tooltip=False,
    )
    chevron.rotate = ft.Rotate(angle=math.pi / 2)
    profile_surface = ft.Container(
        ft.Stack(
            [
                ft.Container(
                    ft.CircleAvatar(
                        ft.Text(
                            resolved_name[:1].upper(),
                            color=tokens.on_accent,
                            weight=ft.FontWeight.W_700,
                        ),
                        bgcolor=tokens.accent_primary,
                        radius=tokens.space_4,
                    ),
                    left=tokens.space_1,
                    top=tokens.space_1,
                    width=tokens.space_8,
                    height=tokens.space_8,
                ),
                ft.Container(
                    chevron,
                    left=44,
                    top=tokens.space_2,
                    width=tokens.icon_large,
                    height=tokens.icon_large,
                ),
            ],
            width=76,
            height=tokens.control_height,
            clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
        ),
        width=76,
        height=tokens.control_height,
        bgcolor=tokens.profile_trigger_background,
        border_radius=tokens.space_5,
        clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
        data={
            "role": "user-menu-trigger",
            "display_name": resolved_name,
            "reference_width": 76,
            "reference_height": 40,
            "avatar_size": 32,
        },
    )
    return ft.Semantics(
        content=profile_surface,
        label=ui_text("profile.menu"),
        button=True,
    )


def page_header(
    title: str,
    tokens: ThemeTokens,
    *,
    subtitle: str | None = None,
    actions: Iterable[ft.Control] = (),
    display_name: str | None = None,
) -> ft.Row:
    """Shared, non-sticky header used inside every main page scroll surface."""
    left_controls: list[ft.Control] = [
        ft.Text(
            title,
            size=tokens.text_title + tokens.space_1,
            weight=ft.FontWeight.W_700,
            color=tokens.text_primary,
            max_lines=1,
            overflow=ft.TextOverflow.ELLIPSIS,
            style=ft.TextStyle(height=1.15),
            data={"role": "page-header-title"},
        )
    ]
    if subtitle:
        left_controls.append(
            ft.Text(
                subtitle,
                size=tokens.text_body,
                color=tokens.text_secondary,
                max_lines=2,
                overflow=ft.TextOverflow.ELLIPSIS,
                style=ft.TextStyle(height=1.2),
                data={"role": "page-header-subtitle"},
            )
        )

    right_controls = [*actions, profile_trigger(tokens, display_name=display_name)]
    return ft.Row(
        [
            ft.Column(
                left_controls,
                spacing=tokens.space_1,
                expand=True,
                data={"role": "page-header-copy", "has_subtitle": bool(subtitle)},
            ),
            ft.Row(
                right_controls,
                spacing=tokens.space_3,
                tight=True,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                data={"role": "page-header-actions"},
            ),
        ],
        spacing=tokens.space_4,
        height=51,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
        data={"role": "page-header", "reference_copy_height": 51},
    )


def page_container(
    title: str,
    content: Iterable[ft.Control],
    tokens: ThemeTokens,
    *,
    subtitle: str | None = None,
    actions: Iterable[ft.Control] = (),
    content_spacing: int | float | None = None,
    header_gap: int | float | None = None,
    page_id: str,
    role: str = "global-page-container",
) -> ft.ListView:
    """One scroll surface with shared page padding, header, and body rhythm."""
    body = ft.Column(
        list(content),
        spacing=tokens.space_4 if content_spacing is None else content_spacing,
        data={"role": "page-content", "page": page_id},
    )
    padding_layer = ft.Container(
        ft.Column(
            [
                page_header(title, tokens, subtitle=subtitle, actions=actions),
                body,
            ],
            spacing=tokens.space_6 if header_gap is None else header_gap,
        ),
        padding=ft.Padding.symmetric(horizontal=tokens.space_6, vertical=tokens.space_4),
        data={
            "role": "global-page-padding-layer",
            "horizontal_padding": tokens.space_6,
            "vertical_padding": tokens.space_4,
        },
    )
    return ft.ListView(
        [padding_layer],
        spacing=tokens.space_0,
        padding=tokens.space_0,
        scroll=ft.ScrollMode.AUTO,
        expand=True,
        data={
            "role": role,
            "layout": "global-page",
            "page": page_id,
            "horizontal_padding": tokens.space_6,
            "vertical_padding": tokens.space_4,
            "header_gap": tokens.space_6 if header_gap is None else header_gap,
        },
    )


def workspace_page(
    header: ft.Control,
    toolbar: ft.Control,
    view_host: ft.Control,
    tokens: ThemeTokens,
    *,
    page_id: str,
    content_spacing: int | float | None = None,
) -> ft.Container:
    """Viewport-filling page whose working view owns the remaining space."""
    header.expand = False
    toolbar.expand = False
    view_host.expand = True
    workspace_column = ft.Column(
        [header, toolbar, view_host],
        spacing=tokens.space_4 if content_spacing is None else content_spacing,
        horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
        expand=True,
        data={"role": "workspace-page-content", "page": page_id},
    )
    return ft.Container(
        workspace_column,
        padding=ft.Padding.symmetric(
            horizontal=tokens.space_6,
            vertical=tokens.space_4,
        ),
        expand=True,
        data={
            "role": "workspace-page-container",
            "layout": "workspace-page",
            "page": page_id,
            "horizontal_padding": tokens.space_6,
            "vertical_padding": tokens.space_4,
            "scroll_owner": "view-host",
        },
    )
