from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from overlord.app.services import ApplicationServices


def moved_task_ids(
    task_ids: tuple[int, ...] | list[int],
    task_id: int,
    before_task_id: int | None,
) -> tuple[int, ...]:
    """Return one stable task order with ``task_id`` moved before its target."""
    if task_id not in task_ids or before_task_id == task_id:
        return tuple(task_ids)
    moved = [candidate for candidate in task_ids if candidate != task_id]
    if before_task_id in moved:
        moved.insert(moved.index(before_task_id), task_id)
    else:
        moved.append(task_id)
    return tuple(moved)


@dataclass(frozen=True, slots=True)
class TaskOrderController:
    """Shared Presentation boundary for persisted per-day Task ordering."""

    services: ApplicationServices

    def persist_for_day(self, day: date, task_ids: tuple[int, ...]) -> None:
        if task_ids:
            self.services.tasks.reorder_for_day.execute(day, task_ids)

    def move_before_for_day(
        self,
        day: date,
        task_ids: tuple[int, ...],
        task_id: int,
        before_task_id: int | None,
    ) -> tuple[int, ...]:
        moved = moved_task_ids(task_ids, task_id, before_task_id)
        if moved != task_ids:
            self.persist_for_day(day, moved)
        return moved
