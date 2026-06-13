"""The loader builds MetaData from a spec dir -- the schema-agnostic framework.

Uses a synthetic fixture spec (not the real corpus schema), so the public
framework's tests carry no personal schema.
"""

from pathlib import Path

import pytest

from mnemosyne_core.config import Config
from mnemosyne_core.loader import build_metadata, resolve_type
from mnemosyne_core.schema import load_schema
from mnemosyne_core.spec import load_specs
from mnemosyne_core.types import Vector

FIXTURE = Path(__file__).parent / "fixtures" / "schema"


def test_load_and_build_tables():
    md = build_metadata(load_specs(FIXTURE))
    assert set(md.tables) == {"demo.widgets", "demo.secrets"}


def test_column_shapes_survive():
    md = build_metadata(load_specs(FIXTURE))
    widgets = md.tables["demo.widgets"]
    assert widgets.c.id.primary_key
    assert widgets.c.label.nullable is False
    assert isinstance(widgets.c.embedding.type, Vector)
    assert widgets.c.embedding.type.dim == 8


def test_unknown_type_fails_closed():
    with pytest.raises(ValueError, match="unknown column type"):
        resolve_type("nonsense")


def test_load_schema_from_config():
    cfg = Config(
        database_url=None,
        db_role=None,
        vector_dim=8,
        sqlite_path=Path("unused.db"),
        schema_dir=FIXTURE,
    )
    schema = load_schema(cfg)
    assert schema.namespaces == frozenset({"demo"})
    assert "demo.widgets" in schema.metadata.tables
    assert schema.search_path[-1] == "public"
