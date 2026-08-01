"""
draft_rate_exception_justification -- a canned, parameterized starting point
for the most common finance-adjacent writing task at Swiftrail: a sales_rep
asking for an above-authority discount has to write a justification that's
specific enough to survive finance_manager review (the rate_exceptions table
even enforces a 20-character minimum). Rather than every client/agent
re-inventing this prompt, the server exposes it via prompts/list so any
host can surface it as a canned starting point.
"""

from app_instance import app


@app.prompt()
def draft_rate_exception_justification(shipment_id: str, discount_pct: str, reason_summary: str) -> str:
    """Draft a justification for an above-authority rate exception request, ready to submit
    alongside approve_rate_exception."""
    return (
        f"Write a concise, specific justification (at least 20 characters, no fluff) for "
        f"requesting a {discount_pct}% discount on shipment {shipment_id}. "
        f"Context from the requester: {reason_summary}. "
        f"The justification will be read by a finance_manager deciding whether to approve "
        f"an above-authority discount, so it should name the concrete business reason "
        f"(competitive match, volume commitment, service failure credit, etc.) rather than "
        f"a generic appeal."
    )
