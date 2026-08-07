from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

from overlord.domain.projects import Project, ProjectStatus
from overlord.domain.tasks import TaskLifecycle, TodayGroup, require_definition_of_done, week_start

from .common import TaskListItem, UnitOfWorkFactory


@dataclass(frozen=True, slots=True)
class PlanningCandidate:
    item: TaskListItem
    in_current_week: bool
    is_overdue: bool
    in_active_cycle: bool


@dataclass(frozen=True, slots=True)
class DailyPlanningReadModel:
    day: date
    primary: tuple[TaskListItem, ...]
    secondary: tuple[TaskListItem, ...]
    candidates: tuple[PlanningCandidate, ...]
    projects: tuple[Project, ...]


@dataclass(frozen=True, slots=True)
class GetDailyPlanningQuery:
    uow_factory: UnitOfWorkFactory

    def execute(self, day: date) -> DailyPlanningReadModel:
        with self.uow_factory(read_only=True) as uow:
            settings = uow.settings.get()
            first_day = 6 if settings.first_day_of_week == "sunday" else 0
            start = week_start(day, first_day)
            end = start + timedelta(days=6)
            all_tasks = tuple(uow.tasks.list())
            active_cycle = uow.cycles.active()
            active_cycle_ids = {
                item.task.id for item in active_cycle.tasks
            } if active_cycle else set()

            assigned = tuple(
                item for item in all_tasks
                if item.current_plan and item.current_plan.planned_date == day
            )
            primary = tuple(
                item for item in assigned
                if item.current_plan and item.current_plan.today_group is TodayGroup.PRIMARY
            )
            secondary = tuple(
                item for item in assigned
                if item.current_plan and item.current_plan.today_group is TodayGroup.SECONDARY
            )

            candidates: list[PlanningCandidate] = []
            assigned_ids = {item.task.id for item in primary + secondary}
            for item in all_tasks:
                task = item.task
                if task.archived_at is not None or task.lifecycle_status is TaskLifecycle.CANCELLED:
                    continue
                if task.lifecycle_status is TaskLifecycle.COMPLETED and task.id not in assigned_ids:
                    continue
                plan = item.current_plan
                candidates.append(
                    PlanningCandidate(
                        item=item,
                        in_current_week=bool(plan and start <= plan.planned_date <= end),
                        is_overdue=bool(
                            plan
                            and plan.planned_date < day
                            and task.lifecycle_status is not TaskLifecycle.COMPLETED
                        ),
                        in_active_cycle=task.id in active_cycle_ids,
                    )
                )

            candidates.sort(
                key=lambda candidate: (
                    0 if candidate.item.task.id in assigned_ids else 1,
                    0 if candidate.is_overdue else 1,
                    candidate.item.current_plan.planned_date if candidate.item.current_plan else date.max,
                    (candidate.item.project_title or "").lower(),
                    candidate.item.task.title.lower(),
                )
            )
            projects = tuple(uow.projects.list(ProjectStatus.ACTIVE))
        return DailyPlanningReadModel(day, primary, secondary, tuple(candidates), projects)


@dataclass(frozen=True, slots=True)
class SaveDailyPlan:
    uow_factory: UnitOfWorkFactory

    def execute(
        self,
        day: date,
        primary_task_ids: tuple[int, ...],
        secondary_task_ids: tuple[int, ...],
    ) -> None:
        if len(primary_task_ids) > 3:
            raise ValueError("A daily plan can contain at most 3 Primary Tasks.")
        if len(secondary_task_ids) > 4:
            raise ValueError("A daily plan can contain at most 4 Secondary Tasks.")
        desired_ids = primary_task_ids + secondary_task_ids
        if len(set(desired_ids)) != len(desired_ids):
            raise ValueError("A Task can appear only once in a daily plan.")

        with self.uow_factory() as uow:
            task_items = {item.task.id: item for item in uow.tasks.list()}
            missing = [task_id for task_id in desired_ids if task_id not in task_items]
            if missing:
                raise ValueError(f"Task {missing[0]} does not exist.")
            for task_id in primary_task_ids:
                require_definition_of_done(
                    task_items[task_id].task.definition_of_done,
                    context="assigning a Primary slot",
                )

            settings = uow.settings.get()
            first_day = 6 if settings.first_day_of_week == "sunday" else 0
            selected_week_start = week_start(day, first_day)
            current_assigned = [
                item for item in uow.tasks.list(planned_date=day)
                if item.current_plan and item.current_plan.today_group is not None
            ]

            # Clear occupied slots first so swaps and complete reorders remain atomic.
            for item in current_assigned:
                uow.tasks.assign_plan(
                    item.task.id,
                    day,
                    None,
                    None,
                    selected_week_start,
                )
            for position, task_id in enumerate(primary_task_ids, start=1):
                uow.tasks.assign_plan(
                    task_id,
                    day,
                    TodayGroup.PRIMARY,
                    position,
                    selected_week_start,
                )
            for position, task_id in enumerate(secondary_task_ids, start=1):
                uow.tasks.assign_plan(
                    task_id,
                    day,
                    TodayGroup.SECONDARY,
                    position,
                    selected_week_start,
                )


@dataclass(frozen=True, slots=True)
class DailyPlanningApplication:
    get_plan: GetDailyPlanningQuery
    save_plan: SaveDailyPlan
