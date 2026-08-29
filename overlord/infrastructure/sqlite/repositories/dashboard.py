from __future__ import annotations

import sqlite3
from datetime import date, timedelta


class SqliteDashboardRepository:
    def __init__(self, connection: sqlite3.Connection):
        self.connection = connection

    def weekly_counts(self, start: date) -> list[tuple[date, int, int]]:
        end = start + timedelta(days=6)
        rows = {
            row["schedule_start_date"]: (row["planned"], row["completed"])
            for row in self.connection.execute(
                """
                SELECT schedule_start_date, COUNT(*) AS planned,
                       COUNT(CASE WHEN lifecycle_status='completed' THEN 1 END) AS completed
                FROM tasks
                WHERE creation_mode='normal' AND schedule_start_date BETWEEN ? AND ?
                GROUP BY schedule_start_date
                """,
                (start.isoformat(), end.isoformat()),
            )
        }
        return [(start + timedelta(days=i), *rows.get((start + timedelta(days=i)).isoformat(), (0, 0))) for i in range(7)]

    def execution_counts(self, start: date) -> tuple[int, int]:
        end = start + timedelta(days=6)
        row = self.connection.execute(
            """
            SELECT COUNT(*) AS planned,
                   COALESCE(SUM(CASE WHEN lifecycle_status='completed' THEN 1 ELSE 0 END),0) AS completed
            FROM tasks
            WHERE creation_mode='normal' AND schedule_start_date BETWEEN ? AND ?
            """,
            (start.isoformat(), end.isoformat()),
        ).fetchone()
        return row["planned"], row["completed"]

    def weekly_time_totals(self, start: date) -> tuple[int | None, int | None]:
        end = start + timedelta(days=6)
        row = self.connection.execute(
            """
            SELECT SUM(active_time_minutes) AS active_time_minutes,
                   SUM(total_time_minutes) AS total_time_minutes
            FROM tasks
            WHERE creation_mode='normal' AND schedule_start_date BETWEEN ? AND ?
            """,
            (start.isoformat(), end.isoformat()),
        ).fetchone()
        return row["active_time_minutes"], row["total_time_minutes"]
