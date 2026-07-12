import frappe
from frappe import _

from mseller_ecf.mseller_ecf.mapper.sales_invoice import build_sales_invoice_payload
from mseller_ecf.mseller_ecf.mapper.purchase_invoice import build_purchase_invoice_payload
from mseller_ecf.mseller_ecf.jobs.status_sync import sync_document

IN_FLIGHT_STATUSES = {"Queued", "Pending"}
COMPLETED_STATUSES = {"Sent", "Aceptado", "Aceptado Condicional"}


@frappe.whitelist()
def preview_sales_invoice_payload(invoice_name: str):
    if not frappe.has_permission("Sales Invoice", "read", doc=invoice_name):
        frappe.throw(_("Not permitted"), frappe.PermissionError)
    return build_sales_invoice_payload(invoice_name)


@frappe.whitelist()
def enqueue_sales_invoice(invoice_name: str):
    if not frappe.has_permission("Sales Invoice", "write", doc=invoice_name):
        frappe.throw(_("Not permitted"), frappe.PermissionError)

    return _enqueue_invoice(
        "Sales Invoice",
        invoice_name,
        "sales_invoice",
        "mseller_ecf.mseller_ecf.jobs.send_document.send_sales_invoice",
    )


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

    return _enqueue_invoice(
        "Purchase Invoice",
        invoice_name,
        "purchase_invoice",
        "mseller_ecf.mseller_ecf.jobs.send_document.send_purchase_invoice",
    )


@frappe.whitelist()
def sync_purchase_invoice_status(invoice_name: str):
    if not frappe.has_permission("Purchase Invoice", "read", doc=invoice_name):
        frappe.throw(_("Not permitted"), frappe.PermissionError)

    document_name = frappe.db.get_value("MSeller ECF Document", {"purchase_invoice": invoice_name})
    if not document_name:
        frappe.throw(_("No MSeller ECF Document found for this Purchase Invoice."))

    return sync_document(document_name)


def _enqueue_invoice(doctype: str, invoice_name: str, link_field: str, method: str):
    invoice_status = frappe.db.get_value(doctype, invoice_name, "mseller_ecf_status")
    if invoice_status in IN_FLIGHT_STATUSES | COMPLETED_STATUSES:
        return {"queued": False, "status": invoice_status}

    document_status = frappe.db.get_value("MSeller ECF Document", {link_field: invoice_name}, "status")
    if document_status in IN_FLIGHT_STATUSES | COMPLETED_STATUSES:
        return {"queued": False, "status": document_status}

    frappe.enqueue(
        method,
        queue="short",
        timeout=300,
        enqueue_after_commit=True,
        job_name=f"mseller_ecf:{doctype}:{invoice_name}",
        job_id=f"mseller_ecf:{doctype}:{invoice_name}",
        deduplicate=True,
        invoice_name=invoice_name,
    )
    frappe.db.set_value(
        doctype,
        invoice_name,
        {
            "mseller_ecf_status": "Queued",
            "mseller_ecf_last_error": "",
            "mseller_ecf_last_sync": frappe.utils.now_datetime(),
        },
        update_modified=False,
    )
    return {"queued": True, "status": "Queued"}
