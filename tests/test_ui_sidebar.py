import unittest
from types import SimpleNamespace

import flet as ft

from overlord.ui.design_system.tokens import DARK_TOKENS, LIGHT_TOKENS
from overlord.ui.navigation import NAVIGATION, AppRoute
from overlord.ui.shell.sidebar import Sidebar, _update_from_event


def _event(updates: list[bool], data: object | None = None) -> SimpleNamespace:
    return SimpleNamespace(data=data, control=SimpleNamespace(update=lambda: updates.append(True)))


class SidebarTests(unittest.TestCase):
    def test_late_pointer_event_ignores_a_detector_detached_by_animation(self):
        detached = ft.GestureDetector()
        _update_from_event(SimpleNamespace(control=detached))

    def test_sidebar_constructs_rebuilds_selects_and_dispatches_callbacks(self):
        navigated: list[str] = []
        toggled: list[object] = []
        sidebar = Sidebar(LIGHT_TOKENS, "/projects/42", False, navigated.append, toggled.append)
        host = sidebar.control

        self.assertEqual(232, host.width)
        self.assertIsInstance(host.content, ft.Column)
        self.assertIsNone(host.animate)
        self.assertEqual(420, host.animate_size.duration)
        self.assertEqual(LIGHT_TOKENS.sidebar_border, host.border.right.color)
        self.assertEqual([item.label for item in NAVIGATION], [item.label for item in sidebar._nav_items.values()])
        for item in sidebar._nav_items.values():
            self.assertEqual(231, item.surface.width)
            self.assertEqual(48, item.surface.height)
            self.assertIsNone(item.surface.border)
            self.assertIsInstance(item.surface.content, ft.ListTile)
            self.assertEqual(item.label, item.tile.title)
            self.assertEqual(8, item.tile.horizontal_spacing)
            self.assertEqual(20, item.tile.min_leading_width)
            self.assertEqual(14, item.tile.title_text_style.size)
        self.assertEqual(LIGHT_TOKENS.accent_primary, sidebar._nav_items[AppRoute.PROJECTS].surface.bgcolor)
        self.assertEqual(LIGHT_TOKENS.on_accent, sidebar._nav_items[AppRoute.PROJECTS].tile.text_color)

        sidebar._nav_items[AppRoute.DASHBOARD].control.on_tap(_event([]))
        sidebar._header_action.control.on_tap("collapse")
        self.assertEqual([AppRoute.DASHBOARD.value], navigated)
        self.assertEqual(["collapse"], toggled)
        self.assertEqual(ft.Colors.TRANSPARENT, sidebar._header_action.surface.bgcolor)
        self.assertIsNone(sidebar._header_action.surface.border)

        sidebar.update_selection(LIGHT_TOKENS, AppRoute.DASHBOARD.value)
        dashboard = sidebar._nav_items[AppRoute.DASHBOARD]
        projects = sidebar._nav_items[AppRoute.PROJECTS]
        self.assertEqual(LIGHT_TOKENS.accent_primary, dashboard.surface.bgcolor)
        self.assertEqual(LIGHT_TOKENS.on_accent, dashboard.icon.color)
        self.assertEqual(LIGHT_TOKENS.app_bar, projects.surface.bgcolor)
        updates: list[bool] = []
        projects.control.on_enter(_event(updates))
        self.assertEqual(LIGHT_TOKENS.interactive_selected, projects.surface.bgcolor)
        self.assertIsNone(projects.surface.border)
        projects.control.on_tap_down(_event(updates))
        self.assertEqual(LIGHT_TOKENS.interactive_pressed, projects.surface.bgcolor)

        sidebar.rebuild(DARK_TOKENS, "/cycles/7", True)
        self.assertIs(host, sidebar.control)
        self.assertEqual(56, host.width)
        for item in sidebar._nav_items.values():
            self.assertEqual(44, item.surface.width)
            self.assertEqual(44, item.surface.height)
            self.assertEqual(1, len(item.surface.content.controls))
            self.assertIsNone(item.tile)
        cycles = sidebar._nav_items[AppRoute.CYCLES]
        settings = sidebar._nav_items[AppRoute.SETTINGS]
        self.assertEqual(DARK_TOKENS.accent_primary, cycles.surface.bgcolor)
        self.assertEqual(DARK_TOKENS.sidebar_active_border, cycles.surface.border.top.color)
        self.assertEqual(DARK_TOKENS.app_bar, settings.surface.bgcolor)
        self.assertIsNone(settings.surface.border)
        settings.control.on_enter(_event([]))
        self.assertEqual(DARK_TOKENS.sidebar_hover_border, settings.surface.border.top.color)

        header = sidebar._header_action
        self.assertEqual(ft.Colors.TRANSPARENT, header.surface.bgcolor)
        self.assertIsNone(header.surface.border)
        self.assertTrue(header.logo.visible)
        self.assertFalse(header.icon.visible)
        header.control.on_enter(_event([]))
        self.assertFalse(header.logo.visible)
        self.assertTrue(header.icon.visible)
        self.assertEqual(DARK_TOKENS.interactive_hover, header.surface.bgcolor)
        header.control.on_exit(_event([]))
        self.assertTrue(header.logo.visible)
        self.assertFalse(header.icon.visible)
        header.control.on_tap("expand")
        self.assertEqual(["collapse", "expand"], toggled)

        language = sidebar._language_toggle
        self.assertEqual("sidebar-language-toggle", language.control.data)
        self.assertEqual(56, language.control.width)
        self.assertEqual(32, language.control.height)
        self.assertEqual(24, language.thumb.width)
        self.assertEqual(24, language.thumb.height)
        self.assertEqual(12, language.thumb.border_radius)
        language.control.on_enter(_event([]))
        self.assertEqual(20, language.thumb.width)
        self.assertEqual(20, language.thumb.height)
        self.assertEqual(10, language.thumb.border_radius)

    def test_header_toggle_updates_before_replacing_its_mounted_control_tree(self):
        sidebar: Sidebar
        old_header = None
        updates: list[bool] = []

        def toggle(_event: object) -> None:
            sidebar.rebuild(LIGHT_TOKENS, AppRoute.DASHBOARD.value, True)

        sidebar = Sidebar(LIGHT_TOKENS, AppRoute.DASHBOARD.value, False, lambda _route: None, toggle)
        old_header = sidebar._header_action

        def guarded_update() -> None:
            if sidebar._header_action is not old_header:
                raise RuntimeError("detached control updated after sidebar rebuild")
            updates.append(True)

        old_header.control.on_tap(SimpleNamespace(control=SimpleNamespace(update=guarded_update)))

        self.assertEqual([True], updates)
        self.assertEqual(56, sidebar.control.width)
        self.assertIsNot(old_header, sidebar._header_action)


if __name__ == "__main__":
    unittest.main()
