from __future__ import annotations

import calendar
from datetime import date, datetime, timedelta

from overlord.app.read_models import TaskListItem
from overlord.modules.tasks.domain import TaskBoardColumn, board_column, is_scheduled_for_day
from overlord.ui.components.task_ordering import moved_task_ids


def week_start(day: date, first_day: int) -> date:
    return day - timedelta(days=(day.weekday() - first_day) % 7)


def month_shift(day: date, offset: int) -> date:
    month_index = day.year * 12 + day.month - 1 + offset
    return date(month_index // 12, month_index % 12 + 1, 1)


def month_weeks(day: date, first_day: int) -> tuple[tuple[date, ...], ...]:
    first = day.replace(day=1)
    last = day.replace(day=calendar.monthrange(day.year, day.month)[1])
    grid_start = week_start(first, first_day)
    grid_end = week_start(last, first_day) + timedelta(days=6)
    days = tuple(
        grid_start + timedelta(days=offset)
        for offset in range((grid_end - grid_start).days + 1)
    )
    return tuple(tuple(days[index : index + 7]) for index in range(0, len(days), 7))


def parse_calendar_anchor(value: str | None, today: date) -> date:
    if not value:
        return today
    try:
        return date.fromisoformat(value)
    except ValueError:
        return today


def normalized_view_mode(value: str) -> str:
    return value if value in {"kanban", "week", "month"} else "kanban"


def task_query_filters(search: str, project: str) -> dict[str, object]:
    filters: dict[str, object] = {"search": search}
    if project == "none":
        filters["without_project"] = True
    elif project != "all":
        filters["project_id"] = int(project)
    return filters


def group_board_items(
    items: tuple[TaskListItem, ...],
    reference: datetime,
) -> dict[TaskBoardColumn, tuple[TaskListItem, ...]]:
    grouped: dict[TaskBoardColumn, list[TaskListItem]] = {
        column: [] for column in TaskBoardColumn
    }
    for item in items:
        grouped[board_column(item.task, reference)].append(item)
    return {column: tuple(column_items) for column, column_items in grouped.items()}


def normalized_column_order(order: list[str]) -> list[str]:
    valid = [column.value for column in TaskBoardColumn]
    normalized = [value for value in order if value in valid]
    normalized.extend(value for value in valid if value not in normalized)
    return normalized


def reordered_columns(order: list[str], source: str, target: str) -> list[str]:
    if source not in order or target not in order or source == target:
        return list(order)
    reordered = list(order)
    reordered.remove(source)
    reordered.insert(reordered.index(target), source)
    return reordered


def reconcile_card_order(
    order: list[int],
    items: tuple[TaskListItem, ...],
    *,
    initial_order: tuple[int, ...] = (),
) -> tuple[list[int], tuple[TaskListItem, ...]]:
    reconciled = list(order or initial_order)
    present = {item.task.id for item in items}
    reconciled = [task_id for task_id in reconciled if task_id in present]
    reconciled.extend(item.task.id for item in items if item.task.id not in reconciled)
    by_id = {item.task.id: item for item in items}
    return reconciled, tuple(by_id[task_id] for task_id in reconciled)


def moved_card_orders(
    card_orders: dict[str, list[int]],
    task_id: int,
    target: str,
    before_task_id: int | None,
) -> dict[str, list[int]]:
    moved = {column: list(order) for column, order in card_orders.items()}
    for order in moved.values():
        if task_id in order:
            order.remove(task_id)
    target_order = moved.setdefault(target, [])
    target_order[:] = moved_task_ids(tuple((*target_order, task_id)), task_id, before_task_id)
    return moved


def merged_today_order(scheduled_ids: tuple[int, ...], desired_ids: list[int]) -> tuple[int, ...]:
    scheduled = set(scheduled_ids)
    desired = [task_id for task_id in desired_ids if task_id in scheduled]
    desired_set = set(desired)
    desired_iter = iter(desired)
    return tuple(
        next(desired_iter) if task_id in desired_set else task_id
        for task_id in scheduled_ids
    )


def scheduled_items_for_day(
    items: tuple[TaskListItem, ...],
    selected_day: date,
) -> tuple[TaskListItem, ...]:
    return tuple(item for item in items if is_scheduled_for_day(item.task, selected_day))
