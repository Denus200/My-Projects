"""Application commands, queries, ports, and immutable read models."""

from dataclasses import dataclass

from .cycles import CycleApplication
from .dashboard import GetDashboardQuery
from .projects import ProjectApplication
from .settings import SettingsApplication
from .tasks import TaskApplication


@dataclass(frozen=True, slots=True)
class ApplicationServices:
    projects: ProjectApplication
    tasks: TaskApplication
    settings: SettingsApplication
    dashboard: GetDashboardQuery
    cycles: CycleApplication
