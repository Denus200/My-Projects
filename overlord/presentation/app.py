from __future__ import annotations

import logging
import uuid
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import flet as ft

from overlord.application import ApplicationServices
from overlord.presentation.design_system.assets import brand_mark
from overlord.presentation.design_system.icons import IconName, lucide_icon
from overlord.presentation.design_system.themes import DARK_THEME, LIGHT_THEME, flet_theme_mode
from overlord.presentation.design_system.tokens import ThemeTokens, resolve_tokens
from overlord.presentation.navigation import NAVIGATION, AppRoute, route_family
from overlord.presentation.pages.cycles import build_cycles
from overlord.presentation.pages.dashboard import build_dashboard
from overlord.presentation.pages.projects import build_projects
from overlord.presentation.pages.settings import build_settings
from overlord.presentation.pages.tasks import build_tasks
from overlord.presentation.state import AppSessionState


class OverlordApp:
    def __init__(self, page: ft.Page, services: ApplicationServices):
        self.page = page
        self.services = services
        settings = services.settings.get_settings.execute()
        self.state = AppSessionState(
            theme_mode=settings.theme_mode,
            sidebar_collapsed=settings.sidebar_collapsed,
        )
        initial = f"/{settings.startup_destination}"
        current = page.route or "/"
        self.state.route = initial if current in {"", "/"} else current
        self.page.on_route_change = self._on_route_change

    def mount(self) -> None:
        self.page.title = "Overlord"
        self.page.padding = 0
        self.page.theme = LIGHT_THEME
        self.page.dark_theme = DARK_THEME
        if (self.page.route or "/") != self.state.route:
            self.page.go(self.state.route)
        else:
            self.render()

    def _on_route_change(self, event) -> None:
        self.state.route = event.route
        parsed = urlparse(event.route)
        if parsed.path == AppRoute.TASKS:
            selected = parse_qs(parsed.query).get("task")
            if selected:
                try:
                    self.state.selected_task_id = int(selected[0])
                except ValueError:
                    self.state.selected_task_id = None
        self.render()

    def navigate(self, route: str) -> None:
        self.page.go(route)

    def report_error(self, message: str) -> None:
        self.state.error_message = message
        self.render()

    def apply_settings(self, settings) -> None:
        self.state.theme_mode = settings.theme_mode
        self.state.sidebar_collapsed = settings.sidebar_collapsed
        self.state.error_message = None
        self.render()

    def toggle_sidebar(self, _event) -> None:
        try:
            updated = self.services.settings.update_settings.execute(
                sidebar_collapsed=not self.state.sidebar_collapsed
            )
            self.state.sidebar_collapsed = updated.sidebar_collapsed
            self.render()
        except Exception as error:
            self.report_error(str(error))

    def _is_system_dark(self) -> bool:
        return getattr(self.page, "platform_brightness", ft.Brightness.LIGHT) == ft.Brightness.DARK

    def _sidebar(self, tokens: ThemeTokens, active: AppRoute | None) -> ft.Container:
        collapsed = self.state.sidebar_collapsed
        width = 76 if collapsed else 232
        items: list[ft.Control] = [
            ft.Container(
                brand_mark(color=tokens.text_primary, expanded=not collapsed, title_size=tokens.text_title),
                padding=ft.Padding.symmetric(horizontal=tokens.space_4, vertical=tokens.space_6),
            )
        ]
        for item in NAVIGATION:
            selected = active is item.route
            content = ft.Row(
                [
                    lucide_icon(
                        item.icon,
                        color=tokens.accent_primary if selected else tokens.text_secondary,
                        size=tokens.icon_medium,
                        label=item.label,
                    ),
                    *([] if collapsed else [ft.Text(
                        item.label,
                        color=tokens.text_primary if selected else tokens.text_secondary,
                        weight=ft.FontWeight.W_600 if selected else ft.FontWeight.W_400,
                    )]),
                ],
                alignment=ft.MainAxisAlignment.CENTER if collapsed else ft.MainAxisAlignment.START,
                spacing=tokens.space_3,
            )
            items.append(
                ft.Button(
                    content,
                    bgcolor=tokens.soft_red_background if selected else tokens.app_bar,
                    color=tokens.text_primary,
                    elevation=0,
                    width=width - tokens.space_4,
                    height=48,
                    tooltip=item.label,
                    on_click=lambda _e, route=item.route: self.navigate(route.value),
                )
            )
        collapse_name = IconName.EXPAND if collapsed else IconName.COLLAPSE
        items.append(
            ft.Container(
                ft.Button(
                    lucide_icon(collapse_name, color=tokens.text_secondary, size=tokens.icon_medium, label="Expand sidebar" if collapsed else "Collapse sidebar"),
                    bgcolor=tokens.app_bar,
                    elevation=0,
                    width=width - tokens.space_4,
                    height=48,
                    tooltip="Expand sidebar" if collapsed else "Collapse sidebar",
                    on_click=self.toggle_sidebar,
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

    def _not_found(self, tokens: ThemeTokens) -> ft.Control:
        return ft.Column([
            ft.Text("Page not found", size=tokens.text_display, color=tokens.text_primary, weight=ft.FontWeight.W_700),
            ft.Text("This route is not part of Foundation v0.1.", color=tokens.text_secondary),
            ft.Button("Go to Dashboard", bgcolor=tokens.accent_primary, color=tokens.on_accent, on_click=lambda _e: self.navigate(AppRoute.DASHBOARD.value)),
        ], spacing=tokens.space_4)

    def _page_content(self, tokens: ThemeTokens, path: str, family: AppRoute | None) -> ft.Control:
        if family is AppRoute.DASHBOARD:
            return build_dashboard(self.services, tokens, self.navigate, self.render, self.report_error)
        if family is AppRoute.TASKS:
            return build_tasks(self.services, tokens, self.state, self.render, self.report_error)
        if family is AppRoute.PROJECTS:
            return build_projects(self.services, tokens, path, self.navigate, self.render, self.report_error)
        if family is AppRoute.CYCLES:
            return build_cycles(self.services, tokens, path, self.navigate, self.render, self.report_error)
        if family is AppRoute.SETTINGS:
            return build_settings(self.services, tokens, self.apply_settings, self.report_error)
        return self._not_found(tokens)

    def render(self) -> None:
        parsed = urlparse(self.state.route)
        path = parsed.path
        family = route_family(path)
        tokens = resolve_tokens(self.state.theme_mode, self._is_system_dark())
        self.page.theme_mode = flet_theme_mode(self.state.theme_mode)
        self.page.bgcolor = tokens.app_background
        try:
            content = self._page_content(tokens, path, family)
        except Exception as error:
            content = ft.Column([
                ft.Text("This page could not be loaded.", size=tokens.text_title, color=tokens.error.text, weight=ft.FontWeight.W_600),
                ft.Text(str(error), color=tokens.text_secondary),
                ft.Button("Try again", on_click=lambda _e: self.render()),
            ], spacing=tokens.space_3)
        banners: list[ft.Control] = []
        if self.state.error_message:
            banners.append(
                ft.Container(
                    ft.Row([
                        lucide_icon(IconName.ALERT, color=tokens.error.text, size=tokens.icon_medium, label="Error"),
                        ft.Text(self.state.error_message, color=tokens.error.text, expand=True),
                        ft.TextButton("Dismiss", on_click=lambda _e: self._dismiss_error()),
                    ]),
                    bgcolor=tokens.error.background,
                    border_radius=tokens.radius_medium,
                    padding=tokens.space_3,
                )
            )
        body = ft.Container(
            ft.Column([*banners, content], spacing=tokens.space_4, expand=True),
            padding=tokens.space_6,
            expand=True,
        )
        self.page.controls.clear()
        self.page.add(ft.Row([self._sidebar(tokens, family), body], spacing=tokens.space_0, expand=True))
        self.page.update()

    def _dismiss_error(self) -> None:
        self.state.error_message = None
        self.render()


def show_recovery(page: ft.Page, error: Exception, database_path: Path) -> None:
    correlation_id = uuid.uuid4().hex[:12]
    logging.getLogger("overlord").exception(
        "startup_failed error_id=%s error_class=%s", correlation_id, error.__class__.__name__
    )
    tokens = resolve_tokens("light")
    page.title = "Overlord — Recovery"
    page.bgcolor = tokens.app_background
    page.theme = LIGHT_THEME
    page.dark_theme = DARK_THEME
    error_message = str(error).lower()
    if "checksum" in error_message or "migration" in error_message or "schema" in error_message:
        category = "Migration or schema error"
    elif "corrupt" in error_message or "malformed" in error_message or "integrity" in error_message:
        category = "Database integrity error"
    elif "locked" in error_message or "busy" in error_message:
        category = "Database lock error"
    elif error.__class__.__name__ in {"PermissionError", "PermissionDenied"} or "permission" in error_message or "readonly" in error_message:
        category = "Database permission error"
    else:
        category = "Unexpected startup error"
    page.add(
        ft.Container(
            ft.Column([
                lucide_icon(IconName.ALERT, color=tokens.error.main, size=tokens.icon_display, label="Startup error"),
                ft.Text("Overlord could not open safely", size=tokens.text_display, color=tokens.text_primary, weight=ft.FontWeight.W_700),
                ft.Text("Normal write actions are disabled. The database was not automatically recreated or restored.", color=tokens.text_secondary),
                ft.Text(f"Error ID: {correlation_id}", color=tokens.text_muted),
                ft.Text(f"Database: {database_path}", color=tokens.text_muted, selectable=True),
                ft.Text(f"Category: {category}", color=tokens.error.text),
                ft.Text(f"Error type: {error.__class__.__name__}", color=tokens.text_muted),
                ft.Text("Review data/backups and docs/architecture/DATABASE_RECOVERY.md before restoring anything.", color=tokens.text_secondary),
            ], spacing=tokens.space_4),
            bgcolor=tokens.surface_card,
            border=ft.Border.all(tokens.border_width, tokens.border_default),
            border_radius=tokens.radius_card,
            padding=tokens.space_8,
            margin=tokens.space_8,
        )
    )
