from __future__ import annotations

import asyncio
import hashlib
import threading
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
from overlord.ui.app import OverlordApp


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


def _walk(control):
    yield control
    content = getattr(control, "content", None)
    if isinstance(content, ft.Control):
        yield from _walk(content)
    for child in getattr(control, "controls", ()) or ():
        yield from _walk(child)


def _role(control, role: str):
    return next(
        item
        for item in _walk(control)
        if isinstance(getattr(item, "data", None), dict) and item.data.get("role") == role
    )


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
        self.dialogs: list[ft.Control] = []

    def add(self, *controls):
        self.add_count += 1
        self.controls.extend(controls)

    def update(self):
        self.update_count += 1

    def show_dialog(self, dialog):
        self.dialogs.append(dialog)

    def pop_dialog(self):
        return self.dialogs.pop() if self.dialogs else None

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

    def test_desktop_runtime_rejects_retired_web_arguments(self):
        self.assertEqual([], main_module.desktop_runtime_arguments(["--demo"]))
        for arguments in (["--web"], ["--port", "8550"], ["--port=8550"]):
            with self.subTest(arguments=arguments):
                with self.assertRaisesRegex(ValueError, "web mode has been retired"):
                    main_module.desktop_runtime_arguments(arguments)

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

    def test_demo_startup_reseeds_after_session_mutation(self):
        production_hash = _sha256(DEFAULT_DATABASE_PATH)
        demo = TEST_TEMP_ROOT / f"demo-session-{uuid.uuid4().hex}.db"
        try:
            seeded = seed_demo_database(demo, reset=True)
            services = bootstrap(demo).services
            created = services.tasks.create_task.execute(None, "Disposable demo mutation")
            self.assertEqual(
                "Disposable demo mutation",
                services.tasks.get_editor.execute(created.id).task.title,
            )

            restarted = ensure_demo_database(demo)
            self.assertEqual("reset", restarted.seed_action)
            with self.assertRaisesRegex(ValueError, "does not exist"):
                bootstrap(demo).services.tasks.get_editor.execute(created.id)
            self.assertEqual(seeded.task_count, restarted.task_count)
            self.assertEqual(production_hash, _sha256(DEFAULT_DATABASE_PATH))
        finally:
            demo.unlink(missing_ok=True)
            Path(f"{demo}-wal").unlink(missing_ok=True)
            Path(f"{demo}-shm").unlink(missing_ok=True)
            Path(f"{demo}.seed.json").unlink(missing_ok=True)

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

    def test_tasks_workspace_stays_mounted_through_resize_restore_and_sidebar_toggle(self):
        page = FakePage("/tasks")
        page.width = 1280
        page.height = 720
        app = OverlordApp(page, self.services, loading_delay_seconds=0.05)
        app.mount()

        shell = page.controls[0]
        workspace = app._shell.content_host.content
        view_host = _role(workspace, "task-view-host")
        self.assertEqual(232, app._shell.sidebar.control.width)
        self.assertEqual("workspace-page", workspace.data["layout"])
        self.assertTrue(workspace.expand)
        self.assertTrue(view_host.expand)
        self.assertIsNone(view_host.width)
        self.assertIsNone(view_host.height)

        for width, height in ((1600, 900), (1920, 1080), (1280, 720)):
            page.width = width
            page.height = height
            page.on_resize(None)
            self.assertIs(workspace, app._shell.content_host.content)
            self.assertIs(view_host, _role(workspace, "task-view-host"))
            self.assertEqual(1, page.add_count)
            self.assertEqual("/tasks", app.state.route)

        app.toggle_sidebar(None)
        self.assertEqual(56, app._shell.sidebar.control.width)
        self.assertIs(workspace, app._shell.content_host.content)
        self.assertIs(view_host, _role(workspace, "task-view-host"))
        self.assertIs(shell, page.controls[0])

        for mode in ("week", "month", "kanban"):
            tab = next(
                control
                for control in _walk(workspace)
                if isinstance(getattr(control, "data", None), dict)
                and control.data.get("role") == "segmented-tab"
                and control.data.get("tab") == mode
            )
            with patch.object(ft.Control, "update", lambda _control: None):
                tab.on_click(None)
            self.assertIs(view_host, _role(workspace, "task-view-host"))
            self.assertEqual(mode, app.state.task_view_mode)

        app.toggle_sidebar(None)
        self.assertEqual(232, app._shell.sidebar.control.width)
        self.assertIs(workspace, app._shell.content_host.content)
        self.assertIs(view_host, _role(workspace, "task-view-host"))
        self.assertEqual(1, page.add_count)

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

    def test_dashboard_top_row_contract_survives_navigation_and_language_rebuilds(self):
        page, app = self._app()

        def placement() -> tuple[type, list[str], object, object, object]:
            row = _role(page.controls[0], "first-bento-row")
            return (
                type(row),
                [item.data["role"] for item in row.controls],
                row.spacing,
                row.height,
                row.controls[1].width,
            )

        expected = (
            ft.Row,
            ["three-day-task-board", "weekly-progress-widget"],
            16,
            433,
            None,
        )
        self.assertEqual(expected, placement())
        asyncio.run(app.transition_to("/tasks"))
        asyncio.run(app.transition_to("/dashboard"))
        self.assertEqual(expected, placement())
        try:
            app.toggle_language(SimpleNamespace(control=SimpleNamespace(value=True)))
            self.assertEqual(expected, placement())
        finally:
            app.toggle_language(SimpleNamespace(control=SimpleNamespace(value=False)))

    def test_fast_route_has_no_loading_flash_and_logs_timing(self):
        page, app = self._app(loading_delay=0.2)
        shell = page.controls[0]
        with self.assertLogs("overlord.navigation", level="INFO") as captured:
            changed = asyncio.run(app.transition_to("/settings"))
        self.assertTrue(changed)
        self.assertFalse(app.last_route_timing.loading_visible)
        self.assertFalse(app._shell.loading_indicator.visible)
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
        self.assertFalse(app._shell.loading_indicator.visible)
        self.assertEqual(1, page.add_count)

    def test_route_failure_is_contained_inside_content(self):
        page, app = self._app(loading_delay=0.2)
        shell = page.controls[0]
        with patch.object(app, "_page_content", side_effect=RuntimeError("contained route failure")):
            changed = asyncio.run(app.transition_to("/settings"))
        self.assertTrue(changed)
        self.assertTrue(app.last_route_timing.failed)
        self.assertIs(shell, page.controls[0])
        self.assertIn("This page could not be loaded.", _text_values(app._shell.content_host.content))
        self.assertNotIn("contained route failure", _text_values(app._shell.content_host.content))
        self.assertTrue(any(value.startswith("Error ID: ") for value in _text_values(app._shell.content_host.content)))

    def test_sync_refresh_and_async_navigation_share_the_same_failure_commit(self):
        page, app = self._app(loading_delay=0.2)
        shell = page.controls[0]

        with patch.object(app, "_page_content", side_effect=RuntimeError("sync failure")):
            app.render()
        sync_copy = _text_values(app._shell.content_host.content)
        self.assertTrue(app.last_route_timing.failed)
        self.assertEqual("/dashboard", app.last_route_timing.requested_route)

        with patch.object(app, "_page_content", side_effect=RuntimeError("async failure")):
            changed = asyncio.run(app.transition_to("/settings"))
        async_copy = _text_values(app._shell.content_host.content)

        self.assertTrue(changed)
        self.assertTrue(app.last_route_timing.failed)
        self.assertIn("This page could not be loaded.", sync_copy)
        self.assertIn("This page could not be loaded.", async_copy)
        self.assertIs(shell, page.controls[0])

    def test_selected_task_route_behavior_survives_the_shared_pipeline(self):
        task = self.services.tasks.create_task.execute(None, "Open from route")
        page, app = self._app()
        shell = page.controls[0]

        changed = asyncio.run(app.transition_to(f"/tasks?task={task.id}"))

        self.assertTrue(changed)
        self.assertEqual(f"/tasks?task={task.id}", app.state.route)
        self.assertIsNone(app.state.selected_task_id)
        self.assertEqual(1, len(page.dialogs))
        self.assertIn("Open from route", _text_values(page.dialogs[0]))
        app.render()
        self.assertEqual(2, len(page.dialogs))
        self.assertTrue(all("Open from route" in _text_values(dialog) for dialog in page.dialogs))
        self.assertIs(shell, page.controls[0])

    def test_superseded_route_cannot_replace_the_latest_content(self):
        page, app = self._app(loading_delay=0.2)
        shell = page.controls[0]
        first_started = threading.Event()
        release_first = threading.Event()
        original = app._page_content

        def controlled_content(tokens, path, family):
            if path == "/settings":
                first_started.set()
                self.assertTrue(release_first.wait(timeout=2))
            return original(tokens, path, family)

        async def run_transitions():
            first = asyncio.create_task(app.transition_to("/settings"))
            started = await asyncio.to_thread(first_started.wait, 2)
            self.assertTrue(started)
            second_result = await app.transition_to("/tasks")
            release_first.set()
            first_result = await first
            return first_result, second_result

        with patch.object(app, "_page_content", side_effect=controlled_content):
            first_result, second_result = asyncio.run(run_transitions())

        self.assertFalse(first_result)
        self.assertTrue(second_result)
        self.assertEqual("/tasks", app.state.route)
        self.assertEqual("/tasks", app.last_route_timing.requested_route)
        self.assertIs(shell, page.controls[0])
        self.assertIn("My Tasks", _text_values(app._shell.content_host.content))

    def test_rapid_route_switching_commits_only_the_latest_request(self):
        page, app = self._app(loading_delay=0.2)
        shell = page.controls[0]
        settings_started = threading.Event()
        projects_started = threading.Event()
        release_stale = threading.Event()
        original = app._page_content

        def controlled_content(tokens, path, family):
            if path == "/settings":
                settings_started.set()
                self.assertTrue(release_stale.wait(timeout=3))
            elif path == "/projects":
                projects_started.set()
                self.assertTrue(release_stale.wait(timeout=3))
            return original(tokens, path, family)

        async def run_transitions():
            settings = asyncio.create_task(app.transition_to("/settings"))
            self.assertTrue(await asyncio.to_thread(settings_started.wait, 2))
            projects = asyncio.create_task(app.transition_to("/projects"))
            self.assertTrue(await asyncio.to_thread(projects_started.wait, 2))
            tasks_result = await app.transition_to("/tasks")
            release_stale.set()
            return await settings, await projects, tasks_result

        with patch.object(app, "_page_content", side_effect=controlled_content):
            settings_result, projects_result, tasks_result = asyncio.run(run_transitions())

        self.assertFalse(settings_result)
        self.assertFalse(projects_result)
        self.assertTrue(tasks_result)
        self.assertEqual("/tasks", app.state.route)
        self.assertEqual("/tasks", app.last_route_timing.requested_route)
        self.assertFalse(app._shell.loading_indicator.visible)
        self.assertIn("My Tasks", _text_values(app._shell.content_host.content))
        self.assertIs(shell, page.controls[0])


if __name__ == "__main__":
    unittest.main()
