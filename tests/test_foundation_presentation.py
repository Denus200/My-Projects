import unittest
import uuid
from datetime import date
from pathlib import Path

import flet as ft

from overlord.bootstrap import bootstrap
from overlord.domain.cycles import CycleStatus
from overlord.presentation.design_system.themes import build_dark_theme, build_light_theme
from overlord.presentation.design_system.tokens import LIGHT_TOKENS
from overlord.presentation.design_system.icons import IconName, lucide_icon
from overlord.presentation.pages.cycles import build_cycles
from overlord.presentation.pages.daily_planning import build_daily_planning
from overlord.presentation.pages.dashboard import build_dashboard
from overlord.presentation.pages.projects import build_projects
from overlord.presentation.pages.settings import build_settings
from overlord.presentation.pages.tasks import build_tasks
from overlord.presentation.state import AppSessionState


TEST_TEMP_ROOT = Path(__file__).resolve().parents[1] / "data" / "test-tmp"
TEST_TEMP_ROOT.mkdir(parents=True, exist_ok=True)


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
        controls = [
            build_dashboard(self.services, LIGHT_TOKENS, "/dashboard", self.noop, self.noop, self.noop),
            build_daily_planning(self.services, LIGHT_TOKENS, "/planning/day", self.noop, self.noop),
            build_tasks(self.services, LIGHT_TOKENS, AppSessionState(), self.noop, self.noop),
            build_projects(self.services, LIGHT_TOKENS, "/projects", self.noop, self.noop, self.noop),
            build_projects(self.services, LIGHT_TOKENS, f"/projects/{self.project.id}", self.noop, self.noop, self.noop),
            build_cycles(self.services, LIGHT_TOKENS, "/cycles", self.noop, self.noop, self.noop),
            build_cycles(self.services, LIGHT_TOKENS, f"/cycles/{self.cycle.id}", self.noop, self.noop, self.noop),
            build_settings(self.services, LIGHT_TOKENS, self.noop, self.noop),
        ]
        self.assertTrue(all(isinstance(control, ft.Control) for control in controls))

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
