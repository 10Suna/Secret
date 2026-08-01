"""
approve_rate_exception -- discount approval on a shipment.

<=15% discount is within any employee's standing authority and resolves
immediately. >15% (up to the DB's hard cap of 50%, enforced by the schema
CHECK constraint) is where margin actually gets given away, so it triggers
elicitation: the model must stop and get an explicit human decision before
approving it at all, and the row will only ever move to 'approved' (vs.
'auto_approved') under a finance_manager session, checked in the handler.
"""

from pydantic import BaseModel, Field

from app_instance import app
from db import get_connection
from session import SESSION
from mcp.server.fastmcp import Context


class DiscountOverrideDecision(BaseModel):
    """Elicitation schema for a discount that exceeds standing sales_rep authority."""
    approve: bool = Field(description="Type true to approve this above-authority discount, false to reject it.")
    reviewer_note: str = Field(
        min_length=10,
        description="Reason for the decision (min 10 characters), stored for audit purposes.",
    )


@app.tool()
async def approve_rate_exception(
    exception_id: int = Field(gt=0, description="Primary key of the rate_exceptions row to approve."),
    ctx: Context = None,
) -> str:
    """Approve a pending rate exception (discount) request on a shipment. Discounts of 15% or less
    auto-approve immediately. Discounts over 15% require an explicit human decision via elicitation
    plus finance_manager authorization before the row can move to 'approved'."""

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM rate_exceptions WHERE id = %s", (exception_id,))
    exception = cursor.fetchone()

    # --- server-side validation, independent of the schema ---
    if not exception:
        cursor.close()
        conn.close()
        return f"No rate exception found with id {exception_id}"

    if exception["status"] != "pending":
        cursor.close()
        conn.close()
        return f"Rate exception {exception_id} is already '{exception['status']}', cannot re-approve."

    discount = float(exception["discount_pct"])

    if discount <= 15:
        cursor.execute(
            "UPDATE rate_exceptions SET status = 'auto_approved', approved_by = NULL, resolved_at = NOW() WHERE id = %s",
            (exception_id,),
        )
        conn.commit()
        cursor.close()
        conn.close()
        return f"Rate exception {exception_id} marked as 'auto_approved' ({discount}% is within standing authority)."

    # --- above-authority discount: elicitation + handler-level authorization ---
    client_supports_elicitation = _client_declared_elicitation(ctx)

    if not client_supports_elicitation:
        cursor.close()
        conn.close()
        return (
            f"Discount of {discount}% on rate exception {exception_id} exceeds sales_rep "
            "authority (max 15% auto-approval), and this client connection does not "
            "support elicitation. Refusing to auto-approve; have a finance_manager "
            "review this through a client that supports elicitation."
        )

    result = await ctx.elicit(
        message=(
            f"Rate exception {exception_id} requests a {discount}% discount "
            f"(justification: {exception['justification']}). This exceeds the 15% "
            f"sales_rep auto-approval ceiling. Approve or reject?"
        ),
        schema=DiscountOverrideDecision,
    )

    if result.action != "accept" or not result.data.approve:
        cursor.execute(
            "UPDATE rate_exceptions SET status = 'rejected', approved_by = %s, resolved_at = NOW() WHERE id = %s",
            (SESSION.employee_id, exception_id),
        )
        conn.commit()
        cursor.close()
        conn.close()
        return f"Rate exception {exception_id} was rejected (human declined the override)."

    if SESSION.role != "finance_manager":
        cursor.close()
        conn.close()
        return (
            f"Discount of {discount}% on rate exception {exception_id} was confirmed by a "
            f"human, but the active session role is '{SESSION.role}', not finance_manager. "
            "Use the authenticate tool to switch roles, then retry the approval."
        )

    cursor.execute(
        "UPDATE rate_exceptions SET status = 'approved', approved_by = %s, resolved_at = NOW() WHERE id = %s",
        (SESSION.employee_id, exception_id),
    )
    conn.commit()
    cursor.close()
    conn.close()

    return (
        f"Rate exception {exception_id} marked as 'approved' by employee "
        f"{SESSION.employee_id} ({SESSION.role}). Note: {result.data.reviewer_note}"
    )


def _client_declared_elicitation(ctx: Context) -> bool:
    try:
        caps = ctx.session.client_params.capabilities
        return caps.elicitation is not None
    except AttributeError:
        return False
