# UX Phase U3 - Projects Working Contexts

Status: implemented and covered by disposable automated tests on 2026-08-07.

Automated result: 77/77 repository tests passed. Production database SHA-256 before and after U3: `A2729A7AFC5461E5E94184E014D42A86BECD5625E2DF8DBF213EE1BD86CA8589`; integrity check is `ok` with zero foreign-key violations.

## Scope

U3 changes only Project browsing, transient Project creation, Project summaries, and Project Detail. Dashboard, Daily Planning, standalone Tasks, 12-Week Plan editing, Settings, migrations, and Domain entities remain unchanged.

## Project summaries

The browse-first list now supports title/description search, lifecycle filtering, clear filters, and persisted filter state. Summary cards expose status, stage, current meaningful Milestone, a trustworthy next action, eligible-Task progress, open Task count, blockers, and active-Cycle context.

Progress is `completed eligible Tasks / all eligible Tasks`. Cancelled Tasks and archived Tasks are excluded. When there are no eligible Tasks, the UI reports that progress is unavailable and does not show `0%`.

Next Action is shown only when it is unambiguous: one in-progress Task next action, or one next action across all eligible open Tasks. Multiple planned candidates are not silently ranked.

## Project Detail

Project Detail is ordered around execution context: stage, Milestone, next action, active Cycle, honest progress, blockers, and canonical Tasks. Milestone status, Definition of Done, and target date are shown when present. Blockers retain their type, description, date, and affected Task. Task views separate Open, Completed, and Blocked work.

Quick Task reuses the U2 dialog and preselects the current Project. Project remains optional in that shared component.

## Data safety

No migration or schema change was required. U3 adds a focused immutable Project read model and SQLite mapping behind the existing repository port. Presentation still has no direct SQLite or concrete repository access.

The deterministic demo seed is version 3 and contains seven Projects covering rich active, active without Cycle, no Milestone, no Tasks, completed, and archived states while retaining the existing 22 Tasks and U1/U2 records.

## Verification commands

```powershell
cd E:\Projects\Overlord
python -B -m unittest discover -s tests -v
python -B scripts/smoke_environment.py
python scripts/seed_demo.py
python main.py --demo
```

Desktop visual checks remain a human-operated step because automated verification must not launch Chrome or another GUI process unexpectedly.
