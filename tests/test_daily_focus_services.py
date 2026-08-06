import os
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path

from core.statuses import TaskStatus
from services.project_service import ProjectService
from services.today_service import TodayService
from storage.database import connect_database, initialize_database
from storage.repositories.project_repository import ProjectRepository
from storage.repositories.task_repository import TaskRepository


class DailyFocusServiceTests(unittest.TestCase):
    def setUp(self):
        test_tmp_root = Path(__file__).resolve().parents[1] / "data" / "test-tmp"
        test_tmp_root.mkdir(parents=True, exist_ok=True)
        self.temp_dir = tempfile.TemporaryDirectory(dir=test_tmp_root)
        self.db_path = os.path.join(self.temp_dir.name, "overlord-test.db")
        self.connection = connect_database(self.db_path)
        initialize_database(self.connection)
        self.projects = ProjectService(ProjectRepository(self.connection))
        self.today = TodayService(TaskRepository(self.connection), ProjectRepository(self.connection))

    def tearDown(self):
        self.connection.close()
        self.temp_dir.cleanup()

    def test_creates_project_and_task_for_today(self):
        project = self.projects.create_project("Build Overlord", "Daily focus MVP")
        task = self.today.create_task(
            project_id=project.id,
            title="Create storage layer",
            scheduled_date=date.today(),
            planned_minutes=45,
        )

        tasks = self.today.get_today_tasks()

        self.assertEqual(1, len(tasks))
        self.assertEqual(task.id, tasks[0].id)
        self.assertEqual("Build Overlord", tasks[0].project_title)
        self.assertEqual(TaskStatus.PLANNED.value, tasks[0].status)

    def test_limits_today_screen_to_three_tasks(self):
        project = self.projects.create_project("Portfolio", "")
        for index in range(4):
            self.today.create_task(project.id, f"Task {index}", date.today())

        tasks = self.today.get_today_tasks()

        self.assertEqual(3, len(tasks))
        self.assertEqual(["Task 0", "Task 1", "Task 2"], [task.title for task in tasks])

    def test_ignores_tasks_scheduled_for_other_dates(self):
        project = self.projects.create_project("Room redesign", "")
        self.today.create_task(project.id, "Today task", date.today())
        self.today.create_task(project.id, "Tomorrow task", date.today() + timedelta(days=1))

        tasks = self.today.get_today_tasks()

        self.assertEqual(["Today task"], [task.title for task in tasks])

    def test_updates_status_and_comment(self):
        project = self.projects.create_project("Case study", "")
        task = self.today.create_task(project.id, "Write outline", date.today())

        updated = self.today.update_task_state(
            task.id,
            status=TaskStatus.PARTIAL.value,
            comment="Drafted the structure, examples left.",
        )

        self.assertEqual(TaskStatus.PARTIAL.value, updated.status)
        self.assertEqual("Drafted the structure, examples left.", updated.comment)

    def test_rejects_unknown_status(self):
        project = self.projects.create_project("Guitar", "")
        task = self.today.create_task(project.id, "Practice chord changes", date.today())

        with self.assertRaises(ValueError):
            self.today.update_task_state(task.id, status="maybe")

    def test_rejects_task_without_existing_project(self):
        with self.assertRaises(ValueError):
            self.today.create_task(999, "Orphan task", date.today())

    def test_preserves_data_after_reopening_database(self):
        project = self.projects.create_project("English", "Speaking practice")
        task = self.today.create_task(project.id, "Record a short monologue", date.today())
        self.today.update_task_state(task.id, status=TaskStatus.DONE.value, comment="Done in the morning.")
        self.connection.close()

        reopened = connect_database(self.db_path)
        try:
            initialize_database(reopened)
            today = TodayService(TaskRepository(reopened), ProjectRepository(reopened))

            tasks = today.get_today_tasks()

            self.assertEqual(1, len(tasks))
            self.assertEqual(TaskStatus.DONE.value, tasks[0].status)
            self.assertEqual("Done in the morning.", tasks[0].comment)
        finally:
            reopened.close()


if __name__ == "__main__":
    unittest.main()
