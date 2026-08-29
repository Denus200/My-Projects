"""Application service composition."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from overlord.modules.cycles.application import CycleApplication
    from overlord.modules.dashboard.application import GetDashboardQuery
    from overlord.modules.projects.application import ProjectApplication
    from overlord.modules.settings.application import SettingsApplication
    from overlord.modules.tasks.application import TaskApplication
    from overlord.modules.weather.application import WeatherService


@dataclass(frozen=True, slots=True)
class ApplicationServices:
    projects: ProjectApplication
    tasks: TaskApplication
    settings: SettingsApplication
    dashboard: GetDashboardQuery
    cycles: CycleApplication
    weather: WeatherService
