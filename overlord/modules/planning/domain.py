from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from enum import StrEnum


class TodayGroup(StrEnum):
    PRIMARY = "primary"
    SECONDARY = "secondary"


@dataclass(frozen=True, slots=True)
class TaskPlan:
    id: int
    task_id: int
    planned_date: date
    planned_week_start: date
    today_group: TodayGroup | None
    position: int | None
    supersedes_plan_id: int | None
    created_at: datetime
    ended_at: datetime | None = None


def validate_slot(group: TodayGroup | None, position: int | None) -> None:
    if (group is None) != (position is None):
        raise ValueError("Today group and position must be provided together.")
    if group is TodayGroup.PRIMARY and position not in range(1, 4):
        raise ValueError("Primary position must be from 1 to 3.")
    if group is TodayGroup.SECONDARY and position not in range(1, 5):
        raise ValueError("Secondary position must be from 1 to 4.")


def week_start(value: date, first_day: int = 0) -> date:
    return value.fromordinal(value.toordinal() - ((value.weekday() - first_day) % 7))
