from __future__ import annotations

from collections.abc import Callable
from urllib.parse import urlparse

import flet as ft

from overlord.ui.design_system.assets import brand_mark
from overlord.ui.design_system.icons import IconName, lucide_icon
from overlord.ui.design_system.tokens import ThemeTokens
from overlord.ui.navigation import NAVIGATION, AppRoute, route_family
from overlord.ui.strings import ui_text


class Sidebar:
    def __init__(
        self,
        tokens: ThemeTokens,
        current_route: str,
        collapsed: bool,
        on_navigate: Callable[[str], None],
        on_toggle: Callable[[object], None],
    ) -> None:
        self._on_navigate = on_navigate
        self._on_toggle = on_toggle
        self._nav_buttons: dict[AppRoute, ft.Button] = {}
        self._nav_icons: dict[AppRoute, ft.Image] = {}
        self._nav_labels: dict[AppRoute, ft.Text] = {}
        self.control = self._build(tokens, self._active_route(current_route), collapsed)

    def rebuild(self, tokens: ThemeTokens, current_route: str, collapsed: bool) -> None:
        replacement = self._build(tokens, self._active_route(current_route), collapsed)
        self.control.content = replacement.content
        self.control.width = replacement.width
        self.control.bgcolor = replacement.bgcolor
        self.control.border = replacement.border
        self.control.padding = replacement.padding

    def update_selection(self, tokens: ThemeTokens, current_route: str) -> None:
        active = self._active_route(current_route)
        for route, button in self._nav_buttons.items():
            selected = active is route
            button.bgcolor = tokens.soft_red_background if selected else tokens.app_bar
            button.color = tokens.text_primary
            icon = self._nav_icons[route]
            icon.color = tokens.accent_primary if selected else tokens.text_secondary
            label = self._nav_labels[route]
            label.color = tokens.text_primary if selected else tokens.text_secondary
            label.weight = ft.FontWeight.W_600 if selected else ft.FontWeight.W_400

    @staticmethod
    def _active_route(current_route: str) -> AppRoute | None:
        family = route_family(urlparse(current_route).path)
        return AppRoute.DASHBOARD if family is AppRoute.DAILY_PLANNING else family

    def _build(self, tokens: ThemeTokens, active: AppRoute | None, collapsed: bool) -> ft.Container:
        width = 76 if collapsed else 232
        self._nav_buttons.clear()
        self._nav_icons.clear()
        self._nav_labels.clear()
        items: list[ft.Control] = [
            ft.Container(
                brand_mark(color=tokens.text_primary, expanded=not collapsed, title_size=tokens.text_title),
                padding=ft.Padding.symmetric(horizontal=tokens.space_4, vertical=tokens.space_6),
            )
        ]
        for item in NAVIGATION:
            selected = active is item.route
            icon = lucide_icon(
                item.icon,
                color=tokens.accent_primary if selected else tokens.text_secondary,
                size=tokens.icon_medium,
                label=item.label,
            )
            label = ft.Text(
                item.label,
                color=tokens.text_primary if selected else tokens.text_secondary,
                weight=ft.FontWeight.W_600 if selected else ft.FontWeight.W_400,
            )
            content = ft.Row(
                [icon, *([] if collapsed else [label])],
                alignment=ft.MainAxisAlignment.CENTER if collapsed else ft.MainAxisAlignment.START,
                spacing=tokens.space_3,
            )
            button = ft.Button(
                content,
                bgcolor=tokens.soft_red_background if selected else tokens.app_bar,
                color=tokens.text_primary,
                elevation=0,
                width=width - tokens.space_4,
                height=48,
                tooltip=item.label,
                on_click=lambda _e, route=item.route: self._on_navigate(route.value),
            )
            self._nav_buttons[item.route] = button
            self._nav_icons[item.route] = icon
            self._nav_labels[item.route] = label
            items.append(button)
        collapse_name = IconName.EXPAND if collapsed else IconName.COLLAPSE
        collapse_label = ui_text("nav.expand_sidebar") if collapsed else ui_text("nav.collapse_sidebar")
        items.append(
            ft.Container(
                ft.Button(
                    lucide_icon(collapse_name, color=tokens.text_secondary, size=tokens.icon_medium, label=collapse_label),
                    bgcolor=tokens.app_bar,
                    elevation=0,
                    width=width - tokens.space_4,
                    height=48,
                    tooltip=collapse_label,
                    on_click=self._on_toggle,
                ),
                expand=True,
                alignment=ft.Alignment.BOTTOM_CENTER,
            )
        )
        return ft.Container(
            ft.Column(items, spacing=tokens.space_2, expand=True),
            width=width,
            bgcolor=tokens.app_bar,
            border=ft.Border.only(right=ft.BorderSide(tokens.border_width, tokens.border_default)),
            padding=ft.Padding.symmetric(horizontal=tokens.space_2),
        )
