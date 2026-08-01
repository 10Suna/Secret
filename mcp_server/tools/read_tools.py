import json

from app_instance import app
from db import get_connection


@app.tool()
def search_customer(customer_id: int) -> str:
    """Get a customer's profile including credit status and balance. Read-only, no authorization required."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM customers WHERE id = %s", (customer_id,))
    row = cursor.fetchone()
    cursor.close()
    conn.close()

    if not row:
        return f"No customer found with id {customer_id}"
    return json.dumps(row, default=str)


@app.tool()
def get_shipment_status(shipment_id: int) -> str:
    """Get the current status and details of a shipment. Read-only, no authorization required."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM shipments WHERE id = %s", (shipment_id,))
    row = cursor.fetchone()
    cursor.close()
    conn.close()

    if not row:
        return f"No shipment found with id {shipment_id}"
    return json.dumps(row, default=str)


@app.tool()
def list_customer_invoices(customer_id: int) -> str:
    """List all invoices for a customer, including paid, unpaid, and overdue amounts. Read-only, no authorization required."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM invoices WHERE customer_id = %s", (customer_id,))
    rows = cursor.fetchall()
    cursor.close()
    conn.close()

    if not rows:
        return f"No invoices found for customer {customer_id}"
    return json.dumps(rows, default=str)
