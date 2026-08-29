from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from overlord.modules.cycles.application import (
    ActivateCycle,
    ArchiveCycle,
    ChangeCycleStatus,
    CompleteCycle,
    ConnectCycleMilestone,
    ConnectCycleProject,
    ConnectCycleTask,
    CreateCycle,
    CreateCyclePlan,
    CycleApplication,
    GetCycleWizardOptionsQuery,
    GetCycleDetailQuery,
    ListCycleSummariesQuery,
    SearchCyclesQuery,
    SetWeeklyOutcome,
)
from overlord.app.services import ApplicationServices
from overlord.modules.dashboard.application import GetDashboardQuery
from overlord.modules.weather.application import WeatherService
from overlord.modules.projects.application import (
    AddProjectFile,
    ArchiveProject,
    ChangeProjectPlanStatus,
    ChangeProjectStageStatus,
    CreateProjectPlan,
    CreateProjectStage,
    CreateProjectNote,
    CreateProject,
    GetProjectDetailQuery,
    GetProjectWorkspaceQuery,
    ListProjectSummariesQuery,
    ListProjectPlansQuery,
    ListProjectStagesQuery,
    ListProjectsQuery,
    ProjectApplication,
    UpdateProject,
)
from overlord.modules.settings.application import GetSettingsQuery, SettingsApplication, UpdateSettings
from overlord.modules.tasks.application import (
    ChangeTaskLifecycle,
    CompleteTask,
    CreateTask,
    DeleteTask,
    GetTaskEditorQuery,
    ListTasksQuery,
    MoveTaskToBoardColumn,
    OpenBlocker,
    ResolveBlocker,
    ReorderTasksForDay,
    TaskApplication,
    ToggleTaskCompletionForDay,
    UpdateTask,
    UpdateTaskDetails,
)
from overlord.infrastructure.logging import configure_logging
from overlord.infrastructure.local_project_workspace import LocalProjectWorkspace
from overlord.infrastructure.weather.cache import JsonWeatherCache
from overlord.infrastructure.weather.config import MEREFA_WEATHER_CONFIG
from overlord.infrastructure.weather.open_meteo import OpenMeteoWeatherProvider
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
    project_workspace = LocalProjectWorkspace(path.parent / "project-workspaces")
    weather_cache = path.with_name(f"{path.stem}-weather-cache.json")
    projects = ProjectApplication(
        CreateProject(uow), UpdateProject(uow), ArchiveProject(uow),
        ListProjectsQuery(uow), ListProjectSummariesQuery(uow), GetProjectDetailQuery(uow),
        CreateProjectPlan(uow), ChangeProjectPlanStatus(uow), ListProjectPlansQuery(uow),
        CreateProjectStage(uow), ChangeProjectStageStatus(uow), ListProjectStagesQuery(uow),
        CreateProjectNote(uow, project_workspace), AddProjectFile(uow, project_workspace),
        GetProjectWorkspaceQuery(uow, project_workspace),
    )
    tasks = TaskApplication(
        CreateTask(uow), UpdateTask(uow), UpdateTaskDetails(uow), DeleteTask(uow), ChangeTaskLifecycle(uow),
        CompleteTask(uow), ReorderTasksForDay(uow), ToggleTaskCompletionForDay(uow),
        MoveTaskToBoardColumn(uow), OpenBlocker(uow), ResolveBlocker(uow), ListTasksQuery(uow),
        GetTaskEditorQuery(uow),
    )
    settings = SettingsApplication(GetSettingsQuery(uow), UpdateSettings(uow))
    cycles = CycleApplication(
        CreateCycle(uow), CreateCyclePlan(uow), ChangeCycleStatus(uow), ActivateCycle(uow), CompleteCycle(uow),
        ArchiveCycle(uow), ConnectCycleProject(uow),
        ConnectCycleTask(uow), ConnectCycleMilestone(uow), SetWeeklyOutcome(uow),
        SearchCyclesQuery(uow), ListCycleSummariesQuery(uow), GetCycleWizardOptionsQuery(uow), GetCycleDetailQuery(uow),
    )
    return BootstrapResult(
        ApplicationServices(
            projects,
            tasks,
            settings,
            GetDashboardQuery(uow),
            cycles,
            WeatherService(
                OpenMeteoWeatherProvider(MEREFA_WEATHER_CONFIG),
                JsonWeatherCache(weather_cache),
                location_name=MEREFA_WEATHER_CONFIG.location_name,
            ),
        ),
        migrations,
    )
