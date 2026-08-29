from __future__ import annotations

from collections.abc import Callable, Iterable

import flet as ft

from overlord.ui.components.controls import secondary_button
from overlord.ui.components.layout import profile_trigger
from overlord.ui.components.status import status_badge
from overlord.ui.design_system.icons import IconName, lucide_icon
from overlord.ui.design_system.tokens import ThemeTokens
from overlord.ui.strings import ui_text


def project_details_header(
    *,
    title: str,
    description: str | None,
    project_color: str,
    status: str,
    status_label: str,
    favorite_control: ft.Control,
    tokens: ThemeTokens,
    on_back: Callable[[object], None],
    on_more: Callable[[object], None],
) -> ft.Container:
    """Reference-aligned Project identity header shared by every detail tab."""
    back_label = ui_text("projects.back_to_projects")
    back = secondary_button(
        lucide_icon(
            IconName.ARROW_LEFT,
            color=tokens.text_primary,
            size=tokens.icon_large,
            label=back_label,
            show_tooltip=False,
        ),
        tokens,
        width=48,
        height=48,
        tooltip=back_label,
        on_click=on_back,
        data={"role": "project-details-back"},
    )
    identity_icon = ft.Container(
        lucide_icon(
            IconName.PROJECTS,
            color=tokens.accent_primary,
            size=tokens.icon_medium,
            label=title,
            show_tooltip=False,
        ),
        width=48,
        height=48,
        bgcolor=project_color,
        border=ft.Border.all(tokens.border_width, tokens.border_default),
        border_radius=tokens.radius_pill,
        alignment=ft.Alignment.CENTER,
        data={"role": "project-details-icon", "color": project_color},
    )
    title_row = ft.Row(
        [
            ft.Text(
                title,
                size=tokens.text_title + tokens.space_1,
                weight=ft.FontWeight.W_700,
                color=tokens.text_primary,
                max_lines=1,
                overflow=ft.TextOverflow.ELLIPSIS,
                data={"role": "project-details-title"},
            ),
            favorite_control,
        ],
        spacing=tokens.space_1,
        tight=True,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
    )
    identity_copy: list[ft.Control] = [title_row]
    if description:
        identity_copy.append(
            ft.Text(
                description,
                size=tokens.text_body,
                color=tokens.text_secondary,
                max_lines=1,
                overflow=ft.TextOverflow.ELLIPSIS,
                data={"role": "project-details-description"},
            )
        )
    identity = ft.Row(
        [
            identity_icon,
            ft.Column(identity_copy, spacing=tokens.space_0, expand=True),
        ],
        spacing=tokens.space_3,
        expand=True,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
        data={"role": "project-details-identity", "has_description": bool(description)},
    )
    more = secondary_button(
        ft.Row(
            [
                lucide_icon(
                    IconName.MORE,
                    color=tokens.text_primary,
                    size=tokens.icon_small,
                    label=ui_text("projects.more"),
                    show_tooltip=False,
                ),
                ft.Text(ui_text("projects.more"), color=tokens.text_primary, weight=ft.FontWeight.W_500),
            ],
            spacing=tokens.space_2,
            tight=True,
        ),
        tokens,
        width=92,
        height=36,
        on_click=on_more,
        data={"role": "project-details-more"},
    )
    header = ft.Row(
        [
            ft.Row(
                [back, identity],
                spacing=tokens.space_6,
                expand=True,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            ft.Row(
                [
                    status_badge(status, status_label, tokens),
                    more,
                    profile_trigger(tokens),
                ],
                spacing=tokens.space_4,
                tight=True,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                data={"role": "project-details-actions"},
            ),
        ],
        height=51,
        spacing=tokens.space_4,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
        data={"role": "project-details-header"},
    )
    return ft.Container(
        header,
        height=51,
        data={"role": "page-header", "variant": "project-details"},
    )


def project_details_shell(
    header: ft.Control,
    tabs: ft.Control,
    content: Iterable[ft.Control],
    tokens: ThemeTokens,
) -> ft.ListView:
    """One reusable Project Details scroll surface for every Project sub-route."""
    body = ft.Column(
        list(content),
        spacing=tokens.space_4,
        horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
        data={"role": "project-details-content"},
    )
    padding_layer = ft.Container(
        ft.Column(
            [header, tabs, body],
            spacing=tokens.space_4,
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
        ),
        padding=ft.Padding.symmetric(horizontal=tokens.space_6, vertical=tokens.space_4),
        data={
            "role": "global-page-padding-layer",
            "variant": "project-details",
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
            "role": "project-detail-page",
            "layout": "global-page",
            "variant": "responsive-project-details",
            "content_gap": tokens.space_4,
        },
    )
