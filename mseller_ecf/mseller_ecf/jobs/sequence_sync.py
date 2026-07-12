from __future__ import annotations

import frappe
from frappe import _

from mseller_ecf.mseller_ecf.doctype.mseller_ecf_sequence.mseller_ecf_sequence import get_sequence_status


@frappe.whitelist()
def refresh_sequence_status(sequence_name: str):
    if not frappe.has_permission("MSeller ECF Sequence", "write", doc=sequence_name):
        frappe.throw(_("Not permitted"), frappe.PermissionError)

    updated = _refresh_one(sequence_name)
    frappe.db.commit()
    return updated


def refresh_all_sequence_statuses(limit: int = 500):
    rows = frappe.get_all(
        "MSeller ECF Sequence",
        filters={"status": ["not in", ["Cancelled"]]},
        fields=["name"],
        order_by="modified asc",
        limit_page_length=int(limit or 500),
    )

    updated = 0
    for row in rows:
        updated += int(_refresh_one(row.name).get("updated"))

    if updated:
        frappe.db.commit()

    return updated


def _refresh_one(sequence_name: str) -> dict:
    sequence = frappe.db.get_value(
        "MSeller ECF Sequence",
        sequence_name,
        [
            "status",
            "start_number",
            "end_number",
            "next_number",
            "authorized_quantity",
            "used_quantity",
            "remaining_quantity",
            "expires_on",
        ],
        as_dict=True,
    )
    if not sequence:
        frappe.throw(_("e-NCF sequence {0} was not found.").format(sequence_name))

    next_number = sequence.next_number or sequence.start_number
    authorized_quantity = sequence.authorized_quantity or max(0, sequence.end_number - sequence.start_number + 1)
    used_quantity = max(0, min(next_number - sequence.start_number, authorized_quantity))
    remaining_quantity = max(0, sequence.end_number - next_number + 1)
    status = get_sequence_status(sequence.status, next_number, sequence.end_number, sequence.expires_on)

    values = {
        "used_quantity": used_quantity,
        "remaining_quantity": remaining_quantity,
        "status": status,
    }
    changed = (
        sequence.status != status
        or sequence.get("used_quantity") != used_quantity
        or sequence.get("remaining_quantity") != remaining_quantity
    )

    if changed:
        frappe.db.set_value("MSeller ECF Sequence", sequence_name, values, update_modified=False)

    return {"name": sequence_name, "status": status, "updated": changed}
