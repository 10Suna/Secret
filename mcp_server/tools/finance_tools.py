"""
Tools that only exist in the tool set while SESSION.role == "finance_manager".

These are registered/unregistered at runtime by tools/auth_tools.py, which is
also what fires the tools/list_changed notification. They are NOT declared
with @app.tool() at import time like the rest of the tools in this package --
that would make them always-visible, which defeats the point.

Why this tool deserves to be finance-only rather than just "gated in the
handler": list_portfolio_credit_exposure returns company-wide financial
exposure across every customer at once (total overdue balance, every severe
hold, every above-authority pending discount). A sales_rep legitimately
needs single-customer detail to do their job; there's no legitimate
sales_rep use case for the aggregated company-wide risk picture, so it's
withheld from tools/list entirely rather than merely rejected at call time.
"""

import json

from db import get_connection

_TOOL_NAME = "list_portfolio_credit_exposure"
_registered = False


def _list_portfolio_credit_exposure_impl() -> str:
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT id, customer_id, reason, severity, placed_at FROM credit_holds WHERE status = 'active'"
    )
    active_holds = cursor.fetchall()

    cursor.execute(
        "SELECT id, shipment_id, discount_pct, justification FROM rate_exceptions WHERE status = 'pending'"
    )
    pending_exceptions = cursor.fetchall()

    cursor.execute(
        "SELECT id, name, balance_due, credit_limit FROM customers WHERE credit_status = 'hold'"
    )
    customers_on_hold = cursor.fetchall()

    cursor.close()
    conn.close()

    return json.dumps(
        {
            "active_credit_holds": active_holds,
            "pending_above_authority_discounts": [
                e for e in pending_exceptions if float(e["discount_pct"]) > 15
            ],
            "customers_on_hold": customers_on_hold,
        },
        default=str,
    )


def register(app) -> None:
    """Add the finance-manager tool set to the live server."""
    global _registered
    if _registered:
        return
    app.add_tool(
        _list_portfolio_credit_exposure_impl,
        name=_TOOL_NAME,
        description=(
            "FINANCE-MANAGER ONLY. Company-wide credit risk snapshot: every active "
            "credit hold, every pending discount above the 15% sales_rep ceiling, "
            "and every customer currently on hold. Only visible in the tool set "
            "while the session is authenticated as a finance_manager."
        ),
    )
    _registered = True


def unregister(app) -> None:
    """Remove the finance-manager tool set from the live server (e.g. on role downgrade)."""
    global _registered
    if not _registered:
        return
    try:
        app.remove_tool(_TOOL_NAME)
    except AttributeError:
        # Some SDK versions don't expose remove_tool publicly; fall back to the
        # internal tool manager rather than leaving a stale privileged tool live.
        try:
            del app._tool_manager._tools[_TOOL_NAME]
        except Exception:
            pass
    _registered = False
