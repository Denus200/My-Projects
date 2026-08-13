from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Callable

from overlord import __version__

from .connection import ConnectionFactory


class MigrationError(RuntimeError):
    pass


class UnknownLegacySchemaError(MigrationError):
    pass


class MigrationChecksumError(MigrationError):
    pass


MigrationAction = Callable[[sqlite3.Connection], None]


@dataclass(frozen=True, slots=True)
class Migration:
    version: int
    name: str
    signature: str
    action: MigrationAction
    requires_foreign_keys_off: bool = False

    @property
    def checksum(self) -> str:
        material = f"{self.version}:{self.name}:{self.signature}".encode()
        return hashlib.sha256(material).hexdigest()


@dataclass(frozen=True, slots=True)
class BackupEvidence:
    database_path: Path
    manifest_path: Path
    source_hash: str
    backup_hash: str
    from_version: int
    to_version: int


@dataclass(frozen=True, slots=True)
class MigrationResult:
    from_version: int
    to_version: int
    applied: tuple[int, ...]
    backup: BackupEvidence | None


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(128 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def _tables(connection: sqlite3.Connection) -> set[str]:
    return {
        row[0]
        for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        )
    }


def _columns(connection: sqlite3.Connection, table: str) -> list[str]:
    return [row[1] for row in connection.execute(f"PRAGMA table_info({table})")]


LEGACY_COLUMNS = {
    "projects": ["id", "title", "description", "status", "created_at", "updated_at"],
    "tasks": [
        "id",
        "project_id",
        "title",
        "description",
        "scheduled_date",
        "planned_minutes",
        "status",
        "comment",
        "created_at",
        "updated_at",
    ],
}


def _validate_legacy_or_empty(connection: sqlite3.Connection) -> bool:
    tables = _tables(connection)
    if not tables:
        return False
    if tables != {"projects", "tasks"}:
        raise UnknownLegacySchemaError(
            f"Unrecognized version-0 tables: {', '.join(sorted(tables))}."
        )
    for table, expected in LEGACY_COLUMNS.items():
        info = connection.execute(f"PRAGMA table_info({table})").fetchall()
        actual = [row[1] for row in info]
        if actual != expected:
            raise UnknownLegacySchemaError(
                f"Unrecognized version-0 columns for {table}: {actual!r}."
            )
        if info[0][5] != 1 or info[0][1] != "id":
            raise UnknownLegacySchemaError(f"The legacy {table} primary key is not recognized.")
    project_required = {"title", "description", "status", "created_at", "updated_at"}
    task_required = {"project_id", "title", "description", "scheduled_date", "status", "comment", "created_at", "updated_at"}
    for table, required in (("projects", project_required), ("tasks", task_required)):
        not_null = {row[1] for row in connection.execute(f"PRAGMA table_info({table})") if row[3] == 1}
        if not required.issubset(not_null):
            raise UnknownLegacySchemaError(f"The legacy {table} nullability is not recognized.")
    foreign_keys = connection.execute("PRAGMA foreign_key_list(tasks)").fetchall()
    if len(foreign_keys) != 1 or foreign_keys[0][2:7] != ("projects", "project_id", "id", "NO ACTION", "RESTRICT"):
        raise UnknownLegacySchemaError("The legacy Task-to-Project foreign key is not recognized.")
    indexes = {
        row[0]
        for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND name NOT LIKE 'sqlite_%'"
        )
    }
    required = {"idx_tasks_scheduled_date", "idx_tasks_project_id"}
    if not required.issubset(indexes):
        raise UnknownLegacySchemaError("The legacy Task indexes do not match the supported baseline.")
    return True


def _create_ledger(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            checksum TEXT NOT NULL,
            applied_at TEXT NOT NULL,
            application_version TEXT NOT NULL
        )
        """
    )


def _migration_0001(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL DEFAULT 'active',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    connection.execute(
        """
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
        )
        """
    )
    connection.execute("CREATE INDEX IF NOT EXISTS idx_tasks_scheduled_date ON tasks(scheduled_date)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_tasks_project_id ON tasks(project_id)")
    _create_ledger(connection)


def _migration_0002(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE settings (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            theme_mode TEXT NOT NULL DEFAULT 'system' CHECK (theme_mode IN ('system','light','dark')),
            motion_enabled INTEGER NOT NULL DEFAULT 1 CHECK (motion_enabled IN (0,1)),
            reduced_motion INTEGER NOT NULL DEFAULT 0 CHECK (reduced_motion IN (0,1)),
            first_day_of_week TEXT NOT NULL DEFAULT 'monday' CHECK (first_day_of_week IN ('monday','sunday')),
            default_cycle_length INTEGER NOT NULL DEFAULT 12 CHECK (default_cycle_length BETWEEN 1 AND 52),
            startup_destination TEXT NOT NULL DEFAULT 'dashboard' CHECK (startup_destination IN ('dashboard','tasks','projects','cycles')),
            sidebar_collapsed INTEGER NOT NULL DEFAULT 0 CHECK (sidebar_collapsed IN (0,1)),
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    connection.execute("INSERT INTO settings (id) VALUES (1)")


def _add_column(connection: sqlite3.Connection, table: str, definition: str) -> None:
    name = definition.split()[0]
    if name not in _columns(connection, table):
        connection.execute(f"ALTER TABLE {table} ADD COLUMN {definition}")


def _migration_0003(connection: sqlite3.Connection) -> None:
    additions = (
        "lifecycle_status TEXT CHECK (lifecycle_status IN ('backlog','planned','in_progress','completed','cancelled'))",
        "definition_of_done TEXT",
        "next_action TEXT",
        "importance INTEGER CHECK (importance IN (0,1))",
        "urgency INTEGER CHECK (urgency IN (0,1))",
        "started_at TEXT",
        "completed_at TEXT",
        "archived_at TEXT",
    )
    for definition in additions:
        _add_column(connection, "tasks", definition)
    connection.execute(
        "UPDATE tasks SET lifecycle_status = CASE status WHEN 'planned' THEN 'planned' WHEN 'done' THEN 'completed' ELSE NULL END WHERE lifecycle_status IS NULL"
    )
    connection.execute(
        """
        CREATE TABLE task_plans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id INTEGER NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
            planned_date TEXT NOT NULL,
            planned_week_start TEXT NOT NULL,
            today_group TEXT CHECK (today_group IN ('primary','secondary')),
            position INTEGER,
            supersedes_plan_id INTEGER REFERENCES task_plans(id) ON DELETE RESTRICT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            ended_at TEXT,
            CHECK ((today_group IS NULL AND position IS NULL) OR
                   (today_group = 'primary' AND position BETWEEN 1 AND 3) OR
                   (today_group = 'secondary' AND position BETWEEN 1 AND 4))
        )
        """
    )
    connection.execute(
        "CREATE UNIQUE INDEX ux_task_plans_current_task ON task_plans(task_id) WHERE ended_at IS NULL"
    )
    connection.execute(
        "CREATE UNIQUE INDEX ux_task_plans_current_slot ON task_plans(planned_date, today_group, position) WHERE ended_at IS NULL AND today_group IS NOT NULL"
    )
    connection.execute("CREATE INDEX idx_task_plans_week ON task_plans(planned_week_start, ended_at)")
    connection.execute(
        """
        WITH ranked AS (
            SELECT id, scheduled_date, created_at,
                   ROW_NUMBER() OVER (PARTITION BY scheduled_date ORDER BY created_at, id) AS slot_rank
            FROM tasks
        )
        INSERT INTO task_plans (
            task_id, planned_date, planned_week_start, today_group, position, created_at
        )
        SELECT id,
               scheduled_date,
               date(scheduled_date, '-' || ((CAST(strftime('%w', scheduled_date) AS INTEGER) + 6) % 7) || ' days'),
               CASE WHEN slot_rank <= 3 THEN 'primary' WHEN slot_rank <= 7 THEN 'secondary' ELSE NULL END,
               CASE WHEN slot_rank <= 3 THEN slot_rank WHEN slot_rank <= 7 THEN slot_rank - 3 ELSE NULL END,
               created_at
        FROM ranked
        """
    )
    connection.execute(
        """
        CREATE TABLE task_status_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id INTEGER NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
            from_status TEXT,
            to_status TEXT NOT NULL,
            reason TEXT,
            changed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    connection.execute("CREATE INDEX idx_task_status_history_task ON task_status_history(task_id, changed_at)")
    connection.execute(
        """
        CREATE TABLE blockers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id INTEGER NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
            type TEXT NOT NULL CHECK (type IN ('dependency','decision','resource','clarity','technical','other')),
            description TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            resolved_at TEXT,
            resolution TEXT
        )
        """
    )
    connection.execute("CREATE INDEX idx_blockers_task ON blockers(task_id, resolved_at)")
    connection.execute("CREATE INDEX idx_blockers_open ON blockers(task_id) WHERE resolved_at IS NULL")
    connection.execute("CREATE INDEX idx_tasks_lifecycle_completed ON tasks(lifecycle_status, completed_at)")
    connection.execute("CREATE INDEX idx_tasks_project_lifecycle ON tasks(project_id, lifecycle_status, updated_at)")


def _migration_0004(connection: sqlite3.Connection) -> None:
    for definition in (
        "stage_label TEXT",
        "started_at TEXT",
        "completed_at TEXT",
        "archived_at TEXT",
    ):
        _add_column(connection, "projects", definition)
    connection.execute("CREATE INDEX idx_projects_status_updated ON projects(status, updated_at DESC)")


def _migration_0005(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE cycles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            main_outcome TEXT NOT NULL,
            start_date TEXT NOT NULL,
            length_weeks INTEGER NOT NULL CHECK (length_weeks BETWEEN 1 AND 52),
            end_date TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'draft' CHECK (status IN ('draft','active','completed','archived')),
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            completed_at TEXT,
            archived_at TEXT
        )
        """
    )
    connection.execute("CREATE INDEX idx_cycles_status_start ON cycles(status, start_date DESC)")
    connection.execute("CREATE INDEX idx_cycles_title ON cycles(title)")
    connection.execute("CREATE UNIQUE INDEX ux_cycles_one_active ON cycles(status) WHERE status = 'active'")
    connection.execute(
        """
        CREATE TABLE milestones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE RESTRICT,
            title TEXT NOT NULL,
            definition_of_done TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'planned' CHECK (status IN ('planned','in_progress','completed','cancelled')),
            target_date TEXT,
            position INTEGER NOT NULL DEFAULT 1,
            started_at TEXT,
            completed_at TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    connection.execute("CREATE INDEX idx_milestones_project_status ON milestones(project_id, status, position)")
    _add_column(connection, "tasks", "milestone_id INTEGER REFERENCES milestones(id) ON DELETE SET NULL")
    connection.execute("CREATE INDEX idx_tasks_milestone_lifecycle ON tasks(milestone_id, lifecycle_status)")
    connection.execute(
        """
        CREATE TABLE cycle_projects (
            cycle_id INTEGER NOT NULL REFERENCES cycles(id) ON DELETE CASCADE,
            project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE RESTRICT,
            position INTEGER NOT NULL DEFAULT 1,
            connected_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (cycle_id, project_id)
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE cycle_milestones (
            cycle_id INTEGER NOT NULL REFERENCES cycles(id) ON DELETE CASCADE,
            milestone_id INTEGER NOT NULL REFERENCES milestones(id) ON DELETE RESTRICT,
            position INTEGER NOT NULL DEFAULT 1,
            connected_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (cycle_id, milestone_id)
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE cycle_tasks (
            cycle_id INTEGER NOT NULL REFERENCES cycles(id) ON DELETE CASCADE,
            task_id INTEGER NOT NULL REFERENCES tasks(id) ON DELETE RESTRICT,
            connected_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            disconnected_at TEXT,
            PRIMARY KEY (cycle_id, task_id, connected_at)
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE weekly_outcomes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cycle_id INTEGER NOT NULL REFERENCES cycles(id) ON DELETE CASCADE,
            week_number INTEGER NOT NULL CHECK (week_number BETWEEN 1 AND 52),
            title TEXT NOT NULL,
            definition_of_done TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'planned' CHECK (status IN ('planned','achieved','partial','not_achieved')),
            completed_at TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (cycle_id, week_number)
        )
        """
    )
    connection.execute("CREATE INDEX idx_cycle_tasks_open ON cycle_tasks(cycle_id, disconnected_at)")


def _migration_0006(connection: sqlite3.Connection) -> None:
    """Allow a Task to exist independently of a Project.

    SQLite cannot remove a NOT NULL constraint in place. Rebuild only the
    parent table while deferring child foreign-key checks until the replacement
    table has the canonical ``tasks`` name again.
    """
    connection.execute(
        """
        CREATE TABLE tasks_u2 (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER,
            title TEXT NOT NULL,
            description TEXT NOT NULL DEFAULT '',
            scheduled_date TEXT NOT NULL,
            planned_minutes INTEGER,
            status TEXT NOT NULL DEFAULT 'planned',
            comment TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            lifecycle_status TEXT CHECK (lifecycle_status IN ('backlog','planned','in_progress','completed','cancelled')),
            definition_of_done TEXT,
            next_action TEXT,
            importance INTEGER CHECK (importance IN (0,1)),
            urgency INTEGER CHECK (urgency IN (0,1)),
            started_at TEXT,
            completed_at TEXT,
            archived_at TEXT,
            milestone_id INTEGER REFERENCES milestones(id) ON DELETE SET NULL,
            FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE RESTRICT
        )
        """
    )
    connection.execute(
        """
        INSERT INTO tasks_u2 (
            id, project_id, title, description, scheduled_date, planned_minutes,
            status, comment, created_at, updated_at, lifecycle_status,
            definition_of_done, next_action, importance, urgency, started_at,
            completed_at, archived_at, milestone_id
        )
        SELECT id, project_id, title, description, scheduled_date, planned_minutes,
               status, comment, created_at, updated_at, lifecycle_status,
               definition_of_done, next_action, importance, urgency, started_at,
               completed_at, archived_at, milestone_id
        FROM tasks
        """
    )
    connection.execute("DROP TABLE tasks")
    connection.execute("ALTER TABLE tasks_u2 RENAME TO tasks")
    connection.execute("CREATE INDEX idx_tasks_scheduled_date ON tasks(scheduled_date)")
    connection.execute("CREATE INDEX idx_tasks_project_id ON tasks(project_id)")
    connection.execute("CREATE INDEX idx_tasks_lifecycle_completed ON tasks(lifecycle_status, completed_at)")
    connection.execute("CREATE INDEX idx_tasks_project_lifecycle ON tasks(project_id, lifecycle_status, updated_at)")
    connection.execute("CREATE INDEX idx_tasks_milestone_lifecycle ON tasks(milestone_id, lifecycle_status)")


def _migration_0007(connection: sqlite3.Connection) -> None:
    _add_column(
        connection,
        "settings",
        "locale TEXT NOT NULL DEFAULT 'en' CHECK (locale IN ('en','ru'))",
    )


def _migration_0008(connection: sqlite3.Connection) -> None:
    """Make Task scheduling date-driven and preserve legacy slot history.

    ``task_plans`` remains immutable historical evidence, but current product
    behavior reads the canonical schedule directly from ``tasks``.
    """
    for definition in (
        "schedule_start_date TEXT",
        "schedule_start_time TEXT",
        "schedule_end_date TEXT",
        "schedule_end_time TEXT",
        "deadline_at TEXT",
    ):
        _add_column(connection, "tasks", definition)
    connection.execute(
        """
        UPDATE tasks
        SET schedule_start_date = (
            SELECT planned_date
            FROM task_plans
            WHERE task_plans.task_id = tasks.id AND task_plans.ended_at IS NULL
        )
        WHERE schedule_start_date IS NULL
          AND EXISTS (
              SELECT 1 FROM task_plans
              WHERE task_plans.task_id = tasks.id AND task_plans.ended_at IS NULL
          )
        """
    )
    connection.execute(
        "CREATE INDEX idx_tasks_schedule_start ON tasks(schedule_start_date, lifecycle_status)"
    )
    connection.execute(
        "CREATE INDEX idx_tasks_schedule_end ON tasks(schedule_end_date, lifecycle_status)"
    )
    connection.execute(
        "CREATE INDEX idx_tasks_deadline ON tasks(deadline_at, lifecycle_status)"
    )


def _migration_0009(connection: sqlite3.Connection) -> None:
    """Persist explicit task ordering independently for each scheduled day."""
    connection.execute(
        """
        CREATE TABLE task_day_positions (
            task_id INTEGER NOT NULL,
            day TEXT NOT NULL,
            position INTEGER NOT NULL CHECK (position >= 0),
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (day, task_id),
            FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE
        )
        """
    )
    connection.execute(
        "CREATE INDEX idx_task_day_positions_order ON task_day_positions(day, position)"
    )


MIGRATIONS = (
    Migration(1, "baseline", "legacy-project-task-schema-v1", _migration_0001),
    Migration(2, "settings", "typed-singleton-settings-v1", _migration_0002),
    Migration(3, "task_planning_attention", "canonical-task-plan-history-blockers-v2", _migration_0003),
    Migration(4, "project_task_workflows", "project-stage-timestamps-indexes-v1", _migration_0004),
    Migration(5, "cycles_milestones_outcomes", "cycle-junction-weekly-outcome-v1", _migration_0005),
    Migration(
        6,
        "standalone_tasks",
        "nullable-task-project-preserve-all-records-v1",
        _migration_0006,
        requires_foreign_keys_off=True,
    ),
    Migration(7, "interface_locale", "persistent-en-ru-interface-locale-v1", _migration_0007),
    Migration(
        8,
        "date_driven_tasks",
        "canonical-task-schedule-preserve-legacy-plans-v1",
        _migration_0008,
    ),
    Migration(
        9,
        "task_day_ordering",
        "persistent-task-position-per-scheduled-day-v1",
        _migration_0009,
    ),
)


def _backup_database(database_path: Path, from_version: int, to_version: int) -> BackupEvidence:
    backup_directory = database_path.parent / "backups"
    backup_directory.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    backup_path = backup_directory / f"overlord-v{from_version}-{stamp}.db"
    suffix = 1
    while backup_path.exists():
        backup_path = backup_directory / f"overlord-v{from_version}-{stamp}-{suffix}.db"
        suffix += 1
    source_hash = _sha256(database_path)
    source = sqlite3.connect(f"file:{database_path.as_posix()}?mode=ro", uri=True)
    destination = sqlite3.connect(backup_path)
    try:
        source.backup(destination)
    finally:
        destination.close()
        source.close()
    verify = sqlite3.connect(backup_path)
    try:
        integrity = verify.execute("PRAGMA integrity_check").fetchone()[0]
        foreign_keys = verify.execute("PRAGMA foreign_key_check").fetchall()
    finally:
        verify.close()
    if integrity != "ok" or foreign_keys:
        backup_path.unlink(missing_ok=True)
        raise MigrationError("The pre-migration backup failed validation.")
    backup_hash = _sha256(backup_path)
    manifest_path = backup_path.with_suffix(".manifest.json")
    manifest = {
        "source_path": str(database_path),
        "backup_path": str(backup_path),
        "source_sha256": source_hash,
        "backup_sha256": backup_hash,
        "source_size": database_path.stat().st_size,
        "backup_size": backup_path.stat().st_size,
        "from_version": from_version,
        "to_version": to_version,
        "created_at": datetime.now(UTC).isoformat(),
    }
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return BackupEvidence(
        backup_path, manifest_path, source_hash, backup_hash, from_version, to_version
    )


class MigrationRunner:
    def __init__(self, factory: ConnectionFactory):
        self.factory = factory

    def migrate(self, target_version: int | None = None) -> MigrationResult:
        target = target_version if target_version is not None else MIGRATIONS[-1].version
        selected = tuple(migration for migration in MIGRATIONS if migration.version <= target)
        if not selected or target != selected[-1].version:
            raise MigrationError(f"Unsupported target migration version {target}.")
        database_existed = self.factory.database_path.exists() and self.factory.database_path.stat().st_size > 0
        with self.factory.open() as connection:
            from_version = int(connection.execute("PRAGMA user_version").fetchone()[0])
            tables = _tables(connection)
            if from_version == 0:
                has_legacy_data = _validate_legacy_or_empty(connection)
            else:
                has_legacy_data = False
                if "schema_migrations" not in tables:
                    raise MigrationError("A versioned database is missing its migration ledger.")
            if from_version > target:
                raise MigrationError(
                    f"Database version {from_version} is newer than supported version {target}."
                )
            applied_rows = {}
            if "schema_migrations" in tables:
                applied_rows = {
                    row["version"]: row
                    for row in connection.execute("SELECT * FROM schema_migrations")
                }
            for migration in selected:
                row = applied_rows.get(migration.version)
                if row and row["checksum"] != migration.checksum:
                    raise MigrationChecksumError(
                        f"Migration {migration.version:04d} checksum differs from the bundled migration."
                    )
            pending = tuple(m for m in selected if m.version > from_version)
        backup = None
        if pending and database_existed and (has_legacy_data or from_version > 0):
            backup = _backup_database(self.factory.database_path, from_version, target)
        applied: list[int] = []
        with self.factory.open() as connection:
            for migration in pending:
                foreign_keys_disabled = migration.requires_foreign_keys_off
                try:
                    if foreign_keys_disabled:
                        connection.execute("PRAGMA foreign_keys = OFF")
                    connection.execute("BEGIN IMMEDIATE")
                    migration.action(connection)
                    _create_ledger(connection)
                    connection.execute(
                        """
                        INSERT INTO schema_migrations (version, name, checksum, applied_at, application_version)
                        VALUES (?, ?, ?, ?, ?)
                        """,
                        (
                            migration.version,
                            migration.name,
                            migration.checksum,
                            datetime.now(UTC).isoformat(),
                            __version__,
                        ),
                    )
                    connection.execute(f"PRAGMA user_version = {migration.version}")
                    connection.commit()
                    applied.append(migration.version)
                except Exception as error:
                    connection.rollback()
                    raise MigrationError(
                        f"Migration {migration.version:04d}_{migration.name} failed."
                    ) from error
                finally:
                    if foreign_keys_disabled:
                        connection.execute("PRAGMA foreign_keys = ON")
            integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
            foreign_keys = connection.execute("PRAGMA foreign_key_check").fetchall()
            if integrity != "ok" or foreign_keys:
                raise MigrationError("Post-migration database validation failed.")
            final_version = int(connection.execute("PRAGMA user_version").fetchone()[0])
        return MigrationResult(from_version, final_version, tuple(applied), backup)
