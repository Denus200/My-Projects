from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from overlord.app.read_models import TaskListItem
from overlord.modules.cycles.domain import Cycle, CycleStatus, Milestone, WeeklyOutcome
from overlord.modules.projects.domain import Project
from overlord.modules.projects.read_models import ProjectDetail


@dataclass(frozen=True, slots=True)
class CycleDetail:
    cycle: Cycle
    projects: tuple[Project, ...]
    milestones: tuple[Milestone, ...]
    tasks: tuple[TaskListItem, ...]
    weekly_outcomes: tuple[WeeklyOutcome, ...]
    project_summaries: tuple[ProjectDetail, ...] = ()


@dataclass(frozen=True, slots=True)
class CycleSummary:
    cycle: Cycle
    achieved_count: int
    partial_count: int
    not_achieved_count: int
    planned_count: int
    projects: tuple[Project, ...]
    next_milestone: Milestone | None

    @property
    def scheduled_outcome_count(self) -> int:
        return self.achieved_count + self.partial_count + self.not_achieved_count + self.planned_count

    @property
    def unplanned_week_count(self) -> int:
        return max(0, self.cycle.length_weeks - self.scheduled_outcome_count)

    def current_week(self, as_of: date) -> int | None:
        if self.cycle.status is not CycleStatus.ACTIVE:
            return None
        if not self.cycle.start_date <= as_of <= self.cycle.end_date:
            return None
        return min(self.cycle.length_weeks, (as_of - self.cycle.start_date).days // 7 + 1)


@dataclass(frozen=True, slots=True)
class CycleWizardOptions:
    projects: tuple[ProjectDetail, ...]
    milestones: tuple[Milestone, ...]
    active_cycle: Cycle | None
