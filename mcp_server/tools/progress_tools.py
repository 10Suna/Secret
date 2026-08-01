"""
run_portfolio_risk_sweep -- the one tool in this server whose work is
genuinely multi-step and slow enough that a client blocked on a single
response would look hung: it walks every customer, pulls their shipments,
invoices, and holds, and computes a per-customer risk score. On a real
production customer table (thousands of rows, each requiring a couple of
queries) this is seconds-to-minutes of work, not milliseconds. We simulate
the per-row latency here so the demo is fast but the progress-reporting
mechanism is real, not decorative.
"""

import asyncio
import json

from app_instance import app
from db import get_connection
from mcp.server.fastmcp import Context


@app.tool()
async def run_portfolio_risk_sweep(ctx: Context = None) -> str:
    """Scan every customer in the portfolio and compute a risk score from their overdue
    invoice total and active credit holds. Long-running (one DB round trip per customer);
    reports progress after each customer processed instead of blocking silently."""

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, credit_limit, balance_due FROM customers")
    customers = cursor.fetchall()

    results = []
    total = len(customers)

    for i, customer in enumerate(customers, start=1):
        cursor.execute(
            "SELECT COALESCE(SUM(amount), 0) AS overdue_total FROM invoices "
            "WHERE customer_id = %s AND paid_status = 'overdue'",
            (customer["id"],),
        )
        overdue_total = float(cursor.fetchone()["overdue_total"])

        cursor.execute(
            "SELECT COUNT(*) AS n FROM credit_holds WHERE customer_id = %s AND status = 'active'",
            (customer["id"],),
        )
        active_holds = cursor.fetchone()["n"]

        exposure_ratio = overdue_total / float(customer["credit_limit"]) if customer["credit_limit"] else 0
        risk_score = round(min(100, exposure_ratio * 100 + active_holds * 15), 1)

        results.append(
            {
                "customer_id": customer["id"],
                "name": customer["name"],
                "overdue_total": overdue_total,
                "active_holds": active_holds,
                "risk_score": risk_score,
            }
        )

        if ctx is not None:
            await ctx.report_progress(
                progress=i,
                total=total,
                message=f"Scored {customer['name']} ({i}/{total})",
            )

        # Simulated per-row latency so the progress stream is observable in a
        # live demo; a real deployment would omit this and rely on genuine
        # query latency at scale.
        await asyncio.sleep(0.3)

    cursor.close()
    conn.close()

    results.sort(key=lambda r: r["risk_score"], reverse=True)

    narrative_summary = await _summarize_top_risk(ctx, results[:3])

    return json.dumps(
        {"scanned": total, "ranked_by_risk": results, "narrative_summary": narrative_summary},
        default=str,
    )


async def _summarize_top_risk(ctx: Context, top_customers: list) -> str:
    """SAMPLING: ask the *connected client's* model to turn the top-3 risk rows into a
    short prose summary a finance manager could paste into an email, instead of the
    server hand-rolling a summary with string formatting or running its own model call.

    This is a genuine reasoning need -- deciding how to phrase a risk summary for a
    human reader isn't something a fixed template does well -- and it goes through
    sampling/createMessage, so it uses whichever model the connected agent brought
    (its client, its API key, its choice of model), not a call the server makes on
    its own account.
    """
    if ctx is None or not top_customers:
        return "(sampling unavailable: no active context)"

    prompt = (
        "You are drafting a one-paragraph risk summary for a finance manager. "
        "Given this ranked list of the highest-risk customers (JSON), write 2-3 "
        "plain-English sentences flagging who needs attention and why:\n\n"
        f"{json.dumps(top_customers, default=str)}"
    )

    try:
        result = await ctx.sample(prompt, max_tokens=200)
        # FastMCP's ctx.sample returns a TextContent-like object with `.text`
        # on most SDK versions; fall back to str() if that's not present.
        return getattr(result, "text", str(result))
    except AttributeError:
        return "(sampling unavailable: connected client did not declare the sampling capability)"
