"""Foundation unit tests (T008) -- SQLite-backed, no live PG required."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest
from sqlalchemy import Integer, String, select
from sqlalchemy.dialects import postgresql, sqlite
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

if TYPE_CHECKING:
    from pathlib import Path

    from sqlalchemy.engine import Engine
    from sqlalchemy.types import TypeEngine

from mnemosyne_core.capabilities import (
    Capability,
    CapabilityError,
    available_capabilities,
    require,
)
from mnemosyne_core.config import Config
from mnemosyne_core.engine import make_engine
from mnemosyne_core.session import NamespaceBoundaryError, scoped_session
from mnemosyne_core.types import JSONB, BigIntArray, TSVector, Vector

PG = postgresql.dialect()
LITE = sqlite.dialect()


# --- config ---------------------------------------------------------------
def test_config_defaults_to_sqlite():
    cfg = Config.from_env({})
    assert cfg.is_postgres is False
    assert cfg.backend == "sqlite"
    assert cfg.vector_dim == 768
    assert cfg.sqlite_path.name == "mnemosyne.db"


def test_config_database_url_selects_postgres():
    cfg = Config.from_env({"DATABASE_URL": "postgresql://h/db"})
    assert cfg.is_postgres is True
    assert cfg.backend == "postgres"


def test_config_env_overrides():
    cfg = Config.from_env({"MNEMOSYNE_VECTOR_DIM": "1024"})
    assert cfg.vector_dim == 1024


# --- portable types -------------------------------------------------------
@pytest.mark.parametrize(
    ("type_", "pg_token", "lite_token"),
    [
        (Vector(768), "VECTOR", "JSON"),
        (JSONB(), "JSONB", "JSON"),
        (BigIntArray(), "BIGINT", "JSON"),
        (TSVector(), "TSVECTOR", "TEXT"),
    ],
)
def test_types_render_per_dialect(
    type_: TypeEngine[Any], pg_token: str, lite_token: str
):
    assert pg_token in type_.compile(dialect=PG).upper()
    assert lite_token in type_.compile(dialect=LITE).upper()


# --- engine selection -----------------------------------------------------
def test_make_engine_sqlite(tmp_path: Path):
    cfg = Config.from_env({"MNEMOSYNE_SQLITE_PATH": str(tmp_path / "t.db")})
    engine = make_engine(cfg, ["entities"])
    assert engine.dialect.name == "sqlite"


# --- session boundary -----------------------------------------------------
class _B(DeclarativeBase):
    pass


class _Entity(_B):
    __tablename__ = "boundary_entity"
    __table_args__ = {"schema": "entities"}
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String)


class _HistoryRow(_B):
    __tablename__ = "boundary_history"
    __table_args__ = {"schema": "history"}
    id: Mapped[int] = mapped_column(Integer, primary_key=True)


@pytest.fixture
def lite_engine(tmp_path: Path):
    cfg = Config.from_env({"MNEMOSYNE_SQLITE_PATH": str(tmp_path / "b.db")})
    engine = make_engine(cfg, ["entities", "history"])
    _B.metadata.create_all(engine)
    return engine


def test_write_in_declared_namespace_ok(lite_engine: Engine):
    with scoped_session(lite_engine, ["entities"]) as s:
        s.add(_Entity(id=1, name="ok"))
    with scoped_session(lite_engine, ["entities"]) as s:
        assert s.scalar(select(_Entity.name).where(_Entity.id == 1)) == "ok"


def test_write_outside_declared_namespace_rejected(lite_engine: Engine):
    with (
        pytest.raises(NamespaceBoundaryError),
        scoped_session(lite_engine, ["entities"]) as s,
    ):
        s.add(_HistoryRow(id=1))


# --- capabilities ---------------------------------------------------------
def test_sqlite_lacks_role_enforcement():
    cfg = Config.from_env({})
    assert Capability.ROLE_ENFORCEMENT not in available_capabilities(cfg)
    with pytest.raises(CapabilityError, match="role_enforcement"):
        require([Capability.ROLE_ENFORCEMENT], cfg)


def test_postgres_offers_full_set():
    cfg = Config.from_env({"DATABASE_URL": "postgresql://h/db"})
    caps = available_capabilities(cfg)
    assert {Capability.VECTOR_SEARCH, Capability.ROLE_ENFORCEMENT} <= caps
    require([Capability.VECTOR_SEARCH, Capability.JSON_QUERY], cfg)  # no raise
