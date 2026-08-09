from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from overlord.ui.design_system.icons import IconName
from .strings import ui_text


class AppRoute(StrEnum):
    DASHBOARD = "/dashboard"
    DAILY_PLANNING = "/planning/day"
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
    NavigationItem(AppRoute.DASHBOARD, ui_text("nav.dashboard"), IconName.DASHBOARD),
    NavigationItem(AppRoute.TASKS, ui_text("nav.tasks"), IconName.TASKS),
    NavigationItem(AppRoute.PROJECTS, ui_text("nav.projects"), IconName.PROJECTS),
    NavigationItem(AppRoute.CYCLES, ui_text("nav.cycles"), IconName.CYCLES),
    NavigationItem(AppRoute.SETTINGS, ui_text("nav.settings"), IconName.SETTINGS),
)


def route_family(route: str) -> AppRoute | None:
    if route == AppRoute.DASHBOARD:
        return AppRoute.DASHBOARD
    if route == AppRoute.DAILY_PLANNING:
        return AppRoute.DAILY_PLANNING
    if route == AppRoute.TASKS:
        return AppRoute.TASKS
    if route == AppRoute.PROJECTS or route.startswith("/projects/"):
        return AppRoute.PROJECTS
    if route == AppRoute.CYCLES or route.startswith("/cycles/"):
        return AppRoute.CYCLES
    if route == AppRoute.SETTINGS:
        return AppRoute.SETTINGS
    return None
