"""Portable column types -- one model definition, two backends.

Each type renders the native PostgreSQL type under the PG dialect and a
SQLite-compatible fallback under SQLite, so a single declarative model serves the
corpus (PG) and a standalone star (SQLite). The PostgreSQL rendering is
authoritative for schema-diff against the live store (FR-1); the SQLite fallback
is the graceful-degradation path (FR-12).

``UUIDType`` is SQLAlchemy's built-in :class:`~sqlalchemy.Uuid` (native ``uuid``
on PG, ``CHAR(32)`` on SQLite) re-exported for a single import site.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from pgvector.sqlalchemy import Vector as _PGVector
from sqlalchemy import JSON, Text, TypeDecorator, Uuid
from sqlalchemy.dialects.postgresql import ARRAY, TSVECTOR
from sqlalchemy.dialects.postgresql import JSONB as _PG_JSONB
from sqlalchemy.types import BigInteger, Integer

if TYPE_CHECKING:
    from sqlalchemy.engine.interfaces import Dialect
    from sqlalchemy.types import TypeEngine

UUIDType = Uuid

__all__ = ["JSONB", "BigIntArray", "IntArray", "TSVector", "UUIDType", "Vector"]


class Vector(TypeDecorator[Any]):
    """pgvector ``vector(dim)`` on PostgreSQL; a JSON list on SQLite."""

    impl = JSON
    cache_ok = True

    def __init__(self, dim: int) -> None:
        """Store the vector dimensionality."""
        super().__init__()
        self.dim = dim

    def load_dialect_impl(self, dialect: Dialect) -> TypeEngine[Any]:
        """Render pgvector on PostgreSQL, a JSON list on SQLite."""
        if dialect.name == "postgresql":
            return dialect.type_descriptor(_PGVector(self.dim))
        return dialect.type_descriptor(JSON())


class JSONB(TypeDecorator[Any]):
    """``jsonb`` on PostgreSQL; ``JSON`` on SQLite."""

    impl = JSON
    cache_ok = True

    def load_dialect_impl(self, dialect: Dialect) -> TypeEngine[Any]:
        """Render jsonb on PostgreSQL, JSON on SQLite."""
        if dialect.name == "postgresql":
            return dialect.type_descriptor(_PG_JSONB())
        return dialect.type_descriptor(JSON())


class BigIntArray(TypeDecorator[Any]):
    """``bigint[]`` on PostgreSQL; a JSON array on SQLite."""

    impl = JSON
    cache_ok = True

    def load_dialect_impl(self, dialect: Dialect) -> TypeEngine[Any]:
        """Render bigint[] on PostgreSQL, a JSON array on SQLite."""
        if dialect.name == "postgresql":
            return dialect.type_descriptor(ARRAY(BigInteger()))
        return dialect.type_descriptor(JSON())


class IntArray(TypeDecorator[Any]):
    """``integer[]`` on PostgreSQL; a JSON array on SQLite."""

    impl = JSON
    cache_ok = True

    def load_dialect_impl(self, dialect: Dialect) -> TypeEngine[Any]:
        """Render integer[] on PostgreSQL, a JSON array on SQLite."""
        if dialect.name == "postgresql":
            return dialect.type_descriptor(ARRAY(Integer()))
        return dialect.type_descriptor(JSON())


class TSVector(TypeDecorator[Any]):
    """``tsvector`` on PostgreSQL; ``TEXT`` on SQLite (degraded, non-indexed)."""

    impl = Text
    cache_ok = True

    def load_dialect_impl(self, dialect: Dialect) -> TypeEngine[Any]:
        """Render tsvector on PostgreSQL, TEXT on SQLite."""
        if dialect.name == "postgresql":
            return dialect.type_descriptor(TSVECTOR())
        return dialect.type_descriptor(Text())
