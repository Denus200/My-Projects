from __future__ import annotations

import hashlib
import inspect
import sqlite3
import unittest
import uuid
from datetime import date, timedelta
from pathlib import Path

from main import startup_database_path
from overlord.bootstrap import DEFAULT_DATABASE_PATH, bootstrap
from overlord.demo import DEMO_DATABASE_PATH, seed_demo_database
from overlord.domain.tasks import TodayGroup
from overlord.presentation.design_system.tokens import LIGHT_TOKENS
from overlord.presentation.pages.dashboard import build_dashboard
from overlord.presentation.pages import tasks as tasks_page


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


class U1DailyPlanningTests(unittest.TestCase):
    def test_task_creation_does_not_offer_dashboard_group_or_position(self):
        source = inspect.getsource(tasks_page.build_tasks)
        self.assertNotIn('label="Dashboard slot"', source)
        self.assertNotIn('label="Position"', source)
        self.assertIn("today_group=None", source)
        self.assertIn("position=None", source)

    def setUp(self):
        self.path = TEST_TEMP_ROOT / f"u1-{uuid.uuid4().hex}.db"
        self.services = bootstrap(self.path).services
        self.project = self.services.projects.create_project.execute("Planning Project")
        self.day = date(2026, 8, 6)

    def tearDown(self):
        self.path.unlink(missing_ok=True)

    def create_task(self, title: str):
        return self.services.tasks.create_task.execute(
            self.project.id,
            title,
            planned_date=self.day,
            definition_of_done=f"{title} is complete.",
        )

    def test_demo_mode_always_uses_the_isolated_database(self):
        resolved = startup_database_path(
            ["--demo"],
            {"OVERLORD_DB_PATH": str(DEFAULT_DATABASE_PATH)},
        )
        self.assertEqual(DEMO_DATABASE_PATH.resolve(), resolved)
        self.assertNotEqual(DEFAULT_DATABASE_PATH.resolve(), resolved)

    def test_deterministic_seed_reset_and_production_hash_safety(self):
        production_before = _sha256(DEFAULT_DATABASE_PATH)
        first = seed_demo_database(self.path, today=self.day, reset=True)
        first_snapshot = self.semantic_snapshot()
        second = seed_demo_database(self.path, today=self.day, reset=True)
        second_snapshot = self.semantic_snapshot()

        self.assertEqual(first_snapshot, second_snapshot)
        self.assertEqual((3, 4), (first.primary_count, first.secondary_count))
        self.assertEqual((3, 4), (second.primary_count, second.secondary_count))
        self.assertEqual(production_before, _sha256(DEFAULT_DATABASE_PATH))

    def semantic_snapshot(self):
        connection = sqlite3.connect(self.path)
        try:
            return tuple(
                tuple(connection.execute(query).fetchall())
                for query in (
                    "SELECT id,title,status,stage_label FROM projects ORDER BY id",
                    "SELECT id,project_id,title,lifecycle_status,definition_of_done,next_action,importance,urgency FROM tasks ORDER BY id",
                    "SELECT task_id,planned_date,today_group,position,supersedes_plan_id FROM task_plans ORDER BY id",
                    "SELECT task_id,type,description,resolved_at FROM blockers ORDER BY id",
                    "SELECT title,main_outcome,start_date,length_weeks,status FROM cycles ORDER BY id",
                    "SELECT week_number,title,status FROM weekly_outcomes ORDER BY week_number",
                )
            )
        finally:
            connection.close()

    def test_capacity_assignment_removal_reordering_and_identity(self):
        tasks = [self.create_task(f"Task {number}") for number in range(1, 9)]
        with self.assertRaisesRegex(ValueError, "at most 3 Primary"):
            self.services.daily_planning.save_plan.execute(self.day, tuple(task.id for task in tasks[:4]), ())
        with self.assertRaisesRegex(ValueError, "at most 4 Secondary"):
            self.services.daily_planning.save_plan.execute(self.day, (), tuple(task.id for task in tasks[:5]))

        self.services.daily_planning.save_plan.execute(
            self.day,
            (tasks[0].id, tasks[1].id, tasks[2].id),
            (tasks[3].id, tasks[4].id, tasks[5].id, tasks[6].id),
        )
        initial = self.services.daily_planning.get_plan.execute(self.day)
        self.assertEqual([tasks[0].id, tasks[1].id, tasks[2].id], [item.task.id for item in initial.primary])
        self.assertEqual([tasks[3].id, tasks[4].id, tasks[5].id, tasks[6].id], [item.task.id for item in initial.secondary])

        self.services.daily_planning.save_plan.execute(
            self.day,
            (tasks[2].id, tasks[0].id),
            (tasks[6].id, tasks[4].id),
        )
        updated = self.services.daily_planning.get_plan.execute(self.day)
        self.assertEqual([tasks[2].id, tasks[0].id], [item.task.id for item in updated.primary])
        self.assertEqual([tasks[6].id, tasks[4].id], [item.task.id for item in updated.secondary])
        self.assertEqual(tasks[0].id, self.services.tasks.get_editor.execute(tasks[0].id).task.id)
        self.assertEqual(tasks[1].title, self.services.tasks.get_editor.execute(tasks[1].id).task.title)
        removed_plan = self.services.tasks.get_editor.execute(tasks[1].id).planning_history[-1]
        self.assertIsNone(removed_plan.today_group)
        self.assertIsNone(removed_plan.position)

    def test_overflow_remains_global_while_dashboard_has_seven_slots(self):
        tasks = [self.create_task(f"Visible {number}") for number in range(1, 9)]
        self.services.daily_planning.save_plan.execute(
            self.day,
            tuple(task.id for task in tasks[:3]),
            tuple(task.id for task in tasks[3:7]),
        )
        dashboard = self.services.dashboard.execute(self.day)
        global_tasks = self.services.tasks.list_tasks.execute(planned_date=self.day)
        self.assertEqual(3, len(dashboard.primary))
        self.assertEqual(4, len(dashboard.secondary))
        self.assertEqual(8, len(global_tasks))
        self.assertIn(tasks[7].id, {item.task.id for item in global_tasks})

    def test_empty_and_populated_dashboard_states(self):
        empty_data = self.services.dashboard.execute(self.day + timedelta(days=10))
        self.assertFalse(empty_data.primary)
        self.assertFalse(empty_data.secondary)
        empty_control = build_dashboard(
            self.services,
            LIGHT_TOKENS,
            f"/dashboard?date={(self.day + timedelta(days=10)).isoformat()}",
            lambda *_: None,
            lambda *_: None,
            lambda *_: None,
        )
        self.assertIn("Nothing is planned for today.", _text_values(empty_control))

        seed_demo_database(self.path, today=self.day, reset=True)
        seeded_services = bootstrap(self.path).services
        populated = seeded_services.dashboard.execute(self.day)
        self.assertEqual(
            [
                "Finalize Viora evidence section",
                "Record English project explanation",
                "Review Overlord Dashboard",
            ],
            [item.task.title for item in populated.primary],
        )
        self.assertEqual(4, len(populated.secondary))
        self.assertEqual(7, len(populated.weekly_bars))
        self.assertEqual(4, len(populated.attention))


if __name__ == "__main__":
    unittest.main()
