from __future__ import annotations

import sqlite3
from datetime import date, datetime, time

from overlord.modules.blockers.domain import Blocker, BlockerType
from overlord.modules.cycles.domain import (
    Cycle,
    CycleStatus,
    Milestone,
    MilestoneStatus,
    WeeklyOutcome,
    WeeklyOutcomeStatus,
)
from overlord.modules.projects.domain import Project, ProjectStatus
from overlord.modules.tasks.domain import Task, TaskLifecycle


def _datetime(value: str | None) -> datetime | None:
    return datetime.fromisoformat(value) if value else None


def _date(value: str | None) -> date | None:
    return date.fromisoformat(value) if value else None


def _time(value: str | None) -> time | None:
    return time.fromisoformat(value) if value else None


def _boolean(value: int | None) -> bool | None:
    return None if value is None else bool(value)


def _project(row: sqlite3.Row) -> Project:
    return Project(
        id=row["id"],
        title=row["title"],
        description=row["description"] or None,
        status=ProjectStatus(row["status"]),
        created_at=_datetime(row["created_at"]),
        updated_at=_datetime(row["updated_at"]),
        stage_label=row["stage_label"],
        started_at=_datetime(row["started_at"]),
        completed_at=_datetime(row["completed_at"]),
        archived_at=_datetime(row["archived_at"]),
    )


def _task(row: sqlite3.Row) -> Task:
    lifecycle = row["lifecycle_status"]
    return Task(
        id=row["id"],
        project_id=row["project_id"],
        title=row["title"],
        description=row["description"] or None,
        lifecycle_status=TaskLifecycle(lifecycle) if lifecycle else None,
        legacy_status=row["status"],
        definition_of_done=row["definition_of_done"],
        next_action=row["next_action"],
        importance=_boolean(row["importance"]),
        urgency=_boolean(row["urgency"]),
        estimate_minutes=row["planned_minutes"],
        schedule_start_date=_date(row["schedule_start_date"]),
        schedule_start_time=_time(row["schedule_start_time"]),
        schedule_end_date=_date(row["schedule_end_date"]),
        schedule_end_time=_time(row["schedule_end_time"]),
        deadline_at=_datetime(row["deadline_at"]),
        started_at=_datetime(row["started_at"]),
        completed_at=_datetime(row["completed_at"]),
        archived_at=_datetime(row["archived_at"]),
        milestone_id=row["milestone_id"],
        created_at=_datetime(row["created_at"]),
        updated_at=_datetime(row["updated_at"]),
    )


def _blocker(row: sqlite3.Row) -> Blocker:
    return Blocker(
        id=row["id"],
        task_id=row["task_id"],
        type=BlockerType(row["type"]),
        description=row["description"],
        created_at=_datetime(row["created_at"]),
        resolved_at=_datetime(row["resolved_at"]),
        resolution=row["resolution"],
    )


def _cycle(row: sqlite3.Row) -> Cycle:
    return Cycle(
        id=row["id"],
        title=row["title"],
        main_outcome=row["main_outcome"],
        start_date=_date(row["start_date"]),
        length_weeks=row["length_weeks"],
        end_date=_date(row["end_date"]),
        status=CycleStatus(row["status"]),
        created_at=_datetime(row["created_at"]),
        updated_at=_datetime(row["updated_at"]),
        completed_at=_datetime(row["completed_at"]),
        archived_at=_datetime(row["archived_at"]),
    )


def _milestone(row: sqlite3.Row) -> Milestone:
    return Milestone(
        id=row["id"],
        project_id=row["project_id"],
        title=row["title"],
        definition_of_done=row["definition_of_done"],
        status=MilestoneStatus(row["status"]),
        target_date=_date(row["target_date"]),
        position=row["position"],
        started_at=_datetime(row["started_at"]),
        completed_at=_datetime(row["completed_at"]),
        created_at=_datetime(row["created_at"]),
        updated_at=_datetime(row["updated_at"]),
    )


def _outcome(row: sqlite3.Row) -> WeeklyOutcome:
    return WeeklyOutcome(
        id=row["id"],
        cycle_id=row["cycle_id"],
        week_number=row["week_number"],
        title=row["title"],
        definition_of_done=row["definition_of_done"],
        status=WeeklyOutcomeStatus(row["status"]),
        completed_at=_datetime(row["completed_at"]),
        created_at=_datetime(row["created_at"]),
        updated_at=_datetime(row["updated_at"]),
    )
