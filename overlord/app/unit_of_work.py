from __future__ import annotations

from typing import ContextManager, Protocol

from overlord.modules.blockers.repository import BlockerRepositoryPort
from overlord.modules.cycles.repository import CycleRepositoryPort
from overlord.modules.dashboard.repository import DashboardRepositoryPort
from overlord.modules.projects.repository import ProjectRepositoryPort
from overlord.modules.settings.repository import SettingsRepositoryPort
from overlord.modules.tasks.repository import TaskRepositoryPort


class UnitOfWork(Protocol):
    projects: ProjectRepositoryPort
    tasks: TaskRepositoryPort
    blockers: BlockerRepositoryPort
    cycles: CycleRepositoryPort
    settings: SettingsRepositoryPort
    dashboard: DashboardRepositoryPort


class UnitOfWorkFactory(Protocol):
    def __call__(self, *, read_only: bool = False) -> ContextManager[UnitOfWork]: ...
