from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class BlockerType(StrEnum):
    DEPENDENCY = "dependency"
    DECISION = "decision"
    RESOURCE = "resource"
    CLARITY = "clarity"
    TECHNICAL = "technical"
    OTHER = "other"


@dataclass(frozen=True, slots=True)
class Blocker:
    id: int
    task_id: int
    type: BlockerType
    description: str
    created_at: datetime
    resolved_at: datetime | None = None
    resolution: str | None = None
