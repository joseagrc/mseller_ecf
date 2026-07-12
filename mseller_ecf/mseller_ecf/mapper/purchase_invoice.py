from __future__ import annotations

import frappe
from frappe import _

from mseller_ecf.mseller_ecf.mapper.sales_invoice import ITBIS_RATE_TO_FIELD
from mseller_ecf.mseller_ecf.utils import clean_tax_id, date_dmy, money, require_value


def build_purchase_invoice_payload(invoice_name: str) -> dict:
    invoice = frappe.get_doc("Purchase Invoice", invoice_name)
    settings = frappe.get_single("MSeller ECF Settings")
    return PurchaseInvoiceECFMapper(invoice, settings).build()


class PurchaseInvoiceECFMapper:
    def __init__(self, invoice, settings):
        self.invoice = invoice
        self.settings = settings

    def build(self) -> dict:
        self.validate()

        encabezado = {
            "Version": "1.0",
            "IdDoc": self.id_doc(),
            "Emisor": self.emisor(),
            "Totales": self.totales(),
        }

        if self.invoice.mseller_ecf_type != "43":
            encabezado["Comprador"] = self.comprador()

        if self.invoice.mseller_ecf_type == "47":
            encabezado["OtraMoneda"] = self.otra_moneda()

        payload = {
            "ECF": {
                "Encabezado": encabezado,
                "DetallesItems": {"Item": self.items()},
            }
        }

        if self.invoice.mseller_ecf_type == "47":
            payload["ECF"]["Subtotales"] = self.subtotales()

        return payload

    def validate(self):
        if self.invoice.docstatus != 1:
            frappe.throw(_("Only submitted Purchase Invoices can be sent to MSeller ECF."))

        require_value(self.invoice.get("mseller_ecf_type"), _("e-CF Type"))
        require_value(self.invoice.get("mseller_ecf_ncf"), _("e-NCF"))
        require_value(self.settings.rnc_emisor or self.company_tax_id(), _("Company RNC"))

        if self.invoice.mseller_ecf_type not in {"41", "43", "47"}:
            frappe.throw(_("Purchase Invoice e-CF Type must be 41, 43, or 47."))

        if self.invoice.mseller_ecf_type == "47":
            require_value(self.foreign_identifier(), _("Foreign Identifier"))
        elif self.invoice.mseller_ecf_type == "41":
            require_value(self.supplier_tax_id(), _("Supplier Tax ID"))

        if not self.invoice.items:
            frappe.throw(_("Purchase Invoice must have at least one item for MSeller ECF."))

    def id_doc(self) -> dict:
        data = {
            "TipoeCF": self.invoice.mseller_ecf_type,
            "eNCF": self.invoice.mseller_ecf_ncf,
        }

        if self.invoice.get("mseller_ecf_sequence_expiry_date") or self.settings.sequence_expiry_date:
            data["FechaVencimientoSecuencia"] = date_dmy(
                self.invoice.get("mseller_ecf_sequence_expiry_date") or self.settings.sequence_expiry_date
            )

        if self.invoice.mseller_ecf_type == "41":
            data["IndicadorMontoGravado"] = self.settings.default_taxable_amount_indicator or "0"
            data["TipoPago"] = self.invoice.get("mseller_ecf_payment_type") or self.default_payment_type()
            if self.invoice.get("due_date") and data["TipoPago"] != "1":
                data["FechaLimitePago"] = date_dmy(self.invoice.due_date)
        elif self.invoice.mseller_ecf_type == "47":
            if self.invoice.get("mseller_ecf_payment_account"):
                data["NumeroCuentaPago"] = self.invoice.mseller_ecf_payment_account
            if self.invoice.get("mseller_ecf_payment_bank"):
                data["BancoPago"] = self.invoice.mseller_ecf_payment_bank

        return {key: value for key, value in data.items() if value not in (None, "")}

    def emisor(self) -> dict:
        data = {
            "RNCEmisor": clean_tax_id(self.settings.rnc_emisor or self.company_tax_id()),
            "RazonSocialEmisor": self.settings.issuer_legal_name or self.invoice.company,
            "DireccionEmisor": self.settings.issuer_address or self.invoice.company,
            "FechaEmision": date_dmy(self.invoice.posting_date),
        }
        if self.invoice.mseller_ecf_type == "47":
            data["NumeroFacturaInterna"] = self.invoice.name
        return data

    def comprador(self) -> dict:
        buyer = {"RazonSocialComprador": self.invoice.supplier_name}
        if self.invoice.mseller_ecf_type == "47":
            buyer["IdentificadorExtranjero"] = self.foreign_identifier()
            return buyer

        tax_id = self.supplier_tax_id()
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
                "MontoItem": money(item.net_amount or item.amount),
            }

            retention = self.item_retention(item)
            if retention:
                row["Retencion"] = retention

            if self.invoice.mseller_ecf_type == "47":
                row["OtraMonedaDetalle"] = {
                    "PrecioOtraMoneda": money(item.rate / self.conversion_rate()),
                    "MontoItemOtraMoneda": money((item.net_amount or item.amount) / self.conversion_rate()),
                }

            rows.append({key: value for key, value in row.items() if value not in (None, "")})
        return rows

    def totales(self) -> dict:
        exempt_total = self.exempt_total()
        taxable_total = money(self.invoice.net_total - exempt_total)
        totals = {
            "MontoExento": money(exempt_total),
            "MontoTotal": money(self.invoice.grand_total),
        }

        if taxable_total:
            tax_rate = self.primary_itbis_rate()
            amount_field, rate_field, tax_field = ITBIS_RATE_TO_FIELD.get(tax_rate, ITBIS_RATE_TO_FIELD[18])
            totals["MontoGravadoTotal"] = taxable_total
            totals[amount_field] = taxable_total
            totals[rate_field] = tax_rate
            totals["TotalITBIS"] = money(self.invoice.total_taxes_and_charges)
            totals[tax_field] = money(self.invoice.total_taxes_and_charges)

        itbis_withheld = self.total_itbis_withheld()
        isr_withheld = self.total_isr_withheld()
        if self.invoice.mseller_ecf_type in {"41", "47"}:
            totals["TotalITBISRetenido"] = money(itbis_withheld)
            totals["TotalISRRetencion"] = money(isr_withheld)

        return {key: value for key, value in totals.items() if value not in (None, "")}

    def otra_moneda(self) -> dict:
        conversion_rate = self.conversion_rate()
        return {
            "TipoMoneda": self.invoice.currency,
            "TipoCambio": money(conversion_rate),
            "MontoExentoOtraMoneda": money(self.exempt_total() / conversion_rate),
            "MontoTotalOtraMoneda": money(self.invoice.grand_total / conversion_rate),
        }

    def subtotales(self) -> dict:
        return {
            "Subtotal": [
                {
                    "NumeroSubTotal": "1",
                    "DescripcionSubtotal": "N/A",
                    "Orden": 1,
                    "SubTotalExento": money(self.exempt_total()),
                    "MontoSubTotal": money(self.invoice.grand_total),
                    "Lineas": len(self.invoice.items),
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

    def supplier_tax_id(self) -> str | None:
        if self.invoice.get("tax_id"):
            return self.invoice.tax_id
        supplier = frappe.get_cached_doc("Supplier", self.invoice.supplier)
        return supplier.get("tax_id")

    def foreign_identifier(self) -> str | None:
        if self.invoice.get("mseller_ecf_foreign_identifier"):
            return self.invoice.mseller_ecf_foreign_identifier
        supplier = frappe.get_cached_doc("Supplier", self.invoice.supplier)
        return supplier.get("mseller_ecf_foreign_identifier") or supplier.get("tax_id")

    def unit_code(self, uom: str) -> str:
        for row in self.settings.get("uom_mappings") or []:
            if row.uom == uom and row.dgii_unit_code:
                return row.dgii_unit_code
        return self.settings.default_unit_code or "43"

    def goods_or_service_indicator(self, item) -> str:
        if item.get("mseller_ecf_goods_service_indicator"):
            return item.mseller_ecf_goods_service_indicator
        return "2" if self.invoice.mseller_ecf_type == "47" else self.settings.default_goods_service_indicator or "1"

    def item_billing_indicator(self, item) -> str:
        if item.get("mseller_ecf_billing_indicator"):
            return item.mseller_ecf_billing_indicator
        return "1" if self.invoice.mseller_ecf_type == "41" else "4"

    def item_retention(self, item) -> dict | None:
        itbis = money(item.get("mseller_ecf_itbis_withheld") or 0)
        isr = money(item.get("mseller_ecf_isr_withheld") or 0)
        if not itbis and not isr and self.invoice.mseller_ecf_type != "41":
            return None

        data = {"IndicadorAgenteRetencionoPercepcion": "1"}
        if itbis:
            data["MontoITBISRetenido"] = itbis
        if isr:
            data["MontoISRRetenido"] = isr
        return data

    def exempt_total(self) -> float:
        return sum(
            money(item.net_amount or item.amount) for item in self.invoice.items if self.item_billing_indicator(item) == "4"
        )

    def primary_itbis_rate(self) -> int:
        for tax in self.invoice.taxes:
            if tax.get("rate") is not None and tax.rate > 0:
                return int(tax.rate)
        return 18

    def total_itbis_withheld(self) -> float:
        return sum(money(item.get("mseller_ecf_itbis_withheld") or 0) for item in self.invoice.items)

    def total_isr_withheld(self) -> float:
        return sum(money(item.get("mseller_ecf_isr_withheld") or 0) for item in self.invoice.items)

    def conversion_rate(self) -> float:
        return float(self.invoice.get("conversion_rate") or 1)
