from __future__ import annotations

from datetime import date
from typing import Callable

import flet as ft

from overlord.app.services import ApplicationServices
from overlord.modules.projects.domain import Project
from overlord.ui.components.task_details import build_task_details_dialog
from overlord.ui.components.task_workspace import build_tasks_workspace
from overlord.ui.design_system.tokens import ThemeTokens
from overlord.ui.state import AppSessionState


def build_task_editor_content(
    services: ApplicationServices,
    projects: tuple[Project, ...],
    task_id: int,
    tokens: ThemeTokens,
    on_saved: Callable[[], None],
    on_changed: Callable[[], None],
    close: Callable[[], None],
    report_error,
    *,
    page: ft.Page | None = None,
) -> ft.AlertDialog:
    """Compatibility adapter for the shared Task Details dialog."""
    del on_changed
    task = services.tasks.get_editor.execute(task_id).task
    return build_task_details_dialog(
        services,
        projects,
        task_id,
        task.schedule_start_date or date.today(),
        tokens,
        on_saved,
        close,
        report_error,
        page=page,
        on_deleted=on_saved,
    )


def build_tasks(
    services: ApplicationServices,
    tokens: ThemeTokens,
    state: AppSessionState,
    refresh,
    report_error,
    page: ft.Page | None = None,
) -> ft.Control:
    return build_tasks_workspace(
        services,
        tokens,
        state,
        refresh,
        report_error,
        page,
        build_task_editor_content,
    )
