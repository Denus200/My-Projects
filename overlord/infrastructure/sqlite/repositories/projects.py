from __future__ import annotations

import sqlite3
from datetime import date, datetime

from overlord.modules.cycles.domain import CycleStatus
from overlord.modules.projects.domain import (
    Project,
    ProjectPlan,
    ProjectPlanStatus,
    ProjectStage,
    ProjectStageStatus,
    ProjectStatus,
)
from overlord.modules.projects.read_models import (
    ProjectBlockerItem,
    ProjectDetail,
    ProjectFile,
    ProjectNote,
    ProjectPlanProgress,
    ProjectStageProgress,
)

from .mappers import _blocker, _cycle, _milestone, _project, _project_plan, _project_stage


def _db_value(value: object) -> object:
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    return value


class SqliteProjectRepository:
    def __init__(self, connection: sqlite3.Connection):
        self.connection = connection

    def create(
        self,
        title: str,
        description: str = "",
        status: ProjectStatus = ProjectStatus.ACTIVE,
        *,
        color: str,
        favorite: bool = False,
    ) -> Project:
        cursor = self.connection.execute(
            "INSERT INTO projects (title,description,status,color,favorite) VALUES (?,?,?,?,?)",
            (title, description, status.value, color, int(favorite)),
        )
        project = self.get(cursor.lastrowid)
        if project is None:
            raise RuntimeError("Created Project could not be loaded.")
        return project

    def get(self, project_id: int) -> Project | None:
        row = self.connection.execute("SELECT * FROM projects WHERE id = ?", (project_id,)).fetchone()
        return _project(row) if row else None

    def list(
        self,
        status: ProjectStatus | None = None,
        search: str = "",
        *,
        favorite_only: bool = False,
        sort: str = "recent",
    ) -> list[Project]:
        clauses: list[str] = []
        values: list[object] = []
        if status:
            clauses.append("status = ?")
            values.append(status.value)
        if search.strip():
            clauses.append("(title LIKE ? OR COALESCE(description, '') LIKE ?)")
            values.extend((f"%{search.strip()}%", f"%{search.strip()}%"))
        if favorite_only:
            clauses.append("favorite = 1")
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        order = {
            "recent": "updated_at DESC, id DESC",
            "name": "title COLLATE NOCASE, id",
            "favorite": "favorite DESC, updated_at DESC, id DESC",
        }.get(sort, "updated_at DESC, id DESC")
        rows = self.connection.execute(
            f"SELECT * FROM projects {where} ORDER BY {order}", values
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
                COALESCE(SUM(CASE WHEN lifecycle_status NOT IN ('completed','cancelled') OR lifecycle_status IS NULL THEN 1 ELSE 0 END), 0) AS open_count,
                COALESCE(SUM(CASE WHEN lifecycle_status='in_progress' THEN 1 ELSE 0 END), 0) AS in_progress_count
            FROM tasks
            WHERE id IN (SELECT task_id FROM task_project_links WHERE project_id=?)
              AND creation_mode='normal'
              AND archived_at IS NULL
              AND (lifecycle_status != 'cancelled' OR lifecycle_status IS NULL)
            """,
            (project_id,),
        ).fetchone()
        blocker_rows = self.connection.execute(
            """
            SELECT b.*, t.title AS task_title
            FROM blockers b
            JOIN tasks t ON t.id=b.task_id
            JOIN task_project_links tpl ON tpl.task_id=t.id
            WHERE tpl.project_id=? AND t.creation_mode='normal'
              AND t.archived_at IS NULL AND b.resolved_at IS NULL
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
        milestone_cycle_row = (
            self.connection.execute(
                """
                SELECT c.id
                FROM cycles c
                JOIN cycle_milestones cm ON cm.cycle_id=c.id
                WHERE cm.milestone_id=?
                ORDER BY CASE c.status WHEN 'active' THEN 0 ELSE 1 END,
                         c.start_date DESC,
                         c.id DESC
                LIMIT 1
                """,
                (milestone_row["id"],),
            ).fetchone()
            if milestone_row
            else None
        )
        linked_cycle_row = self.connection.execute(
            """
            SELECT c.* FROM cycles c
            JOIN cycle_projects cp ON cp.cycle_id=c.id
            WHERE cp.project_id=?
            ORDER BY CASE c.status WHEN 'active' THEN 0 ELSE 1 END,
                     c.start_date DESC,
                     c.id DESC
            LIMIT 1
            """,
            (project_id,),
        ).fetchone()
        next_action_rows = self.connection.execute(
            """
            SELECT id, lifecycle_status, TRIM(next_action) AS next_action
            FROM tasks
            WHERE id IN (SELECT task_id FROM task_project_links WHERE project_id=?)
              AND creation_mode='normal'
              AND archived_at IS NULL
              AND lifecycle_status NOT IN ('completed','cancelled')
              AND next_action IS NOT NULL AND TRIM(next_action) != ''
            ORDER BY id
            """,
            (project_id,),
        ).fetchall()
        in_progress_actions = [row for row in next_action_rows if row["lifecycle_status"] == "in_progress"]
        if len(in_progress_actions) == 1:
            next_action_row = in_progress_actions[0]
        elif len(next_action_rows) == 1:
            next_action_row = next_action_rows[0]
        else:
            next_action_row = None
        blockers = tuple(
            ProjectBlockerItem(_blocker(row), row["task_title"])
            for row in blocker_rows
        )
        plan_row = self.connection.execute(
            "SELECT * FROM project_plans WHERE project_id=? AND status='active' ORDER BY updated_at DESC,id DESC LIMIT 1",
            (project_id,),
        ).fetchone()
        stages = tuple(self.list_stages(project_id, plan_row["id"] if plan_row else None))
        stage_counts: dict[int, tuple[int, int]] = {}
        if stages:
            stage_ids = tuple(stage.id for stage in stages)
            placeholders = ",".join("?" for _ in stage_ids)
            for row in self.connection.execute(
                f"""
                SELECT tpl.stage_id,
                       COUNT(t.id) AS eligible_count,
                       COALESCE(SUM(CASE WHEN t.lifecycle_status='completed' THEN 1 ELSE 0 END),0) AS completed_count
                FROM task_project_links tpl
                JOIN tasks t ON t.id=tpl.task_id
                WHERE tpl.stage_id IN ({placeholders})
                  AND t.creation_mode='normal'
                  AND t.archived_at IS NULL
                  AND (t.lifecycle_status!='cancelled' OR t.lifecycle_status IS NULL)
                GROUP BY tpl.stage_id
                """,
                stage_ids,
            ):
                stage_counts[int(row["stage_id"])] = (
                    int(row["eligible_count"]),
                    int(row["completed_count"]),
                )
        stage_progress = tuple(
            ProjectStageProgress(
                stage,
                stage_counts.get(stage.id, (0, 0))[0],
                stage_counts.get(stage.id, (0, 0))[1],
            )
            for stage in stages
        )
        plan = _project_plan(plan_row) if plan_row else None
        linked_cycle = _cycle(linked_cycle_row) if linked_cycle_row else None
        estimated_minutes = self.connection.execute(
            """
            SELECT COALESCE(SUM(COALESCE(t.planned_minutes,0)),0)
            FROM tasks t JOIN task_project_links tpl ON tpl.task_id=t.id
            WHERE tpl.project_id=? AND t.creation_mode='normal' AND t.archived_at IS NULL
              AND (t.lifecycle_status!='cancelled' OR t.lifecycle_status IS NULL)
            """,
            (project_id,),
        ).fetchone()[0]
        return ProjectDetail(
            project=project,
            eligible_task_count=counts["eligible_count"],
            completed_task_count=counts["completed_count"],
            open_task_count=counts["open_count"],
            in_progress_task_count=counts["in_progress_count"],
            blockers=blockers,
            current_milestone=_milestone(milestone_row) if milestone_row else None,
            active_cycle=(
                linked_cycle
                if linked_cycle is not None and linked_cycle.status is CycleStatus.ACTIVE
                else None
            ),
            next_action=next_action_row["next_action"] if next_action_row else None,
            active_plan=plan,
            stages=stages,
            estimated_minutes=int(estimated_minutes),
            plan_progress=(
                ProjectPlanProgress(plan, stage_progress)
                if plan is not None
                else None
            ),
            next_action_task_id=int(next_action_row["id"]) if next_action_row else None,
            linked_cycle=linked_cycle,
            current_milestone_cycle_id=(
                int(milestone_cycle_row["id"])
                if milestone_cycle_row is not None
                else None
            ),
        )

    def update(self, project_id: int, **changes: object) -> Project:
        allowed = {
            "title", "description", "status", "stage_label", "started_at", "completed_at",
            "archived_at", "color", "favorite",
        }
        clean = {
            key: _db_value(value.value if hasattr(value, "value") else value)
            for key, value in changes.items()
            if key in allowed
        }
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

    def create_plan(self, project_id: int, title: str) -> ProjectPlan:
        cursor = self.connection.execute(
            "INSERT INTO project_plans(project_id,title) VALUES (?,?)",
            (project_id, title),
        )
        plan = self.get_plan(cursor.lastrowid)
        if plan is None:
            raise RuntimeError("Created Project Plan could not be loaded.")
        return plan

    def get_plan(self, plan_id: int) -> ProjectPlan | None:
        row = self.connection.execute("SELECT * FROM project_plans WHERE id=?", (plan_id,)).fetchone()
        return _project_plan(row) if row else None

    def list_plans(self, project_id: int) -> list[ProjectPlan]:
        rows = self.connection.execute(
            "SELECT * FROM project_plans WHERE project_id=? ORDER BY CASE status WHEN 'active' THEN 0 WHEN 'completed' THEN 1 ELSE 2 END, updated_at DESC,id DESC",
            (project_id,),
        ).fetchall()
        return [_project_plan(row) for row in rows]

    def update_plan(self, plan_id: int, status: ProjectPlanStatus) -> ProjectPlan:
        completed = "CURRENT_TIMESTAMP" if status is ProjectPlanStatus.COMPLETED else "NULL"
        archived = "CURRENT_TIMESTAMP" if status is ProjectPlanStatus.ARCHIVED else "NULL"
        cursor = self.connection.execute(
            f"UPDATE project_plans SET status=?,completed_at={completed},archived_at={archived},updated_at=CURRENT_TIMESTAMP WHERE id=?",
            (status.value, plan_id),
        )
        if cursor.rowcount != 1:
            raise ValueError(f"Project Plan {plan_id} does not exist.")
        return self.get_plan(plan_id)

    def create_stage(self, plan_id: int, project_id: int, title: str, **fields: object) -> ProjectStage:
        position = self.connection.execute(
            "SELECT COALESCE(MAX(position)+1,0) FROM project_stages WHERE project_plan_id=?",
            (plan_id,),
        ).fetchone()[0]
        cursor = self.connection.execute(
            """
            INSERT INTO project_stages(project_plan_id,project_id,title,status,position,start_date,end_date)
            VALUES (?,?,?,?,?,?,?)
            """,
            (
                plan_id,
                project_id,
                title,
                getattr(fields.get("status", ProjectStageStatus.PLANNED), "value", fields.get("status", "planned")),
                position,
                _db_value(fields.get("start_date")),
                _db_value(fields.get("end_date")),
            ),
        )
        stage = self.get_stage(cursor.lastrowid)
        if stage is None:
            raise RuntimeError("Created Project Stage could not be loaded.")
        return stage

    def get_stage(self, stage_id: int) -> ProjectStage | None:
        row = self.connection.execute("SELECT * FROM project_stages WHERE id=?", (stage_id,)).fetchone()
        return _project_stage(row) if row else None

    def list_stages(self, project_id: int, plan_id: int | None = None) -> list[ProjectStage]:
        clauses = ["project_id=?"]
        values: list[object] = [project_id]
        if plan_id is not None:
            clauses.append("project_plan_id=?")
            values.append(plan_id)
        rows = self.connection.execute(
            f"SELECT * FROM project_stages WHERE {' AND '.join(clauses)} ORDER BY position,id",
            values,
        ).fetchall()
        return [_project_stage(row) for row in rows]

    def update_stage(self, stage_id: int, **changes: object) -> ProjectStage:
        allowed = {"title", "status", "position", "start_date", "end_date", "archived_at"}
        clean = {
            key: _db_value(value.value if hasattr(value, "value") else value)
            for key, value in changes.items()
            if key in allowed
        }
        if clean:
            assignments = ",".join(f"{key}=?" for key in clean)
            cursor = self.connection.execute(
                f"UPDATE project_stages SET {assignments},updated_at=CURRENT_TIMESTAMP WHERE id=?",
                (*clean.values(), stage_id),
            )
            if cursor.rowcount != 1:
                raise ValueError(f"Stage {stage_id} does not exist.")
        stage = self.get_stage(stage_id)
        if stage is None:
            raise ValueError(f"Stage {stage_id} does not exist.")
        return stage

    def clear_stage_links(self, stage_id: int) -> None:
        self.connection.execute("UPDATE task_project_links SET stage_id=NULL WHERE stage_id=?", (stage_id,))

    def create_note(self, project_id: int, title: str, relative_path: str) -> ProjectNote:
        cursor = self.connection.execute(
            "INSERT INTO project_notes(project_id,title,relative_path) VALUES (?,?,?)",
            (project_id, title, relative_path),
        )
        return ProjectNote(cursor.lastrowid, project_id, title, relative_path)

    def list_notes(self, project_id: int) -> list[ProjectNote]:
        return [
            ProjectNote(row["id"], row["project_id"], row["title"], row["relative_path"])
            for row in self.connection.execute(
                "SELECT * FROM project_notes WHERE project_id=? AND archived_at IS NULL ORDER BY updated_at DESC,id DESC",
                (project_id,),
            )
        ]

    def create_file(self, project_id: int, display_name: str, relative_path: str, size_bytes: int) -> ProjectFile:
        cursor = self.connection.execute(
            "INSERT INTO project_files(project_id,display_name,relative_path,size_bytes) VALUES (?,?,?,?)",
            (project_id, display_name, relative_path, size_bytes),
        )
        return ProjectFile(cursor.lastrowid, project_id, display_name, relative_path, size_bytes)

    def list_files(self, project_id: int) -> list[ProjectFile]:
        return [
            ProjectFile(row["id"], row["project_id"], row["display_name"], row["relative_path"], row["size_bytes"])
            for row in self.connection.execute(
                "SELECT * FROM project_files WHERE project_id=? AND archived_at IS NULL ORDER BY added_at DESC,id DESC",
                (project_id,),
            )
        ]
