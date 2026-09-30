"""CampusHire AI MCP server package.

Exposes a small set of Model Context Protocol tools backed by the project's
pure analysis kernel (see ``backend/app/kernel``). The server is a thin,
read-only adapter over kernel functions; it performs no database or network I/O
and does not mutate any application state.

Named ``mcp_server`` (not ``mcp``) so it never shadows the installed ``mcp`` SDK
package when running from the ``backend/`` directory.
"""
