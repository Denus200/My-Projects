# Decision 0007: Task Details flow

Date: 2026-08-21

## Decision

Task Details is one reusable desktop modal for Dashboard cards, the Tasks Kanban/week/month workspace, and Project Task deep links. It edits the existing canonical Task and the same persisted fields used by Create Task: Title, Description, Date, Deadline, zero-to-four Project links, one optional same-Project Stage per link, nullable Estimated Time, nested Checklist, and lifecycle status.

`UpdateTaskDetails` validates the complete form before opening one Unit of Work, then updates Task fields, normalized Project/Stage assignments, stable-ID Checklist rows, Blockers used for the derived Blocked state, and lifecycle history atomically. Cancel and close do not invoke that command. Draft creation mode is preserved unless a future explicit publishing decision says otherwise.

The manually selectable working states are Planned, In progress, Blocked, and Paused. Completed continues to use the existing lifecycle completion semantics and may be reopened to Planned. Blocked is still derived from open Blockers rather than stored in `tasks.lifecycle_status`; selecting Blocked opens a Task-owned Blocker when necessary, and selecting another working state resolves open Blockers. Paused is persisted as a lifecycle state through forward-only migration `0012_task_details_flow`.

Checklist synchronization retains IDs for existing items, inserts only new items, updates parent/position/completion in place, and removes only omitted items. Explicit Task deletion first disconnects `cycle_tasks`, whose foreign key intentionally uses `RESTRICT`, then deletes the Task so declared cascades remove Task-owned plans, status history, Blockers, day ordering, Project links, and Checklist rows. Projects, Stages, and Cycles remain intact.

## Consequences

- Dashboard and Tasks no longer maintain separate legacy Task editing forms.
- Create Task and Task Details share the established calendar, tooltip, icon-action, Project count, and Project Stage labeling infrastructure without changing Create Task presentation.
- Cycle/12-Week relationship editing is not part of this tranche; existing Cycle links are preserved by Task Details saves.
- Total Time, Active Time, the completion-time modal, and final estimate locking were deferred here and are subsequently defined by Decision 0008.
- The production database path and desktop-only runtime are unchanged; migration verification runs only on disposable copies.
