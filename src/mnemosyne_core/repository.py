"""The repository -- a namespace-scoped, name-based query surface over the schema.

A :class:`Repository` opens the env-selected backend, binds to the loaded schema,
and serves reads/writes by ``(namespace, table)`` through the metadata -- no model
classes. A write outside the declared namespaces raises
:class:`~mnemosyne_core.session.NamespaceBoundaryError`; PostgreSQL grants are the
second, authoritative lock.
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import TYPE_CHECKING, Any

from sqlalchemy import insert, select

from mnemosyne_core.config import Config
from mnemosyne_core.engine import make_engine
from mnemosyne_core.schema import load_schema
from mnemosyne_core.session import NamespaceBoundaryError, scoped_session

if TYPE_CHECKING:
    from collections.abc import Generator, Iterable, Mapping

    from sqlalchemy import Table
    from sqlalchemy.engine import Engine
    from sqlalchemy.orm import Session

    from mnemosyne_core.schema import Schema


class Repository:
    """A namespace-scoped, backend-agnostic, name-based query surface."""

    def __init__(
        self, engine: Engine, schema: Schema, namespaces: Iterable[str]
    ) -> None:
        """Bind *namespaces* (the write boundary) over *engine* and *schema*."""
        self._engine = engine
        self._schema = schema
        self._namespaces = frozenset(namespaces)

    @classmethod
    def open(
        cls, namespaces: Iterable[str], config: Config | None = None
    ) -> Repository:
        """Open on the env-selected backend with the schema loaded from spec."""
        cfg = config or Config.from_env()
        schema = load_schema(cfg)
        engine = make_engine(cfg, schema.namespaces, schema.search_path)
        return cls(engine, schema, namespaces)

    def table(self, namespace: str, table: str) -> Table:
        """Return the :class:`~sqlalchemy.Table` for ``namespace.table``."""
        return self._schema.metadata.tables[f"{namespace}.{table}"]

    @contextmanager
    def session(self) -> Generator[Session, None, None]:
        """Yield a session scoped to the declared namespaces (boundary-enforced)."""
        with scoped_session(self._engine, self._namespaces) as s:
            yield s

    def read(
        self, namespace: str, table: str, *, limit: int | None = None
    ) -> list[dict[str, Any]]:
        """Return rows of ``namespace.table`` as mappings (optionally capped)."""
        target = self.table(namespace, table)
        stmt = select(target)
        if limit is not None:
            stmt = stmt.limit(limit)
        with self.session() as session:
            return [dict(row._mapping) for row in session.execute(stmt)]

    def insert(
        self, namespace: str, table: str, values: Mapping[str, Any]
    ) -> None:
        """Insert *values* into ``namespace.table`` within the write boundary."""
        if namespace not in self._namespaces:
            raise NamespaceBoundaryError(
                f"write to namespace {namespace!r} outside the declared set "
                f"{sorted(self._namespaces)}"
            )
        target = self.table(namespace, table)
        with self.session() as session:
            session.execute(insert(target).values(**values))
