import unittest
import uuid
from datetime import date
from pathlib import Path

import flet as ft

from overlord.bootstrap import bootstrap
from overlord.modules.cycles.domain import CycleStatus
from overlord.ui.design_system.themes import build_dark_theme, build_light_theme
from overlord.ui.design_system.tokens import LIGHT_TOKENS
from overlord.ui.design_system.icons import IconName, lucide_icon
from overlord.ui.pages.cycles.page import build_cycles
from overlord.ui.pages.projects.page import build_projects
from overlord.ui.pages.dashboard.page import build_dashboard
from overlord.ui.pages.settings.page import build_settings
from overlord.ui.pages.tasks.page import build_tasks
from overlord.ui.state import AppSessionState


TEST_TEMP_ROOT = Path(__file__).resolve().parents[1] / "data" / "test-tmp"
TEST_TEMP_ROOT.mkdir(parents=True, exist_ok=True)


def _walk(control: ft.Control):
    yield control
    content = getattr(control, "content", None)
    if isinstance(content, ft.Control):
        yield from _walk(content)
    for child in getattr(control, "controls", ()) or ():
        yield from _walk(child)


def _role(control: ft.Control, role: str) -> list[ft.Control]:
    return [
        item
        for item in _walk(control)
        if isinstance(getattr(item, "data", None), dict) and item.data.get("role") == role
    ]


class FoundationPresentationTests(unittest.TestCase):
    def setUp(self):
        self.path = TEST_TEMP_ROOT / f"presentation-{uuid.uuid4().hex}.db"
        self.services = bootstrap(self.path).services
        self.project = self.services.projects.create_project.execute("UI Project")
        self.task = self.services.tasks.create_task.execute(self.project.id, "UI Task")
        self.cycle = self.services.cycles.create_cycle.execute("UI Cycle", "Ship a useful foundation", date.today())
        self.services.cycles.change_status.execute(self.cycle.id, CycleStatus.ACTIVE)
        self.noop = lambda *args, **kwargs: None

    def tearDown(self):
        self.path.unlink(missing_ok=True)

    def test_all_route_pages_construct_with_flet_084(self):
        tasks = build_tasks(self.services, LIGHT_TOKENS, AppSessionState(), self.noop, self.noop)
        scrolling_pages = [
            build_dashboard(self.services, LIGHT_TOKENS, "/dashboard", self.noop, self.noop, self.noop),
            build_projects(self.services, LIGHT_TOKENS, "/projects", self.noop, self.noop, self.noop),
            build_projects(self.services, LIGHT_TOKENS, f"/projects/{self.project.id}", self.noop, self.noop, self.noop),
            build_cycles(self.services, LIGHT_TOKENS, "/cycles", self.noop, self.noop, self.noop),
            build_cycles(self.services, LIGHT_TOKENS, f"/cycles/{self.cycle.id}", self.noop, self.noop, self.noop),
            build_settings(self.services, LIGHT_TOKENS, self.noop, self.noop),
        ]
        controls = [tasks, *scrolling_pages]
        self.assertTrue(all(isinstance(control, ft.Control) for control in controls))
        self.assertTrue(all(isinstance(control, ft.ListView) for control in scrolling_pages))
        self.assertTrue(all(control.data["layout"] == "global-page" for control in scrolling_pages))
        padding_layers = [_role(control, "global-page-padding-layer")[0] for control in scrolling_pages]
        self.assertTrue(all(layer.padding.left == 24 and layer.padding.right == 24 for layer in padding_layers))
        self.assertTrue(all(layer.padding.top == 16 and layer.padding.bottom == 16 for layer in padding_layers))
        self.assertTrue(all(control.padding == 0 for control in scrolling_pages))
        self.assertIsInstance(tasks, ft.Container)
        self.assertEqual("workspace-page", tasks.data["layout"])
        self.assertTrue(tasks.expand)
        self.assertEqual((24, 24, 16, 16), (
            tasks.padding.left,
            tasks.padding.right,
            tasks.padding.top,
            tasks.padding.bottom,
        ))
        self.assertTrue(_role(tasks, "task-view-host")[0].expand)
        self.assertTrue(all(len(_role(control, "page-header")) == 1 for control in controls))
        self.assertTrue(all(len(_role(control, "user-menu-trigger")) == 1 for control in controls))

    def test_tasks_uses_title_only_shared_header(self):
        control = build_tasks(self.services, LIGHT_TOKENS, AppSessionState(), self.noop, self.noop)
        self.assertEqual("My Tasks", _role(control, "page-header-title")[0].value)
        self.assertEqual([], _role(control, "page-header-subtitle"))

    def test_lucide_registry_assets_are_packaged_and_tintable(self):
        asset_root = Path(__file__).resolve().parents[1] / "assets" / "icons" / "lucide"
        self.assertTrue((asset_root / "LICENSE").exists())
        self.assertTrue((asset_root / "VERSION").exists())
        for name in IconName:
            asset = asset_root / f"{name.value}.svg"
            self.assertTrue(asset.exists(), asset)
            self.assertIn('stroke="currentColor"', asset.read_text(encoding="utf-8"))
            control = lucide_icon(name, color=LIGHT_TOKENS.text_primary, size=LIGHT_TOKENS.icon_medium, label=name.value)
            self.assertEqual(f"icons/lucide/{name.value}.svg", control.src)

        brand_asset = Path(__file__).resolve().parents[1] / "assets" / "brand" / "overlord-mark.svg"
        self.assertTrue(brand_asset.exists())

    def test_browser_sessions_receive_distinct_theme_instances(self):
        first_light = build_light_theme()
        second_light = build_light_theme()
        first_dark = build_dark_theme()
        second_dark = build_dark_theme()

        self.assertIsNot(first_light, second_light)
        self.assertIsNot(first_dark, second_dark)
        self.assertIsNot(first_light.color_scheme, second_light.color_scheme)
        self.assertIsNot(first_dark.color_scheme, second_dark.color_scheme)

    def test_settings_persist_and_effective_motion_respects_reduction(self):
        updated = self.services.settings.update_settings.execute(
            theme_mode="dark", motion_enabled=True, reduced_motion=True, sidebar_collapsed=True
        )
        reloaded = self.services.settings.get_settings.execute()
        self.assertEqual(updated, reloaded)
        self.assertFalse(reloaded.effective_motion)
        self.assertTrue(reloaded.sidebar_collapsed)


if __name__ == "__main__":
    unittest.main()
