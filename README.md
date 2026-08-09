# Overlord

Local-first Windows planning software built with Python, Flet, and SQLite.

## Setup (PowerShell)

```powershell
py -3.14 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

## Run and test

```powershell
python main.py
python -B -m unittest discover -s tests -v
python -B scripts/smoke_environment.py
python -B scripts/migration_smoke_copy.py data/overlord.db
```

Overlord is desktop-only. Web/browser launch support has been retired; `--web` and `--port` are intentionally rejected. For realistic evaluation without touching user data, run `python main.py --demo`.

The application migrates its database at startup. Before every schema-changing batch it creates and validates a backup in `data/backups`. Tests always use disposable databases.

## Read-only database diagnostics

```powershell
python -B scripts/db_diagnostics.py data/overlord.db
```

This command opens SQLite with `mode=ro`; it does not initialize or migrate the database.

`migration_smoke_copy.py` uses SQLite's backup API to migrate a disposable copy, verifies row preservation and backup evidence, and removes its temporary artifacts. The source database remains read-only.
