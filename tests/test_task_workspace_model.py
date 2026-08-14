from __future__ import annotations

import unittest
from datetime import date, datetime
from types import SimpleNamespace

from overlord.app.read_models import TaskListItem
from overlord.modules.tasks.domain import Task, TaskBoardColumn, TaskLifecycle
from overlord.ui.components.task_workspace_controller import TaskWorkspaceController
from overlord.ui.components.task_ordering import TaskOrderController, moved_task_ids
from overlord.ui.components.task_workspace_model import (
    group_board_items,
    merged_today_order,
    month_shift,
    month_weeks,
    moved_card_orders,
    normalized_column_order,
    reconcile_card_order,
    reordered_columns,
    scheduled_items_for_day,
    task_query_filters,
    week_start,
)
from overlord.ui.state import AppSessionState, TaskFilterState, TaskWorkspaceState


def _item(
    task_id: int,
    *,
    scheduled_for: date | None = None,
    lifecycle: TaskLifecycle = TaskLifecycle.PLANNED,
) -> TaskListItem:
    timestamp = datetime(2026, 8, 13, 9, 0)
    return TaskListItem(
        Task(
            id=task_id,
            project_id=None,
            title=f"Task {task_id}",
            lifecycle_status=lifecycle,
            created_at=timestamp,
            updated_at=timestamp,
            schedule_start_date=scheduled_for,
        ),
        None,
    )


class _Command:
    def __init__(self, callback):
        self.callback = callback

    def execute(self, *args, **kwargs):
        return self.callback(*args, **kwargs)


class TaskWorkspaceModelTests(unittest.TestCase):
    def test_shared_task_order_transform_moves_before_or_to_end(self):
        self.assertEqual((3, 1, 2), moved_task_ids((1, 2, 3), 3, 1))
        self.assertEqual((2, 3, 1), moved_task_ids((1, 2, 3), 1, None))
        self.assertEqual((1, 2, 3), moved_task_ids((1, 2, 3), 99, 1))

    def test_calendar_projections_preserve_week_and_month_boundaries(self):
        anchor = date(2026, 8, 13)
        self.assertEqual(date(2026, 8, 10), week_start(anchor, 0))
        self.assertEqual(date(2026, 8, 9), week_start(anchor, 6))
        self.assertEqual(date(2026, 9, 1), month_shift(anchor, 1))
        weeks = month_weeks(anchor, 0)
        self.assertEqual(date(2026, 7, 27), weeks[0][0])
        self.assertEqual(date(2026, 9, 6), weeks[-1][-1])
        self.assertTrue(all(len(week) == 7 for week in weeks))

    def test_query_filter_projection_preserves_project_variants(self):
        self.assertEqual({"search": "alpha"}, task_query_filters("alpha", "all"))
        self.assertEqual(
            {"search": "alpha", "without_project": True},
            task_query_filters("alpha", "none"),
        )
        self.assertEqual(
            {"search": "alpha", "project_id": 7},
            task_query_filters("alpha", "7"),
        )

    def test_board_and_day_projections_keep_input_order(self):
        selected_day = date(2026, 8, 13)
        planned = _item(1)
        today = _item(2, scheduled_for=selected_day)
        completed = _item(
            3,
            scheduled_for=selected_day,
            lifecycle=TaskLifecycle.COMPLETED,
        )
        items = (planned, today, completed)
        grouped = group_board_items(items, datetime(2026, 8, 13, 12, 0))
        self.assertEqual((planned,), grouped[TaskBoardColumn.PLANNED])
        self.assertEqual((today,), grouped[TaskBoardColumn.IN_PROGRESS])
        self.assertEqual((completed,), grouped[TaskBoardColumn.COMPLETED])
        self.assertEqual((today, completed), scheduled_items_for_day(items, selected_day))

    def test_column_and_card_order_transformations_preserve_existing_rules(self):
        self.assertEqual(
            ["archive", "planned", "in_progress", "missed", "completed"],
            normalized_column_order(["unknown", "archive"]),
        )
        self.assertEqual(
            ["archive", "planned", "in_progress", "missed", "completed"],
            reordered_columns(
                ["planned", "in_progress", "missed", "completed", "archive"],
                "archive",
                "planned",
            ),
        )
        first, second = _item(1), _item(2)
        reconciled, ordered = reconcile_card_order([2, 99], (first, second))
        self.assertEqual([2, 1], reconciled)
        self.assertEqual((second, first), ordered)
        moved = moved_card_orders(
            {"planned": [1, 2], "in_progress": [3]},
            2,
            "in_progress",
            3,
        )
        self.assertEqual([1], moved["planned"])
        self.assertEqual([2, 3], moved["in_progress"])
        self.assertEqual((3, 2, 1, 4), merged_today_order((1, 2, 3, 4), [3, 1]))


class TaskWorkspaceControllerTests(unittest.TestCase):
    def test_shared_order_controller_owns_the_per_day_persistence_boundary(self):
        calls: list[tuple[object, ...]] = []
        services = SimpleNamespace(
            tasks=SimpleNamespace(
                reorder_for_day=_Command(
                    lambda day, task_ids: calls.append((day, task_ids))
                )
            )
        )
        selected_day = date(2026, 8, 13)
        controller = TaskOrderController(services)

        moved = controller.move_before_for_day(selected_day, (1, 2, 3), 3, 1)
        unchanged = controller.move_before_for_day(selected_day, moved, 3, 1)

        self.assertEqual((3, 1, 2), moved)
        self.assertEqual(moved, unchanged)
        self.assertEqual([(selected_day, (3, 1, 2))], calls)

    def test_create_save_and_change_callbacks_preserve_ui_effect_order(self):
        controller = TaskWorkspaceController(SimpleNamespace(), TaskWorkspaceState())
        calls: list[str] = []
        close = lambda: calls.append("close")
        render = lambda: calls.append("render")

        controller.task_committed(close, render, lambda: calls.append("created"))
        controller.task_committed(close, render, lambda: calls.append("saved"))
        controller.task_changed(close, render, lambda: calls.append("reopen"))

        self.assertEqual(
            [
                "close",
                "render",
                "created",
                "close",
                "render",
                "saved",
                "close",
                "render",
                "reopen",
            ],
            calls,
        )

    def test_session_state_keeps_legacy_access_on_one_workspace_owner(self):
        filters = TaskFilterState(search="Captured", project="none")
        state = AppSessionState(
            task_filters=filters,
            task_view_mode="month",
            task_calendar_anchor="2026-08-13",
            task_column_order=["archive"],
            task_card_order={"archive": [3]},
        )
        self.assertIs(filters, state.task_workspace.filters)
        self.assertEqual("month", state.task_workspace.view_mode)
        self.assertEqual("2026-08-13", state.task_workspace.calendar_anchor)
        self.assertIs(state.task_column_order, state.task_workspace.column_order)
        self.assertIs(state.task_card_order, state.task_workspace.card_order)

    def test_move_to_today_preserves_command_order_and_persisted_sequence(self):
        today = date(2026, 8, 13)
        calls: list[tuple[object, ...]] = []
        current = _item(1).task
        scheduled = (_item(2, scheduled_for=today), _item(1, scheduled_for=today))

        services = SimpleNamespace(
            tasks=SimpleNamespace(
                get_editor=_Command(
                    lambda task_id: calls.append(("get", task_id))
                    or SimpleNamespace(task=current)
                ),
                move_to_board_column=_Command(
                    lambda task_id, target: calls.append(("move", task_id, target))
                ),
                reorder_for_day=_Command(
                    lambda day, task_ids: calls.append(("reorder", day, task_ids))
                ),
            ),
            dashboard=_Command(
                lambda day: calls.append(("dashboard", day))
                or SimpleNamespace(today_tasks=scheduled)
            ),
        )
        workspace_state = TaskWorkspaceState(
            card_order={"planned": [1], "in_progress": [2]}
        )
        controller = TaskWorkspaceController(services, workspace_state, today=today)
        controller.initialize_view()

        result = controller.move_card(1, TaskBoardColumn.IN_PROGRESS, before_task_id=2)

        self.assertTrue(result.succeeded)
        self.assertEqual(
            [
                ("get", 1),
                ("move", 1, TaskBoardColumn.IN_PROGRESS),
                ("dashboard", today),
                ("reorder", today, (1, 2)),
            ],
            calls,
        )
        self.assertEqual([], workspace_state.card_order["planned"])
        self.assertEqual([1, 2], workspace_state.card_order["in_progress"])


if __name__ == "__main__":
    unittest.main()
