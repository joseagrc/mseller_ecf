import frappe
from frappe import _
from frappe.model.document import Document

from mseller_ecf.mseller_ecf.api.client import VALID_ENVIRONMENTS


class MSellerECFSettings(Document):
    def validate(self):
        if self.environment and self.environment not in VALID_ENVIRONMENTS:
            frappe.throw(_("Environment must be one of: {0}").format(", ".join(sorted(VALID_ENVIRONMENTS))))

        if self.enabled:
            required = {
                "environment": _("Environment"),
                "email": _("Email"),
                "api_key": _("API Key"),
                "default_income_type": _("Default Income Type"),
                "default_cash_payment_type": _("Default Cash Payment Type"),
                "default_credit_payment_type": _("Default Credit Payment Type"),
                "default_unit_code": _("Default Unit Code"),
                "default_billing_indicator": _("Default Billing Indicator"),
                "default_goods_service_indicator": _("Default Goods/Service Indicator"),
            }
            for fieldname, label in required.items():
                if not self.get(fieldname):
                    frappe.throw(_("{0} is required when MSeller ECF is enabled.").format(label))

            if not self.get_password("password"):
                frappe.throw(_("Password is required when MSeller ECF is enabled."))
