# Project Context

Last updated: 2026-08-14

Repository root: `E:\Projects\Overlord`

Open this directory itself as the Codex workspace. From that workspace, use `main.py`, not `Overlord/main.py`.

## 1. Project Summary

Overlord is a private, local-first Windows desktop planning application. It exists to turn Projects, Tasks, daily capacity, blockers, milestones, and 12-week execution cycles into one practical personal operating system without accounts, cloud dependencies, or AI-generated decisions.

The product uses Python 3.14, Flet 0.84, and SQLite. It is intentionally a modular monolith rather than a service-based system.

## 2. Current State

Foundation v0.1 and UX phases U1-U5 are implemented. Date-driven Tasks Stages 1 and 2 and the behavior-preserving Presentation boundary refactor are also implemented. The application has a stable desktop shell and a unified Tasks workspace with Kanban, week, and month views. Dashboard, Projects, Project Detail, 12-Week Plans, Cycle creation/detail, and categorized Settings remain working. The separate Daily Planning workflow has been retired.

The current build is a functional technical Foundation with an implemented light-theme design-system baseline, not final page-level product UX. The next approved activity is manual workflow review and page-by-page UX/UI refinement. Automatic feature expansion is not approved.

Supported launches from the repository root:

```powershell
python main.py
python main.py --demo
```

Web/browser mode is retired. `--web` and `--port` are rejected intentionally.

## 3. What Has Been Done

- Introduced Presentation, Application, Domain, and Infrastructure boundaries.
- Added connection-per-operation SQLite access, explicit Unit of Work transactions, forward-only migrations, validated backups, recovery handling, and rotating local logs.
- Preserved the existing production database and added deterministic isolated demo data at `data/demo/overlord_demo.db`.
- Built a mounted App Shell with persistent collapsible Sidebar, typed routes, contained errors, and delayed content-only loading.
- Built the Dashboard with a fixed three-day Yesterday/Today/Tomorrow task board, Weekly Progress, Current Cycle, and Needs Attention.
- Made Task the single source of scheduling truth with start date/time, optional end date/time, and optional deadline.
- Removed Primary/Secondary capacity, the Daily Planning route, and the Dashboard Plan the day workflow.
- Replaced the Foundation Tasks list with one Kanban/week/month planning workspace and contextual creation for undated work, Today, and calendar dates.
- Added direct Kanban drag-and-drop for card ordering, cross-column Task moves, and column reordering; Not completed remains automatic.
- Removed hidden More details creation; scheduling, details, Project, and Cycle relationships now share one visible task form.
- Added standalone Tasks, searchable/filterable Task browsing, status history, blockers, priorities, and reusable editor content.
- Replaced Project CRUD-first presentation with browse-first Project summaries and execution-oriented Project Detail.
- Added searchable Cycle cards, an atomic five-step Cycle creation wizard, Weekly Outcomes, connected Projects/Milestones/Tasks, and Cycle Detail.
- Redesigned Settings into Appearance, Planning, and Startup categories with System/Light/Dark themes and motion preferences.
- Added complete English/Russian interface catalogs with a persistent EN/RU switch in the mounted Sidebar.
- Centralized Crimson Focus tokens, localized dates/statuses/errors, and Lucide-only interface icons.
- Added one state-aware light design foundation for buttons, inputs, selects, checkboxes, switches, choice chips, and baseline data tables without creating a parallel system.
- Added typed validation metadata and public Task form codecs without changing accepted input or visible messages.
- Separated Task workspace state, pure projections/order transformations, service orchestration, and Flet rendering while preserving one Task and the existing persistence contract.
- Unified Dashboard and Tasks per-day ordering behind one Presentation controller that delegates to the existing Application command.
- Unified synchronous refresh and asynchronous navigation behind one route preparation/resolution/commit pipeline while preserving the mounted shell, delayed loading, failure containment, and superseded-transition guard.
- Added Foundation regression coverage for the current design-system, task, persistence, and navigation contracts.

## 4. Key Decisions

- Desktop is the only supported product surface.
- Open `E:\Projects\Overlord` directly as the workspace so repository commands and file paths are short and unambiguous.
- Production data is `data/overlord.db`; demo data is `data/demo/overlord_demo.db`. Demo mode must never write production data.
- Preserve Python/Flet/SQLite and the modular-monolith architecture. Do not introduce an ORM, dependency-injection framework, services, accounts, or networking without a concrete need.
- Dashboard is a composed read model and owns no scheduling or assignment data; Task infrastructure stores only optional per-day presentation positions.
- There is one Task entity. A Task may be standalone; Project is optional.
- Task identity contains its canonical schedule. Dashboard derives all Tasks active on each displayed date and has no planning group or daily capacity; explicit within-day card order is a separate Task presentation preference.
- Blocked is derived from an open Blocker, not a Task lifecycle status.
- Definition of Done is required before Milestone assignment.
- Projects remain independent from Cycles and may participate in multiple Cycles over time.
- Execution Score is completed originally planned Tasks divided by originally planned Tasks.
- Actual time remains unavailable until Work Sessions exist and must display `Not tracked yet`, never a false zero.
- English and Russian are supported interface languages. English remains the default for migrated settings; the Sidebar switch persists the selected device locale without translating user-entered content.
- Crimson Focus palettes and semantic tokens are authoritative. Lucide is the only interface icon family.
- `overlord/ui/design_system` remains the only design-system source; UI/UX research output is advisory and must not create a parallel generated hierarchy.
- `FieldValidationError` metadata and `overlord/ui/components/task_form_values.py` are the stable Presentation validation/form-codec boundaries; visible exception messages are not control-flow interfaces.
- `TaskWorkspaceState`, `task_workspace_model.py`, `task_workspace_controller.py`, and the `task_workspace.py` Flet facade are the canonical Tasks Presentation boundaries.
- Navigation has one preparation/resolution/commit pipeline. Async navigation may schedule/cancel work, but only the latest generation may commit content into the mounted shell.

## 5. Rejected Directions

### Web version / browser preview

The web preview was introduced because Codex can open websites in a side panel and attach comments to selected interface blocks. That workflow does not work usefully with Overlord: Flet exposes the rendered application as one `flutter-view`, so the annotation tool selects the whole application surface rather than individual Overlord controls.

The preview also added browser startup, port, renderer, and Chrome stability complexity without improving product review. Overlord therefore no longer supports web mode. Do not restore `--web`, `--port`, `flet run --web`, or a browser-based product path unless a new explicit decision reverses this.

Historical browser screenshots and reports remain evidence of earlier verification only.

### Other rejected or deferred directions

- Full rewrite or replacement of Python/Flet/SQLite.
- Microservices, ORM, global state framework, speculative extension points, or a plugin architecture.
- Direct database/repository access from Flet pages.
- Large always-open CRUD forms for Task, Project, or Cycle creation.
- Dashboard slot selection during Task creation.
- Decorative filler or animation without approved direction.
- File Tools integration; the prototype remains disconnected.

## 6. Important Discussions

- Desktop and web previously showed different content because production desktop used `data/overlord.db` while demo modes used `data/demo/overlord_demo.db`; this was expected database isolation, not synchronization failure.
- The global Loading flash came from replacing the full page during route transitions. The shell now stays mounted, duplicate routes are ignored, loading appears only after a delay in the content region, and sync/async rendering share one commit authority.
- Task capture creates the canonical Task directly. Its date determines when it appears; an inclusive start/end range keeps it visible on each covered date; an optional deadline determines when unfinished work becomes missed.
- Legacy TaskPlan rows remain preserved as historical evidence, but current runtime code neither reads nor writes them.
- Project summaries now show honest execution context rather than database fields: stage, milestone, next action, eligible-Task progress, blockers, open Tasks, and active Cycle context.
- Cycle creation is transient until final atomic submission. Weekly progress counts persisted Weekly Outcomes rather than elapsed time.
- A large gray Settings block was traced to a Flet 0.84 layout error: a wrapping Row contained an expanded child. Removing that invalid combination restored the controls, and a regression test now guards it.
- Task editing uses one clear modal window shared by Kanban and calendar cards; its final visual polish remains Stage 3 work.

## 7. Current Problems

- The shared light-theme foundations are consistent, but individual pages and complex workflows still need manual product and UX/UI refinement.
- The supplied Overlord SVG mark is integrated into the mounted Sidebar; the Windows icon, splash asset, and packaging pipeline are not finalized.
- Task-window layout and card density still need reference-driven Stage 3 polish.
- Project/Cycle category-specific visual direction and decorative animation references are missing.
- Python 3.14/Flet imports and some database integration tests can start slowly on this Windows environment.
- Physical desktop visual checks across all Windows scaling levels, themes, and supported resolutions remain partly manual.
- Work Sessions do not exist, so actual-time metrics are intentionally unavailable.
- The Tasks workflow is functionally complete for Stage 2. Reference-driven visual polish, card density tuning, and final page composition belong to Stage 3.

## 8. Next Steps

1. Verify the unified Tasks workflow in the deterministic desktop demo with `python main.py --demo`.
2. Keep recurring actions outside Tasks until their separate goals/skills/habits concept is explicitly designed.
3. Stage 3: use the user's visual reference, adapt it to Overlord's exact workflow, and complete page-level visual polish.
4. Tune card density and Task-window composition from real desktop use without changing canonical scheduling rules.
5. Resolve the logo and category-specific visual direction approval gates before broader feature work.

## 9. Important Constraints

- Never recreate, reset, seed, or run disposable tests against `data/overlord.db`.
- Record the production database hash before and after risky verification. Use read-only diagnostics and disposable copies.
- Do not change migrations, Domain entities, repositories, or Application services for a Presentation-only problem.
- Do not silently normalize ambiguous legacy statuses or discard history.
- Repositories never commit; Application commands own transaction boundaries.
- Presentation must not import SQLite or concrete repositories. Domain must not import Flet.
- Keep the mounted App Shell, duplicate-route guard, delayed content loading, and persistent Sidebar behavior.
- Do not add raw screen-level colors or non-Lucide interface icons.
- Do not expose unfinished modules to fill space.
- Do not implement Goals, Habits, Skills, Work Sessions, Weekly Reviews, AI, Widget behavior, notifications, cloud sync, accounts, collaboration, or new analytics without explicit approval.
- Do not re-enable web mode unless the product decision is explicitly revisited and a block-level review workflow is technically proven.
- Keep `ui/views/file_manager.py` disconnected.
