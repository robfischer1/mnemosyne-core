"""Grant DDL generation from the spec's tier flags."""

from __future__ import annotations

from pathlib import Path

import pytest

from mnemosyne_core.grants import generate_grant_ddl, tiered_tables
from mnemosyne_core.spec import ColumnSpec, NamespaceSpec, TableSpec, load_specs

FIXTURE = Path(__file__).parent / "fixtures" / "schema"


def test_tiered_tables_from_fixture():
    assert ("demo", "secrets", "phi") in tiered_tables(load_specs(FIXTURE))


def test_grant_ddl_emits_revoke_then_grant():
    ddl = generate_grant_ddl(load_specs(FIXTURE))
    assert "REVOKE ALL ON demo.secrets FROM phdb_general;" in ddl
    assert "GRANT SELECT ON demo.secrets TO phdb_phi;" in ddl
    # a non-tiered table emits nothing
    assert "demo.widgets" not in ddl


def test_unknown_tier_fails_closed():
    spec = NamespaceSpec(
        "x",
        (TableSpec("t", (ColumnSpec("id", "bigint", pk=True),), tier="mystery"),),
    )
    with pytest.raises(ValueError, match="no role mapped"):
        generate_grant_ddl([spec])
