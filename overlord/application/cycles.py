from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from overlord.domain.cycles import (
    Cycle,
    CycleStatus,
    WeeklyOutcomeStatus,
    require_cycle_text,
    validate_week_number,
)
from overlord.domain.tasks import require_definition_of_done

from .common import CycleDetail, UnitOfWorkFactory


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
class GetCycleDetailQuery:
    uow_factory: UnitOfWorkFactory

    def execute(self, cycle_id: int) -> CycleDetail:
        with self.uow_factory(read_only=True) as uow:
            detail = uow.cycles.detail(cycle_id)
            if not detail:
                raise ValueError(f"Cycle {cycle_id} does not exist.")
            return detail


@dataclass(frozen=True, slots=True)
class CycleApplication:
    create_cycle: CreateCycle
    change_status: ChangeCycleStatus
    activate_cycle: ActivateCycle
    complete_cycle: CompleteCycle
    archive_cycle: ArchiveCycle
    connect_project: ConnectCycleProject
    connect_task: ConnectCycleTask
    connect_milestone: ConnectCycleMilestone
    set_weekly_outcome: SetWeeklyOutcome
    search_cycles: SearchCyclesQuery
    get_detail: GetCycleDetailQuery
