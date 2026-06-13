"""Import-guard (A3.2): fail if a consumer imports core internals by path.

Stars consume the **public surface** -- the top-level ``mnemosyne_core`` package
(``Repository``, ``load_schema``, ``scoped_session``, ...) and the portable
``mnemosyne_core.types``. They must never reach into the internal modules
(``engine``, ``session``, ``base``, ``schema_diff``, ``import_guard``) by path --
those are implementation, not contract. A star wires this into its CI::

    uv run python -m mnemosyne_core.import_guard src

It exits non-zero, listing every offence, when a forbidden import is found.
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

PACKAGE = "mnemosyne_core"
INTERNAL_MODULES = frozenset(
    {"engine", "session", "base", "schema_diff", "import_guard"}
)


def _is_internal(module: str | None) -> bool:
    if not module:
        return False
    parts = module.split(".")
    return parts[:1] == [PACKAGE] and len(parts) >= 2 and parts[1] in INTERNAL_MODULES


def offences(target: str | Path) -> list[tuple[Path, int, str]]:
    """Return (file, line, module) for every forbidden internal import under target."""
    found: list[tuple[Path, int, str]] = []
    root = Path(target)
    files = root.rglob("*.py") if root.is_dir() else [root]
    for py in files:
        tree = ast.parse(py.read_text(encoding="utf-8"), filename=str(py))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and _is_internal(node.module):
                found.append((py, node.lineno, node.module or ""))
            elif isinstance(node, ast.Import):
                found.extend(
                    (py, node.lineno, alias.name)
                    for alias in node.names
                    if _is_internal(alias.name)
                )
    return found


def main(argv: list[str] | None = None) -> int:
    """Scan the given targets (default ``src``) and report forbidden imports."""
    args = sys.argv if argv is None else argv
    targets = args[1:] or ["src"]
    found = [hit for t in targets for hit in offences(t)]
    for py, line, module in found:
        print(f"{py}:{line}: forbidden internal import {module!r} -- use the public surface")
    if found:
        print(
            f"\n{len(found)} forbidden import(s). "
            f"Stars import `mnemosyne_core`, not its internals."
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
