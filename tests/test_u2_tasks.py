import hashlib
import unittest
import uuid
from datetime import date, datetime, timedelta
from pathlib import Path
from unittest.mock import patch

import flet as ft

from overlord.bootstrap import DEFAULT_DATABASE_PATH, bootstrap
from overlord.modules.projects.domain import ProjectStageStatus
from overlord.modules.tasks.domain import TaskCreationMode
from overlord.ui.components.task_details import build_task_details_dialog
from overlord.ui.components.task_form_values import duration_minutes_value
from overlord.ui.components.tasks import build_quick_task_dialog
from overlord.ui.design_system.tokens import LIGHT_TOKENS
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
    if not isinstance(control, ft.Control):
        return
    yield control
    for name in ("title", "content"):
        child = getattr(control, name, None)
        if isinstance(child, ft.Control):
            yield from _walk(child)
    for name in ("controls", "actions", "items"):
        for child in getattr(control, name, ()) or ():
            yield from _walk(child)


def _role(control, role: str):
    return [
        item
        for item in _walk(control)
        if isinstance(getattr(item, "data", None), dict)
        and item.data.get("role") == role
    ]


def _field(control, label: str):
    return next(item for item in _walk(control) if getattr(item, "label", None) == label)


def _button(control, label: str):
    return next(
        item
        for item in _walk(control)
        if getattr(item, "content", None) == label
        and callable(getattr(item, "on_click", None))
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
        self.project = self.services.projects.create_project.execute("Titan", color="#FFC7D2")
        self.project_without_stages = self.services.projects.create_project.execute("Inbox")
        plan = self.services.projects.create_plan.execute(self.project.id, "Current")
        self.stage = self.services.projects.create_stage.execute(self.project.id, plan.id, "UI Design")
        self.services.projects.change_stage_status.execute(self.stage.id, ProjectStageStatus.IN_PROGRESS)

    def tearDown(self):
        self.path.unlink(missing_ok=True)

    def dialog(self, **kwargs):
        return build_quick_task_dialog(
            self.services,
            self.services.projects.list_projects.execute(),
            LIGHT_TOKENS,
            kwargs.pop("on_created", lambda _task: None),
            kwargs.pop("close", lambda: None),
            **kwargs,
        )

    def expand(self, dialog):
        _role(dialog, "advanced-toggle")[0].on_click(None)
        return dialog.data["state"]

    def select_project(self, dialog, project_id):
        option = next(item for item in _role(dialog, "project-option") if item.data["project_id"] == project_id)
        option.on_click(None)

    def save(self, dialog):
        _role(dialog, "create-task-save")[0].on_click(None)

    def test_create_task_matches_base_progressive_disclosure(self):
        dialog = self.dialog()
        self.assertEqual("create-task-dialog", dialog.data["role"])
        self.assertEqual(TaskCreationMode.NORMAL, dialog.data["state"].creation_mode)
        self.assertTrue(_role(dialog, "create-task-title")[0].autofocus)
        self.assertFalse(_role(dialog, "create-task-advanced")[0].visible)
        self.assertFalse(_role(dialog, "create-task-save")[0].disabled)
        self.assertEqual(1, len(_role(dialog, "creation-mode-selector")))
        self.assertEqual(1, len(_role(dialog, "create-task-close")))

    def test_minimal_task_and_description_persist_without_date(self):
        created = []
        dialog = self.dialog(on_created=created.append)
        title = _role(dialog, "create-task-title")[0]
        title.value = "Captured Task"
        _role(dialog, "create-task-description")[0].value = "Enough context to act."
        with patch.object(ft.Control, "update", lambda _control: None):
            self.save(dialog)
        self.assertEqual(1, len(created))
        self.assertIsNone(created[0].schedule_start_date)
        self.assertEqual("Enough context to act.", created[0].description)

    def test_empty_title_validation_stays_near_title(self):
        dialog = self.dialog()
        title = _role(dialog, "create-task-title")[0]
        title.value = "   "
        with patch.object(ft.Control, "update", lambda _control: None):
            self.save(dialog)
        self.assertEqual("   ", title.value)
        self.assertEqual("Task title is required.", title.error)
        self.assertEqual((), self.services.tasks.list_tasks.execute())

    def test_date_overlay_cancel_and_apply_preserve_form_state(self):
        page = FakePage()
        dialog = self.dialog(page=page)
        title = _role(dialog, "create-task-title")[0]
        title.value = "Keep this title"
        with patch.object(ft.Control, "update", lambda _control: None):
            _role(dialog, "create-task-date")[0].on_click(None)
            self.assertEqual("date-picker", page.dialogs[-1].data["role"])
            _button(page.dialogs[-1], ui_text("tasks.cancel")).on_click(None)
            self.assertEqual("Keep this title", title.value)
            self.assertIsNone(dialog.data["state"].scheduled_date)

            _role(dialog, "create-task-date")[0].on_click(None)
            overlay = page.dialogs[-1]
            target = date.today() + timedelta(days=3)
            day = next(item for item in _role(overlay, "date-picker-day") if item.data["date"] == target.isoformat())
            day.on_click(None)
            _button(overlay, ui_text("tasks.create_save")).on_click(None)
        self.assertEqual(target, dialog.data["state"].scheduled_date)
        self.assertEqual("Keep this title", title.value)

    def test_project_selection_stage_dependency_and_removal_are_independent(self):
        second_plan = self.services.projects.create_plan.execute(self.project_without_stages.id, "Execution")
        second_stage = self.services.projects.create_stage.execute(
            self.project_without_stages.id, second_plan.id, "Delivery"
        )
        dialog = self.dialog()
        with patch.object(ft.Control, "update", lambda _control: None):
            self.expand(dialog)
            self.select_project(dialog, self.project.id)
            self.select_project(dialog, self.project_without_stages.id)
            stage_controls = _role(dialog, "project-stage")
            self.assertEqual({self.project.id, self.project_without_stages.id}, {c.data["project_id"] for c in stage_controls})
            titan_stage = next(c for c in stage_controls if c.data["project_id"] == self.project.id)
            other_stage = next(c for c in stage_controls if c.data["project_id"] == self.project_without_stages.id)
            titan_stage.value = str(self.stage.id)
            other_stage.value = str(second_stage.id)
            titan_stage.on_select(None)
            other_stage.on_select(None)
            self.select_project(dialog, self.project.id)
        state = dialog.data["state"]
        self.assertEqual([self.project_without_stages.id], state.selected_project_ids)
        self.assertNotIn(self.project.id, state.selected_stage_ids)
        self.assertEqual(second_stage.id, state.selected_stage_ids[self.project_without_stages.id])

    def test_project_without_stages_has_no_empty_stage_control(self):
        dialog = self.dialog()
        with patch.object(ft.Control, "update", lambda _control: None):
            self.expand(dialog)
            self.select_project(dialog, self.project_without_stages.id)
        self.assertEqual([], _role(dialog, "project-stage"))

    def test_four_projects_persist_and_fifth_is_prevented(self):
        extra = [self.services.projects.create_project.execute(f"Extra {number}") for number in range(3)]
        dialog = self.dialog()
        with patch.object(ft.Control, "update", lambda _control: None):
            self.expand(dialog)
            for project in (self.project, self.project_without_stages, extra[0], extra[1]):
                self.select_project(dialog, project.id)
            state = dialog.data["state"]
            self.assertEqual(4, len(state.selected_project_ids))
            # The fifth option is disabled and the state stays capped at four.
            fifth = next(item for item in _role(dialog, "project-option") if item.data["project_id"] == extra[2].id)
            self.assertTrue(fifth.disabled)
            fifth.on_click(None)
            self.assertEqual(4, len(state.selected_project_ids))

    def test_deadline_and_estimated_time_are_separate_and_persist(self):
        page = FakePage()
        created = []
        scheduled = date.today() + timedelta(days=5)
        dialog = self.dialog(page=page, preset_start_date=scheduled, on_created=created.append)
        with patch.object(ft.Control, "update", lambda _control: None):
            self.expand(dialog)
            _role(dialog, "deadline-trigger")[0].on_click(None)
            overlay = page.dialogs[-1]
            self.assertEqual("date-time-picker", overlay.data["role"])
            _role(overlay, "date-picker-time")[0].value = "18:10"
            _button(overlay, ui_text("tasks.create_save")).on_click(None)
            _role(dialog, "estimate-hours")[0].value = "1"
            _role(dialog, "estimate-minutes")[0].value = "30"
            _role(dialog, "create-task-title")[0].value = "Timed Task"
            self.save(dialog)
        self.assertEqual(90, created[0].estimate_minutes)
        self.assertEqual(datetime.combine(scheduled, datetime.min.time()).replace(hour=18, minute=10), created[0].deadline_at)

    def test_estimated_time_missing_hours_minutes_and_invalid_minute(self):
        cases = (("", "", None), ("2", "", 120), ("", "45", 45), ("4", "4", 244))
        for number, (hours, minutes, expected) in enumerate(cases):
            with self.subTest(hours=hours, minutes=minutes), patch.object(ft.Control, "update", lambda _control: None):
                created = []
                dialog = self.dialog(on_created=created.append)
                self.expand(dialog)
                _role(dialog, "create-task-title")[0].value = f"Estimate {number}"
                _role(dialog, "estimate-hours")[0].value = hours
                _role(dialog, "estimate-minutes")[0].value = minutes
                self.save(dialog)
                self.assertEqual(expected, created[0].estimate_minutes)

        dialog = self.dialog()
        with patch.object(ft.Control, "update", lambda _control: None):
            self.expand(dialog)
            _role(dialog, "create-task-title")[0].value = "Invalid minutes"
            _role(dialog, "estimate-minutes")[0].value = "60"
            self.save(dialog)
        self.assertEqual("Minutes must be between 0 and 59.", _role(dialog, "estimate-minutes")[0].error)

    def test_shared_duration_control_supports_realistic_values_without_collapsing_units(self):
        cases = (
            ("0", "1", 1),
            ("0", "10", 10),
            ("1", "30", 90),
            ("24", "59", 1499),
            ("150", "0", 9000),
        )
        for hours, minutes, expected in cases:
            with self.subTest(hours=hours, minutes=minutes):
                self.assertEqual(expected, duration_minutes_value(hours, minutes))

        create_dialog = self.dialog()
        with patch.object(ft.Control, "update", lambda _control: None):
            self.expand(create_dialog)
        task = self.services.tasks.create_task.execute(None, "Large estimate", estimate_minutes=9000)
        details_dialog = build_task_details_dialog(
            self.services,
            (self.project,),
            task.id,
            date.today(),
            LIGHT_TOKENS,
            lambda: None,
            lambda: None,
            self.fail,
        )

        for dialog in (create_dialog, details_dialog):
            duration = _role(dialog, "estimated-time")[0]
            hours = _role(dialog, "estimate-hours")[0]
            minutes = _role(dialog, "estimate-minutes")[0]
            units = duration.content.controls[1::2]
            self.assertEqual(186, duration.width)
            self.assertEqual((64, 52), (hours.width, minutes.width))
            self.assertEqual((16, 32), tuple(unit.width for unit in units))
            self.assertTrue(all(unit.content.no_wrap for unit in units))
            self.assertEqual(ft.TextAlign.RIGHT, hours.text_align)
            self.assertEqual(ft.TextAlign.RIGHT, minutes.text_align)

        self.assertEqual("150", _role(details_dialog, "estimate-hours")[0].value)
        self.assertEqual("0", _role(details_dialog, "estimate-minutes")[0].value)

    def test_draft_creation_is_explicit_and_not_a_lifecycle_status(self):
        created = []
        dialog = self.dialog(on_created=created.append)
        draft_option = next(item for item in _role(dialog, "creation-mode-option") if item.data["mode"] == "draft")
        with patch.object(ft.Control, "update", lambda _control: None):
            draft_option.on_click(None)
            _role(dialog, "create-task-title")[0].value = "Draft Task"
            self.save(dialog)
        task = created[0]
        self.assertEqual(TaskCreationMode.DRAFT, task.creation_mode)
        self.assertNotEqual("draft", task.lifecycle_status.value)
        self.assertEqual((), self.services.tasks.list_tasks.execute())
        drafts = self.services.tasks.list_tasks.execute(creation_mode=TaskCreationMode.DRAFT)
        self.assertEqual((task.id,), tuple(item.task.id for item in drafts))

    def test_nested_checklist_persists_progress_and_remove_disables_workspace(self):
        created = []
        dialog = self.dialog(on_created=created.append)
        with patch.object(ft.Control, "update", lambda _control: None):
            self.expand(dialog)
            _role(dialog, "checklist-toggle")[0].on_click(None)
            root = _role(dialog, "checklist-item-title")[0]
            root.value = "Root"
            root.on_change(None)
            add_child = next(
                item for item in _walk(dialog)
                if isinstance(getattr(item, "tooltip", None), ft.Tooltip)
                and item.tooltip.message == ui_text("tasks.add_checklist_child")
            )
            add_child.on_click(None)
            child = _role(dialog, "checklist-item-title")[1]
            child.value = "Child"
            child.on_change(None)
            completed = _role(dialog, "checklist-item-completed")[1]
            completed.value = True
            completed.on_change(None)
            _role(dialog, "create-task-title")[0].value = "Checklist Task"
            self.save(dialog)
        self.assertEqual(("Root", "Child"), tuple(item.title for item in created[0].checklist_items))
        self.assertEqual(0.5, created[0].checklist_progress)

        removed = self.dialog()
        with patch.object(ft.Control, "update", lambda _control: None):
            self.expand(removed)
            _role(removed, "checklist-toggle")[0].on_click(None)
            _button(removed, ui_text("tasks.remove_checklist")).on_click(None)
        self.assertFalse(removed.data["state"].checklist_enabled)
        self.assertFalse(_role(removed, "create-task-checklist")[0].visible)

    def test_large_checklist_stays_inside_scrollable_content_with_fixed_actions(self):
        dialog = self.dialog()
        with patch.object(ft.Control, "update", lambda _control: None):
            self.expand(dialog)
            _role(dialog, "checklist-toggle")[0].on_click(None)
            for _ in range(12):
                _role(dialog, "add-checklist-item")[0].on_click(None)
        self.assertEqual(13, len(_role(dialog, "checklist-item")))
        self.assertEqual(ft.ScrollMode.AUTO, dialog.content.content.scroll)
        self.assertEqual(1, len(dialog.actions))

    def test_project_context_is_inherited(self):
        dialog = self.dialog(selected_project_id=self.project.id)
        self.assertEqual([self.project.id], dialog.data["state"].selected_project_ids)

    def test_quick_task_creation_preserves_filters_and_refreshes_from_page_owner(self):
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
        quick_button = _role(control, "tasks-new-task")[0]
        with patch.object(ft.Control, "update", lambda _control: None):
            quick_button.on_click(None)
            dialog = page.dialogs[-1]
            _role(dialog, "create-task-title")[0].value = "Captured standalone Task"
            self.save(dialog)
        self.assertEqual([True], refresh_calls)
        self.assertEqual("Captured", state.task_filters.search)
        self.assertEqual("none", state.task_filters.project)
        self.assertEqual("yes", state.task_filters.urgency)

    def test_main_editor_uses_the_shared_task_details_dialog(self):
        task = self.services.tasks.create_task.execute(None, "Shared editor Task", schedule_start_date=date.today())
        editor = build_task_editor_content(
            self.services,
            (self.project,),
            task.id,
            LIGHT_TOKENS,
            lambda: None,
            lambda: None,
            lambda: None,
            self.fail,
        )
        self.assertEqual("task-details-dialog", editor.data["role"])
        self.assertEqual(1, len(_role(editor, "task-details-date")))
        self.assertEqual(1, len(_role(editor, "task-status-menu")))

    def test_dashboard_details_uses_picker_controls_instead_of_legacy_date_text(self):
        task = self.services.tasks.create_task.execute(None, "Dashboard details Task", schedule_start_date=date.today())
        dialog = build_task_details_dialog(
            self.services,
            (self.project,),
            task.id,
            date.today(),
            LIGHT_TOKENS,
            lambda: None,
            lambda: None,
            self.fail,
        )
        self.assertEqual(1, len(_role(dialog, "task-details-date")))
        self.assertEqual(1, len(_role(dialog, "deadline-trigger")))
        self.assertEqual([], [item for item in _walk(dialog) if getattr(item, "label", None) == ui_text("tasks.field_start_date")])

    def test_tasks_page_filters_and_view_modes_remain_intact(self):
        control = build_tasks(
            self.services,
            LIGHT_TOKENS,
            AppSessionState(route="/tasks"),
            lambda: None,
            self.fail,
        )
        project_dropdown = _role(control, "tasks-toolbar-filters")[0].controls[2]
        self.assertIn(ui_text("tasks.no_project"), [option.text for option in project_dropdown.options])
        mode_row = _role(control, "task-view-modes")[0]
        self.assertEqual(["Kanban", "Week", "Month"], [button.content for button in mode_row.controls])
        self.assertEqual("My Tasks", _role(control, "page-header-title")[0].value)

    def test_disposable_u2_work_does_not_touch_production_database(self):
        before = _hash(DEFAULT_DATABASE_PATH)
        self.services.tasks.create_task.execute(None, "Disposable standalone Task")
        after = _hash(DEFAULT_DATABASE_PATH)
        self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()
