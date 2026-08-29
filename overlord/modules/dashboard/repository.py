from __future__ import annotations

from datetime import date
from typing import Protocol


class DashboardRepositoryPort(Protocol):
    def weekly_counts(self, start: date) -> list[tuple[date, int, int]]: ...
    def execution_counts(self, start: date) -> tuple[int, int]: ...
    def weekly_time_totals(self, start: date) -> tuple[int | None, int | None]: ...
