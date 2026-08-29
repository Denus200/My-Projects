import sqlite3
import unittest
import uuid
from contextlib import closing
from unittest.mock import patch
from pathlib import Path

from overlord.infrastructure.sqlite.connection import ConnectionFactory
from overlord.infrastructure.sqlite.migrations import (
    Migration,
    MigrationError,
    MigrationChecksumError,
    MigrationRunner,
    UnknownLegacySchemaError,
)

TEST_TEMP_ROOT = Path(__file__).resolve().parents[1] / "data" / "test-tmp"
TEST_TEMP_ROOT.mkdir(parents=True, exist_ok=True)


LEGACY_DDL = """
CREATE TABLE projects (
 id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL,
 description TEXT NOT NULL DEFAULT '', status TEXT NOT NULL DEFAULT 'active',
 created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE tasks (
 id INTEGER PRIMARY KEY AUTOINCREMENT, project_id INTEGER NOT NULL, title TEXT NOT NULL,
 description TEXT NOT NULL DEFAULT '', scheduled_date TEXT NOT NULL, planned_minutes INTEGER,
 status TEXT NOT NULL DEFAULT 'planned', comment TEXT NOT NULL DEFAULT '',
 created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
 FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE RESTRICT
);
CREATE INDEX idx_tasks_scheduled_date ON tasks(scheduled_date);
CREATE INDEX idx_tasks_project_id ON tasks(project_id);
"""


class FoundationMigrationTests(unittest.TestCase):
    def setUp(self):
        self.paths: list[Path] = []

    def database_path(self, label: str) -> Path:
        path = TEST_TEMP_ROOT / f"{label}-{uuid.uuid4().hex}.db"
        self.paths.append(path)
        return path

    def tearDown(self):
        for path in self.paths:
            path.unlink(missing_ok=True)

    def test_fresh_database_reaches_version_thirteen(self):
        path = self.database_path("fresh")
        result = MigrationRunner(ConnectionFactory(path)).migrate()
        self.assertEqual((1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13), result.applied)
        self.assertIsNone(result.backup)
        with closing(sqlite3.connect(path)) as connection:
            self.assertEqual(13, connection.execute("PRAGMA user_version").fetchone()[0])
            self.assertEqual("ok", connection.execute("PRAGMA integrity_check").fetchone()[0])
            self.assertEqual([], connection.execute("PRAGMA foreign_key_check").fetchall())
            self.assertEqual(1, connection.execute("SELECT COUNT(*) FROM settings").fetchone()[0])
            self.assertEqual("en", connection.execute("SELECT locale FROM settings WHERE id=1").fetchone()[0])
            task_columns = {row[1] for row in connection.execute("PRAGMA table_info(tasks)")}
            self.assertTrue({"schedule_start_date", "schedule_start_time", "schedule_end_date", "schedule_end_time", "deadline_at", "creation_mode", "total_time_minutes", "active_time_minutes"}.issubset(task_columns))
            self.assertIsNotNone(connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='task_day_positions'"
            ).fetchone())
            self.assertIsNotNone(connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='task_project_links'"
            ).fetchone())
            self.assertIsNotNone(connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='task_checklist_items'"
            ).fetchone())

    def test_exact_legacy_database_is_backed_up_and_preserved(self):
        path = self.database_path("legacy")
        connection = sqlite3.connect(path)
        connection.executescript(LEGACY_DDL)
        project_id = connection.execute("INSERT INTO projects(title) VALUES ('Keep me')").lastrowid
        task_id = connection.execute(
            "INSERT INTO tasks(project_id,title,scheduled_date,status) VALUES (?,?,?,?)",
            (project_id, "Keep task", "2026-08-06", "planned"),
        ).lastrowid
        connection.commit()
        connection.close()
        result = MigrationRunner(ConnectionFactory(path)).migrate()
        self.assertIsNotNone(result.backup)
        self.paths.extend((result.backup.database_path, result.backup.manifest_path))
        self.assertTrue(result.backup.database_path.exists())
        self.assertTrue(result.backup.manifest_path.exists())
        with closing(sqlite3.connect(path)) as migrated:
            self.assertEqual((project_id, "Keep me"), migrated.execute("SELECT id,title FROM projects").fetchone())
            self.assertEqual((task_id, "Keep task", "planned"), migrated.execute(
                "SELECT id,title,lifecycle_status FROM tasks"
            ).fetchone())
            self.assertEqual(("primary", 1), migrated.execute(
                "SELECT today_group,position FROM task_plans WHERE task_id=?", (task_id,)
            ).fetchone())
            self.assertEqual(("2026-08-06",), migrated.execute(
                "SELECT schedule_start_date FROM tasks WHERE id=?", (task_id,)
            ).fetchone())

    def test_already_current_database_is_idempotent(self):
        path = self.database_path("current")
        runner = MigrationRunner(ConnectionFactory(path))
        runner.migrate()
        second = runner.migrate()
        self.assertEqual((), second.applied)
        self.assertIsNone(second.backup)

    def test_unknown_version_zero_shape_is_refused(self):
        path = self.database_path("unknown")
        with closing(sqlite3.connect(path)) as connection:
            connection.execute("CREATE TABLE surprising(id INTEGER PRIMARY KEY)")
            connection.commit()
        with self.assertRaises(UnknownLegacySchemaError):
            MigrationRunner(ConnectionFactory(path)).migrate()

    def test_applied_checksum_drift_is_refused(self):
        path = self.database_path("tampered")
        runner = MigrationRunner(ConnectionFactory(path))
        runner.migrate()
        with closing(sqlite3.connect(path)) as connection:
            connection.execute("UPDATE schema_migrations SET checksum='tampered' WHERE version=3")
            connection.commit()
        with self.assertRaises(MigrationChecksumError):
            runner.migrate()

    def test_failed_migration_rolls_back_active_version(self):
        path = self.database_path("rollback")

        def fail_after_write(connection):
            connection.execute("CREATE TABLE should_rollback(id INTEGER PRIMARY KEY)")
            raise RuntimeError("simulated migration failure")

        bad = Migration(1, "simulated_failure", "failure-test-v1", fail_after_write)
        with patch("overlord.infrastructure.sqlite.migrations.MIGRATIONS", (bad,)):
            with self.assertRaises(MigrationError):
                MigrationRunner(ConnectionFactory(path)).migrate()
        with closing(sqlite3.connect(path)) as connection:
            self.assertEqual(0, connection.execute("PRAGMA user_version").fetchone()[0])
            self.assertIsNone(connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='should_rollback'"
            ).fetchone())

    def test_previous_version_advances_without_reapplying_history(self):
        path = self.database_path("previous")
        runner = MigrationRunner(ConnectionFactory(path))
        first = runner.migrate(target_version=4)
        self.assertEqual(4, first.to_version)
        final = runner.migrate()
        self.assertEqual((5, 6, 7, 8, 9, 10, 11, 12, 13), final.applied)
        self.assertIsNotNone(final.backup)
        self.paths.extend((final.backup.database_path, final.backup.manifest_path))

    def test_version_five_records_and_relationships_survive_nullable_project_migration(self):
        path = self.database_path("nullable-project")
        runner = MigrationRunner(ConnectionFactory(path))
        runner.migrate(target_version=5)
        with closing(sqlite3.connect(path)) as connection:
            connection.execute("PRAGMA foreign_keys=ON")
            project_id = connection.execute("INSERT INTO projects(title) VALUES ('Preserve me')").lastrowid
            task_id = connection.execute(
                "INSERT INTO tasks(project_id,title,scheduled_date,lifecycle_status) VALUES (?,?,?,'planned')",
                (project_id, "Preserve Task", "2026-08-07"),
            ).lastrowid
            plan_id = connection.execute(
                "INSERT INTO task_plans(task_id,planned_date,planned_week_start) VALUES (?,?,?)",
                (task_id, "2026-08-07", "2026-08-03"),
            ).lastrowid
            blocker_id = connection.execute(
                "INSERT INTO blockers(task_id,type,description) VALUES (?,'other','Preserve blocker')",
                (task_id,),
            ).lastrowid
            connection.commit()

        result = runner.migrate()
        self.assertEqual((6, 7, 8, 9, 10, 11, 12, 13), result.applied)
        self.assertIsNotNone(result.backup)
        self.paths.extend((result.backup.database_path, result.backup.manifest_path))
        with closing(sqlite3.connect(path)) as migrated:
            migrated.execute("PRAGMA foreign_keys=ON")
            project_column = next(row for row in migrated.execute("PRAGMA table_info(tasks)") if row[1] == "project_id")
            self.assertEqual(0, project_column[3])
            self.assertEqual((task_id, project_id, "Preserve Task"), migrated.execute(
                "SELECT id,project_id,title FROM tasks WHERE id=?", (task_id,)
            ).fetchone())
            self.assertEqual((plan_id, task_id), migrated.execute(
                "SELECT id,task_id FROM task_plans WHERE id=?", (plan_id,)
            ).fetchone())
            self.assertEqual((blocker_id, task_id), migrated.execute(
                "SELECT id,task_id FROM blockers WHERE id=?", (blocker_id,)
            ).fetchone())
            self.assertEqual([], migrated.execute("PRAGMA foreign_key_check").fetchall())

    def test_version_nine_legacy_project_link_is_preserved_in_normalized_table(self):
        path = self.database_path("project-links")
        runner = MigrationRunner(ConnectionFactory(path))
        runner.migrate(target_version=9)
        with closing(sqlite3.connect(path)) as connection:
            project_id = connection.execute("INSERT INTO projects(title) VALUES ('Titan')").lastrowid
            task_id = connection.execute(
                "INSERT INTO tasks(project_id,title,scheduled_date,lifecycle_status) VALUES (?,?,?,'planned')",
                (project_id, "Legacy linked Task", "2026-08-07"),
            ).lastrowid
            connection.commit()
        result = runner.migrate()
        self.assertEqual((10, 11, 12, 13), result.applied)
        self.paths.extend((result.backup.database_path, result.backup.manifest_path))
        with closing(sqlite3.connect(path)) as migrated:
            self.assertEqual(
                (task_id, project_id, None, 1),
                migrated.execute(
                    "SELECT task_id,project_id,stage_id,position FROM task_project_links"
                ).fetchone(),
            )
            self.assertEqual("ok", migrated.execute("PRAGMA integrity_check").fetchone()[0])
            self.assertEqual([], migrated.execute("PRAGMA foreign_key_check").fetchall())

    def test_version_ten_tasks_default_to_normal_creation_mode(self):
        path = self.database_path("create-task-flow")
        runner = MigrationRunner(ConnectionFactory(path))
        runner.migrate(target_version=10)
        with closing(sqlite3.connect(path)) as connection:
            task_id = connection.execute(
                "INSERT INTO tasks(title,scheduled_date,lifecycle_status) VALUES (?,?,?)",
                ("Existing Task", "2026-08-21", "planned"),
            ).lastrowid
            connection.commit()
        result = runner.migrate()
        self.assertEqual((11, 12, 13), result.applied)
        self.paths.extend((result.backup.database_path, result.backup.manifest_path))
        with closing(sqlite3.connect(path)) as migrated:
            self.assertEqual(
                (task_id, "normal"),
                migrated.execute("SELECT id,creation_mode FROM tasks WHERE id=?", (task_id,)).fetchone(),
            )
            self.assertEqual("ok", migrated.execute("PRAGMA integrity_check").fetchone()[0])
            self.assertEqual([], migrated.execute("PRAGMA foreign_key_check").fetchall())

    def test_version_eleven_task_details_migration_preserves_owned_relations(self):
        path = self.database_path("task-details-flow")
        runner = MigrationRunner(ConnectionFactory(path))
        runner.migrate(target_version=11)
        with closing(sqlite3.connect(path)) as connection:
            connection.execute("PRAGMA foreign_keys=ON")
            project_id = connection.execute("INSERT INTO projects(title) VALUES ('Titan')").lastrowid
            task_id = connection.execute(
                "INSERT INTO tasks(project_id,title,scheduled_date,lifecycle_status,creation_mode) VALUES (?,?,?,'in_progress','draft')",
                (project_id, "Preserve Details", "2026-08-21"),
            ).lastrowid
            connection.execute(
                "INSERT INTO task_project_links(task_id,project_id,position) VALUES (?,?,1)",
                (task_id, project_id),
            )
            checklist_id = connection.execute(
                "INSERT INTO task_checklist_items(task_id,title,position) VALUES (?,?,0)",
                (task_id, "Preserve checklist"),
            ).lastrowid
            blocker_id = connection.execute(
                "INSERT INTO blockers(task_id,type,description) VALUES (?,'other','Preserve blocker')",
                (task_id,),
            ).lastrowid
            connection.commit()

        result = runner.migrate()
        self.assertEqual((12, 13), result.applied)
        self.paths.extend((result.backup.database_path, result.backup.manifest_path))
        with closing(sqlite3.connect(path)) as migrated:
            migrated.execute("PRAGMA foreign_keys=ON")
            self.assertEqual(
                (task_id, "in_progress", "draft"),
                migrated.execute(
                    "SELECT id,lifecycle_status,creation_mode FROM tasks WHERE id=?", (task_id,)
                ).fetchone(),
            )
            self.assertEqual((checklist_id, task_id), migrated.execute(
                "SELECT id,task_id FROM task_checklist_items WHERE id=?", (checklist_id,)
            ).fetchone())
            self.assertEqual((blocker_id, task_id), migrated.execute(
                "SELECT id,task_id FROM blockers WHERE id=?", (blocker_id,)
            ).fetchone())
            migrated.execute("UPDATE tasks SET lifecycle_status='paused' WHERE id=?", (task_id,))
            self.assertEqual("paused", migrated.execute(
                "SELECT lifecycle_status FROM tasks WHERE id=?", (task_id,)
            ).fetchone()[0])
            self.assertEqual([], migrated.execute("PRAGMA foreign_key_check").fetchall())

    def test_version_twelve_complete_task_migration_preserves_task_relations(self):
        path = self.database_path("complete-task-flow")
        runner = MigrationRunner(ConnectionFactory(path))
        runner.migrate(target_version=12)
        with closing(sqlite3.connect(path)) as connection:
            connection.execute("PRAGMA foreign_keys=ON")
            project_id = connection.execute("INSERT INTO projects(title) VALUES ('Titan')").lastrowid
            task_id = connection.execute(
                "INSERT INTO tasks(project_id,title,scheduled_date,lifecycle_status,planned_minutes) VALUES (?,?,?,'paused',?)",
                (project_id, "Preserve Completion", "2026-08-21", 244),
            ).lastrowid
            connection.execute(
                "INSERT INTO task_project_links(task_id,project_id,position) VALUES (?,?,1)",
                (task_id, project_id),
            )
            checklist_id = connection.execute(
                "INSERT INTO task_checklist_items(task_id,title,position) VALUES (?,?,0)",
                (task_id, "Preserve checklist"),
            ).lastrowid
            connection.commit()

        result = runner.migrate()
        self.assertEqual((13,), result.applied)
        self.paths.extend((result.backup.database_path, result.backup.manifest_path))
        with closing(sqlite3.connect(path)) as migrated:
            self.assertEqual(
                (task_id, "paused", 244, None, None),
                migrated.execute(
                    "SELECT id,lifecycle_status,planned_minutes,total_time_minutes,active_time_minutes FROM tasks WHERE id=?",
                    (task_id,),
                ).fetchone(),
            )
            self.assertEqual((task_id, project_id), migrated.execute(
                "SELECT task_id,project_id FROM task_project_links WHERE task_id=?", (task_id,)
            ).fetchone())
            self.assertEqual((checklist_id, task_id), migrated.execute(
                "SELECT id,task_id FROM task_checklist_items WHERE id=?", (checklist_id,)
            ).fetchone())
            self.assertEqual("ok", migrated.execute("PRAGMA integrity_check").fetchone()[0])
            self.assertEqual([], migrated.execute("PRAGMA foreign_key_check").fetchall())


if __name__ == "__main__":
    unittest.main()
