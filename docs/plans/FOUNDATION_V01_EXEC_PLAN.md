# Overlord Foundation v0.1 Execution Plan

## Document Status

- Owner: Overlord repository
- Branch: `foundation-v0.1`
- Approval: Approved for implementation
- Last update: 2026-08-21
- Current phase: Foundation complete; Task Card/three-day Dashboard and Projects foundation/redesign implemented

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

English and Russian UI with a persistent Sidebar switch; date-driven Task scheduling with no daily slot limit; seven-day planned/completed bars; persistent collapsible sidebar; Definition of Done before Milestone assignment; task-count Execution Score based on scheduled work; reusable Task editor content with its final container deferred; text brand fallback until the real logo arrives.

## Scope and Exclusions

Phases 0–4 deliver baseline safety, shell/themes, Dashboard, Projects/Tasks, Settings, and 12-week Cycles. Work Sessions, Weekly Reviews, widget process, accounts, cloud, AI, habits, skills, analytics, imports, and exports are excluded. Missing actual time displays as “Not tracked yet.”

## Information Architecture

Routes: `/dashboard`, `/tasks`, `/projects`, `/projects/{id}`, `/cycles`, `/cycles/new`, `/cycles/{id}`, and `/settings`. Unknown routes show a contained not-found state. Dashboard composes Today, Weekly Progress, Current Cycle, and Needs Attention without decorative filler. Tasks owns scheduling; there is no separate Daily Planning route. Settings contains only Appearance, Planning, and Startup categories.

## Architecture

Presentation → Application → Domain; Infrastructure implements ports. Domain imports standard library only. Presentation imports neither `sqlite3` nor concrete repositories. A connection factory creates one configured connection per operation. Commands own transactions; repositories never commit. Screen controllers refresh immutable query DTOs after commands.

## Data, Migration, and Recovery

`0001_baseline` adopts or creates the legacy schema and ledger; `0002_settings` adds typed preferences; `0003_task_planning_attention` adds canonical Task lifecycle, historical planning, and Blockers; `0004_project_task_workflows` adds Project workflow metadata; `0005_cycles_milestones_outcomes` adds Cycles, Milestones, junctions, and Weekly Outcomes; `0006_standalone_tasks` makes Task-to-Project optional without changing existing records; `0007_interface_locale` adds the persistent `en`/`ru` interface locale; `0008_date_driven_tasks` adds the canonical Task schedule and migrates current legacy plan dates without deleting history; `0009_task_day_ordering` adds persistent per-day presentation order for scheduled Tasks; `0010_projects_foundation` adds Project color/favorite state, Project Plans and Stages, normalized zero-to-four Task links, and local-workspace metadata while migrating legacy single-Project links; `0011_create_task_flow` adds explicit normal/draft creation intent and nested Task Checklist persistence; `0012_task_details_flow` adds the Paused lifecycle value while preserving Task relations; `0013_complete_task_flow` adds nullable manual Total Time and Active Time values. A validated SQLite API backup precedes any pending migration batch. Unknown legacy shapes and migration checksum drift fail closed.

## Design System

The approved Crimson Focus light/dark palettes map to centralized semantic tokens. Pages use shared spacing, typography, radius, motion, state, and component tokens. System/Light/Dark settings resolve through Flet themes. Interface icons are selected, pinned Lucide SVG assets through one registry. The mounted Sidebar uses the supplied Overlord SVG mark in expanded and compact responsive states.

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
- [x] Add the approved Weather card with fixed Merefa Open-Meteo data, centralized WMO normalization, local normalized cache/offline fallback, and non-blocking 30-minute refresh without resize/Sidebar requests.

### Phase 3 — Project and Task workflows

- [x] Add searchable/filterable lists, creation/editing/planning/blocker actions, histories, Project detail, and reusable editor content.

### Phase 4 — 12-Week Cycles

- [x] Add Cycle/Milestone/Weekly Outcome model and migrations, list/create/detail workflows, one-active-cycle rule, and Dashboard integration.

### Stage 1 — Date-driven Tasks

- [x] Replace Primary/Secondary assignment with canonical Task start, end, and deadline fields.
- [x] Remove Daily Planning and the Dashboard planning call to action.
- [x] Show every Task active on the selected date without a capacity limit.
- [x] Preserve legacy TaskPlan history through migration `0008_date_driven_tasks`.
- [x] Define derived Planned, In progress, Not completed, Completed, and Archive placement for later Kanban UI.

### Stage 2 — Unified Tasks workspace

- [x] Remove hidden progressive disclosure from Task creation and show one complete scheduling form.
- [x] Add contextual creation for Planned, Today, and individual calendar dates.
- [x] Add the four-column My Tasks/Kanban presentation, grouping canonical Not completed/Archive placement plus Paused/open-blocker conditions into non-assignable Needs Attention.
- [x] Redesign Week as a seven-day fixed-width horizontal board with independent day scrolling, contextual creation, filtered counts, and shared expandable Week/Month date-navigation Tabs.
- [x] Redesign Month as a responsive Monday-first calendar matrix with real adjacent dates, dynamic today treatment, fixed-height independently scrolling cells, shared compact Task Cards, contextual creation, and normalized filters.
- [x] Keep Project and 12-week Cycle membership as Task relationships and show them on cards.
- [x] Keep recurring actions outside Tasks.

### Projects foundation and redesign

- [x] Persist Project color, Favorite, lifecycle state, Project Plans, and ordered Stages.
- [x] Normalize Task-to-Project membership with zero-to-four unique links and one optional same-Project Stage per link.
- [x] Preserve legacy single-Project associations through forward migration `0010_projects_foundation`.
- [x] Redesign Create Task as one state-driven modal with progressive advanced options, shared date/date-time overlays, zero-to-four Project links, per-Project Stages, nullable duration estimates, normal/draft creation intent, and nested Checklist persistence through `0011_create_task_flow`.
- [x] Redesign Task Details as one shared state-driven modal with atomic Task/Project/Stage/Checklist editing, stable Checklist IDs, Planned/In progress/Blocked/Paused/Completed behavior, shared pickers, and confirmed relationally safe deletion through `0012_task_details_flow`.
- [x] Route Dashboard, Task Details, Tasks/Kanban, and Project Tasks through one Complete Task modal; atomically persist completion and optional Estimated/Total/Active minutes through `0013_complete_task_flow`.
- [x] Connect persisted Project colors to the shared Task Card without creating a Projects-only card implementation.
- [x] Implement responsive Project cards, explicit post-create routing, shared detail tabs, conditional 12-week context, Project Tasks by Stage, local Notes & Files, and reversible Archive behavior.

## Test Matrix

Stage 1 additionally verifies unlimited date-driven Dashboard membership, inclusive ranges, schedule validation, derived board placement, removal of the Daily Planning route and call to action, legacy-plan migration, and production/demo database isolation.

Unit tests cover domain rules and derived metrics. Application tests cover atomicity, planning, blockers, attention, and cycle activation. SQLite tests cover fresh/legacy/idempotent migrations, checksums, backups, constraints, and rollback. Static tests enforce dependency and design-system boundaries. Manual smoke covers supported Windows sizes/scales, themes, sidebar states, motion preferences, empty/overflow/error states, and keyboard navigation.

## Risks and Mitigations

The only user database is protected by copy-based tests, strict baseline recognition, API backups, and integrity checks. Ambiguous legacy statuses remain raw with nullable canonical lifecycle. Separate connections avoid shared-lock failures. Missing branding/visual references remain explicit acceptance gates rather than invented designs.

## Open Decisions and Approval Gates

Windows icon and packaging; permanent Task Detail container; decorative animation reference; category-specific visual polish for Projects/Cycles; final centrally replaceable palette tuning.

## Decision Log

- 2026-08-06: Foundation v0.1 plan approved in full.
- 2026-08-13: Date-driven Task scheduling Stage 1 approved; the daily slot model is superseded.
- 2026-08-14: Approved the behavior-preserving Presentation refactor: typed validation metadata, explicit design-system ownership, Task workspace/controller boundaries, shared per-day ordering ownership, and one navigation resolution/commit pipeline. No persistence boundary or product decision changed.
- 2026-08-21: Approved normalized multi-Project Task membership, Project-owned Plans and Stages, persistent Project color/favorite state, local Project workspaces, and the reference-driven Projects redesign. Project Plans remain distinct from global 12-week Cycles.

## Change Log

- 2026-08-06: Baseline recorded; implementation checklist initialized.
- 2026-08-06: Phases 0–4 implemented; 35 tests passed; actual production-copy migration reached v5 with rows preserved and a validated backup; production source hash, size, and timestamp remained unchanged.
- 2026-08-07: UX Phase U2 adds standalone Tasks, compact Quick Task capture, progressive details, browsing filters, and migration `0006_standalone_tasks`.
- 2026-08-07: UX Phase U3 replaces Project CRUD surfaces with browse-first summaries, transient creation, honest eligible-Task progress, and execution-oriented Project Detail. No migration was required.
- 2026-08-07: UX Phase U4 replaces Cycle CRUD surfaces with browse-first summaries, an atomic five-step creation wizard, explicit Weekly Outcome progress, and execution-oriented Cycle Detail. No migration was required.
- 2026-08-11: Added complete English/Russian catalogs, localized dates/statuses/validation, a persistent Sidebar language switch, and migration `0007_interface_locale`.
- 2026-08-12: Applied the approved Sidebar component references, supplied Overlord SVG mark, compact 56-pixel rail, header collapse/hover-expand behavior, and explicit navigation/toggle interaction states.
- 2026-08-07: UX Phase U5 completes Foundation with compact categorized Settings, centralized Presentation copy, shared dialog/success patterns, semantic theme defaults, contained route errors, accessibility/responsive hardening, and U1-U4 regression cleanup. No migration was required.
- 2026-08-09: Retired the experimental web preview because Flet's single `flutter-view` prevents useful block-level Codex browser annotations. Desktop and deterministic demo desktop remain supported; web arguments now fail safely before startup.
- 2026-08-13: Added migration `0008_date_driven_tasks`, retired Daily Planning and Primary/Secondary slots, made Task schedules canonical, and derived Dashboard Today directly from scheduled Tasks.
- 2026-08-13: Replaced Dashboard Today with a three-day board and added migration `0009_task_day_ordering` for explicit same-day Task ordering.
- 2026-08-13: Replaced the Foundation Tasks list with one Kanban/week/month workspace, contextual creation, a fully visible Task form, and editable Cycle relationships.
- 2026-08-14: Refactored Presentation incrementally without schema or persisted-format changes. Validation routing no longer depends on exception prose; design roles are explicit; Task workspace state/projections/controllers are separated; Dashboard and Tasks share per-day ordering ownership; synchronous refresh and asynchronous navigation now share route preparation, resolution, and commit behavior.
- 2026-08-21: Added migration `0010_projects_foundation`, preserved legacy Project links, introduced Project Plans/Stages and local workspace metadata, connected real Project colors to the shared Task Card, and implemented the current Projects list/create/detail/overview/plan/tasks/notes/archive reference states.
- 2026-08-21: Added migration `0011_create_task_flow` and completed Create Task tranche 1 with a single progressive modal, shared calendar overlays, normalized Project/Stage assignments, nullable hour/minute estimates, explicit draft creation intent, atomic nested Checklists, and native reference-comparison captures. Task Details and Complete Task remain deferred.
- 2026-08-21: Added migration `0012_task_details_flow` and completed Task Details tranche 2 with one Dashboard/Tasks/Project-deep-link editor, atomic lifecycle and relationship saves, stable-ID Checklist synchronization, Paused lifecycle support, Blocked derivation through open Blockers, confirmed Task deletion, and nine native captures. Complete Task remains deferred.
- 2026-08-21: Added migration `0013_complete_task_flow` and completed Complete Task tranche 3 with one confirmation modal across Dashboard, Task Details, Tasks/Kanban, and Project Tasks; existing estimates are locked, missing estimates and independent manual Total/Active values are optional, confirmation is atomic, and six native captures cover the approved states.
- 2026-08-21: Corrected the shared nullable duration control for three-digit hours and made the Dashboard three-day working lists lifecycle-aware: Planned/In progress and Completed remain visible, while Blocked and Paused retain their Task data but are excluded from actionable day lists.
- 2026-08-22: Renamed Tasks to My Tasks and redesigned Kanban as a responsive four-column board with independent column scrolling, shared Task Cards and flows, session order preservation, normalized Project filtering, and a derived non-assignable Needs Attention grouping. No schema or domain state changed.
- 2026-08-22: Redesigned My Tasks/Week as a reference-matched seven-day horizontal board with fixed 300-pixel columns, independent vertical Task lists, real-date placement, contextual per-day creation, Search/normalized Project filtering, and shared transient expandable Week/Month navigation. Schema, Domain, and Application boundaries remain unchanged.
- 2026-08-22: Redesigned My Tasks/Month as a reference-matched responsive calendar grid with Monday–Sunday ordering, real adjacent dates, dynamic today highlighting, compact shared Task Cards, internal busy-day overflow, contextual creation, and shared details/completion/filter/navigation behavior. No migration or persistence boundary changed.
- 2026-08-27: Connected the approved Dashboard Weather widget to Open-Meteo for fixed Merefa current conditions and five daily forecasts. Added centralized WMO normalization, a database-specific normalized JSON cache, stale/offline fallback, and an asynchronous 30-minute refresh loop; no schema or persisted business-data boundary changed.
