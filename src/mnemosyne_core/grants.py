"""Generate the PII/PHI grant DDL from the schema spec's tier flags.

A table's ``tier`` (e.g. ``phi``, ``others_pii``) is the only policy the spec
carries; this module turns those flags into idempotent REVOKE/GRANT statements, so
the grant model is reproducible from the spec rather than hand-written. The
tier -> role mapping and the general role are operator policy, injected here and
defaulting to the live phdb role set.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping

    from mnemosyne_core.spec import NamespaceSpec

DEFAULT_TIER_ROLES: dict[str, str] = {
    "phi": "phdb_phi",
    "others_pii": "phdb_pii",
    "contact_pii": "phdb_pii",
}


def tiered_tables(specs: Iterable[NamespaceSpec]) -> list[tuple[str, str, str]]:
    """Return ``(namespace, table, tier)`` for every table carrying a tier flag."""
    return [
        (ns.namespace, table.name, table.tier)
        for ns in specs
        for table in ns.tables
        if table.tier is not None
    ]


def generate_grant_ddl(
    specs: Iterable[NamespaceSpec],
    *,
    general_role: str = "phdb_general",
    tier_roles: Mapping[str, str] | None = None,
) -> str:
    """Render fail-closed REVOKE/GRANT DDL for every tier-flagged table."""
    roles = dict(DEFAULT_TIER_ROLES if tier_roles is None else tier_roles)
    lines: list[str] = []
    for namespace, table, tier in sorted(tiered_tables(specs)):
        role = roles.get(tier)
        if role is None:
            raise ValueError(f"no role mapped for tier {tier!r}")
        qualified = f"{namespace}.{table}"
        lines.append(f"REVOKE ALL ON {qualified} FROM {general_role};")
        lines.append(f"GRANT SELECT ON {qualified} TO {role};")
    return "\n".join(lines)
