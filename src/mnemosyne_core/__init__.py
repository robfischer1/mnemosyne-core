"""mnemosyne core -- the shared schema-contract framework every star imports.

The public surface: point ``MNEMOSYNE_SCHEMA_DIR`` at the schema spec, open a
:class:`~mnemosyne_core.repository.Repository`, and read/write by
``(namespace, table)`` -- never a raw engine or hand-built SQL. The backend
(PostgreSQL corpus or standalone SQLite) is selected at runtime from the
environment; the schema is loaded from the spec, never baked in.
"""

from __future__ import annotations

from mnemosyne_core.capabilities import (
    Capability,
    CapabilityError,
    available_capabilities,
    require,
)
from mnemosyne_core.config import Config
from mnemosyne_core.repository import Repository
from mnemosyne_core.schema import Schema, load_schema
from mnemosyne_core.session import NamespaceBoundaryError, scoped_session

__version__ = "0.1.0"

__all__ = [
    "Capability",
    "CapabilityError",
    "Config",
    "NamespaceBoundaryError",
    "Repository",
    "Schema",
    "__version__",
    "available_capabilities",
    "load_schema",
    "require",
    "scoped_session",
]
