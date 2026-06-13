"""Capability declaration and fail-clear startup checks.

A star declares the capabilities it needs; :func:`require` resolves what the
active backend actually offers and raises :class:`CapabilityError` -- naming the
missing capability -- when the backend cannot satisfy them (FR-11). PostgreSQL
offers the full set; SQLite offers vector search only when sqlite-vec loads, and
never offers PostgreSQL-role enforcement.
"""

from __future__ import annotations

from enum import StrEnum
from typing import TYPE_CHECKING

from mnemosyne_core.config import Config

if TYPE_CHECKING:
    from collections.abc import Iterable


class Capability(StrEnum):
    """A backend feature a star may require."""

    VECTOR_SEARCH = "vector_search"
    FULLTEXT_SEARCH = "fulltext_search"
    ROLE_ENFORCEMENT = "role_enforcement"
    JSON_QUERY = "json_query"


class CapabilityError(RuntimeError):
    """A required capability is unavailable on the selected backend."""


def sqlite_vec_loadable() -> bool:
    """Return True when sqlite-vec can load on this interpreter/platform."""
    import sqlite3

    try:
        conn = sqlite3.connect(":memory:")
        conn.enable_load_extension(True)
        import sqlite_vec

        sqlite_vec.load(conn)
        conn.close()
    except Exception:  # noqa: BLE001 - any failure means "not available", fail-clear
        return False
    return True


def available_capabilities(config: Config | None = None) -> set[Capability]:
    """Return the capabilities the active backend offers."""
    cfg = config or Config.from_env()
    caps: set[Capability] = {Capability.JSON_QUERY, Capability.FULLTEXT_SEARCH}
    if cfg.is_postgres:
        caps |= {Capability.VECTOR_SEARCH, Capability.ROLE_ENFORCEMENT}
    elif sqlite_vec_loadable():
        caps.add(Capability.VECTOR_SEARCH)
    return caps


def require(
    capabilities: Iterable[Capability],
    config: Config | None = None,
) -> None:
    """Raise :class:`CapabilityError` if any of *capabilities* is unavailable."""
    cfg = config or Config.from_env()
    have = available_capabilities(cfg)
    missing = [c for c in capabilities if c not in have]
    if missing:
        names = ", ".join(c.value for c in missing)
        raise CapabilityError(
            f"backend {cfg.backend!r} lacks required capability/ies: {names}"
        )
