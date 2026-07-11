from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP

import frappe
from frappe import _


def money(value) -> float:
    return float(Decimal(str(value or 0)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def date_dmy(value) -> str:
    return frappe.utils.getdate(value).strftime("%d-%m-%Y")


def clean_tax_id(value: str | None) -> str:
    return "".join(ch for ch in (value or "") if ch.isdigit())


def require_value(value, label: str):
    if value in (None, ""):
        frappe.throw(_("{0} is required for MSeller ECF.").format(label))
    return value
