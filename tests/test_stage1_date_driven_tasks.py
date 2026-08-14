from __future__ import annotations

import hashlib
import sqlite3
import unittest
import uuid
from datetime import date, timedelta
from pathlib import Path

from main import startup_database_path
from overlord.bootstrap import DEFAULT_DATABASE_PATH, bootstrap
from overlord.demo import DEMO_DATABASE_PATH, seed_demo_database
from overlord.infrastructure.sqlite.connection import ConnectionFactory
from overlord.infrastructure.sqlite.migrations import MigrationRunner
from overlord.ui.design_system.tokens import LIGHT_TOKENS
from overlord.ui.pages.dashboard.page import build_dashboard
from overlord.ui.navigation import route_family


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
    for slot in ("header", "footer"):
        child = getattr(control, slot, None)
        if child is not None:
            values.extend(_text_values(child))
    for child in getattr(control, "controls", ()) or ():
        values.extend(_text_values(child))
    return values


class Stage1DateDrivenTaskTests(unittest.TestCase):
    def setUp(self):
        self.path = TEST_TEMP_ROOT / f"stage1-{uuid.uuid4().hex}.db"
        self.services = bootstrap(self.path).services
        self.project = self.services.projects.create_project.execute("Scheduling Project")
        self.day = date(2026, 8, 13)

    def tearDown(self):
        self.path.unlink(missing_ok=True)

    def test_daily_planning_route_and_service_are_removed(self):
        self.assertIsNone(route_family("/planning/day"))
        self.assertFalse(hasattr(self.services, "daily_planning"))

    def test_every_task_scheduled_for_today_appears_without_slots_or_capacity(self):
        tasks = [
            self.services.tasks.create_task.execute(
                self.project.id,
                f"Visible {number}",
                schedule_start_date=self.day,
            )
            for number in range(1, 9)
        ]
        dashboard = self.services.dashboard.execute(self.day)
        self.assertEqual({task.id for task in tasks}, {item.task.id for item in dashboard.today_tasks})

    def test_date_range_appears_on_every_inclusive_day(self):
        task = self.services.tasks.create_task.execute(
            self.project.id,
            "Multi-day task",
            schedule_start_date=self.day,
            schedule_end_date=self.day + timedelta(days=5),
        )
        for offset in range(6):
            self.assertIn(
                task.id,
                {item.task.id for item in self.services.dashboard.execute(self.day + timedelta(days=offset)).today_tasks},
            )
        self.assertNotIn(
            task.id,
            {item.task.id for item in self.services.dashboard.execute(self.day + timedelta(days=6)).today_tasks},
        )

    def test_dashboard_empty_state_has_no_planning_call_to_action(self):
        control = build_dashboard(
            self.services,
            LIGHT_TOKENS,
            f"/dashboard?date={self.day.isoformat()}",
            lambda *_: None,
            lambda *_: None,
            lambda *_: None,
        )
        copy = _text_values(control)
        self.assertEqual(3, copy.count("No tasks"))
        self.assertIn("Yesterday", copy)
        self.assertIn("Today", copy)
        self.assertIn("Tomorrow", copy)
        self.assertNotIn("Plan the day", copy)
        self.assertNotIn("3 Primary · 4 Secondary", copy)

    def test_migration_copies_current_legacy_plan_and_preserves_history(self):
        legacy_path = TEST_TEMP_ROOT / f"stage1-legacy-{uuid.uuid4().hex}.db"
        backup_paths: list[Path] = []
        try:
            runner = MigrationRunner(ConnectionFactory(legacy_path))
            runner.migrate(target_version=7)
            connection = sqlite3.connect(legacy_path)
            try:
                task_id = connection.execute(
                    "INSERT INTO tasks(project_id,title,scheduled_date,lifecycle_status) VALUES (NULL,?,?,?)",
                    ("Legacy history", self.day.isoformat(), "planned"),
                ).lastrowid
                connection.execute(
                    "INSERT INTO task_plans(task_id,planned_date,planned_week_start) VALUES (?,?,?)",
                    (task_id, self.day.isoformat(), (self.day - timedelta(days=self.day.weekday())).isoformat()),
                )
                connection.commit()
            finally:
                connection.close()
            result = runner.migrate()
            if result.backup:
                backup_paths.extend((result.backup.database_path, result.backup.manifest_path))
            migrated = bootstrap(legacy_path).services.tasks.get_editor.execute(task_id).task
            self.assertEqual(self.day, migrated.schedule_start_date)
            connection = sqlite3.connect(legacy_path)
            try:
                self.assertEqual(1, connection.execute("SELECT COUNT(*) FROM task_plans WHERE task_id=?", (task_id,)).fetchone()[0])
            finally:
                connection.close()
        finally:
            legacy_path.unlink(missing_ok=True)
            for path in backup_paths:
                path.unlink(missing_ok=True)

    def test_demo_reset_is_deterministic_and_does_not_touch_production(self):
        resolved = startup_database_path(["--demo"], {"OVERLORD_DB_PATH": str(DEFAULT_DATABASE_PATH)})
        self.assertEqual(DEMO_DATABASE_PATH.resolve(), resolved)
        production_before = _sha256(DEFAULT_DATABASE_PATH)
        first = seed_demo_database(self.path, today=self.day, reset=True)
        second = seed_demo_database(self.path, today=self.day, reset=True)
        self.assertEqual(7, first.scheduled_today_count)
        self.assertEqual(first.scheduled_today_count, second.scheduled_today_count)
        self.assertEqual(production_before, _sha256(DEFAULT_DATABASE_PATH))


if __name__ == "__main__":
    unittest.main()
