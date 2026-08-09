from __future__ import annotations

import sqlite3

from overlord.modules.projects.domain import Project, ProjectStatus
from overlord.modules.projects.read_models import ProjectBlockerItem, ProjectDetail

from .mappers import _blocker, _cycle, _milestone, _project


class SqliteProjectRepository:
    def __init__(self, connection: sqlite3.Connection):
        self.connection = connection

    def create(self, title: str, description: str = "", status: ProjectStatus = ProjectStatus.ACTIVE) -> Project:
        cursor = self.connection.execute(
            "INSERT INTO projects (title, description, status) VALUES (?, ?, ?)",
            (title, description, status.value),
        )
        project = self.get(cursor.lastrowid)
        if project is None:
            raise RuntimeError("Created Project could not be loaded.")
        return project

    def get(self, project_id: int) -> Project | None:
        row = self.connection.execute("SELECT * FROM projects WHERE id = ?", (project_id,)).fetchone()
        return _project(row) if row else None

    def list(self, status: ProjectStatus | None = None, search: str = "") -> list[Project]:
        clauses: list[str] = []
        values: list[object] = []
        if status:
            clauses.append("status = ?")
            values.append(status.value)
        if search.strip():
            clauses.append("(title LIKE ? OR COALESCE(description, '') LIKE ?)")
            values.extend((f"%{search.strip()}%", f"%{search.strip()}%"))
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        rows = self.connection.execute(
            f"SELECT * FROM projects {where} ORDER BY updated_at DESC, id DESC", values
        ).fetchall()
        return [_project(row) for row in rows]

    def detail(self, project_id: int) -> ProjectDetail | None:
        project = self.get(project_id)
        if not project:
            return None
        counts = self.connection.execute(
            """
            SELECT
                COUNT(*) AS eligible_count,
                COALESCE(SUM(CASE WHEN lifecycle_status='completed' THEN 1 ELSE 0 END), 0) AS completed_count,
                COALESCE(SUM(CASE WHEN lifecycle_status NOT IN ('completed','cancelled') OR lifecycle_status IS NULL THEN 1 ELSE 0 END), 0) AS open_count
            FROM tasks
            WHERE project_id=? AND archived_at IS NULL
              AND (lifecycle_status != 'cancelled' OR lifecycle_status IS NULL)
            """,
            (project_id,),
        ).fetchone()
        blocker_rows = self.connection.execute(
            """
            SELECT b.*, t.title AS task_title
            FROM blockers b
            JOIN tasks t ON t.id=b.task_id
            WHERE t.project_id=? AND t.archived_at IS NULL AND b.resolved_at IS NULL
            ORDER BY b.created_at, b.id
            """,
            (project_id,),
        ).fetchall()
        milestone_row = self.connection.execute(
            """
            SELECT * FROM milestones
            WHERE project_id=? AND status IN ('planned','in_progress')
            ORDER BY CASE status WHEN 'in_progress' THEN 0 ELSE 1 END, position, id
            LIMIT 1
            """,
            (project_id,),
        ).fetchone()
        cycle_row = self.connection.execute(
            """
            SELECT c.* FROM cycles c
            JOIN cycle_projects cp ON cp.cycle_id=c.id
            WHERE cp.project_id=? AND c.status='active'
            LIMIT 1
            """,
            (project_id,),
        ).fetchone()
        next_action_rows = self.connection.execute(
            """
            SELECT lifecycle_status, TRIM(next_action) AS next_action
            FROM tasks
            WHERE project_id=? AND archived_at IS NULL
              AND lifecycle_status NOT IN ('completed','cancelled')
              AND next_action IS NOT NULL AND TRIM(next_action) != ''
            ORDER BY id
            """,
            (project_id,),
        ).fetchall()
        in_progress_actions = [row["next_action"] for row in next_action_rows if row["lifecycle_status"] == "in_progress"]
        if len(in_progress_actions) == 1:
            next_action = in_progress_actions[0]
        elif len(next_action_rows) == 1:
            next_action = next_action_rows[0]["next_action"]
        else:
            next_action = None
        blockers = tuple(
            ProjectBlockerItem(_blocker(row), row["task_title"])
            for row in blocker_rows
        )
        return ProjectDetail(
            project=project,
            eligible_task_count=counts["eligible_count"],
            completed_task_count=counts["completed_count"],
            open_task_count=counts["open_count"],
            blockers=blockers,
            current_milestone=_milestone(milestone_row) if milestone_row else None,
            active_cycle=_cycle(cycle_row) if cycle_row else None,
            next_action=next_action,
        )

    def update(self, project_id: int, **changes: object) -> Project:
        allowed = {"title", "description", "status", "stage_label", "started_at", "completed_at", "archived_at"}
        clean = {key: value.value if hasattr(value, "value") else value for key, value in changes.items() if key in allowed}
        if not clean:
            project = self.get(project_id)
            if not project:
                raise ValueError(f"Project {project_id} does not exist.")
            return project
        assignments = ", ".join(f"{key} = ?" for key in clean)
        cursor = self.connection.execute(
            f"UPDATE projects SET {assignments}, updated_at=CURRENT_TIMESTAMP WHERE id=?",
            (*clean.values(), project_id),
        )
        if cursor.rowcount != 1:
            raise ValueError(f"Project {project_id} does not exist.")
        return self.get(project_id)
