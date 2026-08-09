# Overlord Repository Guide

## Purpose
Overlord is a private, local-first Windows personal operating system. Foundation v0.1 and UX phases U1-U5 cover the stable shell, dashboard and daily planning, tasks, projects, 12-week cycles, and categorized settings.

## Stack and commands
Python 3.14, Flet 0.84, SQLite.

Open `E:\Projects\Overlord` itself as the workspace root. Do not use `E:\Projects` as the project workspace when a repository-root workspace is available.

- Desktop: `python main.py`
- Demo desktop: `python main.py --demo`
- Reset deterministic demo data: `python scripts/seed_demo.py`
- Test: `python -B -m unittest discover -s tests -v`
- Environment check: `python -B scripts/smoke_environment.py`

Web mode is retired and intentionally rejected by `main.py`. Do not restore `--web`, `--port`, `flet run --web`, a browser preview, or a browser-based product path without a new explicit product decision. The Codex browser annotation system selects Flet's whole `flutter-view` surface rather than individual Overlord controls, so it does not provide the block-level review workflow the web experiment was meant to enable.

Demo data is isolated at `data/demo/overlord_demo.db`. Never point demo seeding at `data/overlord.db`.

Source launches default to development timing logs. Set `OVERLORD_ENV=production` to disable route timing diagnostics. Runtime startup logs identify production/demo mode, desktop application type, the resolved database, and demo seed timing.

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

Read `PROJECT_CONTEXT.md` first when starting a new task or moving this repository to a new Codex workspace.

Goals, Habits, Skills, Work Sessions, Weekly Reviews, AI, desktop Widget behavior, notifications, cloud sync, accounts, collaboration, and additional analytics remain outside Foundation.
