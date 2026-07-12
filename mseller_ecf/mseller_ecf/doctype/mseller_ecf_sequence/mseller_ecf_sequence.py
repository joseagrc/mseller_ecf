from __future__ import annotations

import re

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate, nowdate


ECF_RE = re.compile(r"^(E\d{2})(\d+)$")
AUTO_MANAGED_STATUSES = {"Active", "Expired", "Exhausted"}


class MSellerECFSequence(Document):
    def validate(self):
        self._set_derived_values()
        self._validate_unique_active_sequence()

    def _set_derived_values(self):
        start_prefix, start_number, padding = parse_ecf(self.start_ecf)
        end_prefix, end_number, end_padding = parse_ecf(self.end_ecf)

        if start_prefix != end_prefix:
            frappe.throw(_("Start e-NCF and End e-NCF must have the same prefix."))

        if padding != end_padding:
            frappe.throw(_("Start e-NCF and End e-NCF must use the same numeric length."))

        expected_prefix = f"E{self.ecf_type}"
        if self.ecf_type and start_prefix != expected_prefix:
            frappe.throw(_("e-CF Type {0} requires sequence prefix {1}.").format(self.ecf_type, expected_prefix))

        if end_number < start_number:
            frappe.throw(_("End e-NCF must be greater than or equal to Start e-NCF."))

        self.prefix = start_prefix
        self.padding_length = padding
        self.start_number = start_number
        self.end_number = end_number
        self.authorized_quantity = end_number - start_number + 1

        if not self.next_number:
            self.next_number = start_number

        if self.next_number < start_number:
            frappe.throw(_("Next Number cannot be lower than Start Number."))

        self.used_quantity = max(0, min(self.next_number - start_number, self.authorized_quantity))
        self.remaining_quantity = max(0, end_number - self.next_number + 1)
        self.status = get_sequence_status(
            status=self.status,
            next_number=self.next_number,
            end_number=self.end_number,
            expires_on=self.expires_on,
        )

    def _validate_unique_active_sequence(self):
        if self.status != "Active":
            return

        filters = {
            "company": self.company,
            "environment": self.environment,
            "ecf_type": self.ecf_type,
            "status": "Active",
            "auto_assign": 1,
        }
        active_name = frappe.db.get_value("MSeller ECF Sequence", filters, "name")
        if active_name and active_name != self.name and self.auto_assign:
            frappe.throw(
                _("Only one active auto-assign sequence is allowed per Company, Environment, and e-CF Type. Existing: {0}").format(
                    active_name
                )
            )

    def before_save(self):
        self.status = get_sequence_status(
            status=self.status,
            next_number=self.next_number,
            end_number=self.end_number,
            expires_on=self.expires_on,
        )


def parse_ecf(ecf: str | None) -> tuple[str, int, int]:
    if not ecf:
        frappe.throw(_("e-NCF is required."))

    match = ECF_RE.match(ecf.strip())
    if not match:
        frappe.throw(_("Invalid e-NCF format: {0}. Expected format like E310000000001.").format(ecf))

    prefix, number_text = match.groups()
    return prefix, int(number_text), len(number_text)


def format_ecf(prefix: str, number: int, padding_length: int) -> str:
    return f"{prefix}{number:0{padding_length}d}"


def get_sequence_status(status: str | None, next_number: int | None, end_number: int | None, expires_on: str | None) -> str:
    if status == "Cancelled":
        return "Cancelled"

    if expires_on and getdate(expires_on) < getdate(nowdate()):
        return "Expired"

    if next_number and end_number and next_number > end_number:
        return "Exhausted"

    if status == "Paused":
        return "Paused"

    if status in AUTO_MANAGED_STATUSES:
        return "Active"

    return status or "Active"
