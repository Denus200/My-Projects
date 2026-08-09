from __future__ import annotations

import sqlite3
from datetime import date, timedelta


class SqliteDashboardRepository:
    def __init__(self, connection: sqlite3.Connection):
        self.connection = connection

    def weekly_counts(self, start: date) -> list[tuple[date, int, int]]:
        end = start + timedelta(days=6)
        rows = {
            row["planned_date"]: (row["planned"], row["completed"])
            for row in self.connection.execute(
                """
                SELECT tp.planned_date, COUNT(DISTINCT tp.task_id) AS planned,
                       COUNT(DISTINCT CASE WHEN t.lifecycle_status='completed' THEN tp.task_id END) AS completed
                FROM task_plans tp JOIN tasks t ON t.id=tp.task_id
                WHERE tp.planned_date BETWEEN ? AND ?
                GROUP BY tp.planned_date
                """,
                (start.isoformat(), end.isoformat()),
            )
        }
        return [(start + timedelta(days=i), *rows.get((start + timedelta(days=i)).isoformat(), (0, 0))) for i in range(7)]

    def execution_counts(self, start: date) -> tuple[int, int]:
        end = start + timedelta(days=6)
        row = self.connection.execute(
            """
            WITH original AS (
              SELECT task_id, planned_week_start, ROW_NUMBER() OVER (PARTITION BY task_id ORDER BY created_at,id) AS n
              FROM task_plans
            )
            SELECT COUNT(*) AS planned,
                   COALESCE(SUM(CASE WHEN t.lifecycle_status='completed' THEN 1 ELSE 0 END),0) AS completed
            FROM original o JOIN tasks t ON t.id=o.task_id
            WHERE o.n=1 AND o.planned_week_start BETWEEN ? AND ?
            """,
            (start.isoformat(), end.isoformat()),
        ).fetchone()
        return row["planned"], row["completed"]
