from __future__ import annotations

import sqlite3
from datetime import date

from overlord.app.read_models import TaskListItem
from overlord.modules.planning.domain import week_start
from overlord.modules.tasks.domain import Task, TaskLifecycle
from overlord.modules.tasks.read_models import StatusHistoryEntry

from .mappers import _datetime, _plan, _task


class SqliteTaskRepository:
    def __init__(self, connection: sqlite3.Connection):
        self.connection = connection

    def create(self, project_id: int | None, title: str, lifecycle: TaskLifecycle, **fields: object) -> Task:
        planned_date = fields.pop("planned_date", date.today())
        values = {
            "project_id": project_id,
            "title": title,
            "description": fields.get("description") or "",
            "scheduled_date": planned_date.isoformat() if isinstance(planned_date, date) else str(planned_date),
            "planned_minutes": fields.get("estimate_minutes"),
            "status": "done" if lifecycle is TaskLifecycle.COMPLETED else "planned",
            "lifecycle_status": lifecycle.value,
            "definition_of_done": fields.get("definition_of_done"),
            "next_action": fields.get("next_action"),
            "importance": fields.get("importance"),
            "urgency": fields.get("urgency"),
            "milestone_id": fields.get("milestone_id"),
        }
        cursor = self.connection.execute(
            """
            INSERT INTO tasks (project_id,title,description,scheduled_date,planned_minutes,status,
                               lifecycle_status,definition_of_done,next_action,importance,urgency,milestone_id)
            VALUES (:project_id,:title,:description,:scheduled_date,:planned_minutes,:status,
                    :lifecycle_status,:definition_of_done,:next_action,:importance,:urgency,:milestone_id)
            """,
            values,
        )
        task = self.get(cursor.lastrowid)
        if not task:
            raise RuntimeError("Created Task could not be loaded.")
        return task

    def get(self, task_id: int) -> Task | None:
        row = self.connection.execute("SELECT * FROM tasks WHERE id=?", (task_id,)).fetchone()
        return _task(row) if row else None

    def _list_row(self, row: sqlite3.Row) -> TaskListItem:
        return TaskListItem(
            task=_task(row),
            project_title=row["project_title"],
            current_plan=_plan(row),
            open_blockers=row["open_blockers"],
            carry_over_count=row["carry_over_count"],
        )

    def list(self, **filters: object) -> list[TaskListItem]:
        clauses: list[str] = []
        values: list[object] = []
        search = str(filters.get("search") or "").strip()
        if search:
            clauses.append("(t.title LIKE ? OR COALESCE(p.title, '') LIKE ?)")
            values.extend((f"%{search}%", f"%{search}%"))
        if filters.get("without_project"):
            clauses.append("t.project_id IS NULL")
        if filters.get("project_id") is not None:
            clauses.append("t.project_id = ?")
            values.append(filters["project_id"])
        lifecycle = filters.get("lifecycle")
        if lifecycle:
            clauses.append("t.lifecycle_status = ?")
            values.append(lifecycle.value if hasattr(lifecycle, "value") else lifecycle)
        if filters.get("planned_date"):
            clauses.append("cp.planned_date = ?")
            value = filters["planned_date"]
            values.append(value.isoformat() if isinstance(value, date) else value)
        if filters.get("planned_week_start"):
            clauses.append("cp.planned_week_start = ?")
            value = filters["planned_week_start"]
            values.append(value.isoformat() if isinstance(value, date) else value)
        date_scope = filters.get("date_scope")
        reference_date = filters.get("reference_date") or date.today()
        reference_value = reference_date.isoformat() if isinstance(reference_date, date) else str(reference_date)
        if date_scope == "today":
            clauses.append("cp.planned_date = ?")
            values.append(reference_value)
        elif date_scope == "this_week":
            week_value = filters.get("reference_week_start") or week_start(
                reference_date if isinstance(reference_date, date) else date.fromisoformat(reference_value)
            )
            clauses.append("cp.planned_week_start = ?")
            values.append(week_value.isoformat() if isinstance(week_value, date) else str(week_value))
        elif date_scope == "overdue":
            clauses.append("cp.planned_date < ? AND t.lifecycle_status NOT IN ('completed','cancelled')")
            values.append(reference_value)
        elif date_scope == "unplanned":
            clauses.append("cp.id IS NULL")
        if filters.get("today_group"):
            clauses.append("cp.today_group = ?")
            group = filters["today_group"]
            values.append(group.value if hasattr(group, "value") else group)
        if filters.get("importance") is not None:
            clauses.append("t.importance = ?")
            values.append(int(bool(filters["importance"])))
        if filters.get("urgency") is not None:
            clauses.append("t.urgency = ?")
            values.append(int(bool(filters["urgency"])))
        if filters.get("attention_only"):
            clauses.append(
                "(ob.open_blockers > 0 OR moves.carry_over_count >= 2 OR t.lifecycle_status IS NULL "
                "OR (t.lifecycle_status='in_progress' AND datetime(t.updated_at) <= datetime('now','-7 days')) "
                "OR ((t.lifecycle_status='in_progress' OR cp.today_group='primary') "
                "AND NULLIF(TRIM(t.next_action),'') IS NULL))"
            )
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        rows = self.connection.execute(
            f"""
            SELECT t.*, p.title AS project_title,
                   cp.id AS plan_id, cp.task_id AS plan_task_id, cp.planned_date,
                   cp.planned_week_start, cp.today_group, cp.position,
                   cp.supersedes_plan_id, cp.created_at AS plan_created_at, cp.ended_at,
                   COALESCE(ob.open_blockers, 0) AS open_blockers,
                   COALESCE(moves.carry_over_count, 0) AS carry_over_count
            FROM tasks t
            LEFT JOIN projects p ON p.id=t.project_id
            LEFT JOIN task_plans cp ON cp.task_id=t.id AND cp.ended_at IS NULL
            LEFT JOIN (SELECT task_id, COUNT(*) AS open_blockers FROM blockers
                       WHERE resolved_at IS NULL GROUP BY task_id) ob ON ob.task_id=t.id
            LEFT JOIN (SELECT task_id, COUNT(*) AS carry_over_count FROM task_plans
                       WHERE supersedes_plan_id IS NOT NULL GROUP BY task_id) moves ON moves.task_id=t.id
            {where}
            ORDER BY CASE cp.today_group WHEN 'primary' THEN 0 WHEN 'secondary' THEN 1 ELSE 2 END,
                     cp.position, cp.planned_date, t.updated_at DESC, t.id DESC
            """,
            values,
        ).fetchall()
        return [self._list_row(row) for row in rows]

    def update(self, task_id: int, **changes: object) -> Task:
        mapping = {"estimate_minutes": "planned_minutes", "lifecycle": "lifecycle_status"}
        allowed = {"project_id", "title", "description", "planned_minutes", "definition_of_done", "next_action", "importance", "urgency", "milestone_id"}
        clean: dict[str, object] = {}
        for original, value in changes.items():
            key = mapping.get(original, original)
            if key in allowed:
                clean[key] = value.value if hasattr(value, "value") else value
        if not clean:
            task = self.get(task_id)
            if not task:
                raise ValueError(f"Task {task_id} does not exist.")
            return task
        assignments = ", ".join(f"{key}=?" for key in clean)
        cursor = self.connection.execute(
            f"UPDATE tasks SET {assignments}, updated_at=CURRENT_TIMESTAMP WHERE id=?",
            (*clean.values(), task_id),
        )
        if cursor.rowcount != 1:
            raise ValueError(f"Task {task_id} does not exist.")
        return self.get(task_id)

    def change_lifecycle(self, task_id: int, lifecycle: TaskLifecycle, reason: str | None = None) -> Task:
        current = self.get(task_id)
        if not current:
            raise ValueError(f"Task {task_id} does not exist.")
        now_field = "completed_at=CURRENT_TIMESTAMP," if lifecycle is TaskLifecycle.COMPLETED else ""
        self.connection.execute(
            f"UPDATE tasks SET lifecycle_status=?, status=?, {now_field} updated_at=CURRENT_TIMESTAMP WHERE id=?",
            (lifecycle.value, "done" if lifecycle is TaskLifecycle.COMPLETED else "planned", task_id),
        )
        self.connection.execute(
            "INSERT INTO task_status_history (task_id,from_status,to_status,reason) VALUES (?,?,?,?)",
            (task_id, current.lifecycle_status.value if current.lifecycle_status else current.legacy_status, lifecycle.value, reason),
        )
        return self.get(task_id)

    def status_history(self, task_id: int) -> list[StatusHistoryEntry]:
        return [
            StatusHistoryEntry(row["from_status"], row["to_status"], row["reason"], _datetime(row["changed_at"]))
            for row in self.connection.execute(
                "SELECT * FROM task_status_history WHERE task_id=? ORDER BY changed_at,id", (task_id,)
            )
        ]
