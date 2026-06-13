"""Runtime configuration for the mnemosyne core.

All knobs are environment-driven (Twelve-Factor). The backend is selected by the
presence of ``DATABASE_URL``: set -> PostgreSQL (the corpus), unset -> the baked
SQLite file (standalone degradation). Everything else has a baked default so a
star runs with zero configuration.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Mapping

DEFAULT_VECTOR_DIM = 768  # nomic-embed-text
DEFAULT_SQLITE_FILENAME = "mnemosyne.db"


@dataclass(frozen=True, slots=True)
class Config:
    """Resolved runtime configuration.

    Construct via :meth:`from_env`. ``database_url`` is the single backend
    selector: present -> PostgreSQL, absent -> the baked SQLite file at
    ``sqlite_path``.
    """

    database_url: str | None
    db_role: str | None
    vector_dim: int
    sqlite_path: Path
    schema_dir: Path | None = None

    @property
    def is_postgres(self) -> bool:
        """True when a ``DATABASE_URL`` selects the PostgreSQL backend."""
        return self.database_url is not None

    @property
    def backend(self) -> str:
        """The active backend name -- ``"postgres"`` or ``"sqlite"``."""
        return "postgres" if self.is_postgres else "sqlite"

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> Config:
        """Resolve configuration from ``env`` (defaults to ``os.environ``)."""
        source = os.environ if env is None else env
        dim_raw = source.get("MNEMOSYNE_VECTOR_DIM")
        schema_dir = source.get("MNEMOSYNE_SCHEMA_DIR")
        return cls(
            database_url=source.get("DATABASE_URL") or None,
            db_role=source.get("MNEMOSYNE_DB_ROLE") or None,
            vector_dim=int(dim_raw) if dim_raw else DEFAULT_VECTOR_DIM,
            sqlite_path=Path(
                source.get("MNEMOSYNE_SQLITE_PATH") or DEFAULT_SQLITE_FILENAME
            ),
            schema_dir=Path(schema_dir) if schema_dir else None,
        )
