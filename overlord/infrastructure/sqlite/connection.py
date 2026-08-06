from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator


class ConnectionFactory:
    def __init__(self, database_path: str | Path, *, busy_timeout_ms: int = 3_000):
        self.database_path = Path(database_path).resolve()
        self.busy_timeout_ms = busy_timeout_ms

    @contextmanager
    def open(self, *, read_only: bool = False) -> Iterator[sqlite3.Connection]:
        if not read_only:
            self.database_path.parent.mkdir(parents=True, exist_ok=True)
            connection = sqlite3.connect(self.database_path, timeout=self.busy_timeout_ms / 1000)
        else:
            uri = f"file:{self.database_path.as_posix()}?mode=ro"
            connection = sqlite3.connect(uri, uri=True, timeout=self.busy_timeout_ms / 1000)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute(f"PRAGMA busy_timeout = {int(self.busy_timeout_ms)}")
        if read_only:
            connection.execute("PRAGMA query_only = ON")
        try:
            yield connection
        finally:
            connection.close()
