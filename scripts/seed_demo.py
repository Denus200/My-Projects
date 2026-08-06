from __future__ import annotations

import sys
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT))

from overlord.demo import seed_demo_database


def main() -> int:
    summary = seed_demo_database(reset=True)
    print(f"Demo database: {summary.database_path}")
    print(f"Projects: {summary.project_count}")
    print(f"Tasks: {summary.task_count}")
    print(f"Today: {summary.primary_count} Primary, {summary.secondary_count} Secondary")
    print(f"Active Cycle: {summary.cycle_title}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
