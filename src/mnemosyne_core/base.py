"""The declarative base and shared metadata for all namespace models.

Every namespace module defines its tables against this one ``MetaData`` with an
explicit ``{"schema": <namespace>}`` in ``__table_args__``; importing
:mod:`mnemosyne_core.models` assembles all eight namespaces into a single typed
contract -- one definition, no drift.
"""

from __future__ import annotations

from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase

# A stable naming convention so generated constraint/index names are
# deterministic across backends and diffs.
NAMING_CONVENTION: dict[str, str] = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

metadata = MetaData(naming_convention=NAMING_CONVENTION)


class Base(DeclarativeBase):
    """Declarative base shared by every namespace model.

    Subclasses set ``__tablename__`` and ``__table_args__ = {"schema": ns}``
    where ``ns`` is one of :class:`~mnemosyne_core.namespaces.Namespace`.
    """

    metadata = metadata
