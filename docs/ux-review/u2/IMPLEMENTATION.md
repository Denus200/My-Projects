# UX Phase U2 — Tasks and Quick Capture

> **Historical U2 implementation record — superseded by date-driven Tasks Stages 1–2.** The current Task form exposes scheduling and relationship fields directly, Tasks uses one Kanban/week/month workspace, and successful mutations refresh through the mounted page owner. The migration and standalone-Task preservation notes below remain valid historical evidence; the old form/filter composition and web-preview wording are not current instructions.

U2 replaces the always-open Create Task form with a compact `Quick Task` dialog. Title is required; Project defaults to `No Project`. Planned date, estimate, importance, urgency, Definition of Done, next action, and blocker information stay behind `More details`. Dashboard group and position are not part of Task creation.

The Tasks page now prioritizes browsing. It supports search, Project (including `No Project`), lifecycle, Today/This week/Overdue/Not planned, importance, urgency, Needs Attention, and reset. Creation, completion, filtering, and editing update the content locally without rebuilding the App Shell. Search and filters live in `AppSessionState` and survive local changes and route reconstruction.

Migration `0006_standalone_tasks` rebuilds only `tasks` so `project_id` is nullable. The migration runner creates and validates a SQLite backup before applying it, temporarily disables foreign-key actions only for the table rebuild, immediately restores them, and validates integrity and foreign keys. Existing Task IDs, Project links, TaskPlan rows, Blockers, histories, and Cycle junctions are preserved.

Standalone Quick Tasks without a planned date begin in Backlog and have no TaskPlan. Adding a planned date creates a current plan without a Today group or position. Definition of Done remains optional until Primary or Milestone assignment.

Historical note: U2 also canonicalized `/` to `/dashboard` for the then-supported web preview. Root canonicalization and mounted-shell preservation remain current desktop behavior, but web/browser launch support is retired and `--web`/`--port` are intentionally rejected.
