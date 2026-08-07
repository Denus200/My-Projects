from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from overlord.domain.tasks import (
    Blocker,
    BlockerType,
    Task,
    TaskLifecycle,
    TodayGroup,
    require_definition_of_done,
    require_task_title,
    validate_estimate,
    validate_slot,
    week_start,
)

from .common import TaskEditorData, TaskListItem, UnitOfWorkFactory


@dataclass(frozen=True, slots=True)
class CreateTask:
    uow_factory: UnitOfWorkFactory

    def execute(
        self,
        project_id: int | None,
        title: str,
        *,
        description: str = "",
        planned_date: date | None = None,
        today_group: TodayGroup | None = None,
        position: int | None = None,
        definition_of_done: str | None = None,
        next_action: str | None = None,
        importance: bool | None = None,
        urgency: bool | None = None,
        estimate_minutes: int | None = None,
        milestone_id: int | None = None,
        blocker_type: BlockerType | None = None,
        blocker_description: str | None = None,
    ) -> Task:
        clean_title = require_task_title(title)
        validate_slot(today_group, position)
        estimate = validate_estimate(estimate_minutes)
        clean_blocker = (blocker_description or "").strip()
        if blocker_type is not None and not clean_blocker:
            raise ValueError("Blocker description is required.")
        if clean_blocker and blocker_type is None:
            blocker_type = BlockerType.OTHER
        if today_group is TodayGroup.PRIMARY:
            require_definition_of_done(definition_of_done, context="assigning a Primary slot")
        if milestone_id is not None:
            require_definition_of_done(definition_of_done, context="attaching to a Milestone")
        chosen_date = planned_date or (date.today() if today_group is not None else None)
        lifecycle = TaskLifecycle.PLANNED if chosen_date else TaskLifecycle.BACKLOG
        with self.uow_factory() as uow:
            if project_id is not None and not uow.projects.get(project_id):
                raise ValueError(f"Project {project_id} does not exist.")
            task = uow.tasks.create(
                project_id,
                clean_title,
                lifecycle,
                description=description.strip(),
                planned_date=chosen_date or date.today(),
                definition_of_done=(definition_of_done or "").strip() or None,
                next_action=(next_action or "").strip() or None,
                importance=importance,
                urgency=urgency,
                estimate_minutes=estimate,
                milestone_id=milestone_id,
            )
            if chosen_date is not None:
                first_day = 6 if uow.settings.get().first_day_of_week == "sunday" else 0
                uow.tasks.assign_plan(task.id, chosen_date, today_group, position, week_start(chosen_date, first_day))
            if blocker_type is not None:
                uow.tasks.open_blocker(task.id, blocker_type, clean_blocker)
            return uow.tasks.get(task.id)


@dataclass(frozen=True, slots=True)
class UpdateTask:
    uow_factory: UnitOfWorkFactory

    def execute(self, task_id: int, **changes: object) -> Task:
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
            return uow.tasks.update(task_id, **changes)


@dataclass(frozen=True, slots=True)
class ChangeTaskLifecycle:
    uow_factory: UnitOfWorkFactory

    def execute(self, task_id: int, lifecycle: TaskLifecycle, reason: str | None = None) -> Task:
        with self.uow_factory() as uow:
            return uow.tasks.change_lifecycle(task_id, lifecycle, reason)


@dataclass(frozen=True, slots=True)
class AssignTaskPlan:
    uow_factory: UnitOfWorkFactory

    def execute(
        self,
        task_id: int,
        planned_date: date,
        today_group: TodayGroup | None = None,
        position: int | None = None,
    ):
        validate_slot(today_group, position)
        with self.uow_factory() as uow:
            task = uow.tasks.get(task_id)
            if not task:
                raise ValueError(f"Task {task_id} does not exist.")
            if today_group is TodayGroup.PRIMARY:
                require_definition_of_done(task.definition_of_done, context="assigning a Primary slot")
            first_day = 6 if uow.settings.get().first_day_of_week == "sunday" else 0
            return uow.tasks.assign_plan(
                task_id, planned_date, today_group, position, week_start(planned_date, first_day)
            )


MoveTaskPlan = AssignTaskPlan


@dataclass(frozen=True, slots=True)
class CompleteTask:
    uow_factory: UnitOfWorkFactory

    def execute(self, task_id: int) -> Task:
        with self.uow_factory() as uow:
            return uow.tasks.change_lifecycle(task_id, TaskLifecycle.COMPLETED, "Completed")


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
            return uow.tasks.open_blocker(task_id, blocker_type, clean)


@dataclass(frozen=True, slots=True)
class ResolveBlocker:
    uow_factory: UnitOfWorkFactory

    def execute(self, blocker_id: int, resolution: str) -> Blocker:
        clean = resolution.strip()
        if not clean:
            raise ValueError("Blocker resolution is required.")
        with self.uow_factory() as uow:
            return uow.tasks.resolve_blocker(blocker_id, clean)


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
                tuple(uow.tasks.list_blockers(task_id)),
                tuple(uow.tasks.plan_history(task_id)),
                tuple(uow.tasks.status_history(task_id)),
            )


@dataclass(frozen=True, slots=True)
class TaskApplication:
    create_task: CreateTask
    update_task: UpdateTask
    change_lifecycle: ChangeTaskLifecycle
    assign_plan: AssignTaskPlan
    complete_task: CompleteTask
    open_blocker: OpenBlocker
    resolve_blocker: ResolveBlocker
    list_tasks: ListTasksQuery
    get_editor: GetTaskEditorQuery
