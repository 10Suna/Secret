"""
Production-shaped transport: Streamable HTTP.

Why we moved off stdio: stdio only works when the client can spawn the
server as a local subprocess on the same machine. Swiftrail's actual rollout
plan has the sales team's agent running on their laptops while the MCP
server sits next to the database on internal infrastructure -- there is no
"spawn the server as a child process" story there, and we want one server
process serving many concurrent employee sessions rather than one process
per stdio pipe. Streamable HTTP is the transport in the spec built for
exactly that: a long-lived server reachable over the network, with the
option to layer standard HTTP auth (a bearer token / reverse proxy) in
front of it, which stdio has no equivalent for.

We kept server.py (stdio) working throughout -- the two files share every
tool/resource/prompt module, only the transport differs -- so local
development and debugging didn't get slower just because the deployment
target changed. The commit that added this file is a separate commit from
the tool-logic commits, on purpose, so the transport change is visible on
its own in `git log`.
"""

from app_instance import app

import tools.read_tools
import tools.rate_exception
import tools.credit_hold
import tools.auth_tools
import tools.progress_tools
import resources.policy_resource
import prompts.prompt_templates


if __name__ == "__main__":
    # FastMCP's Streamable HTTP transport. Binds to 0.0.0.0:8000 by default;
    # override with app.settings.host / app.settings.port or the MCP_HOST /
    # MCP_PORT env vars depending on your installed SDK version. Put this
    # behind a reverse proxy (nginx/Caddy) doing TLS + bearer-token auth
    # before exposing it outside localhost -- this file intentionally does
    # not implement its own auth layer.
    app.run(transport="streamable-http")
