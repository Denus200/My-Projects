import hashlib
import sqlite3
import unittest
import uuid
from datetime import date, datetime, time, timedelta
from pathlib import Path
from unittest.mock import patch

import flet as ft

from overlord.bootstrap import DEFAULT_DATABASE_PATH, bootstrap
from overlord.demo import demo_seed_fingerprint, seed_demo_database
from overlord.modules.blockers.domain import BlockerType
from overlord.modules.cycles.domain import CycleStatus
from overlord.modules.projects.domain import ProjectStageStatus, ProjectStatus
from overlord.modules.tasks.domain import TaskLifecycle, TaskProjectAssignment
from overlord.ui.design_system.tokens import LIGHT_TOKENS
from overlord.ui.pages.projects.page import _task_matches, build_projects
from overlord.ui.state import AppSessionState, ProjectFilterState
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

    def test_plan_progress_separates_current_stage_from_whole_plan(self):
        plan = self.services.projects.create_plan.execute(self.project.id, "Foundation UX Improvements")
        stages = tuple(
            self.services.projects.create_stage.execute(self.project.id, plan.id, title)
            for title in ("Research", "Findings", "Design", "Delivery")
        )
        for stage in stages[:2]:
            self.services.projects.change_stage_status.execute(stage.id, ProjectStageStatus.COMPLETED)
        self.services.projects.change_stage_status.execute(stages[2].id, ProjectStageStatus.IN_PROGRESS)

        initial = self.services.projects.get_detail.execute(self.project.id).plan_progress
        self.assertIsNotNone(initial)
        self.assertEqual(2, initial.completed_stage_count)
        self.assertEqual(0.0, initial.current_stage_progress)
        self.assertEqual(0.5, initial.overall_progress)
        self.assertEqual(stages[2].id, initial.current_stage.stage.id)

        completed = self.services.tasks.create_task.execute(
            None,
            "Completed design task",
            project_links=(TaskProjectAssignment(self.project.id, stages[2].id),),
        )
        self.services.tasks.complete_task.execute(completed.id)
        self.services.tasks.create_task.execute(
            None,
            "Open design task",
            project_links=(TaskProjectAssignment(self.project.id, stages[2].id),),
        )
        partial = self.services.projects.get_detail.execute(self.project.id).plan_progress
        self.assertEqual(0.5, partial.current_stage_progress)
        self.assertEqual(0.625, partial.overall_progress)

        self.services.projects.change_stage_status.execute(stages[2].id, ProjectStageStatus.COMPLETED)
        self.services.projects.change_stage_status.execute(stages[3].id, ProjectStageStatus.COMPLETED)
        finished = self.services.projects.get_detail.execute(self.project.id).plan_progress
        self.assertEqual(4, finished.completed_stage_count)
        self.assertIsNone(finished.current_stage_progress)
        self.assertEqual(1.0, finished.overall_progress)

    def test_checkpoint_binding_uses_milestone_target_date_only(self):
        cycle = self.services.cycles.create_cycle.execute("Checkpoint Cycle", "Review evidence", date.today())
        self.services.cycles.connect_project.execute(cycle.id, self.project.id)
        milestone = self.services.cycles.connect_milestone.execute(
            cycle.id,
            self.project.id,
            "Dashboard task flow approved",
            "Approval is recorded.",
        )
        undated = self.services.projects.get_detail.execute(self.project.id)
        self.assertEqual(milestone.id, undated.current_milestone.id)
        self.assertIsNone(undated.current_milestone.target_date)
        self.assertEqual(cycle.id, undated.current_milestone_cycle_id)

        target = date.today() + timedelta(days=9)
        connection = sqlite3.connect(self.path)
        try:
            connection.execute(
                "UPDATE milestones SET target_date=? WHERE id=?",
                (target.isoformat(), milestone.id),
            )
            connection.commit()
        finally:
            connection.close()
        dated = self.services.projects.get_detail.execute(self.project.id)
        self.assertEqual(target, dated.current_milestone.target_date)

    def test_next_action_binding_preserves_selected_task_identity_and_optional_date(self):
        planned = self.services.tasks.create_task.execute(
            self.project.id,
            "Planned task",
            next_action="Use the shared action text",
        )
        selected = self.services.tasks.create_task.execute(
            self.project.id,
            "Current task",
            schedule_start_date=date.today(),
            deadline_at=datetime.combine(date.today() + timedelta(days=2), time(17, 0)),
            next_action="Use the shared action text",
        )
        self.services.tasks.change_lifecycle.execute(selected.id, TaskLifecycle.IN_PROGRESS)
        detail = self.services.projects.get_detail.execute(self.project.id)
        self.assertEqual(selected.id, detail.next_action_task_id)
        self.assertNotEqual(planned.id, detail.next_action_task_id)

    def test_linked_cycle_uses_active_then_most_recent_persisted_relation(self):
        older = self.services.cycles.create_cycle.execute(
            "Completed Plan",
            "Completed outcome",
            date.today() - timedelta(weeks=14),
        )
        self.services.cycles.connect_project.execute(older.id, self.project.id)
        self.services.cycles.change_status.execute(older.id, CycleStatus.COMPLETED)
        inactive = self.services.projects.get_detail.execute(self.project.id)
        self.assertIsNone(inactive.active_cycle)
        self.assertEqual(older.id, inactive.linked_cycle.id)
        self.assertIsNone(inactive.linked_cycle.current_week(date.today()))

        newer_inactive = self.services.cycles.create_cycle.execute(
            "Draft Plan",
            "Future outcome",
            date.today() - timedelta(weeks=1),
        )
        self.services.cycles.connect_project.execute(newer_inactive.id, self.project.id)
        most_recent = self.services.projects.get_detail.execute(self.project.id)
        self.assertIsNone(most_recent.active_cycle)
        self.assertEqual(newer_inactive.id, most_recent.linked_cycle.id)

        active = self.services.cycles.create_cycle.execute("Active Plan", "Current outcome", date.today())
        self.services.cycles.change_status.execute(active.id, CycleStatus.ACTIVE)
        self.services.cycles.connect_project.execute(active.id, self.project.id)
        current = self.services.projects.get_detail.execute(self.project.id)
        self.assertEqual(active.id, current.active_cycle.id)
        self.assertEqual(active.id, current.linked_cycle.id)
        self.assertEqual(1, current.linked_cycle.current_week(date.today()))

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
        self.assertEqual(1, len(_role(control, "projects-grid")))
        self.assertEqual(1, len(_role(control, "projects-toolbar")))
        self.assertEqual([], page.dialogs)
        with patch.object(ft.Control, "update", lambda _control: None):
            _role(control, "projects-new-project")[0].on_click(None)
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
            f"/projects/{self.project.id}/tasks",
            lambda _route: None,
            lambda: None,
            self.fail,
            AppSessionState(route=f"/projects/{self.project.id}/tasks"),
            page,
        )
        filters = _role(control, "project-task-filters")[0]
        quick_button = filters.controls[-1].content
        quick_button.on_click(None)
        self.assertEqual(
            [self.project.id],
            page.dialogs[-1].data["state"].selected_project_ids,
        )

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
        visible = " ".join(str(getattr(item, "value", "")) for item in _walk(control))
        self.assertIn(ui_text("projects.no_project_plan"), visible)
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
