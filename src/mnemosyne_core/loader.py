"""Build a SQLAlchemy :class:`MetaData` from a schema spec -- the framework core.

The public framework imports no models: :func:`build_metadata` takes loaded
:class:`~mnemosyne_core.spec.NamespaceSpec`s and constructs imperative
:class:`~sqlalchemy.Table`s on a shared metadata, mapping each spec type token to a
portable column type from :mod:`mnemosyne_core.types`. Engine, session, and
repository bind to the result.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    REAL,
    BigInteger,
    Boolean,
    Column,
    Date,
    DateTime,
    Double,
    Integer,
    LargeBinary,
    MetaData,
    Numeric,
    SmallInteger,
    Table,
    Text,
    Time,
    text,
)

from mnemosyne_core.base import NAMING_CONVENTION
from mnemosyne_core.types import (
    JSONB,
    BigIntArray,
    IntArray,
    TSVector,
    UUIDType,
    Vector,
)

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable

    from sqlalchemy.types import TypeEngine

    from mnemosyne_core.spec import ColumnSpec, NamespaceSpec

_VECTOR_PREFIX = "vector("

_TYPES: dict[str, Callable[[], TypeEngine[Any]]] = {
    "bigint": BigInteger,
    "integer": Integer,
    "smallint": SmallInteger,
    "boolean": Boolean,
    "numeric": Numeric,
    "double precision": Double,
    "real": REAL,
    "text": Text,
    "bytea": LargeBinary,
    "uuid": UUIDType,
    "jsonb": JSONB,
    "tsvector": TSVector,
    "bigint[]": BigIntArray,
    "integer[]": IntArray,
    "date": Date,
    "time": Time,
    "timestamptz": lambda: DateTime(timezone=True),
}


def resolve_type(token: str) -> TypeEngine[Any]:
    """Map a spec type token to a portable SQLAlchemy type."""
    if token.startswith(_VECTOR_PREFIX):
        return Vector(int(token[len(_VECTOR_PREFIX) : -1]))
    factory = _TYPES.get(token)
    if factory is None:
        raise ValueError(f"unknown column type {token!r}")
    return factory()


def _column(spec: ColumnSpec) -> Column[Any]:
    return Column(
        spec.name,
        resolve_type(spec.type),
        primary_key=spec.pk,
        nullable=spec.nullable,
        server_default=text(spec.default) if spec.default is not None else None,
    )


def build_metadata(
    specs: Iterable[NamespaceSpec], metadata: MetaData | None = None
) -> MetaData:
    """Construct a :class:`MetaData` of imperative tables from *specs*."""
    md = (
        metadata
        if metadata is not None
        else MetaData(naming_convention=NAMING_CONVENTION)
    )
    for ns in specs:
        for table in ns.tables:
            Table(
                table.name,
                md,
                *[_column(c) for c in table.columns],
                schema=ns.namespace,
            )
    return md
