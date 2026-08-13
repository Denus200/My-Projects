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

from overlord.app.services import ApplicationServices
from overlord.ui.components.controls import primary_button, secondary_button
from overlord.ui.design_system.themes import build_dark_theme, build_light_theme, flet_theme_mode
from overlord.ui.design_system.tokens import ThemeTokens, resolve_tokens
from overlord.ui.navigation import AppRoute, route_family
from overlord.ui.recovery import build_recovery_view
from overlord.ui.pages.cycles.page import build_cycles
from overlord.ui.pages.projects.page import build_projects
from overlord.ui.pages.dashboard.page import build_dashboard
from overlord.ui.pages.settings.page import build_settings
from overlord.ui.pages.tasks.page import build_tasks
from overlord.ui.state import AppSessionState
from overlord.ui.strings import set_locale, ui_error, ui_text
from overlord.ui.shell.app_shell import AppShell


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
        set_locale(settings.locale)
        self.state = AppSessionState(
            locale=settings.locale,
            theme_mode=settings.theme_mode,
            motion_enabled=settings.motion_enabled,
            reduced_motion=settings.reduced_motion,
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
        self._shell: AppShell | None = None

    def mount(self) -> None:
        if self._mounted:
            return
        self.page.title = ui_text("app.name")
        self.page.padding = 0
        self.page.theme = build_light_theme(motion_enabled=self.state.effective_motion)
        self.page.dark_theme = build_dark_theme(motion_enabled=self.state.effective_motion)
        tokens = self._tokens()
        self._apply_page_theme(tokens)

        self._shell = AppShell(
            tokens,
            self.state.route,
            self.state.sidebar_collapsed,
            self.navigate,
            self.toggle_sidebar,
            self.toggle_language,
        )
        self.page.add(self._shell.control)
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
        if self._shell is not None:
            self._shell.sidebar.update_selection(self._tokens(), requested_route)
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
        assert self._shell is not None
        self._shell.set_content(content)
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
        if self._shell is not None:
            self._shell.sidebar.update_selection(self._tokens(), requested_route)
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
        if self._shell is not None:
            self._shell.set_loading_visible(visible)

    def report_error(self, message: str) -> None:
        self.state.error_message = message
        self.state.notice_message = None
        self._refresh_banner(self._tokens())
        self.page.update()

    def apply_settings(self, settings, notice_message: str | None = None) -> None:
        sidebar_changed = self.state.sidebar_collapsed != settings.sidebar_collapsed
        locale_changed = self.state.locale != settings.locale
        self.state.locale = settings.locale
        set_locale(settings.locale)
        self.state.theme_mode = settings.theme_mode
        self.state.motion_enabled = settings.motion_enabled
        self.state.reduced_motion = settings.reduced_motion
        self.state.sidebar_collapsed = settings.sidebar_collapsed
        self.state.error_message = None
        self.state.notice_message = notice_message
        tokens = self._tokens()
        self.page.theme = build_light_theme(motion_enabled=self.state.effective_motion)
        self.page.dark_theme = build_dark_theme(motion_enabled=self.state.effective_motion)
        self._apply_page_theme(tokens)
        if self._shell is not None:
            if sidebar_changed or locale_changed:
                self._shell.sidebar.rebuild(tokens, self.state.route, self.state.sidebar_collapsed)
            else:
                self._shell.sidebar.update_selection(tokens, self.state.route)
        self.render()

    def toggle_sidebar(self, _event) -> None:
        try:
            updated = self.services.settings.update_settings.execute(
                sidebar_collapsed=not self.state.sidebar_collapsed
            )
            self.state.sidebar_collapsed = updated.sidebar_collapsed
            if self._shell is not None:
                self._shell.sidebar.rebuild(self._tokens(), self.state.route, self.state.sidebar_collapsed)
            self.page.update()
        except Exception as error:
            self.report_error(ui_error(error))

    def toggle_language(self, event) -> None:
        try:
            requested = "ru" if bool(getattr(event.control, "value", False)) else "en"
            updated = self.services.settings.update_settings.execute(locale=requested)
            self.state.locale = updated.locale
            set_locale(updated.locale)
            self.state.error_message = None
            self.state.notice_message = None
            if self._shell is not None:
                self._shell.sidebar.rebuild(self._tokens(), self.state.route, self.state.sidebar_collapsed)
            self.render()
        except Exception as error:
            self.report_error(ui_error(error))

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
        if self._shell is not None:
            self._shell.sidebar.update_selection(tokens, requested_route)
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
        assert self._shell is not None
        self._shell.set_content(content)
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

    def _not_found(self, tokens: ThemeTokens) -> ft.Control:
        return ft.Column([
            ft.Text(ui_text("app.not_found.title"), size=tokens.text_display, color=tokens.text_primary, weight=ft.FontWeight.W_700),
            ft.Text(ui_text("app.not_found.description"), color=tokens.text_secondary),
            primary_button(ui_text("app.not_found.action"), tokens, on_click=lambda _e: self.navigate(AppRoute.DASHBOARD.value)),
        ], spacing=tokens.space_4)

    def _page_content(self, tokens: ThemeTokens, path: str, family: AppRoute | None) -> ft.Control:
        if family is AppRoute.DASHBOARD:
            return build_dashboard(
                self.services,
                tokens,
                self.state.route,
                self.navigate,
                self.render,
                self.report_error,
                self.page,
            )
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
            secondary_button(ui_text("common.try_again"), tokens, on_click=lambda _e: self.render()),
        ], spacing=tokens.space_3)

    def _refresh_banner(self, tokens: ThemeTokens) -> None:
        if self._shell is None:
            return
        if self.state.error_message:
            self._shell.show_error(tokens, self.state.error_message, self._dismiss_error)
        elif self.state.notice_message:
            self._shell.show_notice(tokens, self.state.notice_message, self._dismiss_notice)
        else:
            self._shell.clear_banner()

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
    page.title = ui_text("recovery.page_title")
    page.bgcolor = tokens.app_background
    page.theme = build_light_theme()
    page.dark_theme = build_dark_theme()
    error_message = str(error).lower()
    if "checksum" in error_message or "migration" in error_message or "schema" in error_message:
        category = ui_text("recovery.category.migration")
    elif "corrupt" in error_message or "malformed" in error_message or "integrity" in error_message:
        category = ui_text("recovery.category.integrity")
    elif "locked" in error_message or "busy" in error_message:
        category = ui_text("recovery.category.lock")
    elif error.__class__.__name__ in {"PermissionError", "PermissionDenied"} or "permission" in error_message or "readonly" in error_message:
        category = ui_text("recovery.category.permission")
    else:
        category = ui_text("recovery.category.unexpected")
    page.add(build_recovery_view(
        tokens,
        error_id=correlation_id,
        database_path=str(database_path),
        category=category,
        error_type=error.__class__.__name__,
    ))
