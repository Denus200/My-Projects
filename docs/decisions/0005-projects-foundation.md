# Decision 0005 — Projects foundation and normalized Task membership

Date: 2026-08-21

## Decision

A canonical Task may be standalone or belong to at most four Projects. Membership is stored in `task_project_links`, where `(task_id, project_id)` is unique, link position is unique per Task, and each link may reference zero or one Stage. A referenced Stage must belong to the same Project and must not be archived. The legacy nullable `tasks.project_id` column remains temporarily as a first-link compatibility shadow; normalized links are the source of truth.

Projects persist an actual color value and an independent Favorite flag. Project colors are reusable and are exposed through immutable Task read models so the shared Task Card can render zero to four real Project indicators.

A Project Plan is a Project-owned execution plan and is not a global 12-week Cycle. A Project may have one active Project Plan, and that plan owns ordered Stages. Archiving a Stage clears its Task-link Stage assignments without deleting Tasks or their Project links. Archiving a Project is reversible and never deletes linked Tasks.

Project notes and imported files remain local. Markdown and attachment contents live beneath a database-adjacent `project-workspaces` directory; SQLite stores metadata and safe relative paths, not file blobs.

## Migration and compatibility

Forward-only migration `0010_projects_foundation` adds the new Project columns and normalized tables. It copies every existing non-null legacy Task Project association into link position one with `INSERT OR IGNORE`, preserving Tasks, Projects, ordering, lifecycle, and scheduling. SQLite constraints and triggers enforce the four-Project maximum and same-Project Stage ownership even if Application validation is bypassed.

## Consequences

Project-scoped queries aggregate only explicitly linked Tasks. A Task linked to several Projects contributes to each of those Project views, while global analytics must continue to count the canonical Task once. The unfinished Create Task redesign is deferred; current single-Project forms remain compatible through the first-link shadow while Application commands already accept the normalized relationship model.
