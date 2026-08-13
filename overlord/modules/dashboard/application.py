from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta

from overlord.modules.cycles.domain import MilestoneStatus
from overlord.modules.dashboard.read_models import (
    AttentionItem,
    CurrentCycleReadModel,
    DashboardReadModel,
    WeeklyBar,
    execution_score,
)
from overlord.app.read_models import TaskListItem
from overlord.app.unit_of_work import UnitOfWorkFactory
from overlord.modules.tasks.application import order_tasks_for_day
from overlord.modules.tasks.domain import TaskLifecycle, is_scheduled_for_day


def _week_start(value: date, first_day: int = 0) -> date:
    return value.fromordinal(value.toordinal() - ((value.weekday() - first_day) % 7))


@dataclass(frozen=True, slots=True)
class GetDashboardQuery:
    uow_factory: UnitOfWorkFactory

    def execute(self, day: date | None = None) -> DashboardReadModel:
        selected_day = day or date.today()
        now = datetime.now()
        with self.uow_factory(read_only=True) as uow:
            settings = uow.settings.get()
            start = _week_start(selected_day, 6 if settings.first_day_of_week == "sunday" else 0)
            all_tasks = uow.tasks.list()
            selected_days = (
                selected_day - timedelta(days=1),
                selected_day,
                selected_day + timedelta(days=1),
            )
            day_tasks = tuple(
                order_tasks_for_day(
                    tuple(
                        item
                        for item in all_tasks
                        if item.task.lifecycle_status is not TaskLifecycle.CANCELLED
                        and is_scheduled_for_day(item.task, current_day)
                    ),
                    uow.tasks.day_positions(current_day),
                )
                for current_day in selected_days
            )
            weekly_bars = tuple(WeeklyBar(*values) for values in uow.dashboard.weekly_counts(start))
            originally_planned, completed = uow.dashboard.execution_counts(start)
            attention: list[AttentionItem] = []
            for item in all_tasks:
                task = item.task
                if task.lifecycle_status in {TaskLifecycle.COMPLETED, TaskLifecycle.CANCELLED}:
                    continue
                reasons: list[str] = []
                if item.open_blockers:
                    reasons.append("Open blocker")
                if task.lifecycle_status is TaskLifecycle.IN_PROGRESS and task.updated_at <= now - timedelta(days=7):
                    reasons.append("No update for seven days")
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
            day=selected_day,
            yesterday_tasks=day_tasks[0],
            today_tasks=day_tasks[1],
            tomorrow_tasks=day_tasks[2],
            weekly_bars=weekly_bars,
            execution_score=execution_score(originally_planned, completed),
            current_cycle=cycle_model,
            attention=tuple(attention),
            outcome_label=outcome_label,
        )
