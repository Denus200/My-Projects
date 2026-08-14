from __future__ import annotations

import unittest
import uuid
from datetime import date, timedelta
from pathlib import Path

from overlord.bootstrap import bootstrap
from overlord.modules.tasks.domain import TaskBoardColumn, TaskLifecycle


TEST_TEMP_ROOT = Path(__file__).resolve().parents[1] / "data" / "test-tmp"
TEST_TEMP_ROOT.mkdir(parents=True, exist_ok=True)


class TaskPersistenceContractTests(unittest.TestCase):
    def setUp(self):
        self.path = TEST_TEMP_ROOT / f"task-restart-{uuid.uuid4().hex}.db"
        self.today = date.today()

    def tearDown(self):
        self.path.unlink(missing_ok=True)
        for suffix in ("-wal", "-shm"):
            Path(f"{self.path}{suffix}").unlink(missing_ok=True)

    def restart(self):
        return bootstrap(self.path).services

    def test_normal_mode_task_mutations_survive_fresh_bootstrap(self):
        services = self.restart()
        edited = services.tasks.create_task.execute(
            None,
            "Before edit",
            schedule_start_date=self.today + timedelta(days=1),
        )
        first = services.tasks.create_task.execute(None, "First", schedule_start_date=self.today)
        second = services.tasks.create_task.execute(None, "Second", schedule_start_date=self.today)
        moved = services.tasks.create_task.execute(None, "Move between columns")

        services.tasks.update_task.execute(
            edited.id,
            title="After edit",
            schedule_start_date=self.today + timedelta(days=2),
        )
        services = self.restart()
        persisted_edit = services.tasks.get_editor.execute(edited.id).task
        self.assertEqual("After edit", persisted_edit.title)
        self.assertEqual(self.today + timedelta(days=2), persisted_edit.schedule_start_date)

        services.tasks.toggle_completion_for_day.execute(second.id, self.today)
        services = self.restart()
        self.assertEqual(
            TaskLifecycle.COMPLETED,
            services.tasks.get_editor.execute(second.id).task.lifecycle_status,
        )
        services.tasks.toggle_completion_for_day.execute(second.id, self.today)
        services = self.restart()
        self.assertEqual(
            TaskLifecycle.PLANNED,
            services.tasks.get_editor.execute(second.id).task.lifecycle_status,
        )

        services.tasks.reorder_for_day.execute(self.today, (second.id, first.id))
        services = self.restart()
        self.assertEqual(
            (second.id, first.id),
            tuple(item.task.id for item in services.dashboard.execute(self.today).today_tasks),
        )

        services.tasks.move_to_board_column.execute(
            moved.id,
            TaskBoardColumn.IN_PROGRESS,
            selected_day=self.today,
        )
        services = self.restart()
        moved_today = services.tasks.get_editor.execute(moved.id).task
        self.assertEqual(self.today, moved_today.schedule_start_date)
        self.assertEqual(TaskLifecycle.PLANNED, moved_today.lifecycle_status)

        services.tasks.move_to_board_column.execute(moved.id, TaskBoardColumn.PLANNED)
        services = self.restart()
        moved_back = services.tasks.get_editor.execute(moved.id).task
        self.assertIsNone(moved_back.schedule_start_date)
        self.assertEqual(TaskLifecycle.BACKLOG, moved_back.lifecycle_status)


if __name__ == "__main__":
    unittest.main()
