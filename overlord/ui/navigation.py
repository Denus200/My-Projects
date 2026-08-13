from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from overlord.ui.design_system.icons import IconName
from .strings import ui_text


class AppRoute(StrEnum):
    DASHBOARD = "/dashboard"
    TASKS = "/tasks"
    PROJECTS = "/projects"
    CYCLES = "/cycles"
    SETTINGS = "/settings"


@dataclass(frozen=True, slots=True)
class NavigationItem:
    route: AppRoute
    label_key: str
    icon: IconName

    @property
    def label(self) -> str:
        return ui_text(self.label_key)


NAVIGATION = (
    NavigationItem(AppRoute.DASHBOARD, "nav.dashboard", IconName.DASHBOARD),
    NavigationItem(AppRoute.TASKS, "nav.tasks", IconName.TASKS),
    NavigationItem(AppRoute.PROJECTS, "nav.projects", IconName.PROJECTS),
    NavigationItem(AppRoute.CYCLES, "nav.cycles", IconName.CYCLES),
    NavigationItem(AppRoute.SETTINGS, "nav.settings", IconName.SETTINGS),
)


def route_family(route: str) -> AppRoute | None:
    if route == AppRoute.DASHBOARD:
        return AppRoute.DASHBOARD
    if route == AppRoute.TASKS:
        return AppRoute.TASKS
    if route == AppRoute.PROJECTS or route.startswith("/projects/"):
        return AppRoute.PROJECTS
    if route == AppRoute.CYCLES or route.startswith("/cycles/"):
        return AppRoute.CYCLES
    if route == AppRoute.SETTINGS:
        return AppRoute.SETTINGS
    return None
