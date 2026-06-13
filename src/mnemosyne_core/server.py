"""A standard Forge MCP service.

A standard Forge MCP service: streamable-HTTP, stateless, config from env.
"""

from __future__ import annotations

import os

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("mnemosyne-core", stateless_http=True, json_response=True)


@mcp.tool()
def ping() -> dict[str, str]:
    """Liveness sample tool — returns ok. Replace with real tools."""
    return {"status": "ok", "service": "mnemosyne-core"}


def main() -> None:
    """Run the MCP server over streamable-HTTP, binding 0.0.0.0:$PORT."""
    mcp.settings.host = os.environ.get("HOST", "0.0.0.0")  # noqa: S104
    mcp.settings.port = int(os.environ.get("PORT", "8201"))
    mcp.run(transport="streamable-http")


if __name__ == "__main__":
    main()
