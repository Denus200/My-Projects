from __future__ import annotations

from typing import Protocol

from overlord.modules.blockers.domain import Blocker, BlockerType


class BlockerRepositoryPort(Protocol):
    def open_blocker(self, task_id: int, blocker_type: BlockerType, description: str) -> Blocker: ...
    def resolve_blocker(self, blocker_id: int, resolution: str) -> Blocker: ...
    def list_blockers(self, task_id: int, open_only: bool = False) -> list[Blocker]: ...
