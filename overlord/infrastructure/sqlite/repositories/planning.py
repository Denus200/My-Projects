from __future__ import annotations

import sqlite3
from datetime import date

from overlord.modules.planning.domain import TaskPlan, TodayGroup, week_start

from .mappers import _plan


class SqlitePlanningRepository:
    def __init__(self, connection: sqlite3.Connection):
        self.connection = connection

    def current_plan(self, task_id: int) -> TaskPlan | None:
        row = self.connection.execute(
            """
            SELECT id AS plan_id, task_id, planned_date, planned_week_start, today_group, position,
                   supersedes_plan_id, created_at AS plan_created_at, ended_at
            FROM task_plans WHERE task_id=? AND ended_at IS NULL
            """,
            (task_id,),
        ).fetchone()
        return _plan(row) if row else None

    def assign_plan(self, task_id: int, planned_date: date, group: TodayGroup | None, position: int | None, planned_week_start: date | None = None) -> TaskPlan:
        current = self.current_plan(task_id)
        if current:
            self.connection.execute("UPDATE task_plans SET ended_at=CURRENT_TIMESTAMP WHERE id=?", (current.id,))
        try:
            cursor = self.connection.execute(
                """
                INSERT INTO task_plans (task_id,planned_date,planned_week_start,today_group,position,supersedes_plan_id)
                VALUES (?,?,?,?,?,?)
                """,
                (
                    task_id,
                    planned_date.isoformat(),
                    (planned_week_start or week_start(planned_date)).isoformat(),
                    group.value if group else None,
                    position,
                    current.id if current else None,
                ),
            )
        except sqlite3.IntegrityError as error:
            raise ValueError("That planning slot is already occupied.") from error
        self.connection.execute(
            "UPDATE tasks SET scheduled_date=?, updated_at=CURRENT_TIMESTAMP WHERE id=?",
            (planned_date.isoformat(), task_id),
        )
        row = self.connection.execute(
            """
            SELECT id AS plan_id, task_id, planned_date, planned_week_start, today_group, position,
                   supersedes_plan_id, created_at AS plan_created_at, ended_at
            FROM task_plans WHERE id=?
            """,
            (cursor.lastrowid,),
        ).fetchone()
        return _plan(row)

    def plan_history(self, task_id: int) -> list[TaskPlan]:
        rows = self.connection.execute(
            """
            SELECT id AS plan_id, task_id, planned_date, planned_week_start, today_group, position,
                   supersedes_plan_id, created_at AS plan_created_at, ended_at
            FROM task_plans WHERE task_id=? ORDER BY created_at,id
            """,
            (task_id,),
        ).fetchall()
        return [_plan(row) for row in rows]
