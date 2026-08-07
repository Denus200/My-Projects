import hashlib
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch

import flet as ft

from overlord.bootstrap import DEFAULT_DATABASE_PATH, bootstrap
from overlord.presentation.design_system.tokens import LIGHT_TOKENS
from overlord.presentation.pages.tasks import build_quick_task_dialog, build_tasks
from overlord.presentation.state import AppSessionState, TaskFilterState
from overlord.presentation.strings import ui_text


TEST_TEMP_ROOT = Path(__file__).resolve().parents[1] / "data" / "test-tmp"
TEST_TEMP_ROOT.mkdir(parents=True, exist_ok=True)


def _hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(128 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


class FakePage:
    def __init__(self):
        self.dialogs = []

    def show_dialog(self, dialog):
        self.dialogs.append(dialog)

    def pop_dialog(self):
        return self.dialogs.pop() if self.dialogs else None


class U2TaskPresentationTests(unittest.TestCase):
    def setUp(self):
        self.path = TEST_TEMP_ROOT / f"u2-tasks-{uuid.uuid4().hex}.db"
        self.services = bootstrap(self.path).services
        self.project = self.services.projects.create_project.execute("U2 Project")

    def tearDown(self):
        self.path.unlink(missing_ok=True)

    def test_quick_task_progressive_fields_start_hidden_and_have_no_dashboard_assignment(self):
        dialog = build_quick_task_dialog(
            self.services,
            (self.project,),
            LIGHT_TOKENS,
            lambda _task: None,
            lambda: None,
        )
        controls = dialog.content.content.controls
        details = controls[4]
        self.assertFalse(details.visible)
        visible_copy = " ".join(
            str(value)
            for control in controls
            for value in (getattr(control, "label", ""), getattr(control, "value", ""))
            if value
        )
        self.assertNotIn("Primary", visible_copy)
        self.assertNotIn("Secondary", visible_copy)
        self.assertNotIn("Dashboard", visible_copy)
        with patch.object(ft.Control, "update", lambda _control: None):
            controls[3].on_click(None)
        self.assertTrue(details.visible)

    def test_empty_title_validation_stays_near_title_and_preserves_input(self):
        dialog = build_quick_task_dialog(
            self.services,
            (),
            LIGHT_TOKENS,
            lambda _task: None,
            lambda: None,
        )
        title = dialog.content.content.controls[1]
        title.value = "   "
        with patch.object(ft.Control, "update", lambda _control: None):
            dialog.actions[-1].on_click(None)
        self.assertEqual("   ", title.value)
        self.assertEqual("Task title is required.", title.error)
        self.assertEqual((), self.services.tasks.list_tasks.execute())

    def test_quick_task_creation_preserves_filters_and_does_not_call_route_refresh(self):
        state = AppSessionState(
            route="/tasks",
            task_filters=TaskFilterState(search="Captured", project="none", urgency="yes"),
        )
        page = FakePage()
        refresh_calls = []
        control = build_tasks(
            self.services,
            LIGHT_TOKENS,
            state,
            lambda: refresh_calls.append(True),
            self.fail,
            page,
        )
        quick_button = control.controls[0].controls[-1]
        with patch.object(ft.Control, "update", lambda _control: None):
            quick_button.on_click(None)
            dialog = page.dialogs[-1]
            form_controls = dialog.content.content.controls
            form_controls[1].value = "Captured standalone Task"
            details = form_controls[4]
            urgency = details.content.controls[1].controls[1]
            urgency.value = True
            dialog.actions[-1].on_click(None)
        self.assertEqual([], refresh_calls)
        self.assertEqual("Captured", state.task_filters.search)
        self.assertEqual("none", state.task_filters.project)
        self.assertEqual("yes", state.task_filters.urgency)
        matches = self.services.tasks.list_tasks.execute(without_project=True, urgency=True)
        self.assertEqual(("Captured standalone Task",), tuple(item.task.title for item in matches))

    def test_tasks_page_project_filter_contains_no_project(self):
        control = build_tasks(
            self.services,
            LIGHT_TOKENS,
            AppSessionState(route="/tasks"),
            lambda: None,
            self.fail,
        )
        result_card = control.controls[1]
        filter_row = result_card.content.controls[1]
        project_dropdown = filter_row.controls[1].content
        labels = [option.text for option in project_dropdown.options]
        self.assertIn(ui_text("tasks.no_project"), labels)

    def test_filter_actions_use_valid_responsive_layout_without_expand_in_wrap(self):
        control = build_tasks(
            self.services,
            LIGHT_TOKENS,
            AppSessionState(route="/tasks"),
            lambda: None,
            self.fail,
        )
        result_card = control.controls[1]
        action_row = result_card.content.controls[2]
        self.assertIsInstance(action_row, ft.ResponsiveRow)
        button_row = action_row.controls[1].content
        self.assertIsInstance(button_row, ft.Row)
        self.assertFalse(button_row.wrap)
        self.assertFalse(any(getattr(child, "expand", False) for child in button_row.controls))

    def test_disposable_u2_work_does_not_touch_production_database(self):
        before = _hash(DEFAULT_DATABASE_PATH)
        self.services.tasks.create_task.execute(None, "Disposable standalone Task")
        after = _hash(DEFAULT_DATABASE_PATH)
        self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()
