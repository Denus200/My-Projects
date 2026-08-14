import unittest

import flet as ft

from overlord.ui.design_system.tokens import DARK_TOKENS, LIGHT_TOKENS
from overlord.ui.shell.app_shell import AppShell


def _texts(control: ft.Control) -> list[str]:
    values: list[str] = []
    value = getattr(control, "value", None)
    if isinstance(value, str):
        values.append(value)
    content = getattr(control, "content", None)
    if content is not None:
        values.extend(_texts(content))
    for child in getattr(control, "controls", ()) or ():
        values.extend(_texts(child))
    return values


class AppShellTests(unittest.TestCase):
    def test_shell_preserves_controls_and_displays_supplied_state(self):
        navigated: list[str] = []
        toggled: list[object] = []
        dismissed: list[str] = []
        shell = AppShell(LIGHT_TOKENS, "/dashboard", False, navigated.append, toggled.append)
        root = shell.control
        sidebar_control = shell.sidebar.control
        content_host = shell.content_host

        self.assertIs(sidebar_control, root.controls[0])
        self.assertEqual(232, sidebar_control.width)
        first = ft.Text("First route")
        second = ft.Text("Second route")
        shell.set_content(first)
        self.assertEqual(24, shell.body.padding)
        global_page = ft.ListView(
            data={"role": "global-page-container", "layout": "global-page", "page": "dashboard"},
            padding=ft.Padding.symmetric(horizontal=24, vertical=16),
        )
        shell.set_content(global_page)
        self.assertEqual(0, shell.body.padding)
        shell.set_content(second)
        self.assertEqual(24, shell.body.padding)
        self.assertIs(root, shell.control)
        self.assertIs(content_host, shell.content_host)
        self.assertIs(second, content_host.content)

        shell.set_loading_visible(True)
        self.assertTrue(shell.loading_indicator.visible)
        shell.set_loading_visible(False)
        self.assertFalse(shell.loading_indicator.visible)

        shell.show_error(LIGHT_TOKENS, "Error message", lambda: dismissed.append("error"))
        self.assertTrue(shell.banner_host.visible)
        self.assertIn("Error message", _texts(shell.banner_host))
        shell.banner_host.controls[0].content.controls[-1].on_click(None)
        shell.show_notice(LIGHT_TOKENS, "Notice message", lambda: dismissed.append("notice"))
        self.assertIn("Notice message", _texts(shell.banner_host))
        shell.banner_host.controls[0].content.controls[-1].on_click(None)
        self.assertEqual(["error", "notice"], dismissed)
        shell.clear_banner()
        self.assertEqual([], shell.banner_host.controls)
        self.assertFalse(shell.banner_host.visible)

        shell.sidebar.rebuild(DARK_TOKENS, "/cycles/2", True)
        self.assertIs(root, shell.control)
        self.assertIs(sidebar_control, shell.sidebar.control)
        self.assertEqual(56, sidebar_control.width)


if __name__ == "__main__":
    unittest.main()
