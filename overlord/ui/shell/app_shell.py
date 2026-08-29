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
        on_toggle_language: Callable[[object], None] | None = None,
    ) -> None:
        self.sidebar = Sidebar(
            tokens,
            current_route,
            sidebar_collapsed,
            on_navigate,
            on_toggle_sidebar,
            on_toggle_language,
        )
        self.banner_host = ft.Column(spacing=tokens.space_3, visible=False)
        self.loading_indicator = ft.ProgressBar(
            color=tokens.accent_primary,
            bgcolor=tokens.border_default,
            visible=False,
        )
        self.content_host = ft.Container(expand=True)
        self._tokens = tokens
        self.body = ft.Container(
            ft.Column(
                [self.banner_host, self.loading_indicator, self.content_host],
                spacing=tokens.space_0,
                expand=True,
            ),
            padding=tokens.space_6,
            expand=True,
        )
        self.control = ft.Row([self.sidebar.control, self.body], spacing=tokens.space_0, expand=True)

    def set_content(self, content: ft.Control) -> None:
        self.content_host.content = content
        data = getattr(content, "data", None)
        if isinstance(data, dict) and data.get("layout") in {
            "global-page",
            "workspace-page",
        }:
            self.body.padding = self._tokens.space_0
        else:
            self.body.padding = self._tokens.space_6

    def set_loading_visible(self, visible: bool) -> None:
        self.loading_indicator.visible = visible

    def clear_banner(self) -> None:
        self.banner_host.controls = []
        self.banner_host.visible = False

    def show_error(self, tokens: ThemeTokens, message: str, on_dismiss: Callable[[], None]) -> None:
        self.banner_host.visible = True
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
        self.banner_host.visible = True
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
