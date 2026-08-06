from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from overlord.application.cycles import (
    ActivateCycle,
    ArchiveCycle,
    ChangeCycleStatus,
    CompleteCycle,
    ConnectCycleMilestone,
    ConnectCycleProject,
    ConnectCycleTask,
    CreateCycle,
    CycleApplication,
    GetCycleDetailQuery,
    SearchCyclesQuery,
    SetWeeklyOutcome,
)
from overlord.application import ApplicationServices
from overlord.application.dashboard import GetDashboardQuery
from overlord.application.projects import (
    ArchiveProject,
    CreateProject,
    GetProjectDetailQuery,
    ListProjectsQuery,
    ProjectApplication,
    UpdateProject,
)
from overlord.application.settings import GetSettingsQuery, SettingsApplication, UpdateSettings
from overlord.application.tasks import (
    AssignTaskPlan,
    ChangeTaskLifecycle,
    CompleteTask,
    CreateTask,
    GetTaskEditorQuery,
    ListTasksQuery,
    OpenBlocker,
    ResolveBlocker,
    TaskApplication,
    UpdateTask,
)
from overlord.infrastructure.logging import configure_logging
from overlord.infrastructure.sqlite.connection import ConnectionFactory
from overlord.infrastructure.sqlite.migrations import MigrationResult, MigrationRunner
from overlord.infrastructure.sqlite.unit_of_work import SqliteUnitOfWorkFactory


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATABASE_PATH = REPOSITORY_ROOT / "data" / "overlord.db"


@dataclass(frozen=True, slots=True)
class BootstrapResult:
    services: ApplicationServices
    migrations: MigrationResult


def bootstrap(database_path: str | Path = DEFAULT_DATABASE_PATH) -> BootstrapResult:
    path = Path(database_path).resolve()
    logger = configure_logging(path.parent / "logs")
    factory = ConnectionFactory(path)
    migrations = MigrationRunner(factory).migrate()
    logger.info(
        "migration_complete from_version=%s to_version=%s applied=%s",
        migrations.from_version,
        migrations.to_version,
        list(migrations.applied),
    )
    uow = SqliteUnitOfWorkFactory(factory)
    projects = ProjectApplication(
        CreateProject(uow), UpdateProject(uow), ArchiveProject(uow),
        ListProjectsQuery(uow), GetProjectDetailQuery(uow),
    )
    tasks = TaskApplication(
        CreateTask(uow), UpdateTask(uow), ChangeTaskLifecycle(uow), AssignTaskPlan(uow),
        CompleteTask(uow), OpenBlocker(uow), ResolveBlocker(uow), ListTasksQuery(uow),
        GetTaskEditorQuery(uow),
    )
    settings = SettingsApplication(GetSettingsQuery(uow), UpdateSettings(uow))
    cycles = CycleApplication(
        CreateCycle(uow), ChangeCycleStatus(uow), ActivateCycle(uow), CompleteCycle(uow),
        ArchiveCycle(uow), ConnectCycleProject(uow),
        ConnectCycleTask(uow), ConnectCycleMilestone(uow), SetWeeklyOutcome(uow),
        SearchCyclesQuery(uow), GetCycleDetailQuery(uow),
    )
    return BootstrapResult(
        ApplicationServices(projects, tasks, settings, GetDashboardQuery(uow), cycles),
        migrations,
    )
    CompleteCycle,
