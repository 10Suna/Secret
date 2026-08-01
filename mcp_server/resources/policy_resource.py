"""
credit_policy -- exposed as a resource, not a tool.

This is a static reference document (Swiftrail's credit-hold and discount
authority policy). The model should read it once per conversation and reason
over it when deciding what to expect from release_credit_hold /
approve_rate_exception -- it isn't an action with side effects and it
doesn't take parameters, so wrapping it as a callable tool would be the
wrong shape. resources/list lets a client discover it exists;
resources/read fetches the content on demand.
"""

from app_instance import app

_POLICY_TEXT = """\
SWIFTRAIL LOGISTICS -- CREDIT HOLD & DISCOUNT AUTHORITY POLICY
(internal reference, v1.2)

1. CREDIT HOLDS
   - MINOR severity: invoice 30-89 days overdue, OR overdue balance under
     25% of the customer's credit limit. Any employee (sales_rep or
     finance_manager) may release a minor hold once the underlying issue
     is resolved.
   - SEVERE severity: invoice 90+ days overdue, AND overdue balance at or
     above 25% of the customer's credit limit. Severe holds require
     explicit finance_manager sign-off to release, confirmed interactively
     at release time -- a standing finance_manager role alone is not
     sufficient without that per-release confirmation.

2. DISCOUNTS / RATE EXCEPTIONS
   - Up to 15% off the base rate: within any sales_rep's standing
     authority, auto-approved.
   - Above 15% (hard ceiling 50%, enforced by schema): requires an
     explicit reviewer decision plus finance_manager authorization before
     the exception can move to 'approved'.

3. AUDIT
   - Every severe hold release and every above-authority discount approval
     must include a written note (reviewer_note / authorization_note)
     describing the reason, regardless of who approves it.
"""


@app.resource("policy://credit-and-discount-authority")
def credit_policy() -> str:
    """Swiftrail's credit-hold severity thresholds and discount authority policy."""
    return _POLICY_TEXT
