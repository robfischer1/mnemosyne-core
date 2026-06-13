"""The backend engine factory -- PostgreSQL (the corpus) or SQLite (standalone).

:func:`make_engine` selects the backend from :class:`~mnemosyne_core.config.Config`
and is bound to the loaded schema's *namespaces* and *search_path* (they come from
the spec, not a hard-coded list). A ``DATABASE_URL`` yields a pooled,
pgvector-aware PostgreSQL engine that issues ``SET ROLE`` under the configured
least-privilege role (the Component B/C hook); absent, it yields a SQLite engine
over the baked file with the standard pragma set, a best-effort sqlite-vec load,
and a ``schema_translate_map`` so ``schema=``-bound tables resolve on a schemaless
backend.

Low-level: stars use :mod:`mnemosyne_core.repository`, not a raw engine.
"""

from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING, Any

from sqlalchemy import create_engine, event

if TYPE_CHECKING:
    from collections.abc import Iterable, Sequence

    from sqlalchemy.engine import Engine

    from mnemosyne_core.config import Config

logger = logging.getLogger(__name__)

# The standard SQLite pragma set (mirrors the legacy phdb dialect).
_SQLITE_PRAGMAS: tuple[tuple[str, str], ...] = (
    ("journal_mode", "WAL"),
    ("synchronous", "NORMAL"),
    ("temp_store", "MEMORY"),
    ("busy_timeout", "30000"),
    ("foreign_keys", "ON"),
)

# A PostgreSQL role name we are willing to interpolate into ``SET ROLE`` (which
# cannot be parameterized). Operator-configured, but validated fail-closed.
_ROLE_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def make_engine(
    config: Config,
    namespaces: Iterable[str],
    search_path: Sequence[str] | None = None,
) -> Engine:
    """Build the engine for the active backend over *namespaces*.

    *search_path* defaults to the namespaces followed by ``public``.
    """
    names = tuple(namespaces)
    path = tuple(search_path) if search_path is not None else (*names, "public")
    if config.is_postgres:
        return _make_postgres_engine(config, path)
    return _make_sqlite_engine(config, names)


def _make_postgres_engine(config: Config, search_path: Sequence[str]) -> Engine:
    url = config.database_url
    if url is None:  # pragma: no cover - guarded by caller
        raise ValueError("postgres engine requires a DATABASE_URL")
    if url.startswith("postgresql://") and "+psycopg" not in url:
        url = url.replace("postgresql://", "postgresql+psycopg://", 1)

    role = config.db_role
    if role is not None and not _ROLE_RE.match(role):
        raise ValueError(f"invalid MNEMOSYNE_DB_ROLE {role!r}")

    engine = create_engine(
        url,
        pool_size=5,
        max_overflow=5,
        pool_pre_ping=True,
        connect_args={"options": f"-c search_path={','.join(search_path)}"},
    )

    def _on_connect(dbapi_conn: Any, _record: Any) -> None:
        try:
            from pgvector.psycopg import register_vector

            register_vector(dbapi_conn)
        except Exception:  # noqa: BLE001 - pgvector is best-effort per connection
            logger.debug("pgvector register_vector failed", exc_info=True)
        if role is not None:
            with dbapi_conn.cursor() as cur:
                cur.execute(f'SET ROLE "{role}"')

    event.listen(engine, "connect", _on_connect)
    return engine


def _make_sqlite_engine(config: Config, namespaces: Iterable[str]) -> Engine:
    engine = create_engine(f"sqlite+pysqlite:///{config.sqlite_path}")

    def _on_connect(dbapi_conn: Any, _record: Any) -> None:
        cur = dbapi_conn.cursor()
        for name, value in _SQLITE_PRAGMAS:
            cur.execute(f"PRAGMA {name} = {value}")
        cur.close()
        try:
            dbapi_conn.enable_load_extension(True)
            import sqlite_vec

            sqlite_vec.load(dbapi_conn)
            dbapi_conn.enable_load_extension(False)
        except Exception:  # noqa: BLE001 - sqlite-vec is an optional capability
            logger.debug("sqlite-vec load failed", exc_info=True)

    event.listen(engine, "connect", _on_connect)

    # SQLite has no schemas: translate every namespace to the single file so
    # ``schema=``-bound tables resolve. Duplicate table names across namespaces
    # require a declared-subset star (see A4.3).
    return engine.execution_options(
        schema_translate_map=dict.fromkeys(namespaces, None)
    )
