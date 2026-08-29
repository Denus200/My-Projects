from __future__ import annotations

import sqlite3
from datetime import date, datetime, time, timedelta

from overlord.app.read_models import TaskListItem, TaskProjectContext
from overlord.modules.tasks.domain import (
    ChecklistItemDraft,
    Task,
    TaskChecklistItem,
    TaskCreationMode,
    TaskLifecycle,
    TaskProjectAssignment,
    TaskProjectLink,
)
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
            "creation_mode": (
                fields.get("creation_mode", TaskCreationMode.NORMAL).value
                if hasattr(fields.get("creation_mode", TaskCreationMode.NORMAL), "value")
                else str(fields.get("creation_mode", TaskCreationMode.NORMAL.value))
            ),
        }
        cursor = self.connection.execute(
            """
            INSERT INTO tasks (project_id,title,description,scheduled_date,planned_minutes,status,
                               lifecycle_status,definition_of_done,next_action,importance,urgency,milestone_id,
                               schedule_start_date,schedule_start_time,schedule_end_date,schedule_end_time,deadline_at,
                               creation_mode)
            VALUES (:project_id,:title,:description,:scheduled_date,:planned_minutes,:status,
                    :lifecycle_status,:definition_of_done,:next_action,:importance,:urgency,:milestone_id,
                    :schedule_start_date,:schedule_start_time,:schedule_end_date,:schedule_end_time,:deadline_at,
                    :creation_mode)
            """,
            values,
        )
        task = self.get(cursor.lastrowid)
        if project_id is not None:
            self.replace_project_links(
                cursor.lastrowid,
                (TaskProjectAssignment(int(project_id)),),
            )
            task = self.get(cursor.lastrowid)
        if not task:
            raise RuntimeError("Created Task could not be loaded.")
        return task

    def get(self, task_id: int) -> Task | None:
        row = self.connection.execute("SELECT * FROM tasks WHERE id=?", (task_id,)).fetchone()
        return _task(row, self.project_links(task_id), self.checklist_items(task_id)) if row else None

    def project_links(self, task_id: int) -> tuple[TaskProjectLink, ...]:
        return tuple(
            TaskProjectLink(row["task_id"], row["project_id"], row["stage_id"], row["position"])
            for row in self.connection.execute(
                "SELECT task_id,project_id,stage_id,position FROM task_project_links WHERE task_id=? ORDER BY position,project_id",
                (task_id,),
            )
        )

    def checklist_items(self, task_id: int) -> tuple[TaskChecklistItem, ...]:
        return tuple(
            TaskChecklistItem(
                row["id"],
                row["task_id"],
                row["parent_item_id"],
                row["title"],
                bool(row["is_completed"]),
                row["position"],
            )
            for row in self.connection.execute(
                """
                SELECT id,task_id,parent_item_id,title,is_completed,position
                FROM task_checklist_items
                WHERE task_id=?
                ORDER BY COALESCE(parent_item_id,0),position,id
                """,
                (task_id,),
            )
        )

    def _project_contexts(self, task_id: int) -> tuple[TaskProjectContext, ...]:
        return tuple(
            TaskProjectContext(
                project_id=row["project_id"],
                project_title=row["project_title"],
                project_color=row["project_color"],
                stage_id=row["stage_id"],
                stage_title=row["stage_title"],
            )
            for row in self.connection.execute(
                """
                SELECT tpl.project_id,p.title AS project_title,p.color AS project_color,
                       tpl.stage_id,ps.title AS stage_title
                FROM task_project_links tpl
                JOIN projects p ON p.id=tpl.project_id
                LEFT JOIN project_stages ps ON ps.id=tpl.stage_id
                WHERE tpl.task_id=?
                ORDER BY tpl.position,tpl.project_id
                """,
                (task_id,),
            )
        )

    def _list_row(self, row: sqlite3.Row) -> TaskListItem:
        contexts = self._project_contexts(row["id"])
        return TaskListItem(
            task=_task(row, self.project_links(row["id"]), self.checklist_items(row["id"])),
            project_title=contexts[0].project_title if contexts else None,
            open_blockers=row["open_blockers"],
            cycle_titles=tuple(filter(None, (row["cycle_titles"] or "").split("||"))),
            project_contexts=contexts,
        )

    def list(self, **filters: object) -> list[TaskListItem]:
        clauses: list[str] = []
        values: list[object] = []
        creation_mode = filters.get("creation_mode")
        if creation_mode is not None:
            clauses.append("t.creation_mode = ?")
            values.append(creation_mode.value if hasattr(creation_mode, "value") else creation_mode)
        elif not filters.get("include_drafts"):
            clauses.append("t.creation_mode = 'normal'")
        search = str(filters.get("search") or "").strip()
        if search:
            clauses.append(
                "(t.title LIKE ? OR EXISTS (SELECT 1 FROM task_project_links spl JOIN projects sp ON sp.id=spl.project_id WHERE spl.task_id=t.id AND sp.title LIKE ?))"
            )
            values.extend((f"%{search}%", f"%{search}%"))
        if filters.get("without_project"):
            clauses.append("NOT EXISTS (SELECT 1 FROM task_project_links npl WHERE npl.task_id=t.id)")
        if filters.get("project_id") is not None:
            clauses.append("EXISTS (SELECT 1 FROM task_project_links fpl WHERE fpl.task_id=t.id AND fpl.project_id=?)")
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
            SELECT t.*,
                   COALESCE(ob.open_blockers, 0) AS open_blockers,
                   cyc.cycle_titles
            FROM tasks t
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
        mapping = {
            "estimate_minutes": "planned_minutes",
            "total_time_minutes": "total_time_minutes",
            "active_time_minutes": "active_time_minutes",
            "lifecycle": "lifecycle_status",
        }
        allowed = {
            "project_id", "title", "description", "planned_minutes", "definition_of_done",
            "next_action", "importance", "urgency", "milestone_id", "schedule_start_date",
            "schedule_start_time", "schedule_end_date", "schedule_end_time", "deadline_at",
            "creation_mode", "total_time_minutes", "active_time_minutes",
        }
        project_change = changes.pop("project_id", ...)
        clean: dict[str, object] = {}
        for original, value in changes.items():
            key = mapping.get(original, original)
            if key in allowed:
                clean[key] = _db_value(value.value if hasattr(value, "value") else value)
        if not clean:
            task = self.get(task_id)
            if not task:
                raise ValueError(f"Task {task_id} does not exist.")
            if project_change is not ...:
                assignments = () if project_change is None else (TaskProjectAssignment(int(project_change)),)
                self.replace_project_links(task_id, assignments)
                task = self.get(task_id)
            return task
        assignments = ", ".join(f"{key}=?" for key in clean)
        cursor = self.connection.execute(
            f"UPDATE tasks SET {assignments}, updated_at=CURRENT_TIMESTAMP WHERE id=?",
            (*clean.values(), task_id),
        )
        if cursor.rowcount != 1:
            raise ValueError(f"Task {task_id} does not exist.")
        if project_change is not ...:
            assignments = () if project_change is None else (TaskProjectAssignment(int(project_change)),)
            self.replace_project_links(task_id, assignments)
        return self.get(task_id)

    def replace_project_links(
        self,
        task_id: int,
        assignments: tuple[TaskProjectAssignment, ...],
    ) -> tuple[TaskProjectLink, ...]:
        if len(assignments) > 4:
            raise ValueError("A Task may belong to at most 4 Projects.")
        project_ids = tuple(assignment.project_id for assignment in assignments)
        if len(set(project_ids)) != len(project_ids):
            raise ValueError("A Task cannot link to the same Project more than once.")
        if self.connection.execute("SELECT 1 FROM tasks WHERE id=?", (task_id,)).fetchone() is None:
            raise ValueError(f"Task {task_id} does not exist.")
        self.connection.execute("DELETE FROM task_project_links WHERE task_id=?", (task_id,))
        self.connection.executemany(
            "INSERT INTO task_project_links(task_id,project_id,stage_id,position) VALUES (?,?,?,?)",
            (
                (task_id, assignment.project_id, assignment.stage_id, position)
                for position, assignment in enumerate(assignments, start=1)
            ),
        )
        compatibility_project_id = assignments[0].project_id if assignments else None
        self.connection.execute(
            "UPDATE tasks SET project_id=?,updated_at=CURRENT_TIMESTAMP WHERE id=?",
            (compatibility_project_id, task_id),
        )
        return self.project_links(task_id)

    def replace_checklist(
        self,
        task_id: int,
        items: tuple[ChecklistItemDraft, ...],
    ) -> tuple[TaskChecklistItem, ...]:
        if self.connection.execute("SELECT 1 FROM tasks WHERE id=?", (task_id,)).fetchone() is None:
            raise ValueError(f"Task {task_id} does not exist.")

        existing_ids = {
            int(row["id"])
            for row in self.connection.execute(
                "SELECT id FROM task_checklist_items WHERE task_id=?",
                (task_id,),
            )
        }
        supplied_ids: set[int] = set()

        def collect_ids(children: tuple[ChecklistItemDraft, ...]) -> None:
            for item in children:
                if item.item_id is not None:
                    if item.item_id not in existing_ids:
                        raise ValueError(f"Checklist item {item.item_id} does not belong to Task {task_id}.")
                    if item.item_id in supplied_ids:
                        raise ValueError("Checklist item IDs must be unique.")
                    supplied_ids.add(item.item_id)
                collect_ids(item.children)

        collect_ids(items)
        # Move existing positions out of the normal range so sibling removal or
        # reparenting cannot transiently violate the unique position index.
        self.connection.execute(
            "UPDATE task_checklist_items SET position=1000000000+id WHERE task_id=?",
            (task_id,),
        )
        retained_ids: set[int] = set()

        def insert_children(
            children: tuple[ChecklistItemDraft, ...],
            parent_item_id: int | None,
        ) -> None:
            for position, item in enumerate(children):
                if item.item_id is None:
                    cursor = self.connection.execute(
                        """
                        INSERT INTO task_checklist_items(task_id,parent_item_id,title,is_completed,position)
                        VALUES (?,?,?,?,?)
                        """,
                        (task_id, parent_item_id, item.title, int(item.completed), position),
                    )
                    item_id = int(cursor.lastrowid)
                else:
                    item_id = item.item_id
                    self.connection.execute(
                        """
                        UPDATE task_checklist_items
                        SET parent_item_id=?,title=?,is_completed=?,position=?,updated_at=CURRENT_TIMESTAMP
                        WHERE id=? AND task_id=?
                        """,
                        (parent_item_id, item.title, int(item.completed), position, item_id, task_id),
                    )
                retained_ids.add(item_id)
                insert_children(item.children, item_id)

        insert_children(items, None)
        removed_ids = existing_ids - retained_ids
        if removed_ids:
            placeholders = ",".join("?" for _ in removed_ids)
            self.connection.execute(
                f"DELETE FROM task_checklist_items WHERE task_id=? AND id IN ({placeholders})",
                (task_id, *sorted(removed_ids)),
            )
        return self.checklist_items(task_id)

    def delete(self, task_id: int) -> None:
        if self.connection.execute("SELECT 1 FROM tasks WHERE id=?", (task_id,)).fetchone() is None:
            raise ValueError(f"Task {task_id} does not exist.")
        # cycle_tasks intentionally uses RESTRICT so history cannot disappear by
        # accident. Explicit Task deletion owns the disconnect.
        self.connection.execute("DELETE FROM cycle_tasks WHERE task_id=?", (task_id,))
        self.connection.execute(
            "UPDATE task_plans SET supersedes_plan_id=NULL WHERE task_id=?",
            (task_id,),
        )
        cursor = self.connection.execute("DELETE FROM tasks WHERE id=?", (task_id,))
        if cursor.rowcount != 1:
            raise ValueError(f"Task {task_id} does not exist.")

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
