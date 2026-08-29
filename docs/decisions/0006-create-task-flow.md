# Decision 0006: Create Task flow

Date: 2026-08-21

## Decision

Create Task is one state-driven desktop modal shared by Tasks, Dashboard, and Project Tasks. Its base state contains Title, Description, Date, creation intent, and actions. Advanced options progressively reveal zero-to-four Projects, optional same-Project Stage assignments, Deadline, Estimated Time, and Checklist. Date and Deadline use one calendar component; Deadline enables the time row.

Normal and Draft are creation modes, not Task lifecycle states. Normal Tasks enter the existing schedule-derived workflow. Draft Tasks retain an ordinary Task lifecycle and canonical schedule but are omitted from normal Task browsing, Dashboard metrics, and Project execution summaries unless a query explicitly requests drafts.

Estimated Time remains the nullable `planned_minutes` duration in total minutes. Missing input persists `NULL`; an entered zero duration is rejected by the existing positive-estimate rule. Deadline remains a concrete datetime and is independent from duration and Date.

Forward-only migration `0011_create_task_flow` adds `tasks.creation_mode` and `task_checklist_items`. Checklist items support nested parent relationships, completion state, stable sibling position, and same-Task parent guards. CreateTask validates Project/Stage ownership and Checklist values, then saves the Task, Project links, Checklist, Blocker, and Cycle links inside one existing Unit of Work transaction.

## Consequences

- The normalized `task_project_links` architecture remains authoritative; no duplicate Task or relationship model is introduced.
- Removing a Project from transient form state clears only that Project's Stage selection.
- Task Details, Complete Task, Total Time, Active Time, and 12-Week Plan selection are not part of this decision.
- Existing Task Card, Dashboard, Projects presentation, and Kanban composition remain unchanged.
