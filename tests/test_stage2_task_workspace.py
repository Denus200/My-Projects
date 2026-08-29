from __future__ import annotations

import unittest
import uuid
from datetime import date, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import flet as ft

from overlord.bootstrap import bootstrap
from overlord.modules.blockers.domain import BlockerType
from overlord.modules.tasks.domain import TaskLifecycle, TaskProjectAssignment
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
    for name in ("title",):
        child = getattr(control, name, None)
        if isinstance(child, ft.Control):
            values.extend(_all_copy(child))
    for name in ("controls", "actions", "items"):
        for child in getattr(control, name, ()) or ():
            values.extend(_all_copy(child))
    return values


def _walk(control):
    yield control
    for name in ("title", "content"):
        content = getattr(control, name, None)
        if isinstance(content, ft.Control):
            yield from _walk(content)
    for name in ("controls", "actions", "items"):
        for child in getattr(control, name, ()) or ():
            yield from _walk(child)


def _role(control, role: str):
    return next(
        item
        for item in _walk(control)
        if isinstance(getattr(item, "data", None), dict) and item.data.get("role") == role
    )


def _roles(control, role: str):
    return [
        item
        for item in _walk(control)
        if isinstance(getattr(item, "data", None), dict)
        and item.data.get("role") == role
    ]


def _kanban_columns(workspace: ft.Control) -> list[ft.Control]:
    return list(_role(workspace, "kanban-columns").controls)


def _kanban_column(workspace: ft.Control, key: str) -> ft.Control:
    return next(column for column in _kanban_columns(workspace) if column.data["column"] == key)


def _view_tab(workspace: ft.Control, key: str) -> ft.Control:
    return next(
        control
        for control in _roles(workspace, "segmented-tab")
        if control.data.get("tab") == key
    )


def _navigation_action(workspace: ft.Control, action: str) -> ft.Control:
    return next(
        control
        for control in _roles(workspace, "segmented-tab-navigation-action")
        if control.data.get("action") == action
    )


def _week_day(workspace: ft.Control, day: date) -> ft.Control:
    return next(
        control
        for control in _roles(workspace, "week-day-column")
        if control.data.get("day") == day.isoformat()
    )


def _month_day(workspace: ft.Control, day: date) -> ft.Control:
    return next(
        control
        for control in _roles(workspace, "month-day-cell")
        if control.data.get("day") == day.isoformat()
    )


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

    def test_kanban_has_four_reference_columns_with_derived_attention_group(self):
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
        columns = _kanban_columns(workspace)
        self.assertEqual(4, len(columns))
        titles = [_role(column, "kanban-column-header").controls[0].value for column in columns]
        self.assertEqual(["Planned", "In Progress", "Needs Attention", "Completed"], titles)
        column_copy = {column.data["column"]: set(_all_copy(column)) for column in columns}
        self.assertIn("Undated", column_copy["planned"])
        self.assertIn("Today", column_copy["in_progress"])
        self.assertIn("Missed", column_copy["needs_attention"])
        self.assertIn("Archived", column_copy["needs_attention"])
        self.assertIn("Done", column_copy["completed"])
        self.assertEqual(
            [1, 1, 2, 1],
            [item.data["count"] for item in _roles(workspace, "kanban-column-count")],
        )

    def test_workspace_layout_uses_parent_space_and_independent_column_scrolls(self):
        expanded = self.build(AppSessionState(route="/tasks", sidebar_collapsed=False))
        self.assertIsInstance(expanded, ft.Container)
        self.assertEqual("workspace-page", expanded.data["layout"])
        self.assertTrue(expanded.expand)
        self.assertEqual((24, 24, 16, 16), (
            expanded.padding.left,
            expanded.padding.right,
            expanded.padding.top,
            expanded.padding.bottom,
        ))
        view_host = _role(expanded, "task-view-host")
        toolbar = _role(expanded, "tasks-toolbar")
        self.assertTrue(view_host.expand)
        self.assertIsNone(view_host.width)
        self.assertIsNone(view_host.height)
        self.assertIsNone(toolbar.width)
        board = _role(expanded, "kanban-board")
        self.assertIs(ft.ScrollMode.AUTO, board.scroll)
        self.assertTrue(board.expand)
        self.assertIsNone(board.width)
        self.assertIsNone(board.height)
        self.assertEqual("horizontal-scroll", board.data["narrow_behavior"])
        self.assertEqual("view-host", board.data["size_source"])
        self.assertEqual(16, board.spacing)
        self.assertEqual(16, board.data["bottom_inset"])
        self.assertEqual(16, _role(expanded, "kanban-columns").spacing)
        self.assertEqual(288, _role(expanded, "kanban-add-section").width)
        task_lists = _roles(expanded, "kanban-column-task-list")
        self.assertEqual(4, len(task_lists))
        self.assertTrue(all(item.expand for item in task_lists))
        self.assertTrue(all(item.scroll is ft.ScrollMode.AUTO for item in task_lists))

        collapsed = self.build(AppSessionState(route="/tasks", sidebar_collapsed=True))
        collapsed_host = _role(collapsed, "task-view-host")
        collapsed_board = _role(collapsed, "kanban-board")
        self.assertTrue(collapsed_host.expand)
        self.assertIsNone(collapsed_host.width)
        self.assertIsNone(collapsed_host.height)
        self.assertTrue(collapsed_board.expand)
        self.assertIsNone(collapsed_board.width)
        self.assertIsNone(collapsed_board.height)
        self.assertEqual(288, _role(collapsed, "kanban-add-section").width)
        self.assertEqual(48, _role(collapsed, "tasks-toolbar").data["reference_height"])

    def test_search_projection_updates_counts_without_pruning_hidden_task_order(self):
        tasks = [
            self.services.tasks.create_task.execute(None, title)
            for title in ("Alpha", "Bravo", "Charlie")
        ]
        state = AppSessionState(route="/tasks")
        workspace = self.build(state)
        original_order = tuple(state.task_card_order["planned"])
        self.assertEqual({task.id for task in tasks}, set(original_order))
        search = next(item for item in _walk(workspace) if isinstance(item, ft.TextField))

        with patch.object(ft.Control, "update", lambda _control: None):
            search.value = "Bravo"
            search.on_change(None)
        self.assertEqual(original_order, tuple(state.task_card_order["planned"]))
        self.assertEqual(
            1,
            _role(_kanban_column(workspace, "planned"), "kanban-column-count").data["count"],
        )

        with patch.object(ft.Control, "update", lambda _control: None):
            search.value = ""
            search.on_change(None)
        self.assertEqual(original_order, tuple(state.task_card_order["planned"]))
        self.assertEqual(
            3,
            _role(_kanban_column(workspace, "planned"), "kanban-column-count").data["count"],
        )

    def test_project_filter_matches_any_normalized_task_project_link(self):
        first = self.services.projects.create_project.execute("First")
        second = self.services.projects.create_project.execute("Second")
        linked = self.services.tasks.create_task.execute(
            None,
            "Multi-project Task",
            project_links=(
                TaskProjectAssignment(first.id),
                TaskProjectAssignment(second.id),
            ),
        )
        self.services.tasks.create_task.execute(first.id, "First only")
        workspace = self.build()
        project_filter = _role(workspace, "tasks-toolbar-filters").controls[2]

        with patch.object(ft.Control, "update", lambda _control: None):
            project_filter.value = str(second.id)
            project_filter.on_select(None)
        planned = _kanban_column(workspace, "planned")
        self.assertEqual(1, _role(planned, "kanban-column-count").data["count"])
        self.assertIn(linked.title, _all_copy(planned))
        self.assertNotIn("First only", _all_copy(planned))

    def test_contextual_add_uses_no_date_in_planned_and_today_in_progress(self):
        workspace = self.build()
        with patch.object(ft.Control, "update", lambda _control: None):
            _role(_kanban_column(workspace, "planned"), "kanban-column-add").on_click(None)
        planned_dialog = self.page.dialogs.pop()
        self.assertIsNone(planned_dialog.data["state"].scheduled_date)

        with patch.object(ft.Control, "update", lambda _control: None):
            _role(_kanban_column(workspace, "in_progress"), "kanban-column-add").on_click(None)
        today_dialog = self.page.dialogs.pop()
        self.assertEqual(self.today, today_dialog.data["state"].scheduled_date)

    def test_week_day_add_prefills_the_selected_date(self):
        state = AppSessionState(route="/tasks")
        workspace = self.build(state)
        with patch.object(ft.Control, "update", lambda _control: None):
            _view_tab(workspace, "week").on_click(None)
        self.assertEqual("week", state.task_view_mode)
        selected_day = date.fromisoformat(state.task_calendar_anchor or self.today.isoformat())
        week_start = selected_day - timedelta(days=selected_day.weekday())
        expected_day = week_start + timedelta(days=4)
        with patch.object(ft.Control, "update", lambda _control: None):
            _role(_week_day(workspace, expected_day), "week-day-add").on_click(None)
        dialog = self.page.dialogs[-1]
        self.assertEqual(expected_day, dialog.data["state"].scheduled_date)

    def test_month_view_navigates_forward_and_keeps_day_level_creation(self):
        state = AppSessionState(
            route="/tasks",
            task_calendar_anchor=date(2026, 8, 13).isoformat(),
        )
        workspace = self.build(state)
        with patch.object(ft.Control, "update", lambda _control: None):
            _view_tab(workspace, "month").on_click(None)
        self.assertEqual("month", state.task_view_mode)
        month = _role(workspace, "task-view-host").content
        self.assertGreaterEqual(len(month.controls), 6)

        with patch.object(ft.Control, "update", lambda _control: None):
            _role(workspace, "segmented-tab-navigation-toggle").on_click(None)
            _navigation_action(workspace, "next").on_click(None)
        self.assertEqual("2026-09-01", state.task_calendar_anchor)

        september = _role(workspace, "task-view-host").content
        first_week = september.controls[1]
        future_cell = first_week.controls[2]
        expected_date = date(2026, 9, 2)
        with patch.object(ft.Control, "update", lambda _control: None):
            _role(future_cell, "month-day-add").on_tap(None)
        dialog = self.page.dialogs[-1]
        self.assertEqual(expected_date, dialog.data["state"].scheduled_date)

    def test_month_reference_grid_is_monday_first_responsive_and_scrollable(self):
        anchor = date(2020, 8, 15)
        expanded = self.build(
            AppSessionState(
                route="/tasks",
                task_view_mode="month",
                task_calendar_anchor=anchor.isoformat(),
                sidebar_collapsed=False,
            )
        )
        board = _role(expanded, "month-board")
        self.assertEqual("2020-08-01", board.data["anchor_month"])
        self.assertEqual("2020-07-27", board.data["start"])
        self.assertEqual("2020-09-06", board.data["end"])
        self.assertEqual(6, board.data["week_count"])
        self.assertEqual(42, board.data["day_count"])
        self.assertEqual(tuple(range(7)), board.data["weekday_order"])
        self.assertEqual(8, board.data["column_gap"])
        self.assertEqual(8, board.data["row_gap"])
        self.assertIs(ft.ScrollMode.AUTO, board.scroll)
        self.assertTrue(board.data["vertical_scroll"])
        self.assertEqual(
            ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"],
            _all_copy(_role(expanded, "month-weekday-header")),
        )
        rows = _roles(expanded, "month-week-row")
        self.assertEqual(6, len(rows))
        self.assertTrue(all(len(row.controls) == 7 for row in rows))
        self.assertTrue(all(row.height == 164 and row.spacing == 8 for row in rows))
        cells = _roles(expanded, "month-day-cell")
        self.assertEqual(42, len(cells))
        self.assertTrue(all(cell.expand and cell.height == 164 for cell in cells))
        self.assertTrue(board.expand)
        self.assertEqual("view-host", board.data["size_source"])

        collapsed = self.build(
            AppSessionState(
                route="/tasks",
                task_view_mode="month",
                task_calendar_anchor=anchor.isoformat(),
                sidebar_collapsed=True,
            )
        )
        collapsed_board = _role(collapsed, "month-board")
        self.assertTrue(collapsed_board.expand)
        self.assertEqual("view-host", collapsed_board.data["size_source"])
        collapsed_cells = _roles(collapsed, "month-day-cell")
        self.assertEqual(42, len(collapsed_cells))
        self.assertTrue(all(cell.expand and cell.width is None for cell in collapsed_cells))

    def test_month_adjacent_dates_today_state_compact_cards_and_date_prefill(self):
        anchor = date(2026, 8, 15)
        previous_month_day = date(2026, 7, 31)
        current_month_day = date(2026, 8, 15)
        next_month_day = date(2026, 9, 1)
        adjacent = self.services.tasks.create_task.execute(
            None,
            "Adjacent date task",
            schedule_start_date=previous_month_day,
        )
        current = self.services.tasks.create_task.execute(
            None,
            "Current date task",
            schedule_start_date=current_month_day,
        )
        self.services.tasks.create_task.execute(
            None,
            "Trailing date task",
            schedule_start_date=next_month_day,
        )
        workspace = self.build(
            AppSessionState(
                route="/tasks",
                task_view_mode="month",
                task_calendar_anchor=anchor.isoformat(),
            )
        )
        self.assertFalse(_month_day(workspace, previous_month_day).data["in_current_month"])
        self.assertTrue(_month_day(workspace, current_month_day).data["in_current_month"])
        self.assertFalse(_month_day(workspace, next_month_day).data["in_current_month"])
        current_card = _role(_month_day(workspace, current_month_day), "workspace-task-card")
        self.assertEqual(current.id, current_card.data["task_id"])
        self.assertEqual("compact", current_card.data["variant"])
        adjacent_card = _role(_month_day(workspace, previous_month_day), "workspace-task-card")
        self.assertEqual(adjacent.id, adjacent_card.data["task_id"])

        today_workspace = self.build(
            AppSessionState(
                route="/tasks",
                task_view_mode="month",
                task_calendar_anchor=self.today.isoformat(),
            )
        )
        today_cell = _month_day(today_workspace, self.today)
        self.assertTrue(today_cell.data["today"])
        self.assertTrue(
            all(
                cell.data["today"] == (cell.data["day"] == self.today.isoformat())
                for cell in _roles(today_workspace, "month-day-cell")
            )
        )

        with patch.object(ft.Control, "update", lambda _control: None):
            _role(_month_day(workspace, next_month_day), "month-day-add").on_tap(None)
        self.assertEqual(next_month_day, self.page.dialogs[-1].data["state"].scheduled_date)

    def test_month_keeps_complete_paused_and_blocked_tasks_and_uses_shared_flows(self):
        selected_day = date(2026, 8, 17)
        planned = self.services.tasks.create_task.execute(
            None, "Month planned", schedule_start_date=selected_day
        )
        paused = self.services.tasks.create_task.execute(
            None, "Month paused", schedule_start_date=selected_day
        )
        self.services.tasks.change_lifecycle.execute(
            paused.id, TaskLifecycle.PAUSED, "Paused for Month test"
        )
        blocked = self.services.tasks.create_task.execute(
            None, "Month blocked", schedule_start_date=selected_day
        )
        self.services.tasks.open_blocker.execute(
            blocked.id, BlockerType.OTHER, "Blocked for Month test"
        )
        completed = self.services.tasks.create_task.execute(
            None, "Month completed", schedule_start_date=selected_day
        )
        self.services.tasks.complete_task.execute(completed.id)
        state = AppSessionState(
            route="/tasks",
            task_view_mode="month",
            task_calendar_anchor=selected_day.isoformat(),
        )
        workspace = self.build(state)
        cell = _month_day(workspace, selected_day)
        self.assertEqual(4, cell.data["visible_count"])
        for title in (planned.title, paused.title, blocked.title, completed.title):
            self.assertIn(title, _all_copy(cell))

        task_body = next(
            item
            for item in _roles(cell, "task-body")
            if item.data.get("task_id") == planned.id
        )
        task_body.on_tap(None)
        self.assertEqual("task-details-dialog", self.page.dialogs[-1].data["role"])

        completion = next(
            item
            for item in _roles(cell, "completion")
            if item.data.get("task_id") == planned.id and item.on_tap is not None
        )
        completion.on_tap(None)
        self.assertEqual("complete-task-dialog", self.page.dialogs[-1].data["role"])
        self.assertNotEqual(
            TaskLifecycle.COMPLETED,
            self.services.tasks.get_editor.execute(planned.id).task.lifecycle_status,
        )

    def test_month_busy_day_scrolls_internally_without_stretching_the_grid(self):
        selected_day = date(2026, 8, 19)
        for index in range(12):
            self.services.tasks.create_task.execute(
                None,
                f"Busy Month item {index + 1:02d}",
                schedule_start_date=selected_day,
            )
        workspace = self.build(
            AppSessionState(
                route="/tasks",
                task_view_mode="month",
                task_calendar_anchor=selected_day.isoformat(),
            )
        )
        cell = _month_day(workspace, selected_day)
        task_list = _role(cell, "month-day-task-list")
        self.assertEqual(164, cell.height)
        self.assertEqual(12, cell.data["visible_count"])
        self.assertEqual(12, task_list.data["visible_count"])
        self.assertTrue(task_list.expand)
        self.assertIs(ft.ScrollMode.AUTO, task_list.scroll)
        self.assertEqual(12, len(_roles(cell, "workspace-task-card")))
        self.assertEqual([], [item for item in _walk(_role(workspace, "month-board")) if isinstance(item, ft.Draggable)])

    def test_month_filters_preserve_cells_dates_and_normalized_project_links(self):
        selected_day = date(2026, 8, 20)
        first = self.services.projects.create_project.execute("Month First")
        second = self.services.projects.create_project.execute("Month Second")
        matching = self.services.tasks.create_task.execute(
            None,
            "Alpha multi-project",
            schedule_start_date=selected_day,
            project_links=(
                TaskProjectAssignment(first.id),
                TaskProjectAssignment(second.id),
            ),
        )
        self.services.tasks.create_task.execute(
            first.id, "Bravo first-only", schedule_start_date=selected_day
        )
        state = AppSessionState(
            route="/tasks",
            task_view_mode="month",
            task_calendar_anchor=selected_day.isoformat(),
        )
        workspace = self.build(state)
        search = next(item for item in _walk(workspace) if isinstance(item, ft.TextField))
        project_filter = _role(workspace, "tasks-toolbar-filters").controls[2]

        with patch.object(ft.Control, "update", lambda _control: None):
            project_filter.value = str(second.id)
            project_filter.on_select(None)
        cell = _month_day(workspace, selected_day)
        self.assertEqual(1, cell.data["visible_count"])
        self.assertIn(matching.title, _all_copy(cell))

        with patch.object(ft.Control, "update", lambda _control: None):
            search.value = "missing"
            search.on_change(None)
        self.assertEqual(0, _month_day(workspace, selected_day).data["visible_count"])
        self.assertIn("No Tasks", _all_copy(_month_day(workspace, selected_day)))
        self.assertEqual(42, len(_roles(workspace, "month-day-cell")))

        with patch.object(ft.Control, "update", lambda _control: None):
            search.value = "Alpha"
            search.on_change(None)
        self.assertEqual(1, _month_day(workspace, selected_day).data["visible_count"])
        self.assertEqual(
            selected_day,
            self.services.tasks.get_editor.execute(matching.id).task.schedule_start_date,
        )

        with patch.object(ft.Control, "update", lambda _control: None):
            search.value = ""
            project_filter.value = "all"
            search.on_change(None)
            project_filter.on_select(None)
        self.assertEqual(2, _month_day(workspace, selected_day).data["visible_count"])

    def test_month_navigation_regenerates_calendar_across_years_and_today(self):
        state = AppSessionState(
            route="/tasks",
            task_view_mode="month",
            task_calendar_anchor=date(2026, 12, 15).isoformat(),
        )
        workspace = self.build(state)
        with patch.object(ft.Control, "update", lambda _control: None):
            _role(workspace, "segmented-tab-navigation-toggle").on_click(None)
            _navigation_action(workspace, "next").on_click(None)
        self.assertEqual("2027-01-01", state.task_calendar_anchor)
        january = _role(workspace, "month-board")
        self.assertEqual("2027-01-01", january.data["anchor_month"])
        self.assertEqual("2026-12-28", january.data["start"])

        with patch.object(ft.Control, "update", lambda _control: None):
            _navigation_action(workspace, "previous").on_click(None)
        self.assertEqual("2026-12-01", state.task_calendar_anchor)
        self.assertEqual("2026-12-01", _role(workspace, "month-board").data["anchor_month"])

        with patch.object(ft.Control, "update", lambda _control: None):
            _navigation_action(workspace, "today").on_click(None)
        self.assertEqual(self.today.isoformat(), state.task_calendar_anchor)
        self.assertEqual(
            self.today.replace(day=1).isoformat(),
            _role(workspace, "month-board").data["anchor_month"],
        )

    def test_month_task_date_changes_and_deletion_refresh_the_correct_cells(self):
        old_day = date(2026, 8, 9)
        new_day = date(2026, 8, 17)
        task = self.services.tasks.create_task.execute(
            None, "Move and delete in Month", schedule_start_date=old_day
        )
        state = AppSessionState(
            route="/tasks",
            task_view_mode="month",
            task_calendar_anchor=old_day.isoformat(),
        )
        workspace = self.build(state)
        self.assertIn(task.title, _all_copy(_month_day(workspace, old_day)))

        self.services.tasks.update_task.execute(task.id, schedule_start_date=new_day)
        moved = self.build(state)
        self.assertNotIn(task.title, _all_copy(_month_day(moved, old_day)))
        self.assertIn(task.title, _all_copy(_month_day(moved, new_day)))

        body = next(
            item
            for item in _roles(_month_day(moved, new_day), "task-body")
            if item.data.get("task_id") == task.id
        )
        body.on_tap(None)
        details = self.page.dialogs[-1]
        _role(details, "delete-task").on_click(None)
        confirmation = self.page.dialogs[-1]
        self.assertEqual("delete-task-confirmation", confirmation.data["role"])
        with patch.object(ft.Control, "update", lambda _control: None):
            _role(confirmation, "delete-task-confirm").on_click(None)
        with self.assertRaisesRegex(ValueError, "does not exist"):
            self.services.tasks.get_editor.execute(task.id)
        self.assertGreaterEqual(self.refresh_count, 1)

    def test_week_reference_layout_has_seven_fixed_columns_and_nested_scrolls(self):
        start = self.today - timedelta(days=self.today.weekday())
        for offset, count in ((0, 2), (1, 7), (4, 1)):
            day = start + timedelta(days=offset)
            for index in range(count):
                self.services.tasks.create_task.execute(
                    None,
                    f"Day {offset} Task {index}",
                    schedule_start_date=day,
                )

        expanded = self.build(
            AppSessionState(
                route="/tasks",
                task_view_mode="week",
                task_calendar_anchor=self.today.isoformat(),
                sidebar_collapsed=False,
            )
        )
        board = _role(expanded, "week-board")
        columns = _roles(expanded, "week-day-column")
        self.assertEqual(7, len(columns))
        self.assertEqual(7, board.data["day_count"])
        self.assertEqual(300, board.data["column_width"])
        self.assertEqual(16, board.spacing)
        self.assertIs(ft.ScrollMode.ALWAYS, board.scroll)
        self.assertEqual("always", board.data["scrollbar"])
        self.assertTrue(board.expand)
        self.assertIsNone(board.width)
        self.assertIsNone(board.height)
        self.assertIs(ft.CrossAxisAlignment.STRETCH, board.vertical_alignment)
        self.assertEqual("view-host", board.data["size_source"])
        self.assertFalse(board.tight)
        self.assertTrue(all(column.width == 300 for column in columns))
        self.assertTrue(all(column.height is None for column in columns))
        lists = _roles(expanded, "week-day-task-list")
        self.assertEqual(7, len(lists))
        self.assertTrue(all(item.expand for item in lists))
        self.assertTrue(all(item.scroll is ft.ScrollMode.AUTO for item in lists))
        self.assertEqual(7, _role(_week_day(expanded, start + timedelta(days=1)), "week-day-count").data["count"])

        collapsed = self.build(
            AppSessionState(
                route="/tasks",
                task_view_mode="week",
                task_calendar_anchor=self.today.isoformat(),
                sidebar_collapsed=True,
            )
        )
        collapsed_board = _role(collapsed, "week-board")
        self.assertTrue(collapsed_board.expand)
        self.assertIsNone(collapsed_board.width)
        self.assertIsNone(collapsed_board.height)
        self.assertEqual("view-host", collapsed_board.data["size_source"])
        self.assertFalse(collapsed_board.tight)
        self.assertTrue(
            all(column.width == 300 for column in _roles(collapsed, "week-day-column"))
        )

    def test_week_scroll_viewport_survives_view_switching_and_keeps_nested_scrolls(self):
        state = AppSessionState(
            route="/tasks",
            task_view_mode="week",
            task_calendar_anchor=self.today.isoformat(),
            sidebar_collapsed=False,
        )
        workspace = self.build(state)
        first_board = _role(workspace, "week-board")
        self.assertEqual(7, len(_roles(first_board, "week-day-column")))
        view_host = _role(workspace, "task-view-host")
        self.assertTrue(first_board.expand)
        self.assertTrue(view_host.expand)
        self.assertIsNone(first_board.height)
        self.assertIsNone(view_host.height)

        with patch.object(ft.Control, "update", lambda _control: None):
            _view_tab(workspace, "kanban").on_click(None)
            _view_tab(workspace, "month").on_click(None)
            _view_tab(workspace, "week").on_click(None)

        rebuilt_board = _role(workspace, "week-board")
        self.assertTrue(rebuilt_board.expand)
        self.assertIsNone(rebuilt_board.width)
        self.assertIsNone(rebuilt_board.height)
        self.assertIs(ft.ScrollMode.ALWAYS, rebuilt_board.scroll)
        self.assertEqual(7, len(_roles(rebuilt_board, "week-day-column")))
        nested_lists = _roles(rebuilt_board, "week-day-task-list")
        self.assertEqual(7, len(nested_lists))
        self.assertTrue(all(item.scroll is ft.ScrollMode.AUTO for item in nested_lists))
        self.assertTrue(all(item.expand for item in nested_lists))

    def test_expandable_week_and_month_navigation_reset_on_view_change(self):
        state = AppSessionState(route="/tasks")
        workspace = self.build(state)
        with patch.object(ft.Control, "update", lambda _control: None):
            _view_tab(workspace, "week").on_click(None)
        toggle = _role(workspace, "segmented-tab-navigation-toggle")
        self.assertFalse(toggle.data["expanded"])
        self.assertEqual(273, _role(workspace, "segmented-tabs-surface").width)

        with patch.object(ft.Control, "update", lambda _control: None):
            toggle.on_click(None)
        self.assertEqual("week", state.task_expanded_date_navigation)
        self.assertEqual(3, len(_roles(workspace, "segmented-tab-navigation-action")))
        self.assertEqual(517, _role(workspace, "segmented-tabs-surface").width)

        with patch.object(ft.Control, "update", lambda _control: None):
            _role(workspace, "segmented-tab-navigation-toggle").on_click(None)
        self.assertIsNone(state.task_expanded_date_navigation)
        self.assertEqual([], _roles(workspace, "segmented-tab-navigation-action"))

        with patch.object(ft.Control, "update", lambda _control: None):
            _role(workspace, "segmented-tab-navigation-toggle").on_click(None)
            _view_tab(workspace, "kanban").on_click(None)
            _view_tab(workspace, "week").on_click(None)
        self.assertIsNone(state.task_expanded_date_navigation)
        self.assertFalse(_role(workspace, "segmented-tab-navigation-toggle").data["expanded"])

        with patch.object(ft.Control, "update", lambda _control: None):
            _view_tab(workspace, "month").on_click(None)
            _role(workspace, "segmented-tab-navigation-toggle").on_click(None)
            _view_tab(workspace, "week").on_click(None)
            _view_tab(workspace, "month").on_click(None)
        self.assertIsNone(state.task_expanded_date_navigation)
        self.assertFalse(_role(workspace, "segmented-tab-navigation-toggle").data["expanded"])

    def test_week_navigation_changes_only_the_visible_date_range(self):
        anchor = date(2026, 8, 13)
        state = AppSessionState(
            route="/tasks",
            task_view_mode="week",
            task_calendar_anchor=anchor.isoformat(),
        )
        workspace = self.build(state)
        with patch.object(ft.Control, "update", lambda _control: None):
            _role(workspace, "segmented-tab-navigation-toggle").on_click(None)
            _navigation_action(workspace, "previous").on_click(None)
        self.assertEqual("2026-08-06", state.task_calendar_anchor)
        self.assertEqual("2026-08-03", _role(workspace, "week-board").data["start"])

        with patch.object(ft.Control, "update", lambda _control: None):
            _navigation_action(workspace, "next").on_click(None)
        self.assertEqual(anchor.isoformat(), state.task_calendar_anchor)

        with patch.object(ft.Control, "update", lambda _control: None):
            _navigation_action(workspace, "today").on_click(None)
        self.assertEqual(self.today.isoformat(), state.task_calendar_anchor)

    def test_week_filters_update_counts_without_mutating_dates(self):
        start = self.today - timedelta(days=self.today.weekday())
        project = self.services.projects.create_project.execute("Week Project")
        other = self.services.projects.create_project.execute("Other")
        matching = self.services.tasks.create_task.execute(
            None,
            "Alpha linked",
            schedule_start_date=start,
            project_links=(TaskProjectAssignment(project.id), TaskProjectAssignment(other.id)),
        )
        self.services.tasks.create_task.execute(
            project.id,
            "Bravo linked",
            schedule_start_date=start,
        )
        state = AppSessionState(
            route="/tasks",
            task_view_mode="week",
            task_calendar_anchor=start.isoformat(),
        )
        workspace = self.build(state)
        search = next(item for item in _walk(workspace) if isinstance(item, ft.TextField))
        project_filter = _role(workspace, "tasks-toolbar-filters").controls[2]

        with patch.object(ft.Control, "update", lambda _control: None):
            project_filter.value = str(other.id)
            project_filter.on_select(None)
        self.assertEqual(1, _role(_week_day(workspace, start), "week-day-count").data["count"])
        self.assertIn(matching.title, _all_copy(_week_day(workspace, start)))

        with patch.object(ft.Control, "update", lambda _control: None):
            search.value = "missing"
            search.on_change(None)
        self.assertEqual(0, _role(_week_day(workspace, start), "week-day-count").data["count"])

        with patch.object(ft.Control, "update", lambda _control: None):
            search.value = ""
            project_filter.value = "all"
            search.on_change(None)
            project_filter.on_select(None)
        self.assertEqual(2, _role(_week_day(workspace, start), "week-day-count").data["count"])
        self.assertEqual(start, self.services.tasks.get_editor.execute(matching.id).task.schedule_start_date)

    def test_week_placement_follows_task_date_and_uses_shared_full_cards(self):
        start = self.today - timedelta(days=self.today.weekday())
        tuesday = start + timedelta(days=1)
        thursday = start + timedelta(days=3)
        task = self.services.tasks.create_task.execute(
            None,
            "Move by date",
            schedule_start_date=tuesday,
        )
        state = AppSessionState(
            route="/tasks",
            task_view_mode="week",
            task_calendar_anchor=start.isoformat(),
        )
        workspace = self.build(state)
        card = _role(_week_day(workspace, tuesday), "workspace-task-card")
        self.assertEqual("full", card.data["variant"])
        self.assertEqual([], [item for item in _walk(_role(workspace, "week-board")) if isinstance(item, ft.Draggable)])

        self.services.tasks.update_task.execute(task.id, schedule_start_date=thursday)
        rebuilt = self.build(state)
        self.assertNotIn(task.title, _all_copy(_week_day(rebuilt, tuesday)))
        self.assertIn(task.title, _all_copy(_week_day(rebuilt, thursday)))

    def test_week_scroll_fix_preserves_shared_details_and_completion_actions(self):
        start = self.today - timedelta(days=self.today.weekday())
        selected_day = start + timedelta(days=6)
        task = self.services.tasks.create_task.execute(
            None,
            "Later-day interaction",
            schedule_start_date=selected_day,
        )
        workspace = self.build(
            AppSessionState(
                route="/tasks",
                task_view_mode="week",
                task_calendar_anchor=start.isoformat(),
            )
        )
        sunday = _week_day(workspace, selected_day)
        body = next(
            item
            for item in _roles(sunday, "task-body")
            if item.data.get("task_id") == task.id
        )
        body.on_tap(None)
        self.assertEqual("task-details-dialog", self.page.dialogs[-1].data["role"])

        _role(sunday, "workspace-task-card").on_hover(SimpleNamespace(data="true"))
        completion = next(
            item
            for item in _roles(sunday, "completion")
            if item.data.get("task_id") == task.id and item.on_tap is not None
        )
        completion.on_tap(None)
        self.assertEqual("complete-task-dialog", self.page.dialogs[-1].data["role"])

    def test_task_form_has_collapsed_advanced_options_without_removed_creation_fields(self):
        dialog = build_quick_task_dialog(
            self.services,
            (),
            LIGHT_TOKENS,
            lambda _task: None,
            lambda: None,
        )
        self.assertNotIn("More details", _all_copy(dialog))
        self.assertTrue(_role(dialog, "create-task-title").visible)
        self.assertTrue(_role(dialog, "create-task-description").visible)
        self.assertTrue(_role(dialog, "create-task-date").visible)
        self.assertFalse(_role(dialog, "create-task-advanced").visible)
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
        in_progress_drop_target = _role(
            _kanban_column(workspace, "in_progress"), "kanban-column-card-target"
        )
        with patch.object(ft.Control, "update", lambda _control: None):
            in_progress_drop_target.on_accept(
                _drag_event({"kind": "task", "task_id": task.id, "column": "planned"})
            )
        moved = self.services.tasks.get_editor.execute(task.id).task
        self.assertEqual(self.today, moved.schedule_start_date)

    def test_dragging_card_to_completed_waits_for_canonical_confirmation(self):
        task = self.services.tasks.create_task.execute(None, "Confirm dragged completion")
        workspace = self.build()
        completed_drop_target = _role(
            _kanban_column(workspace, "completed"), "kanban-column-card-target"
        )
        completed_drop_target.on_accept(
            _drag_event({"kind": "task", "task_id": task.id, "column": "planned"})
        )
        self.assertNotEqual(
            "completed",
            self.services.tasks.get_editor.execute(task.id).task.lifecycle_status.value,
        )
        dialog = self.page.dialogs[-1]
        self.assertEqual("complete-task-dialog", dialog.data["role"])
        with patch.object(ft.Control, "update", lambda _control: None):
            _role(dialog, "complete-task-confirm").on_click(None)
        self.assertEqual(
            "completed",
            self.services.tasks.get_editor.execute(task.id).task.lifecycle_status.value,
        )

    def test_dragging_column_header_changes_column_order(self):
        state = AppSessionState(route="/tasks")
        workspace = self.build(state)
        planned_target = _kanban_column(workspace, "planned")
        with patch.object(ft.Control, "update", lambda _control: None):
            planned_target.on_accept(
                _drag_event({"kind": "column", "column": "needs_attention"})
            )
        self.assertEqual(["missed", "archive"], state.task_column_order[:2])

    def test_dragging_card_onto_another_card_reorders_the_column(self):
        first = self.services.tasks.create_task.execute(None, "First")
        second = self.services.tasks.create_task.execute(None, "Second")
        state = AppSessionState(route="/tasks")
        workspace = self.build(state)
        planned = _kanban_column(workspace, "planned")
        card_targets = [
            control
            for control in _walk(planned)
            if isinstance(control, ft.DragTarget)
            and isinstance(getattr(control, "data", None), dict)
            and "before_task_id" in control.data
        ]
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
        planned_body = _kanban_column(workspace, "planned")
        target = next(
            control
            for control in _walk(planned_body)
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
        in_progress_body = _kanban_column(workspace, "in_progress")
        target = next(
            control
            for control in _walk(in_progress_body)
            if isinstance(control, ft.DragTarget) and control.data.get("before_task_id") == first.id
        )
        with patch.object(ft.Control, "update", lambda _control: None):
            target.on_accept(_drag_event({"kind": "task", "task_id": second.id, "column": "in_progress"}))
        self.assertEqual(
            (second.id, first.id),
            tuple(item.task.id for item in self.services.dashboard.execute(self.today).today_tasks),
        )

        rebuilt = self.build(AppSessionState(route="/tasks"))
        rebuilt_body = _kanban_column(rebuilt, "in_progress")
        rebuilt_titles = _all_copy(rebuilt_body)
        self.assertLess(rebuilt_titles.index("Second today"), rebuilt_titles.index("First today"))

    def test_successful_create_and_complete_refresh_without_updating_replaced_workspace_children(self):
        workspace = self.build()
        _role(_kanban_column(workspace, "planned"), "kanban-column-add").on_click(None)
        dialog = self.page.dialogs[-1]
        title = _role(dialog, "create-task-title")
        title.value = "Workspace safe create"

        with patch.object(ft.Control, "update", side_effect=RuntimeError("frozen child update")):
            _role(dialog, "create-task-save").on_click(None)

        created = next(item.task for item in self.services.tasks.list_tasks.execute() if item.task.title == "Workspace safe create")
        rebuilt = self.build()
        card = next(
            item
            for item in _walk(rebuilt)
            if isinstance(getattr(item, "data", None), dict)
            and item.data.get("role") == "workspace-task-card"
            and item.data.get("task_id") == created.id
        )
        card.on_hover(SimpleNamespace(data="true"))
        complete_button = next(
            item
            for item in _walk(card)
            if isinstance(getattr(item, "data", None), dict)
            and item.data.get("role") == "completion"
            and item.on_tap is not None
        )
        with patch.object(ft.Control, "update", side_effect=RuntimeError("frozen child update")):
            complete_button.on_tap(None)

        self.assertNotEqual("completed", self.services.tasks.get_editor.execute(created.id).task.lifecycle_status.value)
        complete_dialog = self.page.dialogs[-1]
        self.assertEqual("complete-task-dialog", complete_dialog.data["role"])
        with patch.object(ft.Control, "update", side_effect=RuntimeError("frozen child update")):
            _role(complete_dialog, "complete-task-confirm").on_click(None)

        self.assertEqual("completed", self.services.tasks.get_editor.execute(created.id).task.lifecycle_status.value)
        self.assertEqual(2, self.refresh_count)


if __name__ == "__main__":
    unittest.main()
