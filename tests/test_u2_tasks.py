import hashlib
import unittest
import uuid
from datetime import date, time
from pathlib import Path
from unittest.mock import patch

import flet as ft

from overlord.bootstrap import DEFAULT_DATABASE_PATH, bootstrap
from overlord.ui.design_system.tokens import LIGHT_TOKENS
from overlord.ui.components.task_details import build_task_details_dialog
from overlord.ui.components.tasks import build_quick_task_dialog
from overlord.ui.pages.tasks.page import build_task_editor_content, build_tasks
from overlord.ui.state import AppSessionState, TaskFilterState
from overlord.ui.strings import ui_text


TEST_TEMP_ROOT = Path(__file__).resolve().parents[1] / "data" / "test-tmp"
TEST_TEMP_ROOT.mkdir(parents=True, exist_ok=True)


def _hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(128 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


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


def _field(control, label: str):
    return next(item for item in _walk(control) if getattr(item, "label", None) == label)


def _button(control, label: str):
    return next(
        item
        for item in _walk(control)
        if getattr(item, "content", None) == label and callable(getattr(item, "on_click", None))
    )


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

    def test_task_form_is_compact_by_default_and_hides_model_details(self):
        dialog = build_quick_task_dialog(
            self.services,
            (self.project,),
            LIGHT_TOKENS,
            lambda _task: None,
            lambda: None,
        )
        controls = dialog.content.content.controls
        self.assertEqual("Create Task", dialog.title)
        self.assertTrue(controls[0].autofocus)
        self.assertEqual("Title", controls[0].label)
        self.assertEqual("Description", controls[1].label)
        self.assertEqual("none", controls[2].value)
        self.assertEqual("today", controls[3].value)
        self.assertFalse(controls[4].visible)
        self.assertFalse(controls[6].visible)
        self.assertTrue(dialog.actions[-1].disabled)
        visible_copy = " ".join(
            str(value)
            for control in controls
            for value in (getattr(control, "label", ""), getattr(control, "value", ""))
            if value
        )
        self.assertNotIn("Primary", visible_copy)
        self.assertNotIn("Secondary", visible_copy)
        self.assertNotIn("Dashboard", visible_copy)
        self.assertNotIn("More details", visible_copy)
        self.assertNotIn("Definition of Done", visible_copy)
        self.assertNotIn("Next Action", visible_copy)
        self.assertNotIn("Connections", visible_copy)
        self.assertNotIn("Blocker", visible_copy)

    def test_empty_title_validation_stays_near_title_and_preserves_input(self):
        dialog = build_quick_task_dialog(
            self.services,
            (),
            LIGHT_TOKENS,
            lambda _task: None,
            lambda: None,
        )
        title = dialog.content.content.controls[0]
        title.value = "   "
        with patch.object(ft.Control, "update", lambda _control: None):
            dialog.actions[-1].on_click(None)
        self.assertEqual("   ", title.value)
        self.assertEqual("Task title is required.", title.error)
        self.assertEqual((), self.services.tasks.list_tasks.execute())

    def test_quick_task_creation_preserves_filters_and_refreshes_from_the_page_owner(self):
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
        quick_button = _role(control, "page-header-actions")[0].controls[0]
        with patch.object(ft.Control, "update", lambda _control: None):
            quick_button.on_click(None)
            dialog = page.dialogs[-1]
            form_controls = dialog.content.content.controls
            form_controls[0].value = "Captured standalone Task"
            advanced = form_controls[6].content
            urgency = advanced.controls[4].controls[1].controls[1]
            urgency.selected = True
            dialog.actions[-1].on_click(None)
        self.assertEqual([True], refresh_calls)
        self.assertEqual("Captured", state.task_filters.search)
        self.assertEqual("none", state.task_filters.project)
        self.assertEqual("yes", state.task_filters.urgency)
        matches = self.services.tasks.list_tasks.execute(without_project=True, urgency=True)
        self.assertEqual(("Captured standalone Task",), tuple(item.task.title for item in matches))

    def test_basic_creation_defaults_to_today(self):
        created = []
        dialog = build_quick_task_dialog(
            self.services,
            (self.project,),
            LIGHT_TOKENS,
            created.append,
            lambda: None,
        )
        controls = dialog.content.content.controls
        controls[0].value = "Default-today Task"
        controls[1].value = "Enough context to act on it."
        with patch.object(ft.Control, "update", lambda _control: None):
            controls[0].on_change(None)
            self.assertFalse(dialog.actions[-1].disabled)
            dialog.actions[-1].on_click(None)
        self.assertEqual(1, len(created))
        self.assertEqual(date.today(), created[0].schedule_start_date)
        self.assertEqual("Enough context to act on it.", created[0].description)

    def test_project_context_is_inherited(self):
        dialog = build_quick_task_dialog(
            self.services,
            (self.project,),
            LIGHT_TOKENS,
            lambda _task: None,
            lambda: None,
            selected_project_id=self.project.id,
        )
        self.assertEqual(str(self.project.id), dialog.content.content.controls[2].value)

    def test_advanced_options_persist_time_deadline_estimate_and_priority(self):
        created = []
        dialog = build_quick_task_dialog(
            self.services,
            (self.project,),
            LIGHT_TOKENS,
            created.append,
            lambda: None,
        )
        controls = dialog.content.content.controls
        advanced = controls[6].content
        schedule_modes = advanced.controls[0].controls
        time_mode = schedule_modes[0].content
        deadline_mode = schedule_modes[1].content
        estimate_mode = schedule_modes[2].content
        start_time = advanced.controls[1].controls[0]
        deadline_date = advanced.controls[2].controls[0]
        importance, urgency = advanced.controls[4].controls[1].controls

        controls[0].value = "Configured Task"
        controls[2].value = str(self.project.id)
        time_mode.value = "custom"
        start_time.value = "14:30"
        deadline_mode.value = "custom"
        deadline_date.value = "16082026"
        estimate_mode.value = "30"
        importance.selected = True
        urgency.selected = True
        importance.on_select(None)
        urgency.on_select(None)
        with patch.object(ft.Control, "update", lambda _control: None):
            controls[5].on_click(None)
            dialog.actions[-1].on_click(None)

        self.assertTrue(controls[6].visible)
        self.assertEqual(1, len(created))
        task = created[0]
        self.assertEqual(self.project.id, task.project_id)
        self.assertEqual(time(14, 30), task.schedule_start_time)
        self.assertEqual(date(2026, 8, 16), task.deadline_at.date())
        self.assertEqual(30, task.estimate_minutes)
        self.assertTrue(task.importance)
        self.assertTrue(task.urgency)

    def test_manual_custom_date_is_forgiving_and_normalizes_on_blur(self):
        created = []
        dialog = build_quick_task_dialog(
            self.services,
            (),
            LIGHT_TOKENS,
            created.append,
            lambda: None,
        )
        controls = dialog.content.content.controls
        custom_date = controls[4].controls[0]
        controls[0].value = "Human date Task"
        controls[3].value = "choose_date"
        custom_date.value = "13082026"
        with patch.object(ft.Control, "update", lambda _control: None):
            controls[3].on_select(None)
            custom_date.on_blur(None)
            dialog.actions[-1].on_click(None)
        self.assertEqual("13.08.2026", custom_date.value)
        self.assertEqual(date(2026, 8, 13), created[0].schedule_start_date)

    def test_quick_form_validation_error_targets_are_characterized(self):
        cases = (
            ("date", "Date must use DD.MM.YYYY."),
            ("time", "Time must use HH:MM."),
            ("deadline", "Date must use DD.MM.YYYY."),
            ("estimate", "Estimate must be a whole number of minutes."),
        )
        for target, expected in cases:
            with self.subTest(target=target), patch.object(ft.Control, "update", lambda _control: None):
                dialog = build_quick_task_dialog(
                    self.services,
                    (self.project,),
                    LIGHT_TOKENS,
                    lambda _task: self.fail("Invalid form must not create a Task."),
                    lambda: None,
                )
                controls = dialog.content.content.controls
                advanced = controls[6].content
                time_mode = advanced.controls[0].controls[0].content
                deadline_mode = advanced.controls[0].controls[1].content
                estimate_mode = advanced.controls[0].controls[2].content
                custom_date = controls[4].controls[0]
                start_time = advanced.controls[1].controls[0]
                deadline_date = advanced.controls[2].controls[0]
                custom_estimate = advanced.controls[3]
                controls[0].value = f"Invalid {target} Task"

                if target == "date":
                    controls[3].value = "choose_date"
                    custom_date.value = "not-a-date"
                    expected_field = custom_date
                elif target == "time":
                    time_mode.value = "custom"
                    start_time.value = "not-a-time"
                    expected_field = start_time
                elif target == "deadline":
                    deadline_mode.value = "custom"
                    deadline_date.value = "not-a-date"
                    expected_field = deadline_date
                else:
                    estimate_mode.value = "custom"
                    custom_estimate.value = "not-a-number"
                    expected_field = custom_estimate

                dialog.actions[-1].on_click(None)
                self.assertEqual(expected, expected_field.error)

    def test_main_editor_keeps_strict_date_errors_in_the_form_message(self):
        task = self.services.tasks.create_task.execute(None, "Strict editor Task", schedule_start_date=date.today())
        saved = []
        editor = build_task_editor_content(
            self.services,
            (self.project,),
            task.id,
            LIGHT_TOKENS,
            lambda: saved.append(True),
            lambda: None,
            lambda: None,
            self.fail,
        )
        start_date = _field(editor, ui_text("tasks.field_start_date"))
        start_date.value = "13.08.2026"
        message = editor.controls[10]

        with patch.object(ft.Control, "update", lambda _control: None):
            _button(editor, ui_text("tasks.save")).on_click(None)

        self.assertEqual([], saved)
        self.assertIsNone(start_date.error)
        self.assertEqual("Date must use YYYY-MM-DD.", message.value)

    def test_dashboard_details_keeps_flexible_date_error_on_deadline_field(self):
        task = self.services.tasks.create_task.execute(None, "Dashboard details Task", schedule_start_date=date.today())
        reported = []
        dialog = build_task_details_dialog(
            self.services,
            (self.project,),
            task.id,
            date.today(),
            LIGHT_TOKENS,
            lambda: self.fail("Invalid form must not save."),
            lambda: None,
            reported.append,
        )
        scheduled_date = _field(dialog, ui_text("tasks.field_start_date"))
        deadline = _field(dialog, ui_text("tasks.field_deadline"))
        scheduled_date.value = "not-a-date"

        with patch.object(ft.Control, "update", lambda _control: None):
            dialog.actions[-1].on_click(None)

        self.assertIsNone(scheduled_date.error)
        self.assertEqual("Date must use DD.MM.YYYY.", deadline.error)
        self.assertEqual([], reported)

    def test_tasks_page_project_filter_contains_no_project(self):
        control = build_tasks(
            self.services,
            LIGHT_TOKENS,
            AppSessionState(route="/tasks"),
            lambda: None,
            self.fail,
        )
        filter_row = _role(control, "page-content")[0].controls[0]
        project_dropdown = filter_row.controls[1].content
        labels = [option.text for option in project_dropdown.options]
        self.assertIn(ui_text("tasks.no_project"), labels)

    def test_tasks_workspace_exposes_three_view_modes(self):
        control = build_tasks(
            self.services,
            LIGHT_TOKENS,
            AppSessionState(route="/tasks"),
            lambda: None,
            self.fail,
        )
        mode_row = _role(control, "task-view-modes")[0]
        self.assertEqual(3, len(mode_row.controls))
        self.assertEqual(["Kanban", "Week", "Month"], [button.content for button in mode_row.controls])

    def test_disposable_u2_work_does_not_touch_production_database(self):
        before = _hash(DEFAULT_DATABASE_PATH)
        self.services.tasks.create_task.execute(None, "Disposable standalone Task")
        after = _hash(DEFAULT_DATABASE_PATH)
        self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()
