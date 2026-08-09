from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from overlord.modules.planning.domain import week_start
from overlord.modules.projects.domain import Project, ProjectStatus, require_project_title
from overlord.modules.tasks.domain import TaskLifecycle, require_task_title, validate_estimate

from overlord.app.unit_of_work import UnitOfWorkFactory
from overlord.modules.projects.read_models import ProjectDetail


@dataclass(frozen=True, slots=True)
class CreateProject:
    uow_factory: UnitOfWorkFactory

    def execute(
        self,
        title: str,
        description: str = "",
        *,
        first_task_title: str | None = None,
        first_task_date: date | None = None,
        first_task_estimate: int | None = None,
    ) -> Project:
        clean_title = require_project_title(title)
        clean_task = require_task_title(first_task_title) if first_task_title is not None else None
        estimate = validate_estimate(first_task_estimate)
        with self.uow_factory() as uow:
            project = uow.projects.create(clean_title, description.strip())
            if clean_task:
                task = uow.tasks.create(
                    project.id,
                    clean_task,
                    TaskLifecycle.PLANNED,
                    planned_date=first_task_date or date.today(),
                    estimate_minutes=estimate,
                )
                chosen_date = first_task_date or date.today()
                first_day = 6 if uow.settings.get().first_day_of_week == "sunday" else 0
                uow.planning.assign_plan(task.id, chosen_date, None, None, week_start(chosen_date, first_day))
            return project


@dataclass(frozen=True, slots=True)
class UpdateProject:
    uow_factory: UnitOfWorkFactory

    def execute(self, project_id: int, **changes: object) -> Project:
        if "title" in changes:
            changes["title"] = require_project_title(str(changes["title"]))
        with self.uow_factory() as uow:
            return uow.projects.update(project_id, **changes)


@dataclass(frozen=True, slots=True)
class ArchiveProject:
    uow_factory: UnitOfWorkFactory

    def execute(self, project_id: int) -> Project:
        with self.uow_factory() as uow:
            return uow.projects.update(project_id, status=ProjectStatus.ARCHIVED)


@dataclass(frozen=True, slots=True)
class ListProjectsQuery:
    uow_factory: UnitOfWorkFactory

    def execute(self, status: ProjectStatus | None = None, search: str = "") -> tuple[Project, ...]:
        with self.uow_factory(read_only=True) as uow:
            return tuple(uow.projects.list(status, search))


@dataclass(frozen=True, slots=True)
class ListProjectSummariesQuery:
    uow_factory: UnitOfWorkFactory

    def execute(self, status: ProjectStatus | None = None, search: str = "") -> tuple[ProjectDetail, ...]:
        with self.uow_factory(read_only=True) as uow:
            projects = uow.projects.list(status, search)
            return tuple(
                detail
                for project in projects
                if (detail := uow.projects.detail(project.id)) is not None
            )


@dataclass(frozen=True, slots=True)
class GetProjectDetailQuery:
    uow_factory: UnitOfWorkFactory

    def execute(self, project_id: int) -> ProjectDetail:
        with self.uow_factory(read_only=True) as uow:
            detail = uow.projects.detail(project_id)
            if not detail:
                raise ValueError(f"Project {project_id} does not exist.")
            return detail


@dataclass(frozen=True, slots=True)
class ProjectApplication:
    create_project: CreateProject
    update_project: UpdateProject
    archive_project: ArchiveProject
    list_projects: ListProjectsQuery
    list_summaries: ListProjectSummariesQuery
    get_detail: GetProjectDetailQuery
