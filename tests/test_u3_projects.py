import hashlib
import unittest
import uuid
from datetime import date
from pathlib import Path
from unittest.mock import patch

import flet as ft

from overlord.bootstrap import DEFAULT_DATABASE_PATH, bootstrap
from overlord.demo import demo_seed_fingerprint, seed_demo_database
from overlord.domain.cycles import CycleStatus
from overlord.domain.projects import ProjectStatus
from overlord.domain.tasks import BlockerType, TaskLifecycle
from overlord.presentation.design_system.tokens import LIGHT_TOKENS
from overlord.presentation.pages.projects import _task_matches, build_projects
from overlord.presentation.state import AppSessionState, ProjectFilterState
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


class U3ProjectTests(unittest.TestCase):
    def setUp(self):
        self.path = TEST_TEMP_ROOT / f"u3-projects-{uuid.uuid4().hex}.db"
        self.services = bootstrap(self.path).services
        self.project = self.services.projects.create_project.execute(
            "Portfolio Context",
            "Evidence-backed project description",
        )

    def tearDown(self):
        self.path.unlink(missing_ok=True)
        Path(f"{self.path}.seed.json").unlink(missing_ok=True)

    def test_project_search_covers_title_and_description_and_status_filter(self):
        archived = self.services.projects.create_project.execute("Historical Work", "Contains a hidden phrase")
        self.services.projects.update_project.execute(archived.id, status=ProjectStatus.ARCHIVED)
        by_description = self.services.projects.list_summaries.execute(search="hidden phrase")
        archived_only = self.services.projects.list_summaries.execute(ProjectStatus.ARCHIVED)
        self.assertEqual((archived.id,), tuple(item.project.id for item in by_description))
        self.assertEqual((archived.id,), tuple(item.project.id for item in archived_only))

    def test_progress_excludes_cancelled_tasks_and_is_unavailable_without_eligible_tasks(self):
        cancelled = self.services.tasks.create_task.execute(self.project.id, "Cancelled work")
        self.services.tasks.change_lifecycle.execute(cancelled.id, TaskLifecycle.CANCELLED, "Not required")
        detail = self.services.projects.get_detail.execute(self.project.id)
        self.assertEqual(0, detail.eligible_task_count)
        self.assertEqual(0, detail.open_task_count)
        self.assertIsNone(detail.progress)

    def test_summary_exposes_honest_progress_blocker_milestone_cycle_and_next_action(self):
        current = self.services.tasks.create_task.execute(
            self.project.id,
            "Current execution Task",
            definition_of_done="The work is accepted.",
            next_action="Open the source document.",
        )
        self.services.tasks.change_lifecycle.execute(current.id, TaskLifecycle.IN_PROGRESS, "Started")
        complete = self.services.tasks.create_task.execute(self.project.id, "Completed Task")
        self.services.tasks.complete_task.execute(complete.id)
        self.services.tasks.open_blocker.execute(current.id, BlockerType.DEPENDENCY, "Waiting for review.")
        cycle = self.services.cycles.create_cycle.execute("Active Cycle", "Ship the outcome", date.today())
        self.services.cycles.change_status.execute(cycle.id, CycleStatus.ACTIVE)
        self.services.cycles.connect_project.execute(cycle.id, self.project.id)
        milestone = self.services.cycles.connect_milestone.execute(
            cycle.id,
            self.project.id,
            "Approval received",
            "The work has explicit approval.",
        )
        detail = self.services.projects.get_detail.execute(self.project.id)
        self.assertEqual(2, detail.eligible_task_count)
        self.assertEqual(1, detail.completed_task_count)
        self.assertEqual(1, detail.open_task_count)
        self.assertEqual(0.5, detail.progress)
        self.assertEqual("Open the source document.", detail.next_action)
        self.assertEqual(milestone.id, detail.current_milestone.id)
        self.assertEqual(cycle.id, detail.active_cycle.id)
        self.assertEqual("Current execution Task", detail.blockers[0].task_title)

    def test_multiple_planned_next_actions_are_not_silently_ranked(self):
        self.services.tasks.create_task.execute(self.project.id, "First", next_action="First action")
        self.services.tasks.create_task.execute(self.project.id, "Second", next_action="Second action")
        self.assertIsNone(self.services.projects.get_detail.execute(self.project.id).next_action)

    def test_projects_page_is_browse_first_and_creation_is_transient(self):
        page = FakePage()
        state = AppSessionState(
            route="/projects",
            project_filters=ProjectFilterState(search="Created", status="all"),
        )
        refresh_calls = []
        control = build_projects(
            self.services,
            LIGHT_TOKENS,
            "/projects",
            lambda _route: None,
            lambda: refresh_calls.append(True),
            self.fail,
            state,
            page,
        )
        self.assertEqual(ui_text("projects.browse"), control.controls[1].content.controls[0].value)
        self.assertNotEqual(ui_text("projects.new_title"), control.controls[1].content.controls[0].value)
        with patch.object(ft.Control, "update", lambda _control: None):
            control.controls[0].controls[-1].on_click(None)
            dialog = page.dialogs[-1]
            dialog.content.content.controls[1].value = "Created Project"
            dialog.content.content.controls[2].value = "Created from compact dialog"
            dialog.actions[-1].on_click(None)
        self.assertEqual([], refresh_calls)
        self.assertEqual("Created", state.project_filters.search)
        self.assertEqual(1, len(self.services.projects.list_projects.execute(search="Created Project")))

    def test_project_detail_quick_task_reuses_u2_dialog_with_project_preselected(self):
        page = FakePage()
        control = build_projects(
            self.services,
            LIGHT_TOKENS,
            f"/projects/{self.project.id}",
            lambda _route: None,
            lambda: None,
            self.fail,
            AppSessionState(route=f"/projects/{self.project.id}"),
            page,
        )
        tasks_card = control.controls[-1]
        quick_button = tasks_card.content.controls[1].controls[-1]
        quick_button.on_click(None)
        project_dropdown = page.dialogs[-1].content.content.controls[2]
        self.assertEqual(str(self.project.id), project_dropdown.value)

    def test_project_task_views_separate_open_completed_and_blocked(self):
        open_task = self.services.tasks.create_task.execute(self.project.id, "Open")
        completed_task = self.services.tasks.create_task.execute(self.project.id, "Completed")
        self.services.tasks.complete_task.execute(completed_task.id)
        blocked_task = self.services.tasks.create_task.execute(self.project.id, "Blocked")
        self.services.tasks.open_blocker.execute(blocked_task.id, BlockerType.OTHER, "Needs input")
        items = self.services.tasks.list_tasks.execute(project_id=self.project.id)
        by_title = {item.task.title: item for item in items}
        self.assertTrue(_task_matches(by_title["Open"], "open"))
        self.assertFalse(_task_matches(by_title["Completed"], "open"))
        self.assertTrue(_task_matches(by_title["Completed"], "completed"))
        self.assertTrue(_task_matches(by_title["Blocked"], "blocked"))

    def test_empty_project_detail_constructs_without_false_zero_progress(self):
        detail = self.services.projects.get_detail.execute(self.project.id)
        self.assertIsNone(detail.current_milestone)
        self.assertIsNone(detail.active_cycle)
        control = build_projects(
            self.services,
            LIGHT_TOKENS,
            f"/projects/{self.project.id}",
            lambda _route: None,
            lambda: None,
            self.fail,
        )
        self.assertIsInstance(control, ft.Control)
        progress_card = control.controls[2].controls[0]
        visible = " ".join(str(getattr(item, "value", "")) for item in progress_card.content.controls)
        self.assertIn("Progress unavailable", visible)
        self.assertNotIn("0%", visible)

    def test_project_lifecycle_changes_preserve_project_and_tasks(self):
        task = self.services.tasks.create_task.execute(self.project.id, "Preserved Task")
        for status in (ProjectStatus.ON_HOLD, ProjectStatus.COMPLETED, ProjectStatus.ARCHIVED, ProjectStatus.ACTIVE):
            updated = self.services.projects.update_project.execute(self.project.id, status=status)
            self.assertEqual(status, updated.status)
        self.assertEqual(task.id, self.services.tasks.list_tasks.execute(project_id=self.project.id)[0].task.id)

    def test_standalone_tasks_remain_unaffected_by_project_queries(self):
        standalone = self.services.tasks.create_task.execute(None, "Standalone Task")
        self.services.projects.list_summaries.execute()
        matches = self.services.tasks.list_tasks.execute(without_project=True)
        self.assertIn(standalone.id, tuple(item.task.id for item in matches))

    def test_disposable_u3_work_does_not_touch_production_database(self):
        before = _hash(DEFAULT_DATABASE_PATH)
        self.services.projects.create_project.execute("Disposable U3 Project")
        after = _hash(DEFAULT_DATABASE_PATH)
        self.assertEqual(before, after)

    def test_u3_demo_seed_is_deterministic_and_covers_project_states(self):
        first = seed_demo_database(self.path, today=date(2026, 8, 7), reset=True)
        first_fingerprint = demo_seed_fingerprint(self.path)
        second = seed_demo_database(self.path, today=date(2026, 8, 7), reset=True)
        second_fingerprint = demo_seed_fingerprint(self.path)
        services = bootstrap(self.path).services
        projects = services.projects.list_summaries.execute()
        by_title = {item.project.title: item for item in projects}
        self.assertEqual(7, first.project_count)
        self.assertEqual(first.project_count, second.project_count)
        self.assertEqual(first_fingerprint, second_fingerprint)
        self.assertIsNotNone(by_title["Portfolio Refresh"].active_cycle)
        self.assertIsNone(by_title["Overlord"].active_cycle)
        self.assertIsNone(by_title["Home"].current_milestone)
        self.assertIsNone(by_title["Health Admin"].progress)
        self.assertEqual(ProjectStatus.COMPLETED, by_title["Website Launch"].project.status)
        self.assertEqual(ProjectStatus.ARCHIVED, by_title["Old Job Search"].project.status)


if __name__ == "__main__":
    unittest.main()
