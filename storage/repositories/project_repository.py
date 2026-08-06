import sqlite3

from core.models import Project


def _project_from_row(row: sqlite3.Row) -> Project:
    return Project(
        id=row["id"],
        title=row["title"],
        description=row["description"],
        status=row["status"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


class ProjectRepository:
    def __init__(self, connection: sqlite3.Connection):
        self.connection = connection

    def create(self, title: str, description: str = "", status: str = "active") -> Project:
        cursor = self.connection.execute(
            """
            INSERT INTO projects (title, description, status)
            VALUES (?, ?, ?)
            """,
            (title, description, status),
        )
        self.connection.commit()
        project = self.get_by_id(cursor.lastrowid)
        if project is None:
            raise RuntimeError("Created project could not be loaded.")
        return project

    def get_by_id(self, project_id: int) -> Project | None:
        row = self.connection.execute(
            "SELECT * FROM projects WHERE id = ?",
            (project_id,),
        ).fetchone()
        return _project_from_row(row) if row else None

    def list_by_status(self, status: str = "active") -> list[Project]:
        rows = self.connection.execute(
            "SELECT * FROM projects WHERE status = ? ORDER BY created_at ASC, id ASC",
            (status,),
        ).fetchall()
        return [_project_from_row(row) for row in rows]
