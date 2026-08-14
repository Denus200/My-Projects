import hashlib
import unittest
import uuid
from datetime import date
from pathlib import Path
from unittest.mock import patch

import flet as ft

from overlord.modules.cycles.application import WeeklyOutcomeDraft
from overlord.bootstrap import DEFAULT_DATABASE_PATH, bootstrap
from overlord.demo import demo_seed_fingerprint, seed_demo_database
from overlord.modules.cycles.domain import CycleStatus, WeeklyOutcomeStatus
from overlord.infrastructure.sqlite.repositories import SqliteCycleRepository
from overlord.ui.design_system.tokens import LIGHT_TOKENS
from overlord.ui.pages.cycles.page import build_cycles
from overlord.ui.state import AppSessionState, CycleFilterState, CycleWizardState
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


class U4CycleTests(unittest.TestCase):
    def setUp(self):
        self.path = TEST_TEMP_ROOT / f"u4-cycles-{uuid.uuid4().hex}.db"
        self.services = bootstrap(self.path).services
        self.project = self.services.projects.create_project.execute("Connected Project", "Cycle context")

    def tearDown(self):
        self.path.unlink(missing_ok=True)
        Path(f"{self.path}.seed.json").unlink(missing_ok=True)

    def test_cycle_summaries_support_search_status_current_week_and_explicit_denominator(self):
        cycle = self.services.cycles.create_cycle.execute("Focused Cycle", "Ship the useful result", date(2026, 8, 1), 12)
        self.services.cycles.connect_project.execute(cycle.id, self.project.id)
        self.services.cycles.set_weekly_outcome.execute(cycle.id, 1, "First", "First is accepted", WeeklyOutcomeStatus.ACHIEVED)
        self.services.cycles.set_weekly_outcome.execute(cycle.id, 2, "Second", "Second is reviewed", WeeklyOutcomeStatus.PARTIAL)
        self.services.cycles.set_weekly_outcome.execute(cycle.id, 3, "Third", "Third is complete", WeeklyOutcomeStatus.PLANNED)
        self.services.cycles.change_status.execute(cycle.id, CycleStatus.ACTIVE)
        summary = self.services.cycles.list_summaries.execute(CycleStatus.ACTIVE, "useful result")[0]
        self.assertEqual(cycle.id, summary.cycle.id)
        self.assertEqual(1, summary.achieved_count)
        self.assertEqual(1, summary.partial_count)
        self.assertEqual(1, summary.planned_count)
        self.assertEqual(3, summary.scheduled_outcome_count)
        self.assertEqual(9, summary.unplanned_week_count)
        self.assertEqual(3, summary.current_week(date(2026, 8, 15)))

    def test_atomic_create_plan_connects_project_milestone_and_weekly_outcomes(self):
        source = self.services.cycles.create_cycle.execute("Source", "Hold existing Milestone", date(2026, 1, 1))
        milestone = self.services.cycles.connect_milestone.execute(
            source.id,
            self.project.id,
            "Existing Milestone",
            "The existing milestone is complete when reviewed.",
        )
        cycle = self.services.cycles.create_plan.execute(
            "Atomic Plan",
            "Create the full graph once",
            date(2026, 9, 1),
            12,
            project_ids=(self.project.id,),
            milestone_ids=(milestone.id,),
            weekly_outcomes=(WeeklyOutcomeDraft(1, "Plan week one", "Week one has a reviewed result."),),
        )
        detail = self.services.cycles.get_detail.execute(cycle.id)
        self.assertEqual(CycleStatus.DRAFT, cycle.status)
        self.assertEqual((self.project.id,), tuple(item.id for item in detail.projects))
        self.assertEqual((milestone.id,), tuple(item.id for item in detail.milestones))
        self.assertEqual((1,), tuple(item.week_number for item in detail.weekly_outcomes))

    def test_atomic_create_plan_rolls_back_on_weekly_outcome_failure(self):
        before = len(self.services.cycles.search_cycles.execute())
        with patch.object(SqliteCycleRepository, "set_weekly_outcome", side_effect=RuntimeError("simulated failure")):
            with self.assertRaisesRegex(RuntimeError, "simulated failure"):
                self.services.cycles.create_plan.execute(
                    "Rollback Plan",
                    "Leave no partial Cycle",
                    date(2026, 9, 1),
                    12,
                    project_ids=(self.project.id,),
                    weekly_outcomes=(WeeklyOutcomeDraft(1, "Week one", "The week is reviewed."),),
                )
        self.assertEqual(before, len(self.services.cycles.search_cycles.execute()))

    def test_active_cycle_conflict_is_explicit_and_creates_no_partial_cycle(self):
        active = self.services.cycles.create_cycle.execute("Existing Active", "Stay active", date.today())
        self.services.cycles.change_status.execute(active.id, CycleStatus.ACTIVE)
        before = len(self.services.cycles.search_cycles.execute())
        with self.assertRaisesRegex(ValueError, "already active"):
            self.services.cycles.create_plan.execute(
                "Conflicting",
                "Must remain a draft choice",
                date.today(),
                12,
                activate=True,
            )
        self.assertEqual(before, len(self.services.cycles.search_cycles.execute()))

    def test_cycles_page_is_browse_first_and_preserves_filters(self):
        self.services.cycles.create_cycle.execute("Browse Me", "Meaningful Outcome", date.today())
        state = AppSessionState(route="/cycles", cycle_filters=CycleFilterState(search="Browse", status="draft"))
        routes = []
        control = build_cycles(
            self.services,
            LIGHT_TOKENS,
            "/cycles",
            routes.append,
            lambda: None,
            self.fail,
            state,
        )
        browse_card = _role(control, "page-content")[0].controls[0]
        self.assertEqual(ui_text("cycles.browse"), browse_card.content.controls[0].value)
        self.assertEqual("Browse", state.cycle_filters.search)
        self.assertEqual("draft", state.cycle_filters.status)
        _role(control, "page-header-actions")[0].controls[0].on_click(None)
        self.assertEqual(["/cycles/new"], routes)

    def test_wizard_has_exactly_five_steps_and_preserves_identity_on_validation_failure(self):
        state = AppSessionState(route="/cycles/new")
        control = build_cycles(
            self.services,
            LIGHT_TOKENS,
            "/cycles/new",
            lambda _route: None,
            lambda: None,
            self.fail,
            state,
        )
        host = _role(control, "page-content")[0].controls[0]
        self.assertEqual(5, len(host.content.controls[0].controls))
        step_card = host.content.controls[1]
        title = step_card.content.controls[1]
        outcome = step_card.content.controls[2]
        title.value = "Preserved title"
        with patch.object(ft.Control, "update", lambda _control: None):
            host.content.controls[-1].controls[-1].on_click(None)
        self.assertEqual(1, state.cycle_wizard.step)
        self.assertEqual("Preserved title", state.cycle_wizard.title)
        self.assertTrue(outcome.error)

    def test_wizard_back_and_continue_preserve_state_across_all_five_steps(self):
        state = AppSessionState(route="/cycles/new")
        control = build_cycles(
            self.services,
            LIGHT_TOKENS,
            "/cycles/new",
            lambda _route: None,
            lambda: None,
            self.fail,
            state,
        )
        host = _role(control, "page-content")[0].controls[0]
        with patch.object(ft.Control, "update", lambda _control: None):
            identity = host.content.controls[1].content.controls
            identity[1].value = "Five Step Plan"
            identity[2].value = "Reach a meaningful result"
            host.content.controls[-1].controls[-1].on_click(None)
            self.assertEqual(2, state.cycle_wizard.step)
            dates = host.content.controls[1].content.controls[1]
            dates.controls[1].content.value = "2"
            host.content.controls[-1].controls[-1].on_click(None)
            self.assertEqual(3, state.cycle_wizard.step)
            host.content.controls[-1].controls[-1].on_click(None)
            self.assertEqual(4, state.cycle_wizard.step)
            host.content.controls[-1].controls[-1].on_click(None)
            self.assertEqual(5, state.cycle_wizard.step)
            host.content.controls[-1].controls[1].on_click(None)
            self.assertEqual(4, state.cycle_wizard.step)
        self.assertEqual("Five Step Plan", state.cycle_wizard.title)
        self.assertEqual("Reach a meaningful result", state.cycle_wizard.main_outcome)

    def test_atomic_plan_can_create_and_activate_when_no_conflict_exists(self):
        cycle = self.services.cycles.create_plan.execute(
            "Activate Me",
            "Become the active execution period",
            date.today(),
            12,
            activate=True,
        )
        self.assertEqual(CycleStatus.ACTIVE, cycle.status)
        self.assertEqual(cycle.id, self.services.cycles.list_summaries.execute(CycleStatus.ACTIVE)[0].cycle.id)

    def test_wizard_cancel_creates_no_partial_records(self):
        state = AppSessionState(route="/cycles/new")
        routes = []
        before = len(self.services.cycles.search_cycles.execute())
        control = build_cycles(
            self.services,
            LIGHT_TOKENS,
            "/cycles/new",
            routes.append,
            lambda: None,
            self.fail,
            state,
        )
        host = _role(control, "page-content")[0].controls[0]
        host.content.controls[-1].controls[0].on_click(None)
        self.assertIsNone(state.cycle_wizard)
        self.assertEqual(before, len(self.services.cycles.search_cycles.execute()))
        self.assertEqual(["/cycles"], routes)

    def test_review_step_can_create_draft_without_partial_navigation(self):
        state = AppSessionState(
            route="/cycles/new",
            cycle_wizard=CycleWizardState(
                step=5,
                title="Reviewed Draft",
                main_outcome="Create only after review",
                start_date="2026-09-01",
                length_weeks=12,
                selected_project_ids={self.project.id},
                weekly_titles={1: "Week one"},
                weekly_definitions={1: "Week one is reviewed."},
            ),
        )
        routes = []
        page = FakePage()
        control = build_cycles(
            self.services,
            LIGHT_TOKENS,
            "/cycles/new",
            routes.append,
            lambda: None,
            self.fail,
            state,
            page,
        )
        host = _role(control, "page-content")[0].controls[0]
        actions = host.content.controls[-1]
        actions.controls[-2].on_click(None)
        created = self.services.cycles.search_cycles.execute(search="Reviewed Draft")
        self.assertEqual(1, len(created))
        self.assertEqual(CycleStatus.DRAFT, created[0].status)
        self.assertIsNone(state.cycle_wizard)
        self.assertEqual([f"/cycles/{created[0].id}"], routes)

    def test_weekly_outcome_edit_updates_only_selected_week(self):
        cycle = self.services.cycles.create_cycle.execute("Edit Cycle", "Edit one week", date.today())
        self.services.cycles.set_weekly_outcome.execute(cycle.id, 1, "Original one", "Original one is done.")
        self.services.cycles.set_weekly_outcome.execute(cycle.id, 2, "Original two", "Original two is done.")
        page = FakePage()
        control = build_cycles(
            self.services,
            LIGHT_TOKENS,
            f"/cycles/{cycle.id}",
            lambda _route: None,
            lambda: None,
            self.fail,
            AppSessionState(route=f"/cycles/{cycle.id}"),
            page,
        )
        first_week_row = _role(control, "page-content")[0].controls[2].content.controls[1]
        first_week_row.content.controls[-1].on_click(None)
        dialog = page.dialogs[-1]
        dialog.content.content.controls[0].value = "Updated one"
        dialog.content.content.controls[1].value = "Updated one is reviewed."
        dialog.content.content.controls[2].value = WeeklyOutcomeStatus.PARTIAL.value
        with patch.object(ft.Control, "update", lambda _control: None):
            dialog.actions[-1].on_click(None)
        outcomes = {item.week_number: item for item in self.services.cycles.get_detail.execute(cycle.id).weekly_outcomes}
        self.assertEqual("Updated one", outcomes[1].title)
        self.assertEqual(WeeklyOutcomeStatus.PARTIAL, outcomes[1].status)
        self.assertEqual("Original two", outcomes[2].title)

    def test_cycle_detail_project_action_navigates_to_existing_project_route(self):
        cycle = self.services.cycles.create_cycle.execute("Connected", "Navigate to Project", date.today())
        self.services.cycles.connect_project.execute(cycle.id, self.project.id)
        routes = []
        control = build_cycles(
            self.services,
            LIGHT_TOKENS,
            f"/cycles/{cycle.id}",
            routes.append,
            lambda: None,
            self.fail,
        )
        connections = _role(control, "page-content")[0].controls[3]
        projects_card = connections.controls[0]
        project_row = projects_card.content.controls[1].content
        project_row.controls[-1].on_click(None)
        self.assertEqual([f"/projects/{self.project.id}"], routes)

    def test_u4_demo_is_deterministic_and_covers_cycle_lifecycle_states(self):
        first = seed_demo_database(self.path, today=date(2026, 8, 7), reset=True)
        fingerprint = demo_seed_fingerprint(self.path)
        second = seed_demo_database(self.path, today=date(2026, 8, 7), reset=True)
        services = bootstrap(self.path).services
        summaries = services.cycles.list_summaries.execute()
        statuses = {item.cycle.status for item in summaries}
        active = next(item for item in summaries if item.cycle.status is CycleStatus.ACTIVE)
        self.assertEqual(first.project_count, second.project_count)
        self.assertEqual(fingerprint, demo_seed_fingerprint(self.path))
        self.assertEqual({CycleStatus.DRAFT, CycleStatus.ACTIVE, CycleStatus.COMPLETED, CycleStatus.ARCHIVED}, statuses)
        self.assertEqual(3, active.current_week(date(2026, 8, 7)))
        self.assertEqual(1, active.unplanned_week_count)

    def test_disposable_u4_work_does_not_touch_production_database(self):
        before = _hash(DEFAULT_DATABASE_PATH)
        self.services.cycles.create_cycle.execute("Disposable U4", "Remain isolated", date.today())
        after = _hash(DEFAULT_DATABASE_PATH)
        self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()
