from enum import Enum


class TaskStatus(Enum):
    PLANNED = "planned"
    DONE = "done"
    PARTIAL = "partial"
    SKIPPED = "skipped"
    BLOCKED = "blocked"
    MOVED = "moved"


def is_valid_task_status(status: str) -> bool:
    return status in {item.value for item in TaskStatus}


def task_status_values() -> list[str]:
    return [item.value for item in TaskStatus]
