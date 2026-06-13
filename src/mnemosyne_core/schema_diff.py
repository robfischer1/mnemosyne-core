"""Schema-diff -- the FR-1 acceptance check: declared models vs the live PG store.

Compares the declared :data:`mnemosyne_core.base.metadata` against a live
PostgreSQL schema (via reflection over ``DATABASE_URL``) and reports drift per
namespace: missing/extra tables, missing/extra columns, and type/nullability
mismatches. Exit code is non-zero on any drift, so CI fails the build when the
contract and the store disagree.

Run::

    DATABASE_URL=postgresql://... uv run python -m mnemosyne_core.schema_diff

The canonical type vocabulary lets the two sides be compared apples-to-apples:
SQLAlchemy types are compiled to their PostgreSQL DDL and normalized to the same
tokens that ``information_schema`` reports.
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from sqlalchemy import create_engine, text
from sqlalchemy.dialects import postgresql

from mnemosyne_core.config import Config
from mnemosyne_core.schema import load_schema

if TYPE_CHECKING:
    from collections.abc import Mapping

    from sqlalchemy.engine import Engine
    from sqlalchemy.types import TypeEngine

    from mnemosyne_core.schema import Schema

_PG = postgresql.dialect()  # type: ignore[no-untyped-call]

# (schema, table, column) -> (canonical type, nullable)
ColumnKey = tuple[str, str, str]
ColumnShape = tuple[str, bool]
Shape = dict[ColumnKey, ColumnShape]


def canon_from_pg_ddl(ddl: str) -> str:
    """Normalize a compiled PostgreSQL type DDL to a canonical token."""
    up = ddl.upper()
    if "[]" in up:
        if "BIGINT" in up:
            return "bigint[]"
        if "INTEGER" in up:
            return "integer[]"
        return up.lower()
    if "TSVECTOR" in up:  # must precede VECTOR (substring)
        return "tsvector"
    if "VECTOR" in up:
        return "vector"
    if "TIMESTAMP" in up:
        return "timestamptz"
    if up == "FLOAT" or "DOUBLE" in up:
        return "double precision"
    if "REAL" in up:
        return "real"
    for token in ("BIGINT", "SMALLINT", "INTEGER", "BOOLEAN", "NUMERIC"):
        if token in up:
            return token.lower()
    if "JSONB" in up or "JSON" in up:
        return "jsonb"
    if "UUID" in up:
        return "uuid"
    if "CHAR" in up or "TEXT" in up:
        return "text"
    return up.lower()


def canon_from_info_schema(data_type: str, udt_name: str) -> str:
    """Normalize an information_schema (data_type, udt_name) to a canonical token."""
    if data_type == "ARRAY":
        return {"_int8": "bigint[]", "_int4": "integer[]"}.get(
            udt_name, udt_name.lstrip("_") + "[]"
        )
    if data_type == "USER-DEFINED":
        return udt_name
    return {
        "timestamp with time zone": "timestamptz",
        "character varying": "text",
        "character": "text",
        "json": "jsonb",
    }.get(data_type, data_type)


def declared_shape(schema: Schema) -> Shape:
    """Return the shape declared by the spec, keyed by (schema, table, column)."""
    shape: Shape = {}
    for table in schema.metadata.tables.values():
        schema_name = table.schema or "public"
        for col in table.columns:
            col_type: TypeEngine[object] = col.type
            shape[(schema_name, table.name, col.name)] = (
                canon_from_pg_ddl(col_type.compile(dialect=_PG)),
                bool(col.nullable),
            )
    return shape


def live_shape(engine: Engine, namespaces: frozenset[str]) -> Shape:
    """Return the live shape from information_schema, keyed (schema, table, column)."""
    shape: Shape = {}
    sql = text(
        "SELECT table_schema, table_name, column_name, data_type, udt_name, "
        "is_nullable FROM information_schema.columns "
        "WHERE table_schema = ANY(:schemas)"
    )
    with engine.connect() as conn:
        rows = conn.execute(sql, {"schemas": list(namespaces)}).all()
    for schema, table, column, data_type, udt_name, is_nullable in rows:
        shape[(schema, table, column)] = (
            canon_from_info_schema(data_type, udt_name),
            is_nullable == "YES",
        )
    return shape


@dataclass
class Drift:
    """A single point of disagreement between models and the live store."""

    kind: str  # missing_table | extra_table | missing_column | extra_column
    #            | type_mismatch | nullable_mismatch
    key: str
    detail: str = ""


@dataclass
class DiffResult:
    """The full set of drifts, grouped for reporting."""

    drifts: list[Drift] = field(default_factory=list)

    @property
    def clean(self) -> bool:
        """Return True when there is zero drift."""
        return not self.drifts


def diff(declared: Shape, live: Shape) -> DiffResult:
    """Compare declared vs live shapes and return all drifts."""
    result = DiffResult()
    declared_tables = {(s, t) for (s, t, _c) in declared}
    live_tables = {(s, t) for (s, t, _c) in live}
    for s, t in sorted(declared_tables - live_tables):
        result.drifts.append(Drift("missing_table", f"{s}.{t}", "declared, not in store"))
    for s, t in sorted(live_tables - declared_tables):
        result.drifts.append(Drift("extra_table", f"{s}.{t}", "in store, not declared"))

    shared_tables = declared_tables & live_tables
    for key, (dtype, dnull) in sorted(declared.items()):
        s, t, c = key
        if (s, t) not in shared_tables:
            continue
        if key not in live:
            result.drifts.append(
                Drift("missing_column", f"{s}.{t}.{c}", "declared, not in store")
            )
            continue
        ltype, lnull = live[key]
        if dtype != ltype:
            result.drifts.append(
                Drift("type_mismatch", f"{s}.{t}.{c}", f"declared {dtype!r} vs live {ltype!r}")
            )
        if dnull != lnull:
            result.drifts.append(
                Drift(
                    "nullable_mismatch",
                    f"{s}.{t}.{c}",
                    f"declared nullable={dnull} vs live nullable={lnull}",
                )
            )
    for key in sorted(live):
        s, t, c = key
        if (s, t) in shared_tables and key not in declared:
            result.drifts.append(
                Drift("extra_column", f"{s}.{t}.{c}", "in store, not declared")
            )
    return result


def format_report(result: DiffResult) -> str:
    """Render a human-readable drift report."""
    if result.clean:
        return "schema-diff: ZERO DRIFT -- the spec matches the live store."
    by_kind: dict[str, list[Drift]] = {}
    for d in result.drifts:
        by_kind.setdefault(d.kind, []).append(d)
    lines = [f"schema-diff: {len(result.drifts)} drift(s) found", ""]
    for kind in sorted(by_kind):
        items = by_kind[kind]
        lines.append(f"## {kind} ({len(items)})")
        lines.extend(f"  {d.key}: {d.detail}" for d in items)
        lines.append("")
    return "\n".join(lines)


def main(argv: Mapping[str, str] | None = None) -> int:
    """Connect via DATABASE_URL, diff, print the report, return an exit code."""
    env = os.environ if argv is None else argv
    url = env.get("DATABASE_URL")
    if not url:
        print("schema-diff: DATABASE_URL not set; nothing to compare.", file=sys.stderr)
        return 2
    if url.startswith("postgresql://") and "+psycopg" not in url:
        url = url.replace("postgresql://", "postgresql+psycopg://", 1)
    engine = create_engine(url)
    schema = load_schema(Config.from_env(env))
    result = diff(declared_shape(schema), live_shape(engine, schema.namespaces))
    print(format_report(result))
    return 0 if result.clean else 1


if __name__ == "__main__":
    raise SystemExit(main())
