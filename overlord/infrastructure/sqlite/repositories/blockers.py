from __future__ import annotations

import sqlite3

from overlord.modules.blockers.domain import Blocker, BlockerType

from .mappers import _blocker


class SqliteBlockerRepository:
    def __init__(self, connection: sqlite3.Connection):
        self.connection = connection

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
