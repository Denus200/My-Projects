from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, timedelta

from overlord.app.read_models import TaskListItem
from overlord.app.services import ApplicationServices
from overlord.modules.projects.domain import Project
from overlord.modules.tasks.domain import TaskBoardColumn, board_column
from overlord.ui.components.task_workspace_model import (
    expanded_board_column_order,
    merged_today_order,
    month_shift,
    moved_card_orders,
    normalized_column_order,
    normalized_kanban_column_order,
    normalized_view_mode,
    parse_calendar_anchor,
    reconcile_card_order,
    reordered_columns,
    task_query_filters,
)
from overlord.ui.components.task_ordering import TaskOrderController
from overlord.ui.state import TaskFilterState, TaskWorkspaceState


@dataclass(frozen=True, slots=True)
class TaskOperationResult:
    error: Exception | None = None

    @property
    def succeeded(self) -> bool:
        return self.error is None


class TaskWorkspaceController:
    def __init__(
        self,
        services: ApplicationServices,
        state: TaskWorkspaceState,
        *,
        today: date | None = None,
    ) -> None:
        self.services = services
        self.state = state
        self._today = today
        self.anchor: date | None = None
        self.ordering = TaskOrderController(services)

    @property
    def today(self) -> date:
        if self._today is None:
            self._today = date.today()
        return self._today

    def initialize_view(self) -> None:
        self.state.view_mode = normalized_view_mode(self.state.view_mode)
        if self.state.expanded_date_navigation != self.state.view_mode:
            self.state.expanded_date_navigation = None
        self.anchor = parse_calendar_anchor(self.state.calendar_anchor, self.today)

    @property
    def filters(self) -> TaskFilterState:
        if self.state.filters is None:
            self.state.filters = TaskFilterState()
        return self.state.filters

    def list_projects(self) -> tuple[Project, ...]:
        return self.services.projects.list_projects.execute()

    def first_day_of_week(self) -> int:
        settings = self.services.settings.get_settings.execute()
        return 0 if settings.first_day_of_week == "monday" else 6

    def filtered_items(self, search: str, project: str) -> tuple[TaskListItem, ...]:
        self.filters.search = search
        self.filters.project = project
        return self.services.tasks.list_tasks.execute(**task_query_filters(search, project))

    def all_items(self) -> tuple[TaskListItem, ...]:
        return self.services.tasks.list_tasks.execute()

    def task_committed(
        self,
        close: Callable[[], None],
        render: Callable[[], None],
        notify: Callable[[], None],
    ) -> None:
        close()
        render()
        notify()

    def task_changed(
        self,
        close: Callable[[], None],
        render: Callable[[], None],
        reopen: Callable[[], None],
    ) -> None:
        close()
        render()
        reopen()

    def ordered_items(
        self,
        column: TaskBoardColumn,
        items: tuple[TaskListItem, ...],
    ) -> tuple[TaskListItem, ...]:
        order = self.state.card_order.setdefault(column.value, [])
        initial_order: tuple[int, ...] = ()
        if column is TaskBoardColumn.IN_PROGRESS and not order:
            initial_order = tuple(
                item.task.id
                for item in self.services.dashboard.execute(self.today).today_tasks
                if board_column(item.task) is TaskBoardColumn.IN_PROGRESS
            )
        reconciled, ordered = reconcile_card_order(
            order,
            items,
            initial_order=initial_order,
        )
        order[:] = reconciled
        return ordered

    def normalize_column_order(self) -> None:
        self.state.column_order[:] = normalized_column_order(self.state.column_order)

    def initialize_card_orders(
        self,
        grouped: dict[TaskBoardColumn, tuple[TaskListItem, ...]],
    ) -> None:
        """Reconcile against all Tasks before filters project visible subsets."""
        for column in TaskBoardColumn:
            self.ordered_items(column, grouped[column])

    def projected_items(
        self,
        items: tuple[TaskListItem, ...],
    ) -> tuple[TaskListItem, ...]:
        input_position = {item.task.id: position for position, item in enumerate(items)}
        column_position = {
            value: position for position, value in enumerate(self.state.column_order)
        }

        def ordering_key(item: TaskListItem) -> tuple[int, int, int]:
            source = board_column(item.task)
            ordered_ids = self.state.card_order.get(source.value, [])
            try:
                card_position = ordered_ids.index(item.task.id)
            except ValueError:
                card_position = len(ordered_ids) + input_position[item.task.id]
            return (
                column_position.get(source.value, len(column_position)),
                card_position,
                input_position[item.task.id],
            )

        return tuple(sorted(items, key=ordering_key))

    def reorder_kanban_column(self, source: str, target: str) -> bool:
        current = normalized_kanban_column_order(self.state.column_order)
        reordered = reordered_columns(current, source, target)
        if reordered == current:
            return False
        self.state.column_order[:] = expanded_board_column_order(reordered)
        return True

    def reorder_column(self, source: TaskBoardColumn, target: TaskBoardColumn) -> bool:
        reordered = reordered_columns(self.state.column_order, source.value, target.value)
        if reordered == self.state.column_order:
            return False
        self.state.column_order[:] = reordered
        return True

    def complete(self, task_id: int) -> TaskOperationResult:
        try:
            self.services.tasks.complete_task.execute(task_id)
            return TaskOperationResult()
        except Exception as error:
            return TaskOperationResult(error)

    def move_card(
        self,
        task_id: int,
        target: TaskBoardColumn,
        before_task_id: int | None = None,
    ) -> TaskOperationResult:
        try:
            current = self.services.tasks.get_editor.execute(task_id).task
            source = board_column(current)
            if source is not target:
                self.services.tasks.move_to_board_column.execute(task_id, target)
            moved = moved_card_orders(
                self.state.card_order,
                task_id,
                target.value,
                before_task_id,
            )
            for column, order in moved.items():
                current_order = self.state.card_order.get(column)
                if current_order is None:
                    self.state.card_order[column] = order
                else:
                    current_order[:] = order
            if source is TaskBoardColumn.IN_PROGRESS or target is TaskBoardColumn.IN_PROGRESS:
                self.persist_today_suborder()
            return TaskOperationResult()
        except Exception as error:
            return TaskOperationResult(error)

    def persist_today_suborder(self) -> None:
        scheduled = self.services.dashboard.execute(self.today).today_tasks
        ordered_ids = merged_today_order(
            tuple(item.task.id for item in scheduled),
            self.state.card_order.get(TaskBoardColumn.IN_PROGRESS.value, []),
        )
        if ordered_ids:
            self.ordering.persist_for_day(self.today, ordered_ids)

    def switch_mode(self, mode: str) -> None:
        normalized = normalized_view_mode(mode)
        if normalized != self.state.view_mode:
            self.state.expanded_date_navigation = None
        self.state.view_mode = normalized

    def toggle_date_navigation(self, mode: str) -> None:
        if mode not in {"week", "month"} or mode != self.state.view_mode:
            self.state.expanded_date_navigation = None
            return
        self.state.expanded_date_navigation = (
            None if self.state.expanded_date_navigation == mode else mode
        )

    def move_calendar(self, offset: int) -> None:
        assert self.anchor is not None
        if self.state.view_mode == "week":
            self.anchor += timedelta(days=offset * 7)
        else:
            self.anchor = month_shift(self.anchor, offset)
        self.state.calendar_anchor = self.anchor.isoformat()

    def go_today(self) -> None:
        self.anchor = self.today
        self.state.calendar_anchor = self.anchor.isoformat()
