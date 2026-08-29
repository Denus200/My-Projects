from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time

from overlord.app.read_models import TaskListItem
from overlord.app.unit_of_work import UnitOfWorkFactory
from overlord.modules.blockers.domain import Blocker, BlockerType
from overlord.modules.cycles.domain import CycleStatus
from overlord.modules.definition_of_done import require_definition_of_done
from overlord.modules.tasks.domain import (
    ChecklistItemDraft,
    Task,
    TaskBoardColumn,
    TaskCreationMode,
    TaskDetailsStatus,
    TaskLifecycle,
    TaskProjectAssignment,
    is_scheduled_for_day,
    require_task_title,
    validate_completion_duration,
    validate_estimate,
    validate_checklist,
    validate_schedule,
)
from overlord.modules.tasks.read_models import TaskEditorData


_UNCHANGED = object()


def _normalize_project_assignments(
    project_id: int | None,
    assignments: tuple[TaskProjectAssignment, ...] | None,
) -> tuple[TaskProjectAssignment, ...]:
    normalized = assignments if assignments is not None else (
        (TaskProjectAssignment(project_id),) if project_id is not None else ()
    )
    if len(normalized) > 4:
        raise ValueError("A Task may belong to at most 4 Projects.")
    project_ids = tuple(assignment.project_id for assignment in normalized)
    if len(project_ids) != len(set(project_ids)):
        raise ValueError("A Task cannot link to the same Project more than once.")
    return normalized


def _validate_project_assignments(uow, assignments: tuple[TaskProjectAssignment, ...]) -> None:
    for assignment in assignments:
        if not uow.projects.get(assignment.project_id):
            raise ValueError(f"Project {assignment.project_id} does not exist.")
        if assignment.stage_id is None:
            continue
        stage = uow.projects.get_stage(assignment.stage_id)
        if not stage:
            raise ValueError(f"Stage {assignment.stage_id} does not exist.")
        if stage.project_id != assignment.project_id:
            raise ValueError("Task Stage must belong to the linked Project.")
        if stage.status.value == "archived":
            raise ValueError("Archived Stages cannot be assigned to Tasks.")


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
        project_links: tuple[TaskProjectAssignment, ...] | None = None,
        creation_mode: TaskCreationMode = TaskCreationMode.NORMAL,
        checklist_items: tuple[ChecklistItemDraft, ...] = (),
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
        mode = TaskCreationMode(creation_mode)
        checklist = validate_checklist(checklist_items)
        clean_blocker = (blocker_description or "").strip()
        if blocker_type is not None and not clean_blocker:
            raise ValueError("Blocker description is required.")
        if clean_blocker and blocker_type is None:
            blocker_type = BlockerType.OTHER
        if milestone_id is not None:
            require_definition_of_done(definition_of_done, context="attaching to a Milestone")
        lifecycle = TaskLifecycle.PLANNED if schedule_start_date else TaskLifecycle.BACKLOG
        assignments = _normalize_project_assignments(project_id, project_links)
        with self.uow_factory() as uow:
            _validate_project_assignments(uow, assignments)
            for cycle_id in cycle_ids:
                cycle = uow.cycles.get(cycle_id)
                if not cycle:
                    raise ValueError(f"Cycle {cycle_id} does not exist.")
                if cycle.status is CycleStatus.ARCHIVED:
                    raise ValueError("Archived Cycles are read-only until restored.")
            task = uow.tasks.create(
                assignments[0].project_id if assignments else None,
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
                creation_mode=mode,
            )
            uow.tasks.replace_project_links(task.id, assignments)
            uow.tasks.replace_checklist(task.id, checklist)
            if blocker_type is not None:
                uow.blockers.open_blocker(task.id, blocker_type, clean_blocker)
            uow.cycles.replace_task_cycles(task.id, cycle_ids)
            return uow.tasks.get(task.id)


@dataclass(frozen=True, slots=True)
class UpdateTask:
    uow_factory: UnitOfWorkFactory

    def execute(self, task_id: int, **changes: object) -> Task:
        cycle_ids = changes.pop("cycle_ids", None)
        explicit_project_links = changes.pop("project_links", None)
        project_change_supplied = "project_id" in changes
        project_id_change = changes.pop("project_id", None) if project_change_supplied else None
        if "title" in changes:
            changes["title"] = require_task_title(str(changes["title"]))
        if "estimate_minutes" in changes:
            changes["estimate_minutes"] = validate_estimate(changes["estimate_minutes"])
        with self.uow_factory() as uow:
            current = uow.tasks.get(task_id)
            if not current:
                raise ValueError(f"Task {task_id} does not exist.")
            effective_dod = changes.get("definition_of_done", current.definition_of_done)
            assignments = None
            if explicit_project_links is not None or project_change_supplied:
                assignments = _normalize_project_assignments(
                    int(project_id_change) if project_id_change is not None else None,
                    tuple(explicit_project_links) if explicit_project_links is not None else None,
                )
                _validate_project_assignments(uow, assignments)
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
            if assignments is not None:
                uow.tasks.replace_project_links(task_id, assignments)
                updated = uow.tasks.get(task_id)
            if cycle_ids is not None:
                uow.cycles.replace_task_cycles(task_id, tuple(int(value) for value in cycle_ids))
            return updated


@dataclass(frozen=True, slots=True)
class UpdateTaskDetails:
    """Atomically save the shared Task Details form."""

    uow_factory: UnitOfWorkFactory

    def execute(
        self,
        task_id: int,
        *,
        title: str,
        description: str,
        schedule_start_date: date | None,
        deadline_at: datetime | None,
        estimate_minutes: int | None,
        project_links: tuple[TaskProjectAssignment, ...],
        checklist_items: tuple[ChecklistItemDraft, ...],
        status: TaskDetailsStatus | None = None,
    ) -> Task:
        clean_title = require_task_title(title)
        estimate = validate_estimate(estimate_minutes)
        assignments = _normalize_project_assignments(None, project_links)
        checklist = validate_checklist(checklist_items)
        selected_status = TaskDetailsStatus(status) if status is not None else None
        if selected_status is TaskDetailsStatus.CANCELLED:
            raise ValueError("Cancelled is not a manually selectable Task Details status.")
        if selected_status is TaskDetailsStatus.COMPLETED:
            raise ValueError("Completed must be confirmed through Complete Task.")

        with self.uow_factory() as uow:
            current = uow.tasks.get(task_id)
            if not current:
                raise ValueError(f"Task {task_id} does not exist.")
            _validate_project_assignments(uow, assignments)
            end_date = current.schedule_end_date if schedule_start_date == current.schedule_start_date else None
            end_time = current.schedule_end_time if schedule_start_date == current.schedule_start_date else None
            validate_schedule(
                schedule_start_date,
                current.schedule_start_time,
                end_date,
                end_time,
                deadline_at,
            )
            uow.tasks.update(
                task_id,
                title=clean_title,
                description=description.strip(),
                schedule_start_date=schedule_start_date,
                schedule_end_date=end_date,
                schedule_end_time=end_time,
                deadline_at=deadline_at,
                estimate_minutes=estimate,
            )
            uow.tasks.replace_project_links(task_id, assignments)
            uow.tasks.replace_checklist(task_id, checklist)

            if selected_status is not None:
                open_blockers = tuple(uow.blockers.list_blockers(task_id, open_only=True))
                if selected_status is TaskDetailsStatus.BLOCKED:
                    if current.lifecycle_status in {TaskLifecycle.COMPLETED, TaskLifecycle.CANCELLED}:
                        uow.tasks.change_lifecycle(task_id, TaskLifecycle.PLANNED, "Reopened in Task Details")
                    if not open_blockers:
                        uow.blockers.open_blocker(
                            task_id,
                            BlockerType.OTHER,
                            "Marked blocked in Task Details",
                        )
                else:
                    for blocker in open_blockers:
                        uow.blockers.resolve_blocker(blocker.id, "Status changed in Task Details")
                    target = {
                        TaskDetailsStatus.PLANNED: TaskLifecycle.PLANNED,
                        TaskDetailsStatus.IN_PROGRESS: TaskLifecycle.IN_PROGRESS,
                        TaskDetailsStatus.PAUSED: TaskLifecycle.PAUSED,
                    }[selected_status]
                    if current.lifecycle_status is not target:
                        uow.tasks.change_lifecycle(task_id, target, "Changed in Task Details")
            return uow.tasks.get(task_id)


@dataclass(frozen=True, slots=True)
class DeleteTask:
    uow_factory: UnitOfWorkFactory

    def execute(self, task_id: int) -> None:
        with self.uow_factory() as uow:
            uow.tasks.delete(task_id)


@dataclass(frozen=True, slots=True)
class ChangeTaskLifecycle:
    uow_factory: UnitOfWorkFactory

    def execute(self, task_id: int, lifecycle: TaskLifecycle, reason: str | None = None) -> Task:
        with self.uow_factory() as uow:
            return uow.tasks.change_lifecycle(task_id, lifecycle, reason)


def _complete_task_in_uow(
    uow,
    task_id: int,
    *,
    estimate_minutes: int | None | object = _UNCHANGED,
    total_time_minutes: int | None | object = _UNCHANGED,
    active_time_minutes: int | None | object = _UNCHANGED,
    selected_day: date | None = None,
    reason: str,
) -> Task:
    current = uow.tasks.get(task_id)
    if not current:
        raise ValueError(f"Task {task_id} does not exist.")
    if current.lifecycle_status is TaskLifecycle.COMPLETED:
        return current
    if selected_day is not None and not is_scheduled_for_day(current, selected_day):
        raise ValueError("Task is not active on the selected day.")

    if current.estimate_minutes is not None:
        estimate = current.estimate_minutes
    elif estimate_minutes is _UNCHANGED:
        estimate = None
    else:
        estimate = validate_estimate(estimate_minutes)
    total = (
        current.total_time_minutes
        if total_time_minutes is _UNCHANGED
        else validate_completion_duration(total_time_minutes, field="total_time", label="Total Time")
    )
    active = (
        current.active_time_minutes
        if active_time_minutes is _UNCHANGED
        else validate_completion_duration(active_time_minutes, field="active_time", label="Active Time")
    )

    uow.tasks.update(
        task_id,
        estimate_minutes=estimate,
        total_time_minutes=total,
        active_time_minutes=active,
    )
    completed = uow.tasks.change_lifecycle(task_id, TaskLifecycle.COMPLETED, reason)
    if selected_day is not None:
        ordered = order_tasks_for_day(
            tuple(
                item
                for item in uow.tasks.list(schedule_date=selected_day)
                if item.task.lifecycle_status is not TaskLifecycle.CANCELLED
            ),
            uow.tasks.day_positions(selected_day),
        )
        uow.tasks.replace_day_order(
            selected_day,
            (task_id, *(item.task.id for item in ordered if item.task.id != task_id)),
        )
    return completed


@dataclass(frozen=True, slots=True)
class CompleteTask:
    uow_factory: UnitOfWorkFactory

    def execute(
        self,
        task_id: int,
        *,
        estimate_minutes: int | None | object = _UNCHANGED,
        total_time_minutes: int | None | object = _UNCHANGED,
        active_time_minutes: int | None | object = _UNCHANGED,
        selected_day: date | None = None,
    ) -> Task:
        with self.uow_factory() as uow:
            return _complete_task_in_uow(
                uow,
                task_id,
                estimate_minutes=estimate_minutes,
                total_time_minutes=total_time_minutes,
                active_time_minutes=active_time_minutes,
                selected_day=selected_day,
                reason="Completed",
            )


@dataclass(frozen=True, slots=True)
class ReorderTasksForDay:
    uow_factory: UnitOfWorkFactory

    def execute(self, day: date, task_ids: tuple[int, ...]) -> None:
        if len(task_ids) != len(set(task_ids)):
            raise ValueError("Task day order cannot contain duplicates.")
        with self.uow_factory() as uow:
            current = order_tasks_for_day(
                tuple(
                    item
                    for item in uow.tasks.list(schedule_date=day)
                    if item.task.lifecycle_status is not TaskLifecycle.CANCELLED
                ),
                uow.tasks.day_positions(day),
            )
            current_ids = tuple(item.task.id for item in current)
            if not set(task_ids).issubset(current_ids):
                raise ValueError("Task day order may contain only Tasks scheduled for that day.")
            submitted = iter(task_ids)
            submitted_ids = set(task_ids)
            merged = tuple(
                next(submitted) if task_id in submitted_ids else task_id
                for task_id in current_ids
            )
            uow.tasks.replace_day_order(day, merged)


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
            if current.lifecycle_status is TaskLifecycle.COMPLETED:
                ordered = order_tasks_for_day(
                    tuple(
                        item
                        for item in uow.tasks.list(schedule_date=day)
                        if item.task.lifecycle_status is not TaskLifecycle.CANCELLED
                    ),
                    uow.tasks.day_positions(day),
                )
                updated = uow.tasks.change_lifecycle(task_id, TaskLifecycle.PLANNED, "Reopened from Dashboard")
                next_order = tuple(item.task.id for item in ordered)
                uow.tasks.replace_day_order(day, next_order)
                return updated
            return _complete_task_in_uow(
                uow,
                task_id,
                selected_day=day,
                reason="Completed from Dashboard",
            )


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
                return _complete_task_in_uow(
                    uow,
                    task_id,
                    reason="Moved on Kanban",
                )
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
    update_details: UpdateTaskDetails
    delete_task: DeleteTask
    change_lifecycle: ChangeTaskLifecycle
    complete_task: CompleteTask
    reorder_for_day: ReorderTasksForDay
    toggle_completion_for_day: ToggleTaskCompletionForDay
    move_to_board_column: MoveTaskToBoardColumn
    open_blocker: OpenBlocker
    resolve_blocker: ResolveBlocker
    list_tasks: ListTasksQuery
    get_editor: GetTaskEditorQuery
