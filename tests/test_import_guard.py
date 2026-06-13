"""Tests for the A3.2 import-guard -- it flags internal imports, allows public."""

from __future__ import annotations

from typing import TYPE_CHECKING

from mnemosyne_core.import_guard import main, offences

if TYPE_CHECKING:
    from pathlib import Path

_ALLOWED = """\
from mnemosyne_core import Repository, load_schema
from mnemosyne_core.types import Vector
"""

_FORBIDDEN = """\
from mnemosyne_core.engine import make_engine
from mnemosyne_core.session import scoped_session
import mnemosyne_core.base
"""


def test_public_imports_pass(tmp_path: Path):
    (tmp_path / "ok.py").write_text(_ALLOWED, encoding="utf-8")
    assert offences(tmp_path) == []
    assert main(["prog", str(tmp_path)]) == 0


def test_internal_imports_flagged(tmp_path: Path):
    (tmp_path / "bad.py").write_text(_FORBIDDEN, encoding="utf-8")
    hits = offences(tmp_path)
    flagged = {module for _f, _line, module in hits}
    assert flagged == {
        "mnemosyne_core.engine",
        "mnemosyne_core.session",
        "mnemosyne_core.base",
    }
    assert main(["prog", str(tmp_path)]) == 1
