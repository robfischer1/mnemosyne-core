"""Smoke tests for mnemosyne-core."""

from mnemosyne_core import __version__
from mnemosyne_core.server import mcp, ping


def test_version() -> None:
    assert __version__ == "0.2.0"


def test_ping_tool() -> None:
    assert ping()["status"] == "ok"


def test_server_name() -> None:
    assert mcp.name == "mnemosyne-core"
