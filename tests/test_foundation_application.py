import sqlite3
import unittest
import uuid
from contextlib import closing
from datetime import date, datetime, time, timedelta
from pathlib import Path

from overlord.bootstrap import bootstrap
from overlord.modules.blockers.domain import BlockerType
from overlord.modules.cycles.domain import CycleStatus, cycle_end_date
from overlord.modules.tasks.domain import TaskBoardColumn, TaskLifecycle, board_column


TEST_TEMP_ROOT = Path(__file__).resolve().parents[1] / "data" / "test-tmp"
TEST_TEMP_ROOT.mkdir(parents=True, exist_ok=True)


class FoundationApplicationTests(unittest.TestCase):
    def setUp(self):
        self.path = TEST_TEMP_ROOT / f"application-{uuid.uuid4().hex}.db"
        self.services = bootstrap(self.path).services
        self.project = self.services.projects.create_project.execute("Foundation")

    def tearDown(self):
        self.path.unlink(missing_ok=True)

    def test_invalid_schedule_range_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "end date"):
            self.services.tasks.create_task.execute(
                self.project.id,
                "Invalid range",
                schedule_start_date=date.today(),
                schedule_end_date=date.today() - timedelta(days=1),
            )
        self.assertEqual((), self.services.tasks.list_tasks.execute())

    def test_invalid_estimate_is_rejected_at_application_boundary(self):
        with self.assertRaisesRegex(ValueError, "positive"):
            self.services.tasks.create_task.execute(
                self.project.id, "Invalid estimate", estimate_minutes=0
            )

    def test_standalone_task_is_backlog_without_a_plan(self):
        task = self.services.tasks.create_task.execute(None, "  Replace hallway bulb  ")
        editor = self.services.tasks.get_editor.execute(task.id)
        self.assertIsNone(task.project_id)
        self.assertEqual("Replace hallway bulb", task.title)
        self.assertEqual(TaskLifecycle.BACKLOG, task.lifecycle_status)
        self.assertIsNone(editor.task.schedule_start_date)

    def test_project_linked_task_keeps_optional_relationship(self):
        task = self.services.tasks.create_task.execute(self.project.id, "Linked Task")
        self.assertEqual(self.project.id, task.project_id)
        listed = self.services.tasks.list_tasks.execute(project_id=self.project.id)
        self.assertEqual((task.id,), tuple(item.task.id for item in listed))
        updated = self.services.tasks.update_task.execute(task.id, project_id=None)
        self.assertIsNone(updated.project_id)

    def test_no_project_filter_returns_only_standalone_tasks(self):
        standalone = self.services.tasks.create_task.execute(None, "Standalone")
        self.services.tasks.create_task.execute(self.project.id, "Linked")
        matches = self.services.tasks.list_tasks.execute(without_project=True)
        self.assertEqual((standalone.id,), tuple(item.task.id for item in matches))

    def test_quick_task_blocker_is_created_atomically(self):
        task = self.services.tasks.create_task.execute(
            None,
            "Blocked capture",
            blocker_type=BlockerType.CLARITY,
            blocker_description="Need the final dimensions",
        )
        editor = self.services.tasks.get_editor.execute(task.id)
        self.assertEqual(1, len(editor.blockers))
        self.assertEqual("Need the final dimensions", editor.blockers[0].description)

    def test_task_browsing_filters_cover_search_lifecycle_date_flags_and_attention(self):
        today = date.today()
        standalone = self.services.tasks.create_task.execute(
            None, "Urgent standalone errand", importance=True, urgency=True
        )
        linked = self.services.tasks.create_task.execute(
            self.project.id, "Planned Foundation work", schedule_start_date=today, importance=True
        )
        overdue = self.services.tasks.create_task.execute(
            self.project.id, "Overdue blocked work", schedule_start_date=today - timedelta(days=2), urgency=True
        )
        completed = self.services.tasks.create_task.execute(
            self.project.id, "Completed work", schedule_start_date=today
        )
        self.services.tasks.complete_task.execute(completed.id)
        self.services.tasks.open_blocker.execute(
            overdue.id, BlockerType.DEPENDENCY, "Waiting for a response"
        )

        def ids(**filters):
            return {item.task.id for item in self.services.tasks.list_tasks.execute(**filters)}

        self.assertEqual({standalone.id}, ids(search="errand"))
        self.assertIn(completed.id, ids(lifecycle=TaskLifecycle.COMPLETED))
        self.assertIn(linked.id, ids(date_scope="today", reference_date=today))
        self.assertIn(linked.id, ids(date_scope="this_week", reference_date=today))
        self.assertEqual({overdue.id}, ids(date_scope="overdue", reference_date=today))
        self.assertIn(standalone.id, ids(date_scope="unplanned", reference_date=today))
        self.assertTrue({standalone.id, linked.id}.issubset(ids(importance=True)))
        self.assertTrue({standalone.id, overdue.id}.issubset(ids(urgency=True)))
        self.assertIn(overdue.id, ids(attention_only=True))

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

    def test_dashboard_has_no_daily_capacity_limit(self):
        for number in range(1, 9):
            self.services.tasks.create_task.execute(
                self.project.id, f"Today {number}", schedule_start_date=date.today()
            )
        dashboard = self.services.dashboard.execute()
        self.assertEqual(8, len(dashboard.today_tasks))

    def test_schedule_update_changes_when_task_appears(self):
        task = self.services.tasks.create_task.execute(
            self.project.id,
            "Move transparently",
            schedule_start_date=date.today(),
        )
        tomorrow = date.today() + timedelta(days=1)
        self.services.tasks.update_task.execute(task.id, schedule_start_date=tomorrow)
        editor = self.services.tasks.get_editor.execute(task.id)
        self.assertEqual(tomorrow, editor.task.schedule_start_date)
        self.assertFalse(self.services.dashboard.execute(date.today()).today_tasks)
        self.assertEqual((task.id,), tuple(item.task.id for item in self.services.dashboard.execute(tomorrow).today_tasks))

    def test_blocker_does_not_change_task_lifecycle(self):
        task = self.services.tasks.create_task.execute(
            self.project.id, "Blocked but planned", schedule_start_date=date.today()
        )
        blocker = self.services.tasks.open_blocker.execute(task.id, BlockerType.DEPENDENCY, "Waiting for input")
        self.assertEqual(TaskLifecycle.PLANNED, self.services.tasks.get_editor.execute(task.id).task.lifecycle_status)
        self.services.tasks.resolve_blocker.execute(blocker.id, "Input received")
        self.assertEqual(TaskLifecycle.PLANNED, self.services.tasks.get_editor.execute(task.id).task.lifecycle_status)

    def test_dashboard_execution_score_uses_original_week(self):
        task = self.services.tasks.create_task.execute(
            self.project.id,
            "Finish this week",
            definition_of_done="Complete",
            schedule_start_date=date.today(),
        )
        self.services.tasks.complete_task.execute(task.id)
        dashboard = self.services.dashboard.execute(date.today())
        self.assertEqual(1.0, dashboard.execution_score)
        self.assertEqual("Not tracked yet", dashboard.actual_time_label)

    def test_board_columns_are_derived_from_schedule_and_completion(self):
        reference = datetime(2026, 8, 13, 12, 0)
        planned = self.services.tasks.create_task.execute(
            None, "Future", schedule_start_date=date(2026, 8, 14)
        )
        active = self.services.tasks.create_task.execute(
            None,
            "Active range",
            schedule_start_date=date(2026, 8, 12),
            schedule_end_date=date(2026, 8, 18),
        )
        missed = self.services.tasks.create_task.execute(
            None,
            "Missed deadline",
            schedule_start_date=date(2026, 8, 12),
            deadline_at=datetime(2026, 8, 13, 9, 0),
        )
        missed_end_time = self.services.tasks.create_task.execute(
            None,
            "Missed end time",
            schedule_start_date=date(2026, 8, 13),
            schedule_end_date=date(2026, 8, 13),
            schedule_end_time=time(11, 30),
        )
        archived = self.services.tasks.create_task.execute(
            None, "Past appointment", schedule_start_date=date(2026, 8, 12)
        )
        completed = self.services.tasks.create_task.execute(
            None, "Done", schedule_start_date=date(2026, 8, 13)
        )
        completed = self.services.tasks.complete_task.execute(completed.id)

        self.assertEqual(TaskBoardColumn.PLANNED, board_column(planned, reference))
        self.assertEqual(TaskBoardColumn.IN_PROGRESS, board_column(active, reference))
        self.assertEqual(TaskBoardColumn.MISSED, board_column(missed, reference))
        self.assertEqual(TaskBoardColumn.MISSED, board_column(missed_end_time, reference))
        self.assertEqual(TaskBoardColumn.ARCHIVE, board_column(archived, reference))
        self.assertEqual(TaskBoardColumn.COMPLETED, board_column(completed, reference))

    def test_kanban_moves_update_canonical_task_state(self):
        task = self.services.tasks.create_task.execute(
            None,
            "Move across board",
            schedule_start_date=date(2026, 8, 20),
            deadline_at=datetime(2026, 8, 20, 18, 0),
        )
        moved = self.services.tasks.move_to_board_column.execute(
            task.id,
            TaskBoardColumn.IN_PROGRESS,
            selected_day=date(2026, 8, 13),
        )
        self.assertEqual(date(2026, 8, 13), moved.schedule_start_date)
        self.assertIsNone(moved.deadline_at)

        completed = self.services.tasks.move_to_board_column.execute(task.id, TaskBoardColumn.COMPLETED)
        self.assertEqual(TaskLifecycle.COMPLETED, completed.lifecycle_status)
        planned = self.services.tasks.move_to_board_column.execute(task.id, TaskBoardColumn.PLANNED)
        self.assertEqual(TaskLifecycle.BACKLOG, planned.lifecycle_status)
        self.assertIsNone(planned.completed_at)
        self.assertIsNone(planned.schedule_start_date)
        archived = self.services.tasks.move_to_board_column.execute(task.id, TaskBoardColumn.ARCHIVE)
        self.assertEqual(TaskLifecycle.CANCELLED, archived.lifecycle_status)
        self.assertIsNotNone(archived.archived_at)
        with self.assertRaisesRegex(ValueError, "derived"):
            self.services.tasks.move_to_board_column.execute(task.id, TaskBoardColumn.MISSED)

    def test_only_one_cycle_can_be_active(self):
        first = self.services.cycles.create_cycle.execute("First", "Outcome one", date.today())
        second = self.services.cycles.create_cycle.execute("Second", "Outcome two", date.today())
        self.services.cycles.change_status.execute(first.id, CycleStatus.ACTIVE)
        with self.assertRaisesRegex(ValueError, "already active"):
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
