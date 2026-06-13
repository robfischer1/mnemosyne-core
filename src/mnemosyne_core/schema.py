"""Load a runtime :class:`Schema` from the spec -- the framework's entry point.

The framework imports no models: it reads the namespace TOMLs from
``config.schema_dir`` and builds the metadata, the namespace set, and the
search-path order. Every store access binds to the resulting metadata; with no
schema configured the framework cannot resolve a table, which is the point --
the schema is injected, never baked in.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from mnemosyne_core.loader import build_metadata
from mnemosyne_core.spec import load_specs

if TYPE_CHECKING:
    from sqlalchemy import MetaData

    from mnemosyne_core.config import Config


class SchemaNotConfiguredError(RuntimeError):
    """Raised when no schema directory is configured (``MNEMOSYNE_SCHEMA_DIR``)."""


@dataclass(frozen=True, slots=True)
class Schema:
    """The loaded schema: its metadata, namespace set, and search-path order."""

    metadata: MetaData
    namespaces: frozenset[str]
    search_path: tuple[str, ...]


def load_schema(config: Config) -> Schema:
    """Build the :class:`Schema` from the spec at ``config.schema_dir``."""
    if config.schema_dir is None:
        raise SchemaNotConfiguredError(
            "set MNEMOSYNE_SCHEMA_DIR to the schema spec directory"
        )
    specs = load_specs(config.schema_dir)
    names = tuple(sorted(spec.namespace for spec in specs))
    return Schema(
        metadata=build_metadata(specs),
        namespaces=frozenset(names),
        search_path=(*names, "public"),
    )
