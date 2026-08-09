# Project Context

Last updated: 2026-08-09

Repository root: `E:\Projects\Overlord`

Open this directory itself as the Codex workspace. From that workspace, use `main.py`, not `Overlord/main.py`.

## 1. Project Summary

Overlord is a private, local-first Windows desktop planning application. It exists to turn Projects, Tasks, daily capacity, blockers, milestones, and 12-week execution cycles into one practical personal operating system without accounts, cloud dependencies, or AI-generated decisions.

The product uses Python 3.14, Flet 0.84, and SQLite. It is intentionally a modular monolith rather than a service-based system.

## 2. Current State

Foundation v0.1 and UX phases U1-U5 are implemented. The application has a stable desktop shell and working Dashboard, Daily Planning, Tasks, Projects, Project Detail, 12-Week Plans, Cycle creation/detail, and categorized Settings.

The current build is a functional technical Foundation, not final product UX. The next approved activity is a manual product and UX/UI redesign pass based on real desktop use and Figma exploration. Automatic feature expansion is not approved.

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
- Built the Dashboard with daily Primary/Secondary work, Weekly Progress, Current Cycle, and Needs Attention.
- Separated lightweight Task capture from Daily Planning. Daily Planning owns the three Primary and four Secondary positions.
- Added standalone Tasks, searchable/filterable Task browsing, planning/status histories, blockers, priorities, and reusable editor content.
- Replaced Project CRUD-first presentation with browse-first Project summaries and execution-oriented Project Detail.
- Added searchable Cycle cards, an atomic five-step Cycle creation wizard, Weekly Outcomes, connected Projects/Milestones/Tasks, and Cycle Detail.
- Redesigned Settings into Appearance, Planning, and Startup categories with System/Light/Dark themes and motion preferences.
- Centralized Crimson Focus tokens, localization-ready English strings, and Lucide-only interface icons.
- Added Foundation regression coverage. The desktop-only startup update was verified by a full run of 102 passing tests on 2026-08-09.

## 4. Key Decisions

- Desktop is the only supported product surface.
- Open `E:\Projects\Overlord` directly as the workspace so repository commands and file paths are short and unambiguous.
- Production data is `data/overlord.db`; demo data is `data/demo/overlord_demo.db`. Demo mode must never write production data.
- Preserve Python/Flet/SQLite and the modular-monolith architecture. Do not introduce an ORM, dependency-injection framework, services, accounts, or networking without a concrete need.
- Dashboard is a composed read model and owns no persisted data.
- There is one Task entity. A Task may be standalone; Project is optional.
- Task identity does not contain a Dashboard group or position. Daily planning owns up to three Primary and four Secondary assignments.
- Blocked is derived from an open Blocker, not a Task lifecycle status.
- Definition of Done is required before Primary or Milestone assignment.
- Projects remain independent from Cycles and may participate in multiple Cycles over time.
- Execution Score is completed originally planned Tasks divided by originally planned Tasks.
- Actual time remains unavailable until Work Sessions exist and must display `Not tracked yet`, never a false zero.
- English is the current interface language; visible copy should remain localization-ready for future RU/UK catalogs.
- Crimson Focus palettes and semantic tokens are authoritative. Lucide is the only interface icon family.

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
- The global Loading flash came from replacing the full page during route transitions. The shell now stays mounted, duplicate routes are ignored, and loading appears only after a delay in the content region.
- Task capture was simplified to title plus optional Project, with progressively disclosed details. Daily positioning moved into a separate Daily Planning workflow.
- Project summaries now show honest execution context rather than database fields: stage, milestone, next action, eligible-Task progress, blockers, open Tasks, and active Cycle context.
- Cycle creation is transient until final atomic submission. Weekly progress counts persisted Weekly Outcomes rather than elapsed time.
- A large gray Settings block was traced to a Flet 0.84 layout error: a wrapping Row contained an expanded child. Removing that invalid combination restored the controls, and a regression test now guards it.
- The permanent Task Detail outer container remains intentionally undecided pending manual design work.

## 7. Current Problems

- The visible UX is coherent but still needs a manual product and UX/UI redesign rather than more automatic feature work.
- The real Overlord logo, Windows icon, splash asset, and packaging pipeline are not finalized.
- The permanent Task Detail container is still undecided.
- Project/Cycle category-specific visual direction and decorative animation references are missing.
- Python 3.14/Flet imports and some database integration tests can start slowly on this Windows environment.
- Physical desktop visual checks across all Windows scaling levels, themes, and supported resolutions remain partly manual.
- Work Sessions do not exist, so actual-time metrics are intentionally unavailable.

## 8. Next Steps

1. Open and use the deterministic desktop demo with `python main.py --demo`.
2. Perform the `Manual Product & UX/UI Redesign Pass` on the working Foundation.
3. Record real workflow friction, then redesign the affected screens and relationships in Figma before changing code.
4. Resolve the logo, Task Detail container, and category-specific visual direction approval gates.
5. Only after that review, decide whether future systems such as Goals, Habits, Skills, Work Sessions, Weekly Reviews, or a desktop Widget belong in the roadmap.

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
