import frappe

from mseller_ecf.mseller_ecf.mapper.sales_invoice import build_sales_invoice_payload


@frappe.whitelist()
def preview_sales_invoice_payload(invoice_name: str):
    if not frappe.has_permission("Sales Invoice", "read", doc=invoice_name):
        frappe.throw("Not permitted", frappe.PermissionError)
    return build_sales_invoice_payload(invoice_name)


@frappe.whitelist()
def enqueue_sales_invoice(invoice_name: str):
    if not frappe.has_permission("Sales Invoice", "write", doc=invoice_name):
        frappe.throw("Not permitted", frappe.PermissionError)

    frappe.enqueue(
        "mseller_ecf.mseller_ecf.jobs.send_document.send_sales_invoice",
        queue="short",
        timeout=300,
        enqueue_after_commit=True,
        invoice_name=invoice_name,
    )
    return {"queued": True}
