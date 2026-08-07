from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta

from overlord.domain.cycles import MilestoneStatus
from overlord.domain.planning import execution_score
from overlord.domain.tasks import TaskLifecycle, TodayGroup, week_start

from .common import TaskListItem, UnitOfWorkFactory
from .tasks import AssignTaskPlan, CompleteTask


@dataclass(frozen=True, slots=True)
class WeeklyBar:
    day: date
    planned: int
    completed: int


@dataclass(frozen=True, slots=True)
class AttentionItem:
    task_id: int
    title: str
    project_title: str | None
    reasons: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class CurrentCycleReadModel:
    cycle_id: int
    title: str
    main_outcome: str
    week_number: int
    length_weeks: int
    next_milestone: str | None
    progress: float
    weekly_outcome: str
    days_remaining: int


@dataclass(frozen=True, slots=True)
class DashboardReadModel:
    day: date
    primary: tuple[TaskListItem, ...]
    secondary: tuple[TaskListItem, ...]
    weekly_bars: tuple[WeeklyBar, ...]
    execution_score: float | None
    current_cycle: CurrentCycleReadModel | None
    attention: tuple[AttentionItem, ...]
    actual_time_label: str = "Not tracked yet"
    outcome_label: str = "Not set"


@dataclass(frozen=True, slots=True)
class GetDashboardQuery:
    uow_factory: UnitOfWorkFactory

    def execute(self, day: date | None = None) -> DashboardReadModel:
        selected_day = day or date.today()
        now = datetime.now()
        with self.uow_factory(read_only=True) as uow:
            settings = uow.settings.get()
            start = week_start(selected_day, 6 if settings.first_day_of_week == "sunday" else 0)
            today = uow.tasks.list(planned_date=selected_day)
            primary = tuple(item for item in today if item.current_plan and item.current_plan.today_group is TodayGroup.PRIMARY)
            secondary = tuple(item for item in today if item.current_plan and item.current_plan.today_group is TodayGroup.SECONDARY)
            weekly_bars = tuple(WeeklyBar(*values) for values in uow.tasks.weekly_counts(start))
            originally_planned, completed = uow.tasks.execution_counts(start)
            all_tasks = uow.tasks.list()
            attention: list[AttentionItem] = []
            for item in all_tasks:
                task = item.task
                if task.lifecycle_status in {TaskLifecycle.COMPLETED, TaskLifecycle.CANCELLED}:
                    continue
                reasons: list[str] = []
                if item.open_blockers:
                    reasons.append("Open blocker")
                if item.carry_over_count >= 2:
                    reasons.append(f"Carried over {item.carry_over_count} times")
                if task.lifecycle_status is TaskLifecycle.IN_PROGRESS and task.updated_at <= now - timedelta(days=7):
                    reasons.append("No update for seven days")
                if (
                    item.current_plan
                    and item.current_plan.today_group is TodayGroup.PRIMARY
                    and task.lifecycle_status is TaskLifecycle.IN_PROGRESS
                    and not task.next_action
                ):
                    reasons.append("Primary task needs a next action")
                if task.lifecycle_status is None:
                    reasons.append("Legacy status requires review")
                if reasons:
                    attention.append(AttentionItem(task.id, task.title, item.project_title, tuple(reasons)))
            active = uow.cycles.active()
            cycle_model = None
            outcome_label = "Not set"
            if active:
                cycle = active.cycle
                week_number = max(1, min(cycle.length_weeks, (selected_day - cycle.start_date).days // 7 + 1))
                next_milestone = next(
                    (m.title for m in active.milestones if m.status not in {MilestoneStatus.COMPLETED, MilestoneStatus.CANCELLED}),
                    None,
                )
                current_outcome = next((o for o in active.weekly_outcomes if o.week_number == week_number), None)
                achieved = sum(1 for o in active.weekly_outcomes if o.status.value == "achieved")
                outcome_label = current_outcome.status.value.replace("_", " ").title() if current_outcome else "Not set"
                cycle_model = CurrentCycleReadModel(
                    cycle.id,
                    cycle.title,
                    cycle.main_outcome,
                    week_number,
                    cycle.length_weeks,
                    next_milestone,
                    achieved / cycle.length_weeks,
                    outcome_label,
                    max(0, (cycle.end_date - selected_day).days),
                )
        return DashboardReadModel(
            selected_day,
            primary,
            secondary,
            weekly_bars,
            execution_score(originally_planned, completed),
            cycle_model,
            tuple(attention),
            outcome_label=outcome_label,
        )


CompleteDashboardTask = CompleteTask
ReorderTodaySlots = AssignTaskPlan
