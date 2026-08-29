"""Project domain model and validation."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from enum import StrEnum
import re

from overlord.modules.validation import FieldValidationError


class ProjectStatus(StrEnum):
    ACTIVE = "active"
    ON_HOLD = "on_hold"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class ProjectPlanStatus(StrEnum):
    ACTIVE = "active"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class ProjectStageStatus(StrEnum):
    PLANNED = "planned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    ARCHIVED = "archived"


DEFAULT_PROJECT_COLOR = "#F1ECEF"
PROJECT_COLOR_PATTERN = re.compile(r"^#[0-9A-Fa-f]{6}$")


@dataclass(frozen=True, slots=True)
class Project:
    id: int
    title: str
    status: ProjectStatus
    created_at: datetime
    updated_at: datetime
    description: str | None = None
    stage_label: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    archived_at: datetime | None = None
    color: str = DEFAULT_PROJECT_COLOR
    favorite: bool = False


@dataclass(frozen=True, slots=True)
class ProjectPlan:
    id: int
    project_id: int
    title: str
    status: ProjectPlanStatus
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None = None
    archived_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class ProjectStage:
    id: int
    project_plan_id: int
    project_id: int
    title: str
    status: ProjectStageStatus
    position: int
    created_at: datetime
    updated_at: datetime
    start_date: date | None = None
    end_date: date | None = None
    archived_at: datetime | None = None


def require_project_title(title: str) -> str:
    clean = title.strip()
    if not clean:
        raise FieldValidationError("title", "required", "Project title is required.")
    return clean


def require_project_color(color: str) -> str:
    clean = color.strip().upper()
    if not PROJECT_COLOR_PATTERN.fullmatch(clean):
        raise FieldValidationError("color", "invalid", "Project color must be a six-digit hex color.")
    return clean


def require_project_plan_title(title: str) -> str:
    clean = title.strip()
    if not clean:
        raise FieldValidationError("plan_title", "required", "Project Plan title is required.")
    return clean


def require_project_stage_title(title: str) -> str:
    clean = title.strip()
    if not clean:
        raise FieldValidationError("stage_title", "required", "Stage title is required.")
    return clean
