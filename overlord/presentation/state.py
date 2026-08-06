from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class AppSessionState:
    route: str = "/dashboard"
    theme_mode: str = "system"
    sidebar_collapsed: bool = False
    selected_task_id: int | None = None
    error_message: str | None = None
