from __future__ import annotations

import sqlite3

from overlord.modules.settings.domain import SettingsData

from .mappers import _datetime


class SqliteSettingsRepository:
    def __init__(self, connection: sqlite3.Connection):
        self.connection = connection

    def get(self) -> SettingsData:
        row = self.connection.execute("SELECT * FROM settings WHERE id=1").fetchone()
        if not row:
            raise RuntimeError("Settings row is missing.")
        return SettingsData(
            locale=row["locale"], theme_mode=row["theme_mode"], motion_enabled=bool(row["motion_enabled"]),
            reduced_motion=bool(row["reduced_motion"]), first_day_of_week=row["first_day_of_week"],
            default_cycle_length=row["default_cycle_length"], startup_destination=row["startup_destination"],
            sidebar_collapsed=bool(row["sidebar_collapsed"]), updated_at=_datetime(row["updated_at"]),
        )

    def update(self, **changes: object) -> SettingsData:
        allowed = {"locale", "theme_mode", "motion_enabled", "reduced_motion", "first_day_of_week", "default_cycle_length", "startup_destination", "sidebar_collapsed"}
        clean = {key: int(value) if isinstance(value, bool) else value for key, value in changes.items() if key in allowed}
        if clean:
            assignments = ", ".join(f"{key}=?" for key in clean)
            self.connection.execute(
                f"UPDATE settings SET {assignments}, updated_at=CURRENT_TIMESTAMP WHERE id=1", tuple(clean.values())
            )
        return self.get()
