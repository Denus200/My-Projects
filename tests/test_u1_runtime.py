from __future__ import annotations

import asyncio
import hashlib
import time
import unittest
import uuid
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

import flet as ft

import main as main_module
from overlord.bootstrap import DEFAULT_DATABASE_PATH, bootstrap
from overlord.demo import DEMO_DATABASE_PATH, demo_seed_fingerprint, ensure_demo_database, seed_demo_database
from overlord.presentation.app import OverlordApp


TEST_TEMP_ROOT = Path(__file__).resolve().parents[1] / "data" / "test-tmp"
TEST_TEMP_ROOT.mkdir(parents=True, exist_ok=True)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(65_536), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def _text_values(control) -> list[str]:
    values: list[str] = []
    value = getattr(control, "value", None)
    if isinstance(value, str):
        values.append(value)
    content = getattr(control, "content", None)
    if content is not None:
        values.extend(_text_values(content))
    for child in getattr(control, "controls", ()) or ():
        values.extend(_text_values(child))
    return values


class FakePage:
    def __init__(self, route: str = "/dashboard", *, web: bool = False):
        self.route = route
        self.web = web
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


class U1RuntimeTests(unittest.TestCase):
    def setUp(self):
        self.path = TEST_TEMP_ROOT / f"runtime-{uuid.uuid4().hex}.db"
        self.services = bootstrap(self.path).services

    def tearDown(self):
        self.path.unlink(missing_ok=True)
        for suffix in ("-wal", "-shm"):
            Path(f"{self.path}{suffix}").unlink(missing_ok=True)

    def _app(self, *, loading_delay: float = 0.05):
        page = FakePage()
        app = OverlordApp(page, self.services, loading_delay_seconds=loading_delay)
        app.mount()
        return page, app

    def test_cli_and_environment_demo_resolution_share_one_database(self):
        cli = main_module.runtime_configuration(["--demo"], {})
        environment = main_module.runtime_configuration([], {"OVERLORD_DEMO": "1"})
        production = main_module.runtime_configuration([], {})
        self.assertEqual("demo", cli.mode)
        self.assertEqual("demo", environment.mode)
        self.assertEqual(DEMO_DATABASE_PATH.resolve(), cli.database_path)
        self.assertEqual(cli.database_path, environment.database_path)
        self.assertEqual("production", production.mode)
        self.assertEqual(DEFAULT_DATABASE_PATH.resolve(), production.database_path)

    def test_application_owned_web_arguments_are_parsed_without_flet_cli(self):
        self.assertTrue(main_module.web_requested(["--web", "--port", "8550"]))
        self.assertFalse(main_module.web_requested(["--demo"]))
        self.assertEqual(8550, main_module.web_port(["--web"]))
        self.assertEqual(8551, main_module.web_port(["--web", "--port", "8551"]))
        self.assertEqual(8552, main_module.web_port(["--port=8552", "--web"]))
        self.assertEqual([], main_module._runtime_arguments(["--demo", "--web", "--port", "8550"]))
        with self.assertRaisesRegex(ValueError, "between 1 and 65535"):
            main_module.web_port(["--web", "--port", "70000"])

    def test_deterministic_demo_seed_fingerprint_and_production_isolation(self):
        production_hash = _sha256(DEFAULT_DATABASE_PATH)
        first = TEST_TEMP_ROOT / f"demo-a-{uuid.uuid4().hex}.db"
        second = TEST_TEMP_ROOT / f"demo-b-{uuid.uuid4().hex}.db"
        try:
            seed_demo_database(first, reset=True)
            first_fingerprint = demo_seed_fingerprint(first)
            reused = ensure_demo_database(first)
            self.assertEqual("reused", reused.seed_action)
            seed_demo_database(first, reset=True)
            seed_demo_database(second, reset=True)
            self.assertEqual(first_fingerprint, demo_seed_fingerprint(first))
            self.assertEqual(first_fingerprint, demo_seed_fingerprint(second))
            self.assertEqual(production_hash, _sha256(DEFAULT_DATABASE_PATH))
        finally:
            first.unlink(missing_ok=True)
            second.unlink(missing_ok=True)
            Path(f"{first}.seed.json").unlink(missing_ok=True)
            Path(f"{second}.seed.json").unlink(missing_ok=True)

    def test_main_bootstraps_once_for_one_session(self):
        fake_page = FakePage()
        fake_services = Mock()
        fake_result = SimpleNamespace(services=fake_services)
        mounted = Mock()
        with (
            patch.object(main_module, "STARTUP_RUNTIME", main_module.RuntimeConfiguration("production", self.path, True)),
            patch.object(main_module, "bootstrap", return_value=fake_result) as bootstrap_mock,
            patch.object(main_module, "OverlordApp") as app_class,
        ):
            app_class.return_value.mount = mounted
            main_module.main(fake_page)
        bootstrap_mock.assert_called_once_with(self.path)
        mounted.assert_called_once_with()

    def test_duplicate_route_is_ignored_and_shell_stays_mounted(self):
        page, app = self._app()
        shell = page.controls[0]
        changed = asyncio.run(app.transition_to("/dashboard"))
        self.assertFalse(changed)
        self.assertTrue(app.last_route_timing.duplicate)
        self.assertEqual(1, page.add_count)
        self.assertIs(shell, page.controls[0])

    def test_direct_route_and_sidebar_toggle_keep_the_same_shell(self):
        page = FakePage("/cycles")
        app = OverlordApp(page, self.services, loading_delay_seconds=0.05)
        app.mount()
        shell = page.controls[0]
        self.assertEqual("/cycles", app.state.route)
        self.assertFalse(app.state.sidebar_collapsed)
        app.toggle_sidebar(None)
        self.assertTrue(app.state.sidebar_collapsed)
        self.assertTrue(self.services.settings.get_settings.execute().sidebar_collapsed)
        self.assertEqual(1, page.add_count)
        self.assertIs(shell, page.controls[0])

    def test_root_route_resolves_to_dashboard_without_rebuilding_shell(self):
        page = FakePage("/tasks")
        app = OverlordApp(page, self.services, loading_delay_seconds=0.05)
        app.mount()
        shell = page.controls[0]

        changed = asyncio.run(app.transition_to("/"))

        self.assertTrue(changed)
        self.assertEqual("/dashboard", app.state.route)
        self.assertEqual(1, page.add_count)
        self.assertIs(shell, page.controls[0])

    def test_fast_route_has_no_loading_flash_and_logs_timing(self):
        page, app = self._app(loading_delay=0.2)
        shell = page.controls[0]
        with self.assertLogs("overlord.navigation", level="INFO") as captured:
            changed = asyncio.run(app.transition_to("/settings"))
        self.assertTrue(changed)
        self.assertFalse(app.last_route_timing.loading_visible)
        self.assertFalse(app._loading_indicator.visible)
        self.assertIs(shell, page.controls[0])
        output = "\n".join(captured.output)
        self.assertIn("route_query_start", output)
        self.assertIn("route_query_complete", output)
        self.assertIn("route_render_complete", output)

    def test_slow_route_shows_delayed_content_indicator(self):
        page, app = self._app(loading_delay=0.005)
        original = app._page_content

        def slow_content(*args, **kwargs):
            time.sleep(0.04)
            return original(*args, **kwargs)

        with patch.object(app, "_page_content", side_effect=slow_content):
            changed = asyncio.run(app.transition_to("/settings"))
        self.assertTrue(changed)
        self.assertTrue(app.last_route_timing.loading_visible)
        self.assertFalse(app._loading_indicator.visible)
        self.assertEqual(1, page.add_count)

    def test_route_failure_is_contained_inside_content(self):
        page, app = self._app(loading_delay=0.2)
        shell = page.controls[0]
        with patch.object(app, "_page_content", side_effect=RuntimeError("contained route failure")):
            changed = asyncio.run(app.transition_to("/settings"))
        self.assertTrue(changed)
        self.assertTrue(app.last_route_timing.failed)
        self.assertIs(shell, page.controls[0])
        self.assertIn("This page could not be loaded.", _text_values(app._content_host.content))
        self.assertNotIn("contained route failure", _text_values(app._content_host.content))
        self.assertTrue(any(value.startswith("Error ID: ") for value in _text_values(app._content_host.content)))


if __name__ == "__main__":
    unittest.main()
