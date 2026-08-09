from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import date

from overlord.modules.cycles.domain import (
    Cycle,
    CycleStatus,
    WeeklyOutcomeStatus,
    require_cycle_text,
    validate_week_number,
)
from overlord.modules.definition_of_done import require_definition_of_done

from overlord.app.unit_of_work import UnitOfWorkFactory
from overlord.modules.cycles.read_models import CycleDetail, CycleSummary, CycleWizardOptions


@dataclass(frozen=True, slots=True)
class WeeklyOutcomeDraft:
    week_number: int
    title: str
    definition_of_done: str


@dataclass(frozen=True, slots=True)
class CreateCyclePlan:
    uow_factory: UnitOfWorkFactory

    def execute(
        self,
        title: str,
        main_outcome: str,
        start_date: date,
        length_weeks: int,
        *,
        project_ids: tuple[int, ...] = (),
        milestone_ids: tuple[int, ...] = (),
        weekly_outcomes: tuple[WeeklyOutcomeDraft, ...] = (),
        activate: bool = False,
    ) -> Cycle:
        clean_title = require_cycle_text(title, "Cycle title")
        clean_outcome = require_cycle_text(main_outcome, "Main outcome")
        seen_weeks: set[int] = set()
        clean_weekly: list[WeeklyOutcomeDraft] = []
        for item in weekly_outcomes:
            validate_week_number(item.week_number, length_weeks)
            if item.week_number in seen_weeks:
                raise ValueError(f"Week {item.week_number} is repeated.")
            seen_weeks.add(item.week_number)
            clean_weekly.append(
                WeeklyOutcomeDraft(
                    item.week_number,
                    require_cycle_text(item.title, "Weekly outcome"),
                    require_definition_of_done(item.definition_of_done, context="setting a Weekly Outcome"),
                )
            )
        with self.uow_factory() as uow:
            if activate and (active := uow.cycles.active()) is not None:
                raise ValueError(f'"{active.cycle.title}" is already active. Create this Cycle as Draft instead.')
            projects = {project_id: uow.projects.get(project_id) for project_id in dict.fromkeys(project_ids)}
            if any(project is None for project in projects.values()):
                raise ValueError("One or more selected Projects no longer exist.")
            milestones = {item.id: item for item in uow.cycles.list_milestones()}
            for milestone_id in dict.fromkeys(milestone_ids):
                milestone = milestones.get(milestone_id)
                if milestone is None:
                    raise ValueError("One or more selected Milestones no longer exist.")
                if milestone.project_id not in projects:
                    raise ValueError("A selected Milestone requires its Project to be connected.")
            cycle = uow.cycles.create(clean_title, clean_outcome, start_date, length_weeks)
            for project_id in projects:
                uow.cycles.connect_project(cycle.id, project_id)
            for milestone_id in dict.fromkeys(milestone_ids):
                uow.cycles.connect_milestone(cycle.id, milestone_id)
            for item in clean_weekly:
                uow.cycles.set_weekly_outcome(
                    cycle.id,
                    item.week_number,
                    item.title,
                    item.definition_of_done,
                    WeeklyOutcomeStatus.PLANNED.value,
                )
            if activate:
                cycle = uow.cycles.change_status(cycle.id, CycleStatus.ACTIVE)
            return cycle


@dataclass(frozen=True, slots=True)
class CreateCycle:
    uow_factory: UnitOfWorkFactory

    def execute(self, title: str, main_outcome: str, start_date: date, length_weeks: int | None = None) -> Cycle:
        clean_title = require_cycle_text(title, "Cycle title")
        clean_outcome = require_cycle_text(main_outcome, "Main outcome")
        with self.uow_factory() as uow:
            length = length_weeks or uow.settings.get().default_cycle_length
            return uow.cycles.create(clean_title, clean_outcome, start_date, length)


@dataclass(frozen=True, slots=True)
class ChangeCycleStatus:
    uow_factory: UnitOfWorkFactory

    def execute(self, cycle_id: int, status: CycleStatus) -> Cycle:
        with self.uow_factory() as uow:
            if status is CycleStatus.ACTIVE:
                active = uow.cycles.active()
                if active is not None and active.cycle.id != cycle_id:
                    raise ValueError(f'"{active.cycle.title}" is already active. Complete or archive it before activating another Cycle.')
            return uow.cycles.change_status(cycle_id, status)


@dataclass(frozen=True, slots=True)
class ActivateCycle:
    uow_factory: UnitOfWorkFactory

    def execute(self, cycle_id: int) -> Cycle:
        return ChangeCycleStatus(self.uow_factory).execute(cycle_id, CycleStatus.ACTIVE)


@dataclass(frozen=True, slots=True)
class CompleteCycle:
    uow_factory: UnitOfWorkFactory

    def execute(self, cycle_id: int) -> Cycle:
        return ChangeCycleStatus(self.uow_factory).execute(cycle_id, CycleStatus.COMPLETED)


@dataclass(frozen=True, slots=True)
class ArchiveCycle:
    uow_factory: UnitOfWorkFactory

    def execute(self, cycle_id: int) -> Cycle:
        return ChangeCycleStatus(self.uow_factory).execute(cycle_id, CycleStatus.ARCHIVED)


@dataclass(frozen=True, slots=True)
class ConnectCycleProject:
    uow_factory: UnitOfWorkFactory

    def execute(self, cycle_id: int, project_id: int) -> None:
        with self.uow_factory() as uow:
            cycle = uow.cycles.get(cycle_id)
            if not cycle or not uow.projects.get(project_id):
                raise ValueError("Cycle or Project does not exist.")
            if cycle.status is CycleStatus.ARCHIVED:
                raise ValueError("Archived Cycles are read-only until restored.")
            uow.cycles.connect_project(cycle_id, project_id)


@dataclass(frozen=True, slots=True)
class ConnectCycleTask:
    uow_factory: UnitOfWorkFactory

    def execute(self, cycle_id: int, task_id: int) -> None:
        with self.uow_factory() as uow:
            cycle = uow.cycles.get(cycle_id)
            if not cycle or not uow.tasks.get(task_id):
                raise ValueError("Cycle or Task does not exist.")
            if cycle.status is CycleStatus.ARCHIVED:
                raise ValueError("Archived Cycles are read-only until restored.")
            uow.cycles.connect_task(cycle_id, task_id)


@dataclass(frozen=True, slots=True)
class ConnectCycleMilestone:
    uow_factory: UnitOfWorkFactory

    def execute(self, cycle_id: int, project_id: int, title: str, definition_of_done: str):
        clean_title = require_cycle_text(title, "Milestone title")
        clean_dod = require_definition_of_done(definition_of_done, context="creating a Milestone")
        with self.uow_factory() as uow:
            cycle = uow.cycles.get(cycle_id)
            if not cycle:
                raise ValueError(f"Cycle {cycle_id} does not exist.")
            if cycle.status is CycleStatus.ARCHIVED:
                raise ValueError("Archived Cycles are read-only until restored.")
            return uow.cycles.create_milestone(cycle_id, project_id, clean_title, clean_dod)


@dataclass(frozen=True, slots=True)
class SetWeeklyOutcome:
    uow_factory: UnitOfWorkFactory

    def execute(
        self,
        cycle_id: int,
        week_number: int,
        title: str,
        definition_of_done: str,
        status: WeeklyOutcomeStatus = WeeklyOutcomeStatus.PLANNED,
    ):
        with self.uow_factory() as uow:
            cycle = uow.cycles.get(cycle_id)
            if not cycle:
                raise ValueError(f"Cycle {cycle_id} does not exist.")
            if cycle.status is CycleStatus.ARCHIVED:
                raise ValueError("Archived Cycles are read-only until restored.")
            validate_week_number(week_number, cycle.length_weeks)
            return uow.cycles.set_weekly_outcome(
                cycle_id,
                week_number,
                require_cycle_text(title, "Weekly outcome"),
                require_definition_of_done(definition_of_done, context="setting a Weekly Outcome"),
                status.value,
            )


@dataclass(frozen=True, slots=True)
class SearchCyclesQuery:
    uow_factory: UnitOfWorkFactory

    def execute(self, status: CycleStatus | None = None, search: str = "") -> tuple[Cycle, ...]:
        with self.uow_factory(read_only=True) as uow:
            return tuple(uow.cycles.list(status, search))


@dataclass(frozen=True, slots=True)
class ListCycleSummariesQuery:
    uow_factory: UnitOfWorkFactory

    def execute(self, status: CycleStatus | None = None, search: str = "") -> tuple[CycleSummary, ...]:
        with self.uow_factory(read_only=True) as uow:
            return tuple(uow.cycles.summaries(status, search))


@dataclass(frozen=True, slots=True)
class GetCycleWizardOptionsQuery:
    uow_factory: UnitOfWorkFactory

    def execute(self) -> CycleWizardOptions:
        with self.uow_factory(read_only=True) as uow:
            projects = tuple(
                detail
                for project in uow.projects.list()
                if (detail := uow.projects.detail(project.id)) is not None
            )
            active = uow.cycles.active()
            return CycleWizardOptions(
                projects=projects,
                milestones=tuple(uow.cycles.list_milestones()),
                active_cycle=active.cycle if active else None,
            )


@dataclass(frozen=True, slots=True)
class GetCycleDetailQuery:
    uow_factory: UnitOfWorkFactory

    def execute(self, cycle_id: int) -> CycleDetail:
        with self.uow_factory(read_only=True) as uow:
            detail = uow.cycles.detail(cycle_id)
            if not detail:
                raise ValueError(f"Cycle {cycle_id} does not exist.")
            project_summaries = tuple(
                project_detail
                for project in detail.projects
                if (project_detail := uow.projects.detail(project.id)) is not None
            )
            return replace(detail, project_summaries=project_summaries)


@dataclass(frozen=True, slots=True)
class CycleApplication:
    create_cycle: CreateCycle
    create_plan: CreateCyclePlan
    change_status: ChangeCycleStatus
    activate_cycle: ActivateCycle
    complete_cycle: CompleteCycle
    archive_cycle: ArchiveCycle
    connect_project: ConnectCycleProject
    connect_task: ConnectCycleTask
    connect_milestone: ConnectCycleMilestone
    set_weekly_outcome: SetWeeklyOutcome
    search_cycles: SearchCyclesQuery
    list_summaries: ListCycleSummariesQuery
    get_wizard_options: GetCycleWizardOptionsQuery
    get_detail: GetCycleDetailQuery
