from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import getdate, nowdate

from mseller_ecf.mseller_ecf.doctype.mseller_ecf_sequence.mseller_ecf_sequence import format_ecf, parse_ecf


def assign_ecf_if_missing(invoice):
    settings = frappe.get_single("MSeller ECF Settings")
    if not settings.enabled:
        return

    if not invoice.get("mseller_ecf_type"):
        if settings.require_ecf_fields_on_submit:
            frappe.throw(_("e-CF Type is required before submitting this Sales Invoice."))
        return

    if invoice.get("mseller_ecf_ncf"):
        sync_existing_ecf(invoice, settings.environment)
        return

    sequence_name = get_active_sequence_name(invoice.company, settings.environment, invoice.mseller_ecf_type)
    if not sequence_name:
        if settings.require_ecf_fields_on_submit:
            frappe.throw(
                _("No active e-NCF sequence found for Company {0}, Environment {1}, e-CF Type {2}.").format(
                    invoice.company, settings.environment, invoice.mseller_ecf_type
                )
            )
        return

    ecf, expires_on = consume_sequence(sequence_name, invoice.name)
    invoice.mseller_ecf_ncf = ecf
    invoice.mseller_ecf_sequence = sequence_name
    invoice.mseller_ecf_environment = settings.environment
    if expires_on and not invoice.get("mseller_ecf_sequence_expiry_date"):
        invoice.mseller_ecf_sequence_expiry_date = expires_on


def get_active_sequence_name(company: str, environment: str, ecf_type: str) -> str | None:
    return frappe.db.get_value(
        "MSeller ECF Sequence",
        {
            "company": company,
            "environment": environment,
            "ecf_type": ecf_type,
            "status": "Active",
            "auto_assign": 1,
        },
        "name",
        order_by="expires_on asc, creation asc",
    )


def consume_sequence(sequence_name: str, invoice_name: str) -> tuple[str, str | None]:
    row = frappe.db.sql(
        """
        select
            name, prefix, padding_length, start_number, end_number, next_number, expires_on, status
        from `tabMSeller ECF Sequence`
        where name = %s
        for update
        """,
        sequence_name,
        as_dict=True,
    )
    if not row:
        frappe.throw(_("e-NCF sequence {0} was not found.").format(sequence_name))

    sequence = row[0]
    if sequence.status != "Active":
        frappe.throw(_("e-NCF sequence {0} is not active.").format(sequence_name))

    if sequence.expires_on and getdate(sequence.expires_on) < getdate(nowdate()):
        frappe.db.set_value("MSeller ECF Sequence", sequence_name, "status", "Expired", update_modified=False)
        frappe.throw(_("e-NCF sequence {0} is expired.").format(sequence_name))

    next_number = sequence.next_number or sequence.start_number
    if next_number > sequence.end_number:
        frappe.db.set_value("MSeller ECF Sequence", sequence_name, "status", "Exhausted", update_modified=False)
        frappe.throw(_("e-NCF sequence {0} is exhausted.").format(sequence_name))

    ecf = format_ecf(sequence.prefix, next_number, sequence.padding_length)
    new_next_number = next_number + 1
    status = "Exhausted" if new_next_number > sequence.end_number else "Active"
    used_quantity = max(0, new_next_number - sequence.start_number)
    remaining_quantity = max(0, sequence.end_number - new_next_number + 1)

    frappe.db.set_value(
        "MSeller ECF Sequence",
        sequence_name,
        {
            "next_number": new_next_number,
            "status": status,
            "used_quantity": used_quantity,
            "remaining_quantity": remaining_quantity,
            "last_assigned_ecf": ecf,
            "last_sales_invoice": invoice_name,
        },
        update_modified=False,
    )

    return ecf, sequence.expires_on


def sync_existing_ecf(invoice, environment: str):
    prefix, number, _padding_length = parse_ecf(invoice.mseller_ecf_ncf)
    expected_prefix = f"E{invoice.mseller_ecf_type}"
    if prefix != expected_prefix:
        frappe.throw(_("e-NCF {0} does not match e-CF Type {1}.").format(invoice.mseller_ecf_ncf, invoice.mseller_ecf_type))

    rows = frappe.db.sql(
        """
        select
            name, prefix, padding_length, start_number, end_number, next_number, expires_on, status
        from `tabMSeller ECF Sequence`
        where
            company = %s
            and environment = %s
            and ecf_type = %s
            and status = 'Active'
            and auto_assign = 1
            and start_number <= %s
            and end_number >= %s
        order by expires_on asc, creation asc
        limit 1
        for update
        """,
        (invoice.company, environment, invoice.mseller_ecf_type, number, number),
        as_dict=True,
    )
    if not rows:
        frappe.throw(
            _("No active e-NCF sequence covers {0} for Company {1}, Environment {2}, e-CF Type {3}.").format(
                invoice.mseller_ecf_ncf, invoice.company, environment, invoice.mseller_ecf_type
            )
        )

    sequence = rows[0]
    if sequence.expires_on and getdate(sequence.expires_on) < getdate(nowdate()):
        frappe.db.set_value("MSeller ECF Sequence", sequence.name, "status", "Expired", update_modified=False)
        frappe.throw(_("e-NCF sequence {0} is expired.").format(sequence.name))

    next_number = sequence.next_number or sequence.start_number
    if number > next_number:
        next_ecf = format_ecf(sequence.prefix, next_number, sequence.padding_length)
        frappe.throw(
            _("e-NCF {0} cannot be used yet. The next e-NCF for sequence {1} is {2}.").format(
                invoice.mseller_ecf_ncf, sequence.name, next_ecf
            )
        )

    invoice.mseller_ecf_sequence = sequence.name
    invoice.mseller_ecf_environment = environment
    if sequence.expires_on and not invoice.get("mseller_ecf_sequence_expiry_date"):
        invoice.mseller_ecf_sequence_expiry_date = sequence.expires_on

    if number < next_number:
        return

    new_next_number = number + 1
    status = "Exhausted" if new_next_number > sequence.end_number else "Active"
    used_quantity = max(0, new_next_number - sequence.start_number)
    remaining_quantity = max(0, sequence.end_number - new_next_number + 1)

    frappe.db.set_value(
        "MSeller ECF Sequence",
        sequence.name,
        {
            "next_number": new_next_number,
            "status": status,
            "used_quantity": used_quantity,
            "remaining_quantity": remaining_quantity,
            "last_assigned_ecf": invoice.mseller_ecf_ncf,
            "last_sales_invoice": invoice.name,
        },
        update_modified=False,
    )
