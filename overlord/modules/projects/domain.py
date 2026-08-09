"""Project domain model and validation."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class ProjectStatus(StrEnum):
    ACTIVE = "active"
    ON_HOLD = "on_hold"
    COMPLETED = "completed"
    ARCHIVED = "archived"


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


def require_project_title(title: str) -> str:
    clean = title.strip()
    if not clean:
        raise ValueError("Project title is required.")
    return clean
