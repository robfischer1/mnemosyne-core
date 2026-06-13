"""The schema spec -- the framework's contract, expressed as data not code.

A :class:`NamespaceSpec` describes one store namespace (a PostgreSQL schema) and
its tables; a table is a name plus an ordered tuple of :class:`ColumnSpec`. This
is what the public framework loads -- it never imports a hand-written model -- and
what the private schema TOML deserializes into. The optional table ``tier`` carries
the grant policy (e.g. ``"phi"``, ``"others_pii"``) so the grant DDL reads it here.
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pathlib import Path


@dataclass(frozen=True, slots=True)
class ColumnSpec:
    """One column: a name, a type token, and its nullability / key / default."""

    name: str
    type: str
    nullable: bool = True
    pk: bool = False
    default: str | None = None


@dataclass(frozen=True, slots=True)
class TableSpec:
    """One table: a name, its columns, and an optional grant ``tier``."""

    name: str
    columns: tuple[ColumnSpec, ...]
    tier: str | None = None


@dataclass(frozen=True, slots=True)
class NamespaceSpec:
    """One namespace (a PostgreSQL schema) and the tables it declares."""

    namespace: str
    tables: tuple[TableSpec, ...]


def _column_from_dict(data: dict[str, Any]) -> ColumnSpec:
    default = data.get("default")
    return ColumnSpec(
        name=str(data["name"]),
        type=str(data["type"]),
        nullable=bool(data.get("nullable", True)),
        pk=bool(data.get("pk", False)),
        default=None if default is None else str(default),
    )


def namespace_from_dict(data: dict[str, Any]) -> NamespaceSpec:
    """Parse a TOML-shaped mapping (one namespace) into a :class:`NamespaceSpec`."""
    tables: list[TableSpec] = []
    for raw in data.get("tables", []):
        tables.append(
            TableSpec(
                name=str(raw["name"]),
                columns=tuple(
                    _column_from_dict(c) for c in raw.get("columns", [])
                ),
                tier=None if raw.get("tier") is None else str(raw["tier"]),
            )
        )
    return NamespaceSpec(namespace=str(data["namespace"]), tables=tuple(tables))


def _column_to_dict(col: ColumnSpec) -> dict[str, object]:
    out: dict[str, object] = {"name": col.name, "type": col.type}
    if not col.nullable:
        out["nullable"] = False
    if col.pk:
        out["pk"] = True
    if col.default is not None:
        out["default"] = col.default
    return out


def namespace_to_dict(spec: NamespaceSpec) -> dict[str, object]:
    """Render a :class:`NamespaceSpec` to a TOML-shaped mapping (omitting defaults)."""
    tables: list[dict[str, object]] = []
    for table in spec.tables:
        entry: dict[str, object] = {"name": table.name}
        if table.tier is not None:
            entry["tier"] = table.tier
        entry["columns"] = [_column_to_dict(c) for c in table.columns]
        tables.append(entry)
    return {"namespace": spec.namespace, "tables": tables}


def load_specs(directory: Path) -> list[NamespaceSpec]:
    """Load every ``*.toml`` namespace spec from *directory* (sorted by name)."""
    specs: list[NamespaceSpec] = []
    for path in sorted(directory.glob("*.toml")):
        with path.open("rb") as handle:
            specs.append(namespace_from_dict(tomllib.load(handle)))
    return specs
