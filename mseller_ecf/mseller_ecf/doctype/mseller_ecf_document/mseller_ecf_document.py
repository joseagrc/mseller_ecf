import frappe
from frappe.model.document import Document


class MSellerECFDocument(Document):
    def validate(self):
        if self.sales_invoice and not self.ecf:
            self.ecf = frappe.db.get_value("Sales Invoice", self.sales_invoice, "mseller_ecf_ncf")

    def apply_send_response(self, response: dict):
        self.response_payload = frappe.as_json(response, indent=2)
        self.status = _pick(response, "status", "estado", "dgiiStatus") or "Sent"
        self.internal_track_id = _pick(response, "internalTrackId", "internal_track_id", "trackId")
        self.security_code = _pick(response, "securityCode", "codigoSeguridad", "codigo_seguridad")
        self.qr_url = _pick(response, "qrUrl", "qr_url", "urlQR", "url_qr")
        self.signed_date = _pick(response, "signedDate", "fechaFirma", "fecha_hora_firma")
        self.customer_id = _pick(response, "customerId", "customer_id")
        self.document_type = _pick(response, "documentType", "document_type", "tipoeCF")
        self.signed_xml = _pick(response, "signedXml", "signed_xml", "xmlFirmado")
        self.dgii_response = frappe.as_json(_pick(response, "dgiiResponse", "dgii_response") or {}, indent=2)
        self.last_error = None

    def apply_status_response(self, response: dict):
        self.status_payload = frappe.as_json(response, indent=2)
        self.response_payload = self.response_payload or frappe.as_json(response, indent=2)
        self.status = _pick(response, "status", "estado", "dgiiStatus") or self.status
        self.security_code = _pick(response, "securityCode", "codigoSeguridad", "codigo_seguridad") or self.security_code
        self.qr_url = _pick(response, "qrUrl", "qr_url", "urlQR", "url_qr") or self.qr_url
        self.signed_date = _pick(response, "signedDate", "fechaFirma", "fecha_hora_firma") or self.signed_date
        self.customer_response = frappe.as_json(_pick(response, "customerResponse", "customer_response") or {}, indent=2)
        self.dgii_response = frappe.as_json(_pick(response, "dgiiResponse", "dgii_response") or {}, indent=2)
        self.last_error = _pick(response, "error", "message", "mensaje") if self.status == "Rechazado" else None


def _pick(data: dict, *keys):
    for key in keys:
        if isinstance(data, dict) and data.get(key) not in (None, ""):
            return data.get(key)
    return None
