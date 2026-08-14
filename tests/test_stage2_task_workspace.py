from __future__ import annotations

import unittest
import uuid
from datetime import date, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import flet as ft

from overlord.bootstrap import bootstrap
from overlord.ui.components.tasks import build_quick_task_dialog
from overlord.ui.design_system.tokens import LIGHT_TOKENS
from overlord.ui.pages.tasks.page import build_tasks
from overlord.ui.state import AppSessionState


TEST_TEMP_ROOT = Path(__file__).resolve().parents[1] / "data" / "test-tmp"
TEST_TEMP_ROOT.mkdir(parents=True, exist_ok=True)


class FakePage:
    def __init__(self):
        self.dialogs: list[ft.AlertDialog] = []

    def show_dialog(self, dialog):
        self.dialogs.append(dialog)

    def pop_dialog(self):
        return self.dialogs.pop() if self.dialogs else None


def _all_copy(control) -> list[str]:
    values: list[str] = []
    for attribute in ("value", "label", "content"):
        value = getattr(control, attribute, None)
        if isinstance(value, str):
            values.append(value)
        elif isinstance(value, ft.Control):
            values.extend(_all_copy(value))
    for child in getattr(control, "controls", ()) or ():
        values.extend(_all_copy(child))
    return values


def _walk(control):
    yield control
    content = getattr(control, "content", None)
    if isinstance(content, ft.Control):
        yield from _walk(content)
    for child in getattr(control, "controls", ()) or ():
        yield from _walk(child)


def _role(control, role: str):
    return next(
        item
        for item in _walk(control)
        if isinstance(getattr(item, "data", None), dict) and item.data.get("role") == role
    )


def _kanban_body(column: ft.Control) -> ft.Column:
    return column.content.content.content


def _drag_event(data: dict[str, object]):
    return SimpleNamespace(src=SimpleNamespace(data=data))


class Stage2TaskWorkspaceTests(unittest.TestCase):
    def setUp(self):
        self.path = TEST_TEMP_ROOT / f"stage2-{uuid.uuid4().hex}.db"
        self.services = bootstrap(self.path).services
        self.page = FakePage()
        self.today = date.today()
        self.refresh_count = 0

    def tearDown(self):
        self.path.unlink(missing_ok=True)

    def build(self, state: AppSessionState | None = None):
        return build_tasks(
            self.services,
            LIGHT_TOKENS,
            state or AppSessionState(route="/tasks"),
            self.refresh,
            self.fail,
            self.page,
        )

    def refresh(self):
        self.refresh_count += 1

    def test_kanban_has_five_derived_columns(self):
        self.services.tasks.create_task.execute(None, "Undated")
        self.services.tasks.create_task.execute(None, "Today", schedule_start_date=self.today)
        self.services.tasks.create_task.execute(
            None,
            "Missed",
            schedule_start_date=self.today - timedelta(days=1),
            deadline_at=datetime.combine(self.today, datetime.min.time()) - timedelta(minutes=1),
        )
        completed = self.services.tasks.create_task.execute(None, "Done", schedule_start_date=self.today)
        self.services.tasks.complete_task.execute(completed.id)
        self.services.tasks.create_task.execute(None, "Archived", schedule_start_date=self.today - timedelta(days=1))

        workspace = self.build()
        board = _role(workspace, "task-view-host").content
        self.assertEqual(5, len(board.controls))
        titles = [_kanban_body(column).controls[0].content.controls[0].value for column in board.controls]
        self.assertEqual(["Planned", "In progress", "Not completed", "Completed", "Archive"], titles)
        column_copy = [set(_all_copy(column)) for column in board.controls]
        for expected, copy in zip(("Undated", "Today", "Missed", "Done", "Archived"), column_copy):
            self.assertIn(expected, copy)

    def test_contextual_add_uses_no_date_in_planned_and_today_in_progress(self):
        workspace = self.build()
        board = _role(workspace, "task-view-host").content
        with patch.object(ft.Control, "update", lambda _control: None):
            _kanban_body(board.controls[0]).controls[1].on_click(None)
        planned_dialog = self.page.dialogs.pop()
        self.assertEqual("no_date", planned_dialog.content.content.controls[3].value)
        self.assertFalse(planned_dialog.content.content.controls[4].visible)

        with patch.object(ft.Control, "update", lambda _control: None):
            _kanban_body(board.controls[1]).controls[1].on_click(None)
        today_dialog = self.page.dialogs.pop()
        self.assertEqual("today", today_dialog.content.content.controls[3].value)
        self.assertFalse(today_dialog.content.content.controls[4].visible)

    def test_week_day_add_prefills_the_selected_date(self):
        state = AppSessionState(route="/tasks")
        workspace = self.build(state)
        with patch.object(ft.Control, "update", lambda _control: None):
            _role(workspace, "task-view-modes").controls[1].on_click(None)
        self.assertEqual("week", state.task_view_mode)
        self.assertTrue(_role(workspace, "task-calendar-header").visible)
        week = _role(workspace, "task-view-host").content
        selected_cell = week.controls[4]
        selected_day = date.fromisoformat(state.task_calendar_anchor or self.today.isoformat())
        week_start = selected_day - timedelta(days=selected_day.weekday())
        expected_day = week_start + timedelta(days=4)
        with patch.object(ft.Control, "update", lambda _control: None):
            selected_cell.content.controls[0].controls[1].on_click(None)
        dialog = self.page.dialogs[-1]
        controls = dialog.content.content.controls
        if expected_day == self.today:
            self.assertEqual("today", controls[3].value)
            self.assertFalse(controls[4].visible)
        elif expected_day == self.today + timedelta(days=1):
            self.assertEqual("tomorrow", controls[3].value)
            self.assertFalse(controls[4].visible)
        else:
            self.assertEqual("choose_date", controls[3].value)
            self.assertTrue(controls[4].visible)
            self.assertEqual(expected_day.strftime("%d.%m.%Y"), controls[4].controls[0].value)

    def test_month_view_navigates_forward_and_keeps_day_level_creation(self):
        state = AppSessionState(
            route="/tasks",
            task_calendar_anchor=date(2026, 8, 13).isoformat(),
        )
        workspace = self.build(state)
        with patch.object(ft.Control, "update", lambda _control: None):
            _role(workspace, "task-view-modes").controls[2].on_click(None)
        self.assertEqual("month", state.task_view_mode)
        month = _role(workspace, "task-view-host").content
        self.assertGreaterEqual(len(month.controls), 6)

        with patch.object(ft.Control, "update", lambda _control: None):
            _role(workspace, "task-calendar-header").controls[2].on_click(None)
        self.assertEqual("2026-09-01", state.task_calendar_anchor)

        september = _role(workspace, "task-view-host").content
        first_week = september.controls[1]
        future_cell = first_week.controls[2]
        expected_date = date(2026, 9, 2)
        with patch.object(ft.Control, "update", lambda _control: None):
            future_cell.content.controls[0].controls[1].on_click(None)
        controls = self.page.dialogs[-1].content.content.controls
        self.assertEqual("choose_date", controls[3].value)
        self.assertEqual(expected_date.strftime("%d.%m.%Y"), controls[4].controls[0].value)

    def test_task_form_has_collapsed_advanced_options_without_removed_creation_fields(self):
        dialog = build_quick_task_dialog(
            self.services,
            (),
            LIGHT_TOKENS,
            lambda _task: None,
            lambda: None,
        )
        self.assertNotIn("More details", _all_copy(dialog))
        controls = dialog.content.content.controls
        self.assertEqual([True, True, True, True], [controls[index].visible for index in range(4)])
        self.assertFalse(controls[6].visible)
        copy = _all_copy(dialog)
        self.assertNotIn("Definition of Done", copy)
        self.assertNotIn("Next Action", copy)
        self.assertNotIn("Connections", copy)
        self.assertNotIn("Blocker type", copy)

    def test_cycles_are_task_relationships_and_can_be_replaced(self):
        cycle = self.services.cycles.create_cycle.execute("Focus Cycle", "Ship Stage 2", self.today)
        task = self.services.tasks.create_task.execute(None, "Connected", cycle_ids=(cycle.id,))
        listed = self.services.tasks.list_tasks.execute()
        self.assertEqual(("Focus Cycle",), listed[0].cycle_titles)
        editor = self.services.tasks.get_editor.execute(task.id)
        self.assertEqual((cycle.id,), editor.connected_cycle_ids)

        self.services.tasks.update_task.execute(task.id, cycle_ids=())
        self.assertEqual((), self.services.tasks.get_editor.execute(task.id).connected_cycle_ids)

    def test_dragging_card_to_in_progress_reschedules_it_for_today(self):
        task = self.services.tasks.create_task.execute(None, "Move me")
        workspace = self.build()
        board = _role(workspace, "task-view-host").content
        in_progress_drop_target = board.controls[1].content
        with patch.object(ft.Control, "update", lambda _control: None):
            in_progress_drop_target.on_accept(
                _drag_event({"kind": "task", "task_id": task.id, "column": "planned"})
            )
        moved = self.services.tasks.get_editor.execute(task.id).task
        self.assertEqual(self.today, moved.schedule_start_date)

    def test_dragging_column_header_changes_column_order(self):
        state = AppSessionState(route="/tasks")
        workspace = self.build(state)
        planned_target = _role(workspace, "task-view-host").content.controls[0]
        with patch.object(ft.Control, "update", lambda _control: None):
            planned_target.on_accept(_drag_event({"kind": "column", "column": "archive"}))
        self.assertEqual("archive", state.task_column_order[0])

    def test_dragging_card_onto_another_card_reorders_the_column(self):
        first = self.services.tasks.create_task.execute(None, "First")
        second = self.services.tasks.create_task.execute(None, "Second")
        state = AppSessionState(route="/tasks")
        workspace = self.build(state)
        planned_body = _kanban_body(_role(workspace, "task-view-host").content.controls[0])
        card_targets = [control for control in planned_body.controls if isinstance(control, ft.DragTarget)]
        target = next(control for control in card_targets if control.data["before_task_id"] == first.id)
        with patch.object(ft.Control, "update", lambda _control: None):
            target.on_accept(_drag_event({"kind": "task", "task_id": second.id, "column": "planned"}))
        self.assertLess(
            state.task_card_order["planned"].index(second.id),
            state.task_card_order["planned"].index(first.id),
        )

    def test_kanban_dragging_is_exposed_only_by_the_shared_six_dot_handle(self):
        task = self.services.tasks.create_task.execute(None, "Handle only")
        workspace = self.build()
        planned_body = _kanban_body(_role(workspace, "task-view-host").content.controls[0])
        target = next(
            control
            for control in planned_body.controls
            if isinstance(control, ft.DragTarget) and control.data.get("before_task_id") == task.id
        )
        handles = [item for item in _walk(target) if isinstance(item, ft.Draggable)]
        self.assertEqual(1, len(handles))
        self.assertEqual("task-drag-handle", handles[0].data["role"])
        self.assertEqual(task.id, handles[0].data["task_id"])
        self.assertEqual(1, len([item for item in _walk(target) if getattr(item, "data", None) == {
            "role": "task-body",
            "task_id": task.id,
        }]))

    def test_today_column_manual_order_reuses_persistent_day_order(self):
        first = self.services.tasks.create_task.execute(None, "First today", schedule_start_date=self.today)
        second = self.services.tasks.create_task.execute(None, "Second today", schedule_start_date=self.today)
        workspace = self.build(AppSessionState(route="/tasks"))
        in_progress_body = _kanban_body(_role(workspace, "task-view-host").content.controls[1])
        target = next(
            control
            for control in in_progress_body.controls
            if isinstance(control, ft.DragTarget) and control.data.get("before_task_id") == first.id
        )
        with patch.object(ft.Control, "update", lambda _control: None):
            target.on_accept(_drag_event({"kind": "task", "task_id": second.id, "column": "in_progress"}))
        self.assertEqual(
            (second.id, first.id),
            tuple(item.task.id for item in self.services.dashboard.execute(self.today).today_tasks),
        )

        rebuilt = self.build(AppSessionState(route="/tasks"))
        rebuilt_body = _kanban_body(_role(rebuilt, "task-view-host").content.controls[1])
        rebuilt_titles = _all_copy(rebuilt_body)
        self.assertLess(rebuilt_titles.index("Second today"), rebuilt_titles.index("First today"))

    def test_successful_create_and_complete_refresh_without_updating_replaced_workspace_children(self):
        workspace = self.build()
        board = _role(workspace, "task-view-host").content
        _kanban_body(board.controls[0]).controls[1].on_click(None)
        dialog = self.page.dialogs[-1]
        title = next(item for item in _walk(dialog) if isinstance(item, ft.TextField) and item.label == "Title")
        title.value = "Workspace safe create"

        with patch.object(ft.Control, "update", side_effect=RuntimeError("frozen child update")):
            dialog.actions[-1].on_click(None)

        created = next(item.task for item in self.services.tasks.list_tasks.execute() if item.task.title == "Workspace safe create")
        rebuilt = self.build()
        card = next(
            item
            for item in _walk(rebuilt)
            if isinstance(getattr(item, "data", None), dict)
            and item.data.get("role") == "workspace-task-card"
            and item.data.get("task_id") == created.id
        )
        complete_button = next(item for item in _walk(card) if isinstance(item, ft.Button) and item.on_click is not None)
        with patch.object(ft.Control, "update", side_effect=RuntimeError("frozen child update")):
            complete_button.on_click(None)

        self.assertEqual("completed", self.services.tasks.get_editor.execute(created.id).task.lifecycle_status.value)
        self.assertEqual(2, self.refresh_count)


if __name__ == "__main__":
    unittest.main()
