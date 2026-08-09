from __future__ import annotations

import flet as ft

from overlord.ui.design_system.tokens import ThemeTokens


def show_success(page: ft.Page | None, tokens: ThemeTokens, message: str) -> None:
    if page is None:
        return
    page.show_dialog(
        ft.SnackBar(
            ft.Text(message, color=tokens.on_accent),
            bgcolor=tokens.success.main,
            show_close_icon=True,
        )
    )


def empty_state(message: str, tokens: ThemeTokens, action: ft.Control | None = None) -> ft.Container:
    controls: list[ft.Control] = [ft.Text(message, color=tokens.text_muted, size=tokens.text_body)]
    if action:
        controls.append(action)
    return ft.Container(
        ft.Column(controls, horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=tokens.space_3),
        alignment=ft.Alignment.CENTER,
        bgcolor=tokens.surface_inner,
        border_radius=tokens.radius_medium,
        padding=tokens.space_6,
    )


def loading_state(message: str, tokens: ThemeTokens) -> ft.Container:
    return ft.Container(
        ft.Column(
            [
                ft.ProgressRing(color=tokens.accent_primary, bgcolor=tokens.border_default),
                ft.Text(message, color=tokens.text_secondary, size=tokens.text_body),
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=tokens.space_3,
        ),
        alignment=ft.Alignment.CENTER,
        bgcolor=tokens.surface_inner,
        border_radius=tokens.radius_medium,
        padding=tokens.space_6,
    )
