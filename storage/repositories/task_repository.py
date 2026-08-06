import sqlite3
from datetime import date

from core.models import Task


def _date_to_storage(value: date | str) -> str:
    return value.isoformat() if isinstance(value, date) else value


def _task_from_row(row: sqlite3.Row) -> Task:
    return Task(
        id=row["id"],
        project_id=row["project_id"],
        project_title=row["project_title"],
        title=row["title"],
        description=row["description"],
        scheduled_date=row["scheduled_date"],
        planned_minutes=row["planned_minutes"],
        status=row["status"],
        comment=row["comment"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


class TaskRepository:
    def __init__(self, connection: sqlite3.Connection):
        self.connection = connection

    def create(
        self,
        project_id: int,
        title: str,
        scheduled_date: date | str,
        description: str = "",
        planned_minutes: int | None = None,
        status: str = "planned",
    ) -> Task:
        cursor = self.connection.execute(
            """
            INSERT INTO tasks (
                project_id, title, description, scheduled_date, planned_minutes, status
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (project_id, title, description, _date_to_storage(scheduled_date), planned_minutes, status),
        )
        self.connection.commit()
        task = self.get_by_id(cursor.lastrowid)
        if task is None:
            raise RuntimeError("Created task could not be loaded.")
        return task

    def get_by_id(self, task_id: int) -> Task | None:
        row = self.connection.execute(
            """
            SELECT tasks.*, projects.title AS project_title
            FROM tasks
            JOIN projects ON projects.id = tasks.project_id
            WHERE tasks.id = ?
            """,
            (task_id,),
        ).fetchone()
        return _task_from_row(row) if row else None

    def list_for_date(self, scheduled_date: date | str, limit: int = 3) -> list[Task]:
        rows = self.connection.execute(
            """
            SELECT tasks.*, projects.title AS project_title
            FROM tasks
            JOIN projects ON projects.id = tasks.project_id
            WHERE tasks.scheduled_date = ?
            ORDER BY tasks.created_at ASC, tasks.id ASC
            LIMIT ?
            """,
            (_date_to_storage(scheduled_date), limit),
        ).fetchall()
        return [_task_from_row(row) for row in rows]

    def update_state(self, task_id: int, status: str, comment: str) -> Task:
        self.connection.execute(
            """
            UPDATE tasks
            SET status = ?, comment = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (status, comment, task_id),
        )
        self.connection.commit()
        task = self.get_by_id(task_id)
        if task is None:
            raise ValueError(f"Task {task_id} does not exist.")
        return task
