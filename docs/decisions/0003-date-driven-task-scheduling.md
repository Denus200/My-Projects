# Decision 0003: Date-driven Task scheduling

Date: 2026-08-13

Status: Approved and implemented for Stage 1

## Context

The Foundation daily-planning workflow required a Task to be assigned to one of three Primary or four Secondary slots before it appeared on the Dashboard. This made a Task's own date insufficient, imposed an artificial daily capacity, and split task management between Tasks and a separate Daily Planning screen.

## Decision

Task is the single scheduling source of truth. A Task may have a start date and time, an optional end date and time, and an optional deadline. A Task scheduled for one date appears on that date; a Task with a date range appears on every date in the inclusive range. Dashboard derives its Today list from this schedule and does not own or persist assignments.

Primary and Secondary slots, their capacity rules, the Daily Planning route, and the Dashboard's Plan the day action are removed from current product behavior. The Tasks area owns task creation and future planning.

Board placement is derived, not independently editable: future or undated work is Planned; work active on the current date is In progress; work past an end date/time or deadline is Not completed; completed work is Completed; and a past one-date task without an end or deadline is Archive. Recurring actions are explicitly outside this stage.

## Data compatibility

Migration `0008_date_driven_tasks` adds canonical schedule fields to `tasks`. The current date from each legacy `task_plans` record is copied to `tasks.schedule_start_date`. The `task_plans` table remains intact as historical evidence, but runtime repositories and services no longer read or write it.

The legacy non-null `tasks.scheduled_date` column remains as a storage-compatibility field until a future table-rebuild migration. It does not control product scheduling.

## Consequences

- All Tasks scheduled for a date appear on the Dashboard; there is no 3+4 limit.
- Creating or editing a Task is sufficient to schedule it.
- Completion remains an explicit user action; other board states follow schedule and current time.
- Kanban, week, and month presentation are implemented in Stage 2 and consume the same canonical fields and derived rules.
- Historical slot data is preserved without keeping the obsolete workflow alive.

## Stage 2 interaction model

Tasks is the only planning workspace. Its Kanban view groups the complete task set into the five derived columns. Its week and month views project scheduled Tasks onto every date covered by their inclusive range. Creating from Planned leaves the Task undated; creating from Today or a calendar day supplies that date to the same visible task form.

Project and 12-week Cycle membership are relationships of the canonical Task. They appear on cards and in the task window; neither creates a separate Task subtype. Recurring actions remain outside Tasks.

Kanban cards and column headers are directly draggable. Card moves to Planned, In progress, Completed, and Archive update canonical Task state; Not completed remains derived and cannot be assigned manually. Card and column ordering is retained for the active desktop session.
