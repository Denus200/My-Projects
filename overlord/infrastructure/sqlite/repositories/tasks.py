from __future__ import annotations

import sqlite3
from datetime import date, datetime, time, timedelta

from overlord.app.read_models import TaskListItem
from overlord.modules.tasks.domain import Task, TaskLifecycle
from overlord.modules.tasks.read_models import StatusHistoryEntry

from .mappers import _datetime, _task


def _db_value(value: object) -> object:
    if isinstance(value, (date, datetime, time)):
        return value.isoformat()
    return value


class SqliteTaskRepository:
    def __init__(self, connection: sqlite3.Connection):
        self.connection = connection

    def create(self, project_id: int | None, title: str, lifecycle: TaskLifecycle, **fields: object) -> Task:
        start_date = fields.get("schedule_start_date")
        values = {
            "project_id": project_id,
            "title": title,
            "description": fields.get("description") or "",
            # Retained for compatibility with the original schema. New product
            # behavior reads the nullable canonical schedule fields below.
            "scheduled_date": (start_date or date.today()).isoformat() if isinstance(start_date or date.today(), date) else str(start_date),
            "planned_minutes": fields.get("estimate_minutes"),
            "status": "done" if lifecycle is TaskLifecycle.COMPLETED else "planned",
            "lifecycle_status": lifecycle.value,
            "definition_of_done": fields.get("definition_of_done"),
            "next_action": fields.get("next_action"),
            "importance": fields.get("importance"),
            "urgency": fields.get("urgency"),
            "milestone_id": fields.get("milestone_id"),
            "schedule_start_date": _db_value(start_date),
            "schedule_start_time": _db_value(fields.get("schedule_start_time")),
            "schedule_end_date": _db_value(fields.get("schedule_end_date")),
            "schedule_end_time": _db_value(fields.get("schedule_end_time")),
            "deadline_at": _db_value(fields.get("deadline_at")),
        }
        cursor = self.connection.execute(
            """
            INSERT INTO tasks (project_id,title,description,scheduled_date,planned_minutes,status,
                               lifecycle_status,definition_of_done,next_action,importance,urgency,milestone_id,
                               schedule_start_date,schedule_start_time,schedule_end_date,schedule_end_time,deadline_at)
            VALUES (:project_id,:title,:description,:scheduled_date,:planned_minutes,:status,
                    :lifecycle_status,:definition_of_done,:next_action,:importance,:urgency,:milestone_id,
                    :schedule_start_date,:schedule_start_time,:schedule_end_date,:schedule_end_time,:deadline_at)
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
            open_blockers=row["open_blockers"],
            cycle_titles=tuple(filter(None, (row["cycle_titles"] or "").split("||"))),
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
        if filters.get("schedule_date"):
            clauses.append("t.schedule_start_date <= ? AND COALESCE(t.schedule_end_date,t.schedule_start_date) >= ?")
            value = filters["schedule_date"]
            serialized = value.isoformat() if isinstance(value, date) else value
            values.extend((serialized, serialized))
        if filters.get("schedule_start_date"):
            clauses.append("t.schedule_start_date = ?")
            value = filters["schedule_start_date"]
            values.append(value.isoformat() if isinstance(value, date) else value)
        date_scope = filters.get("date_scope")
        reference_date = filters.get("reference_date") or date.today()
        reference_value = reference_date.isoformat() if isinstance(reference_date, date) else str(reference_date)
        if date_scope == "today":
            clauses.append("t.schedule_start_date <= ? AND COALESCE(t.schedule_end_date,t.schedule_start_date) >= ?")
            values.extend((reference_value, reference_value))
        elif date_scope == "this_week":
            reference = reference_date if isinstance(reference_date, date) else date.fromisoformat(reference_value)
            first_day = int(filters.get("first_day", 0))
            week_value = filters.get("reference_week_start") or reference.fromordinal(
                reference.toordinal() - ((reference.weekday() - first_day) % 7)
            )
            week_end = week_value + timedelta(days=6)
            clauses.append("t.schedule_start_date <= ? AND COALESCE(t.schedule_end_date,t.schedule_start_date) >= ?")
            values.extend((week_end.isoformat(), week_value.isoformat()))
        elif date_scope == "overdue":
            clauses.append(
                "t.schedule_start_date IS NOT NULL AND "
                "COALESCE(t.schedule_end_date,t.schedule_start_date) < ? "
                "AND t.lifecycle_status NOT IN ('completed','cancelled')"
            )
            values.append(reference_value)
        elif date_scope == "unplanned":
            clauses.append("t.schedule_start_date IS NULL")
        if filters.get("importance") is not None:
            clauses.append("t.importance = ?")
            values.append(int(bool(filters["importance"])))
        if filters.get("urgency") is not None:
            clauses.append("t.urgency = ?")
            values.append(int(bool(filters["urgency"])))
        if filters.get("attention_only"):
            clauses.append(
                "(ob.open_blockers > 0 OR t.lifecycle_status IS NULL "
                "OR (t.lifecycle_status='in_progress' AND datetime(t.updated_at) <= datetime('now','-7 days')))"
            )
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        rows = self.connection.execute(
            f"""
            SELECT t.*, p.title AS project_title,
                   COALESCE(ob.open_blockers, 0) AS open_blockers,
                   cyc.cycle_titles
            FROM tasks t
            LEFT JOIN projects p ON p.id=t.project_id
            LEFT JOIN (SELECT task_id, COUNT(*) AS open_blockers FROM blockers
                       WHERE resolved_at IS NULL GROUP BY task_id) ob ON ob.task_id=t.id
            LEFT JOIN (
                SELECT ct.task_id, GROUP_CONCAT(c.title, '||') AS cycle_titles
                FROM cycle_tasks ct
                JOIN cycles c ON c.id=ct.cycle_id
                WHERE ct.disconnected_at IS NULL
                GROUP BY ct.task_id
            ) cyc ON cyc.task_id=t.id
            {where}
            ORDER BY CASE WHEN t.schedule_start_date IS NULL THEN 1 ELSE 0 END,
                     t.schedule_start_date, t.schedule_start_time, t.updated_at DESC, t.id DESC
            """,
            values,
        ).fetchall()
        return [self._list_row(row) for row in rows]

    def update(self, task_id: int, **changes: object) -> Task:
        mapping = {"estimate_minutes": "planned_minutes", "lifecycle": "lifecycle_status"}
        allowed = {
            "project_id", "title", "description", "planned_minutes", "definition_of_done",
            "next_action", "importance", "urgency", "milestone_id", "schedule_start_date",
            "schedule_start_time", "schedule_end_date", "schedule_end_time", "deadline_at",
        }
        clean: dict[str, object] = {}
        for original, value in changes.items():
            key = mapping.get(original, original)
            if key in allowed:
                clean[key] = _db_value(value.value if hasattr(value, "value") else value)
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
        if lifecycle is TaskLifecycle.COMPLETED:
            timestamp_fields = "completed_at=CURRENT_TIMESTAMP, archived_at=NULL,"
        elif lifecycle is TaskLifecycle.CANCELLED:
            timestamp_fields = "completed_at=NULL, archived_at=CURRENT_TIMESTAMP,"
        else:
            timestamp_fields = "completed_at=NULL, archived_at=NULL,"
        self.connection.execute(
            f"UPDATE tasks SET lifecycle_status=?, status=?, {timestamp_fields} updated_at=CURRENT_TIMESTAMP WHERE id=?",
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

    def day_positions(self, day: date) -> dict[int, int]:
        return {
            int(row["task_id"]): int(row["position"])
            for row in self.connection.execute(
                "SELECT task_id,position FROM task_day_positions WHERE day=? ORDER BY position,task_id",
                (day.isoformat(),),
            )
        }

    def replace_day_order(self, day: date, task_ids: tuple[int, ...]) -> None:
        serialized = day.isoformat()
        self.connection.execute("DELETE FROM task_day_positions WHERE day=?", (serialized,))
        self.connection.executemany(
            "INSERT INTO task_day_positions(task_id,day,position) VALUES (?,?,?)",
            ((task_id, serialized, position) for position, task_id in enumerate(task_ids)),
        )
