# Foundation v0.1 Architecture

Overlord is a modular monolith. Presentation depends on Application DTOs and commands; Application owns use-case and transaction boundaries; Domain owns entities and rules; Infrastructure implements SQLite ports.

```text
Flet Presentation → Application → Domain
                         ↑
                  SQLite Infrastructure
```

Connections are created per command/query, enable foreign keys and a bounded busy timeout, and close through context managers. Commands use one explicit Unit of Work; repositories never commit. Queries return immutable read models rather than SQLite rows.

The Dashboard is a composed query, never an entity or table. Task planning is append-only. A Task may have no Project; `tasks.project_id` is nullable from migration `0006_standalone_tasks`, while existing Task and Project records remain unchanged. Blocked state is derived from an open Blocker. Cycle relationships use junction tables so Projects and Tasks remain independent across cycles.

Project browsing uses a focused immutable read model. Infrastructure maps eligible Task counts, open Blockers, current Milestone, and active-Cycle context; Application exposes summaries and detail; Presentation never ranks Tasks or derives database context. Eligible Project progress excludes cancelled and archived Tasks, and is unavailable when the denominator is empty.

Cycle browsing uses a consolidated read model for lifecycle, explicit Weekly Outcome counts, connected Projects, and next Milestone. The five-step Cycle wizard remains transient until one atomic Application command creates the Cycle graph inside a single Unit of Work. Cycle progress counts persisted Weekly Outcomes only; elapsed time is presented separately as active-week context.

Presentation keeps one mounted App Shell and replaces only route content. Settings is a compact categorized surface with Appearance, Planning, and Startup sections; narrow desktop widths replace the category rail with a selector. System, Light, and Dark themes resolve through centralized semantic tokens, and reduced motion suppresses nonessential motion without removing state feedback. Stable visible copy is accessed through the centralized English catalog so RU/UK catalogs can be added later without coupling business rules to labels.

Shared Presentation components cover established cross-screen patterns such as page/section headings, task rows, dialog footers, empty/loading states, and non-blocking success feedback. Route and mutation errors remain contained, expose neutral user copy, and retain technical detail in local logs. Interface icons come exclusively from the pinned Lucide adapter.

The stable startup command remains `python main.py`. `overlord/bootstrap.py` is the composition root. A future widget may reuse Application queries through a separate read-only connection, but no widget process is part of v0.1. Foundation ends after UX Phase U5; any broader product or visual changes require a separate manual product and UX/UI redesign pass.
