from __future__ import annotations

import sqlite3
from datetime import date

from overlord.modules.cycles.domain import (
    Cycle,
    CycleStatus,
    Milestone,
    WeeklyOutcome,
    cycle_end_date,
)
from overlord.modules.cycles.read_models import CycleDetail, CycleSummary
from overlord.modules.cycles.repository import TaskListReader
from overlord.modules.projects.domain import Project

from .mappers import _cycle, _milestone, _outcome, _project


class SqliteCycleRepository:
    def __init__(self, connection: sqlite3.Connection, tasks: TaskListReader):
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

    def cycle_ids_for_task(self, task_id: int) -> tuple[int, ...]:
        return tuple(
            row[0]
            for row in self.connection.execute(
                "SELECT cycle_id FROM cycle_tasks WHERE task_id=? AND disconnected_at IS NULL ORDER BY cycle_id",
                (task_id,),
            )
        )

    def replace_task_cycles(self, task_id: int, cycle_ids: tuple[int, ...]) -> None:
        selected = tuple(dict.fromkeys(cycle_ids))
        if selected:
            placeholders = ",".join("?" for _ in selected)
            self.connection.execute(
                f"""
                UPDATE cycle_tasks
                SET disconnected_at=CURRENT_TIMESTAMP
                WHERE task_id=? AND disconnected_at IS NULL
                  AND cycle_id NOT IN ({placeholders})
                  AND cycle_id IN (SELECT id FROM cycles WHERE status!='archived')
                """,
                (task_id, *selected),
            )
        else:
            self.connection.execute(
                """
                UPDATE cycle_tasks
                SET disconnected_at=CURRENT_TIMESTAMP
                WHERE task_id=? AND disconnected_at IS NULL
                  AND cycle_id IN (SELECT id FROM cycles WHERE status!='archived')
                """,
                (task_id,),
            )
        for cycle_id in selected:
            self.connect_task(cycle_id, task_id)

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
