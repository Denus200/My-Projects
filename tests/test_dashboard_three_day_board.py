from __future__ import annotations

import unittest
import uuid
from datetime import date, time, timedelta
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import flet as ft

from overlord.bootstrap import bootstrap
from overlord.modules.tasks.domain import TaskLifecycle
from overlord.ui.design_system.tokens import DARK_TOKENS, LIGHT_TOKENS
from overlord.ui.pages.dashboard.page import build_dashboard


TEST_TEMP_ROOT = Path(__file__).resolve().parents[1] / "data" / "test-tmp"
TEST_TEMP_ROOT.mkdir(parents=True, exist_ok=True)


class FakePage:
    def __init__(self):
        self.dialogs: list[ft.Control] = []

    def show_dialog(self, dialog):
        self.dialogs.append(dialog)

    def pop_dialog(self):
        return self.dialogs.pop() if self.dialogs else None


def _walk(control):
    yield control
    content = getattr(control, "content", None)
    if isinstance(content, ft.Control):
        yield from _walk(content)
    for child in getattr(control, "controls", ()) or ():
        yield from _walk(child)


def _role(control, role: str):
    return [
        item
        for item in _walk(control)
        if isinstance(getattr(item, "data", None), dict) and item.data.get("role") == role
    ]


class DashboardThreeDayBoardTests(unittest.TestCase):
    def setUp(self):
        self.path = TEST_TEMP_ROOT / f"dashboard-board-{uuid.uuid4().hex}.db"
        self.services = bootstrap(self.path).services
        self.page = FakePage()
        self.day = date.today()
        self.refresh_count = 0

    def tearDown(self):
        self.path.unlink(missing_ok=True)

    def build(self):
        return build_dashboard(
            self.services,
            LIGHT_TOKENS,
            f"/dashboard?date={self.day.isoformat()}",
            lambda *_: None,
            self.refresh,
            self.fail,
            self.page,
        )

    def refresh(self):
        self.refresh_count += 1

    def test_query_groups_three_actual_days_and_uses_predictable_initial_order(self):
        yesterday = self.services.tasks.create_task.execute(
            None, "Yesterday", schedule_start_date=self.day - timedelta(days=1)
        )
        tomorrow = self.services.tasks.create_task.execute(
            None, "Tomorrow", schedule_start_date=self.day + timedelta(days=1)
        )
        untimed = self.services.tasks.create_task.execute(None, "Untimed", schedule_start_date=self.day)
        late = self.services.tasks.create_task.execute(
            None, "Late", schedule_start_date=self.day, schedule_start_time=time(11, 30)
        )
        early = self.services.tasks.create_task.execute(
            None, "Early", schedule_start_date=self.day, schedule_start_time=time(9, 0)
        )
        completed = self.services.tasks.create_task.execute(None, "Completed", schedule_start_date=self.day)
        self.services.tasks.complete_task.execute(completed.id)

        data = self.services.dashboard.execute(self.day)
        self.assertEqual((yesterday.id,), tuple(item.task.id for item in data.yesterday_tasks))
        self.assertEqual((tomorrow.id,), tuple(item.task.id for item in data.tomorrow_tasks))
        self.assertEqual(
            (completed.id, early.id, late.id, untimed.id),
            tuple(item.task.id for item in data.today_tasks),
        )
        self.assertEqual(self.day, self.services.dashboard.execute().day)

    def test_shared_header_uses_dynamic_today_count_from_dashboard_read_model(self):
        self.services.tasks.create_task.execute(None, "Today one", schedule_start_date=self.day)
        self.services.tasks.create_task.execute(None, "Today two", schedule_start_date=self.day)
        self.services.tasks.create_task.execute(
            None,
            "Tomorrow only",
            schedule_start_date=self.day + timedelta(days=1),
        )
        control = self.build()
        header = _role(control, "page-header")
        titles = _role(control, "page-header-title")
        subtitles = _role(control, "page-header-subtitle")
        self.assertEqual(1, len(header))
        self.assertEqual("Good morning, Denys", titles[0].value)
        self.assertEqual("You have 2 tasks today", subtitles[0].value)
        self.assertEqual(1, len(_role(control, "user-menu-trigger")))

    def test_completion_moves_to_top_and_manual_order_survives_restart(self):
        first = self.services.tasks.create_task.execute(None, "First", schedule_start_date=self.day)
        second = self.services.tasks.create_task.execute(None, "Second", schedule_start_date=self.day)
        third = self.services.tasks.create_task.execute(None, "Third", schedule_start_date=self.day)

        self.services.tasks.toggle_completion_for_day.execute(second.id, self.day)
        completed_order = tuple(item.task.id for item in self.services.dashboard.execute(self.day).today_tasks)
        self.assertEqual(second.id, completed_order[0])
        self.assertEqual(TaskLifecycle.COMPLETED, self.services.tasks.get_editor.execute(second.id).task.lifecycle_status)

        manual_order = (third.id, first.id, second.id)
        self.services.tasks.reorder_for_day.execute(self.day, manual_order)
        reopened = bootstrap(self.path).services
        self.assertEqual(manual_order, tuple(item.task.id for item in reopened.dashboard.execute(self.day).today_tasks))

        reopened.tasks.toggle_completion_for_day.execute(second.id, self.day)
        self.assertEqual(manual_order, tuple(item.task.id for item in reopened.dashboard.execute(self.day).today_tasks))
        self.assertEqual(TaskLifecycle.PLANNED, reopened.tasks.get_editor.execute(second.id).task.lifecycle_status)

    def test_board_has_fixed_three_columns_and_independent_hidden_scroll_lists(self):
        control = self.build()
        board = _role(control, "three-day-task-board")[0]
        bento_row = _role(control, "first-bento-row")[0]
        weekly = _role(control, "weekly-progress-widget")[0]
        columns = _role(board, "day-column")
        lists = _role(board, "day-task-list")
        add_controls = _role(board, "add-task")
        self.assertEqual(455, board.height)
        self.assertIsNone(board.width)
        self.assertEqual(1080, board.data["max_width"])
        self.assertIsInstance(bento_row, ft.ResponsiveRow)
        self.assertIs(bento_row.alignment, ft.MainAxisAlignment.START)
        self.assertEqual(24, bento_row.spacing)
        self.assertEqual(24, bento_row.run_spacing)
        self.assertEqual({"sm": 12, "xxl": 9}, board.col)
        self.assertEqual({"sm": 12, "xxl": 3}, weekly.col)
        self.assertIsNone(getattr(bento_row, "on_size_change", None))
        self.assertEqual(3, len(columns))
        self.assertEqual(3, len(lists))
        self.assertTrue(all(isinstance(task_list, ft.ListView) for task_list in lists))
        self.assertFalse(any(isinstance(item, ft.ReorderableListView) for item in _walk(board)))
        self.assertTrue(all(task_list.scroll is ft.ScrollMode.HIDDEN for task_list in lists))
        self.assertTrue(all(task_list.build_controls_on_demand is False for task_list in lists))
        self.assertEqual([True, False, False], [item.data["disabled"] for item in add_controls])
        self.assertEqual(3, len(_role(board, "date-chip")))

        rebuilt = self.build()
        rebuilt_row = _role(rebuilt, "first-bento-row")[0]
        self.assertEqual(
            ["three-day-task-board", "weekly-progress-widget"],
            [item.data["role"] for item in rebuilt_row.controls],
        )

    def test_day_list_contains_outer_scroll_and_board_tooltips_are_hidden(self):
        control = self.build()
        root = _role(control, "dashboard-scroll-root")[0]
        regions = _role(control, "day-scroll-containment")
        self.assertEqual(3, len(regions))
        self.assertIs(root.scroll, ft.ScrollMode.AUTO)
        with patch.object(ft.Control, "update", lambda _control: None):
            regions[1].on_enter(None)
        self.assertIsNone(root.scroll)
        with patch.object(ft.Control, "update", lambda _control: None):
            regions[1].on_exit(None)
        self.assertIs(root.scroll, ft.ScrollMode.AUTO)

        board = _role(control, "three-day-task-board")[0]
        self.assertTrue(all(getattr(item, "tooltip", None) is None for item in _walk(board)))

    def test_add_task_hover_and_completion_chip_match_fixed_states(self):
        task = self.services.tasks.create_task.execute(None, "Finish this", schedule_start_date=self.day)
        control = self.build()
        add_controls = _role(control, "add-task")
        disabled_surface = add_controls[0].content
        active_surface = add_controls[1].content
        self.assertEqual("#ECECEC", disabled_surface.bgcolor)
        self.assertEqual("#E7E7E7", disabled_surface.border.top.color)
        self.assertEqual("#F1F1F1", active_surface.bgcolor)
        self.assertEqual("#E9E9E9", active_surface.border.top.color)
        self.assertEqual("#000000", LIGHT_TOKENS.dashboard_add_icon)
        self.assertEqual("#F1F1F1", DARK_TOKENS.dashboard_add_background)
        self.assertEqual("#E9E9E9", DARK_TOKENS.dashboard_add_border)
        self.assertEqual("#9A9A9A", DARK_TOKENS.dashboard_add_text)
        self.assertEqual("#000000", DARK_TOKENS.dashboard_add_icon)
        self.assertEqual("#ECECEC", DARK_TOKENS.dashboard_add_disabled_background)
        self.assertEqual("#E7E7E7", DARK_TOKENS.dashboard_add_disabled_border)
        self.assertEqual("#DDDDDD", DARK_TOKENS.dashboard_add_disabled_text)
        with patch.object(ft.Control, "update", lambda _control: None):
            active_surface.on_hover(SimpleNamespace(data="true"))
        self.assertEqual("#D61F45", active_surface.border.top.color)
        with patch.object(ft.Control, "update", lambda _control: None):
            active_surface.on_hover(SimpleNamespace(data="false"))
        self.assertEqual("#E9E9E9", active_surface.border.top.color)

        completion = next(item for item in _role(control, "completion") if item.data["task_id"] == task.id)
        chip = completion.content
        self.assertEqual((22, 22), (chip.width, chip.height))
        self.assertIsNone(chip.bgcolor)
        self.assertEqual("#DDDDDD", chip.border.top.color)
        self.services.tasks.toggle_completion_for_day.execute(task.id, self.day)
        completed_control = self.build()
        completed = next(item for item in _role(completed_control, "completion") if item.data["task_id"] == task.id)
        completed_chip = completed.content
        self.assertEqual((22, 22), (completed_chip.width, completed_chip.height))
        self.assertEqual("#12C933", completed_chip.bgcolor)
        self.assertEqual("#47A958", completed_chip.border.top.color)

    def test_today_and_tomorrow_creation_inherit_the_column_date(self):
        control = self.build()
        add_controls = _role(control, "add-task")
        today_add, tomorrow_add = add_controls[1], add_controls[2]
        with patch.object(ft.Control, "update", lambda _control: None):
            today_add.on_tap(None)
        today_dialog = self.page.dialogs.pop()
        self.assertEqual("today", today_dialog.content.content.controls[3].value)

        with patch.object(ft.Control, "update", lambda _control: None):
            tomorrow_add.on_tap(None)
        tomorrow_dialog = self.page.dialogs.pop()
        self.assertEqual("tomorrow", tomorrow_dialog.content.content.controls[3].value)

    def test_cards_support_description_variants_and_separate_click_targets(self):
        plain = self.services.tasks.create_task.execute(None, "Plain", schedule_start_date=self.day)
        described = self.services.tasks.create_task.execute(
            None,
            "Described",
            description="A compact preview that belongs under the title.",
            schedule_start_date=self.day,
        )
        control = self.build()
        cards = _role(control, "task-card")
        self.assertEqual({plain.id, described.id}, {card.data["task_id"] for card in cards})
        bodies = _role(control, "task-body")
        completions = _role(control, "completion")
        handles = [item for item in _walk(control) if isinstance(item, ft.Draggable)]
        self.assertEqual(2, len(bodies))
        self.assertEqual(2, len(completions))
        self.assertEqual(2, len(handles))
        self.assertTrue(all(handle.data["role"] == "task-drag-handle" for handle in handles))
        described_body = next(item for item in bodies if item.data["task_id"] == described.id)
        described_text = [item for item in _walk(described_body) if isinstance(item, ft.Text)]
        copy = [item.value for item in described_text]
        self.assertIn("A compact preview that belongs under the title.", copy)
        self.assertEqual(1, described_text[0].max_lines)
        self.assertEqual(2, described_text[1].max_lines)
        plain_body = next(item for item in bodies if item.data["task_id"] == plain.id)
        self.assertEqual(["Plain"], [item.value for item in _walk(plain_body) if isinstance(item, ft.Text)])
        described_card = next(item for item in cards if item.data["task_id"] == described.id)
        self.assertIs(described_card.content.vertical_alignment, ft.CrossAxisAlignment.START)

    def test_drag_handle_reorders_inside_the_day_and_persists(self):
        first = self.services.tasks.create_task.execute(None, "First", schedule_start_date=self.day)
        second = self.services.tasks.create_task.execute(None, "Second", schedule_start_date=self.day)
        control = self.build()
        task_list = next(
            item
            for item in _role(control, "day-task-list")
            if item.data["day"] == self.day.isoformat()
        )
        target = next(
            item
            for item in _walk(task_list)
            if isinstance(item, ft.DragTarget)
            and item.data.get("before_task_id") == first.id
        )
        event = SimpleNamespace(
            src=SimpleNamespace(
                data={"kind": "task", "task_id": second.id, "day": self.day.isoformat()}
            )
        )
        with patch.object(ft.Control, "update", lambda _control: None):
            target.on_accept(event)
        self.assertEqual(
            (second.id, first.id),
            tuple(item.task.id for item in self.services.dashboard.execute(self.day).today_tasks),
        )
        rebuilt = self.build()
        rebuilt_list = next(
            item
            for item in _role(rebuilt, "day-task-list")
            if item.data["day"] == self.day.isoformat()
        )
        end_target = next(
            item
            for item in _role(rebuilt, "day-task-drop-target")
            if item.data["day"] == self.day.isoformat()
        )
        event = SimpleNamespace(
            src=SimpleNamespace(
                data={"kind": "task", "task_id": second.id, "day": self.day.isoformat()}
            )
        )
        with patch.object(ft.Control, "update", lambda _control: None):
            end_target.on_accept(event)
        self.assertEqual(
            (first.id, second.id),
            tuple(item.task.id for item in self.services.dashboard.execute(self.day).today_tasks),
        )

    def test_dashboard_drag_rejects_cross_day_moves(self):
        today = self.services.tasks.create_task.execute(None, "Today", schedule_start_date=self.day)
        tomorrow = self.services.tasks.create_task.execute(
            None,
            "Tomorrow",
            schedule_start_date=self.day + timedelta(days=1),
        )
        control = self.build()
        tomorrow_target = next(
            item
            for item in _role(control, "day-task-drop-target")
            if item.data["day"] == (self.day + timedelta(days=1)).isoformat()
        )
        tomorrow_target.on_accept(
            SimpleNamespace(
                src=SimpleNamespace(
                    data={"kind": "task", "task_id": today.id, "day": self.day.isoformat()}
                )
            )
        )

        self.assertEqual(self.day, self.services.tasks.get_editor.execute(today.id).task.schedule_start_date)
        self.assertEqual(
            (tomorrow.id,),
            tuple(
                item.task.id
                for item in self.services.dashboard.execute(self.day).tomorrow_tasks
            ),
        )
        self.assertEqual(0, self.refresh_count)

    def test_reorderable_items_own_an_exact_eight_pixel_sibling_gap(self):
        self.services.tasks.create_task.execute(None, "First", schedule_start_date=self.day)
        self.services.tasks.create_task.execute(None, "Second", schedule_start_date=self.day)
        control = self.build()
        task_list = next(
            item
            for item in _role(control, "day-task-list")
            if item.data["day"] == self.day.isoformat()
        )
        items = _role(task_list, "task-list-item")
        self.assertEqual(0, task_list.spacing)
        self.assertEqual(2, len(items))
        self.assertTrue(all(item.padding.bottom == 8 for item in items))
        self.assertTrue(all(item.data["gap_after"] == 8 for item in items))
        self.assertEqual(len(items), len({item.key for item in items}))
        self.assertTrue(all(item.key for item in items))

    def test_task_body_opens_editable_details_and_save_refreshes_the_route(self):
        task = self.services.tasks.create_task.execute(None, "Open me", schedule_start_date=self.day)
        control = self.build()
        body = next(item for item in _role(control, "task-body") if item.data["task_id"] == task.id)
        with patch.object(ft.Control, "update", lambda _control: None):
            body.on_tap(None)
        dialog = self.page.dialogs[-1]
        self.assertEqual("Task Details", dialog.title.controls[0].value)
        fields = [item for item in _walk(dialog) if isinstance(item, ft.TextField)]
        title = next(item for item in fields if item.label == "Title")
        title.value = "Updated in details"
        with patch.object(ft.Control, "update", lambda _control: None):
            dialog.actions[-1].on_click(None)
        self.assertEqual([], self.page.dialogs)
        self.assertEqual("Updated in details", self.services.tasks.get_editor.execute(task.id).task.title)
        self.assertEqual(1, self.refresh_count)

    def test_successful_create_and_completion_refresh_the_page_owner_without_child_updates(self):
        control = self.build()
        today_add = _role(control, "add-task")[1]
        today_add.on_tap(None)
        dialog = self.page.dialogs[-1]
        title = next(item for item in _walk(dialog) if isinstance(item, ft.TextField) and item.label == "Title")
        title.value = "Created safely"

        with patch.object(ft.Control, "update", side_effect=RuntimeError("frozen child update")):
            dialog.actions[-1].on_click(None)

        created = next(item for item in self.services.tasks.list_tasks.execute() if item.task.title == "Created safely")
        rebuilt = self.build()
        completion = next(item for item in _role(rebuilt, "completion") if item.data["task_id"] == created.task.id)
        with patch.object(ft.Control, "update", side_effect=RuntimeError("frozen child update")):
            completion.on_tap(None)

        self.assertEqual(TaskLifecycle.COMPLETED, self.services.tasks.get_editor.execute(created.task.id).task.lifecycle_status)
        self.assertEqual(2, self.refresh_count)


if __name__ == "__main__":
    unittest.main()
