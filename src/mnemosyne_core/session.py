"""Scoped sessions with namespace-boundary enforcement.

A star opens a session against the namespaces it declares; a flush that writes a
row in any other namespace raises :class:`NamespaceBoundaryError` before SQL is
emitted (FR-3). This is the *first* guard -- PostgreSQL grants (Component C) are
the second, authoritative one. Sessions close deterministically (FR-5).
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import TYPE_CHECKING

from sqlalchemy import event
from sqlalchemy.orm import Session, sessionmaker

if TYPE_CHECKING:
    from collections.abc import Generator, Iterable

    from sqlalchemy.engine import Engine


class NamespaceBoundaryError(RuntimeError):
    """Raised when a write targets a namespace the session did not declare."""


@contextmanager
def scoped_session(
    engine: Engine,
    namespaces: Iterable[str],
) -> Generator[Session, None, None]:
    """Yield a :class:`~sqlalchemy.orm.Session` scoped to *namespaces*.

    Commits on clean exit, rolls back on error, and always closes. A write to a
    table whose schema is outside *namespaces* raises
    :class:`NamespaceBoundaryError` at flush time.
    """
    declared = frozenset(namespaces)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    session = factory()

    def _guard(sess: Session, _ctx: object, _instances: object) -> None:
        changed = list(sess.new) + list(sess.dirty) + list(sess.deleted)
        for obj in changed:
            schema = obj.__table__.schema
            if schema is not None and schema not in declared:
                raise NamespaceBoundaryError(
                    f"write to namespace {schema!r} outside the declared set "
                    f"{sorted(declared)}"
                )

    event.listen(session, "before_flush", _guard)

    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
