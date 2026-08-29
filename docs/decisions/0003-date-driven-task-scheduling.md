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

Tasks is the only planning workspace. Its My Tasks/Kanban view projects the complete task set into four visible columns: Planned, In Progress, Needs Attention, and Completed. Needs Attention groups the canonical Not completed and Archive placements with Paused Tasks and Tasks that have open Blockers; it remains derived and cannot be assigned manually. The canonical placement and lifecycle models remain unchanged. Week and month views project scheduled Tasks onto every date covered by their inclusive range. Creating from Planned leaves the Task undated; creating from Today or a calendar day supplies that date to the same visible task form.

The Week presentation is one horizontally scrolling seven-day sequence. Each date owns a fixed 300-pixel column and an independently scrolling visible Task list; Search and normalized Project filters alter only the projection and count. Week and Month reuse one expandable date-navigation Tabs interaction whose expansion state resets whenever the active view changes. Week cross-day drag-and-drop is not introduced here because no canonical Week move command existed; Task Details remains the supported persisted date-change flow.

The Month presentation is a responsive Monday-through-Sunday calendar matrix derived with standard calendar/date utilities. It includes real leading and trailing dates, dynamically marks today, and renders dated Planned, In Progress, Paused, Blocked, and Completed Tasks through the shared compact Task Card. Calendar cells retain a fixed usable height and independently scroll their Task content so busy dates cannot stretch an entire row. Search and normalized multi-Project filtering change only visible Task content; the calendar matrix remains. Month cross-date drag-and-drop is not introduced because no canonical Month move command exists; Task Details remains the supported persisted date-change flow.

Project and 12-week Cycle membership are relationships of the canonical Task. They appear on cards and in the task window; neither creates a separate Task subtype. Recurring actions remain outside Tasks.

Kanban cards and column headers are directly draggable. Card moves to Planned, In progress, and Completed update canonical Task state; the grouped Needs Attention destination is derived and cannot be assigned manually. Cards currently in Needs Attention can move out through valid canonical transitions. Card and column ordering is retained for the active desktop session.
