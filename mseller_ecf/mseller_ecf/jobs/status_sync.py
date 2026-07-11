from __future__ import annotations

import frappe

from mseller_ecf.mseller_ecf.api.client import MSellerECFClient
from mseller_ecf.mseller_ecf.api.exceptions import MSellerECFError

TERMINAL_STATUSES = {"Aceptado", "Aceptado Condicional", "Rechazado"}


def sync_pending_documents(limit: int = 100):
    settings = frappe.get_single("MSeller ECF Settings")
    if not settings.enabled:
        return

    rows = frappe.get_all(
        "MSeller ECF Document",
        filters={
            "environment": settings.environment,
            "status": ["not in", list(TERMINAL_STATUSES) + ["Cancelled"]],
            "ecf": ["is", "set"],
        },
        fields=["name", "ecf"],
        order_by="modified asc",
        limit_page_length=min(int(limit or 100), 100),
    )
    if not rows:
        return

    client = MSellerECFClient(settings)
    ecfs = [row.ecf for row in rows]

    try:
        response = client.get_documents_batch(ecfs)
    except MSellerECFError:
        frappe.log_error(frappe.get_traceback(), "MSeller ECF batch status sync failed")
        return

    results = response.get("results") or []
    by_ecf = {item.get("ecf"): item for item in results if item.get("found")}

    for row in rows:
        result = by_ecf.get(row.ecf)
        if not result:
            continue
        doc = frappe.get_doc("MSeller ECF Document", row.name)
        doc.apply_status_response(result.get("data") or result)
        doc.save(ignore_permissions=True)
        if doc.sales_invoice:
            _update_invoice_from_document(doc)

    frappe.db.commit()


@frappe.whitelist()
def sync_document(document_name: str):
    if not frappe.has_permission("MSeller ECF Document", "write", doc=document_name):
        frappe.throw("Not permitted", frappe.PermissionError)

    doc = frappe.get_doc("MSeller ECF Document", document_name)
    response = MSellerECFClient().get_document(doc.ecf)
    doc.apply_status_response(response)
    doc.save(ignore_permissions=True)
    if doc.sales_invoice:
        _update_invoice_from_document(doc)
    frappe.db.commit()
    return response


def cleanup_expired_tokens():
    settings = frappe.get_single("MSeller ECF Settings")
    settings.db_set("id_token", "", update_modified=False)
    settings.db_set("access_token", "", update_modified=False)


def _update_invoice_from_document(doc):
    frappe.db.set_value(
        "Sales Invoice",
        doc.sales_invoice,
        {
            "mseller_ecf_status": doc.status,
            "mseller_ecf_internal_track_id": doc.internal_track_id,
            "mseller_ecf_security_code": doc.security_code,
            "mseller_ecf_signed_date": doc.signed_date,
            "mseller_ecf_qr_url": doc.qr_url,
            "mseller_ecf_last_sync": frappe.utils.now_datetime(),
            "mseller_ecf_last_error": doc.last_error,
        },
        update_modified=False,
    )
