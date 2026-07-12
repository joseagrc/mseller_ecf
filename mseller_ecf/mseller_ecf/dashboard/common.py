from __future__ import annotations

from frappe import _


def add_mseller_ecf_connection(data: dict) -> dict:
    transactions = data.setdefault("transactions", [])
    item = "MSeller ECF Document"

    for group in transactions:
        if item in group.get("items", []):
            return data

    transactions.append({"label": _("MSeller ECF"), "items": [item]})
    return data
