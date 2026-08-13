from __future__ import annotations

import asyncio
from string import Formatter
from types import SimpleNamespace
import unittest
import uuid
from pathlib import Path
from urllib.parse import urlparse

import flet as ft

from overlord.bootstrap import bootstrap
from overlord.ui.app import OverlordApp
from overlord.ui.locales import RUSSIAN_STRINGS
from overlord.ui.navigation import route_family
from overlord.ui.strings import ENGLISH_STRINGS, format_long_date, get_locale, set_locale, ui_text


TEST_TEMP_ROOT = Path(__file__).resolve().parents[1] / "data" / "test-tmp"
TEST_TEMP_ROOT.mkdir(parents=True, exist_ok=True)


def _walk(control):
    if control is None:
        return
    yield control
    content = getattr(control, "content", None)
    if isinstance(content, ft.Control):
        yield from _walk(content)
    for attribute in ("controls", "actions"):
        for child in getattr(control, attribute, ()) or ():
            if isinstance(child, ft.Control):
                yield from _walk(child)


def _texts(control) -> list[str]:
    values: list[str] = []
    for item in _walk(control):
        for attribute in ("value", "text", "label", "tooltip"):
            value = getattr(item, attribute, None)
            if isinstance(value, str):
                values.append(value)
        if isinstance(getattr(item, "content", None), str):
            values.append(item.content)
    return values


def _fields(template: str) -> set[str]:
    return {name for _literal, name, _format, _conversion in Formatter().parse(template) if name}


class FakePage:
    def __init__(self, route: str = "/dashboard"):
        self.route = route
        self.width = 1600
        self.controls: list[ft.Control] = []
        self.add_count = 0
        self.update_count = 0
        self.platform_brightness = ft.Brightness.LIGHT
        self.title = ""
        self.padding = 0
        self.theme = None
        self.dark_theme = None
        self.theme_mode = None
        self.bgcolor = None
        self.on_route_change = None
        self.on_resize = None

    def add(self, *controls):
        self.add_count += 1
        self.controls.extend(controls)

    def update(self):
        self.update_count += 1

    def run_task(self, handler, *args):
        return asyncio.run(handler(*args))

    async def push_route(self, route: str):
        self.route = route
        if self.on_route_change:
            await self.on_route_change(SimpleNamespace(route=route))


class LocalizationTests(unittest.TestCase):
    def setUp(self):
        set_locale("en")
        self.path = TEST_TEMP_ROOT / f"localization-{uuid.uuid4().hex}.db"
        self.services = bootstrap(self.path).services

    def tearDown(self):
        set_locale("en")
        self.path.unlink(missing_ok=True)
        for suffix in ("-wal", "-shm", ".seed.json"):
            Path(f"{self.path}{suffix}").unlink(missing_ok=True)

    def test_catalogs_have_identical_keys_and_placeholders(self):
        self.assertEqual(set(ENGLISH_STRINGS), set(RUSSIAN_STRINGS))
        for key, english in ENGLISH_STRINGS.items():
            self.assertEqual(_fields(english), _fields(RUSSIAN_STRINGS[key]), key)

    def test_locale_defaults_to_english_and_persists(self):
        self.assertEqual("en", self.services.settings.get_settings.execute().locale)
        updated = self.services.settings.update_settings.execute(locale="ru")
        self.assertEqual("ru", updated.locale)
        self.assertEqual("ru", self.services.settings.get_settings.execute().locale)
        with self.assertRaises(ValueError):
            self.services.settings.update_settings.execute(locale="uk")

    def test_language_switch_rebuilds_current_page_without_remounting_shell(self):
        page = FakePage()
        app = OverlordApp(page, self.services)
        app.mount()
        shell = page.controls[0]
        switch = next(item for item in _walk(shell) if getattr(item, "data", None) == "sidebar-language-toggle")

        switch.value = True
        switch.on_change(SimpleNamespace(control=switch))

        self.assertEqual("ru", get_locale())
        self.assertEqual("ru", app.state.locale)
        self.assertEqual("ru", self.services.settings.get_settings.execute().locale)
        self.assertIs(shell, page.controls[0])
        self.assertEqual(1, page.add_count)
        self.assertIn("Задачи", _texts(shell))
        self.assertIn("Обзор", _texts(shell))

    def test_russian_catalog_and_dates_render_immediately(self):
        set_locale("ru")
        self.assertEqual("Настройки", ui_text("settings.title"))
        self.assertEqual("Понедельник, 10 августа", format_long_date(__import__("datetime").date(2026, 8, 10)))

    def test_every_current_route_constructs_in_russian(self):
        self.services.settings.update_settings.execute(locale="ru")
        app = OverlordApp(FakePage(), self.services)
        tokens = app._tokens()
        routes = (
            "/dashboard",
            "/tasks",
            "/projects",
            "/projects/1",
            "/cycles",
            "/cycles/new",
            "/cycles/1",
            "/settings",
        )
        for route in routes:
            parsed = urlparse(route)
            with self.subTest(route=route):
                control = app._page_content(tokens, parsed.path, route_family(parsed.path))
                self.assertIsInstance(control, ft.Control)


if __name__ == "__main__":
    unittest.main()
