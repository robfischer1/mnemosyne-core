"""A4 capability tests -- parity + fail-clear across PG and SQLite (T040).

The cross-backend *identical-results* claim (A4.3) is proven here on its SQLite
leg (sqlite-vec) plus the capability mapping; the PostgreSQL leg (pgvector) runs
where ``DATABASE_URL`` reaches the store. The synthetic fixture never touches the
real corpus.
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING, Any

import pytest
from sqlalchemy import Integer, text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from mnemosyne_core.capabilities import (
    Capability,
    available_capabilities,
    sqlite_vec_loadable,
)
from mnemosyne_core.config import Config
from mnemosyne_core.engine import make_engine
from mnemosyne_core.session import scoped_session
from mnemosyne_core.types import Vector

if TYPE_CHECKING:
    from pathlib import Path

_SQLITE = Config.from_env({})
_PG = Config.from_env({"DATABASE_URL": "postgresql://h/db"})


def test_vector_search_available_on_both_backends():
    # pgvector on PG, sqlite-vec on SQLite -- the A4.3 capability mapping.
    assert Capability.VECTOR_SEARCH in available_capabilities(_PG)
    assert Capability.VECTOR_SEARCH in available_capabilities(_SQLITE)


def test_role_enforcement_is_postgres_only():
    # SET ROLE maps to a no-op on SQLite, so the capability is PG-only.
    assert Capability.ROLE_ENFORCEMENT in available_capabilities(_PG)
    assert Capability.ROLE_ENFORCEMENT not in available_capabilities(_SQLITE)


class _VB(DeclarativeBase):
    pass


class _Emb(_VB):
    __tablename__ = "parity_emb"
    __table_args__ = {"schema": "search"}
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    embedding: Mapped[Any] = mapped_column(Vector(4))


def test_vector_column_roundtrips_on_sqlite(tmp_path: Path):
    # The portable Vector type stores/loads a vector on SQLite (schema flattened).
    engine = make_engine(
        Config.from_env({"MNEMOSYNE_SQLITE_PATH": str(tmp_path / "v.db")}),
        ["search"],
    )
    _VB.metadata.create_all(engine)
    with scoped_session(engine, ["search"]) as s:
        s.add(_Emb(id=1, embedding=[1.0, 2.0, 3.0, 4.0]))
    with scoped_session(engine, ["search"]) as s:
        got = s.get(_Emb, 1)
        assert got is not None
        assert list(got.embedding) == [1.0, 2.0, 3.0, 4.0]


@pytest.mark.skipif(
    not sqlite_vec_loadable(), reason="sqlite-vec not loadable on this platform"
)
def test_sqlite_vec_knn_nearest(tmp_path: Path):
    # A real vec0 KNN query: the nearest neighbour to [1,2,3,4] is row 1, not row 2.
    engine = make_engine(
        Config.from_env({"MNEMOSYNE_SQLITE_PATH": str(tmp_path / "knn.db")}),
        ["search"],
    )
    with engine.begin() as conn:
        conn.execute(text("CREATE VIRTUAL TABLE vec USING vec0(embedding float[4])"))
        conn.execute(
            text("INSERT INTO vec(rowid, embedding) VALUES (1, :a), (2, :b)"),
            {"a": "[1,2,3,4]", "b": "[9,9,9,9]"},
        )
    with engine.connect() as conn:
        rows = conn.execute(
            text(
                "SELECT rowid FROM vec WHERE embedding MATCH :q "
                "ORDER BY distance LIMIT 1"
            ),
            {"q": "[1,2,3,4]"},
        ).all()
    assert rows[0][0] == 1


def _sqlite_knn(tmp_path: Path, vectors: dict[int, str], query: str) -> int | None:
    engine = make_engine(
        Config.from_env({"MNEMOSYNE_SQLITE_PATH": str(tmp_path / "pl.db")}),
        ["search"],
    )
    with engine.begin() as conn:
        conn.execute(text("CREATE VIRTUAL TABLE v USING vec0(embedding float[4])"))
        for rid, vec in vectors.items():
            conn.execute(
                text("INSERT INTO v(rowid, embedding) VALUES (:i, :v)"),
                {"i": rid, "v": vec},
            )
    with engine.connect() as conn:
        return conn.execute(
            text("SELECT rowid FROM v WHERE embedding MATCH :q ORDER BY distance LIMIT 1"),
            {"q": query},
        ).scalar()


@pytest.mark.skipif(
    not os.environ.get("DATABASE_URL"), reason="needs a live PostgreSQL DATABASE_URL"
)
def test_pg_sqlite_knn_parity_identical(tmp_path: Path):
    # A4.3: the mappable vector capability returns the *same* nearest neighbour
    # across pgvector and sqlite-vec on a synthetic fixture (never the corpus).
    vectors = {1: "[1,2,3,4]", 2: "[9,9,9,9]", 3: "[1,2,3,5]"}
    query = "[1,2,3,4]"
    sqlite_nearest = _sqlite_knn(tmp_path, vectors, query)

    pg = make_engine(
        Config.from_env({"DATABASE_URL": os.environ["DATABASE_URL"]}), ["search"]
    )
    try:
        with pg.begin() as conn:
            conn.execute(text("CREATE TEMP TABLE _parity (id int, emb vector(4))"))
            for rid, vec in vectors.items():
                conn.execute(
                    text("INSERT INTO _parity VALUES (:i, CAST(:v AS vector))"),
                    {"i": rid, "v": vec},
                )
            pg_nearest = conn.execute(
                text("SELECT id FROM _parity ORDER BY emb <-> CAST(:q AS vector) LIMIT 1"),
                {"q": query},
            ).scalar()
    finally:
        pg.dispose()

    assert sqlite_nearest == pg_nearest == 1
