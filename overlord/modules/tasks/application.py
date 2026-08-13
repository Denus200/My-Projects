from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time

from overlord.app.read_models import TaskListItem
from overlord.app.unit_of_work import UnitOfWorkFactory
from overlord.modules.blockers.domain import Blocker, BlockerType
from overlord.modules.cycles.domain import CycleStatus
from overlord.modules.definition_of_done import require_definition_of_done
from overlord.modules.tasks.domain import (
    Task,
    TaskBoardColumn,
    TaskLifecycle,
    is_scheduled_for_day,
    require_task_title,
    validate_estimate,
    validate_schedule,
)
from overlord.modules.tasks.read_models import TaskEditorData


def order_tasks_for_day(
    items: tuple[TaskListItem, ...] | list[TaskListItem],
    positions: dict[int, int],
) -> tuple[TaskListItem, ...]:
    def automatic(item: TaskListItem) -> tuple[object, ...]:
        task = item.task
        if task.lifecycle_status is TaskLifecycle.COMPLETED:
            completed_at = task.completed_at or task.updated_at
            return (0, -completed_at.timestamp(), task.id)
        if task.schedule_start_time is not None:
            return (1, 0, task.schedule_start_time, task.created_at, task.id)
        return (1, 1, time.max, task.created_at, task.id)

    automatic_order = sorted(items, key=automatic)
    if not positions:
        return tuple(automatic_order)
    automatic_rank = {item.task.id: index for index, item in enumerate(automatic_order)}
    return tuple(
        sorted(
            automatic_order,
            key=lambda item: (
                0,
                positions[item.task.id],
            ) if item.task.id in positions else (
                1,
                automatic_rank[item.task.id],
            ),
        )
    )


@dataclass(frozen=True, slots=True)
class CreateTask:
    uow_factory: UnitOfWorkFactory

    def execute(
        self,
        project_id: int | None,
        title: str,
        *,
        description: str = "",
        schedule_start_date: date | None = None,
        schedule_start_time: time | None = None,
        schedule_end_date: date | None = None,
        schedule_end_time: time | None = None,
        deadline_at: datetime | None = None,
        definition_of_done: str | None = None,
        next_action: str | None = None,
        importance: bool | None = None,
        urgency: bool | None = None,
        estimate_minutes: int | None = None,
        milestone_id: int | None = None,
        blocker_type: BlockerType | None = None,
        blocker_description: str | None = None,
        cycle_ids: tuple[int, ...] = (),
    ) -> Task:
        clean_title = require_task_title(title)
        validate_schedule(
            schedule_start_date,
            schedule_start_time,
            schedule_end_date,
            schedule_end_time,
            deadline_at,
        )
        estimate = validate_estimate(estimate_minutes)
        clean_blocker = (blocker_description or "").strip()
        if blocker_type is not None and not clean_blocker:
            raise ValueError("Blocker description is required.")
        if clean_blocker and blocker_type is None:
            blocker_type = BlockerType.OTHER
        if milestone_id is not None:
            require_definition_of_done(definition_of_done, context="attaching to a Milestone")
        lifecycle = TaskLifecycle.PLANNED if schedule_start_date else TaskLifecycle.BACKLOG
        with self.uow_factory() as uow:
            if project_id is not None and not uow.projects.get(project_id):
                raise ValueError(f"Project {project_id} does not exist.")
            for cycle_id in cycle_ids:
                cycle = uow.cycles.get(cycle_id)
                if not cycle:
                    raise ValueError(f"Cycle {cycle_id} does not exist.")
                if cycle.status is CycleStatus.ARCHIVED:
                    raise ValueError("Archived Cycles are read-only until restored.")
            task = uow.tasks.create(
                project_id,
                clean_title,
                lifecycle,
                description=description.strip(),
                schedule_start_date=schedule_start_date,
                schedule_start_time=schedule_start_time,
                schedule_end_date=schedule_end_date,
                schedule_end_time=schedule_end_time,
                deadline_at=deadline_at,
                definition_of_done=(definition_of_done or "").strip() or None,
                next_action=(next_action or "").strip() or None,
                importance=importance,
                urgency=urgency,
                estimate_minutes=estimate,
                milestone_id=milestone_id,
            )
            if blocker_type is not None:
                uow.blockers.open_blocker(task.id, blocker_type, clean_blocker)
            uow.cycles.replace_task_cycles(task.id, cycle_ids)
            return uow.tasks.get(task.id)


@dataclass(frozen=True, slots=True)
class UpdateTask:
    uow_factory: UnitOfWorkFactory

    def execute(self, task_id: int, **changes: object) -> Task:
        cycle_ids = changes.pop("cycle_ids", None)
        if "title" in changes:
            changes["title"] = require_task_title(str(changes["title"]))
        if "estimate_minutes" in changes:
            changes["estimate_minutes"] = validate_estimate(changes["estimate_minutes"])
        with self.uow_factory() as uow:
            current = uow.tasks.get(task_id)
            if not current:
                raise ValueError(f"Task {task_id} does not exist.")
            effective_dod = changes.get("definition_of_done", current.definition_of_done)
            if "project_id" in changes:
                project_id = changes["project_id"]
                if project_id is not None and not uow.projects.get(int(project_id)):
                    raise ValueError(f"Project {project_id} does not exist.")
            if changes.get("milestone_id", current.milestone_id) is not None:
                require_definition_of_done(effective_dod, context="attaching to a Milestone")
            start_date = changes.get("schedule_start_date", current.schedule_start_date)
            start_time = changes.get("schedule_start_time", current.schedule_start_time)
            end_date = changes.get("schedule_end_date", current.schedule_end_date)
            end_time = changes.get("schedule_end_time", current.schedule_end_time)
            deadline_at = changes.get("deadline_at", current.deadline_at)
            validate_schedule(start_date, start_time, end_date, end_time, deadline_at)
            if cycle_ids is not None:
                current_cycle_ids = set(uow.cycles.cycle_ids_for_task(task_id))
                for cycle_id in cycle_ids:
                    cycle = uow.cycles.get(int(cycle_id))
                    if not cycle:
                        raise ValueError(f"Cycle {cycle_id} does not exist.")
                    if cycle.status is CycleStatus.ARCHIVED and int(cycle_id) not in current_cycle_ids:
                        raise ValueError("Archived Cycles are read-only until restored.")
            updated = uow.tasks.update(task_id, **changes)
            if cycle_ids is not None:
                uow.cycles.replace_task_cycles(task_id, tuple(int(value) for value in cycle_ids))
            return updated


@dataclass(frozen=True, slots=True)
class ChangeTaskLifecycle:
    uow_factory: UnitOfWorkFactory

    def execute(self, task_id: int, lifecycle: TaskLifecycle, reason: str | None = None) -> Task:
        with self.uow_factory() as uow:
            return uow.tasks.change_lifecycle(task_id, lifecycle, reason)


@dataclass(frozen=True, slots=True)
class CompleteTask:
    uow_factory: UnitOfWorkFactory

    def execute(self, task_id: int) -> Task:
        with self.uow_factory() as uow:
            return uow.tasks.change_lifecycle(task_id, TaskLifecycle.COMPLETED, "Completed")


@dataclass(frozen=True, slots=True)
class ReorderTasksForDay:
    uow_factory: UnitOfWorkFactory

    def execute(self, day: date, task_ids: tuple[int, ...]) -> None:
        if len(task_ids) != len(set(task_ids)):
            raise ValueError("Task day order cannot contain duplicates.")
        with self.uow_factory() as uow:
            current = tuple(
                item.task.id
                for item in uow.tasks.list(schedule_date=day)
                if item.task.lifecycle_status is not TaskLifecycle.CANCELLED
            )
            if set(current) != set(task_ids):
                raise ValueError("Task day order must contain every Task scheduled for that day.")
            uow.tasks.replace_day_order(day, task_ids)


@dataclass(frozen=True, slots=True)
class ToggleTaskCompletionForDay:
    uow_factory: UnitOfWorkFactory

    def execute(self, task_id: int, day: date) -> Task:
        with self.uow_factory() as uow:
            current = uow.tasks.get(task_id)
            if not current:
                raise ValueError(f"Task {task_id} does not exist.")
            if current.lifecycle_status is TaskLifecycle.CANCELLED or not is_scheduled_for_day(current, day):
                raise ValueError("Task is not active on the selected day.")
            ordered = order_tasks_for_day(
                tuple(
                    item
                    for item in uow.tasks.list(schedule_date=day)
                    if item.task.lifecycle_status is not TaskLifecycle.CANCELLED
                ),
                uow.tasks.day_positions(day),
            )
            if current.lifecycle_status is TaskLifecycle.COMPLETED:
                updated = uow.tasks.change_lifecycle(task_id, TaskLifecycle.PLANNED, "Reopened from Dashboard")
                next_order = tuple(item.task.id for item in ordered)
            else:
                updated = uow.tasks.change_lifecycle(task_id, TaskLifecycle.COMPLETED, "Completed from Dashboard")
                next_order = (task_id, *(item.task.id for item in ordered if item.task.id != task_id))
            uow.tasks.replace_day_order(day, tuple(next_order))
            return updated


@dataclass(frozen=True, slots=True)
class MoveTaskToBoardColumn:
    uow_factory: UnitOfWorkFactory

    def execute(
        self,
        task_id: int,
        target: TaskBoardColumn,
        *,
        selected_day: date | None = None,
    ) -> Task:
        if target is TaskBoardColumn.MISSED:
            raise ValueError("Not completed is derived from an expired end time or deadline.")
        day = selected_day or date.today()
        with self.uow_factory() as uow:
            current = uow.tasks.get(task_id)
            if not current:
                raise ValueError(f"Task {task_id} does not exist.")
            if target is TaskBoardColumn.COMPLETED:
                return uow.tasks.change_lifecycle(task_id, TaskLifecycle.COMPLETED, "Moved on Kanban")
            if target is TaskBoardColumn.ARCHIVE:
                return uow.tasks.change_lifecycle(task_id, TaskLifecycle.CANCELLED, "Moved on Kanban")
            if target is TaskBoardColumn.PLANNED:
                uow.tasks.update(
                    task_id,
                    schedule_start_date=None,
                    schedule_start_time=None,
                    schedule_end_date=None,
                    schedule_end_time=None,
                    deadline_at=None,
                )
                return uow.tasks.change_lifecycle(task_id, TaskLifecycle.BACKLOG, "Moved on Kanban")
            uow.tasks.update(
                task_id,
                schedule_start_date=day,
                schedule_end_date=None,
                schedule_end_time=None,
                deadline_at=None,
            )
            return uow.tasks.change_lifecycle(task_id, TaskLifecycle.PLANNED, "Moved on Kanban")


@dataclass(frozen=True, slots=True)
class OpenBlocker:
    uow_factory: UnitOfWorkFactory

    def execute(self, task_id: int, blocker_type: BlockerType, description: str) -> Blocker:
        clean = description.strip()
        if not clean:
            raise ValueError("Blocker description is required.")
        with self.uow_factory() as uow:
            if not uow.tasks.get(task_id):
                raise ValueError(f"Task {task_id} does not exist.")
            return uow.blockers.open_blocker(task_id, blocker_type, clean)


@dataclass(frozen=True, slots=True)
class ResolveBlocker:
    uow_factory: UnitOfWorkFactory

    def execute(self, blocker_id: int, resolution: str) -> Blocker:
        clean = resolution.strip()
        if not clean:
            raise ValueError("Blocker resolution is required.")
        with self.uow_factory() as uow:
            return uow.blockers.resolve_blocker(blocker_id, clean)


@dataclass(frozen=True, slots=True)
class ListTasksQuery:
    uow_factory: UnitOfWorkFactory

    def execute(self, **filters: object) -> tuple[TaskListItem, ...]:
        with self.uow_factory(read_only=True) as uow:
            return tuple(uow.tasks.list(**filters))


@dataclass(frozen=True, slots=True)
class GetTaskEditorQuery:
    uow_factory: UnitOfWorkFactory

    def execute(self, task_id: int) -> TaskEditorData:
        with self.uow_factory(read_only=True) as uow:
            task = uow.tasks.get(task_id)
            if not task:
                raise ValueError(f"Task {task_id} does not exist.")
            return TaskEditorData(
                task,
                tuple(uow.blockers.list_blockers(task_id)),
                tuple(uow.tasks.status_history(task_id)),
                uow.cycles.cycle_ids_for_task(task_id),
            )


@dataclass(frozen=True, slots=True)
class TaskApplication:
    create_task: CreateTask
    update_task: UpdateTask
    change_lifecycle: ChangeTaskLifecycle
    complete_task: CompleteTask
    reorder_for_day: ReorderTasksForDay
    toggle_completion_for_day: ToggleTaskCompletionForDay
    move_to_board_column: MoveTaskToBoardColumn
    open_blocker: OpenBlocker
    resolve_blocker: ResolveBlocker
    list_tasks: ListTasksQuery
    get_editor: GetTaskEditorQuery
