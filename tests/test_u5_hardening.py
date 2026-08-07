from __future__ import annotations

import asyncio
import hashlib
import unittest
import uuid
from pathlib import Path
from types import SimpleNamespace

import flet as ft

from overlord.bootstrap import DEFAULT_DATABASE_PATH, bootstrap
from overlord.presentation.app import OverlordApp
from overlord.presentation.design_system.tokens import LIGHT_TOKENS
from overlord.presentation.pages.settings import build_settings
from overlord.presentation.state import AppSessionState
from overlord.presentation.strings import ENGLISH_STRINGS, ui_text


ROOT = Path(__file__).resolve().parents[1]
TEST_TEMP_ROOT = ROOT / "data" / "test-tmp"
TEST_TEMP_ROOT.mkdir(parents=True, exist_ok=True)


def _hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(128 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


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


def _by_data(control, value: str):
    return next(item for item in _walk(control) if getattr(item, "data", None) == value)


class FakePage:
    def __init__(self, route: str = "/settings", width: int = 1600):
        self.route = route
        self.width = width
        self.web = False
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


class U5HardeningTests(unittest.TestCase):
    def setUp(self):
        self.path = TEST_TEMP_ROOT / f"u5-{uuid.uuid4().hex}.db"
        self.services = bootstrap(self.path).services

    def tearDown(self):
        self.path.unlink(missing_ok=True)
        for suffix in ("-wal", "-shm", ".seed.json"):
            Path(f"{self.path}{suffix}").unlink(missing_ok=True)

    def _settings(self, *, width: int = 1600, state: AppSessionState | None = None):
        page = FakePage(width=width)
        session = state or AppSessionState(route="/settings")
        applied = []
        control = build_settings(
            self.services,
            LIGHT_TOKENS,
            lambda settings, notice=None: applied.append((settings, notice)),
            self.fail,
            session,
            page,
        )
        return control, session, page, applied

    def test_settings_is_categorized_and_does_not_advertise_future_widget(self):
        control, _state, _page, _applied = self._settings()
        visible = " ".join(_texts(control))
        self.assertIn(ui_text("settings.category.appearance"), visible)
        self.assertIn(ui_text("settings.category.planning"), visible)
        self.assertIn(ui_text("settings.category.startup"), visible)
        self.assertNotIn("Future Widget", visible)
        self.assertNotIn("coming soon", visible.lower())

    def test_settings_category_selection_persists_across_rebuild(self):
        state = AppSessionState(route="/settings")
        control, state, _page, _applied = self._settings(state=state)
        _by_data(control, "settings-category-planning").on_click(None)
        self.assertEqual("planning", state.settings_category)
        rebuilt, _state, _page, _applied = self._settings(state=state)
        self.assertEqual("planning", state.settings_category)
        self.assertIn(ui_text("settings.planning.description"), _texts(rebuilt))

    def test_narrow_settings_uses_compact_category_selector(self):
        control, _state, _page, _applied = self._settings(width=1024)
        selector = next(
            item for item in _walk(control)
            if isinstance(item, ft.Dropdown) and item.label == ui_text("settings.category")
        )
        rail = next(item for item in _walk(control) if getattr(item, "width", None) == 214)
        self.assertTrue(selector.visible)
        self.assertFalse(rail.visible)

    def test_settings_has_no_wrapped_row_with_expanded_child(self):
        control, _state, _page, _applied = self._settings()
        for item in _walk(control):
            if isinstance(item, ft.Row) and item.wrap:
                self.assertFalse(
                    any(bool(getattr(child, "expand", False)) for child in item.controls),
                    "Flet cannot lay out an expanded child inside a wrapping Row",
                )

    def test_theme_planning_and_startup_preferences_save_together(self):
        control, _state, _page, applied = self._settings()
        _by_data(control, "settings-theme-dark").on_click(None)
        settings = self.services.settings.get_settings.execute()
        self.assertEqual("system", settings.theme_mode)
        save = next(item for item in _walk(control) if getattr(item, "content", None) == ui_text("settings.save"))
        save.on_click(None)
        self.assertEqual(1, len(applied))
        self.assertEqual("dark", applied[0][0].theme_mode)
        self.assertEqual(ui_text("settings.saved"), applied[0][1])

    def test_theme_update_keeps_shell_mounted_and_shows_success(self):
        page = FakePage()
        app = OverlordApp(page, self.services)
        app.mount()
        shell = page.controls[0]
        updated = self.services.settings.update_settings.execute(theme_mode="dark")
        app.apply_settings(updated, ui_text("settings.saved"))
        self.assertIs(shell, page.controls[0])
        self.assertEqual(1, page.add_count)
        self.assertEqual("dark", app.state.theme_mode)
        self.assertIn(ui_text("settings.saved"), _texts(app._banner_host))

    def test_settings_crossing_narrow_breakpoint_reuses_shell(self):
        page = FakePage(width=1600)
        app = OverlordApp(page, self.services)
        app.mount()
        shell = page.controls[0]
        self.assertFalse(app._settings_narrow)

        page.width = 1024
        page.on_resize(None)

        self.assertTrue(app._settings_narrow)
        self.assertIs(shell, page.controls[0])
        self.assertEqual(1, page.add_count)

    def test_startup_destination_remains_valid_and_persistent(self):
        self.services.settings.update_settings.execute(startup_destination="projects")
        page = FakePage(route="/")
        app = OverlordApp(page, self.services)
        app.mount()
        self.assertEqual("/projects", app.state.route)
        self.assertEqual("projects", self.services.settings.get_settings.execute().startup_destination)

    def test_presentation_catalog_has_no_known_mojibake(self):
        presentation = "\n".join(
            path.read_text(encoding="utf-8") for path in (ROOT / "overlord" / "presentation").rglob("*.py")
        )
        for broken in ("РІР‚вЂњ", "Р’В·", "вЂ™", "вЂ“"):
            self.assertNotIn(broken, presentation)
        self.assertEqual("Today’s Tasks", ui_text("dashboard.today.title"))
        self.assertEqual("3 Primary · 4 Secondary", ui_text("dashboard.today.capacity"))

    def test_u5_visible_settings_copy_is_centralized(self):
        settings_source = (ROOT / "overlord" / "presentation" / "pages" / "settings.py").read_text(encoding="utf-8")
        for visible in ("Motion enabled", "Reduced motion", "Future Widget", "Save Settings"):
            self.assertNotIn(f'"{visible}"', settings_source)
        self.assertEqual("Settings", ENGLISH_STRINGS["settings.title"])

    def test_u5_disposable_work_does_not_touch_production_database(self):
        before = _hash(DEFAULT_DATABASE_PATH)
        self.services.settings.update_settings.execute(theme_mode="dark", startup_destination="cycles")
        self.assertEqual(before, _hash(DEFAULT_DATABASE_PATH))


if __name__ == "__main__":
    unittest.main()
