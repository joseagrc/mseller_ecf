from __future__ import annotations

import frappe

from mseller_ecf.mseller_ecf.api.client import MSellerECFClient
from mseller_ecf.mseller_ecf.api.exceptions import MSellerECFError
from mseller_ecf.mseller_ecf.mapper.sales_invoice import build_sales_invoice_payload


def send_sales_invoice(invoice_name: str):
    existing_name = frappe.db.get_value("MSeller ECF Document", {"sales_invoice": invoice_name})
    if existing_name:
        doc = frappe.get_doc("MSeller ECF Document", existing_name)
    else:
        doc = frappe.new_doc("MSeller ECF Document")
        doc.sales_invoice = invoice_name

    if doc.status in {"Sent", "Aceptado", "Aceptado Condicional"} and doc.ecf:
        return doc.name

    settings = frappe.get_single("MSeller ECF Settings")
    payload = build_sales_invoice_payload(invoice_name)

    doc.environment = settings.environment
    doc.ecf = payload["ECF"]["Encabezado"]["IdDoc"]["eNCF"]
    doc.status = "Pending"
    doc.request_payload = frappe.as_json(payload, indent=2)
    doc.save(ignore_permissions=True)
    frappe.db.commit()

    try:
        response = MSellerECFClient(settings).send_document(payload)
    except MSellerECFError as exc:
        doc.status = "Error"
        doc.last_error = str(exc)
        doc.retry_count = (doc.retry_count or 0) + 1
        doc.save(ignore_permissions=True)
        _update_invoice(invoice_name, {"mseller_ecf_status": "Error"})
        frappe.log_error(frappe.get_traceback(), "MSeller ECF send failed")
        raise

    doc.apply_send_response(response)
    doc.save(ignore_permissions=True)
    _update_invoice_from_document(invoice_name, doc)
    frappe.db.commit()

    return doc.name


def _update_invoice_from_document(invoice_name: str, doc):
    _update_invoice(
        invoice_name,
        {
            "mseller_ecf_status": doc.status,
            "mseller_ecf_environment": doc.environment,
            "mseller_ecf_internal_track_id": doc.internal_track_id,
            "mseller_ecf_security_code": doc.security_code,
            "mseller_ecf_signed_date": doc.signed_date,
            "mseller_ecf_qr_url": doc.qr_url,
            "mseller_ecf_last_sync": frappe.utils.now_datetime(),
        },
    )


def _update_invoice(invoice_name: str, values: dict):
    frappe.db.set_value("Sales Invoice", invoice_name, values, update_modified=False)
