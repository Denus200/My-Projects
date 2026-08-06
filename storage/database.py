import sqlite3
from pathlib import Path


DEFAULT_DATABASE_PATH = Path(__file__).resolve().parents[1] / "data" / "overlord.db"


def connect_database(path: str | Path = DEFAULT_DATABASE_PATH) -> sqlite3.Connection:
    database_path = Path(path)
    database_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(database_path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def initialize_database(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL DEFAULT 'active',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            description TEXT NOT NULL DEFAULT '',
            scheduled_date TEXT NOT NULL,
            planned_minutes INTEGER,
            status TEXT NOT NULL DEFAULT 'planned',
            comment TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE RESTRICT
        );

        CREATE INDEX IF NOT EXISTS idx_tasks_scheduled_date ON tasks(scheduled_date);
        CREATE INDEX IF NOT EXISTS idx_tasks_project_id ON tasks(project_id);
        """
    )
    connection.commit()
