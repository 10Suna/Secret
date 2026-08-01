"""
Development transport: stdio.

Early in the project this is the only transport we ran -- one developer,
one local client process, no auth/network story needed yet. Kept as the
`python server.py` entrypoint for local iteration and for `agent/demo.py`
when run with --transport stdio. See server_http.py for the transport we
moved to once the server needed to be reachable by a real client process
running somewhere else (see README "Transport choice" for the justification
and the commit where this switch happened).
"""

import asyncio

from app_instance import app

# Registering these modules is what actually adds their @app.tool() /
# @app.resource() / @app.prompt() decorated functions to `app`.
import tools.read_tools
import tools.rate_exception
import tools.credit_hold
import tools.auth_tools
import tools.progress_tools
import resources.policy_resource
import prompts.prompt_templates


if __name__ == "__main__":
    asyncio.run(app.run_stdio_async())
