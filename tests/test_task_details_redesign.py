import sqlite3
import unittest
import uuid
from contextlib import closing
from datetime import date, datetime, time, timedelta
from pathlib import Path
from unittest.mock import patch

import flet as ft

from overlord.bootstrap import bootstrap
from overlord.modules.blockers.domain import BlockerType
from overlord.modules.tasks.domain import (
    ChecklistItemDraft,
    TaskCreationMode,
    TaskDetailsStatus,
    TaskLifecycle,
    TaskProjectAssignment,
    task_details_status,
)
from overlord.ui.components.task_details import build_delete_task_confirmation, build_task_details_dialog
from overlord.ui.design_system.tokens import LIGHT_TOKENS


TEST_TEMP_ROOT = Path(__file__).resolve().parents[1] / "data" / "test-tmp"
TEST_TEMP_ROOT.mkdir(parents=True, exist_ok=True)


def _walk(control: ft.Control):
    yield control
    for name in ("title", "content"):
        child = getattr(control, name, None)
        if isinstance(child, ft.Control):
            yield from _walk(child)
    for name in ("controls", "actions", "items"):
        for child in getattr(control, name, ()) or ():
            yield from _walk(child)


def _role(control: ft.Control, role: str) -> list[ft.Control]:
    return [
        item for item in _walk(control)
        if isinstance(getattr(item, "data", None), dict) and item.data.get("role") == role
    ]


class TaskDetailsApplicationTests(unittest.TestCase):
    def setUp(self):
        self.path = TEST_TEMP_ROOT / f"task-details-{uuid.uuid4().hex}.db"
        self.services = bootstrap(self.path).services
        self.titan = self.services.projects.create_project.execute("Titan", color="#FFC7D2")
        self.overlord = self.services.projects.create_project.execute("Overlord", color="#CCEFF3")
        titan_plan = self.services.projects.create_plan.execute(self.titan.id, "Current")
        self.titan_stage = self.services.projects.create_stage.execute(self.titan.id, titan_plan.id, "UI Design")
        overlord_plan = self.services.projects.create_plan.execute(self.overlord.id, "Stage 2")
        self.overlord_stage = self.services.projects.create_stage.execute(
            self.overlord.id, overlord_plan.id, "Projects"
        )

    def tearDown(self):
        self.path.unlink(missing_ok=True)

    def _save_status(self, task_id: int, status: TaskDetailsStatus):
        task = self.services.tasks.get_editor.execute(task_id).task
        return self.services.tasks.update_details.execute(
            task_id,
            title=task.title,
            description=task.description or "",
            schedule_start_date=task.schedule_start_date,
            deadline_at=task.deadline_at,
            estimate_minutes=task.estimate_minutes,
            project_links=tuple(
                TaskProjectAssignment(link.project_id, link.stage_id) for link in task.project_links
            ),
            checklist_items=(),
            status=status,
        )

    def test_atomic_edit_persists_projects_stages_estimate_and_stable_checklist_ids(self):
        task = self.services.tasks.create_task.execute(
            self.titan.id,
            "Original",
            description="Before",
            schedule_start_date=date.today(),
            estimate_minutes=30,
            project_links=(TaskProjectAssignment(self.titan.id, self.titan_stage.id),),
            creation_mode=TaskCreationMode.DRAFT,
            checklist_items=(
                ChecklistItemDraft("Root", False, (ChecklistItemDraft("Child"),)),
            ),
        )
        root_id, child_id = (item.id for item in task.checklist_items)
        deadline = datetime.combine(date.today() + timedelta(days=2), time(18, 45))

        updated = self.services.tasks.update_details.execute(
            task.id,
            title="Updated",
            description="After",
            schedule_start_date=date.today() + timedelta(days=1),
            deadline_at=deadline,
            estimate_minutes=9000,
            project_links=(
                TaskProjectAssignment(self.overlord.id, self.overlord_stage.id),
                TaskProjectAssignment(self.titan.id, self.titan_stage.id),
            ),
            checklist_items=(
                ChecklistItemDraft(
                    "Root edited",
                    True,
                    (
                        ChecklistItemDraft("Child edited", True, (), child_id),
                        ChecklistItemDraft("New child"),
                    ),
                    root_id,
                ),
            ),
            status=TaskDetailsStatus.IN_PROGRESS,
        )

        self.assertEqual("Updated", updated.title)
        self.assertEqual("After", updated.description)
        self.assertEqual(deadline, updated.deadline_at)
        self.assertEqual(9000, updated.estimate_minutes)
        self.assertEqual(TaskLifecycle.IN_PROGRESS, updated.lifecycle_status)
        self.assertEqual(TaskCreationMode.DRAFT, updated.creation_mode)
        self.assertEqual((self.overlord.id, self.titan.id), tuple(link.project_id for link in updated.project_links))
        self.assertEqual((self.overlord_stage.id, self.titan_stage.id), tuple(link.stage_id for link in updated.project_links))
        self.assertEqual(root_id, updated.checklist_items[0].id)
        self.assertEqual(child_id, updated.checklist_items[1].id)
        self.assertEqual(3, len(updated.checklist_items))
        self.assertAlmostEqual(2 / 3, updated.checklist_progress)

        cleared = self.services.tasks.update_details.execute(
            task.id,
            title=updated.title,
            description=updated.description or "",
            schedule_start_date=updated.schedule_start_date,
            deadline_at=None,
            estimate_minutes=None,
            project_links=tuple(
                TaskProjectAssignment(link.project_id, link.stage_id) for link in updated.project_links
            ),
            checklist_items=(),
        )
        self.assertIsNone(cleared.deadline_at)
        self.assertIsNone(cleared.estimate_minutes)
        self.assertEqual((), cleared.checklist_items)

    def test_working_statuses_blocker_derivation_completion_and_reopen(self):
        task = self.services.tasks.create_task.execute(None, "Status Task", schedule_start_date=date.today())
        self.assertEqual(TaskLifecycle.IN_PROGRESS, self._save_status(task.id, TaskDetailsStatus.IN_PROGRESS).lifecycle_status)
        self.assertEqual(TaskLifecycle.PAUSED, self._save_status(task.id, TaskDetailsStatus.PAUSED).lifecycle_status)

        blocked = self._save_status(task.id, TaskDetailsStatus.BLOCKED)
        editor = self.services.tasks.get_editor.execute(task.id)
        self.assertEqual(TaskLifecycle.PAUSED, blocked.lifecycle_status)
        self.assertEqual(TaskDetailsStatus.BLOCKED, task_details_status(blocked, has_open_blockers=True))
        self.assertEqual(1, len([item for item in editor.blockers if item.resolved_at is None]))

        planned = self._save_status(task.id, TaskDetailsStatus.PLANNED)
        editor = self.services.tasks.get_editor.execute(task.id)
        self.assertEqual(TaskLifecycle.PLANNED, planned.lifecycle_status)
        self.assertEqual([], [item for item in editor.blockers if item.resolved_at is None])

        with self.assertRaisesRegex(ValueError, "Complete Task"):
            self._save_status(task.id, TaskDetailsStatus.COMPLETED)
        self.assertEqual(TaskLifecycle.COMPLETED, self.services.tasks.complete_task.execute(task.id).lifecycle_status)
        reopened = self._save_status(task.id, TaskDetailsStatus.PLANNED)
        self.assertEqual(TaskLifecycle.PLANNED, reopened.lifecycle_status)
        self.assertIsNone(reopened.completed_at)

    def test_invalid_cross_project_stage_rolls_back_all_detail_edits(self):
        task = self.services.tasks.create_task.execute(self.titan.id, "Keep title")
        with self.assertRaisesRegex(ValueError, "belong"):
            self.services.tasks.update_details.execute(
                task.id,
                title="Must roll back",
                description="Must roll back",
                schedule_start_date=None,
                deadline_at=None,
                estimate_minutes=60,
                project_links=(TaskProjectAssignment(self.titan.id, self.overlord_stage.id),),
                checklist_items=(ChecklistItemDraft("Must roll back"),),
            )
        preserved = self.services.tasks.get_editor.execute(task.id).task
        self.assertEqual("Keep title", preserved.title)
        self.assertIsNone(preserved.estimate_minutes)
        self.assertEqual((), preserved.checklist_items)

    def test_delete_disconnects_restrict_relation_and_cascades_only_task_owned_rows(self):
        task = self.services.tasks.create_task.execute(
            self.titan.id,
            "Delete me",
            schedule_start_date=date.today(),
            project_links=(TaskProjectAssignment(self.titan.id, self.titan_stage.id),),
            checklist_items=(ChecklistItemDraft("Owned item"),),
        )
        self.services.tasks.open_blocker.execute(task.id, BlockerType.OTHER, "Owned blocker")
        self.services.tasks.reorder_for_day.execute(date.today(), (task.id,))
        cycle = self.services.cycles.create_cycle.execute("Keep cycle", "Keep outcome", date.today())
        self.services.cycles.connect_task.execute(cycle.id, task.id)

        self.services.tasks.delete_task.execute(task.id)

        with self.assertRaisesRegex(ValueError, "does not exist"):
            self.services.tasks.get_editor.execute(task.id)
        with closing(sqlite3.connect(self.path)) as connection:
            self.assertEqual(0, connection.execute("SELECT COUNT(*) FROM tasks WHERE id=?", (task.id,)).fetchone()[0])
            for table in (
                "task_project_links", "task_checklist_items", "blockers", "task_day_positions",
                "task_status_history", "task_plans", "cycle_tasks",
            ):
                self.assertEqual(
                    0,
                    connection.execute(f"SELECT COUNT(*) FROM {table} WHERE task_id=?", (task.id,)).fetchone()[0],
                )
            self.assertEqual(1, connection.execute("SELECT COUNT(*) FROM projects WHERE id=?", (self.titan.id,)).fetchone()[0])
            self.assertEqual(1, connection.execute("SELECT COUNT(*) FROM project_stages WHERE id=?", (self.titan_stage.id,)).fetchone()[0])
            self.assertEqual(1, connection.execute("SELECT COUNT(*) FROM cycles WHERE id=?", (cycle.id,)).fetchone()[0])
            self.assertEqual([], connection.execute("PRAGMA foreign_key_check").fetchall())

    def test_dialog_states_and_delete_confirmation_are_reusable(self):
        task = self.services.tasks.create_task.execute(
            self.titan.id,
            "Visible Details",
            estimate_minutes=9000,
            project_links=(
                TaskProjectAssignment(self.titan.id, self.titan_stage.id),
                TaskProjectAssignment(self.overlord.id, self.overlord_stage.id),
            ),
            checklist_items=(ChecklistItemDraft("One", True), ChecklistItemDraft("Two")),
        )
        projects = self.services.projects.list_projects.execute()
        dialog = build_task_details_dialog(
            self.services, projects, task.id, date.today(), LIGHT_TOKENS,
            lambda: None, lambda: None, self.fail,
        )
        self.assertEqual("task-details-dialog", dialog.data["role"])
        self.assertEqual([self.titan.id, self.overlord.id], dialog.data["state"].selected_project_ids)
        self.assertEqual(2, len(_role(dialog, "project-stage")))
        self.assertEqual("150", _role(dialog, "estimate-hours")[0].value)
        self.assertEqual(2, len(_role(dialog, "checklist-item")))
        self.assertEqual(5, len(_role(dialog, "task-status-option")))

        cancelled = []
        deleted = []
        confirmation = build_delete_task_confirmation(
            self.services, task.id, LIGHT_TOKENS,
            close_confirmation=lambda: cancelled.append(True),
            on_deleted=lambda: deleted.append(True),
            report_error=self.fail,
        )
        _role(confirmation, "delete-task-cancel")[0].on_click(None)
        self.assertEqual([True], cancelled)
        self.assertEqual(task.id, self.services.tasks.get_editor.execute(task.id).task.id)
        with patch.object(ft.Control, "update", lambda _control: None):
            _role(confirmation, "delete-task-confirm")[0].on_click(None)
        self.assertEqual([True], deleted)
        with self.assertRaisesRegex(ValueError, "does not exist"):
            self.services.tasks.get_editor.execute(task.id)

    def test_completed_status_opens_canonical_confirmation_without_early_mutation(self):
        task = self.services.tasks.create_task.execute(None, "Complete from details")

        class FakePage:
            def __init__(self):
                self.dialogs = []

            def show_dialog(self, dialog):
                self.dialogs.append(dialog)

            def pop_dialog(self):
                return self.dialogs.pop() if self.dialogs else None

        page = FakePage()
        saved = []
        dialog = build_task_details_dialog(
            self.services,
            self.services.projects.list_projects.execute(),
            task.id,
            date.today(),
            LIGHT_TOKENS,
            lambda: saved.append(True),
            lambda: None,
            self.fail,
            page=page,
        )
        completed_option = next(
            item for item in _role(dialog, "task-status-option")
            if item.data["status"] == TaskDetailsStatus.COMPLETED.value
        )
        completed_option.on_click(None)
        self.assertNotEqual(TaskLifecycle.COMPLETED, self.services.tasks.get_editor.execute(task.id).task.lifecycle_status)
        complete_dialog = page.dialogs[-1]
        self.assertEqual("complete-task-dialog", complete_dialog.data["role"])
        with patch.object(ft.Control, "update", lambda _control: None):
            _role(complete_dialog, "complete-task-confirm")[0].on_click(None)
        self.assertEqual(TaskLifecycle.COMPLETED, self.services.tasks.get_editor.execute(task.id).task.lifecycle_status)
        self.assertEqual([True], saved)


if __name__ == "__main__":
    unittest.main()
