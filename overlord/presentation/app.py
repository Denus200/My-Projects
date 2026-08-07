from __future__ import annotations

import asyncio
import contextlib
import logging
import uuid
from dataclasses import dataclass
from pathlib import Path
from time import perf_counter
from urllib.parse import parse_qs, urlparse

import flet as ft

from overlord.application import ApplicationServices
from overlord.presentation.design_system.assets import brand_mark
from overlord.presentation.design_system.icons import IconName, lucide_icon
from overlord.presentation.design_system.themes import build_dark_theme, build_light_theme, flet_theme_mode
from overlord.presentation.design_system.tokens import ThemeTokens, resolve_tokens
from overlord.presentation.navigation import NAVIGATION, AppRoute, route_family
from overlord.presentation.pages.cycles import build_cycles
from overlord.presentation.pages.daily_planning import build_daily_planning
from overlord.presentation.pages.dashboard import build_dashboard
from overlord.presentation.pages.projects import build_projects
from overlord.presentation.pages.settings import build_settings
from overlord.presentation.pages.tasks import build_tasks
from overlord.presentation.state import AppSessionState
from overlord.presentation.strings import ui_text


@dataclass(frozen=True, slots=True)
class RouteTiming:
    requested_route: str
    previous_route: str
    query_ms: float
    render_ms: float
    total_ms: float
    loading_visible: bool
    duplicate: bool = False
    failed: bool = False


class OverlordApp:
    def __init__(
        self,
        page: ft.Page,
        services: ApplicationServices,
        *,
        development: bool = True,
        loading_delay_seconds: float = 0.15,
    ):
        self.page = page
        self.services = services
        self.development = development
        self.loading_delay_seconds = loading_delay_seconds
        self.logger = logging.getLogger("overlord.navigation")
        settings = services.settings.get_settings.execute()
        self.state = AppSessionState(
            theme_mode=settings.theme_mode,
            sidebar_collapsed=settings.sidebar_collapsed,
        )
        initial = f"/{settings.startup_destination}"
        current = page.route or "/"
        self.state.route = initial if current in {"", "/"} else current
        self.page.on_route_change = self._on_route_change
        self.page.on_resize = self._on_page_resize

        self._mounted = False
        self._transition_generation = 0
        self._scheduled_route: str | None = None
        self._pending_route: str | None = None
        self._transition_loading_visible = False
        self._settings_narrow: bool | None = None
        self.last_route_timing: RouteTiming | None = None
        self._sidebar_host: ft.Container | None = None
        self._content_host: ft.Container | None = None
        self._banner_host: ft.Column | None = None
        self._loading_indicator: ft.ProgressBar | None = None
        self._nav_buttons: dict[AppRoute, ft.Button] = {}
        self._nav_icons: dict[AppRoute, ft.Image] = {}
        self._nav_labels: dict[AppRoute, ft.Text] = {}

    def mount(self) -> None:
        if self._mounted:
            return
        self.page.title = ui_text("app.name")
        self.page.padding = 0
        self.page.theme = build_light_theme()
        self.page.dark_theme = build_dark_theme()
        tokens = self._tokens()
        self._apply_page_theme(tokens)

        parsed = urlparse(self.state.route)
        family = route_family(parsed.path)
        sidebar_family = self._sidebar_family(family)
        self._sidebar_host = self._sidebar(tokens, sidebar_family)
        self._banner_host = ft.Column(spacing=tokens.space_3)
        self._loading_indicator = ft.ProgressBar(
            color=tokens.accent_primary,
            bgcolor=tokens.border_default,
            visible=False,
        )
        self._content_host = ft.Container(expand=True)
        body = ft.Container(
            ft.Column(
                [self._banner_host, self._loading_indicator, self._content_host],
                spacing=tokens.space_4,
                expand=True,
            ),
            padding=tokens.space_6,
            expand=True,
        )
        shell = ft.Row([self._sidebar_host, body], spacing=tokens.space_0, expand=True)
        self.page.add(shell)
        self._mounted = True
        self._render_route_sync(self.state.route, previous_route="<startup>", log_transition=True)

        if (self.page.route or "/") != self.state.route:
            self._schedule_route_push(self.state.route)

    async def _on_route_change(self, event) -> None:
        await self.transition_to(event.route)

    def _on_page_resize(self, _event=None) -> None:
        if not self._mounted or route_family(urlparse(self.state.route).path) is not AppRoute.SETTINGS:
            return
        narrow = self._is_settings_narrow()
        if self._settings_narrow == narrow:
            return
        self._settings_narrow = narrow
        self.render()

    async def transition_to(self, route: str) -> bool:
        requested_route = self._canonical_route(route)
        previous_route = self.state.route
        if requested_route == self._scheduled_route:
            self._scheduled_route = None
        if requested_route == previous_route or requested_route == self._pending_route:
            self.last_route_timing = RouteTiming(
                requested_route=requested_route,
                previous_route=previous_route,
                query_ms=0.0,
                render_ms=0.0,
                total_ms=0.0,
                loading_visible=False,
                duplicate=True,
            )
            self._log(
                "route_transition_ignored requested_route=%s previous_route=%s reason=duplicate",
                requested_route,
                previous_route,
            )
            return False

        self._transition_generation += 1
        generation = self._transition_generation
        self._pending_route = requested_route
        self._transition_loading_visible = False
        started = perf_counter()
        self._log(
            "route_transition_requested requested_route=%s previous_route=%s",
            requested_route,
            previous_route,
        )

        self.state.route = requested_route
        self._apply_route_selection(requested_route)
        self._update_navigation(self._tokens(), self._sidebar_family(route_family(urlparse(requested_route).path)))
        self.page.update()

        loading_task = asyncio.create_task(self._show_loading_after_delay(generation))
        query_started = perf_counter()
        self._log(
            "route_query_start requested_route=%s previous_route=%s",
            requested_route,
            previous_route,
        )
        failed = False
        try:
            tokens = self._tokens()
            parsed = urlparse(requested_route)
            family = route_family(parsed.path)
            content = await asyncio.to_thread(self._page_content, tokens, parsed.path, family)
        except Exception as error:
            failed = True
            content = self._route_error(self._tokens(), error)
        query_complete = perf_counter()
        query_ms = (query_complete - query_started) * 1000
        self._log(
            "route_query_complete requested_route=%s previous_route=%s elapsed_ms=%.2f failed=%s",
            requested_route,
            previous_route,
            query_ms,
            failed,
        )

        loading_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await loading_task
        if generation != self._transition_generation:
            return False

        render_started = perf_counter()
        self._set_loading_visible(False)
        assert self._content_host is not None
        self._content_host.content = content
        self._refresh_banner(self._tokens())
        self.page.update()
        render_complete = perf_counter()
        render_ms = (render_complete - render_started) * 1000
        total_ms = (render_complete - started) * 1000
        self._pending_route = None
        self.last_route_timing = RouteTiming(
            requested_route=requested_route,
            previous_route=previous_route,
            query_ms=query_ms,
            render_ms=render_ms,
            total_ms=total_ms,
            loading_visible=self._transition_loading_visible,
            failed=failed,
        )
        self._log(
            "route_render_complete requested_route=%s previous_route=%s query_ms=%.2f render_ms=%.2f total_ms=%.2f loading_visible=%s failed=%s",
            requested_route,
            previous_route,
            query_ms,
            render_ms,
            total_ms,
            self._transition_loading_visible,
            failed,
        )
        return True

    def navigate(self, route: str) -> None:
        requested_route = self._canonical_route(route)
        if requested_route in {self.state.route, self._scheduled_route, self._pending_route}:
            self._log(
                "route_transition_ignored requested_route=%s previous_route=%s reason=duplicate_click",
                requested_route,
                self.state.route,
            )
            return
        self._scheduled_route = requested_route
        parsed = urlparse(requested_route)
        self._update_navigation(self._tokens(), self._sidebar_family(route_family(parsed.path)))
        self.page.update()
        self._schedule_route_push(requested_route)

    def _schedule_route_push(self, route: str) -> None:
        if hasattr(self.page, "run_task"):
            self.page.run_task(self._push_route, route)
        else:
            self.page.go(route)

    async def _push_route(self, route: str) -> None:
        try:
            push_route = getattr(self.page, "push_route", None)
            if push_route is not None:
                await push_route(route)
            else:
                self.page.go(route)
        except Exception:
            if self._scheduled_route == route:
                self._scheduled_route = None
            raise

    async def _show_loading_after_delay(self, generation: int) -> None:
        await asyncio.sleep(self.loading_delay_seconds)
        if generation != self._transition_generation or self._pending_route is None:
            return
        self._transition_loading_visible = True
        self._set_loading_visible(True)
        self.page.update()

    def _set_loading_visible(self, visible: bool) -> None:
        if self._loading_indicator is not None:
            self._loading_indicator.visible = visible

    def report_error(self, message: str) -> None:
        self.state.error_message = message
        self.state.notice_message = None
        self._refresh_banner(self._tokens())
        self.page.update()

    def apply_settings(self, settings, notice_message: str | None = None) -> None:
        sidebar_changed = self.state.sidebar_collapsed != settings.sidebar_collapsed
        self.state.theme_mode = settings.theme_mode
        self.state.sidebar_collapsed = settings.sidebar_collapsed
        self.state.error_message = None
        self.state.notice_message = notice_message
        tokens = self._tokens()
        self._apply_page_theme(tokens)
        if sidebar_changed:
            self._rebuild_sidebar(tokens)
        else:
            parsed = urlparse(self.state.route)
            self._update_navigation(tokens, self._sidebar_family(route_family(parsed.path)))
        self.render()

    def toggle_sidebar(self, _event) -> None:
        try:
            updated = self.services.settings.update_settings.execute(
                sidebar_collapsed=not self.state.sidebar_collapsed
            )
            self.state.sidebar_collapsed = updated.sidebar_collapsed
            self._rebuild_sidebar(self._tokens())
            self.page.update()
        except Exception as error:
            self.report_error(str(error))

    def render(self) -> None:
        if not self._mounted:
            return
        self._render_route_sync(self.state.route, previous_route=self.state.route, log_transition=False)

    def _render_route_sync(self, route: str, *, previous_route: str, log_transition: bool) -> None:
        requested_route = self._canonical_route(route)
        started = perf_counter()
        self.state.route = requested_route
        self._apply_route_selection(requested_route)
        tokens = self._tokens()
        self._apply_page_theme(tokens)
        parsed = urlparse(requested_route)
        family = route_family(parsed.path)
        self._update_navigation(tokens, self._sidebar_family(family))
        if log_transition:
            self._log(
                "route_transition_requested requested_route=%s previous_route=%s",
                requested_route,
                previous_route,
            )
            self._log(
                "route_query_start requested_route=%s previous_route=%s",
                requested_route,
                previous_route,
            )
        query_started = perf_counter()
        failed = False
        try:
            content = self._page_content(tokens, parsed.path, family)
        except Exception as error:
            failed = True
            content = self._route_error(tokens, error)
        query_complete = perf_counter()
        query_ms = (query_complete - query_started) * 1000
        assert self._content_host is not None
        self._content_host.content = content
        self._refresh_banner(tokens)
        self._set_loading_visible(False)
        render_started = perf_counter()
        self.page.update()
        render_complete = perf_counter()
        render_ms = (render_complete - render_started) * 1000
        total_ms = (render_complete - started) * 1000
        if log_transition:
            self._log(
                "route_query_complete requested_route=%s previous_route=%s elapsed_ms=%.2f failed=%s",
                requested_route,
                previous_route,
                query_ms,
                failed,
            )
            self._log(
                "route_render_complete requested_route=%s previous_route=%s query_ms=%.2f render_ms=%.2f total_ms=%.2f loading_visible=False failed=%s",
                requested_route,
                previous_route,
                query_ms,
                render_ms,
                total_ms,
                failed,
            )
        self.last_route_timing = RouteTiming(
            requested_route=requested_route,
            previous_route=previous_route,
            query_ms=query_ms,
            render_ms=render_ms,
            total_ms=total_ms,
            loading_visible=False,
            failed=failed,
        )

    def _tokens(self) -> ThemeTokens:
        return resolve_tokens(self.state.theme_mode, self._is_system_dark())

    def _apply_page_theme(self, tokens: ThemeTokens) -> None:
        self.page.theme_mode = flet_theme_mode(self.state.theme_mode)
        self.page.bgcolor = tokens.app_background

    def _is_system_dark(self) -> bool:
        return getattr(self.page, "platform_brightness", ft.Brightness.LIGHT) == ft.Brightness.DARK

    @staticmethod
    def _canonical_route(route: str) -> str:
        value = (route or "/dashboard").strip()
        if not value.startswith("/"):
            value = f"/{value}"
        if value == "/":
            return AppRoute.DASHBOARD.value
        return value

    @staticmethod
    def _sidebar_family(family: AppRoute | None) -> AppRoute | None:
        return AppRoute.DASHBOARD if family is AppRoute.DAILY_PLANNING else family

    def _apply_route_selection(self, route: str) -> None:
        parsed = urlparse(route)
        if parsed.path != AppRoute.TASKS:
            return
        selected = parse_qs(parsed.query).get("task")
        if selected:
            try:
                self.state.selected_task_id = int(selected[0])
            except ValueError:
                self.state.selected_task_id = None

    def _sidebar(self, tokens: ThemeTokens, active: AppRoute | None) -> ft.Container:
        collapsed = self.state.sidebar_collapsed
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
                on_click=lambda _e, route=item.route: self.navigate(route.value),
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

    def _rebuild_sidebar(self, tokens: ThemeTokens) -> None:
        if self._sidebar_host is None:
            return
        parsed = urlparse(self.state.route)
        replacement = self._sidebar(tokens, self._sidebar_family(route_family(parsed.path)))
        self._sidebar_host.content = replacement.content
        self._sidebar_host.width = replacement.width
        self._sidebar_host.bgcolor = replacement.bgcolor
        self._sidebar_host.border = replacement.border
        self._sidebar_host.padding = replacement.padding

    def _update_navigation(self, tokens: ThemeTokens, active: AppRoute | None) -> None:
        for route, button in self._nav_buttons.items():
            selected = active is route
            button.bgcolor = tokens.soft_red_background if selected else tokens.app_bar
            button.color = tokens.text_primary
            icon = self._nav_icons[route]
            icon.color = tokens.accent_primary if selected else tokens.text_secondary
            label = self._nav_labels[route]
            label.color = tokens.text_primary if selected else tokens.text_secondary
            label.weight = ft.FontWeight.W_600 if selected else ft.FontWeight.W_400

    def _not_found(self, tokens: ThemeTokens) -> ft.Control:
        return ft.Column([
            ft.Text(ui_text("app.not_found.title"), size=tokens.text_display, color=tokens.text_primary, weight=ft.FontWeight.W_700),
            ft.Text(ui_text("app.not_found.description"), color=tokens.text_secondary),
            ft.Button(ui_text("app.not_found.action"), bgcolor=tokens.accent_primary, color=tokens.on_accent, on_click=lambda _e: self.navigate(AppRoute.DASHBOARD.value)),
        ], spacing=tokens.space_4)

    def _page_content(self, tokens: ThemeTokens, path: str, family: AppRoute | None) -> ft.Control:
        if family is AppRoute.DASHBOARD:
            return build_dashboard(self.services, tokens, self.state.route, self.navigate, self.render, self.report_error)
        if family is AppRoute.DAILY_PLANNING:
            return build_daily_planning(self.services, tokens, self.state.route, self.navigate, self.report_error)
        if family is AppRoute.TASKS:
            return build_tasks(self.services, tokens, self.state, self.render, self.report_error, self.page)
        if family is AppRoute.PROJECTS:
            return build_projects(
                self.services,
                tokens,
                path,
                self.navigate,
                self.render,
                self.report_error,
                self.state,
                self.page,
            )
        if family is AppRoute.CYCLES:
            return build_cycles(
                self.services,
                tokens,
                path,
                self.navigate,
                self.render,
                self.report_error,
                self.state,
                self.page,
            )
        if family is AppRoute.SETTINGS:
            self._settings_narrow = self._is_settings_narrow()
            return build_settings(
                self.services,
                tokens,
                self.apply_settings,
                self.report_error,
                self.state,
                self.page,
            )
        return self._not_found(tokens)

    def _is_settings_narrow(self) -> bool:
        return float(getattr(self.page, "width", 1280) or 1280) < 1180

    def _route_error(self, tokens: ThemeTokens, error: Exception) -> ft.Control:
        error_id = uuid.uuid4().hex[:12]
        self.logger.exception(
            "route_content_failed error_id=%s route=%s error_class=%s",
            error_id,
            self.state.route,
            error.__class__.__name__,
        )
        return ft.Column([
            ft.Text(ui_text("app.route_error.title"), size=tokens.text_title, color=tokens.error.text, weight=ft.FontWeight.W_600),
            ft.Text(ui_text("app.route_error.description"), color=tokens.text_secondary),
            ft.Text(ui_text("app.route_error.id", error_id=error_id), color=tokens.text_muted, size=tokens.text_small),
            ft.Button(ui_text("common.try_again"), on_click=lambda _e: self.render()),
        ], spacing=tokens.space_3)

    def _refresh_banner(self, tokens: ThemeTokens) -> None:
        if self._banner_host is None:
            return
        self._banner_host.controls = []
        if self.state.error_message:
            self._banner_host.controls.append(
                ft.Container(
                    ft.Row([
                        lucide_icon(IconName.ALERT, color=tokens.error.text, size=tokens.icon_medium, label=ui_text("common.error")),
                        ft.Text(self.state.error_message, color=tokens.error.text, expand=True),
                        ft.TextButton(ui_text("common.dismiss"), on_click=lambda _e: self._dismiss_error()),
                    ]),
                    bgcolor=tokens.error.background,
                    border_radius=tokens.radius_medium,
                    padding=tokens.space_3,
                )
            )
        elif self.state.notice_message:
            self._banner_host.controls.append(
                ft.Container(
                    ft.Row([
                        lucide_icon(IconName.CHECK, color=tokens.success.text, size=tokens.icon_medium, label=ui_text("common.success")),
                        ft.Text(self.state.notice_message, color=tokens.success.text, expand=True),
                        ft.TextButton(ui_text("common.dismiss"), on_click=lambda _e: self._dismiss_notice()),
                    ]),
                    bgcolor=tokens.success.background,
                    border=ft.Border.all(tokens.border_width, tokens.success.main),
                    border_radius=tokens.radius_medium,
                    padding=tokens.space_3,
                )
            )

    def _dismiss_error(self) -> None:
        self.state.error_message = None
        self._refresh_banner(self._tokens())
        self.page.update()

    def _dismiss_notice(self) -> None:
        self.state.notice_message = None
        self._refresh_banner(self._tokens())
        self.page.update()

    def _log(self, message: str, *args: object) -> None:
        if self.development:
            self.logger.info(message, *args)


def show_recovery(page: ft.Page, error: Exception, database_path: Path) -> None:
    correlation_id = uuid.uuid4().hex[:12]
    logging.getLogger("overlord").exception(
        "startup_failed error_id=%s error_class=%s", correlation_id, error.__class__.__name__
    )
    tokens = resolve_tokens("light")
    page.title = "Overlord — Recovery"
    page.bgcolor = tokens.app_background
    page.theme = build_light_theme()
    page.dark_theme = build_dark_theme()
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
