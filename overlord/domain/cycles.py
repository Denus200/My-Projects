from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from enum import StrEnum


class CycleStatus(StrEnum):
    DRAFT = "draft"
    ACTIVE = "active"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class MilestoneStatus(StrEnum):
    PLANNED = "planned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class WeeklyOutcomeStatus(StrEnum):
    PLANNED = "planned"
    ACHIEVED = "achieved"
    PARTIAL = "partial"
    NOT_ACHIEVED = "not_achieved"


@dataclass(frozen=True, slots=True)
class Cycle:
    id: int
    title: str
    main_outcome: str
    start_date: date
    length_weeks: int
    end_date: date
    status: CycleStatus
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None = None
    archived_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class Milestone:
    id: int
    project_id: int
    title: str
    definition_of_done: str
    status: MilestoneStatus
    position: int
    created_at: datetime
    updated_at: datetime
    target_date: date | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class WeeklyOutcome:
    id: int
    cycle_id: int
    week_number: int
    title: str
    definition_of_done: str
    status: WeeklyOutcomeStatus
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None = None


def cycle_end_date(start: date, length_weeks: int) -> date:
    if not 1 <= length_weeks <= 52:
        raise ValueError("Cycle length must be between 1 and 52 weeks.")
    return start + timedelta(days=length_weeks * 7 - 1)


def require_cycle_text(value: str, label: str) -> str:
    clean = value.strip()
    if not clean:
        raise ValueError(f"{label} is required.")
    return clean


def validate_week_number(week_number: int, length_weeks: int) -> int:
    if not 1 <= week_number <= length_weeks:
        raise ValueError(f"Week number must be between 1 and {length_weeks}.")
    return week_number
