"""
Shared FastMCP app instance.

NOTE ON THE SDK: the original starter code did `from mcp.server import
MCPServer`. We switched to `mcp.server.fastmcp.FastMCP`, which is the
official high-level server class in the `mcp` Python SDK (pip install mcp).
It's a drop-in for what MCPServer was doing (`.tool()`, `.run_stdio_async()`,
etc.) and additionally gives us `.resource()`, `.prompt()`, and a `Context`
object injected into tool handlers for elicitation / progress / logging.
If your team's course build actually ships a different `MCPServer` wrapper,
swap the import back -- everything below only depends on the decorator
surface (`@app.tool()`, `@app.resource()`, `@app.prompt()`) and the
`Context` object, which the two implementations share.

CAPABILITY NEGOTIATION
-----------------------
FastMCP declares server capabilities automatically based on what you
register: because this server registers tools, resources, AND prompts, the
`initialize` response will advertise `capabilities.tools`,
`capabilities.resources`, and `capabilities.prompts` (with `listChanged:
true` for tools, since we mutate the tool set at runtime -- see
notifications.py).

We do NOT declare `elicitation` here because elicitation is a *client*
capability, not a server one (the server calls elicitation/create, but only
a client that advertised support for it during its own `initialize` request
can answer). See agent/client.py for where the client declares it, and
tools/credit_hold.py / tools/rate_exception.py for where the server checks
the *client's* declared capability before trying to elicit, falling back to
a safe non-elicited response if the connected client can't handle it.
"""

from mcp.server.fastmcp import FastMCP

app = FastMCP(
    "swiftrail-mcp-server",
    instructions=(
        "Swiftrail Logistics data-access server. Exposes read-only lookups, "
        "two write tools that touch money/credit state (approve_rate_exception, "
        "release_credit_hold), a runtime-gated finance-manager tool set, a "
        "credit policy resource, a rate-exception justification prompt, and a "
        "long-running customer risk report tool with progress reporting."
    ),
)
