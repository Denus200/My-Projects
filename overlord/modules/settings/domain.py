from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class SettingsData:
    locale: str = "en"
    theme_mode: str = "system"
    motion_enabled: bool = True
    reduced_motion: bool = False
    first_day_of_week: str = "monday"
    default_cycle_length: int = 12
    startup_destination: str = "dashboard"
    sidebar_collapsed: bool = False
    updated_at: datetime | None = None

    @property
    def effective_motion(self) -> bool:
        return self.motion_enabled and not self.reduced_motion
