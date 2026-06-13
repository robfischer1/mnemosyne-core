"""A2 surface tests -- a reference consumer reads/writes by name, via the API only."""

from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import event, text

from mnemosyne_core import Config, NamespaceBoundaryError, Repository
from mnemosyne_core.engine import make_engine
from mnemosyne_core.schema import load_schema
from mnemosyne_core.session import scoped_session

FIXTURE = Path(__file__).parent / "fixtures" / "schema"


def _config(sqlite_path: Path) -> Config:
    return Config(
        database_url=None,
        db_role=None,
        vector_dim=8,
        sqlite_path=sqlite_path,
        schema_dir=FIXTURE,
    )


@pytest.fixture
def repo(tmp_path: Path) -> Repository:
    cfg = _config(tmp_path / "r.db")
    schema = load_schema(cfg)
    engine = make_engine(cfg, schema.namespaces, schema.search_path)
    schema.metadata.create_all(engine)
    return Repository(engine, schema, ["demo"])


def test_read_after_insert(repo: Repository):
    repo.insert("demo", "widgets", {"id": 1, "label": "alpha"})
    repo.insert("demo", "widgets", {"id": 2, "label": "beta"})
    rows = repo.read("demo", "widgets")
    assert {r["label"] for r in rows} == {"alpha", "beta"}
    assert len(repo.read("demo", "widgets", limit=1)) == 1


def test_boundary_enforced_through_repo(repo: Repository):
    with pytest.raises(NamespaceBoundaryError):
        repo.insert("history", "events", {"id": 1})


def test_public_surface_hides_engine_and_session():
    import mnemosyne_core as m

    assert "Repository" in m.__all__
    assert "make_engine" not in m.__all__
    assert not hasattr(m, "sessionmaker")


def test_sessions_released_no_leak_soak(tmp_path: Path):
    # FR-5 / A2.2: deterministic release -- every checkout is matched by a
    # checkin across 200 cycles, so no connection leaks.
    cfg = _config(tmp_path / "soak.db")
    schema = load_schema(cfg)
    engine = make_engine(cfg, schema.namespaces, schema.search_path)
    stats = {"checkout": 0, "checkin": 0}

    def _on_checkout(*_args: object) -> None:
        stats["checkout"] += 1

    def _on_checkin(*_args: object) -> None:
        stats["checkin"] += 1

    event.listen(engine, "checkout", _on_checkout)
    event.listen(engine, "checkin", _on_checkin)
    for _ in range(200):
        with scoped_session(engine, ["demo"]) as s:
            s.execute(text("SELECT 1"))
    assert stats["checkout"] > 0
    assert stats["checkout"] == stats["checkin"]
