import frappe
from frappe import _

from mseller_ecf.mseller_ecf.mapper.sales_invoice import build_sales_invoice_payload
from mseller_ecf.mseller_ecf.mapper.purchase_invoice import build_purchase_invoice_payload
from mseller_ecf.mseller_ecf.jobs.status_sync import sync_document


@frappe.whitelist()
def preview_sales_invoice_payload(invoice_name: str):
    if not frappe.has_permission("Sales Invoice", "read", doc=invoice_name):
        frappe.throw(_("Not permitted"), frappe.PermissionError)
    return build_sales_invoice_payload(invoice_name)


@frappe.whitelist()
def enqueue_sales_invoice(invoice_name: str):
    if not frappe.has_permission("Sales Invoice", "write", doc=invoice_name):
        frappe.throw(_("Not permitted"), frappe.PermissionError)

    frappe.enqueue(
        "mseller_ecf.mseller_ecf.jobs.send_document.send_sales_invoice",
        queue="short",
        timeout=300,
        enqueue_after_commit=True,
        invoice_name=invoice_name,
    )
    frappe.db.set_value(
        "Sales Invoice",
        invoice_name,
        {
            "mseller_ecf_status": "Queued",
            "mseller_ecf_last_error": "",
            "mseller_ecf_last_sync": frappe.utils.now_datetime(),
        },
        update_modified=False,
    )
    return {"queued": True}


@frappe.whitelist()
def sync_sales_invoice_status(invoice_name: str):
    if not frappe.has_permission("Sales Invoice", "read", doc=invoice_name):
        frappe.throw(_("Not permitted"), frappe.PermissionError)

    document_name = frappe.db.get_value("MSeller ECF Document", {"sales_invoice": invoice_name})
    if not document_name:
        frappe.throw(_("No MSeller ECF Document found for this Sales Invoice."))

    return sync_document(document_name)


@frappe.whitelist()
def preview_purchase_invoice_payload(invoice_name: str):
    if not frappe.has_permission("Purchase Invoice", "read", doc=invoice_name):
        frappe.throw(_("Not permitted"), frappe.PermissionError)
    return build_purchase_invoice_payload(invoice_name)


@frappe.whitelist()
def enqueue_purchase_invoice(invoice_name: str):
    if not frappe.has_permission("Purchase Invoice", "write", doc=invoice_name):
        frappe.throw(_("Not permitted"), frappe.PermissionError)

    frappe.enqueue(
        "mseller_ecf.mseller_ecf.jobs.send_document.send_purchase_invoice",
        queue="short",
        timeout=300,
        enqueue_after_commit=True,
        invoice_name=invoice_name,
    )
    frappe.db.set_value(
        "Purchase Invoice",
        invoice_name,
        {
            "mseller_ecf_status": "Queued",
            "mseller_ecf_last_error": "",
        },
        update_modified=False,
    )
    return {"queued": True}


@frappe.whitelist()
def sync_purchase_invoice_status(invoice_name: str):
    if not frappe.has_permission("Purchase Invoice", "read", doc=invoice_name):
        frappe.throw(_("Not permitted"), frappe.PermissionError)

    document_name = frappe.db.get_value("MSeller ECF Document", {"purchase_invoice": invoice_name})
    if not document_name:
        frappe.throw(_("No MSeller ECF Document found for this Purchase Invoice."))

    return sync_document(document_name)
