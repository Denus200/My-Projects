import sqlite3
import unittest
import uuid
from contextlib import closing
from datetime import date, timedelta
from pathlib import Path

from overlord.bootstrap import bootstrap
from overlord.domain.cycles import CycleStatus, cycle_end_date
from overlord.domain.tasks import BlockerType, TaskLifecycle, TodayGroup


TEST_TEMP_ROOT = Path(__file__).resolve().parents[1] / "data" / "test-tmp"
TEST_TEMP_ROOT.mkdir(parents=True, exist_ok=True)


class FoundationApplicationTests(unittest.TestCase):
    def setUp(self):
        self.path = TEST_TEMP_ROOT / f"application-{uuid.uuid4().hex}.db"
        self.services = bootstrap(self.path).services
        self.project = self.services.projects.create_project.execute("Foundation")

    def tearDown(self):
        self.path.unlink(missing_ok=True)

    def test_primary_assignment_requires_definition_of_done(self):
        with self.assertRaisesRegex(ValueError, "Definition of Done"):
            self.services.tasks.create_task.execute(
                self.project.id,
                "Unsafe Primary",
                planned_date=date.today(),
                today_group=TodayGroup.PRIMARY,
                position=1,
            )
        self.assertEqual((), self.services.tasks.list_tasks.execute())

    def test_invalid_estimate_is_rejected_at_application_boundary(self):
        with self.assertRaisesRegex(ValueError, "positive"):
            self.services.tasks.create_task.execute(
                self.project.id, "Invalid estimate", estimate_minutes=0
            )

    def test_missing_task_update_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "does not exist"):
            self.services.tasks.update_task.execute(999_999, title="Missing")

    def test_multiple_projects_are_created_independently(self):
        second = self.services.projects.create_project.execute("Second Project")
        self.assertEqual({self.project.id, second.id}, {item.id for item in self.services.projects.list_projects.execute()})

    def test_project_plus_first_task_rolls_back_as_one_transaction(self):
        with closing(sqlite3.connect(self.path)) as connection:
            connection.execute(
                "CREATE TRIGGER test_reject_task BEFORE INSERT ON tasks BEGIN SELECT RAISE(ABORT, 'test failure'); END"
            )
            connection.commit()
        before = len(self.services.projects.list_projects.execute())
        with self.assertRaises(sqlite3.IntegrityError):
            self.services.projects.create_project.execute(
                "Must roll back", first_task_title="Rejected Task"
            )
        self.assertEqual(before, len(self.services.projects.list_projects.execute()))

    def test_daily_capacity_and_overflow_discoverability(self):
        for position in range(1, 4):
            self.services.tasks.create_task.execute(
                self.project.id, f"Primary {position}", definition_of_done="Done",
                today_group=TodayGroup.PRIMARY, position=position,
            )
        for position in range(1, 5):
            self.services.tasks.create_task.execute(
                self.project.id, f"Secondary {position}", today_group=TodayGroup.SECONDARY,
                position=position,
            )
        self.services.tasks.create_task.execute(self.project.id, "Overflow")
        dashboard = self.services.dashboard.execute()
        self.assertEqual(3, len(dashboard.primary))
        self.assertEqual(4, len(dashboard.secondary))
        self.assertEqual(8, len(self.services.tasks.list_tasks.execute()))

    def test_planning_move_preserves_original_plan(self):
        task = self.services.tasks.create_task.execute(
            self.project.id,
            "Move transparently",
            definition_of_done="A verified result exists",
            planned_date=date.today(),
            today_group=TodayGroup.PRIMARY,
            position=1,
        )
        tomorrow = date.today() + timedelta(days=1)
        self.services.tasks.assign_plan.execute(task.id, tomorrow, TodayGroup.SECONDARY, 1)
        editor = self.services.tasks.get_editor.execute(task.id)
        self.assertEqual(2, len(editor.planning_history))
        self.assertEqual(date.today(), editor.planning_history[0].planned_date)
        self.assertIsNone(editor.planning_history[0].supersedes_plan_id)
        self.assertEqual(editor.planning_history[0].id, editor.planning_history[1].supersedes_plan_id)

    def test_blocker_does_not_change_task_lifecycle(self):
        task = self.services.tasks.create_task.execute(self.project.id, "Blocked but planned")
        blocker = self.services.tasks.open_blocker.execute(task.id, BlockerType.DEPENDENCY, "Waiting for input")
        self.assertEqual(TaskLifecycle.PLANNED, self.services.tasks.get_editor.execute(task.id).task.lifecycle_status)
        self.services.tasks.resolve_blocker.execute(blocker.id, "Input received")
        self.assertEqual(TaskLifecycle.PLANNED, self.services.tasks.get_editor.execute(task.id).task.lifecycle_status)

    def test_dashboard_execution_score_uses_original_week(self):
        task = self.services.tasks.create_task.execute(
            self.project.id,
            "Finish this week",
            definition_of_done="Complete",
            planned_date=date.today(),
            today_group=TodayGroup.PRIMARY,
            position=1,
        )
        self.services.tasks.complete_task.execute(task.id)
        dashboard = self.services.dashboard.execute(date.today())
        self.assertEqual(1.0, dashboard.execution_score)
        self.assertEqual("Not tracked yet", dashboard.actual_time_label)

    def test_only_one_cycle_can_be_active(self):
        first = self.services.cycles.create_cycle.execute("First", "Outcome one", date.today())
        second = self.services.cycles.create_cycle.execute("Second", "Outcome two", date.today())
        self.services.cycles.change_status.execute(first.id, CycleStatus.ACTIVE)
        with self.assertRaises(sqlite3.IntegrityError):
            self.services.cycles.change_status.execute(second.id, CycleStatus.ACTIVE)
        active = self.services.dashboard.execute().current_cycle
        self.assertEqual(first.id, active.cycle_id)

    def test_cycle_end_date_is_inclusive(self):
        start = date(2026, 1, 5)
        self.assertEqual(date(2026, 3, 29), cycle_end_date(start, 12))

    def test_archived_cycle_is_read_only_until_restored(self):
        cycle = self.services.cycles.create_cycle.execute("Archive", "Preserve history", date.today())
        self.services.cycles.change_status.execute(cycle.id, CycleStatus.ARCHIVED)
        with self.assertRaisesRegex(ValueError, "read-only"):
            self.services.cycles.connect_project.execute(cycle.id, self.project.id)


if __name__ == "__main__":
    unittest.main()
