from __future__ import annotations

import importlib.util
import sqlite3
import sys


def main() -> int:
    requirements = {"flet": "0.84.0", "flet_desktop": "0.84.0"}
    failures: list[str] = []
    for module, expected in requirements.items():
        if importlib.util.find_spec(module) is None:
            failures.append(f"Missing module: {module}")
            continue
        loaded = __import__(module)
        actual = getattr(loaded, "__version__", None)
        if actual and actual != expected:
            failures.append(f"{module} is {actual}; expected {expected}")
    if sys.version_info < (3, 14):
        failures.append(f"Python 3.14+ is required; found {sys.version.split()[0]}")
    print(f"Python {sys.version.split()[0]}")
    print(f"SQLite {sqlite3.sqlite_version}")
    if failures:
        for failure in failures:
            print(f"ERROR: {failure}")
        return 1
    print("Environment smoke check passed (no database opened).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
