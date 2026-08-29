# Decision 0008: Complete Task flow

Date: 2026-08-21

## Decision

Every Presentation completion entry point uses one canonical Complete Task modal. Task Details, the Dashboard three-day board, Tasks/Kanban (including a drag into Completed), and Project Tasks open the same component; opening, cancelling, or closing it changes no persisted state.

Confirmation invokes one Application command and one Unit of Work. That transaction persists lifecycle completion and any optional duration values together. An existing Estimated Time is shown read-only and cannot be replaced during completion; a missing estimate may be entered. Total Time and Active Time are independent, optional manual values. No comparison between Total and Active is imposed. All three values use the shared hours/minutes control and are stored as nullable total minutes.

Forward-only migration `0013_complete_task_flow` adds nullable, positive-when-present `tasks.total_time_minutes` and `tasks.active_time_minutes` columns. Existing rows receive `NULL`. Reopening a completed Task preserves all duration values, as do Project, Stage, Cycle, Blocker, and Checklist relationships. Direct non-Presentation completion callers preserve previously stored completion durations when they omit those arguments.

Dashboard-selected completion also moves the completed Task to the top of that day inside the same transaction. Existing completed controls continue to reopen Tasks through their established route behavior; they do not open a second completion modal.

## Consequences

- Completion can no longer be selected as an ordinary Task Details save; it must be confirmed through Complete Task.
- Tasks/Kanban and Project Tasks retain their shared Task entity and views. The modal does not introduce a completion-specific entity or repository.
- Work Sessions, timers, inferred time, analytics, and automatic duration calculations remain outside this decision.
- Production migration QA runs against a disposable copy; `data/overlord.db` is never migrated by tests or capture scripts.
