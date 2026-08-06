from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from .design_system.icons import IconName


class AppRoute(StrEnum):
    DASHBOARD = "/dashboard"
    TASKS = "/tasks"
    PROJECTS = "/projects"
    CYCLES = "/cycles"
    SETTINGS = "/settings"


@dataclass(frozen=True, slots=True)
class NavigationItem:
    route: AppRoute
    label: str
    icon: IconName


NAVIGATION = (
    NavigationItem(AppRoute.DASHBOARD, "Dashboard", IconName.DASHBOARD),
    NavigationItem(AppRoute.TASKS, "Tasks", IconName.TASKS),
    NavigationItem(AppRoute.PROJECTS, "Projects", IconName.PROJECTS),
    NavigationItem(AppRoute.CYCLES, "12-Week Plans", IconName.CYCLES),
    NavigationItem(AppRoute.SETTINGS, "Settings", IconName.SETTINGS),
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
