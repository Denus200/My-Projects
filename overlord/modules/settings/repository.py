from __future__ import annotations

from typing import Protocol

from overlord.modules.settings.domain import SettingsData


class SettingsRepositoryPort(Protocol):
    def get(self) -> SettingsData: ...
    def update(self, **changes: object) -> SettingsData: ...
