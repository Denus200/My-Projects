from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
import sys
import uuid
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from overlord.infrastructure.sqlite.connection import ConnectionFactory
from overlord.infrastructure.sqlite.migrations import MigrationRunner


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(128 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def main() -> int:
    parser = argparse.ArgumentParser(description="Migrate and validate a disposable SQLite backup")
    parser.add_argument("source", type=Path)
    args = parser.parse_args()
    source_path = args.source.resolve()
    temp_root = Path(__file__).resolve().parents[1] / "data" / "test-tmp"
    temp_root.mkdir(parents=True, exist_ok=True)
    target_path = temp_root / f"migration-smoke-{uuid.uuid4().hex}.db"
    source = sqlite3.connect(f"file:{source_path.as_posix()}?mode=ro", uri=True)
    target = sqlite3.connect(target_path)
    try:
        source.row_factory = sqlite3.Row
        before_projects = [tuple(row) for row in source.execute(
            "SELECT id,title,description,status,created_at,updated_at FROM projects ORDER BY id"
        )]
        before_tasks = [tuple(row) for row in source.execute(
            "SELECT id,project_id,title,description,scheduled_date,planned_minutes,status,comment,created_at,updated_at FROM tasks ORDER BY id"
        )]
        source.backup(target)
    finally:
        target.close()
        source.close()
    result = None
    try:
        result = MigrationRunner(ConnectionFactory(target_path)).migrate()
        migrated = sqlite3.connect(target_path)
        try:
            after_projects = migrated.execute(
                "SELECT id,title,description,status,created_at,updated_at FROM projects ORDER BY id"
            ).fetchall()
            after_tasks = migrated.execute(
                "SELECT id,project_id,title,description,scheduled_date,planned_minutes,status,comment,created_at,updated_at FROM tasks ORDER BY id"
            ).fetchall()
            evidence = {
                "source_sha256": sha256(source_path),
                "source_user_version": 0,
                "migrated_user_version": migrated.execute("PRAGMA user_version").fetchone()[0],
                "applied": list(result.applied),
                "project_rows_preserved": before_projects == after_projects,
                "task_rows_preserved": before_tasks == after_tasks,
                "integrity_check": migrated.execute("PRAGMA integrity_check").fetchone()[0],
                "foreign_key_violations": len(migrated.execute("PRAGMA foreign_key_check").fetchall()),
                "validated_pre_migration_backup": bool(result.backup),
            }
        finally:
            migrated.close()
        if not all((
            evidence["project_rows_preserved"], evidence["task_rows_preserved"],
            evidence["integrity_check"] == "ok", evidence["foreign_key_violations"] == 0,
            evidence["migrated_user_version"] == 5, evidence["validated_pre_migration_backup"],
        )):
            raise RuntimeError("Disposable production-copy migration validation failed.")
        print(json.dumps(evidence, indent=2))
        return 0
    finally:
        target_path.unlink(missing_ok=True)
        if result and result.backup:
            result.backup.database_path.unlink(missing_ok=True)
            result.backup.manifest_path.unlink(missing_ok=True)


if __name__ == "__main__":
    raise SystemExit(main())
