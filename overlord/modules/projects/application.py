from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

from overlord.modules.projects.domain import (
    DEFAULT_PROJECT_COLOR,
    Project,
    ProjectPlan,
    ProjectPlanStatus,
    ProjectStage,
    ProjectStageStatus,
    ProjectStatus,
    require_project_color,
    require_project_plan_title,
    require_project_stage_title,
    require_project_title,
)
from overlord.modules.tasks.domain import TaskLifecycle, require_task_title, validate_estimate

from overlord.app.unit_of_work import UnitOfWorkFactory
from overlord.modules.projects.read_models import ProjectDetail, ProjectFile, ProjectNote, ProjectWorkspace
from overlord.modules.projects.workspace import ProjectWorkspacePort


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
        color: str = DEFAULT_PROJECT_COLOR,
        status: ProjectStatus = ProjectStatus.ACTIVE,
        favorite: bool = False,
    ) -> Project:
        clean_title = require_project_title(title)
        clean_task = require_task_title(first_task_title) if first_task_title is not None else None
        estimate = validate_estimate(first_task_estimate)
        clean_color = require_project_color(color)
        with self.uow_factory() as uow:
            project = uow.projects.create(
                clean_title,
                description.strip(),
                status,
                color=clean_color,
                favorite=favorite,
            )
            if clean_task:
                chosen_date = first_task_date or date.today()
                uow.tasks.create(
                    project.id,
                    clean_task,
                    TaskLifecycle.PLANNED,
                    schedule_start_date=chosen_date,
                    estimate_minutes=estimate,
                )
            return project


@dataclass(frozen=True, slots=True)
class UpdateProject:
    uow_factory: UnitOfWorkFactory

    def execute(self, project_id: int, **changes: object) -> Project:
        if "title" in changes:
            changes["title"] = require_project_title(str(changes["title"]))
        if "color" in changes:
            changes["color"] = require_project_color(str(changes["color"]))
        if "favorite" in changes:
            changes["favorite"] = bool(changes["favorite"])
        if "status" in changes:
            status = ProjectStatus(changes["status"])
            changes["status"] = status
            if status is ProjectStatus.ARCHIVED:
                changes["archived_at"] = datetime.now()
            elif status is ProjectStatus.COMPLETED:
                changes["completed_at"] = datetime.now()
                changes["archived_at"] = None
            else:
                changes["archived_at"] = None
                if status is ProjectStatus.ACTIVE:
                    changes["completed_at"] = None
        with self.uow_factory() as uow:
            return uow.projects.update(project_id, **changes)


@dataclass(frozen=True, slots=True)
class ArchiveProject:
    uow_factory: UnitOfWorkFactory

    def execute(self, project_id: int) -> Project:
        with self.uow_factory() as uow:
            return uow.projects.update(
                project_id,
                status=ProjectStatus.ARCHIVED,
                archived_at=datetime.now(),
            )


@dataclass(frozen=True, slots=True)
class ListProjectsQuery:
    uow_factory: UnitOfWorkFactory

    def execute(
        self,
        status: ProjectStatus | None = None,
        search: str = "",
        *,
        favorite_only: bool = False,
        sort: str = "recent",
    ) -> tuple[Project, ...]:
        with self.uow_factory(read_only=True) as uow:
            return tuple(uow.projects.list(status, search, favorite_only=favorite_only, sort=sort))


@dataclass(frozen=True, slots=True)
class ListProjectSummariesQuery:
    uow_factory: UnitOfWorkFactory

    def execute(
        self,
        status: ProjectStatus | None = None,
        search: str = "",
        *,
        favorite_only: bool = False,
        sort: str = "recent",
    ) -> tuple[ProjectDetail, ...]:
        with self.uow_factory(read_only=True) as uow:
            projects = uow.projects.list(status, search, favorite_only=favorite_only, sort=sort)
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
class CreateProjectPlan:
    uow_factory: UnitOfWorkFactory

    def execute(self, project_id: int, title: str) -> ProjectPlan:
        clean_title = require_project_plan_title(title)
        with self.uow_factory() as uow:
            if not uow.projects.get(project_id):
                raise ValueError(f"Project {project_id} does not exist.")
            if any(plan.status is ProjectPlanStatus.ACTIVE for plan in uow.projects.list_plans(project_id)):
                raise ValueError("Complete or archive the active Project Plan before creating another.")
            return uow.projects.create_plan(project_id, clean_title)


@dataclass(frozen=True, slots=True)
class ChangeProjectPlanStatus:
    uow_factory: UnitOfWorkFactory

    def execute(self, plan_id: int, status: ProjectPlanStatus) -> ProjectPlan:
        with self.uow_factory() as uow:
            plan = uow.projects.get_plan(plan_id)
            if not plan:
                raise ValueError(f"Project Plan {plan_id} does not exist.")
            return uow.projects.update_plan(plan_id, status)


@dataclass(frozen=True, slots=True)
class CreateProjectStage:
    uow_factory: UnitOfWorkFactory

    def execute(self, project_id: int, plan_id: int, title: str) -> ProjectStage:
        clean_title = require_project_stage_title(title)
        with self.uow_factory() as uow:
            plan = uow.projects.get_plan(plan_id)
            if not plan or plan.project_id != project_id:
                raise ValueError("Stage Project must match its Project Plan.")
            if plan.status is not ProjectPlanStatus.ACTIVE:
                raise ValueError("Stages can only be added to an active Project Plan.")
            return uow.projects.create_stage(plan_id, project_id, clean_title)


@dataclass(frozen=True, slots=True)
class ChangeProjectStageStatus:
    uow_factory: UnitOfWorkFactory

    def execute(self, stage_id: int, status: ProjectStageStatus) -> ProjectStage:
        with self.uow_factory() as uow:
            stage = uow.projects.get_stage(stage_id)
            if not stage:
                raise ValueError(f"Stage {stage_id} does not exist.")
            changes: dict[str, object] = {"status": status}
            if status is ProjectStageStatus.ARCHIVED:
                uow.projects.clear_stage_links(stage_id)
                changes["archived_at"] = datetime.now()
            elif stage.status is ProjectStageStatus.ARCHIVED:
                changes["archived_at"] = None
            return uow.projects.update_stage(stage_id, **changes)


@dataclass(frozen=True, slots=True)
class ListProjectPlansQuery:
    uow_factory: UnitOfWorkFactory

    def execute(self, project_id: int) -> tuple[ProjectPlan, ...]:
        with self.uow_factory(read_only=True) as uow:
            return tuple(uow.projects.list_plans(project_id))


@dataclass(frozen=True, slots=True)
class ListProjectStagesQuery:
    uow_factory: UnitOfWorkFactory

    def execute(self, project_id: int, plan_id: int | None = None) -> tuple[ProjectStage, ...]:
        with self.uow_factory(read_only=True) as uow:
            return tuple(uow.projects.list_stages(project_id, plan_id))


@dataclass(frozen=True, slots=True)
class CreateProjectNote:
    uow_factory: UnitOfWorkFactory
    workspace: ProjectWorkspacePort

    def execute(self, project_id: int, title: str, content: str) -> ProjectNote:
        clean_title = title.strip()
        if not clean_title:
            raise ValueError("Note title is required.")
        relative_path = self.workspace.write_note(project_id, clean_title, content)
        try:
            with self.uow_factory() as uow:
                if not uow.projects.get(project_id):
                    raise ValueError(f"Project {project_id} does not exist.")
                note = uow.projects.create_note(project_id, clean_title, relative_path)
        except Exception:
            self.workspace.remove(project_id, relative_path)
            raise
        return ProjectNote(note.id, note.project_id, note.title, note.relative_path, content)


@dataclass(frozen=True, slots=True)
class AddProjectFile:
    uow_factory: UnitOfWorkFactory
    workspace: ProjectWorkspacePort

    def execute(self, project_id: int, source: str | Path) -> ProjectFile:
        source_path = Path(source)
        relative_path, size_bytes = self.workspace.import_file(project_id, source_path)
        try:
            with self.uow_factory() as uow:
                if not uow.projects.get(project_id):
                    raise ValueError(f"Project {project_id} does not exist.")
                return uow.projects.create_file(
                    project_id,
                    source_path.name,
                    relative_path,
                    size_bytes,
                )
        except Exception:
            self.workspace.remove(project_id, relative_path)
            raise


@dataclass(frozen=True, slots=True)
class GetProjectWorkspaceQuery:
    uow_factory: UnitOfWorkFactory
    workspace: ProjectWorkspacePort

    def execute(self, project_id: int) -> ProjectWorkspace:
        with self.uow_factory(read_only=True) as uow:
            if not uow.projects.get(project_id):
                raise ValueError(f"Project {project_id} does not exist.")
            notes = tuple(
                ProjectNote(
                    note.id,
                    note.project_id,
                    note.title,
                    note.relative_path,
                    self.workspace.read_text(project_id, note.relative_path),
                )
                for note in uow.projects.list_notes(project_id)
            )
            return ProjectWorkspace(notes, tuple(uow.projects.list_files(project_id)))


@dataclass(frozen=True, slots=True)
class ProjectApplication:
    create_project: CreateProject
    update_project: UpdateProject
    archive_project: ArchiveProject
    list_projects: ListProjectsQuery
    list_summaries: ListProjectSummariesQuery
    get_detail: GetProjectDetailQuery
    create_plan: CreateProjectPlan
    change_plan_status: ChangeProjectPlanStatus
    list_plans: ListProjectPlansQuery
    create_stage: CreateProjectStage
    change_stage_status: ChangeProjectStageStatus
    list_stages: ListProjectStagesQuery
    create_note: CreateProjectNote
    add_file: AddProjectFile
    get_workspace: GetProjectWorkspaceQuery
