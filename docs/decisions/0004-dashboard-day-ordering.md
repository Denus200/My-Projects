# Decision 0004 — Persistent per-day Dashboard Task ordering

Date: 2026-08-13

## Context

The Dashboard now presents scheduled Tasks across Yesterday, Today, and Tomorrow. Automatic ordering gives a useful first position, but the user also needs to reorder a day's Tasks manually and keep that order after restarting the application.

## Decision

Task scheduling remains canonical on `Task`. A small Task-owned `task_day_positions` table stores only the explicit presentation order for a Task on a particular calendar day. It does not assign Tasks to days, duplicate schedules, create Dashboard entities, or replace the date-driven query.

When a day has no saved order, completed Tasks appear first, then incomplete timed Tasks in ascending time order, then incomplete untimed Tasks in creation order. A manual reorder persists the full visible order. Completing a Task moves it to the top and persists that position; reopening it preserves its current position.

Migration `0009_task_day_ordering` creates the table and its day/position index. Range Tasks may have a different explicit position on each day in their range.

## Consequences

- Dashboard still owns no Task membership or scheduling data.
- Blocked and Paused Tasks may be absent from the actionable Dashboard day list while retaining their schedule and stored day position. Reordering the visible subset merges that order around hidden Tasks rather than deleting their presentation metadata.
- Manual ordering survives re-rendering and application restart.
- New Tasks without an explicit position are appended after an already customized order.
- Cross-day dragging remains outside this decision; changing dates continues through Task editing.
