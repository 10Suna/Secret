"""
Single in-memory session object shared by every tool module.

This replaces the old hardcoded `session_role = "sales_rep"` /
`session_employee_id = 1` globals in rate_exception.py. Those were fixed for
the lifetime of the process, so there was no way to represent "a finance
manager just logged in" without restarting the server.

`Session` is intentionally a simple mutable object (not a DB row cache) so
that `tools/auth_tools.py` can flip `role` at runtime and every other tool
module that imports SESSION immediately sees the new value on the next call.
That runtime flip is also what triggers the tools/list_changed notification
(see notifications.py) -- the tool set that is *safe to expose* depends on
this object's current role.

In a real deployment this would be per-connection state (keyed off the
authenticated transport session), not a single process-wide object. We keep
it process-wide here because the lab's stdio/HTTP demo only ever has one
active caller at a time; a multi-user deployment is called out as a known
limitation in the README.
"""

from dataclasses import dataclass


@dataclass
class Session:
    employee_id: int = 1
    employee_name: str = "Youssef Adel"
    role: str = "sales_rep"  # "sales_rep" | "finance_manager"


SESSION = Session()
