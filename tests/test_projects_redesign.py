from __future__ import annotations

import shutil
import sqlite3
import unittest
import uuid
from datetime import date, datetime, time, timedelta
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import flet as ft

from overlord.bootstrap import bootstrap
from overlord.modules.cycles.domain import CycleStatus
from overlord.modules.projects.domain import ProjectStageStatus, ProjectStatus
from overlord.modules.tasks.domain import TaskLifecycle, TaskProjectAssignment
from overlord.ui.design_system.tokens import LIGHT_TOKENS
from overlord.ui.pages.projects.page import build_projects
from overlord.ui.state import AppSessionState
from overlord.ui.strings import ui_text


TEST_TEMP_ROOT = Path(__file__).resolve().parents[1] / "data" / "test-tmp"
TEST_TEMP_ROOT.mkdir(parents=True, exist_ok=True)


def _walk(control):
    yield control
    for name in ("title", "content"):
        child = getattr(control, name, None)
        if isinstance(child, ft.Control):
            yield from _walk(child)
    for name in ("controls", "actions", "items"):
        for child in getattr(control, name, ()) or ():
            yield from _walk(child)


def _role(control, role: str):
    return [item for item in _walk(control) if isinstance(getattr(item, "data", None), dict) and item.data.get("role") == role]


def _visible_text(control) -> str:
    return " ".join(str(getattr(item, "value", "")) for item in _walk(control))


class FakePage:
    def __init__(self):
        self.dialogs = []

    def show_dialog(self, dialog):
        self.dialogs.append(dialog)

    def pop_dialog(self):
        return self.dialogs.pop() if self.dialogs else None


class ProjectsRedesignTests(unittest.TestCase):
    def setUp(self):
        self.path = TEST_TEMP_ROOT / f"projects-redesign-{uuid.uuid4().hex}.db"
        self.services = bootstrap(self.path).services
        self.titan = self.services.projects.create_project.execute(
            "Project Titan",
            "Implement feedback from the last user testing session",
            color="#FFC7D2",
            favorite=True,
        )
        self.personal = self.services.projects.create_project.execute(
            "Personal",
            "Independent work",
            color="#D6F2E7",
        )
        self.plan = self.services.projects.create_plan.execute(self.titan.id, "User Testing Improvements")
        self.research = self.services.projects.create_stage.execute(self.titan.id, self.plan.id, "Collect feedback")
        self.design = self.services.projects.create_stage.execute(self.titan.id, self.plan.id, "Design updates")
        self.services.projects.change_stage_status.execute(self.research.id, ProjectStageStatus.COMPLETED)
        self.services.projects.change_stage_status.execute(self.design.id, ProjectStageStatus.IN_PROGRESS)
        self.shared = self.services.tasks.create_task.execute(
            None,
            "Review onboarding screens",
            project_links=(
                TaskProjectAssignment(self.titan.id, self.design.id),
                TaskProjectAssignment(self.personal.id),
            ),
            estimate_minutes=90,
        )

    def tearDown(self):
        self.path.unlink(missing_ok=True)
        for suffix in ("-wal", "-shm"):
            Path(f"{self.path}{suffix}").unlink(missing_ok=True)
        shutil.rmtree(TEST_TEMP_ROOT / "project-workspaces", ignore_errors=True)

    def build(self, route: str, *, page=None, navigate=None, refresh=None, state=None):
        return build_projects(
            self.services,
            LIGHT_TOKENS,
            route,
            navigate or (lambda _route: None),
            refresh or (lambda: None),
            self.fail,
            state or AppSessionState(route=route),
            page,
        )

    def test_list_uses_real_project_colors_fixed_expanded_width_and_no_legacy_favorite(self):
        control = self.build("/projects")
        cards = _role(control, "project-card")
        self.assertEqual({self.titan.id, self.personal.id}, {card.data["project_id"] for card in cards})
        titan_card = next(card for card in cards if card.data["project_id"] == self.titan.id)
        self.assertEqual("#FFC7D2", titan_card.data["color"])
        self.assertEqual(401, titan_card.data["width"])
        self.assertEqual(211, titan_card.data["height"])
        self.assertEqual("#E6B3BD", titan_card.data["hover_color"])
        grid = _role(control, "projects-grid")[0]
        self.assertEqual(401, grid.data["card_width"])
        self.assertEqual(4, grid.data["column_count"])
        self.assertEqual(12, grid.data["column_gap"])
        self.assertEqual("fixed-width-wrap", grid.data["layout"])
        self.assertFalse(_role(control, "project-favorite"))
        self.assertFalse(_role(control, "project-detail-favorite"))
        self.assertNotIn(ui_text("projects.results_count", count=2), _visible_text(control))

    def test_collapsed_sidebar_uses_354px_card_state(self):
        state = AppSessionState(route="/projects", sidebar_collapsed=True)
        control = self.build("/projects", state=state)
        cards = _role(control, "project-card")
        self.assertTrue(cards)
        self.assertEqual({354}, {card.data["width"] for card in cards})
        grid = _role(control, "projects-grid")[0]
        self.assertEqual("collapsed", grid.data["sidebar_state"])
        self.assertEqual(354, grid.data["card_width"])
        self.assertEqual(5, grid.data["column_count"])
        self.assertEqual(11, grid.data["column_gap"])
        state.sidebar_collapsed = False
        rebuilt = self.build("/projects", state=state)
        self.assertEqual(401, _role(rebuilt, "projects-grid")[0].data["card_width"])
        self.assertEqual(4, _role(rebuilt, "projects-grid")[0].data["column_count"])

    def test_search_and_reset_restore_the_default_project_results(self):
        state = AppSessionState(route="/projects")
        control = self.build("/projects", state=state)
        search = _role(control, "search")[0]
        grid = _role(control, "projects-grid")[0]
        reset = _role(control, "projects-reset")[0]
        self.assertFalse(reset.visible)
        search.value = "Titan"
        with patch.object(ft.Control, "update", lambda _control: None):
            search.on_change(None)
        self.assertEqual({self.titan.id}, {card.data["project_id"] for card in _role(grid, "project-card")})
        self.assertTrue(reset.visible)
        with patch.object(ft.Control, "update", lambda _control: None):
            reset.on_click(None)
        self.assertEqual("", state.project_filters.search)
        self.assertEqual("recent", state.project_filters.sort)
        self.assertFalse(state.project_filters.selected_project_ids)
        self.assertFalse(state.project_filters.selected_statuses)
        self.assertEqual({self.titan.id, self.personal.id}, {card.data["project_id"] for card in _role(grid, "project-card")})
        self.assertFalse(reset.visible)

    def test_filter_menus_use_real_data_counts_and_single_select_sort(self):
        state = AppSessionState(route="/projects")
        control = self.build("/projects", state=state)
        projects = _role(control, "projects-multiselect")[0]
        statuses = _role(control, "status-multiselect")[0]
        sort = _role(control, "projects-sort")[0]
        reset = _role(control, "projects-reset")[0]
        grid = _role(control, "projects-grid")[0]

        project_options = dict(projects.data["options"])
        self.assertEqual(
            {str(self.titan.id): self.titan.title, str(self.personal.id): self.personal.title},
            project_options,
        )
        self.assertEqual({value.value for value in ProjectStatus}, set(dict(statuses.data["options"])))
        self.assertEqual("multiple", projects.data["selection_mode"])
        self.assertEqual("multiple", statuses.data["selection_mode"])
        self.assertIsInstance(sort, ft.Dropdown)
        self.assertEqual(184, sort.width)
        self.assertEqual("single", sort.data["selection_mode"])

        titan_option = next(
            option for option in _role(projects, "multiselect-option")
            if option.data["value"] == str(self.titan.id)
        )
        with patch.object(ft.Control, "update", lambda _control: None):
            titan_option.on_click(None)
        self.assertEqual([self.titan.id], sorted(state.project_filters.selected_project_ids))
        self.assertEqual({self.titan.id}, {card.data["project_id"] for card in _role(grid, "project-card")})
        self.assertEqual(1, _role(projects, "multiselect-count")[0].data["count"])
        self.assertTrue(reset.visible)

        sort.value = "name"
        with patch.object(ft.Control, "update", lambda _control: None):
            sort.on_select(SimpleNamespace(control=sort))
        self.assertEqual("name", state.project_filters.sort)

    def test_project_body_and_notch_add_task_are_distinct_actions(self):
        page = FakePage()
        navigations: list[str] = []
        control = self.build("/projects", page=page, navigate=navigations.append)
        body = next(item for item in _role(control, "project-card-body") if item.data["project_id"] == self.titan.id)
        body.on_tap(None)
        self.assertEqual([f"/projects/{self.titan.id}"], navigations)
        add_task = next(item for item in _role(control, "project-add-task") if item.data["project_id"] == self.titan.id)
        add_task.on_tap(None)
        self.assertEqual("create-task-dialog", page.dialogs[-1].data["role"])
        self.assertEqual([self.titan.id], page.dialogs[-1].data["state"].selected_project_ids)
        self.assertEqual([f"/projects/{self.titan.id}"], navigations)

    def test_empty_project_card_uses_full_surface_create_action(self):
        page = FakePage()
        control = self.build("/projects", page=page)
        empty_card = _role(control, "project-add-card")[0]
        self.assertTrue(empty_card.data["full_surface_click"])
        action = _role(empty_card, "project-add-card-action")[0]
        action.on_tap(None)
        self.assertEqual("project-dialog", page.dialogs[-1].data["role"])

    def test_create_project_routes_explicitly_to_plan(self):
        page = FakePage()
        navigations: list[str] = []
        control = self.build("/projects", page=page, navigate=navigations.append)
        _role(control, "projects-new-project")[0].on_click(None)
        dialog = page.dialogs[-1]
        controls = dialog.content.content.controls
        controls[1].value = "Created Project"
        controls[2].value = "Created from the redesigned dialog"
        destination = _role(dialog, "project-destination")[0]
        plan = next(option for option in destination.controls if option.data["value"] == "plan")
        with patch.object(ft.Control, "update", lambda _control: None):
            plan.on_click(None)
        dialog.actions[-1].on_click(None)
        created = self.services.projects.list_projects.execute(search="Created Project")[0]
        self.assertEqual([f"/projects/{created.id}/plan"], navigations)

    def test_detail_shared_shell_tabs_and_linked_cycle_states(self):
        navigations: list[str] = []
        page = FakePage()
        without_cycle = self.build(
            f"/projects/{self.titan.id}",
            page=page,
            navigate=navigations.append,
        )
        tabs = _role(without_cycle, "navigation-tab")
        self.assertEqual(5, len(tabs))
        self.assertTrue(_role(without_cycle, "project-tab-bar")[0].data["baseline"])
        self.assertEqual({44}, {tab.data["stable_height"] for tab in tabs})
        self.assertEqual(1, sum(tab.data["active_indicator"] for tab in tabs))
        self.assertTrue(_role(without_cycle, "project-details-back"))
        self.assertTrue(_role(without_cycle, "project-details-more"))
        self.assertEqual("active", _role(without_cycle, "status-badge")[0].data["status"])
        self.assertNotIn(ui_text("projects.back"), _visible_text(without_cycle))
        linked = _role(without_cycle, "project-linked-cycle")[0]
        self.assertFalse(linked.data["filled"])
        self.assertIn(ui_text("projects.no_linked_cycle"), _visible_text(linked))
        _role(without_cycle, "project-details-back")[0].on_click(None)
        self.assertEqual(["/projects"], navigations)
        _role(without_cycle, "project-details-more")[0].on_click(None)
        self.assertEqual("project-dialog", page.dialogs[-1].data["role"])
        plan_tab = next(tab for tab in tabs if tab.data["tab"] == "plan")
        next(item for item in _walk(without_cycle) if getattr(item, "content", None) is plan_tab).on_tap(None)
        self.assertEqual(f"/projects/{self.titan.id}/plan", navigations[-1])

        cycle = self.services.cycles.create_cycle.execute("Titan 12-Week Plan", "Ship Titan", date.today())
        self.services.cycles.change_status.execute(cycle.id, CycleStatus.ACTIVE)
        self.services.cycles.connect_project.execute(cycle.id, self.titan.id)
        with_cycle = self.build(f"/projects/{self.titan.id}")
        self.assertTrue(_role(with_cycle, "project-linked-cycle")[0].data["filled"])
        self.assertIn("Titan 12-Week Plan", _visible_text(with_cycle))
        self.assertIn(
            ui_text("projects.cycle_week", week=1, length=cycle.length_weeks),
            _visible_text(_role(with_cycle, "project-linked-cycle")[0]),
        )

        self.services.cycles.change_status.execute(cycle.id, CycleStatus.COMPLETED)
        completed_cycle = self.build(f"/projects/{self.titan.id}")
        completed_link = _role(completed_cycle, "project-linked-cycle")[0]
        self.assertTrue(completed_link.data["filled"])
        self.assertIn("Titan 12-Week Plan", _visible_text(completed_link))
        self.assertNotIn(
            ui_text("projects.cycle_week", week=1, length=cycle.length_weeks),
            _visible_text(completed_link),
        )
        self.assertTrue(_role(completed_link, "project-linked-cycle-start-date"))

    def test_overview_uses_real_plan_timeline_and_intentional_empty_states(self):
        populated = self.build(f"/projects/{self.titan.id}")
        self.assertEqual(3, _role(populated, "project-overview-summary-row")[0].data["card_count"])
        self.assertEqual("8:4", _role(populated, "project-overview-main-row")[0].data["proportions"])
        progress = _role(populated, "project-plan-progress")[0]
        self.assertTrue(progress.data["filled"])
        timeline = _role(populated, "project-stage-timeline")[0]
        self.assertEqual(2, timeline.data["stage_count"])
        self.assertEqual(
            ["completed", "current"],
            [step.data["state"] for step in _role(populated, "project-stage-timeline-step")],
        )
        self.assertEqual(0.5, _role(populated, "project-overall-plan-progress")[0].data["value"])
        current_metric = next(
            metric
            for metric in _role(populated, "project-plan-metric")
            if metric.data["metric"] == "current"
        )
        self.assertEqual(0.0, current_metric.data["progress"])
        self.assertIn(ui_text("projects.overall_plan_progress"), _visible_text(progress))
        self.assertFalse(_role(populated, "recent-project-activity")[0].data["filled"])
        self.assertIn(ui_text("projects.recent_updates_empty"), _visible_text(populated))

        empty_project = self.services.projects.create_project.execute("Empty Project", "")
        empty = self.build(f"/projects/{empty_project.id}")
        self.assertFalse(_role(empty, "project-next-checkpoint")[0].data["filled"])
        self.assertFalse(_role(empty, "project-next-action")[0].data["filled"])
        self.assertFalse(_role(empty, "project-linked-cycle")[0].data["filled"])
        self.assertFalse(_role(empty, "project-plan-progress")[0].data["filled"])
        self.assertFalse(_role(empty, "recent-project-activity")[0].data["filled"])
        self.assertFalse(_role(empty, "project-details-description"))
        empty_text = _visible_text(empty)
        for key in (
            "projects.no_current_checkpoint",
            "projects.no_next_action",
            "projects.no_linked_cycle",
            "projects.no_project_plan",
            "projects.recent_updates_empty",
        ):
            self.assertIn(ui_text(key), empty_text)

    def test_overview_next_action_uses_real_task_status_and_navigation(self):
        deadline = date.today() + timedelta(days=2)
        task = self.services.tasks.update_task.execute(
            self.shared.id,
            next_action="Review the latest onboarding notes",
            schedule_start_date=date.today(),
            deadline_at=datetime.combine(deadline, time(17, 0)),
        )
        self.services.tasks.change_lifecycle.execute(task.id, TaskLifecycle.IN_PROGRESS)
        navigations: list[str] = []
        control = self.build(f"/projects/{self.titan.id}", navigate=navigations.append)
        next_action = _role(control, "project-next-action")[0]
        self.assertTrue(next_action.data["filled"])
        self.assertEqual("in_progress", _role(next_action, "status-badge")[0].data["status"])
        self.assertEqual(deadline.isoformat(), _role(next_action, "project-next-action-date")[0].data["date"])
        _role(next_action, "project-next-action-open")[0].on_click(None)
        self.assertEqual([f"/tasks?task={task.id}"], navigations)

    def test_overview_checkpoint_and_next_action_omit_only_missing_dates(self):
        cycle = self.services.cycles.create_cycle.execute("Checkpoint Plan", "Review Titan", date.today())
        self.services.cycles.connect_project.execute(cycle.id, self.titan.id)
        milestone = self.services.cycles.connect_milestone.execute(
            cycle.id,
            self.titan.id,
            "Dashboard task flow approved",
            "Approval is recorded.",
        )
        undated_action = self.services.tasks.create_task.execute(
            self.personal.id,
            "Undated action task",
            next_action="Prepare the next review",
        )
        undated_checkpoint = self.build(f"/projects/{self.titan.id}")
        self.assertTrue(_role(undated_checkpoint, "project-next-checkpoint")[0].data["filled"])
        self.assertFalse(_role(undated_checkpoint, "project-checkpoint-date"))
        undated_next_action = self.build(f"/projects/{self.personal.id}")
        self.assertTrue(_role(undated_next_action, "project-next-action")[0].data["filled"])
        self.assertFalse(_role(undated_next_action, "project-next-action-date"))
        self.assertEqual(
            undated_action.id,
            self.services.projects.get_detail.execute(self.personal.id).next_action_task_id,
        )

        target = date.today() + timedelta(days=7)
        connection = sqlite3.connect(self.path)
        try:
            connection.execute(
                "UPDATE milestones SET target_date=? WHERE id=?",
                (target.isoformat(), milestone.id),
            )
            connection.commit()
        finally:
            connection.close()
        dated = self.build(f"/projects/{self.titan.id}")
        self.assertEqual(target.isoformat(), _role(dated, "project-checkpoint-date")[0].data["date"])

    def test_plan_and_tasks_by_stage_use_real_stage_assignments(self):
        plan_control = self.build(f"/projects/{self.titan.id}/plan")
        stages = _role(plan_control, "project-stage")
        self.assertEqual({self.research.id, self.design.id}, {stage.data["stage_id"] for stage in stages})
        task_control = self.build(f"/projects/{self.titan.id}/tasks")
        self.assertEqual(1, len(_role(task_control, "project-task-card")))
        filters = _role(task_control, "project-task-filters")[0]
        stage_toggle = filters.controls[0].content.controls[1]
        with patch.object(ft.Control, "update", lambda _control: None):
            stage_toggle.on_click(None)
        self.assertIn("Design updates", _visible_text(task_control))
        self.assertIn("Review onboarding screens", _visible_text(task_control))

    def test_project_task_opens_the_canonical_shared_task_details_route(self):
        navigations: list[str] = []
        control = self.build(
            f"/projects/{self.titan.id}/tasks",
            navigate=navigations.append,
        )
        body = _role(control, "task-body")[0]
        body.on_tap(None)
        self.assertEqual([f"/tasks?task={self.shared.id}"], navigations)

    def test_project_task_completion_uses_the_canonical_confirmation_dialog(self):
        page = FakePage()
        refreshed = []
        control = self.build(
            f"/projects/{self.titan.id}/tasks",
            page=page,
            refresh=lambda: refreshed.append(True),
        )
        completion = next(
            item for item in _role(control, "completion")
            if item.data["task_id"] == self.shared.id
        )
        completion.on_tap(None)
        self.assertNotEqual(TaskLifecycle.COMPLETED, self.services.tasks.get_editor.execute(self.shared.id).task.lifecycle_status)
        dialog = page.dialogs[-1]
        self.assertEqual("complete-task-dialog", dialog.data["role"])
        with patch.object(ft.Control, "update", lambda _control: None):
            _role(dialog, "complete-task-confirm")[0].on_click(None)
        self.assertEqual(TaskLifecycle.COMPLETED, self.services.tasks.get_editor.execute(self.shared.id).task.lifecycle_status)
        self.assertEqual([True], refreshed)

    def test_project_note_is_stored_as_local_markdown_and_rendered(self):
        note = self.services.projects.create_note.execute(self.titan.id, "Testing summary", "# Session overview\nValidated locally.")
        self.assertTrue(note.relative_path.endswith(".md"))
        self.assertNotIn("Session overview", str(note.relative_path))
        workspace = self.services.projects.get_workspace.execute(self.titan.id)
        self.assertEqual("# Session overview\nValidated locally.", workspace.notes[0].content)
        source = TEST_TEMP_ROOT / f"attachment-{uuid.uuid4().hex}.txt"
        source.write_text("local file evidence", encoding="utf-8")
        try:
            attached = self.services.projects.add_file.execute(self.titan.id, source)
            self.assertEqual(source.name, attached.display_name)
            self.assertGreater(attached.size_bytes, 0)
        finally:
            source.unlink(missing_ok=True)
        control = self.build(f"/projects/{self.titan.id}/notes")
        self.assertIn("Testing summary", _visible_text(control))
        self.assertIn(attached.display_name, _visible_text(control))

    def test_archive_is_reversible_and_preserves_task_links(self):
        refreshed = []
        control = self.build(f"/projects/{self.titan.id}/archive", refresh=lambda: refreshed.append(True))
        archive_button = _role(control, "project-archive-toggle")[0]
        archive_button.on_click(None)
        self.assertEqual(ProjectStatus.ARCHIVED, self.services.projects.list_projects.execute(ProjectStatus.ARCHIVED)[0].status)
        self.assertEqual((self.shared.id,), tuple(item.task.id for item in self.services.tasks.list_tasks.execute(project_id=self.titan.id)))
        self.assertEqual([True], refreshed)


if __name__ == "__main__":
    unittest.main()
