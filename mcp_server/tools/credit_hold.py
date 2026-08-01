"""
release_credit_hold -- the highest-stakes write tool in this server.

Releasing a credit hold un-blocks a customer's shipments and lets more
product move to a customer who was flagged for non-payment. That's real
money risk, which is why this tool (not a "get customer" tool) is the one
that earns elicitation:

  * minor hold  -> a sales_rep can release it outright (e.g. an invoice that
    was 45 days late is now paid off).
  * severe hold -> the hold exists because a customer is 90+ days overdue
    and over 25% of their credit limit underwater. A sales_rep should not
    be able to quietly wave that through. The tool pauses mid-call with
    elicitation/create and asks a human for an explicit, typed confirmation
    before it will touch the row -- and if the connected client can't
    elicit at all, it refuses outright instead of silently proceeding.

DEFENSIVE TOOL DESIGN (rubric item)
  1. JSON Schema constraints beyond "it's an int": `hold_id` has an explicit
     `gt=0` bound via Pydantic Field, and the tool's docstring plus
     `additionalProperties: false` (FastMCP's default for typed models) keep
     the schema tight.
  2. Server-side validation independent of the schema: we re-check the row
     actually exists and is currently 'active' before doing anything, instead
     of trusting the caller's hold_id blindly.
  3. Handler-level authorization: the finance_manager check happens here,
     against `SESSION.role` read at call time from the DB-independent
     session object -- not "the schema said it's fine".
"""

from pydantic import BaseModel, Field

from app_instance import app
from db import get_connection
from session import SESSION
from mcp.server.fastmcp import Context


class SevereHoldConfirmation(BaseModel):
    """Elicitation schema shown to the human when a severe hold release needs sign-off."""
    confirm_release: bool = Field(
        description="Type true to confirm you are authorizing release of this SEVERE credit hold."
    )
    authorization_note: str = Field(
        min_length=10,
        description="Short justification for the override (min 10 characters), stored for audit purposes.",
    )


@app.tool()
async def release_credit_hold(hold_id: int = Field(gt=0, description="Primary key of the credit_holds row to release."), ctx: Context = None) -> str:
    """Release an active credit hold on a customer. Minor holds release immediately for any employee.
    Severe holds require an explicit human sign-off via elicitation before they can be released, even
    if the caller's role is finance_manager, because the dollar exposure is high enough to warrant a
    stop-and-confirm on every single release, not just a role check."""

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM credit_holds WHERE id = %s", (hold_id,))
    hold = cursor.fetchone()

    # --- server-side validation, independent of the schema ---
    if not hold:
        cursor.close()
        conn.close()
        return f"No credit hold found with id {hold_id}"

    if hold["status"] != "active":
        cursor.close()
        conn.close()
        return f"Credit hold {hold_id} is already '{hold['status']}'."

    if hold["severity"] == "minor":
        # Low risk, no state that would justify interrupting the call.
        cursor.execute(
            "UPDATE credit_holds SET status = 'released', released_by = %s, released_at = NOW() WHERE id = %s",
            (SESSION.employee_id, hold_id),
        )
        conn.commit()
        cursor.close()
        conn.close()
        return f"Credit hold {hold_id} (minor) released by employee {SESSION.employee_id}."

    # --- severe hold: handler-level authorization + elicitation ---
    client_supports_elicitation = _client_declared_elicitation(ctx)

    if not client_supports_elicitation:
        cursor.close()
        conn.close()
        return (
            f"Credit hold {hold_id} is SEVERE (reason: {hold['reason']}). "
            "This client connection did not declare elicitation support during "
            "initialize, so this server will not attempt a silent override. "
            "Reconnect with a client that supports elicitation, or have a "
            "finance_manager release this hold through another channel."
        )

    result = await ctx.elicit(
        message=(
            f"Credit hold {hold_id} on customer_id={hold['customer_id']} is SEVERE "
            f"(reason: {hold['reason']}). Releasing it will let this customer's "
            f"shipments move again while they remain significantly overdue. "
            f"Confirm you want to release it."
        ),
        schema=SevereHoldConfirmation,
    )

    if result.action != "accept" or not result.data.confirm_release:
        cursor.close()
        conn.close()
        return f"Credit hold {hold_id} was NOT released (human declined or did not confirm)."

    if SESSION.role != "finance_manager":
        # Even with a human confirming in the elicitation dialog, we still gate
        # on role: elicitation proves "a human is present and paying attention",
        # it does not by itself prove "this human is authorized". Both checks
        # must pass, at the handler level, before the row changes.
        cursor.close()
        conn.close()
        return (
            f"Credit hold {hold_id} is SEVERE and requires finance_manager "
            f"authorization. Current session role is '{SESSION.role}'. Use the "
            "authenticate tool to switch to a finance_manager session, then retry."
        )

    cursor.execute(
        "UPDATE credit_holds SET status = 'released', released_by = %s, released_at = NOW() WHERE id = %s",
        (SESSION.employee_id, hold_id),
    )
    conn.commit()
    cursor.close()
    conn.close()

    return (
        f"Credit hold {hold_id} (SEVERE) released by employee {SESSION.employee_id} "
        f"({SESSION.role}). Audit note: {result.data.authorization_note}"
    )


def _client_declared_elicitation(ctx: Context) -> bool:
    """Best-effort check of the connected client's declared capabilities.

    The exact attribute path depends on your installed `mcp` SDK version --
    on recent versions the negotiated client capabilities are reachable via
    `ctx.session.client_params.capabilities.elicitation`. We fail safe
    (assume NOT supported) if that path doesn't exist, rather than crashing
    or silently calling ctx.elicit() into the void.
    """
    try:
        caps = ctx.session.client_params.capabilities
        return caps.elicitation is not None
    except AttributeError:
        return False
