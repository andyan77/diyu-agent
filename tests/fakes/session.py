"""Fake SQLAlchemy async session and session factory for testing.

Replaces AsyncMock/MagicMock-based session mocks with real Python classes.
Designed to support all PG adapter test patterns:
- session.add() (sync) / commit() / flush() / close() (async)
- session.execute() -> FakeResult with scalar_one / scalar_one_or_none / rowcount
- session.scalars() -> FakeScalarsResult with all()
- async context manager protocol (__aenter__ / __aexit__)
- session_factory() callable returning session

Usage:
    session = FakeAsyncSession()
    session.set_scalars_result([row1, row2])
    factory = FakeSessionFactory(session)
    store = PgSomeStore(session_factory=factory)
"""

from __future__ import annotations

from typing import Any

_UNSET = object()


class FakeResult:
    """Fake result from session.execute().

    Supports .scalar_one(), .scalar_one_or_none(), .fetchall(), and .rowcount.
    """

    def __init__(
        self,
        *,
        scalar_value: Any = None,
        scalar_one_or_none_value: Any = _UNSET,
        rowcount: int = 0,
        fetchall_rows: list[Any] | None = None,
    ) -> None:
        self._scalar_value = scalar_value
        self._scalar_one_or_none_value = scalar_one_or_none_value
        self.rowcount = rowcount
        self._fetchall_rows = fetchall_rows or []

    def scalar_one(self) -> Any:
        return self._scalar_value

    def scalar_one_or_none(self) -> Any:
        if self._scalar_one_or_none_value is _UNSET:
            return None
        return self._scalar_one_or_none_value

    def fetchall(self) -> list[Any]:
        return list(self._fetchall_rows)


class FakeScalarsResult:
    """Fake result from session.scalars().

    Supports .all() returning a list of rows.
    """

    def __init__(self, rows: list[Any] | None = None) -> None:
        self._rows = rows or []

    def all(self) -> list[Any]:
        return list(self._rows)


class FakeAsyncSession:
    """Fake AsyncSession for testing PG adapter code without mocks.

    Records add/commit/flush/close/execute calls and returns
    configurable results. Supports async context manager protocol.
    """

    def __init__(self) -> None:
        self.added: list[Any] = []
        self.committed: bool = False
        self.commit_count: int = 0
        self.flushed: bool = False
        self.flush_count: int = 0
        self.closed: bool = False
        self.close_count: int = 0
        self.execute_calls: list[Any] = []

        self._execute_result: FakeResult | None = None
        self._execute_results_queue: list[FakeResult] = []
        self._scalars_result: FakeScalarsResult | None = None

    # -- Configuration methods (call before exercising SUT) --

    def set_execute_result(
        self,
        *,
        scalar_value: Any = None,
        scalar_one_or_none_value: Any = _UNSET,
        rowcount: int = 0,
        fetchall_rows: list[Any] | None = None,
    ) -> None:
        """Configure what session.execute() returns."""
        self._execute_result = FakeResult(
            scalar_value=scalar_value,
            scalar_one_or_none_value=scalar_one_or_none_value,
            rowcount=rowcount,
            fetchall_rows=fetchall_rows,
        )

    def set_execute_results(self, results: list[FakeResult]) -> None:
        """Configure multiple sequential execute() results (for hybrid_search etc)."""
        self._execute_results_queue = list(results)

    def set_scalars_result(self, rows: list[Any]) -> None:
        """Configure what session.scalars() returns."""
        self._scalars_result = FakeScalarsResult(rows)

    # -- SQLAlchemy AsyncSession interface --

    def add(self, obj: Any) -> None:
        self.added.append(obj)

    async def commit(self) -> None:
        self.committed = True
        self.commit_count += 1

    async def flush(self) -> None:
        self.flushed = True
        self.flush_count += 1

    async def close(self) -> None:
        self.closed = True
        self.close_count += 1

    async def execute(self, statement: Any, params: Any = None) -> FakeResult:
        self.execute_calls.append((statement, params))
        if self._execute_results_queue:
            return self._execute_results_queue.pop(0)
        return self._execute_result or FakeResult()

    async def scalars(self, statement: Any) -> FakeScalarsResult:
        return self._scalars_result or FakeScalarsResult()

    # -- Async context manager protocol --

    async def __aenter__(self) -> FakeAsyncSession:
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        pass


class FakeSessionFactory:
    """Fake async_sessionmaker that returns a preconfigured FakeAsyncSession.

    Supports single session (repeated calls return same session) or
    a sequence of sessions (for multi-call tests like write-then-read).

    Usage:
        session = FakeAsyncSession()
        factory = FakeSessionFactory(session)
        store = PgSomeStore(session_factory=factory)

        # Multi-session sequence:
        factory = FakeSessionFactory.sequence([write_session, read_session])
    """

    def __init__(self, session: FakeAsyncSession) -> None:
        self._session = session
        self._sequence: list[FakeAsyncSession] = []

    @classmethod
    def sequence(cls, sessions: list[FakeAsyncSession]) -> FakeSessionFactory:
        """Create a factory that returns different sessions on successive calls."""
        factory = cls(sessions[0])
        factory._sequence = list(sessions)
        return factory

    def __call__(self) -> FakeAsyncSession:
        if self._sequence:
            return self._sequence.pop(0)
        return self._session


class FakeOrmRow:
    """Generic fake ORM row that holds arbitrary attributes.

    Usage:
        row = FakeOrmRow(id=uuid4(), content="hello", confidence=0.9)
        assert row.id == ...
        assert row.content == "hello"
    """

    def __init__(self, **kwargs: Any) -> None:
        for k, v in kwargs.items():
            setattr(self, k, v)

    def __getitem__(self, index: int) -> Any:
        """Support tuple-style indexing (for pgvector raw SQL result rows)."""
        return list(self.__dict__.values())[index]
