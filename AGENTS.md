# Overlord Repository Guide

## Purpose
Overlord is a private, local-first Windows personal operating system. Foundation v0.1 covers the shell, dashboard, projects, tasks, settings, and 12-week cycles.

## Stack and commands
- Python 3.14, Flet 0.84, SQLite.
- Run: `python main.py`
- Test: `python -B -m unittest discover -s tests -v`
- Environment check: `python -B scripts/smoke_environment.py`

## Architecture
Dependencies point Presentation → Application → Domain. Infrastructure implements Application ports. Domain must not import Flet; Presentation must not import SQLite or concrete repositories.

## Database safety
Never recreate or test against `data/overlord.db`. Use disposable databases or copies. Schema changes require immutable forward migrations and a validated SQLite backup. Repositories never commit; commands own transaction boundaries.

## Design system
Use semantic tokens from `overlord/presentation/design_system`. Do not place raw UI colors in pages/components. Interface icons must come from the local Lucide registry.

## Domain invariants
There is one Task entity. Dashboard owns no persisted data. Blocked is derived from open Blockers. Definition of Done is required before Primary or Milestone assignment. Projects remain independent of Cycles.

## References and documentation
Decision priority is: approved product decisions → code/runtime evidence → paired reference instructions → reference images. Empty reference folders do not authorize invented category styling. Update `docs/architecture/FOUNDATION.md`, the decision log, and the execution plan when boundaries change.
