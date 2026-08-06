# Overlord Foundation v0.1 Execution Plan

## Document Status

- Owner: Overlord repository
- Branch: `foundation-v0.1`
- Approval: Approved for implementation
- Last update: 2026-08-06
- Current phase: Phases 0–4 implementation

## Source-of-Truth Order

Approved prompt and recorded decisions, verified code/runtime behavior, audit evidence, paired reference instructions, then reference images. Assumptions stay replaceable and do not override approved decisions.

## Executive Summary

Preserve Python/Flet/SQLite and user data. Evolve the working MVP through a layered modular-monolith architecture with forward-only migrations, transaction-owned commands, immutable read models, centralized design tokens, and a Flet desktop shell.

## Verified Baseline

- Repository: `E:\Projects\Overlord`; initial baseline `2451f99` on `foundation-v0.1`.
- Python 3.14.3; Flet/Flet Desktop 0.84.0; SQLite 3.50.4.
- Startup: `python main.py`; baseline used deprecated `ft.app(main)`.
- Baseline tests: eight unittest cases.
- Production database before implementation: schema version 0, SHA-256 `E8339C04B31A302BCEDE1E0A5C708B5A130FA2E368F3D868BBD4CA95A8EFE527`, one Project, two Tasks, integrity and foreign keys healthy.

## Recorded Product Decisions

English UI; three Primary and four Secondary slots; seven-day planned/completed bars; persistent collapsible sidebar; Definition of Done before Primary/Milestone assignment; task-count Execution Score based on original weekly plans; reusable Task editor content with its final container deferred; text brand fallback until the real logo arrives.

## Scope and Exclusions

Phases 0–4 deliver baseline safety, shell/themes, Dashboard, Projects/Tasks, Settings, and 12-week Cycles. Work Sessions, Weekly Reviews, widget process, accounts, cloud, AI, habits, skills, analytics, imports, and exports are excluded. Missing actual time displays as “Not tracked yet.”

## Information Architecture

Routes: `/dashboard`, `/tasks`, `/projects`, `/projects/{id}`, `/cycles`, `/cycles/{id}`, and `/settings`. Unknown routes show a contained not-found state. Dashboard composes Today, Weekly Progress, Current Cycle, Needs Attention, and a replaceable static decorative slot.

## Architecture

Presentation → Application → Domain; Infrastructure implements ports. Domain imports standard library only. Presentation imports neither `sqlite3` nor concrete repositories. A connection factory creates one configured connection per operation. Commands own transactions; repositories never commit. Screen controllers refresh immutable query DTOs after commands.

## Data, Migration, and Recovery

`0001_baseline` adopts or creates the legacy schema and ledger; `0002_settings` adds typed preferences; `0003_task_planning_attention` adds canonical Task lifecycle, append-only planning/history, and Blockers; `0004_project_task_workflows` adds Project workflow metadata; `0005_cycles_milestones_outcomes` adds Cycles, Milestones, junctions, and Weekly Outcomes. A validated SQLite API backup precedes any pending migration batch. Unknown legacy shapes and migration checksum drift fail closed.

## Design System

The approved Crimson Focus light/dark palettes map to centralized semantic tokens. Pages use shared spacing, typography, radius, motion, state, and component tokens. System/Light/Dark settings resolve through Flet themes. Interface icons are selected, pinned Lucide SVG assets through one registry. The logo slot uses “Overlord” text until the real asset is supplied.

## Phase Checklists

### Phase 0 — Baseline and safety

- [x] Track the execution plan, environment commands, and direct dependencies.
- [x] Add non-writing diagnostics and environment smoke checks.
- [x] Add immutable migration ledger, validated backup, logging, and safe startup boundary.
- [x] Confirm final production database hash after all disposable verification.

### Phase 1 — Architecture and shell

- [x] Introduce Domain/Application/Infrastructure/Presentation packages and Unit of Work.
- [x] Add Settings, route registry, reusable shell states, theme tokens, Lucide registry, and brand adapter.
- [x] Preserve `python main.py` and use `ft.run`.

### Phase 2 — Dashboard

- [x] Add canonical lifecycle, plans, histories, Blockers, aggregate query, slots, weekly bars, cycle/attention cards, and factual unavailable states.

### Phase 3 — Project and Task workflows

- [x] Add searchable/filterable lists, creation/editing/planning/blocker actions, histories, Project detail, and reusable editor content.

### Phase 4 — 12-Week Cycles

- [x] Add Cycle/Milestone/Weekly Outcome model and migrations, list/create/detail workflows, one-active-cycle rule, and Dashboard integration.

## Test Matrix

Unit tests cover domain rules and derived metrics. Application tests cover atomicity, planning, blockers, attention, and cycle activation. SQLite tests cover fresh/legacy/idempotent migrations, checksums, backups, constraints, and rollback. Static tests enforce dependency and design-system boundaries. Manual smoke covers supported Windows sizes/scales, themes, sidebar states, motion preferences, empty/overflow/error states, and keyboard navigation.

## Risks and Mitigations

The only user database is protected by copy-based tests, strict baseline recognition, API backups, and integrity checks. Ambiguous legacy statuses remain raw with nullable canonical lifecycle. Separate connections avoid shared-lock failures. Missing branding/visual references remain explicit acceptance gates rather than invented designs.

## Open Decisions and Approval Gates

Real logo/Windows icon; permanent Task Detail container; decorative animation reference; category-specific visual polish for Projects/Cycles; final centrally replaceable palette tuning.

## Decision Log

- 2026-08-06: Foundation v0.1 plan approved in full.

## Change Log

- 2026-08-06: Baseline recorded; implementation checklist initialized.
- 2026-08-06: Phases 0–4 implemented; 35 tests passed; actual production-copy migration reached v5 with rows preserved and a validated backup; production source hash, size, and timestamp remained unchanged.
