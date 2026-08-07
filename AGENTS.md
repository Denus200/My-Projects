# Overlord Repository Guide

## Purpose
Overlord is a private, local-first Windows personal operating system. Foundation v0.1 and UX phases U1-U5 cover the stable shell, dashboard and daily planning, tasks, projects, 12-week cycles, and categorized settings.

## Stack and commands
Python 3.14, Flet 0.84, SQLite.

From the repository root (`E:\Projects\Overlord`):

- Desktop: `python main.py`
- Demo desktop: `python main.py --demo`
- Reset deterministic demo data: `python scripts/seed_demo.py`
- Web preview: `python main.py --web --port 8550`
- Test: `python -B -m unittest discover -s tests -v`
- Environment check: `python -B scripts/smoke_environment.py`

From the parent workspace (`E:\Projects`):

- Production desktop: `python Overlord/main.py`
- Demo desktop: `python Overlord/main.py --demo`
- Demo web: set `$env:OVERLORD_DEMO = "1"`, then run `python Overlord/main.py --web --port 8550`

Before starting a web preview, check whether port 8550 already has one running:

```powershell
Get-NetTCPConnection -LocalPort 8550 -State Listen -ErrorAction SilentlyContinue
```

If the port is occupied, reuse the existing preview or deliberately choose another port, such as `--port 8551`. Do not start a second server on the same port. Do not use `flet run` for this repository on Python 3.14; the verified application-owned `--web` entry point starts the server without automatically launching Chrome. Launch paths, database paths, and asset paths must work from either directory above.

Demo data is isolated at `data/demo/overlord_demo.db`. For a web demo preview, set `OVERLORD_DEMO=1` before running Flet. Never point demo seeding at `data/overlord.db`.

Source launches default to development timing logs. Set `OVERLORD_ENV=production` to disable route timing diagnostics. Runtime startup logs identify production/demo mode, desktop/web type, the resolved database, and demo seed timing.

## Architecture
Dependencies point Presentation → Application → Domain. Infrastructure implements Application ports. Domain must not import Flet; Presentation must not import SQLite or concrete repositories.

## Database safety
Never recreate or test against `data/overlord.db`. Use disposable databases or copies. Schema changes require immutable forward migrations and a validated SQLite backup. Repositories never commit; commands own transaction boundaries.

## Design system
Use semantic tokens from `overlord/presentation/design_system`. Do not place raw UI colors in pages/components. Interface icons must come from the local Lucide registry.

Visible English copy should come from `overlord/presentation/strings.py` when practical. Use shared Presentation components only for patterns already repeated across approved screens. Preserve keyboard focus, tooltips for icon-only controls, compact actionable empty states, contained errors, and reduced-motion behavior.

## Domain invariants
There is one Task entity. A Task may be standalone (`project_id = NULL`); never create a fallback Project to satisfy storage. Dashboard owns no persisted data. Blocked is derived from open Blockers. Definition of Done is required before Primary or Milestone assignment. Projects remain independent of Cycles.

## References and documentation
Decision priority is: approved product decisions → code/runtime evidence → paired reference instructions → reference images. Empty reference folders do not authorize invented category styling. Update `docs/architecture/FOUNDATION.md`, the decision log, and the execution plan when boundaries change.

Goals, Habits, Skills, Work Sessions, Weekly Reviews, AI, desktop Widget behavior, notifications, cloud sync, accounts, collaboration, and additional analytics remain outside Foundation.
