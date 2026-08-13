from __future__ import annotations

from collections.abc import Callable
from types import SimpleNamespace
from urllib.parse import urlparse

import flet as ft

from overlord.ui.design_system.assets import brand_mark
from overlord.ui.design_system.icons import IconName, lucide_icon
from overlord.ui.design_system.tokens import ThemeTokens
from overlord.ui.navigation import NAVIGATION, AppRoute, route_family
from overlord.ui.strings import get_locale, ui_text


def _update_from_event(event: object) -> None:
    control = getattr(event, "control", None)
    # Pointer events can finish after a Sidebar rebuild has detached the old
    # control tree. Flet deliberately rejects updates on such controls.
    if isinstance(control, ft.Control):
        try:
            control.page
        except RuntimeError as error:
            if "Control must be added to the page first" in str(error):
                return
            raise
    update = getattr(control, "update", None)
    if callable(update):
        update()


class _NavigationControl:
    def __init__(
        self,
        tokens: ThemeTokens,
        *,
        route: AppRoute,
        label: str,
        icon_name: IconName,
        selected: bool,
        collapsed: bool,
        on_activate: Callable[[str], None],
    ) -> None:
        self.tokens = tokens
        self.route = route
        self.selected = selected
        self.collapsed = collapsed
        self.hovered = False
        self.pressed = False
        self.disabled = False
        self._on_activate = on_activate
        size = Sidebar.COLLAPSED_ITEM_SIZE if collapsed else Sidebar.EXPANDED_ITEM_HEIGHT
        width = Sidebar.COLLAPSED_ITEM_SIZE if collapsed else Sidebar.EXPANDED_WIDTH - tokens.border_width
        self.icon = lucide_icon(icon_name, color=tokens.sidebar_foreground, size=tokens.icon_medium, label=label)
        self.label = label
        self.tile: ft.ListTile | None = None
        if collapsed:
            content: ft.Control = ft.Row(
                [self.icon],
                tight=True,
                alignment=ft.MainAxisAlignment.CENTER,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            )
        else:
            self.tile = ft.ListTile(
                title=label,
                leading=self.icon,
                content_padding=ft.Padding.symmetric(horizontal=tokens.space_4),
                horizontal_spacing=tokens.space_2,
                min_leading_width=tokens.icon_medium,
                min_vertical_padding=tokens.space_0,
                dense=True,
                min_height=size,
                text_color=tokens.sidebar_foreground,
                icon_color=tokens.sidebar_foreground,
                title_text_style=ft.TextStyle(
                    size=tokens.text_body,
                    height=1.2,
                    weight=ft.FontWeight.W_400,
                    color=tokens.sidebar_foreground,
                ),
                width=width,
                height=size,
            )
            content = self.tile
        self.surface = ft.Container(
            content,
            width=width,
            height=size,
            alignment=ft.Alignment.CENTER if collapsed else ft.Alignment.CENTER_LEFT,
            padding=tokens.space_0,
            border_radius=tokens.space_2 if collapsed else tokens.space_0,
            animate=ft.Animation(tokens.motion_fast, ft.AnimationCurve.EASE_OUT_CUBIC),
        )
        self.control = ft.GestureDetector(
            self.surface,
            width=width,
            height=size,
            mouse_cursor=ft.MouseCursor.CLICK,
            tooltip=label,
            data=f"sidebar-nav-{route.value}",
            on_enter=self._enter,
            on_exit=self._exit,
            on_tap_down=self._tap_down,
            on_tap_up=self._tap_up,
            on_tap_cancel=self._tap_cancel,
            on_tap=self._tap,
        )
        self.semantic = ft.Semantics(
            content=self.control,
            label=label,
            button=True,
            focusable=True,
            selected=selected,
            on_tap=lambda _event=None: self._activate(),
        )
        self._refresh()

    def set_selected(self, selected: bool) -> None:
        self.selected = selected
        self.semantic.selected = selected
        self._refresh()

    def _refresh(self) -> None:
        tokens = self.tokens
        if self.selected:
            background = (
                tokens.accent_primary_pressed
                if self.pressed
                else tokens.accent_primary_hover if self.hovered else tokens.accent_primary
            )
            foreground = tokens.on_accent
        else:
            background = (
                tokens.interactive_pressed
                if self.pressed
                else tokens.interactive_selected if self.hovered else tokens.app_bar
            )
            foreground = tokens.sidebar_foreground
        self.surface.bgcolor = background
        self.surface.opacity = 0.5 if self.disabled else 1.0
        if self.collapsed and self.selected:
            self.surface.border = ft.Border.all(tokens.border_width, tokens.sidebar_active_border)
        elif self.collapsed and self.hovered:
            self.surface.border = ft.Border.all(tokens.border_width, tokens.sidebar_hover_border)
        else:
            self.surface.border = None
        self.icon.color = foreground
        if self.tile is not None:
            self.tile.text_color = foreground
            self.tile.icon_color = foreground
            if self.tile.title_text_style is not None:
                self.tile.title_text_style.color = foreground

    def _enter(self, event: object) -> None:
        self.hovered = True
        self._refresh()
        _update_from_event(event)

    def _exit(self, event: object) -> None:
        self.hovered = False
        self.pressed = False
        self._refresh()
        _update_from_event(event)

    def _tap_down(self, event: object) -> None:
        self.pressed = True
        self._refresh()
        _update_from_event(event)

    def _tap_up(self, event: object) -> None:
        self.pressed = False
        self._refresh()
        _update_from_event(event)

    def _tap_cancel(self, event: object) -> None:
        self.pressed = False
        self._refresh()
        _update_from_event(event)

    def _tap(self, event: object) -> None:
        _update_from_event(event)
        self._activate()

    def _activate(self) -> None:
        if not self.disabled:
            self._on_activate(self.route.value)


class _HeaderAction:
    def __init__(
        self,
        tokens: ThemeTokens,
        *,
        collapsed: bool,
        on_activate: Callable[[object], None],
    ) -> None:
        self.tokens = tokens
        self.collapsed = collapsed
        self.hovered = False
        self.pressed = False
        self._on_activate = on_activate
        label = ui_text("nav.expand_sidebar") if collapsed else ui_text("nav.collapse_sidebar")
        if collapsed:
            self.logo = brand_mark(color=tokens.accent_primary, size=32)
            self.icon = lucide_icon(
                IconName.EXPAND,
                color=tokens.sidebar_foreground,
                size=tokens.icon_medium,
                label=label,
            )
            self.icon.visible = False
            content: ft.Control = ft.Stack(
                [self.logo, self.icon],
                width=48,
                height=48,
                alignment=ft.Alignment.CENTER,
            )
        else:
            self.logo = None
            self.icon = lucide_icon(
                IconName.COLLAPSE,
                color=tokens.sidebar_foreground,
                size=tokens.icon_medium,
                label=label,
            )
            content = self.icon
        self.surface = ft.Container(
            content,
            width=48,
            height=48,
            alignment=ft.Alignment.CENTER,
            bgcolor=ft.Colors.TRANSPARENT,
            border=None,
            border_radius=tokens.space_3,
            animate=ft.Animation(tokens.motion_fast, ft.AnimationCurve.EASE_OUT_CUBIC),
        )
        self.control = ft.GestureDetector(
            self.surface,
            width=48,
            height=48,
            mouse_cursor=ft.MouseCursor.CLICK,
            tooltip=label,
            data="sidebar-expand" if collapsed else "sidebar-collapse",
            on_enter=self._enter,
            on_exit=self._exit,
            on_tap_down=self._tap_down,
            on_tap_up=self._tap_up,
            on_tap_cancel=self._tap_cancel,
            on_tap=self._tap,
        )
        self.semantic = ft.Semantics(
            content=self.control,
            label=label,
            button=True,
            focusable=True,
            on_tap=lambda _event=None: self._on_activate(None),
        )

    def _refresh(self) -> None:
        self.surface.bgcolor = (
            self.tokens.interactive_selected
            if self.pressed
            else self.tokens.interactive_hover if self.hovered else ft.Colors.TRANSPARENT
        )
        self.surface.border = None
        if self.collapsed and self.logo is not None:
            self.logo.visible = not self.hovered
            self.icon.visible = self.hovered

    def _enter(self, event: object) -> None:
        self.hovered = True
        self._refresh()
        _update_from_event(event)

    def _exit(self, event: object) -> None:
        self.hovered = False
        self.pressed = False
        self._refresh()
        _update_from_event(event)

    def _tap_down(self, event: object) -> None:
        self.pressed = True
        self._refresh()
        _update_from_event(event)

    def _tap_up(self, event: object) -> None:
        self.pressed = False
        self._refresh()
        _update_from_event(event)

    def _tap_cancel(self, event: object) -> None:
        self.pressed = False
        self._refresh()
        _update_from_event(event)

    def _tap(self, event: object) -> None:
        # The callback may rebuild the sidebar and detach this detector. Never
        # update the old control after handing lifecycle ownership to the app.
        _update_from_event(event)
        self._on_activate(event)


class _LanguageToggle:
    def __init__(
        self,
        tokens: ThemeTokens,
        *,
        value: bool,
        on_change: Callable[[object], None],
    ) -> None:
        self.tokens = tokens
        self.value = value
        self.hovered = False
        self.pressed = False
        self._on_change = on_change
        self.thumb = ft.Container(
            width=24,
            height=24,
            bgcolor=tokens.on_accent,
            border_radius=12,
            animate_size=ft.Animation(tokens.motion_fast, ft.AnimationCurve.EASE_OUT_CUBIC),
        )
        self.track = ft.Container(
            self.thumb,
            width=56,
            height=32,
            padding=tokens.space_1,
            alignment=ft.Alignment.CENTER_RIGHT if value else ft.Alignment.CENTER_LEFT,
            border_radius=16,
            border=None,
            animate=ft.Animation(tokens.motion_fast, ft.AnimationCurve.EASE_OUT_CUBIC),
            animate_align=ft.Animation(tokens.motion_fast, ft.AnimationCurve.EASE_IN_OUT_CUBIC),
        )
        self.control = ft.GestureDetector(
            self.track,
            width=56,
            height=32,
            mouse_cursor=ft.MouseCursor.CLICK,
            tooltip=ui_text("nav.language.tooltip"),
            data="sidebar-language-toggle",
            on_enter=self._enter,
            on_exit=self._exit,
            on_tap_down=self._tap_down,
            on_tap_up=self._tap_up,
            on_tap_cancel=self._tap_cancel,
            on_tap=self._tap,
        )
        self.control.value = value
        self.control.on_change = on_change
        self._refresh()

    def _refresh(self) -> None:
        tokens = self.tokens
        self.track.bgcolor = (
            tokens.accent_primary_pressed
            if self.value and self.pressed
            else tokens.accent_primary
            if self.value
            else tokens.toggle_track_pressed
            if self.pressed
            else tokens.toggle_track_hover
            if self.hovered
            else tokens.toggle_track_default
        )
        compact_thumb = self.hovered or self.pressed
        self.thumb.width = 20 if compact_thumb else 24
        self.thumb.height = 20 if compact_thumb else 24
        self.thumb.border_radius = 10 if compact_thumb else 12
        self.track.padding = tokens.space_2 if compact_thumb else tokens.space_1
        self.track.alignment = ft.Alignment.CENTER_RIGHT if self.value else ft.Alignment.CENTER_LEFT
        self.track.border = None

    def _enter(self, event: object) -> None:
        self.hovered = True
        self._refresh()
        _update_from_event(event)

    def _exit(self, event: object) -> None:
        self.hovered = False
        self.pressed = False
        self._refresh()
        _update_from_event(event)

    def _tap_down(self, event: object) -> None:
        self.pressed = True
        self._refresh()
        _update_from_event(event)

    def _tap_up(self, event: object) -> None:
        self.pressed = False
        self._refresh()
        _update_from_event(event)

    def _tap_cancel(self, event: object) -> None:
        self.pressed = False
        self._refresh()
        _update_from_event(event)

    def _tap(self, event: object) -> None:
        self.pressed = False
        self.value = not self.value
        self.control.value = self.value
        self._refresh()
        _update_from_event(event)
        self._on_change(SimpleNamespace(control=self.control))


class Sidebar:
    EXPANDED_WIDTH = 232
    COLLAPSED_WIDTH = 56
    EXPANDED_ITEM_HEIGHT = 48
    COLLAPSED_ITEM_SIZE = 44
    TRANSITION_DURATION = 420

    def __init__(
        self,
        tokens: ThemeTokens,
        current_route: str,
        collapsed: bool,
        on_navigate: Callable[[str], None],
        on_toggle: Callable[[object], None],
        on_toggle_language: Callable[[object], None] | None = None,
    ) -> None:
        self._on_navigate = on_navigate
        self._on_toggle = on_toggle
        self._on_toggle_language = on_toggle_language or (lambda _event: None)
        self._nav_items: dict[AppRoute, _NavigationControl] = {}
        self._nav_icons: dict[AppRoute, ft.Image] = {}
        self._nav_labels: dict[AppRoute, str] = {}
        self._header_action: _HeaderAction | None = None
        self._language_toggle: _LanguageToggle | None = None
        self.control = self._build(tokens, self._active_route(current_route), collapsed)

    def rebuild(self, tokens: ThemeTokens, current_route: str, collapsed: bool) -> None:
        replacement = self._build(tokens, self._active_route(current_route), collapsed)
        self.control.content = replacement.content
        self.control.width = replacement.width
        self.control.bgcolor = replacement.bgcolor
        self.control.border = replacement.border
        self.control.padding = replacement.padding
        self.control.clip_behavior = replacement.clip_behavior

    def update_selection(self, tokens: ThemeTokens, current_route: str) -> None:
        active = self._active_route(current_route)
        for route, item in self._nav_items.items():
            item.tokens = tokens
            item.set_selected(active is route)

    @staticmethod
    def _active_route(current_route: str) -> AppRoute | None:
        return route_family(urlparse(current_route).path)

    def _header(self, tokens: ThemeTokens, collapsed: bool) -> ft.Control:
        self._header_action = _HeaderAction(tokens, collapsed=collapsed, on_activate=self._on_toggle)
        if collapsed:
            return self._header_action.semantic
        return ft.Container(
            ft.Row(
                [brand_mark(color=tokens.accent_primary, size=48), self._header_action.semantic],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            height=48,
            padding=ft.Padding.symmetric(horizontal=tokens.space_4),
        )

    def _navigation(self, tokens: ThemeTokens, active: AppRoute | None, collapsed: bool) -> ft.Column:
        controls: list[ft.Control] = []
        for navigation_item in NAVIGATION:
            item = _NavigationControl(
                tokens,
                route=navigation_item.route,
                label=navigation_item.label,
                icon_name=navigation_item.icon,
                selected=active is navigation_item.route,
                collapsed=collapsed,
                on_activate=self._on_navigate,
            )
            self._nav_items[navigation_item.route] = item
            self._nav_icons[navigation_item.route] = item.icon
            self._nav_labels[navigation_item.route] = item.label
            controls.append(item.semantic)
        return ft.Column(
            controls,
            spacing=tokens.space_2 if collapsed else tokens.space_0,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER if collapsed else ft.CrossAxisAlignment.STRETCH,
        )

    def _language_control(self, tokens: ThemeTokens, collapsed: bool) -> ft.Control:
        self._language_toggle = _LanguageToggle(
            tokens,
            value=get_locale() == "ru",
            on_change=self._on_toggle_language,
        )
        if collapsed:
            return self._language_toggle.control
        return ft.Column(
            [
                ft.Text(ui_text("nav.language"), color=tokens.text_muted, size=tokens.text_small),
                ft.Row(
                    [
                        ft.Text("EN", color=tokens.sidebar_foreground, size=tokens.text_small),
                        self._language_toggle.control,
                        ft.Text("RU", color=tokens.sidebar_foreground, size=tokens.text_small),
                    ],
                    spacing=tokens.space_1,
                    alignment=ft.MainAxisAlignment.CENTER,
                ),
            ],
            spacing=tokens.space_1,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        )

    def _build(self, tokens: ThemeTokens, active: AppRoute | None, collapsed: bool) -> ft.Container:
        self._nav_items.clear()
        self._nav_icons.clear()
        self._nav_labels.clear()
        width = self.COLLAPSED_WIDTH if collapsed else self.EXPANDED_WIDTH
        top_group = ft.Column(
            [self._header(tokens, collapsed), self._navigation(tokens, active, collapsed)],
            spacing=tokens.space_6,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER if collapsed else ft.CrossAxisAlignment.STRETCH,
        )
        content = ft.Column(
            [top_group, ft.Container(expand=True), self._language_control(tokens, collapsed)],
            key=f"sidebar-{'collapsed' if collapsed else 'expanded'}",
            spacing=tokens.space_0,
            expand=True,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER if collapsed else ft.CrossAxisAlignment.STRETCH,
        )
        return ft.Container(
            content,
            width=width,
            bgcolor=tokens.app_bar,
            border=ft.Border.only(right=ft.BorderSide(tokens.border_width, tokens.sidebar_border)),
            padding=ft.Padding.symmetric(vertical=tokens.space_4),
            clip_behavior=ft.ClipBehavior.HARD_EDGE,
            animate_size=ft.Animation(self.TRANSITION_DURATION, ft.AnimationCurve.EASE_IN_OUT_SINE),
        )
