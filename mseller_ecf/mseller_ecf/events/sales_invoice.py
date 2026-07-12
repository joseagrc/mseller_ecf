import frappe
from frappe import _

from mseller_ecf.mseller_ecf.sequence import assign_ecf_if_missing


def before_submit(doc, method=None):
    assign_ecf_if_missing(doc)


def on_submit(doc, method=None):
    settings = frappe.get_single("MSeller ECF Settings")
    if not settings.enabled or not settings.auto_send_on_submit:
        return

    if not doc.get("mseller_ecf_type") or not doc.get("mseller_ecf_ncf"):
        if settings.require_ecf_fields_on_submit:
            frappe.throw(_("e-CF Type and e-NCF are required before submitting this Sales Invoice."))
        return

    frappe.db.set_value(
        "Sales Invoice",
        doc.name,
        {
            "mseller_ecf_status": "Queued",
            "mseller_ecf_environment": settings.environment,
        },
        update_modified=False,
    )

    frappe.enqueue(
        "mseller_ecf.mseller_ecf.jobs.send_document.send_sales_invoice",
        queue="short",
        timeout=300,
        enqueue_after_commit=True,
        job_name=f"mseller_ecf:Sales Invoice:{doc.name}",
        job_id=f"mseller_ecf:Sales Invoice:{doc.name}",
        deduplicate=True,
        invoice_name=doc.name,
    )


def on_cancel(doc, method=None):
    if doc.get("mseller_ecf_status") in {"Aceptado", "Aceptado Condicional"}:
        frappe.throw(
            _(
                "This invoice has an accepted e-CF. Create the corresponding electronic credit note instead of cancelling it."
            )
        )

    if doc.get("mseller_ecf_status"):
        frappe.db.set_value(
            "Sales Invoice",
            doc.name,
            "mseller_ecf_status",
            "Cancelled",
            update_modified=False,
        )
