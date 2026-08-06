from dataclasses import dataclass


@dataclass(frozen=True)
class Project:
    id: int
    title: str
    description: str
    status: str
    created_at: str
    updated_at: str


@dataclass(frozen=True)
class Task:
    id: int
    project_id: int
    project_title: str
    title: str
    description: str
    scheduled_date: str
    planned_minutes: int | None
    status: str
    comment: str
    created_at: str
    updated_at: str
