from __future__ import annotations

from datetime import date
from typing import Protocol

from overlord.modules.planning.domain import TaskPlan, TodayGroup


class PlanningRepositoryPort(Protocol):
    def current_plan(self, task_id: int) -> TaskPlan | None: ...
    def assign_plan(
        self,
        task_id: int,
        planned_date: date,
        group: TodayGroup | None,
        position: int | None,
        planned_week_start: date | None = None,
    ) -> TaskPlan: ...
    def plan_history(self, task_id: int) -> list[TaskPlan]: ...
