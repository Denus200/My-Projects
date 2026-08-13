from __future__ import annotations

from types import TracebackType

from .connection import ConnectionFactory
from .repositories import (
    SqliteBlockerRepository,
    SqliteCycleRepository,
    SqliteDashboardRepository,
    SqliteProjectRepository,
    SqliteSettingsRepository,
    SqliteTaskRepository,
)


class SqliteUnitOfWork:
    def __init__(self, factory: ConnectionFactory, *, read_only: bool = False):
        self.factory = factory
        self.read_only = read_only
        self._connection_context = None
        self.connection = None

    def __enter__(self) -> "SqliteUnitOfWork":
        self._connection_context = self.factory.open(read_only=self.read_only)
        self.connection = self._connection_context.__enter__()
        if not self.read_only:
            self.connection.execute("BEGIN IMMEDIATE")
        self.projects = SqliteProjectRepository(self.connection)
        self.tasks = SqliteTaskRepository(self.connection)
        self.blockers = SqliteBlockerRepository(self.connection)
        self.settings = SqliteSettingsRepository(self.connection)
        self.dashboard = SqliteDashboardRepository(self.connection)
        self.cycles = SqliteCycleRepository(self.connection, self.tasks)
        return self

    def __exit__(
        self,
        exception_type: type[BaseException] | None,
        exception: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        try:
            if not self.read_only:
                if exception_type is None:
                    self.connection.commit()
                else:
                    self.connection.rollback()
        finally:
            self._connection_context.__exit__(exception_type, exception, traceback)


class SqliteUnitOfWorkFactory:
    def __init__(self, connection_factory: ConnectionFactory):
        self.connection_factory = connection_factory

    def __call__(self, *, read_only: bool = False) -> SqliteUnitOfWork:
        return SqliteUnitOfWork(self.connection_factory, read_only=read_only)
