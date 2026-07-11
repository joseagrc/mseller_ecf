from __future__ import annotations

import frappe
from frappe import _

from mseller_ecf.mseller_ecf.utils import clean_tax_id, date_dmy, money, require_value

ITBIS_RATE_TO_FIELD = {
    18: ("MontoGravadoI1", "ITBIS1", "TotalITBIS1"),
    16: ("MontoGravadoI2", "ITBIS2", "TotalITBIS2"),
    0: ("MontoGravadoI3", "ITBIS3", "TotalITBIS3"),
}


def build_sales_invoice_payload(invoice_name: str) -> dict:
    invoice = frappe.get_doc("Sales Invoice", invoice_name)
    settings = frappe.get_single("MSeller ECF Settings")
    return SalesInvoiceECFMapper(invoice, settings).build()


class SalesInvoiceECFMapper:
    def __init__(self, invoice, settings):
        self.invoice = invoice
        self.settings = settings

    def build(self) -> dict:
        self.validate()

        payload = {
            "ECF": {
                "Encabezado": {
                    "Version": "1.0",
                    "IdDoc": self.id_doc(),
                    "Emisor": self.emisor(),
                    "Comprador": self.comprador(),
                    "Totales": self.totales(),
                },
                "DetallesItems": {
                    "Item": self.items(),
                },
                "FechaHoraFirma": "",
            }
        }

        if self.invoice.get("mseller_ecf_include_pagination") or self.settings.include_pagination:
            payload["ECF"]["Paginacion"] = self.pagination(payload)

        return payload

    def validate(self):
        if self.invoice.docstatus != 1:
            frappe.throw(_("Only submitted Sales Invoices can be sent to MSeller ECF."))

        require_value(self.invoice.get("mseller_ecf_type"), _("e-CF Type"))
        require_value(self.invoice.get("mseller_ecf_ncf"), _("e-NCF"))
        require_value(self.settings.rnc_emisor or self.company_tax_id(), _("Company RNC"))
        require_value(self.invoice.customer_name, _("Customer Name"))

        if not self.invoice.items:
            frappe.throw(_("Sales Invoice must have at least one item for MSeller ECF."))

    def id_doc(self) -> dict:
        data = {
            "TipoeCF": self.invoice.mseller_ecf_type,
            "eNCF": self.invoice.mseller_ecf_ncf,
            "IndicadorMontoGravado": self.invoice.get("mseller_ecf_taxable_amount_indicator")
            or self.settings.default_taxable_amount_indicator
            or "0",
            "TipoIngresos": self.invoice.get("mseller_ecf_income_type") or self.settings.default_income_type,
            "TipoPago": self.invoice.get("mseller_ecf_payment_type") or self.default_payment_type(),
            "TotalPaginas": 1,
        }

        sequence_expiry = self.invoice.get("mseller_ecf_sequence_expiry_date") or self.settings.sequence_expiry_date
        if sequence_expiry:
            data["FechaVencimientoSecuencia"] = date_dmy(sequence_expiry)

        due_date = self.invoice.get("due_date")
        if due_date and data["TipoPago"] != "1":
            data["FechaLimitePago"] = date_dmy(due_date)

        if self.invoice.get("mseller_ecf_deferred_submission_indicator"):
            data["IndicadorEnvioDiferido"] = self.invoice.mseller_ecf_deferred_submission_indicator
        elif self.settings.default_deferred_submission_indicator:
            data["IndicadorEnvioDiferido"] = self.settings.default_deferred_submission_indicator

        return {key: value for key, value in data.items() if value not in (None, "")}

    def emisor(self) -> dict:
        return {
            "RNCEmisor": clean_tax_id(self.settings.rnc_emisor or self.company_tax_id()),
            "RazonSocialEmisor": self.settings.issuer_legal_name or self.invoice.company,
            "DireccionEmisor": self.settings.issuer_address or self.company_address(),
            "FechaEmision": date_dmy(self.invoice.posting_date),
        }

    def comprador(self) -> dict:
        tax_id = self.customer_tax_id()
        buyer = {
            "RazonSocialComprador": self.invoice.customer_name,
        }
        if tax_id:
            buyer["RNCComprador"] = clean_tax_id(tax_id)
        return buyer

    def items(self) -> list[dict]:
        rows = []
        for idx, item in enumerate(self.invoice.items, start=1):
            row = {
                "NumeroLinea": str(idx),
                "IndicadorFacturacion": self.item_billing_indicator(item),
                "NombreItem": item.item_name or item.item_code,
                "IndicadorBienoServicio": self.goods_or_service_indicator(item),
                "CantidadItem": money(item.qty),
                "UnidadMedida": item.get("uom") and self.unit_code(item.uom),
                "PrecioUnitarioItem": money(item.rate),
                "MontoItem": money(item.net_amount),
            }

            if item.discount_amount:
                row["DescuentoMonto"] = money(item.discount_amount * item.qty)

            rows.append({key: value for key, value in row.items() if value not in (None, "")})
        return rows

    def totales(self) -> dict:
        totals = {
            "MontoGravadoTotal": money(self.invoice.net_total),
            "MontoExento": money(self.exempt_total()),
            "TotalITBIS": money(self.invoice.total_taxes_and_charges),
            "MontoTotal": money(self.invoice.grand_total),
            "MontoNoFacturable": money(self.invoice.get("total_advance") or 0),
        }

        tax_rate = self.primary_itbis_rate()
        amount_field, rate_field, tax_field = ITBIS_RATE_TO_FIELD.get(tax_rate, ITBIS_RATE_TO_FIELD[18])
        taxable_total = money(self.invoice.net_total - self.exempt_total())
        totals[amount_field] = taxable_total
        totals[rate_field] = tax_rate
        totals[tax_field] = money(self.invoice.total_taxes_and_charges)

        return {key: value for key, value in totals.items() if value not in (None, "")}

    def pagination(self, payload: dict) -> dict:
        totals = payload["ECF"]["Encabezado"]["Totales"]
        return {
            "Pagina": [
                {
                    "PaginaNo": 1,
                    "NoLineaDesde": 1,
                    "NoLineaHasta": len(self.invoice.items),
                    "SubtotalMontoGravadoPagina": totals.get("MontoGravadoTotal", 0),
                    "SubtotalMontoGravado1Pagina": totals.get("MontoGravadoI1", 0),
                    "SubtotalExentoPagina": totals.get("MontoExento", 0),
                    "SubtotalItbisPagina": totals.get("TotalITBIS", 0),
                    "SubtotalItbis1Pagina": totals.get("TotalITBIS1", 0),
                    "MontoSubtotalPagina": totals.get("MontoTotal", 0),
                    "SubtotalMontoNoFacturablePagina": totals.get("MontoNoFacturable", 0),
                }
            ]
        }

    def default_payment_type(self) -> str:
        if self.invoice.outstanding_amount and self.invoice.outstanding_amount > 0:
            return self.settings.default_credit_payment_type or "2"
        return self.settings.default_cash_payment_type or "1"

    def company_tax_id(self) -> str:
        company = frappe.get_cached_doc("Company", self.invoice.company)
        return company.get("tax_id")

    def company_address(self) -> str:
        if self.settings.issuer_address:
            return self.settings.issuer_address

        address_name = self.invoice.get("company_address")
        if address_name:
            address = frappe.get_cached_doc("Address", address_name)
            return address.get_display()

        return self.invoice.company

    def customer_tax_id(self) -> str | None:
        if self.invoice.get("tax_id"):
            return self.invoice.tax_id
        customer = frappe.get_cached_doc("Customer", self.invoice.customer)
        return customer.get("tax_id")

    def unit_code(self, uom: str) -> str:
        mapping = self.settings.get("uom_mappings") or []
        for row in mapping:
            if row.uom == uom and row.dgii_unit_code:
                return row.dgii_unit_code
        return self.settings.default_unit_code or "43"

    def goods_or_service_indicator(self, item) -> str:
        if item.get("mseller_ecf_goods_service_indicator"):
            return item.mseller_ecf_goods_service_indicator

        if self.settings.default_goods_service_indicator:
            return self.settings.default_goods_service_indicator

        return "1"

    def item_billing_indicator(self, item) -> str:
        if item.get("mseller_ecf_billing_indicator"):
            return item.mseller_ecf_billing_indicator
        return self.settings.default_billing_indicator or "1"

    def exempt_total(self) -> float:
        return sum(money(item.net_amount) for item in self.invoice.items if self.item_billing_indicator(item) == "4")

    def primary_itbis_rate(self) -> int:
        for tax in self.invoice.taxes:
            if tax.get("rate") is not None and tax.rate > 0:
                return int(tax.rate)
        return 18
