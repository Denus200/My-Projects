from __future__ import annotations

import sqlite3
import unittest
import uuid
from pathlib import Path

from overlord.bootstrap import bootstrap
from overlord.modules.projects.domain import ProjectStageStatus, ProjectStatus
from overlord.modules.tasks.domain import TaskProjectAssignment


TEST_TEMP_ROOT = Path(__file__).resolve().parents[1] / "data" / "test-tmp"
TEST_TEMP_ROOT.mkdir(parents=True, exist_ok=True)


class ProjectsFoundationV10Tests(unittest.TestCase):
    def setUp(self):
        self.path = TEST_TEMP_ROOT / f"projects-v10-{uuid.uuid4().hex}.db"
        self.services = bootstrap(self.path).services

    def tearDown(self):
        self.path.unlink(missing_ok=True)
        for suffix in ("-wal", "-shm"):
            Path(f"{self.path}{suffix}").unlink(missing_ok=True)

    def project(self, title: str, color: str = "#CFEFDA"):
        return self.services.projects.create_project.execute(title, color=color)

    def test_project_color_favorite_edit_status_and_archive_persist(self):
        project = self.services.projects.create_project.execute(
            "Titan",
            "Foundation",
            color="#D7CCFF",
            favorite=True,
        )
        updated = self.services.projects.update_project.execute(
            project.id,
            title="Titan Updated",
            color="#BFEFF3",
            favorite=False,
            status=ProjectStatus.ON_HOLD,
        )
        self.assertEqual("#BFEFF3", updated.color)
        self.assertFalse(updated.favorite)
        self.assertEqual(ProjectStatus.ON_HOLD, updated.status)
        archived = self.services.projects.archive_project.execute(project.id)
        self.assertEqual(ProjectStatus.ARCHIVED, archived.status)
        persisted = bootstrap(self.path).services.projects.list_projects.execute(ProjectStatus.ARCHIVED)[0]
        self.assertEqual("Titan Updated", persisted.title)
        self.assertEqual("#BFEFF3", persisted.color)

    def test_favorite_filter_and_sort_are_independent_from_status(self):
        first = self.project("Zulu")
        second = self.services.projects.create_project.execute(
            "Alpha",
            color="#CFEFDA",
            favorite=True,
            status=ProjectStatus.ON_HOLD,
        )
        favorites = self.services.projects.list_projects.execute(favorite_only=True)
        self.assertEqual((second.id,), tuple(project.id for project in favorites))
        alphabetical = self.services.projects.list_projects.execute(sort="name")
        self.assertEqual((second.id, first.id), tuple(project.id for project in alphabetical))

    def test_task_supports_zero_one_two_and_four_projects(self):
        projects = [self.project(f"Project {number}", f"#{number}{number}{number}{number}{number}{number}") for number in range(1, 5)]
        standalone = self.services.tasks.create_task.execute(None, "Standalone")
        self.assertEqual((), standalone.project_links)
        one = self.services.tasks.create_task.execute(projects[0].id, "One")
        self.assertEqual((projects[0].id,), tuple(link.project_id for link in one.project_links))
        two = self.services.tasks.create_task.execute(
            None,
            "Two",
            project_links=tuple(TaskProjectAssignment(project.id) for project in projects[:2]),
        )
        four = self.services.tasks.create_task.execute(
            None,
            "Four",
            project_links=tuple(TaskProjectAssignment(project.id) for project in projects),
        )
        self.assertEqual(2, len(two.project_links))
        self.assertEqual(4, len(four.project_links))
        item = self.services.tasks.list_tasks.execute(search="Four")[0]
        self.assertEqual(tuple(project.color for project in projects), item.project_colors)

    def test_more_than_four_or_duplicate_projects_are_rejected(self):
        projects = [self.project(f"Project {number}") for number in range(5)]
        with self.assertRaisesRegex(ValueError, "at most 4"):
            self.services.tasks.create_task.execute(
                None,
                "Too many",
                project_links=tuple(TaskProjectAssignment(project.id) for project in projects),
            )
        with self.assertRaisesRegex(ValueError, "same Project"):
            self.services.tasks.create_task.execute(
                None,
                "Duplicate",
                project_links=(TaskProjectAssignment(projects[0].id), TaskProjectAssignment(projects[0].id)),
            )

    def test_unlinking_project_removes_only_that_relationship(self):
        first = self.project("First")
        second = self.project("Second")
        task = self.services.tasks.create_task.execute(
            None,
            "Shared",
            project_links=(TaskProjectAssignment(first.id), TaskProjectAssignment(second.id)),
        )
        updated = self.services.tasks.update_task.execute(
            task.id,
            project_links=(TaskProjectAssignment(second.id),),
        )
        self.assertEqual((second.id,), tuple(link.project_id for link in updated.project_links))
        self.assertEqual((), self.services.tasks.list_tasks.execute(project_id=first.id))
        self.assertEqual((task.id,), tuple(item.task.id for item in self.services.tasks.list_tasks.execute(project_id=second.id)))

    def test_project_plan_stage_assignment_and_cross_project_guard(self):
        titan = self.project("Titan")
        overlord = self.project("Overlord")
        titan_plan = self.services.projects.create_plan.execute(titan.id, "Titan Plan")
        titan_stage = self.services.projects.create_stage.execute(titan.id, titan_plan.id, "UI Design")
        self.assertEqual((), self.services.projects.list_stages.execute(overlord.id))
        task = self.services.tasks.create_task.execute(
            None,
            "Stage-aware",
            project_links=(TaskProjectAssignment(titan.id, titan_stage.id), TaskProjectAssignment(overlord.id)),
        )
        self.assertEqual(titan_stage.id, task.project_links[0].stage_id)
        with self.assertRaisesRegex(ValueError, "linked Project"):
            self.services.tasks.update_task.execute(
                task.id,
                project_links=(TaskProjectAssignment(overlord.id, titan_stage.id),),
            )

    def test_one_stage_per_task_project_pair_and_stage_archive_clears_assignment(self):
        project = self.project("Titan")
        plan = self.services.projects.create_plan.execute(project.id, "Plan")
        stage = self.services.projects.create_stage.execute(project.id, plan.id, "Research")
        task = self.services.tasks.create_task.execute(
            None,
            "Linked",
            project_links=(TaskProjectAssignment(project.id, stage.id),),
        )
        with self.assertRaisesRegex(ValueError, "same Project"):
            self.services.tasks.update_task.execute(
                task.id,
                project_links=(
                    TaskProjectAssignment(project.id, stage.id),
                    TaskProjectAssignment(project.id),
                ),
            )
        self.services.projects.change_stage_status.execute(stage.id, ProjectStageStatus.ARCHIVED)
        persisted = self.services.tasks.get_editor.execute(task.id).task
        self.assertIsNone(persisted.project_links[0].stage_id)

    def test_archiving_project_preserves_linked_tasks(self):
        project = self.project("Archive me")
        task = self.services.tasks.create_task.execute(project.id, "Keep me")
        self.services.projects.archive_project.execute(project.id)
        matches = self.services.tasks.list_tasks.execute(project_id=project.id)
        self.assertEqual((task.id,), tuple(item.task.id for item in matches))

    def test_database_constraints_reject_cross_project_stage(self):
        first = self.project("First")
        second = self.project("Second")
        plan = self.services.projects.create_plan.execute(first.id, "Plan")
        stage = self.services.projects.create_stage.execute(first.id, plan.id, "Stage")
        task = self.services.tasks.create_task.execute(second.id, "Task")
        connection = sqlite3.connect(self.path)
        try:
            connection.execute("PRAGMA foreign_keys=ON")
            with self.assertRaises(sqlite3.IntegrityError):
                connection.execute(
                    "UPDATE task_project_links SET stage_id=? WHERE task_id=? AND project_id=?",
                    (stage.id, task.id, second.id),
                )
        finally:
            connection.close()


if __name__ == "__main__":
    unittest.main()
