from __future__ import annotations

import sqlite3
from datetime import date, datetime, timedelta

from overlord.application.common import (
    CycleDetail,
    CycleSummary,
    ProjectBlockerItem,
    ProjectDetail,
    SettingsData,
    StatusHistoryEntry,
    TaskListItem,
)
from overlord.domain.cycles import (
    Cycle,
    CycleStatus,
    Milestone,
    MilestoneStatus,
    WeeklyOutcome,
    WeeklyOutcomeStatus,
    cycle_end_date,
)
from overlord.domain.planning import TaskPlan
from overlord.domain.projects import Project, ProjectStatus
from overlord.domain.tasks import Blocker, BlockerType, Task, TaskLifecycle, TodayGroup, week_start


def _datetime(value: str | None) -> datetime | None:
    return datetime.fromisoformat(value) if value else None


def _date(value: str | None) -> date | None:
    return date.fromisoformat(value) if value else None


def _boolean(value: int | None) -> bool | None:
    return None if value is None else bool(value)


def _project(row: sqlite3.Row) -> Project:
    return Project(
        id=row["id"],
        title=row["title"],
        description=row["description"] or None,
        status=ProjectStatus(row["status"]),
        created_at=_datetime(row["created_at"]),
        updated_at=_datetime(row["updated_at"]),
        stage_label=row["stage_label"],
        started_at=_datetime(row["started_at"]),
        completed_at=_datetime(row["completed_at"]),
        archived_at=_datetime(row["archived_at"]),
    )


def _task(row: sqlite3.Row) -> Task:
    lifecycle = row["lifecycle_status"]
    return Task(
        id=row["id"],
        project_id=row["project_id"],
        title=row["title"],
        description=row["description"] or None,
        lifecycle_status=TaskLifecycle(lifecycle) if lifecycle else None,
        legacy_status=row["status"],
        definition_of_done=row["definition_of_done"],
        next_action=row["next_action"],
        importance=_boolean(row["importance"]),
        urgency=_boolean(row["urgency"]),
        estimate_minutes=row["planned_minutes"],
        started_at=_datetime(row["started_at"]),
        completed_at=_datetime(row["completed_at"]),
        archived_at=_datetime(row["archived_at"]),
        milestone_id=row["milestone_id"],
        created_at=_datetime(row["created_at"]),
        updated_at=_datetime(row["updated_at"]),
    )


def _plan(row: sqlite3.Row | None, prefix: str = "") -> TaskPlan | None:
    if row is None or row[f"{prefix}plan_id"] is None:
        return None
    task_key = f"{prefix}task_id"
    if task_key not in row.keys() and not prefix and "plan_task_id" in row.keys():
        task_key = "plan_task_id"
    group = row[f"{prefix}today_group"]
    return TaskPlan(
        id=row[f"{prefix}plan_id"],
        task_id=row[task_key],
        planned_date=_date(row[f"{prefix}planned_date"]),
        planned_week_start=_date(row[f"{prefix}planned_week_start"]),
        today_group=TodayGroup(group) if group else None,
        position=row[f"{prefix}position"],
        supersedes_plan_id=row[f"{prefix}supersedes_plan_id"],
        created_at=_datetime(row[f"{prefix}plan_created_at"]),
        ended_at=_datetime(row[f"{prefix}ended_at"]),
    )


def _blocker(row: sqlite3.Row) -> Blocker:
    return Blocker(
        id=row["id"],
        task_id=row["task_id"],
        type=BlockerType(row["type"]),
        description=row["description"],
        created_at=_datetime(row["created_at"]),
        resolved_at=_datetime(row["resolved_at"]),
        resolution=row["resolution"],
    )


def _cycle(row: sqlite3.Row) -> Cycle:
    return Cycle(
        id=row["id"],
        title=row["title"],
        main_outcome=row["main_outcome"],
        start_date=_date(row["start_date"]),
        length_weeks=row["length_weeks"],
        end_date=_date(row["end_date"]),
        status=CycleStatus(row["status"]),
        created_at=_datetime(row["created_at"]),
        updated_at=_datetime(row["updated_at"]),
        completed_at=_datetime(row["completed_at"]),
        archived_at=_datetime(row["archived_at"]),
    )


def _milestone(row: sqlite3.Row) -> Milestone:
    return Milestone(
        id=row["id"],
        project_id=row["project_id"],
        title=row["title"],
        definition_of_done=row["definition_of_done"],
        status=MilestoneStatus(row["status"]),
        target_date=_date(row["target_date"]),
        position=row["position"],
        started_at=_datetime(row["started_at"]),
        completed_at=_datetime(row["completed_at"]),
        created_at=_datetime(row["created_at"]),
        updated_at=_datetime(row["updated_at"]),
    )


def _outcome(row: sqlite3.Row) -> WeeklyOutcome:
    return WeeklyOutcome(
        id=row["id"],
        cycle_id=row["cycle_id"],
        week_number=row["week_number"],
        title=row["title"],
        definition_of_done=row["definition_of_done"],
        status=WeeklyOutcomeStatus(row["status"]),
        completed_at=_datetime(row["completed_at"]),
        created_at=_datetime(row["created_at"]),
        updated_at=_datetime(row["updated_at"]),
    )


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

    def open_blocker(self, task_id: int, blocker_type: BlockerType, description: str) -> Blocker:
        cursor = self.connection.execute(
            "INSERT INTO blockers (task_id,type,description) VALUES (?,?,?)",
            (task_id, blocker_type.value, description),
        )
        row = self.connection.execute("SELECT * FROM blockers WHERE id=?", (cursor.lastrowid,)).fetchone()
        return _blocker(row)

    def resolve_blocker(self, blocker_id: int, resolution: str) -> Blocker:
        cursor = self.connection.execute(
            "UPDATE blockers SET resolved_at=CURRENT_TIMESTAMP,resolution=? WHERE id=? AND resolved_at IS NULL",
            (resolution, blocker_id),
        )
        if cursor.rowcount != 1:
            raise ValueError(f"Open Blocker {blocker_id} does not exist.")
        return _blocker(self.connection.execute("SELECT * FROM blockers WHERE id=?", (blocker_id,)).fetchone())

    def list_blockers(self, task_id: int, open_only: bool = False) -> list[Blocker]:
        suffix = "AND resolved_at IS NULL" if open_only else ""
        rows = self.connection.execute(
            f"SELECT * FROM blockers WHERE task_id=? {suffix} ORDER BY created_at DESC", (task_id,)
        ).fetchall()
        return [_blocker(row) for row in rows]

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

    def status_history(self, task_id: int) -> list[StatusHistoryEntry]:
        return [
            StatusHistoryEntry(row["from_status"], row["to_status"], row["reason"], _datetime(row["changed_at"]))
            for row in self.connection.execute(
                "SELECT * FROM task_status_history WHERE task_id=? ORDER BY changed_at,id", (task_id,)
            )
        ]

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


class SqliteSettingsRepository:
    def __init__(self, connection: sqlite3.Connection):
        self.connection = connection

    def get(self) -> SettingsData:
        row = self.connection.execute("SELECT * FROM settings WHERE id=1").fetchone()
        if not row:
            raise RuntimeError("Settings row is missing.")
        return SettingsData(
            theme_mode=row["theme_mode"], motion_enabled=bool(row["motion_enabled"]),
            reduced_motion=bool(row["reduced_motion"]), first_day_of_week=row["first_day_of_week"],
            default_cycle_length=row["default_cycle_length"], startup_destination=row["startup_destination"],
            sidebar_collapsed=bool(row["sidebar_collapsed"]), updated_at=_datetime(row["updated_at"]),
        )

    def update(self, **changes: object) -> SettingsData:
        allowed = {"theme_mode", "motion_enabled", "reduced_motion", "first_day_of_week", "default_cycle_length", "startup_destination", "sidebar_collapsed"}
        clean = {key: int(value) if isinstance(value, bool) else value for key, value in changes.items() if key in allowed}
        if clean:
            assignments = ", ".join(f"{key}=?" for key in clean)
            self.connection.execute(
                f"UPDATE settings SET {assignments}, updated_at=CURRENT_TIMESTAMP WHERE id=1", tuple(clean.values())
            )
        return self.get()


class SqliteCycleRepository:
    def __init__(self, connection: sqlite3.Connection, tasks: SqliteTaskRepository):
        self.connection = connection
        self.tasks = tasks

    def create(self, title: str, main_outcome: str, start_date: date, length_weeks: int) -> Cycle:
        cursor = self.connection.execute(
            "INSERT INTO cycles (title,main_outcome,start_date,length_weeks,end_date) VALUES (?,?,?,?,?)",
            (title, main_outcome, start_date.isoformat(), length_weeks, cycle_end_date(start_date, length_weeks).isoformat()),
        )
        return self.get(cursor.lastrowid)

    def get(self, cycle_id: int) -> Cycle | None:
        row = self.connection.execute("SELECT * FROM cycles WHERE id=?", (cycle_id,)).fetchone()
        return _cycle(row) if row else None

    def list(self, status: CycleStatus | None = None, search: str = "") -> list[Cycle]:
        clauses, values = [], []
        if status:
            clauses.append("status=?")
            values.append(status.value)
        if search.strip():
            clauses.append("(title LIKE ? OR main_outcome LIKE ?)")
            values.extend((f"%{search.strip()}%", f"%{search.strip()}%"))
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        rows = self.connection.execute(f"SELECT * FROM cycles {where} ORDER BY start_date DESC,id DESC", values).fetchall()
        return [_cycle(row) for row in rows]

    def summaries(self, status: CycleStatus | None = None, search: str = "") -> list[CycleSummary]:
        cycles = self.list(status, search)
        if not cycles:
            return []
        ids = tuple(cycle.id for cycle in cycles)
        placeholders = ",".join("?" for _ in ids)
        outcome_counts = {
            row["cycle_id"]: row
            for row in self.connection.execute(
                f"""
                SELECT cycle_id,
                       SUM(CASE WHEN status='achieved' THEN 1 ELSE 0 END) AS achieved_count,
                       SUM(CASE WHEN status='partial' THEN 1 ELSE 0 END) AS partial_count,
                       SUM(CASE WHEN status='not_achieved' THEN 1 ELSE 0 END) AS not_achieved_count,
                       SUM(CASE WHEN status='planned' THEN 1 ELSE 0 END) AS planned_count
                FROM weekly_outcomes
                WHERE cycle_id IN ({placeholders})
                GROUP BY cycle_id
                """,
                ids,
            )
        }
        projects_by_cycle: dict[int, list[Project]] = {cycle_id: [] for cycle_id in ids}
        for row in self.connection.execute(
            f"""
            SELECT cp.cycle_id, p.*
            FROM cycle_projects cp
            JOIN projects p ON p.id=cp.project_id
            WHERE cp.cycle_id IN ({placeholders})
            ORDER BY cp.cycle_id, cp.position, p.id
            """,
            ids,
        ):
            projects_by_cycle[row["cycle_id"]].append(_project(row))
        milestone_by_cycle: dict[int, Milestone] = {}
        for row in self.connection.execute(
            f"""
            SELECT cm.cycle_id, m.*
            FROM cycle_milestones cm
            JOIN milestones m ON m.id=cm.milestone_id
            WHERE cm.cycle_id IN ({placeholders})
              AND m.status IN ('planned','in_progress')
            ORDER BY cm.cycle_id,
                     CASE m.status WHEN 'in_progress' THEN 0 ELSE 1 END,
                     cm.position,
                     m.id
            """,
            ids,
        ):
            milestone_by_cycle.setdefault(row["cycle_id"], _milestone(row))
        summaries: list[CycleSummary] = []
        for cycle in cycles:
            counts = outcome_counts.get(cycle.id)
            summaries.append(
                CycleSummary(
                    cycle=cycle,
                    achieved_count=int(counts["achieved_count"] or 0) if counts else 0,
                    partial_count=int(counts["partial_count"] or 0) if counts else 0,
                    not_achieved_count=int(counts["not_achieved_count"] or 0) if counts else 0,
                    planned_count=int(counts["planned_count"] or 0) if counts else 0,
                    projects=tuple(projects_by_cycle[cycle.id]),
                    next_milestone=milestone_by_cycle.get(cycle.id),
                )
            )
        return summaries

    def detail(self, cycle_id: int) -> CycleDetail | None:
        cycle = self.get(cycle_id)
        if not cycle:
            return None
        projects = [_project(row) for row in self.connection.execute(
            "SELECT p.* FROM projects p JOIN cycle_projects cp ON cp.project_id=p.id WHERE cp.cycle_id=? ORDER BY cp.position,p.id", (cycle_id,)
        )]
        milestones = [_milestone(row) for row in self.connection.execute(
            "SELECT m.* FROM milestones m JOIN cycle_milestones cm ON cm.milestone_id=m.id WHERE cm.cycle_id=? ORDER BY cm.position,m.id", (cycle_id,)
        )]
        task_ids = [row[0] for row in self.connection.execute(
            "SELECT task_id FROM cycle_tasks WHERE cycle_id=? AND disconnected_at IS NULL", (cycle_id,)
        )]
        all_tasks = self.tasks.list()
        tasks = tuple(item for item in all_tasks if item.task.id in task_ids)
        outcomes = tuple(_outcome(row) for row in self.connection.execute(
            "SELECT * FROM weekly_outcomes WHERE cycle_id=? ORDER BY week_number", (cycle_id,)
        ))
        return CycleDetail(cycle, tuple(projects), tuple(milestones), tasks, outcomes)

    def active(self) -> CycleDetail | None:
        row = self.connection.execute("SELECT id FROM cycles WHERE status='active' LIMIT 1").fetchone()
        return self.detail(row[0]) if row else None

    def change_status(self, cycle_id: int, status: CycleStatus) -> Cycle:
        current = self.get(cycle_id)
        if not current:
            raise ValueError(f"Cycle {cycle_id} does not exist.")
        completed = "completed_at=CURRENT_TIMESTAMP," if status is CycleStatus.COMPLETED else ""
        archived = "archived_at=CURRENT_TIMESTAMP," if status is CycleStatus.ARCHIVED else ""
        self.connection.execute(
            f"UPDATE cycles SET status=?, {completed}{archived} updated_at=CURRENT_TIMESTAMP WHERE id=?",
            (status.value, cycle_id),
        )
        return self.get(cycle_id)

    def connect_project(self, cycle_id: int, project_id: int) -> None:
        self.connection.execute(
            "INSERT OR IGNORE INTO cycle_projects (cycle_id,project_id,position) VALUES (?,?,COALESCE((SELECT MAX(position)+1 FROM cycle_projects WHERE cycle_id=?),1))",
            (cycle_id, project_id, cycle_id),
        )

    def connect_milestone(self, cycle_id: int, milestone_id: int) -> None:
        position = self.connection.execute(
            "SELECT COALESCE(MAX(position)+1,1) FROM cycle_milestones WHERE cycle_id=?",
            (cycle_id,),
        ).fetchone()[0]
        self.connection.execute(
            "INSERT OR IGNORE INTO cycle_milestones (cycle_id,milestone_id,position) VALUES (?,?,?)",
            (cycle_id, milestone_id, position),
        )

    def list_milestones(self) -> list[Milestone]:
        rows = self.connection.execute(
            "SELECT * FROM milestones ORDER BY project_id, position, id"
        ).fetchall()
        return [_milestone(row) for row in rows]

    def connect_task(self, cycle_id: int, task_id: int) -> None:
        active = self.connection.execute(
            "SELECT 1 FROM cycle_tasks WHERE cycle_id=? AND task_id=? AND disconnected_at IS NULL", (cycle_id, task_id)
        ).fetchone()
        if not active:
            self.connection.execute("INSERT INTO cycle_tasks (cycle_id,task_id) VALUES (?,?)", (cycle_id, task_id))

    def create_milestone(self, cycle_id: int, project_id: int, title: str, definition_of_done: str) -> Milestone:
        position = self.connection.execute(
            "SELECT COALESCE(MAX(position)+1,1) FROM milestones WHERE project_id=?", (project_id,)
        ).fetchone()[0]
        cursor = self.connection.execute(
            "INSERT INTO milestones (project_id,title,definition_of_done,position) VALUES (?,?,?,?)",
            (project_id, title, definition_of_done, position),
        )
        self.connection.execute(
            "INSERT INTO cycle_milestones (cycle_id,milestone_id,position) VALUES (?,?,?)",
            (cycle_id, cursor.lastrowid, position),
        )
        return _milestone(self.connection.execute("SELECT * FROM milestones WHERE id=?", (cursor.lastrowid,)).fetchone())

    def set_weekly_outcome(self, cycle_id: int, week_number: int, title: str, definition_of_done: str, status: str) -> WeeklyOutcome:
        self.connection.execute(
            """
            INSERT INTO weekly_outcomes (cycle_id,week_number,title,definition_of_done,status)
            VALUES (?,?,?,?,?)
            ON CONFLICT(cycle_id,week_number) DO UPDATE SET
                title=excluded.title, definition_of_done=excluded.definition_of_done,
                status=excluded.status, updated_at=CURRENT_TIMESTAMP,
                completed_at=CASE WHEN excluded.status='achieved' THEN CURRENT_TIMESTAMP ELSE NULL END
            """,
            (cycle_id, week_number, title, definition_of_done, status),
        )
        row = self.connection.execute(
            "SELECT * FROM weekly_outcomes WHERE cycle_id=? AND week_number=?", (cycle_id, week_number)
        ).fetchone()
        return _outcome(row)
