from __future__ import annotations

from dataclasses import dataclass

from .common import SettingsData, UnitOfWorkFactory


@dataclass(frozen=True, slots=True)
class GetSettingsQuery:
    uow_factory: UnitOfWorkFactory

    def execute(self) -> SettingsData:
        with self.uow_factory(read_only=True) as uow:
            return uow.settings.get()


@dataclass(frozen=True, slots=True)
class UpdateSettings:
    uow_factory: UnitOfWorkFactory

    def execute(self, **changes: object) -> SettingsData:
        if "theme_mode" in changes and changes["theme_mode"] not in {"system", "light", "dark"}:
            raise ValueError("Theme mode must be System, Light, or Dark.")
        if "default_cycle_length" in changes and not 1 <= int(changes["default_cycle_length"]) <= 52:
            raise ValueError("Default cycle length must be between 1 and 52 weeks.")
        with self.uow_factory() as uow:
            return uow.settings.update(**changes)


UpdateAppearanceSettings = UpdateSettings
UpdatePlanningSettings = UpdateSettings
UpdateStartupSettings = UpdateSettings


@dataclass(frozen=True, slots=True)
class SettingsApplication:
    get_settings: GetSettingsQuery
    update_settings: UpdateSettings
