from __future__ import annotations

import unittest
import uuid
from datetime import date
from pathlib import Path
from unittest.mock import patch

import flet as ft

from overlord.bootstrap import bootstrap
from overlord.infrastructure.sqlite.repositories.tasks import SqliteTaskRepository
from overlord.modules.tasks.domain import (
    ChecklistItemDraft,
    TaskLifecycle,
    TaskProjectAssignment,
)
from overlord.ui.components.complete_task import build_complete_task_dialog
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


def _role(control: ft.Control, role: str) -> ft.Control:
    return next(
        item
        for item in _walk(control)
        if isinstance(getattr(item, "data", None), dict) and item.data.get("role") == role
    )


class CompleteTaskFlowTests(unittest.TestCase):
    def setUp(self):
        self.path = TEST_TEMP_ROOT / f"complete-task-{uuid.uuid4().hex}.db"
        self.services = bootstrap(self.path).services
        self.completed = []
        self.closed = 0
        self.errors: list[str] = []

    def tearDown(self):
        self.path.unlink(missing_ok=True)

    def task(self, title: str = "Complete me", **values):
        return self.services.tasks.create_task.execute(None, title, **values)

    def dialog(self, task_id: int):
        return build_complete_task_dialog(
            self.services,
            task_id,
            LIGHT_TOKENS,
            self.completed.append,
            self._close,
            self.errors.append,
            selected_day=date.today(),
        )

    def _close(self):
        self.closed += 1

    def test_atomic_completion_preserves_estimate_relations_and_persists_manual_times(self):
        project = self.services.projects.create_project.execute("Titan")
        plan = self.services.projects.create_plan.execute(project.id, "Current")
        stage = self.services.projects.create_stage.execute(project.id, plan.id, "Delivery")
        task = self.services.tasks.create_task.execute(
            project.id,
            "Measured task",
            schedule_start_date=date.today(),
            estimate_minutes=244,
            project_links=(TaskProjectAssignment(project.id, stage.id),),
            checklist_items=(ChecklistItemDraft("Keep me"),),
        )
        checklist_id = task.checklist_items[0].id

        completed = self.services.tasks.complete_task.execute(
            task.id,
            estimate_minutes=999,
            total_time_minutes=180,
            active_time_minutes=240,
            selected_day=date.today(),
        )

        self.assertEqual(TaskLifecycle.COMPLETED, completed.lifecycle_status)
        self.assertEqual(244, completed.estimate_minutes)
        self.assertEqual(180, completed.total_time_minutes)
        self.assertEqual(240, completed.active_time_minutes)
        self.assertEqual((project.id,), tuple(link.project_id for link in completed.project_links))
        self.assertEqual((stage.id,), tuple(link.stage_id for link in completed.project_links))
        self.assertEqual((checklist_id,), tuple(item.id for item in completed.checklist_items))

        restarted = bootstrap(self.path).services.tasks.get_editor.execute(task.id).task
        self.assertEqual((244, 180, 240), (
            restarted.estimate_minutes,
            restarted.total_time_minutes,
            restarted.active_time_minutes,
        ))

    def test_optional_values_can_remain_null_and_missing_estimate_accepts_large_hours(self):
        empty = self.task(schedule_start_date=date.today())
        completed_empty = self.services.tasks.complete_task.execute(
            empty.id,
            estimate_minutes=None,
            total_time_minutes=None,
            active_time_minutes=None,
        )
        self.assertEqual((None, None, None), (
            completed_empty.estimate_minutes,
            completed_empty.total_time_minutes,
            completed_empty.active_time_minutes,
        ))

        large = self.task("Large duration", schedule_start_date=date.today())
        completed_large = self.services.tasks.complete_task.execute(
            large.id,
            estimate_minutes=9000,
            total_time_minutes=1499,
            active_time_minutes=9000,
        )
        self.assertEqual((9000, 1499, 9000), (
            completed_large.estimate_minutes,
            completed_large.total_time_minutes,
            completed_large.active_time_minutes,
        ))

    def test_failure_after_duration_update_rolls_back_completion_and_all_times(self):
        task = self.task(schedule_start_date=date.today())
        with patch.object(SqliteTaskRepository, "change_lifecycle", side_effect=RuntimeError("fail")):
            with self.assertRaisesRegex(RuntimeError, "fail"):
                self.services.tasks.complete_task.execute(
                    task.id,
                    estimate_minutes=60,
                    total_time_minutes=45,
                    active_time_minutes=30,
                )

        preserved = self.services.tasks.get_editor.execute(task.id).task
        self.assertEqual(TaskLifecycle.PLANNED, preserved.lifecycle_status)
        self.assertEqual((None, None, None), (
            preserved.estimate_minutes,
            preserved.total_time_minutes,
            preserved.active_time_minutes,
        ))

    def test_reopen_preserves_metrics_and_direct_recompletion_does_not_clear_them(self):
        task = self.task(schedule_start_date=date.today())
        self.services.tasks.complete_task.execute(
            task.id,
            estimate_minutes=90,
            total_time_minutes=80,
            active_time_minutes=70,
        )
        self.services.tasks.change_lifecycle.execute(task.id, TaskLifecycle.PLANNED, "Reopened")
        recompleted = self.services.tasks.complete_task.execute(task.id)
        self.assertEqual((90, 80, 70), (
            recompleted.estimate_minutes,
            recompleted.total_time_minutes,
            recompleted.active_time_minutes,
        ))

    def test_dialog_existing_estimate_is_read_only_and_cancel_or_close_persists_nothing(self):
        task = self.task(schedule_start_date=date.today(), estimate_minutes=244)
        dialog = self.dialog(task.id)

        self.assertTrue(dialog.data["estimate_read_only"])
        self.assertTrue(_role(dialog, "complete-estimate-hours").read_only)
        self.assertTrue(_role(dialog, "complete-estimate-minutes").read_only)
        self.assertFalse(_role(dialog, "complete-estimate-hours").disabled)
        self.assertFalse(_role(dialog, "complete-total-hours").disabled)
        self.assertEqual(("4", "4"), (
            _role(dialog, "complete-estimate-hours").value,
            _role(dialog, "complete-estimate-minutes").value,
        ))

        _role(dialog, "complete-task-cancel").on_click(None)
        _role(dialog, "complete-task-close").on_click(None)
        unchanged = self.services.tasks.get_editor.execute(task.id).task
        self.assertEqual(2, self.closed)
        self.assertEqual(TaskLifecycle.PLANNED, unchanged.lifecycle_status)
        self.assertIsNone(unchanged.total_time_minutes)

    def test_dialog_missing_estimate_saves_all_fields_only_on_confirm(self):
        task = self.task(schedule_start_date=date.today())
        dialog = self.dialog(task.id)
        self.assertFalse(dialog.data["estimate_read_only"])
        values = {
            "complete-estimate-hours": "150",
            "complete-estimate-minutes": "0",
            "complete-total-hours": "24",
            "complete-total-minutes": "59",
            "complete-active-hours": "1",
            "complete-active-minutes": "30",
        }
        for role, value in values.items():
            _role(dialog, role).value = value

        with patch.object(ft.Control, "update", lambda _control: None):
            _role(dialog, "complete-task-confirm").on_click(None)

        self.assertEqual(1, len(self.completed))
        result = self.completed[0]
        self.assertEqual(TaskLifecycle.COMPLETED, result.lifecycle_status)
        self.assertEqual((9000, 1499, 90), (
            result.estimate_minutes,
            result.total_time_minutes,
            result.active_time_minutes,
        ))

    def test_minutes_above_fifty_nine_are_rejected_without_completing(self):
        task = self.task(schedule_start_date=date.today())
        dialog = self.dialog(task.id)
        _role(dialog, "complete-total-minutes").value = "60"

        with patch.object(ft.Control, "update", lambda _control: None):
            _role(dialog, "complete-task-confirm").on_click(None)

        unchanged = self.services.tasks.get_editor.execute(task.id).task
        self.assertEqual([], self.completed)
        self.assertEqual(TaskLifecycle.PLANNED, unchanged.lifecycle_status)
        self.assertTrue(_role(dialog, "complete-total-minutes").error)


if __name__ == "__main__":
    unittest.main()
