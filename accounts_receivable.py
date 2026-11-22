"""List validated invoices with an outstanding balance."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal, InvalidOperation

from api_client import DolibarrClient


def first_value(record: dict, *names, default=None):
    for name in names:
        if name in record and record[name] is not None:
            return record[name]
    return default


def money(value) -> Decimal:
    try:
        return Decimal(str(value or "0"))
    except InvalidOperation:
        return Decimal("0")


def format_date(value) -> str:
    if value in (None, "", 0, "0"):
        return "-"
    try:
        number = int(value)
        if number > 10_000_000:
            return datetime.fromtimestamp(number).strftime("%Y-%m-%d")
    except (ValueError, TypeError, OSError):
        pass
    return str(value)


def get_all_unpaid_invoices(api: DolibarrClient) -> list[dict]:
    """Dolibarr status 1 = validated; paid invoices have status 2.

    The SQL filter retrieves validated invoices; remaining balance is checked
    locally so partially paid invoices are included as well.
    """
    invoices = []
    page = 0
    while True:
        batch = api.get("invoices", {
            "limit": 100,
            "page": page,
            "sortfield": "t.rowid",
            "sortorder": "ASC",
            "sqlfilters": "(t.fk_statut:=:1)",
        })
        if not isinstance(batch, list) or not batch:
            break
        invoices.extend(batch)
        if len(batch) < 100:
            break
        page += 1
    return invoices


def main():
    api = DolibarrClient()
    invoices = get_all_unpaid_invoices(api)

    # Cache customer records: several invoices can belong to the same customer.
    customer_names: dict[int, str] = {}
    rows = []
    for invoice in invoices:
        invoice_id = first_value(invoice, "id", "rowid")
        customer_id = first_value(invoice, "socid", "fk_soc")
        if customer_id is None:
            continue

        due = first_value(invoice, "remaintopay", "remain_to_pay", "resteapayer")
        if due is None:
            # Fallback for API versions exposing totals but not the remaining
            # balance in the list response. A detailed invoice response may
            # expose remaintopay; avoid treating the full total as unpaid.
            if invoice_id is not None:
                details = api.get(f"invoices/{invoice_id}")
                due = first_value(details, "remaintopay", "remain_to_pay", "resteapayer")
            if due is None:
                print(f"Warning: cannot determine balance for invoice {invoice_id}; skipped.")
                continue

        amount_due = money(due)
        if amount_due <= 0:
            continue

        customer_id_int = int(customer_id)
        if customer_id_int not in customer_names:
            customer = api.get(f"thirdparties/{customer_id_int}")
            customer_names[customer_id_int] = str(
                first_value(customer, "name", "nom", default=f"Customer {customer_id_int}")
            )

        rows.append({
            "customer": customer_names[customer_id_int],
            "reference": str(first_value(invoice, "ref", "reference", default=invoice_id or "-")),
            "amount": amount_due,
            "due_date": format_date(first_value(invoice, "date_lim_reglement", "date_due")),
        })

    print("\nACCOUNTS RECEIVABLE — UNPAID INVOICES")
    print("-" * 88)
    print(f"{'Customer':30} {'Invoice':18} {'Amount due':18} {'Due date':12}")
    print("-" * 88)
    total = Decimal("0")
    for row in rows:
        total += row["amount"]
        print(f"{row['customer'][:30]:30} {row['reference'][:18]:18} "
              f"{row['amount']:>18.2f} {row['due_date']:12}")
    print("-" * 88)
    print(f"{'TOTAL OUTSTANDING':49} {total:>18.2f}")
    print(f"\nInvoices with an outstanding balance: {len(rows)}")


if __name__ == "__main__":
    main()
