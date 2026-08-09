from __future__ import annotations

from collections.abc import Callable

import flet as ft

from overlord.ui.design_system.icons import IconName, lucide_icon
from overlord.ui.design_system.tokens import ThemeTokens
from overlord.ui.shell.sidebar import Sidebar
from overlord.ui.strings import ui_text


class AppShell:
    def __init__(
        self,
        tokens: ThemeTokens,
        current_route: str,
        sidebar_collapsed: bool,
        on_navigate: Callable[[str], None],
        on_toggle_sidebar: Callable[[object], None],
    ) -> None:
        self.sidebar = Sidebar(
            tokens,
            current_route,
            sidebar_collapsed,
            on_navigate,
            on_toggle_sidebar,
        )
        self.banner_host = ft.Column(spacing=tokens.space_3)
        self.loading_indicator = ft.ProgressBar(
            color=tokens.accent_primary,
            bgcolor=tokens.border_default,
            visible=False,
        )
        self.content_host = ft.Container(expand=True)
        body = ft.Container(
            ft.Column(
                [self.banner_host, self.loading_indicator, self.content_host],
                spacing=tokens.space_4,
                expand=True,
            ),
            padding=tokens.space_6,
            expand=True,
        )
        self.control = ft.Row([self.sidebar.control, body], spacing=tokens.space_0, expand=True)

    def set_content(self, content: ft.Control) -> None:
        self.content_host.content = content

    def set_loading_visible(self, visible: bool) -> None:
        self.loading_indicator.visible = visible

    def clear_banner(self) -> None:
        self.banner_host.controls = []

    def show_error(self, tokens: ThemeTokens, message: str, on_dismiss: Callable[[], None]) -> None:
        self.banner_host.controls = [
            ft.Container(
                ft.Row([
                    lucide_icon(IconName.ALERT, color=tokens.error.text, size=tokens.icon_medium, label=ui_text("common.error")),
                    ft.Text(message, color=tokens.error.text, expand=True),
                    ft.TextButton(ui_text("common.dismiss"), on_click=lambda _e: on_dismiss()),
                ]),
                bgcolor=tokens.error.background,
                border_radius=tokens.radius_medium,
                padding=tokens.space_3,
            )
        ]

    def show_notice(self, tokens: ThemeTokens, message: str, on_dismiss: Callable[[], None]) -> None:
        self.banner_host.controls = [
            ft.Container(
                ft.Row([
                    lucide_icon(IconName.CHECK, color=tokens.success.text, size=tokens.icon_medium, label=ui_text("common.success")),
                    ft.Text(message, color=tokens.success.text, expand=True),
                    ft.TextButton(ui_text("common.dismiss"), on_click=lambda _e: on_dismiss()),
                ]),
                bgcolor=tokens.success.background,
                border=ft.Border.all(tokens.border_width, tokens.success.main),
                border_radius=tokens.radius_medium,
                padding=tokens.space_3,
            )
        ]
