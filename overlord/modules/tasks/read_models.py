from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from overlord.modules.blockers.domain import Blocker
from overlord.modules.tasks.domain import Task


@dataclass(frozen=True, slots=True)
class StatusHistoryEntry:
    from_status: str | None
    to_status: str
    reason: str | None
    changed_at: datetime


@dataclass(frozen=True, slots=True)
class TaskEditorData:
    task: Task
    blockers: tuple[Blocker, ...]
    status_history: tuple[StatusHistoryEntry, ...]
    connected_cycle_ids: tuple[int, ...] = ()
