"""Unit tests for the schema-diff logic (T021) -- synthetic shapes, no live PG."""

from __future__ import annotations

from pathlib import Path

from mnemosyne_core.config import Config
from mnemosyne_core.schema import load_schema
from mnemosyne_core.schema_diff import (
    canon_from_info_schema,
    canon_from_pg_ddl,
    declared_shape,
    diff,
)

FIXTURE = Path(__file__).parent / "fixtures" / "schema"


def test_canon_vocabulary_agrees_across_sides():
    pairs = [
        ("BIGINT", ("bigint", "int8"), "bigint"),
        ("INTEGER", ("integer", "int4"), "integer"),
        ("SMALLINT", ("smallint", "int2"), "smallint"),
        ("TEXT", ("text", "text"), "text"),
        ("BOOLEAN", ("boolean", "bool"), "boolean"),
        ("TIMESTAMP WITH TIME ZONE", ("timestamp with time zone", "timestamptz"), "timestamptz"),
        ("JSONB", ("jsonb", "jsonb"), "jsonb"),
        ("UUID", ("uuid", "uuid"), "uuid"),
        ("VECTOR(768)", ("USER-DEFINED", "vector"), "vector"),
        ("TSVECTOR", ("tsvector", "tsvector"), "tsvector"),
        ("BIGINT[]", ("ARRAY", "_int8"), "bigint[]"),
        ("INTEGER[]", ("ARRAY", "_int4"), "integer[]"),
    ]
    for ddl, (data_type, udt), expected in pairs:
        assert canon_from_pg_ddl(ddl) == expected
        assert canon_from_info_schema(data_type, udt) == expected


def test_float_vs_real_is_a_mismatch():
    # SQLAlchemy Float() compiles to FLOAT -> double precision; PG `real` differs.
    assert canon_from_pg_ddl("FLOAT") == "double precision"
    assert canon_from_info_schema("real", "float4") == "real"


def test_diff_clean_when_identical():
    shape = {("s", "t", "c"): ("bigint", False)}
    assert diff(shape, dict(shape)).clean


def test_diff_detects_every_kind():
    declared = {
        ("s", "t1", "id"): ("bigint", False),
        ("s", "only_declared", "id"): ("bigint", False),
        ("s", "t1", "typ"): ("integer", False),
        ("s", "t1", "nul"): ("text", False),
    }
    live = {
        ("s", "t1", "id"): ("bigint", False),
        ("s", "only_live", "id"): ("bigint", False),
        ("s", "t1", "typ"): ("bigint", False),  # type mismatch
        ("s", "t1", "nul"): ("text", True),  # nullable mismatch
        ("s", "t1", "extra"): ("text", True),  # extra column
    }
    kinds = {d.kind for d in diff(declared, live).drifts}
    assert kinds == {
        "missing_table",
        "extra_table",
        "type_mismatch",
        "nullable_mismatch",
        "extra_column",
    }


def test_declared_shape_from_loaded_schema():
    cfg = Config(
        database_url=None,
        db_role=None,
        vector_dim=8,
        sqlite_path=Path("unused.db"),
        schema_dir=FIXTURE,
    )
    shape = declared_shape(load_schema(cfg))
    assert {s for (s, _t, _c) in shape} == {"demo"}
    assert shape[("demo", "widgets", "embedding")] == ("vector", True)
